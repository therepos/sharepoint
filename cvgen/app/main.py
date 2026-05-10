"""cvgen — main entry point with auth gate."""
import os

import streamlit as st

from app.config import VERSION, ensure_dirs
from app.db import init_db


st.set_page_config(
    page_title="cvgen",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)


def login_gate() -> bool:
    """Return True if user is authenticated, otherwise show login form and return False."""
    if st.session_state.get("authed"):
        return True

    expected_user = os.environ.get("CVGEN_USERNAME", "admin")
    expected_pass = os.environ.get("CVGEN_PASSWORD", "")

    if not expected_pass:
        st.error("⚠️ CVGEN_PASSWORD not set. Configure it via environment variable.")
        st.stop()

    st.title("cvgen")
    st.caption("Sign in to continue")
    with st.form("login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Sign in", type="primary")
    if submit:
        if username == expected_user and password == expected_pass:
            st.session_state["authed"] = True
            st.rerun()
        else:
            st.error("Invalid credentials")
    return False


def main():
    ensure_dirs()
    init_db()

    if not login_gate():
        return

    st.sidebar.title("📋 cvgen")
    st.sidebar.caption("CV / Annex E generator")

    page = st.sidebar.radio(
        "Page",
        [
            "Staff",
            "Projects",
            "Assignments",
            "PII",
            "Family",
            "Templates",
            "Generate",
            "Bulk Import",
            "Settings",
        ],
        label_visibility="collapsed",
    )

    st.sidebar.divider()
    if st.sidebar.button("Sign out"):
        st.session_state.clear()
        st.rerun()
    st.sidebar.caption(f"v{VERSION}")

    # Lazy-import the page module so startup is fast
    if page == "Staff":
        from app.pages import staff
        staff.render()
    elif page == "Projects":
        from app.pages import projects
        projects.render()
    elif page == "Assignments":
        from app.pages import assignments
        assignments.render()
    elif page == "PII":
        from app.pages import pii
        pii.render()
    elif page == "Family":
        from app.pages import family
        family.render()
    elif page == "Templates":
        from app.pages import templates
        templates.render()
    elif page == "Generate":
        from app.pages import generate
        generate.render()
    elif page == "Bulk Import":
        from app.pages import bulk_import
        bulk_import.render()
    elif page == "Settings":
        from app.pages import settings
        settings.render()


if __name__ == "__main__":
    main()
