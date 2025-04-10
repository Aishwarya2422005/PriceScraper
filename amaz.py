from pathlib import Path
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import time
import random
import requests
import os
import zipfile
import sys
import pickle
import logging
from win32com.client import Dispatch
from textblob import TextBlob

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DEBUG = True

def log_debug(message):
    if DEBUG:
        print(f"[DEBUG] {message}")

def get_chrome_version():
    """Get the installed Chrome version."""
    try:
        chrome_path = r"C:/Program Files/Google/Chrome/Application/chrome.exe"
        if os.path.exists(chrome_path):
            parser = Dispatch('Scripting.FileSystemObject')
            version = parser.GetFileVersion(chrome_path)
            return version.split('.')[0]  # Return major version number
    except Exception as e:
        log_debug(f"Error getting Chrome version: {e}")
    return None

def download_chromedriver():
    """Download the appropriate ChromeDriver version."""
    try:
        chrome_version = get_chrome_version()
        if not chrome_version:
            log_debug("Could not determine Chrome version. Please install Chrome first.")
            sys.exit(1)

        log_debug(f"Downloading ChromeDriver for Chrome version {chrome_version}")
        download_url = f"https://chromedriver.storage.googleapis.com/LATEST_RELEASE_{chrome_version}"
        response = requests.get(download_url)
        driver_version = response.text.strip()
        
        driver_url = f"https://chromedriver.storage.googleapis.com/{driver_version}/chromedriver_win32.zip"
        response = requests.get(driver_url)
        
        with open("chromedriver.zip", "wb") as f:
            f.write(response.content)
        
        with zipfile.ZipFile("chromedriver.zip", "r") as zip_ref:
            zip_ref.extractall()
        
        os.remove("chromedriver.zip")
        log_debug("ChromeDriver downloaded and extracted successfully")
        return True
    except Exception as e:
        log_debug(f"Error downloading ChromeDriver: {e}")
        return False

def get_random_user_agent():
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"
    ]
    return random.choice(user_agents)

def setup_chrome_driver(driver_path, headless=False):
    """Setup Chrome driver with anti-detection measures"""
    chrome_options = Options()
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('--disable-infobars')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument(f'user-agent={get_random_user_agent()}')
    chrome_options.add_argument('--start-maximized')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-software-rasterizer')
    
    # Only add headless mode if specified - visible browser helps with manual login
    if headless:
        chrome_options.add_argument('--headless')
    
    log_debug("Starting Chrome browser...")
    
    try:
        service = Service(driver_path)
        browser = webdriver.Chrome(service=service, options=chrome_options)
    except Exception as e:
        if "This version of ChromeDriver only supports Chrome version" in str(e):
            log_debug("ChromeDriver version mismatch detected. Downloading correct version...")
            if download_chromedriver():
                # Retry with new ChromeDriver
                service = Service(driver_path)
                browser = webdriver.Chrome(service=service, options=chrome_options)
            else:
                raise Exception("Failed to download compatible ChromeDriver")
        else:
            raise e
    
    browser.execute_cdp_cmd('Network.setUserAgentOverride', {
        "userAgent": get_random_user_agent()
    })
    browser.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    browser.set_window_size(1920, 1080)
    return browser

def get_html(url, driver_path):
    browser = setup_chrome_driver(driver_path, headless=True)
    
    try:
        log_debug(f"Navigating to URL: {url}")
        browser.get(url)
        
        delay = random.uniform(3, 7)
        log_debug(f"Waiting {delay:.2f} seconds for page to load...")
        time.sleep(delay)
        
        wait = WebDriverWait(browser, 10)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.s-result-item,div[data-component-type="s-search-result"]')))
        
        for i in range(3):
            scroll_amount = random.randint(300, 700)
            browser.execute_script(f"window.scrollTo(0, {scroll_amount})")
            time.sleep(random.uniform(0.5, 1.5))
        
        log_debug("Page loaded successfully")
        return browser.page_source
    except Exception as e:
        log_debug(f"Error during page load: {str(e)}")
        raise
    finally:
        browser.quit()

def extract_price(card):
    price_selectors = [
        'span.a-price-whole',
        'span.a-price span[aria-hidden="true"]',
        'span.a-price',
        'span.a-offscreen'
    ]
    
    for selector in price_selectors:
        price_elem = card.select_one(selector)
        if price_elem:
            price_text = price_elem.text.strip().replace('₹', '').replace(',', '').strip('.')
            # Extract numeric part only
            import re
            price_match = re.search(r'\d+(?:\.\d+)?', price_text)
            if price_match:
                return float(price_match.group())
    return float('inf')  # Return infinity for items with no price

def find_lowest_price_product(search_term, driver_path):
    search_term = search_term.replace(' ', '+')
    amazon_link = f"https://www.amazon.in/s?k={search_term}"
    amazon_home = 'https://www.amazon.in'
    max_retries = 3
    retry_count = 0
    
    lowest_price = float('inf')
    lowest_price_product = None
    
    while retry_count < max_retries:
        try:
            html = get_html(amazon_link, driver_path)
            log_debug("Parsing HTML with BeautifulSoup...")
            soup = BeautifulSoup(html, 'lxml')
            
            selectors = [
                'div[data-component-type="s-search-result"]',
                'div.s-result-item',
                'div.sg-col-inner'
            ]
            
            prod_cards = []
            for selector in selectors:
                prod_cards = soup.select(selector)
                if prod_cards:
                    log_debug(f"Found {len(prod_cards)} products using selector: {selector}")
                    break
            
            if not prod_cards:
                retry_count += 1
                log_debug(f"No products found. Retry {retry_count}/{max_retries}")
                time.sleep(random.uniform(5, 10))
                continue
            
            items = []
            for idx, card in enumerate(prod_cards[:10]):  # Look at first 10 products
                try:
                    title_elem = (card.select_one('h2 a.a-link-normal span') or 
                                card.select_one('h2 span.a-text-normal') or
                                card.select_one('h2'))
                    
                    if not title_elem:
                        continue
                        
                    title = title_elem.text.strip()
                    
                    link_elem = card.select_one('h2 a') or card.select_one('a.a-link-normal')
                    if not link_elem:
                        continue
                        
                    link = link_elem.get('href', '')
                    if not link.startswith('http'):
                        link = amazon_home + link
                    
                    price = extract_price(card)
                    
                    if title and link and price != float('inf'):
                        items.append([title, price, link])
                        print(f"\nProduct {idx + 1}:")
                        print(f"Title: {title}")
                        print(f"Price: ₹{price}")
                        print(f"Link: {link}")
                        
                        if price < lowest_price:
                            lowest_price = price
                            lowest_price_product = [title, price, link]
                
                except Exception as e:
                    log_debug(f"Error processing product {idx + 1}: {str(e)}")
                    continue
            
            if items:
                print("\n" + "="*50)
                print(f"LOWEST PRICE PRODUCT:")
                print(f"Title: {lowest_price_product[0]}")
                print(f"Price: ₹{lowest_price_product[1]}")
                print(f"Link: {lowest_price_product[2]}")
                print("="*50)
                return lowest_price_product
            
        except Exception as e:
            retry_count += 1
            log_debug(f"Error during scraping (attempt {retry_count}/{max_retries}): {str(e)}")
            if retry_count < max_retries:
                time.sleep(random.uniform(5, 10))
            else:
                print(f"Error during scraping: {str(e)}")
    
    return None

class AmazonReviewScraper:
    def __init__(self, driver_path):
        self.driver_path = driver_path
        self.driver = None
    
    def setup_driver(self):
        """Setup Chrome driver with anti-detection measures - visible browser for login"""
        self.driver = setup_chrome_driver(self.driver_path, headless=False)
        return self.driver

    def handle_login(self):
        """Handle Amazon login process"""
        try:
            # First check if we have saved cookies
            if os.path.exists('amazon_cookies.pkl'):
                try:
                    # Try to load existing cookies
                    self.driver.get("https://www.amazon.in")
                    cookies = pickle.load(open("amazon_cookies.pkl", "rb"))
                    for cookie in cookies:
                        try:
                            self.driver.add_cookie(cookie)
                        except Exception:
                            pass
                    self.driver.refresh()
                    time.sleep(3)
                    
                    # Check if login was successful
                    if "Hello, Sign in" not in self.driver.page_source and "Sign in" not in self.driver.page_source:
                        logger.info("Successfully logged in using saved cookies")
                        return True
                    else:
                        logger.info("Saved cookies expired or invalid, proceeding to manual login")
                        os.remove("amazon_cookies.pkl")  # Remove invalid cookies
                except Exception as e:
                    logger.error(f"Error loading cookies: {e}")
                    os.remove("amazon_cookies.pkl")  # Remove corrupted cookies
            
            # Navigate to login page
            self.driver.get("https://www.amazon.in/ap/signin")
            time.sleep(2)
            
            # Prompt user for manual login
            print("\n==== AMAZON LOGIN REQUIRED ====")
            print("A browser window has opened. Please log in to your Amazon account.")
            print("After logging in, press Enter in this console to continue...")
            print("=========================================")
            input()
            
            # Save cookies after successful login
            time.sleep(2)
            pickle.dump(self.driver.get_cookies(), open("amazon_cookies.pkl", "wb"))
            logger.info("Saved new cookies after manual login")
            return True
            
        except Exception as e:
            logger.error(f"Login error: {e}")
            return False

    def navigate_to_reviews(self, product_url):
        """Try multiple methods to access reviews"""
        # Method 1: Try direct review URL
        try:
            # Extract product ID from URL and create review URL
            if "/dp/" in product_url:
                product_id = product_url.split("/dp/")[1].split("/")[0]
                review_url = f"https://www.amazon.in/product-reviews/{product_id}/"
                
                logger.info(f"Navigating directly to reviews URL: {review_url}")
                self.driver.get(review_url)
                time.sleep(3)
                
                # Check if we need login
                if "Sign in" in self.driver.page_source and "for your security" in self.driver.page_source:
                    logger.info("Login required for reviews, handling login...")
                    if not self.handle_login():
                        return False
                    # Retry after login
                    self.driver.get(review_url)
                    time.sleep(3)
                
                # Check if we landed on a review page
                review_indicators = ["customer reviews", "Customer reviews", "Top reviews", "top reviews"]
                for indicator in review_indicators:
                    if indicator in self.driver.page_source:
                        logger.info("Successfully navigated to review page using direct URL")
                        return True
            
            # Method 2: Try original product page and click review link
            logger.info("Direct review URL failed, trying product page...")
            self.driver.get(product_url)
            time.sleep(3)
            
            # Check for login requirement
            if "Sign in" in self.driver.page_source and "for your security" in self.driver.page_source:
                logger.info("Login required, handling login...")
                if not self.handle_login():
                    return False
                # Retry after login
                self.driver.get(product_url)
                time.sleep(3)
                
            # Try to find and click a review link
            try:
                review_link_texts = ["See all reviews", "See all customer reviews", "See more reviews"]
                for text in review_link_texts:
                    try:
                        review_link = WebDriverWait(self.driver, 3).until(
                            EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, text))
                        )
                        review_link.click()
                        logger.info(f"Clicked '{text}' link")
                        time.sleep(3)
                        return True
                    except:
                        continue
                
                # Try finding review section by CSS selector
                review_selectors = ["a[data-hook='see-all-reviews-link-foot']", 
                                   "a.a-link-emphasis[href*='customer-reviews']"]
                for selector in review_selectors:
                    try:
                        review_link = WebDriverWait(self.driver, 3).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                        review_link.click()
                        logger.info(f"Clicked review link using selector: {selector}")
                        time.sleep(3)
                        return True
                    except:
                        continue
                        
                # If we can't find a direct link, maybe we're already on a page with reviews
                if "customer review" in self.driver.page_source.lower():
                    logger.info("Found review content on current page")
                    return True
            except Exception as e:
                logger.error(f"Error finding review link: {e}")
            
            logger.warning("Could not navigate to reviews. Will try to extract from current page")
            return True  # Return True to attempt extraction even if navigation failed
                
        except Exception as e:
            logger.error(f"Error navigating to reviews: {e}")
            return False

    def extract_review_titles(self):
        """Extract review titles and comments from the current page"""
        review_titles = []
        time.sleep(2)

        try:
            # Try multiple selectors for reviews
            selectors = [
                'a[data-hook="review-title"]', 
                'span[data-hook="review-title"]',
                '.review-title',
                '.a-size-base.review-title',
                'div[data-hook="review"]',
                'div.review',
                'div.a-section.review'
            ]
            
            for selector in selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    logger.info(f"Found {len(elements)} review elements with selector: {selector}")
                    break

            if not elements:
                # Try scrolling to load potential lazy-loaded content
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                
                # Try again after scrolling
                for selector in selectors:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        logger.info(f"Found {len(elements)} review elements after scrolling")
                        break

            # Extract text from elements                
            for element in elements:
                try:
                    # Get title text or full review text if title not available
                    title = element.text.strip()
                    if title and len(title) > 5:  # Filter out very short titles/empty elements
                        # Extract just the first line if it's a full review
                        if "\n" in title:
                            title = title.split("\n")[0]
                        review_titles.append(title)
                except:
                    continue

            # Deduplicate reviews
            review_titles = list(set(review_titles))
            logger.info(f"Extracted {len(review_titles)} unique review titles")
            return review_titles

        except Exception as e:
            logger.error(f"Error extracting review titles: {e}")
            return []

    def go_to_next_page(self):
        """Attempt to go to the next page of reviews"""
        try:
            next_selectors = [
                'li.a-last a',
                'a.a-link-normal[href*="pageNumber"]',
                'a[href*="pageNumber"][aria-label*="Next"]',
                'a.a-link-normal.a-text-normal[href*="page="]:not([href*="currentPage"])'
            ]
            
            for selector in next_selectors:
                try:
                    next_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    # Make sure it's not disabled
                    if "a-disabled" not in next_button.get_attribute("class") and next_button.is_displayed():
                        next_button.click()
                        time.sleep(3)
                        logger.info("Navigated to next page")
                        return True
                except NoSuchElementException:
                    continue
            
            logger.info("No more pages available")
            return False
            
        except Exception as e:
            logger.error(f"Error navigating to next page: {e}")
            return False

    def analyze_sentiment(self, reviews):
        """Analyze sentiment and determine if the product is worth buying"""
        if not reviews:
            return "No reviews found to analyze"
            
        positive_count = 0
        negative_count = 0
        neutral_count = 0

        print("\n🔹 Sentiment Analysis of Reviews:")
        for i, review in enumerate(reviews, start=1):
            sentiment = TextBlob(review).sentiment.polarity  # Get sentiment score
            sentiment_str = ""
            
            if sentiment > 0.1:
                positive_count += 1
                sentiment_str = "Positive 👍"
            elif sentiment < -0.1:
                negative_count += 1
                sentiment_str = "Negative 👎"
            else:
                neutral_count += 1
                sentiment_str = "Neutral 😐"
                
            print(f"{i}. \"{review}\" - {sentiment_str} (score: {sentiment:.2f})")

        # Print sentiment distribution
        total = positive_count + negative_count + neutral_count
        if total == 0:
            return "No reviews found with sentiment"
            
        print(f"\n📊 Sentiment Distribution:")
        print(f"Positive reviews: {positive_count} ({positive_count/total*100:.1f}%)")
        print(f"Neutral reviews: {neutral_count} ({neutral_count/total*100:.1f}%)")
        print(f"Negative reviews: {negative_count} ({negative_count/total*100:.1f}%)")

        # Determine final decision (ignoring neutral reviews for decision)
        decision_count = positive_count + negative_count
        if decision_count == 0:
            return "Neutral ⚖️ (No clear positive or negative sentiment)"
            
        if positive_count > negative_count:
            confidence = positive_count / max(1, decision_count) * 100
            return f"Buy ✅ ({confidence:.1f}% positive reviews)"
        elif negative_count > positive_count:
            confidence = negative_count / max(1, decision_count) * 100
            return f"Don't Buy ❌ ({confidence:.1f}% negative reviews)"
        else:
            return "Neutral ⚖️ (Equal positive and negative sentiment)"

    def scrape_review_titles(self, product_url, max_pages=2):
        """Scrape up to max_pages review titles from Amazon and analyze sentiment"""
        self.setup_driver()
        all_titles = []
        page_number = 1

        try:
            # Navigate to reviews with improved logic
            if not self.navigate_to_reviews(product_url):
                logger.error("Failed to navigate to reviews")
                # Still attempt to extract from current page
            
            # Extract reviews from pages
            while page_number <= max_pages:
                logger.info(f"Scraping page {page_number}")

                page_titles = self.extract_review_titles()
                all_titles.extend(page_titles)
                logger.info(f"Collected {len(page_titles)} titles from page {page_number}")

                if not page_titles or not self.go_to_next_page():
                    logger.info("No more pages available")
                    break

                page_number += 1
                time.sleep(2)

            # Perform sentiment analysis
            if all_titles:
                final_decision = self.analyze_sentiment(all_titles)
                return all_titles, final_decision
            else:
                return [], "No reviews could be extracted"
            
        except Exception as e:
            logger.error(f"Error during review scraping: {e}")
            return [], f"Error occurred: {str(e)}"
        finally:
            if self.driver:
                self.driver.quit()

def main():
    # Setup chrome driver path
    DRIVER_PATH = str(Path('chromedriver.exe').resolve())
    
    # Get user input for product search
    search_term = input("Enter item to search: ")
    
    # Find the lowest priced product
    print("\n🔍 Searching for the lowest priced product...")
    lowest_price_product = find_lowest_price_product(search_term, DRIVER_PATH)
    
    if not lowest_price_product:
        print("❌ Could not find any products. Please try again with a different search term.")
        return
    
    product_url = lowest_price_product[2]
    
    # Now scrape reviews for the lowest priced product
    print("\n📊 Analyzing reviews for the lowest priced product...")
    print(f"Product: {lowest_price_product[0]}")
    print(f"Price: ₹{lowest_price_product[1]}")
    print(f"URL: {product_url}")
    
    # Initialize review scraper and analyze reviews
    scraper = AmazonReviewScraper(DRIVER_PATH)
    
    # Clear existing cookies if user wants to
    cookie_choice = input("\nDo you want to clear existing login cookies and log in again? (y/n): ").strip().lower()
    if cookie_choice == 'y' and os.path.exists('amazon_cookies.pkl'):
        os.remove('amazon_cookies.pkl')
        print("Existing cookies cleared. You will need to log in again.")
    
    review_titles, decision = scraper.scrape_review_titles(product_url, max_pages=3)
    
    print("\n🔹 Extracted Review Titles:")
    if review_titles:
        for i, title in enumerate(review_titles, start=1):
            print(f"{i}. {title}")
    else:
        print("No review titles were extracted.")
    
    print("\n🔍 Final Verdict:", decision)
    
    print("\n💡 Should you buy the product?")
    if "Buy ✅" in decision:
        print("Recommendation: YES - This product appears to have overall positive reviews and is the lowest priced option.")
    elif "Don't Buy ❌" in decision:
        print("Recommendation: NO - Although this is the lowest priced option, reviews suggest poor quality or satisfaction.")
    else:
        print("Recommendation: MAYBE - Reviews are mixed. Consider your specific needs carefully.")

if __name__ == "__main__":
    main()
