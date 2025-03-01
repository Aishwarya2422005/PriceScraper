import streamlit as st
import sqlite3
from hashlib import sha256

# Database setup and user management functions
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

# Initialize database and session state
create_userdb()

# Set up page configuration
st.set_page_config(
    page_title="Authentication System",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Background image URL - Replace with your preferred image URL
background_image_url = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRp1yW5GPEuucFyCy3QeEWBwrGDxo6kxeIWtQ&s"
# Apply styling
st.markdown(
    f"""
    <style>
        /* Background styling */
        .stApp {{
            background-image: url("{background_image_url}");
            background-size: cover;
            background-attachment: fixed;
            background-position: center;
            background-repeat: no-repeat;
            font-family: 'Arial', sans-serif;
        }}
        
        /* Title styling */
        h1 {{
            font-family: 'Dancing Script', cursive;
            color: #2c3e50;
            font-size: 48px;
            text-align: center;
            margin-bottom: 20px;
        }}
        
        /* Header styling */
        h2, h3 {{
            color: #2c3e50;
            text-align: center;
        }}
        
        /* Sidebar styling */
        [data-testid="stSidebar"] {{
            background-color: rgba(0, 0, 0, 0.8);
            color: white;
            padding: 20px;
        }}
        
        /* Form styling */
        .stTextInput > div > div > input {{
            background-color: rgba(255, 255, 255, 0.8);
            border-radius: 5px;
            border: 1px solid #2c3e50;
            color: #2c3e50;
        }}
        
        /* Button styling */
        .stButton > button {{
            background-color: rgba(44, 62, 80, 0.9);
            color: white;
            border: none;
            border-radius: 5px;
            padding: 10px 20px;
            width: 100%;
        }}
        
        .stButton > button:hover {{
            background-color: rgba(44, 62, 80, 1);
        }}
        
        /* Tab styling */
        .stTabs [data-baseweb="tab-list"] {{
            background-color: transparent;
        }}
        
        .stTabs [data-baseweb="tab"] {{
            background-color: rgba(255, 255, 255, 0.1);
            color: #2c3e50;
        }}
        
        .stTabs [data-baseweb="tab-panel"] {{
            background-color: rgba(255, 255, 255, 0.8);
            border-radius: 10px;
            padding: 20px;
            backdrop-filter: blur(5px);
        }}
    </style>
    """,
    unsafe_allow_html=True
)

# Include Google Font
st.markdown(
    """
    <link href="https://fonts.googleapis.com/css2?family=Dancing+Script:wght@600&display=swap" rel="stylesheet">
    """,
    unsafe_allow_html=True
)

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""

# Login/Signup Interface
def render_auth_ui():
    """Render the login/signup interface."""
    st.markdown("<h1>Authentication System</h1>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["Login", "Signup"])
    
    # Login Tab
    with tab1:
        st.markdown("<h2>Login</h2>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            login_username = st.text_input("Username", key="login_username")
            login_password = st.text_input("Password", type="password", 
                                         key="login_password")
            
            if st.button("Login"):
                if authenticate_user(login_username, login_password):
                    st.session_state.logged_in = True
                    st.session_state.username = login_username
                    st.rerun()
                else:
                    st.error("Invalid username or password.")

    # Signup Tab
    with tab2:
        st.markdown("<h2>Sign Up</h2>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            signup_username = st.text_input("Username", key="signup_username")
            signup_password = st.text_input("Password", type="password", 
                                          key="signup_password")
            confirm_password = st.text_input("Confirm Password", type="password", 
                                           key="confirm_password")

            if st.button("Signup"):
                if signup_password != confirm_password:
                    st.error("Passwords do not match. Please try again.")
                elif len(signup_password) < 6:
                    st.error("Password must be at least 6 characters long.")
                else:
                    if add_user(signup_username, signup_password):
                        st.success("Signup successful! You can now login.")
                    else:
                        st.error("Username already exists. Try another.")

def main():
    if st.session_state.logged_in:
        st.markdown(f"<h1>Welcome, {st.session_state.username}!</h1>", 
                   unsafe_allow_html=True)
        if st.sidebar.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()
    else:
        render_auth_ui()

if __name__ == "__main__":
    main()