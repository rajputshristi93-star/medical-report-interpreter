import re
import time

import streamlit as st

from auth import friendly_error, login, signup
from i18n import localize, render_language_selector, t
from loader import loading
from profile_data import prefetch_after_login

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")


def _warm_up():
    """Loads profile + photo while the card says step 2, so the page after the rerun opens immediately."""
    user = st.session_state.get("user")
    if user is not None:
        try:
            prefetch_after_login(user)
        except Exception as e:  # never block a login because of this; the normal lazy loading still works
            print("[login] prefetch skipped:", str(e)[:120])


def show_auth():
    _, lang_col = st.columns([4, 1.3])
    with lang_col:
        render_language_selector()
    st.markdown(
        '<div style="text-align:center; padding:24px 0 16px;">'
        '<div class="brand" style="justify-content:center;font-size:2.2rem"><span class="logo" style="width:54px;height:54px;font-size:1.7rem">🩺</span>'
        '<span>MediLens <b>AI</b></span></div>'
        f'<p class="t-lead" style="margin:.8rem auto 0">{t("au.tag")}</p></div>',
        unsafe_allow_html=True,
    )
    _, mid, _ = st.columns([1, 2.2, 1])
    with mid:
        login_tab, signup_tab = st.tabs([t("au.login"), t("au.signup")])

        def say(e):
            msg = friendly_error(e)
            return localize([msg]).get(msg, msg)

        with login_tab:
            st.subheader(t("au.welcome"))
            li_email = st.text_input(t("au.email"), key="login_email")
            li_pw = st.text_input(t("au.password"), type="password", key="login_password")
            if st.button(t("au.login"), type="primary", width="stretch", key="do_login"):
                if not li_email or not li_pw:
                    st.warning(t("au.warn_enter"))
                else:
                    try:
                        steps = [(t("ld.login"), t("ld.login_s"), 45), (t("ld.login2"), t("ld.login2_s"), 90)]
                        with loading(steps, "lock") as step:
                            t0 = time.perf_counter()
                            ok = login(li_email.strip(), li_pw)
                            print(f"[login] sign-in took {time.perf_counter() - t0:.2f}s")
                            if ok:
                                step(2)
                                _warm_up()
                                st.rerun()
                        if not ok:
                            st.error(t("au.fail"))
                    except Exception as e:
                        st.error(say(e))

        with signup_tab:
            st.subheader(t("au.create_t"))
            su_name = st.text_input(t("au.name"), key="signup_name")
            su_email = st.text_input(t("au.email"), key="signup_email")
            su_pw = st.text_input(t("au.pw8"), type="password", key="signup_password")
            su_pw2 = st.text_input(t("au.confirm"), type="password", key="signup_confirm")
            if st.button(t("au.btn_create"), type="primary", width="stretch", key="do_signup"):
                email = su_email.strip()
                if not su_name.strip():
                    st.warning(t("au.w_name"))
                elif not EMAIL_RE.match(email):
                    st.warning(t("au.w_email"))
                elif len(su_pw) < 8:
                    st.warning(t("au.w_pw"))
                elif su_pw != su_pw2:
                    st.warning(t("au.w_match"))
                else:
                    try:
                        steps = [(t("ld.signup"), t("ld.signup_s"), 50), (t("ld.login2"), t("ld.login2_s"), 90)]
                        with loading(steps, "user") as step:
                            response = signup(email, su_pw, su_name.strip())
                            if response.session:
                                step(2)
                                login(email, su_pw)
                                _warm_up()
                                st.rerun()
                        st.info(t("au.info"))
                    except Exception as e:
                        st.error(say(e))
