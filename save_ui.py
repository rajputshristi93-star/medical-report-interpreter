import hashlib
import math
from datetime import date

import streamlit as st

from auth import get_current_user
from database import save_report


def _json_safe(x):
    if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
        return None
    if isinstance(x, dict):
        return {k: _json_safe(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_json_safe(v) for v in x]
    return x


def render_save_section():
    results = st.session_state.get("results")
    user = get_current_user()
    if not results or user is None:
        return

    fp = hashlib.sha1(str(results).encode("utf-8")).hexdigest()

    st.divider()
    st.subheader("💾 Save to my account")

    if st.session_state.get("saved_for") == fp:
        st.success("These results are saved. You can find them on the My Reports page.")
        return

    st.caption(
        "Saving stores the extracted results and the AI explanation in your account. "
        "Your original file is not stored. You can delete saved reports at any time on the My Reports page."
    )
    title = st.text_input("Title", value=f"Lab report {date.today():%d %b %Y}", key="save_title", max_chars=80)
    agree = st.checkbox("I understand and want to save these results", key="save_agree")

    if st.button("Save to my account", type="primary", key="save_btn", disabled=not agree):
        try:
            save_report(
                user_id=user.id,
                filename=title.strip() or "Untitled report",
                source=st.session_state.get("source", "text"),
                context=None,
                confirmed=True,
                results=_json_safe(results),
                explanation=st.session_state.get("explanation", ""),
            )
            st.session_state["saved_for"] = fp
            st.rerun()
        except Exception as e:
            print("save_report error:", str(e)[:300])
            st.error("Could not save. Please log out, log in again, and retry.")