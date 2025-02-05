from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
import time
import random

class Flipkart:
    def __init__(self):
        self.main_url = 'https://www.flipkart.com/'
        self.driver = None
        self.keywords = []

    def create_driver(self):
        try:
            options = Options()
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--disable-blink-features=AutomationControlled")
            # Add these new options to handle SSL issues
            options.add_argument("--ignore-certificate-errors")
            options.add_argument("--ignore-ssl-errors")
            options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
            options.add_experimental_option('useAutomationExtension', False)
            options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            
            service = Service(str(Path('chromedriver.exe').resolve()))
            self.driver = webdriver.Chrome(service=service, options=options)
            
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })
            
            # Add page load timeout
            self.driver.set_page_load_timeout(30)
            self.driver.maximize_window()
            
            # Add error handling for initial page load
            try:
                self.driver.get(self.main_url)
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.NAME, "q"))
                )
                print("[DEBUG] Page loaded successfully")
            except Exception as e:
                print(f"[WARNING] Initial page load issue: {e}")
                self.driver.refresh()
            
            return self.driver
            
        except Exception as e:
            print(f"Error creating WebDriver: {e}")
            return None

    def get_search_keywords(self):
        print("\nEnter your search terms (one per line)")
        print("Press Enter twice to start searching\n")
        
        while True:
            try:
                keyword = input("Enter product to search (or press Enter to start): ").strip()
                if not keyword and not self.keywords:
                    print("Please enter at least one product to search.")
                    continue
                elif not keyword and self.keywords:
                    break
                self.keywords.append(keyword)
                print(f"Added: {keyword}")
            except KeyboardInterrupt:
                print("\nInput cancelled by user.")
                return False
            except Exception as e:
                print(f"Error reading input: {e}")
                continue
        return True

    def handle_popups(self):
        try:
            # Add multiple selectors to handle different popup types
            popup_selectors = [
                "//button[contains(@class, '_2KpZ6l')]",
                "//button[contains(@class, '_2doB4z')]",
                "//button[@class='_30XB9F']"
            ]
            
            for selector in popup_selectors:
                try:
                    close_button = WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    close_button.click()
                    time.sleep(1)
                except TimeoutException:
                    continue
        except Exception as e:
            print(f"[WARNING] Popup handling: {e}")

    def scrape_with_selenium(self):
        try:
            if not self.get_search_keywords():
                return
                
            print(f"\nStarting search for {len(self.keywords)} products...")
            
            self.driver = self.create_driver()
            if not self.driver:
                return
            
            for keyword in self.keywords:
                try:
                    self.handle_popups()
                    
                    # Search for product with retry mechanism
                    max_retries = 3
                    for attempt in range(max_retries):
                        try:
                            input_search = WebDriverWait(self.driver, 10).until(
                                EC.presence_of_element_located((By.NAME, "q"))
                            )
                            input_search.clear()
                            input_search.send_keys(keyword)
                            
                            search_button = WebDriverWait(self.driver, 10).until(
                                EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']"))
                            )
                            search_button.click()
                            
                            # Wait for either product selector to be present
                            WebDriverWait(self.driver, 10).until(
                                lambda driver: driver.find_elements(By.CSS_SELECTOR, "div._4rR01T") or 
                                             driver.find_elements(By.CSS_SELECTOR, "div.s1Q9rs")
                            )
                            break
                        except TimeoutException:
                            if attempt < max_retries - 1:
                                print(f"[WARNING] Retry attempt {attempt + 1} for search")
                                self.driver.refresh()
                                continue
                            raise
                    
                    print("[DEBUG] Parsing page...")
                    time.sleep(2)  # Allow time for dynamic content to load
                    
                    # Try both product card layouts
                    products = self.driver.find_elements(By.CSS_SELECTOR, "div._4rR01T, div.s1Q9rs")
                    
                    if not products:
                        print(f"[WARNING] No products found for '{keyword}'")
                        continue
                    
                    print(f"[DEBUG] Found {len(products)} products")
                    
                    # Process first 10 products
                    for idx, product in enumerate(products[:10], 1):
                        try:
                            # Get parent container with multiple possible class names
                            container = product.find_element(By.XPATH, "./ancestor::div[contains(@class, '_1AtVbE') or contains(@class, '_13oc-S')]")
                            
                            # Extract product details with error handling
                            title = product.text.strip()
                            
                            try:
                                price = container.find_element(By.CSS_SELECTOR, "div._30jeq3").text.strip()
                            except:
                                price = "Price not found"
                            
                            try:
                                link = container.find_element(By.CSS_SELECTOR, "a._1fQZEK, a._2rpwqI").get_attribute("href")
                            except:
                                link = "Link not found"
                            
                            print(f"\nProduct {idx}:")
                            print(f"Title: {title}")
                            print(f"Price: {price}")
                            print(f"Link: {link}")
                            
                        except Exception as e:
                            print(f"[WARNING] Error processing product {idx}: {e}")
                            continue
                    
                except Exception as e:
                    print(f"Error processing search for '{keyword}': {e}")
                    continue
                
        except Exception as e:
            print(f"Scraping error: {e}")
        finally:
            if self.driver:
                self.driver.quit()

if __name__ == '__main__':
    print("************************************************************************")
    print("                     Starting Flipkart Scraper                           ")
    print("************************************************************************")
    
    webscrapper = Flipkart()
    webscrapper.scrape_with_selenium()
    print("\nScraping completed.")