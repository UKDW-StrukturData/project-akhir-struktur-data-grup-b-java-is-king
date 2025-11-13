import streamlit as st

st.set_page_config(
    page_title="PlayHub - Sign Up",
    page_icon="👤",
    layout="centered"
)

st.title("👤 Create Your PlayHub Account")

with st.form("signup_form"):
    st.write("Fill in the details to create your account")
    
    new_username = st.text_input("Username", placeholder="Choose a username")
    new_email = st.text_input("Email", placeholder="Enter your email")
    new_password = st.text_input("Password", type="password", placeholder="Create a password")
    confirm_password = st.text_input("Confirm Password", type="password", placeholder="Re-enter your password")
    
    col1, col2 = st.columns(2)
    
    with col1:
        signup_button = st.form_submit_button("Create Account", use_container_width=True)
    
    with col2:
        back_button = st.form_submit_button("Back to Login", use_container_width=True)
    
    if signup_button:
        if not new_username or not new_email or not new_password:
            st.error("❌ Please fill in all fields!")
        elif new_password != confirm_password:
            st.error("❌ Passwords don't match!")
        elif len(new_password) < 6:
            st.error("❌ Password must be at least 6 characters!")
        else:
            # Simpan data user (dalam session state untuk demo)
            st.session_state.new_user = {
                'username': new_username,
                'email': new_email,
                'password': new_password
            }
            st.success("✅ Account created successfully!")
            st.info("You can now login with your new account.")
            
            # Otomatis redirect ke login setelah 2 detik
            st.write("Redirecting to login page...")
            import time
            time.sleep(2)
            st.switch_page("login.py")
    
    if back_button:
        st.switch_page("login.py")

# Tambahan: Link back to login di luar form
st.markdown("---")
st.write("Already have an account?")
if st.button("Login Here"):
    st.switch_page("login.py")