import os

import streamlit as st
from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()


def get_supabase() -> Client:
    """One client PER browser session. A client remembers the logged-in user's token,
    so it must never be shared between visitors."""
    if "sb_client" not in st.session_state:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if not url or not key:
            raise RuntimeError("SUPABASE_URL or SUPABASE_KEY is missing from .env")
        st.session_state["sb_client"] = create_client(url, key)
    return st.session_state["sb_client"]


class _SessionClient:
    """Keeps old code like `from supabase_client import supabase` working.
    Every attribute access is forwarded to the current visitor's own client."""

    def __getattr__(self, name):
        return getattr(get_supabase(), name)


supabase = _SessionClient()