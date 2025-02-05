from pathlib import Path
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import time
import random

DEBUG = True

def log_debug(message):
    if DEBUG:
        print(f"[DEBUG] {message}")

def get_random_user_agent():
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"
    ]
    return random.choice(user_agents)

def get_html(url):
    op = webdriver.ChromeOptions()
    op.add_argument('--disable-blink-features=AutomationControlled')
    op.add_argument('--no-sandbox')
    op.add_argument('--disable-dev-shm-usage')
    op.add_argument(f'user-agent={get_random_user_agent()}')
    
    # Additional settings to avoid detection
    op.add_experimental_option("excludeSwitches", ["enable-automation"])
    op.add_experimental_option('useAutomationExtension', False)
    
    # Add additional headers
    op.add_argument('--disable-gpu')
    op.add_argument('--disable-software-rasterizer')
    
    log_debug("Starting Chrome browser...")
    
    service = Service(DRIVER_PATH)
    browser = webdriver.Chrome(service=service, options=op)
    
    # Set window size to look more like a real browser
    browser.set_window_size(1920, 1080)
    
    try:
        log_debug(f"Navigating to URL: {url}")
        browser.get(url)
        
        # Add random delay between 3-7 seconds
        delay = random.uniform(3, 7)
        log_debug(f"Waiting {delay:.2f} seconds for page to load...")
        time.sleep(delay)
        
        # Wait for specific elements instead of fixed time
        wait = WebDriverWait(browser, 10)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.s-result-item,div[data-component-type="s-search-result"]')))
        
        # Simulate human-like scrolling
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
    """Extract price using multiple possible selectors"""
    price_selectors = [
        'span.a-price-whole',
        'span.a-price span[aria-hidden="true"]',
        'span.a-price',
        'span.a-offscreen'  # Added additional selector
    ]
    
    for selector in price_selectors:
        price_elem = card.select_one(selector)
        if price_elem:
            price = price_elem.text.strip().replace('₹', '').replace(',', '').strip('.')
            if price:
                return price
    return 'Price not available'

def amazon():
    URL = amazon_link
    amazon_home = 'https://www.amazon.in'
    
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            html = get_html(URL)
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
                time.sleep(random.uniform(5, 10))  # Random delay between retries
                continue
            
            items = []
            for idx, card in enumerate(prod_cards[:5]):
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
                        
                    link = amazon_home + link_elem.get('href', '')
                    
                    price = extract_price(card)
                    
                    if title and link:
                        items.append([title, price, link])
                        print(f"\nProduct {idx + 1}:")
                        print(f"Title: {title}")
                        print(f"Price: ₹{price}" if price != 'Price not available' else "Price: Not available")
                        print(f"Link: {link}")
                
                except Exception as e:
                    log_debug(f"Error processing product {idx + 1}: {str(e)}")
                    continue
            
            if items:
                break  # Success! Exit the retry loop
            
        except Exception as e:
            retry_count += 1
            log_debug(f"Error during scraping (attempt {retry_count}/{max_retries}): {str(e)}")
            if retry_count < max_retries:
                time.sleep(random.uniform(5, 10))  # Random delay between retries
            else:
                print(f"Error during scraping: {str(e)}")

if __name__ == "__main__":
    name = input("Enter item to search: ")
    name = name.replace(' ', '+')
    amazon_link = f"https://www.amazon.in/s?k={name}"
    DRIVER_PATH = str(Path('chromedriver.exe').resolve())
    
    amazon()