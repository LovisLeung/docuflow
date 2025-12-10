import streamlit as st


def init_session_state():
    """Initialize session state variables for authentication."""
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "username" not in st.session_state:
        st.session_state.username = ""


def login(username, password):
    """Simulated login function."""
    # can be substituted with searching in a database or an external authentication service
    if password == "password":
        st.session_state.logged_in = True
        st.session_state.username = username
        return True
    return False


def logout():
    """logged out and refresh the app."""
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.rerun()


def require_login():
    """Decorator to require login for a function.
    If called in other pages, will redirect to login page.
    """
    # Ensure session state is initialized
    init_session_state()

    if not st.session_state.get("logged_in", False):
        st.warning("Please log in to access this page.")

        # login form
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")

        if st.button("Login", key="login_button"):
            if login(username, password):
                st.success("Login successful!")
                st.rerun()  # refresh the app to show the protected page
            else:
                st.error("Invalid username or password.")

        st.stop()
