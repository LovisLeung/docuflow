import streamlit as st
from utils import auth

# 1. Page Configuration(must be at the top)
st.set_page_config(page_title="Docuflow")

# 2. Initialize session state for authentication
auth.init_session_state()

# 3. Main Application Logic
if not st.session_state.logged_in:
    # Loggin Page
    st.title("Docuflow Login")

    col1, col2, col3 = st.columns([1, 2, 1])  # center the login form
    with col2:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("Login", use_container_width=True):
            if auth.login(username, password):
                st.success("Login successful!")
                st.rerun()  # refresh the app to show home page
            else:
                st.error("Invalid username or password.")
else:
    # logged in, show home page
    st.title(f"Welcome to Docuflow, {st.session_state.username}!")

    st.info("Please select a page from the sidebar to get started.")

    st.divider()  # horizontal line

    if st.button("logout"):
        auth.logout()
