import streamlit as st
from ui import inject_css

st.set_page_config(page_title="AI Medical Report Interpreter", page_icon="🩺", layout="wide")
inject_css()

pages = [
    st.Page("views/home.py", title="Home", icon="🏠", default=True),
    st.Page("views/analyze.py", title="Interpreter", icon="🧪"),
]

pg = st.navigation(pages, position="top")
pg.run()