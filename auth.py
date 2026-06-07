"""Simple session-state-based authentication."""

import streamlit as st
import db


def require_auth() -> dict:
    """Show login form if not authenticated. Returns user dict or stops execution."""
    if "user" not in st.session_state:
        st.title("🔐 Timetable Scheduler — Login")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")
        if submitted:
            if db.verify_password(username, password):
                user = db.get_user(username)
                st.session_state.user = user
                st.rerun()
            else:
                st.error("Invalid username or password.")
        st.stop()
    return st.session_state.user


def logout():
    """Clear auth state and rerun."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


def is_admin() -> bool:
    user = st.session_state.get("user")
    return user is not None and user.get("role") == "admin"
