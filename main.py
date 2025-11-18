import streamlit as st
import requests
import pandas as pd
import json as js
import sys
import os

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