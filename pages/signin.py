import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys
import os

# Tambahkan path untuk import utils
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from utils.user_manager import UserManager

def signup_page():
    st.set_page_config(
        page_title="PlayHub - Sign Up",
        page_icon="👤",
        layout="centered"
    )
    
    st.title("👤 Create Your PlayHub Account")
    
    # Inisialisasi UserManager
    user_manager = UserManager()
    
    with st.form("signup_form"):
        st.write("### Fill in your details")
        
        # Input fields
        new_username = st.text_input(
            "👤 Username", 
            placeholder="Choose a unique username",
            help="Username must be 3-20 characters long"
        )
        
        new_email = st.text_input(
            "📧 Email", 
            placeholder="Enter your email address",
            help="We'll send a verification email"
        )
        
        new_password = st.text_input(
            "🔒 Password", 
            type="password",
            placeholder="Create a strong password",
            help="Password must be at least 6 characters"
        )
        
        confirm_password = st.text_input(
            "✅ Confirm Password", 
            type="password",
            placeholder="Re-enter your password"
        )
        
        # Terms and conditions
        agree_terms = st.checkbox(
            "I agree to the Terms of Service and Privacy Policy"
        )
        
        # Submit buttons
        col1, col2 = st.columns(2)
        
        with col1:
            signup_button = st.form_submit_button(
                "🚀 Create Account", 
                use_container_width=True,
                type="primary"
            )
        
        with col2:
            back_button = st.form_submit_button(
                "🔙 Back to Login", 
                use_container_width=True
            )
        
        # Handle form submission
        if signup_button:
            if not all([new_username, new_email, new_password, confirm_password]):
                st.error("❌ Please fill in all fields!")
            
            elif not agree_terms:
                st.error("❌ Please agree to the Terms of Service")
            
            elif len(new_username) < 3:
                st.error("❌ Username must be at least 3 characters long")
            
            elif len(new_password) < 6:
                st.error("❌ Password must be at least 6 characters long")
            
            elif new_password != confirm_password:
                st.error("❌ Passwords don't match!")
            
            elif "@" not in new_email or "." not in new_email:
                st.error("❌ Please enter a valid email address")
            
            else:
                # Register user
                success, message = user_manager.register_user(
                    new_username, new_email, new_password
                )
                
                if success:
                    st.success(f"✅ {message}")
                    st.balloons()
                    
                    # Tampilkan informasi user yang berhasil dibuat
                    user_info = user_manager.get_user_info(new_username)
                    if user_info:
                        with st.expander("📋 Account Details"):
                            st.write(f"**Username:** {user_info['username']}")
                            st.write(f"**Email:** {user_info['email']}")
                            st.write(f"**Created:** {user_info['created_at'][:10]}")
                    
                    # Auto redirect setelah 3 detik
                    st.info("🔄 Redirecting to login page in 3 seconds...")
                    import time
                    time.sleep(3)
                    st.switch_page("main.py")
                
                else:
                    st.error(f"❌ {message}")
        
        if back_button:
            st.switch_page("main.py")
    
    # Additional signup options
    st.markdown("---")
    st.write("Already have an account?")
    
    if st.button("🔐 Login Here", use_container_width=True):
        st.switch_page("main.py")

# Jalankan halaman signup
signup_page()