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
        
        WebDriverWait(browser, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-component-type="s-search-result"]'))
        )
        
        for _ in range(3):
            browser.execute_script("window.scrollBy(0, 500);")
            time.sleep(random.uniform(0.5, 1.5))
        
        html = browser.page_source
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
        time.sleep(10)
        
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
                try:
                    title = container.find_element(By.XPATH, './/div[contains(@class, "_4rR01t") or contains(text(), "iPhone")]').text
                except:
                    title = "Title Not Available"
                
                try:
                    price_elem = container.find_element(By.XPATH, './/div[contains(@class, "_30jeq3") or contains(text(), "₹")]')
                    price = price_elem.text.replace('₹','').replace(',','')
                except:
                    price = "Price Not Available"
                
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

    if search_button and search_query:
        progress_text = "Searching across platforms..."
        progress_bar = st.progress(0)
        
        for i in range(100):
            time.sleep(0.01)
            progress_bar.progress(i + 1)

        with st.spinner('Fetching results...'):
            amazon_results = scrape_amazon(search_query, DRIVER_PATH)
            flipkart_results = scrape_flipkart(search_query, DRIVER_PATH)

        progress_bar.empty()

        if amazon_results or flipkart_results:
            st.markdown("### 📊 Comparison Results")
            
            amazon_col, flipkart_col = st.columns(2)

            with amazon_col:
                st.markdown("""
                    <div class="company-header">
                        <h3>Amazon</h3>
                    </div>
                """, unsafe_allow_html=True)
                
                for product in amazon_results:
                    st.markdown(f"""
                        <div class="product-card">
                            <h4>{product['title']}</h4>
                            <p class="price-tag">₹{product['price']}</p>
                            <a href="{product['link']}" target="_blank">View on Amazon →</a>
                        </div>
                    """, unsafe_allow_html=True)

            with flipkart_col:
                st.markdown("""
                    <div class="company-header">
                        <h3>Flipkart</h3>
                    </div>
                """, unsafe_allow_html=True)
                
                for product in flipkart_results:
                    st.markdown(f"""
                        <div class="product-card">
                            <h4>{product['title']}</h4>
                            <p class="price-tag">₹{product['price']}</p>
                            <a href="{product['link']}" target="_blank">View on Flipkart →</a>
                        </div>
                    """, unsafe_allow_html=True)

            st.markdown("### 💡 Price Analysis")
            
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