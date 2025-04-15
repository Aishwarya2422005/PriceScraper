import streamlit as st
import sqlite3
from hashlib import sha256
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
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database Functions
def create_userdb():
    """Create the SQLite database and users table if not exists."""
    conn = sqlite3.connect("userdb.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def add_user(username, password):
    """Add a new user to the database."""
    conn = sqlite3.connect("userdb.db")
    cursor = conn.cursor()
    try:
        hashed_password = sha256(password.encode()).hexdigest()
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", 
                      (username, hashed_password))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

def authenticate_user(username, password):
    """Authenticate a user against the database."""
    conn = sqlite3.connect("userdb.db")
    cursor = conn.cursor()
    hashed_password = sha256(password.encode()).hexdigest()
    cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", 
                  (username, hashed_password))
    result = cursor.fetchone()
    conn.close()
    return result

# Scraping Utility Functions
def get_random_user_agent():
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        # Added more recent user agents
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ]
    return random.choice(user_agents)

def create_browser(driver_path):
    chrome_options = Options()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--headless')
    chrome_options.add_argument(f'user-agent={get_random_user_agent()}')
    # Added options to better emulate a real browser
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument('--disable-notifications')
    chrome_options.add_argument('--lang=en-US,en;q=0.9')
    
    service = Service(driver_path)
    browser = webdriver.Chrome(service=service, options=chrome_options)
    
    # Set navigator.webdriver to false using CDP
    browser.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
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
        
        WebDriverWait(browser, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-component-type="s-search-result"]'))
        )
        
        for _ in range(3):
            browser.execute_script("window.scrollBy(0, 500);")
            time.sleep(random.uniform(0.5, 1.5))
        
        html = browser.page_source
        logger.info(f"Amazon HTML length: {len(html)}")
        
        soup = BeautifulSoup(html, 'lxml')
        
        amazon_results = []
        for card in soup.select('div[data-component-type="s-search-result"]')[:5]:
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
                logger.error(f"Amazon product processing error: {e}")
        
        logger.info(f"Amazon found {len(amazon_results)} results")
        return amazon_results
    
    except Exception as e:
        logger.error(f"Amazon scraping failed: {e}")
        return []
    
    finally:
        browser.quit()

# Flipkart Scraping Function - Updated
def scrape_flipkart(name, driver_path):
    name = name.replace(' ', '+')
    URL = f"https://www.flipkart.com/search?q={name}"
    
    browser = create_browser(driver_path)
    
    try:
        # Add a debug message about starting the scrape
        logger.info(f"Starting Flipkart scrape for: {name}")
        
        # Go to Flipkart and handle any login popup that might appear
        browser.get(URL)
        
        # Wait for page to load and handle popup if it appears
        try:
            # Try to close login popup if it appears
            WebDriverWait(browser, 3).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button._2KpZ6l._2doB4z'))
            ).click()
            logger.info("Closed Flipkart login popup")
        except Exception as popup_err:
            logger.info(f"No popup found or couldn't close: {popup_err}")
            
        # Wait longer for the page to fully load
        time.sleep(8)
        
        # Scroll multiple times with pauses to ensure dynamic content loads
        for i in range(5):
            browser.execute_script(f"window.scrollBy(0, {300 + i*200});")
            time.sleep(1.5)
        
        # Scroll back to top
        browser.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)
        
        # Wait for product elements to be present
        try:
            WebDriverWait(browser, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div._1YokD2._3Mn1Gg, div._1AtVbE, div._4ddWXP'))
            )
            logger.info("Flipkart product elements found")
        except Exception as wait_err:
            logger.warning(f"Timeout waiting for Flipkart elements: {wait_err}")
        
        # Get page source and create soup
        html = browser.page_source
        logger.info(f"Flipkart HTML length: {len(html)}")
        
        # Add HTML debugging info to a file for inspection
        with open("flipkart_debug.html", "w", encoding="utf-8") as f:
            f.write(html[:10000])  # Write the first 10000 chars for debugging
        
        soup = BeautifulSoup(html, 'lxml')
        
        flipkart_results = []
        
        # Try multiple different selector patterns that Flipkart might be using
        selector_patterns = [
            'div._1AtVbE div._13oc-S',
            'div._1AtVbE',
            'div[data-id]',
            'div._4ddWXP',
            'div._2B099V',
            'a._1fQZEK',
            '._3pLy-c',
            '._4rR01T'
        ]
        
        # Try each selector pattern until we find products
        for pattern in selector_patterns:
            product_containers = soup.select(pattern)
            logger.info(f"Selector '{pattern}' found {len(product_containers)} elements")
            
            if product_containers:
                break
        
        # If we still have no containers, try a more general approach
        if not product_containers:
            logger.info("Trying generic product container identification")
            # Look for any div containing both a title-like element and a price-like element
            product_containers = []
            
            # All possible title selectors
            title_selectors = ['div._4rR01T', 'a.s1Q9rs', 'a.IRpwTa', 'div.CXW8mj', '._3LWZlK', '._4ddWXP', '.s1Q9rs']
            
            # All possible price selectors
            price_selectors = ['div._30jeq3', 'div._30jeq3._1_WHN1', 'div._25b18c']
            
            for title_sel in title_selectors:
                title_elements = soup.select(title_sel)
                for title_elem in title_elements:
                    # Find nearest container
                    container = title_elem.parent
                    for _ in range(5):  # Look up to 5 levels up
                        if container is None:
                            break
                        # Check if this container has a price element
                        for price_sel in price_selectors:
                            if container.select_one(price_sel):
                                product_containers.append(container)
                                break
                        container = container.parent
        
        logger.info(f"Found {len(product_containers)} product containers")
        
        # Process up to 5 product containers
        for container in product_containers[:5]:
            try:
                # Title extraction - using multiple possible selectors
                title_selectors = [
                    'div._4rR01T', 
                    'a.s1Q9rs', 
                    'a.IRpwTa', 
                    'div.CXW8mj',
                    '.s1Q9rs',
                    '.B_NuCI'
                ]
                
                title = "Title Not Available"
                for selector in title_selectors:
                    title_elem = container.select_one(selector)
                    if title_elem:
                        title = title_elem.text.strip()
                        break
                
                # Fallback title extraction - look for any text that might be a title
                if title == "Title Not Available":
                    for link in container.select('a'):
                        if link.text and len(link.text.strip()) > 10:
                            title = link.text.strip()
                            break
                
                # Price extraction - using multiple possible selectors
                price_selectors = [
                    'div._30jeq3._1_WHN1',
                    'div._30jeq3',
                    'div._25b18c',
                    'div._3tbKJL'
                ]
                
                price = "Price Not Available"
                for selector in price_selectors:
                    price_elem = container.select_one(selector)
                    if price_elem:
                        price = price_elem.text.replace('₹','').replace(',','')
                        break
                
                # Link extraction - using multiple possible selectors
                link_selectors = [
                    'a._1fQZEK',
                    'a.s1Q9rs',
                    'a._2rpwqI',
                    'a.IRpwTa',
                    'a[href*="/p/"]'
                ]
                
                link = "Link Not Available"
                for selector in link_selectors:
                    link_elem = container.select_one(selector)
                    if link_elem:
                        link = link_elem.get('href')
                        break
                
                # If no link found, try any link in the container
                if link == "Link Not Available":
                    any_link = container.select_one('a')
                    if any_link:
                        link = any_link.get('href')
                
                # Format the link correctly
                if link != "Link Not Available" and not link.startswith('http'):
                    link = f"https://www.flipkart.com{link}"
                
                # Only add if we have at least a title or price
                if title != "Title Not Available" or price != "Price Not Available":
                    flipkart_results.append({
                        'title': title,
                        'price': price,
                        'link': link
                    })
                    logger.info(f"Added Flipkart product: {title[:30]}...")
            
            except Exception as e:
                logger.error(f"Flipkart product processing error: {e}")
        
        # If we still have no results, try an alternative approach
        if not flipkart_results:
            logger.info("Trying alternative Flipkart extraction approach")
            
            # Look specifically for product grid items
            grid_items = soup.select('div._1xHGtK._373qXS, div._4ddWXP, div._1xHGtK')
            logger.info(f"Found {len(grid_items)} grid items")
            
            for item in grid_items[:5]:
                try:
                    title = item.select_one('a.IRpwTa, a.s1Q9rs, div._2WkVRV').text.strip() if item.select_one('a.IRpwTa, a.s1Q9rs, div._2WkVRV') else "Title Not Available"
                    price = item.select_one('div._30jeq3, div._30jeq3._1_WHN1').text.replace('₹','').replace(',','') if item.select_one('div._30jeq3, div._30jeq3._1_WHN1') else "Price Not Available"
                    link = item.select_one('a').get('href') if item.select_one('a') else "Link Not Available"
                    
                    if link != "Link Not Available" and not link.startswith('http'):
                        link = f"https://www.flipkart.com{link}"
                    
                    flipkart_results.append({
                        'title': title,
                        'price': price,
                        'link': link
                    })
                    
                except Exception as e:
                    logger.error(f"Flipkart alternative extraction error: {e}")
        
        logger.info(f"Flipkart found {len(flipkart_results)} results")
        return flipkart_results
    
    except Exception as e:
        logger.error(f"Flipkart scraping failed: {e}")
        st.error(f"Flipkart scraping encountered an error: {e}")
        return []
    
    finally:
        browser.quit()

# Price Comparison UI
def show_price_comparison():
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.title('🔍 Smart Price Comparison')
        st.markdown('### Compare prices across Amazon and Flipkart')

    search_container = st.container()
    with search_container:
        col1, col2 = st.columns([3,1])
        with col1:
            search_query = st.text_input('', placeholder='Enter product name (e.g., iPhone 13, Samsung TV, Laptop...)')
        with col2:
            search_button = st.button('Compare Prices 🔄', use_container_width=True)

    DRIVER_PATH = str(Path('chromedriver.exe').resolve())
    
    # Add debug info about the driver path
    st.sidebar.info(f"Using Chrome driver at: {DRIVER_PATH}")
    # Add a checkbox to enable debug mode
    debug_mode = st.sidebar.checkbox("Enable Debug Mode")

    if search_button and search_query:
        progress_text = "Searching across platforms..."
        progress_bar = st.progress(0)
        
        for i in range(100):
            time.sleep(0.01)
            progress_bar.progress(i + 1)

        with st.spinner('Fetching results from Amazon...'):
            amazon_results = scrape_amazon(search_query, DRIVER_PATH)
        
        with st.spinner('Fetching results from Flipkart...'):
            flipkart_results = scrape_flipkart(search_query, DRIVER_PATH)

        progress_bar.empty()
        
        # Show debug information if enabled
        if debug_mode:
            st.subheader("Debug Information")
            st.write(f"Found {len(amazon_results)} Amazon results")
            st.write(f"Found {len(flipkart_results)} Flipkart results")
            
            # Show sample of results
            if amazon_results:
                st.write("First Amazon result:", amazon_results[0])
            if flipkart_results:
                st.write("First Flipkart result:", flipkart_results[0])

        if amazon_results or flipkart_results:
            st.markdown("### 📊 Comparison Results")
            
            amazon_col, flipkart_col = st.columns(2)

            with amazon_col:
                st.markdown("""
                    <div class="company-header">
                        <h3>Amazon</h3>
                    </div>
                """, unsafe_allow_html=True)
                
                if amazon_results:
                    for product in amazon_results:
                        st.markdown(f"""
                            <div class="product-card">
                                <h4>{product['title']}</h4>
                                <p class="price-tag">₹{product['price']}</p>
                                <a href="{product['link']}" target="_blank">View on Amazon →</a>
                            </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("No Amazon results found")

            with flipkart_col:
                st.markdown("""
                    <div class="company-header">
                        <h3>Flipkart</h3>
                    </div>
                """, unsafe_allow_html=True)
                
                if flipkart_results:
                    for product in flipkart_results:
                        st.markdown(f"""
                            <div class="product-card">
                                <h4>{product['title']}</h4>
                                <p class="price-tag">₹{product['price']}</p>
                                <a href="{product['link']}" target="_blank">View on Flipkart →</a>
                            </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("No Flipkart results found")

            if amazon_results and flipkart_results:
                st.markdown("### 💡 Price Analysis")
                
                # Convert prices to float, excluding non-numeric values
                amazon_prices = []
                for p in amazon_results:
                    try:
                        if p['price'] != 'Not Available':
                            price_str = p['price'].replace('.','').replace(',','').strip()
                            if price_str.isdigit():
                                amazon_prices.append(float(price_str))
                    except (ValueError, TypeError):
                        pass
                
                flipkart_prices = []
                for p in flipkart_results:
                    try:
                        if p['price'] != 'Price Not Available':
                            price_str = p['price'].replace('.','').replace(',','').strip()
                            if price_str.isdigit():
                                flipkart_prices.append(float(price_str))
                    except (ValueError, TypeError):
                        pass

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
                elif amazon_prices:
                    st.success(f"Best price found on Amazon: ₹{min(amazon_prices):,.2f}")
                elif flipkart_prices:
                    st.success(f"Best price found on Flipkart: ₹{min(flipkart_prices):,.2f}")
                else:
                    st.warning("Could not compare prices as numeric values not found")

        else:
            st.error("No results found. Please try a different search term.")

# Main Application
def main():
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
        /* Auth styling */
        .stApp {
            font-family: 'Arial', sans-serif;
        }
        .auth-container {
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem;
        }
        .auth-title {
            text-align: center;
            color: #2c3e50;
            margin-bottom: 2rem;
        }
        </style>
    """, unsafe_allow_html=True)

    # Initialize session state and database
    create_userdb()
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "username" not in st.session_state:
        st.session_state.username = ""

    # Show logout button in sidebar if logged in
    if st.session_state.logged_in:
        if st.sidebar.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()

    # Main content
    if st.session_state.logged_in:
        show_price_comparison()
    else:
        st.markdown("<h1 class='auth-title'>Price Comparison Tool</h1>", unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["Login", "Signup"])
        
        with tab1:
            with st.form("login_form"):
                st.subheader("Login")
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submit = st.form_submit_button("Login")
                
                if submit:
                    if authenticate_user(username, password):
                        st.session_state.logged_in = True
                        st.session_state.username = username
                        st.rerun()
                    else:
                        st.error("Invalid username or password.")
        
        with tab2:
            with st.form("signup_form"):
                st.subheader("Sign Up")
                new_username = st.text_input("Username")
                new_password = st.text_input("Password", type="password")
                confirm_password = st.text_input("Confirm Password", type="password")
                submit = st.form_submit_button("Sign Up")
                
                if submit:
                    if new_password != confirm_password:
                        st.error("Passwords do not match.")
                    elif len(new_password) < 6:
                        st.error("Password must be at least 6 characters long.")
                    elif len(new_username) < 3:
                        st.error("Username must be at least 3 characters long.")
                    else:
                        if add_user(new_username, new_password):
                            st.success("Account created successfully! You can now login.")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("Username already exists. Please choose a different username.")

    # Footer
    st.markdown("""
        ---
        <div style='text-align: center; color: #666;'>
            Made with ❤️ | Data sourced from Amazon.in and Flipkart.com
        </div>
    """, unsafe_allow_html=True)

if __name__ == '__main__':
    main()
