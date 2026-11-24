import streamlit as st

from admin_data import get_profile
from auth import get_current_user, logout
from i18n import ensure_language, inject_rtl, t
from i18n import render_language_selector
from profile_data import avatar_uri, get_details
from theme import inject_theme, render_nav
from ui import inject_css
from views.auth import show_auth

st.set_page_config(page_title="MediLens AI", page_icon="🩺", layout="wide", initial_sidebar_state="collapsed")
inject_css()
inject_theme()
inject_rtl()
ensure_language()  # makes sure the chosen language is translated (done once, then saved)

user = get_current_user()
if user is None:
    show_auth()
    st.stop()

profile = get_profile(user)
if profile.get("status") == "suspended":
    st.error(t("au.suspended"))
    if st.button(t("nav.logout")):
        logout()
        st.rerun()
    st.stop()

PAGES = [
    ("views/home.py", t("nav.home"), "🏠"),
    ("views/analyze.py", t("nav.interpreter"), "🧪"),
    ("views/reports.py", t("nav.reports"), "📁"),
    ("views/doctors.py", t("nav.doctor"), "📍"),
]
if profile.get("role") == "admin":
    PAGES.append(("views/admin.py", t("nav.admin"), "🛡️"))
pages = [st.Page(p, title=label, icon=icon, default=(p == "views/home.py")) for p, label, icon in PAGES]
pages.append(st.Page("views/profile.py", title=t("pf.title"), icon="👤"))  # reached from the profile menu, not shown as a tab
pg = st.navigation(pages, position="hidden")
details = get_details(user)
who = {"name": details.get("full_name") or profile.get("full_name") or user.email.split("@")[0],
       "avatar": avatar_uri(user, details), "role": profile.get("role")}
render_nav(user, logout, PAGES, extras=render_language_selector, active_label=pg.title, profile=who)
pg.run()
