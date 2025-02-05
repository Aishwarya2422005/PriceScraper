from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def create_browser(driver_path):
    chrome_options = Options()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-javascript')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
    
    service = Service(driver_path)
    browser = webdriver.Chrome(service=service, options=chrome_options)
    return browser

def flipkart():
    URL = flipkart_link
    browser = create_browser(DRIVER_PATH)
    
    try:
        # Navigate to the page
        browser.get(URL)
        time.sleep(10)  # Extended wait time
        
        # Try multiple strategies to find product elements
        product_strategies = [
            (By.CSS_SELECTOR, 'div[data-id]'),
            (By.CSS_SELECTOR, 'div._1AtVbE'),
            (By.XPATH, '//div[contains(@class, "product")]'),
            (By.XPATH, '//a[contains(@href, "/p/")]/../..')
        ]
        
        products_found = False
        for strategy in product_strategies:
            try:
                product_containers = browser.find_elements(*strategy)
                if product_containers:
                    products_found = True
                    print(f"Found {len(product_containers)} products using {strategy}")
                    break
            except Exception as e:
                print(f"Strategy {strategy} failed: {e}")
        
        if not products_found:
            print("No products found. Saving page source for debugging.")
            with open('debug_page_source.html', 'w', encoding='utf-8') as f:
                f.write(browser.page_source)
            return
        
        # Limit to first 5 products
        for idx, container in enumerate(product_containers[:5], 1):
            try:
                # Title extraction with multiple attempts
                try:
                    title = container.find_element(By.XPATH, './/div[contains(@class, "_4rR01t") or contains(text(), "iPhone")]').text
                except:
                    title = "Title Not Available"
                
                # Price extraction with multiple attempts
                try:
                    price = container.find_element(By.XPATH, './/div[contains(@class, "_30jeq3") or contains(text(), "₹")]').text
                    price = price.replace('₹','').replace(',','')
                except:
                    price = "Price Not Available"
                
                # Link extraction
                try:
                    link_elem = container.find_element(By.XPATH, './/a[contains(@href, "/p/")]')
                    link = link_elem.get_attribute('href')
                except:
                    link = "Link Not Available"
                
                # Print product details
                print(f"\nProduct {idx}:")
                print(f"Title: {title}")
                print(f"Price: ₹{price}")
                print(f"Link: {link}")
            
            except Exception as e:
                print(f"Error processing product {idx}: {e}")
    
    except Exception as e:
        print(f"Overall scraping error: {e}")
        with open('debug_error_page.html', 'w', encoding='utf-8') as f:
            f.write(browser.page_source)
    
    finally:
        browser.quit()

if __name__ == "__main__":
    name = input("Enter item to search: ")
    name = name.replace(' ', '+')
    flipkart_link = f"https://www.flipkart.com/search?q={name}"
    DRIVER_PATH = str(Path('chromedriver.exe').resolve())
    
    flipkart()