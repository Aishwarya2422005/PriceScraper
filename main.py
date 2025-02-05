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
import pandas as pd

# Utility Functions
def get_random_user_agent():
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"
    ]
    return random.choice(user_agents)

def create_browser(driver_path):
    chrome_options = Options()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--headless')
    chrome_options.add_argument(f'user-agent={get_random_user_agent()}')
    
    service = Service(driver_path)
    browser = webdriver.Chrome(service=service, options=chrome_options)
    return browser

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
        
        amazon_results = []
        for card in soup.select('div[data-component-type="s-search-result"]')[:5]:
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
        
        product_containers = []
        for strategy in product_strategies:
            try:
                product_containers = browser.find_elements(*strategy)
                if product_containers:
                    break
            except Exception:
                continue
        
        flipkart_results = []
        for container in product_containers[:5]:
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

# Streamlit App with Enhanced UI
def main():
    # Page config
    st.set_page_config(
        page_title="Price Comparison Tool",
        page_icon="🔍",
        layout="wide"
    )

    # Custom CSS
    st.markdown("""
        <style>
        .main {
            padding: 2rem;
        }
        .stAlert {
            padding: 1rem;
            border-radius: 0.5rem;
        }
        .product-card {
            padding: 1.5rem;
            border-radius: 0.5rem;
            border: 1px solid #e0e0e0;
            margin: 1rem 0;
            background-color: white;
        }
        .price-tag {
            font-size: 1.5rem;
            color: #2ecc71;
            font-weight: bold;
        }
        .company-header {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            margin-bottom: 1rem;
        }
        </style>
    """, unsafe_allow_html=True)

    # Header Section
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.title('🔍 Smart Price Comparison')
        st.markdown('### Compare prices across Amazon and Flipkart')

    # Search Section
    search_container = st.container()
    with search_container:
        col1, col2 = st.columns([3,1])
        with col1:
            search_query = st.text_input('', placeholder='Enter product name (e.g., iPhone 13, Samsung TV, Laptop...)')
        with col2:
            search_button = st.button('Compare Prices 🔄', use_container_width=True)

    # ChromeDriver path
    DRIVER_PATH = str(Path('chromedriver.exe').resolve())

    if search_button and search_query:
        progress_text = "Searching across platforms..."
        progress_bar = st.progress(0)
        
        # Searching animation
        for i in range(100):
            time.sleep(0.01)
            progress_bar.progress(i + 1)

        with st.spinner('Fetching results...'):
            amazon_results = scrape_amazon(search_query, DRIVER_PATH)
            flipkart_results = scrape_flipkart(search_query, DRIVER_PATH)

        progress_bar.empty()

        # Results Section
        if amazon_results or flipkart_results:
            st.markdown("### 📊 Comparison Results")
            
            # Create columns for side-by-side comparison
            amazon_col, flipkart_col = st.columns(2)

            # Amazon Results
            with amazon_col:
                st.markdown("""
                    <div class="company-header">
                        <h3>Amazon</h3>
                    </div>
                """, unsafe_allow_html=True)
                
                for product in amazon_results:
                    st.markdown("""
                        <div class="product-card">
                            <h4>{}</h4>
                            <p class="price-tag">₹{}</p>
                            <a href="{}" target="_blank">View on Amazon →</a>
                        </div>
                    """.format(
                        product['title'],
                        product['price'],
                        product['link']
                    ), unsafe_allow_html=True)

            # Flipkart Results
            with flipkart_col:
                st.markdown("""
                    <div class="company-header">
                        <h3>Flipkart</h3>
                    </div>
                """, unsafe_allow_html=True)
                
                for product in flipkart_results:
                    st.markdown("""
                        <div class="product-card">
                            <h4>{}</h4>
                            <p class="price-tag">₹{}</p>
                            <a href="{}" target="_blank">View on Flipkart →</a>
                        </div>
                    """.format(
                        product['title'],
                        product['price'],
                        product['link']
                    ), unsafe_allow_html=True)

            # Price Analysis
            st.markdown("### 💡 Price Analysis")
            
            # Convert prices to numeric values for comparison
            amazon_prices = [float(p['price']) for p in amazon_results if p['price'].replace('.','').isdigit()]
            flipkart_prices = [float(p['price']) for p in flipkart_results if p['price'].replace('.','').isdigit()]

            if amazon_prices and flipkart_prices:
                analysis_cols = st.columns(3)
                
                with analysis_cols[0]:
                    st.metric("Lowest Price on Amazon", f"₹{min(amazon_prices):,.2f}")
                
                with analysis_cols[1]:
                    st.metric("Lowest Price on Flipkart", f"₹{min(flipkart_prices):,.2f}")
                
                with analysis_cols[2]:
                    price_diff = min(amazon_prices) - min(flipkart_prices)
                    better_platform = "Flipkart" if price_diff > 0 else "Amazon"
                    st.metric("Potential Savings", 
                            f"₹{abs(price_diff):,.2f}",
                            f"Better price on {better_platform}")

        else:
            st.error("No results found. Please try a different search term.")

    # Footer
    st.markdown("""
        ---
        <div style='text-align: center; color: #666;'>
            Made with ❤️ | Data sourced from Amazon.in and Flipkart.com
        </div>
    """, unsafe_allow_html=True)

if __name__ == '__main__':
    main()