import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import json as js
# Initialize session state
if 'username' not in st.session_state:
    st.session_state.username = ' '
if 'password' not in st.session_state:
    st.session_state.password = ' '
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# Layout halaman login
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
                if username_input == st.session_state.username and password_input == st.session_state.password:
                    st.session_state.logged_in = True
                    st.session_state.username = username_input
                    st.success("Login successful! Redirecting...")
                    st.switch_page("pages/home.py")
                else:
                    st.error("❌ Invalid username or password")
            else:
                st.warning("⚠️ Please enter both username and password")
    
    with login_col2:
        if st.button("📝 Sign Up", use_container_width=True):
            st.switch_page("pages/signin.py")
