import streamlit as st

from auth import get_current_user, logout
from theme import inject_theme, render_nav
from ui import inject_css
from views.auth import show_auth

st.set_page_config(page_title="MediLens AI", page_icon="🩺", layout="wide", initial_sidebar_state="collapsed")
inject_css()
inject_theme()

user = get_current_user()
if user is None:
    show_auth()
    st.stop()

PAGES = [
    ("views/home.py", "Home", "🏠"),
    ("views/analyze.py", "Interpreter", "🧪"),
    ("views/reports.py", "My Reports", "📁"),
    ("views/doctors.py", "Find a Doctor", "📍"),
]
pages = [st.Page(p, title=label, icon=icon, default=(p == "views/home.py")) for p, label, icon in PAGES]
pg = st.navigation(pages, position="hidden")
render_nav(user, logout, PAGES, active_label=pg.title)
pg.run()
