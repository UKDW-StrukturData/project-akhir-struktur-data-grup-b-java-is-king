import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import json as js
import sys
import os

# # Tambahkan path untuk import utils
# sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# from utils.user_manager import UserManager

# def signup_page():
#     st.set_page_config(
#         page_title="PlayHub - Sign Up",
#         page_icon="👤",
#         layout="centered"
#     )
    
#     st.title("👤 welcome to PlayHub")
    
#     # Inisialisasi UserManager
#     user_manager = UserManager()
    
#     with st.form("signup_form"):
#         st.write("### Fill in your details")
        
#         # Input fields
#         new_username = st.text_input(
#             "👤 Username", 
#             placeholder="Choose a unique username",
#             help="Username must be 3-20 characters long"
#         )
        
#         new_email = st.text_input(
#             "📧 Email", 
#             placeholder="Enter your email address",
#             help="We'll send a verification email"
#         )
        
#         new_password = st.text_input(
#             "🔒 Password", 
#             type="password",
#             placeholder="password",
#             help="Password must be at least 6 characters"
#         )
        
#         # Terms and conditions
#         agree_terms = st.checkbox(
#             "I agree to the Terms of Service and Privacy Policy"
#         )
        
#         # Submit buttons
#         col1, col2 = st.columns(2)
        
#         with col1:
#             signup_button = st.form_submit_button(
#                 "🚀 login", 
#                 use_container_width=True,
#                 type="primary"
#             )
        
#         with col2:
#             back_button = st.form_submit_button(
#                 "🔙 Back to Login", 
#                 use_container_width=True
#             )
        
#         # Handle form submission
#         if signup_button:
#             if not all([new_username, new_email, new_password,]):
#                 st.error("❌ Please fill in all fields!")
            
#             elif not agree_terms:
#                 st.error("❌ Please agree to the Terms of Service")
            
#             elif len(new_username) < 3:
#                 st.error("❌ Username must be at least 3 characters long")
            
#             elif len(new_password) < 6:
#                 st.error("❌ Password must be at least 6 characters long")
            
#             elif "@" not in new_email or "." not in new_email:
#                 st.error("❌ Please enter a valid email address")
            
#             else:
#                 # Register user
#                 success, message = user_manager.register_user(
#                     new_username, new_email, new_password
#                 )
                
#                 if success:
#                     st.success(f"✅ {message}")
#                     st.balloons()
                    
#                     # Tampilkan informasi user yang berhasil dibuat
#                     user_info = user_manager.get_user_info(new_username)
#                     if user_info:
#                         with st.expander("📋 Account Details"):
#                             st.write(f"**Username:** {user_info['username']}")
#                             st.write(f"**Email:** {user_info['email']}")
#                             st.write(f"**Created:** {user_info['created_at'][:10]}")
                    
#                     # Auto redirect setelah 3 detik
#                     st.info("🔄 Redirecting to login page in 3 seconds...")
#                     import time
#                     time.sleep(3)
#                     st.switch_page("main.py")
                
#                 else:
#                     st.error(f"❌ {message}")
        
#         if back_button:
#             st.switch_page("main.py")
    
#     # Additional signup options
#     st.markdown("---")
#     st.write("Already have an account?")
    
#     if st.button("🔐 Login Here", use_container_width=True):
#         st.switch_page("main.py")

# # Jalankan halaman signup
# signup_page()
# # # Initialize session state
# # if 'username' not in st.session_state:
# #     st.session_state.username = ' '
# # if 'password' not in st.session_state:
# #     st.session_state.password = ' '
# # if 'logged_in' not in st.session_state:
# #     st.session_state.logged_in = False

# # # Layout halaman login
# # col1, col2 = st.columns([2, 1])

# # with col1:
# #     st.title("🎮 PlayHub")
# #     st.markdown("### Your Ultimate Gaming Destination")
# #     st.write("Welcome to the future of gaming entertainment!")
    
# #     # Login Form
# #     st.markdown("---")
# #     st.subheader("🔐 Login to Your Account")
    
# #     username_input = st.text_input("👤 Username", placeholder="Enter your username")
# #     password_input = st.text_input("🔒 Password", type="password", placeholder="Enter your password")
    
# #     login_col1, login_col2 = st.columns(2)
    
# #     with login_col1:
# #         if st.button("🚀 Login", use_container_width=True, type="primary"):
# #             if username_input and password_input:
# #                 if username_input == st.session_state.username and password_input == st.session_state.password:
# #                     st.session_state.logged_in = True
# #                     st.session_state.username = username_input
# #                     st.success("Login successful! Redirecting...")
# #                     st.switch_page("pages/home.py")
# #                 else:
# #                     st.error("❌ Invalid username or password")
# #             else:
# #                 st.warning("⚠️ Please enter both username and password")
    
# #     with login_col2:
# #         if st.button("📝 Sign Up", use_container_width=True):
# #             st.switch_page("pages/signin.py")
# Tambahkan path untuk import utils
sys.path.append(os.path.dirname(__file__))

from utils.user_manager import UserManager

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = ""

def login_page():
    st.set_page_config(
        page_title="PlayHub - Login",
        page_icon="🎮",
        layout="centered"
    )
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.title("🎮 PlayHub")
        st.markdown("### Your Ultimate Gaming Destination")
        st.write("Welcome to the future of gaming entertainment!")
        
        # Login Form
        st.markdown("---")
        st.subheader("🔐 Login to Your Account")
        
        username_input = st.text_input("👤 Username", placeholder="Enter your username")
        password_input = st.text_input("🔒 Password", type="password", placeholder="Enter your password")
        
        login_col1, login_col2 = st.columns(2)
        
        with login_col1:
            if st.button("🚀 Login", use_container_width=True, type="primary"):
                if username_input and password_input:
                    user_manager = UserManager()
                    
                    if user_manager.verify_user(username_input, password_input):
                        st.session_state.logged_in = True
                        st.session_state.username = username_input
                        st.success("✅ Login successful! Redirecting...")
                        
                        # Update last login time
                        user_info = user_manager.get_user_info(username_input)
                        if user_info:
                            st.session_state.user_info = user_info
                        
                        st.switch_page("pages/home.py")
                    else:
                        st.error("❌ Invalid username or password")
                else:
                    st.warning("⚠️ Please enter both username and password")
        
        with login_col2:
            if st.button("📝 Sign Up", use_container_width=True):
                st.switch_page("pages/signin.py")

# Check if user is logged in
if not st.session_state.logged_in:
    login_page()
else:
    st.switch_page("pages/home.py")