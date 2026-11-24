import html
from datetime import date

import streamlit as st

import profile_data as pd_
from auth import get_current_user
from i18n import t
from loader import celebrate, simple
from pagecss import inject_page_css
from theme import render_footer

inject_page_css()
esc = html.escape
user = get_current_user()
if user is None:
    st.stop()

details = pd_.get_details(user, force=st.session_state.pop("pf_reload", False))
missing = bool(details.get("_missing"))
uri = pd_.avatar_uri(user, details)
shown_name = details.get("full_name") or user.email.split("@")[0]

st.markdown(f'<div class="dr-top"><div class="pic">👤</div><div><h1>{esc(t("pf.title"))}</h1><p>{esc(t("pf.sub"))}</p></div></div>', unsafe_allow_html=True)
if missing:
    st.warning(t("pf.setup"))

left, right = st.columns([1, 2.2])
with left, st.container(key="rcard"):
    face = (f'<img src="{uri}" alt="" style="width:150px;height:150px;border-radius:50%;object-fit:cover;box-shadow:0 14px 30px rgba(18,49,58,.25);border:5px solid #fff">'
            if uri else f'<div style="width:150px;height:150px;border-radius:50%;display:grid;place-items:center;font:800 3rem Poppins,sans-serif;color:#fff;'
                        f'background:linear-gradient(135deg,#14C4A5,#2B7FF0);box-shadow:0 14px 30px rgba(18,49,58,.25);border:5px solid #fff">{esc(pd_.initials(shown_name))}</div>')
    st.markdown(f'<div style="text-align:center">{face}<div class="dn" style="margin-top:.8rem;font-size:1.2rem">{esc(shown_name)}</div>'
                f'<div class="t-small">{esc(user.email)}</div>'
                f'<span class="exp" style="margin-top:.5rem">{esc(t("nav.role_admin") if st.session_state.get("profile", {}).get("role") == "admin" else t("nav.role_user"))}</span>'
                f'<div class="t-small" style="margin-top:.6rem">{esc(t("pf.member", date=str(details.get("created_at") or "")[:10] or "-"))}</div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sec-t" style="margin-top:1rem;font-size:1rem">{esc(t("pf.photo"))}</div>', unsafe_allow_html=True)
    n = st.session_state.setdefault("pf_up_n", 0)
    up = st.file_uploader(t("pf.upload"), type=["jpg", "jpeg", "png"], key=f"pf_up_{n}", help=t("pf.photo_help"), disabled=missing)
    if up is not None:
        if up.size > pd_.MAX_UPLOAD:
            st.error(t("pf.photo_err"))
        elif st.button(t("pf.upload"), type="primary", key="pf_photo_go", width="stretch"):
            try:
                with simple("ld.photo", "ld.photo_s", "user"):
                    pd_.save_avatar(user, pd_.prepare_avatar(up.getvalue()))
                st.session_state["pf_up_n"] = n + 1
                celebrate(t("pf.photo_ok"), "")
                st.rerun()
            except Exception as e:
                if type(e).__name__ in ("RerunException", "StopException"):
                    raise
                print("photo error:", str(e)[:200])
                st.error(t("pf.photo_err"))
    if uri and st.button(t("pf.remove"), key="pf_photo_rm", width="stretch"):
        with simple("ld.photo", "ld.photo_s", "trash"):
            pd_.remove_avatar(user)
        st.rerun()

with right, st.container(key="pcard"):
    st.text_input(t("pf.email"), value=user.email, disabled=True, key="pf_email")
    st.caption(t("pf.email_note"))
    c1, c2 = st.columns(2)
    name = c1.text_input(t("pf.name"), value=details.get("full_name") or "", max_chars=80, key="pf_name", disabled=missing)
    phone = c2.text_input(t("pf.phone"), value=details.get("phone") or "", max_chars=20, key="pf_phone", disabled=missing)
    c3, c4, c5 = st.columns([1.2, 1, 1])
    city = c3.text_input(t("pf.city"), value=details.get("city") or "", max_chars=60, key="pf_city", disabled=missing)
    options = ["", "Female", "Male", "Other"]
    labels = {"": t("pf.gender_none"), "Female": t("ip.sex_f"), "Male": t("ip.sex_m"), "Other": t("ip.sex_o")}
    gender = c4.selectbox(t("pf.gender"), options, index=options.index(details.get("gender") or ""), format_func=labels.get, key="pf_gender", disabled=missing)
    cur_dob = details.get("date_of_birth")
    dob = c5.date_input(t("pf.dob"), value=date.fromisoformat(str(cur_dob)[:10]) if cur_dob else None, min_value=date(1900, 1, 1),
                        max_value=date.today(), key="pf_dob", disabled=missing)
    about = st.text_area(t("pf.about"), value=details.get("about") or "", max_chars=300, placeholder=t("pf.about_ph"), key="pf_about", disabled=missing)
    st.markdown(f'<div class="pnote">🔒 <span>{esc(t("pf.privacy"))}</span></div>', unsafe_allow_html=True)
    if st.button(t("pf.save"), type="primary", key="pf_save", width="stretch", disabled=missing):
        try:
            with simple("ld.profile", "ld.profile_s", "user"):
                pd_.save_details(user, name, phone, city, gender, dob, about)
            st.session_state["pf_reload"] = True
            celebrate(t("pf.saved"), t("pf.saved_s"))
            st.rerun()
        except Exception as e:
            if type(e).__name__ in ("RerunException", "StopException"):
                raise
            print("profile save error:", str(e)[:200])
            st.error(t("pf.err"))
render_footer()
