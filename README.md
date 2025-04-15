🛍️ PriceScraper – Your Smart E-commerce Price Comparison Tool
PriceScraper is a smart and automated price comparison engine designed to fetch real-time product data from leading Indian e-commerce platforms — Amazon and Flipkart. Built using Python, Selenium, and a simple GUI/CLI interface, PriceScraper helps users compare prices, find the best deals, and make smarter shopping decisions 🧠💰.

📂 Project Structure
Your project is neatly organized with multiple modules for scraping, data handling, and user interface:
├── amaz.py                   # Amazon scraper logic
├── amazon_searcher.py       # Search functionality for Amazon
├── amazonreview.py          # Fetches and displays Amazon reviews
├── flipAPI.py               # Flipkart scraping API
├── flipkart_searcher.py     # Search functionality for Flipkart
├── flipkart_debug.html      # Debugging HTML structure for Flipkart
├── app.py                   # Entry point for GUI-based interface
├── without_gui.py           # CLI-based version of the app
├── main.py                  # Ties together all modules
├── test.py                  # Testing module
├── main.exe                 # Windows executable
├── amazon_cookies.pkl       # Stores session cookies for Amazon
├── chromedriver.exe         # Chrome driver for Selenium automation
├── userdb.db                # SQLite database for user/session data
├── requirements.txt         # Python dependencies
└── static/, templates/      # (Optional) GUI HTML/CSS if added


🚀 Features
🔎 Product Search & Comparison: Enter a product name to fetch real-time prices from Amazon and Flipkart.

📦 Review Aggregation: Extracts product reviews (Amazon) to assist buying decisions.

🖥️ Dual Interface: Available in both GUI (using Tkinter/Flask) and CLI (via terminal) modes.

🧠 Smart Search Matching: Fetches the top result from both platforms for fair comparison.

📁 Session Handling: Uses Amazon cookies to bypass minor restrictions or speed up scraping.

💬 Simple Design: Clean and easy-to-navigate application structure for ease of use.

🛠️ Technology Stack
![image](https://github.com/user-attachments/assets/afa80568-7603-483e-906b-02ee7ca4cffe)

💻 How to Run the Project
🔧 Prerequisites
Make sure you have Python 3.x, pip, and Chrome browser installed.
git clone https://github.com/Aishwarya2422005/PriceScraper.git
cd PriceScraper
pip install -r requirements.txt

Start the App
Without GUI (Terminal Mode):
python without_gui.py

With GUI (If implemented using app.py):
python app.py


🤖How It Works
Input: The user enters a product name (e.g., “iPhone 14”).

Search: Product names are searched in Amazon and Flipkart via automation.

Scraping: The scraper pulls title, price, and optionally reviews.

Display: Output is shown side-by-side in the terminal or GUI for comparison.

Review Analysis: Amazon review data is also fetched to aid decisions.

👨‍👩‍👧‍👦 Use Cases
📌 Shoppers looking for the best price across platforms

📌 Deal-hunters during sales and festive seasons

📌 Students learning web scraping and automation

📌 Developers building retail price comparison systems

OUPUT:
![image](https://github.com/user-attachments/assets/7d9f233e-0c19-4e05-b03e-eedf6d4f495f)
![image](https://github.com/user-attachments/assets/60d2362e-0f00-41fd-94ef-1aa40ddc14d1)
![image](https://github.com/user-attachments/assets/4cae4180-bc8f-483d-9e08-ffecd6f3698c)
![image](https://github.com/user-attachments/assets/69c06e24-3fea-4b4c-a657-a17d11d1bcd4)






