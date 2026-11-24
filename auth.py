import streamlit as st

from supabase_client import get_supabase


def friendly_error(e):
    print("Supabase auth error:", str(e)[:300])
    msg = str(e).lower()
    if "invalid login" in msg or "invalid credentials" in msg:
        return "Wrong email or password."
    if "already registered" in msg or "already been registered" in msg:
        return "This email is already registered. Please use the Login tab."
    if "not confirmed" in msg:
        return "Please confirm your email first (check your inbox), then log in."
    if "rate limit" in msg or "too many" in msg:
        return "Too many attempts. Please wait a while and try again."
    if "email" in msg and "invalid" in msg:
        return "Please enter a valid email address."
    if "password" in msg:
        return "That password is not accepted. Try a longer one."
    return "Something went wrong. Please try again."


def signup(email: str, password: str, full_name: str):
    return get_supabase().auth.sign_up(
        {
            "email": email,
            "password": password,
            "options": {"data": {"full_name": full_name}},
        }
    )


def login(email: str, password: str):
    client = get_supabase()
    response = client.auth.sign_in_with_password({"email": email, "password": password})
    if response.user and response.session:
        try:
            client.postgrest.auth(response.session.access_token)
        except Exception:
            pass  # newer versions attach the token automatically
        st.session_state["user"] = response.user
        st.session_state["session"] = response.session
        return True
    return False


def logout():
    try:
        get_supabase().auth.sign_out()
    except Exception:
        pass
    for key in ("user", "session", "sb_client", "results", "explanation", "source", "unread", "saved_for"):
        st.session_state.pop(key, None)


def get_current_user():
    return st.session_state.get("user")