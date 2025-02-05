import streamlit as st
from pathlib import Path
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import time
import random

# Shared WebDriver Creation Function
def create_browser(driver_path):
    chrome_options = Options()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--headless')
    chrome_options.add_argument(f'user-agent={get_random_user_agent()}')
    
    service = Service(driver_path)
    browser = webdriver.Chrome(service=service, options=chrome_options)
    return browser

# Utility Functions
def get_random_user_agent():
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"
    ]
    return random.choice(user_agents)

# Amazon Scraping Function
def scrape_amazon(name, driver_path):
    name = name.replace(' ', '+')
    URL = f"https://www.amazon.in/s?k={name}"
    amazon_home = 'https://www.amazon.in'
    
    browser = create_browser(driver_path)
    
    try:
        browser.get(URL)
        time.sleep(random.uniform(3, 7))
        
        # Wait for search results
        WebDriverWait(browser, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-component-type="s-search-result"]'))
        )
        
        # Scroll to load more results
        for _ in range(3):
            browser.execute_script("window.scrollBy(0, 500);")
            time.sleep(random.uniform(0.5, 1.5))
        
        html = browser.page_source
        soup = BeautifulSoup(html, 'lxml')
        
        # Product card selectors
        selectors = [
            'div[data-component-type="s-search-result"]',
            'div.s-result-item',
            'div.sg-col-inner'
        ]
        
        amazon_results = []
        for card in soup.select(selectors[0])[:5]:
            try:
                # Title extraction
                title_elem = (card.select_one('h2 a.a-link-normal span') or 
                              card.select_one('h2 span.a-text-normal') or
                              card.select_one('h2'))
                
                if not title_elem:
                    continue
                    
                title = title_elem.text.strip()
                
                # Link extraction
                link_elem = card.select_one('h2 a') or card.select_one('a.a-link-normal')
                if not link_elem:
                    continue
                    
                link = amazon_home + link_elem.get('href', '')
                
                # Price extraction
                price_selectors = [
                    'span.a-price-whole',
                    'span.a-price span[aria-hidden="true"]',
                    'span.a-price',
                    'span.a-offscreen'
                ]
                
                price = 'Not Available'
                for selector in price_selectors:
                    price_elem = card.select_one(selector)
                    if price_elem:
                        price = price_elem.text.strip().replace('₹', '').replace(',', '').strip('.')
                        break
                
                amazon_results.append({
                    'title': title,
                    'price': price,
                    'link': link
                })
                
            except Exception as e:
                st.warning(f"Amazon scraping error: {e}")
        
        return amazon_results
    
    except Exception as e:
        st.error(f"Amazon scraping failed: {e}")
        return []
    
    finally:
        browser.quit()

# Flipkart Scraping Function
def scrape_flipkart(name, driver_path):
    name = name.replace(' ', '+')
    URL = f"https://www.flipkart.com/search?q={name}"
    
    browser = create_browser(driver_path)
    
    try:
        browser.get(URL)
        time.sleep(10)  # Extended wait time
        
        # Try multiple strategies to find product elements
        product_strategies = [
            (By.CSS_SELECTOR, 'div[data-id]'),
            (By.CSS_SELECTOR, 'div._1AtVbE'),
            (By.XPATH, '//div[contains(@class, "product")]'),
            (By.XPATH, '//a[contains(@href, "/p/")]/../..')
        ]
        
        for strategy in product_strategies:
            try:
                product_containers = browser.find_elements(*strategy)
                if product_containers:
                    break
            except Exception as e:
                st.warning(f"Flipkart strategy {strategy} failed")
        
        flipkart_results = []
        for idx, container in enumerate(product_containers[:5]):
            try:
                # Title extraction
                try:
                    title = container.find_element(By.XPATH, './/div[contains(@class, "_4rR01t") or contains(text(), "iPhone")]').text
                except:
                    title = "Title Not Available"
                
                # Price extraction
                try:
                    price_elem = container.find_element(By.XPATH, './/div[contains(@class, "_30jeq3") or contains(text(), "₹")]')
                    price = price_elem.text.replace('₹','').replace(',','')
                except:
                    price = "Price Not Available"
                
                # Link extraction
                try:
                    link_elem = container.find_element(By.XPATH, './/a[contains(@href, "/p/")]')
                    link = link_elem.get_attribute('href')
                except:
                    link = "Link Not Available"
                
                flipkart_results.append({
                    'title': title,
                    'price': price,
                    'link': link
                })
            
            except Exception as e:
                st.warning(f"Flipkart product processing error: {e}")
        
        return flipkart_results
    
    except Exception as e:
        st.error(f"Flipkart scraping failed: {e}")
        return []
    
    finally:
        browser.quit()

# Streamlit App
def main():
    st.title('Price Comparison: Amazon vs Flipkart')
    
    # ChromeDriver path
    DRIVER_PATH = str(Path('chromedriver.exe').resolve())
    
    # Search input
    search_query = st.text_input('Enter product to search')
    
    if st.button('Compare Prices'):
        if search_query:
            with st.spinner('Searching Amazon and Flipkart...'):
                # Parallel scraping
                amazon_results = scrape_amazon(search_query, DRIVER_PATH)
                flipkart_results = scrape_flipkart(search_query, DRIVER_PATH)
            
            # Display Results
            st.subheader('Amazon Results')
            for product in amazon_results:
                st.write(f"**Title:** {product['title']}")
                st.write(f"**Price:** ₹{product['price']}")
                st.write(f"**Link:** {product['link']}")
                st.markdown('---')
            
            st.subheader('Flipkart Results')
            for product in flipkart_results:
                st.write(f"**Title:** {product['title']}")
                st.write(f"**Price:** ₹{product['price']}")
                st.write(f"**Link:** {product['link']}")
                st.markdown('---')

if __name__ == '__main__':
    main()