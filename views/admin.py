import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import admin_data as ad
from loader import simple
from auth import get_current_user
from charts import FONT, _layout, _show

TEAL, BLUE, VIOLET, AMBER, RED, GREEN, GREY = "#0F9D8A", "#1B6FB5", "#6C5CE7", "#F5A623", "#E5484D", "#2FBF71", "#9AA7B2"

user = get_current_user()
if user is None or not ad.is_admin(user):
    st.error("This page is only for administrators.")
    st.stop()

st.markdown("""
<style>
.kpi{background:#fff; border:1px solid var(--line); border-radius:20px; padding:1rem 1.2rem; box-shadow:var(--shadow-3d);
  transition:transform .3s cubic-bezier(.2,.8,.2,1), box-shadow .3s; animation:fadeUp .6s backwards; position:relative; overflow:hidden;}
.kpi:hover{transform:translateY(-6px) rotateX(3deg); box-shadow:var(--shadow-hover);}
.kpi .n{font-family:'Poppins',sans-serif; font-size:2.1rem; font-weight:800; color:var(--navy); line-height:1.1; margin-top:.6rem;}
.kpi .l{font-size:.86rem; color:var(--muted); font-weight:600;}
.kpi .s{font-size:.78rem; color:var(--teal-d); margin-top:.15rem;}
.icon3d.sm{width:42px; height:42px; border-radius:13px; font-size:1.25rem; box-shadow:0 4px 0 var(--teal-d), 0 10px 16px rgba(15,157,138,.3);}
.icon3d.sm.amber{box-shadow:0 4px 0 #B85F0E, 0 10px 16px rgba(245,132,31,.3);} .icon3d.sm.violet{box-shadow:0 4px 0 #3E2A9E, 0 10px 16px rgba(91,63,214,.3);}
.icon3d.sm.rose{box-shadow:0 4px 0 #A92B30, 0 10px 16px rgba(229,72,77,.3);}
.privacy{background:linear-gradient(135deg,rgba(15,157,138,.10),rgba(27,111,181,.10)); border:1px solid var(--line); border-radius:16px; padding:.7rem 1rem; font-size:.9rem; color:var(--ink);}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="t-eyebrow">ADMIN</div><div class="t-h1">Control centre</div>', unsafe_allow_html=True)
st.markdown('<div class="privacy">🔒 You can see accounts and totals here. <b>Report contents are never shown to admins.</b> '
            'Every change you make is written to the activity log.</div>', unsafe_allow_html=True)
if "adm_flash" in st.session_state:
    st.success(st.session_state.pop("adm_flash"))
st.write("")


def friendly(e):
    msg = str(e)
    if "not allowed" in msg:
        return "You are not allowed to do that."
    if "own" in msg and "cannot" in msg:
        return "You cannot change your own account here."
    print("admin error:", msg[:200])
    return "Something went wrong. Please try again."


def act(fn, message):
    try:
        with simple("ld.adm_act", "ld.adm_act_s", "user"):
            fn()
    except Exception as e:
        st.error(friendly(e))
        return
    st.session_state["adm_flash"] = message
    st.rerun()


def kpi(col, icon, tone, number, label, note=""):
    col.markdown(f'<div class="kpi"><div class="icon3d sm {tone}">{icon}</div><div class="n">{int(number or 0):,}</div>'
                 f'<div class="l">{label}</div><div class="s">{note}&nbsp;</div></div>', unsafe_allow_html=True)


def donut(labels, values, colors, centre):
    fig = go.Figure(go.Pie(labels=labels, values=values, hole=0.62, sort=False, textinfo="value",
                           textfont=dict(size=14, color="white"),
                           marker=dict(colors=colors, line=dict(color="white", width=4)),
                           hovertemplate="%{label}: %{value} (%{percent})<extra></extra>"))
    fig.add_annotation(text=centre, showarrow=False, font=dict(size=14, color="#1F3A44"))
    fig.update_layout(legend=dict(orientation="h", y=-0.08, x=0.5, xanchor="center"))
    return _layout(fig, 300)


def whole(fig, *axes):
    """Whole-number ticks that start at zero (counts are never fractions)."""
    for ax in axes:
        getattr(fig, f"update_{ax}axes")(rangemode="tozero", tickformat="d", gridcolor="rgba(18,49,58,.08)")
    return fig


def head(text, sub=""):
    st.markdown(f'<div class="t-h2" style="margin:1.2rem 0 .1rem;font-size:1.25rem">{text}</div>'
                + (f'<p class="t-small">{sub}</p>' if sub else ""), unsafe_allow_html=True)


section = st.segmented_control("Section", ["Overview", "Users", "Doctors", "Activity log"], default="Overview",
                               key="adm_section", label_visibility="collapsed") or "Overview"

# =============================================================== OVERVIEW
if section == "Overview":
    days = st.segmented_control("Period", [7, 30, 90], default=30, key="adm_days",
                                format_func=lambda d: f"Last {d} days") or 30
    try:
        ov = ad.overview()
        users_df = ad.users()
        sg, rp, src = ad.signups(days), ad.reports_per_day(days), ad.sources()
    except Exception as e:
        st.error(friendly(e))
        st.stop()

    c = st.columns(5)
    kpi(c[0], "👥", "", ov.get("total_users"), "Users", f"{ov.get('signups_7d', 0)} new this week")
    kpi(c[1], "✅", "violet", ov.get("active_users"), "Active accounts", f"{ov.get('admin_users', 0)} admin(s)")
    kpi(c[2], "⛔", "rose", ov.get("suspended_users"), "Suspended", "can sign in, cannot save")
    kpi(c[3], "📁", "amber", ov.get("total_reports"), "Reports saved", f"{ov.get('reports_7d', 0)} in the last 7 days")
    kpi(c[4], "📍", "", ov.get("doctors_listed"), "Doctors listed", "in the directory")

    head("Sign-ups", "New accounts per day, with the running total for this period.")
    if sg.empty or sg["signups"].sum() == 0:
        st.info("No sign-ups in this period.")
    else:
        fig = go.Figure()
        fig.add_bar(x=sg["day"], y=sg["signups"], name="New users", marker_color=TEAL,
                    hovertemplate="%{x|%d %b}: %{y} new<extra></extra>")
        fig.add_scatter(x=sg["day"], y=sg["signups"].cumsum(), name="Running total", yaxis="y2", mode="lines+markers",
                        line=dict(color=BLUE, width=3), marker=dict(size=5),
                        hovertemplate="%{x|%d %b}: %{y} in this period<extra></extra>")
        top = max(int(sg["signups"].max()), 1)
        fig.update_layout(yaxis=dict(title="New per day", gridcolor="rgba(18,49,58,.08)", rangemode="tozero", tickformat="d",
                                     dtick=1 if top <= 6 else None, range=[0, top * 1.15]),
                          yaxis2=dict(title="Running total", overlaying="y", side="right", showgrid=False, rangemode="tozero", tickformat="d"),
                          legend=dict(orientation="h", y=1.12, x=0), bargap=0.25)
        _show(st, _layout(fig, 340))

    left, right = st.columns([1.4, 1])
    with left:
        head("Reports saved per day")
        if rp.empty or rp["reports"].sum() == 0:
            st.info("No reports saved in this period.")
        else:
            fig = go.Figure(go.Scatter(x=rp["day"], y=rp["reports"], mode="lines", fill="tozeroy",
                                       line=dict(color=VIOLET, width=3, shape="linear"), fillcolor="rgba(108,92,231,.18)",
                                       hovertemplate="%{x|%d %b}: %{y} reports<extra></extra>"))
            whole(fig, "y")
            _show(st, _layout(fig, 300))
    with right:
        head("How reports were added")
        if src.empty:
            st.info("No reports yet.")
        else:
            names = {"manual": "Typed", "text": "PDF", "image": "Image or scan"}
            _show(st, donut([names.get(s, s.title()) for s in src["source"]], src["reports"],
                            [TEAL, BLUE, AMBER, VIOLET, GREY][:len(src)], f"<b style='font-size:26px'>{int(src['reports'].sum())}</b><br>reports"))

    a, b = st.columns(2)
    with a:
        head("Account status", "Active and suspended accounts.")
        if not users_df.empty:
            counts = users_df["status"].value_counts()
            _show(st, donut([s.title() for s in counts.index], counts.values,
                            [GREEN if s == "active" else RED for s in counts.index], f"<b style='font-size:26px'>{len(users_df)}</b><br>users"))
    with b:
        head("Reports per user", "How many saved reports each account has.")
        if not users_df.empty:
            buckets = pd.cut(users_df["reports_count"], [-1, 0, 1, 3, 5, 10**6], labels=["0", "1", "2 to 3", "4 to 5", "6 or more"])
            order = ["0", "1", "2 to 3", "4 to 5", "6 or more"]
            vc = buckets.astype(str).value_counts().reindex(order).fillna(0).astype(int)
            fig = go.Figure(go.Bar(x=order, y=vc.tolist(), marker_color=[GREY, TEAL, BLUE, VIOLET, AMBER],
                                   text=vc.tolist(), textposition="outside", cliponaxis=False,
                                   hovertemplate="%{x} reports: %{y} users<extra></extra>"))
            fig.update_xaxes(type="category")
            whole(fig, "y")
            fig.update_yaxes(title="Users")
            _show(st, _layout(fig, 300))

# =============================================================== USERS
elif section == "Users":
    try:
        df = ad.users()
    except Exception as e:
        st.error(friendly(e))
        st.stop()
    if df.empty:
        st.info("No users yet.")
        st.stop()
    c1, c2, c3 = st.columns([2, 1, 1])
    q = c1.text_input("Search by email or name", key="adm_q")
    f_status = c2.multiselect("Status", ["active", "suspended"], default=["active", "suspended"], key="adm_fs")
    f_role = c3.multiselect("Role", ["user", "admin"], default=["user", "admin"], key="adm_fr")
    view = df[df["status"].isin(f_status) & df["role"].isin(f_role)]
    if q:
        view = view[view["email"].str.contains(q, case=False, na=False) | view["full_name"].str.contains(q, case=False, na=False)]
    st.caption(f"{len(view)} of {len(df)} users")
    show = view[["email", "full_name", "role", "status", "created_at", "reports_count"]]
    st.dataframe(show, hide_index=True, width="stretch", column_config={
        "email": "Email", "full_name": "Name", "role": "Role", "status": "Status",
        "created_at": st.column_config.DatetimeColumn("Joined", format="DD MMM YYYY"),
        "reports_count": st.column_config.ProgressColumn("Saved reports", min_value=0, max_value=max(int(df["reports_count"].max()), 1), format="%d")})

    head("Manage a user")
    if view.empty:
        st.info("No user matches the filters.")
        st.stop()
    labels = {r.user_id: f"{r.email}  ·  {r.full_name or 'no name'}" for r in view.itertuples()}
    sel = st.selectbox("Choose a user", list(labels), format_func=labels.get, key="adm_sel")
    row = df[df["user_id"] == sel].iloc[0]
    me = sel == user.id
    st.markdown(f"`{row['email']}` · role **{row['role']}** · status **{row['status']}** · {int(row['reports_count'])} saved reports"
                + ("  \n_This is your own account, so these actions are switched off._" if me else ""))
    b1, b2, b3 = st.columns(3)
    with b1, st.container(border=True):
        suspended = row["status"] == "suspended"
        st.caption("A suspended user cannot save reports and is signed out within a minute.")
        if st.button("Reactivate account" if suspended else "Suspend account", disabled=me, key="adm_b1",
                     type="primary" if suspended else "secondary"):
            act(lambda: ad.set_status(sel, "active" if suspended else "suspended"),
                f"{row['email']} is now {'active' if suspended else 'suspended'}.")
    with b2, st.container(border=True):
        is_adm = row["role"] == "admin"
        st.caption("Admins can see this dashboard. They still cannot read report contents.")
        if st.button("Remove admin rights" if is_adm else "Make admin", disabled=me, key="adm_b2"):
            act(lambda: ad.set_role(sel, "user" if is_adm else "admin"),
                f"{row['email']} is now {'a normal user' if is_adm else 'an admin'}.")
    with b3, st.container(border=True):
        st.caption("Use this only when the user asks for their data to be erased.")
        ok = st.checkbox("I understand this cannot be undone", key=f"adm_ok_{sel}")
        if st.button("Delete saved reports", disabled=me or not ok or int(row["reports_count"]) == 0, key="adm_b3"):
            act(lambda: ad.delete_reports(sel), f"Saved reports of {row['email']} were deleted.")

# =============================================================== DOCTORS
elif section == "Doctors":
    try:
        docs = ad.doctors()
    except Exception as e:
        st.error("Could not load the doctor directory. Check that the doctors table exists.")
        st.stop()
    st.caption("Only publicly listed professional details, each with a source and the date you checked it. "
               "No ranking and no payment for listings. Remove anyone who asks.")
    if not docs.empty:
        a, b = st.columns(2)
        with a:
            head("Doctors by specialty")
            vc = docs["specialty"].value_counts().head(10)[::-1]
            fig = go.Figure(go.Bar(y=vc.index, x=vc.values, orientation="h", marker_color=TEAL, text=vc.values, textposition="outside", cliponaxis=False))
            _show(st, whole(_layout(fig, 120 + 32 * len(vc)), "x"))
        with b:
            head("Doctors by city")
            vc = docs["city"].value_counts().head(10)[::-1]
            fig = go.Figure(go.Bar(y=vc.index, x=vc.values, orientation="h", marker_color=BLUE, text=vc.values, textposition="outside", cliponaxis=False))
            _show(st, whole(_layout(fig, 120 + 32 * len(vc)), "x"))

    head("Edit the directory", "Change a cell, add a row at the bottom, or select a row and press Delete. Then press Save.")
    edited = st.data_editor(
        docs, num_rows="dynamic", hide_index=True, width="stretch", key="adm_doc_editor",
        column_config={
            "id": None, "qualification": "Qualification", "clinic": "Clinic", "address": "Address", "phone": "Phone",
            "specialty": st.column_config.SelectboxColumn("Specialty", options=ad.SPECIALTIES, required=True),
            "listing_basis": st.column_config.SelectboxColumn("Listing basis", options=ad.BASIS, required=True),
            "verified_on": st.column_config.DateColumn("Checked on", format="YYYY-MM-DD", required=True),
            "source_url": st.column_config.LinkColumn("Source page", required=True),
            "website": st.column_config.LinkColumn("Website"), "social_url": st.column_config.LinkColumn("Profile"),
            "name": st.column_config.TextColumn("Name", required=True), "city": st.column_config.TextColumn("City", required=True),
        })
    if st.button("Save changes", type="primary", key="adm_doc_save"):
        with simple("ld.adm_save", "ld.adm_save_s", "save"):
            added, updated, deleted, problems = ad.save_doctors(docs, edited)
        for p in problems:
            st.warning(p)
        if added or updated or deleted:
            st.session_state["adm_flash"] = f"Saved: {added} added, {updated} updated, {deleted} deleted."
            if not problems:
                st.rerun()
            st.success(st.session_state.pop("adm_flash"))
        elif not problems:
            st.info("There were no changes to save.")

    with st.expander("Import many doctors from a CSV file"):
        st.caption("Use the doctors_template.csv columns. Rows whose name starts with EXAMPLE are skipped.")
        up = st.file_uploader("CSV file", type=["csv"], key="adm_csv")
        if up is not None:
            try:
                csv = pd.read_csv(up, dtype=str)
            except Exception:
                csv = None
                st.error("This file could not be read as a CSV.")
            if csv is not None:
                st.dataframe(csv.head(10), hide_index=True, width="stretch")
                if st.button(f"Import {len(csv)} rows", key="adm_csv_go"):
                    with simple("ld.adm_save", "ld.adm_save_s", "save"):
                        added, problems = ad.import_doctors(csv)
                    for p in problems:
                        st.warning(p)
                    if added:
                        st.session_state["adm_flash"] = f"{added} doctors imported."
                        st.rerun()

# =============================================================== ACTIVITY LOG
else:
    try:
        lg = ad.audit(200)
    except Exception as e:
        st.error(friendly(e))
        st.stop()
    if lg.empty:
        st.info("Nothing has been logged yet. Actions such as suspending a user or editing the directory appear here.")
    else:
        head("What admins did", "Counts by type of action.")
        vc = lg["action"].value_counts()
        fig = go.Figure(go.Bar(x=vc.index, y=vc.values, marker_color=[TEAL, BLUE, VIOLET, AMBER, RED, GREY][:len(vc)] * 3,
                               text=vc.values, textposition="outside", cliponaxis=False))
        _show(st, whole(_layout(fig, 280), "y"))
        st.dataframe(lg.rename(columns={"created_at": "When", "admin_email": "Admin", "action": "Action",
                                        "target": "Target", "detail": "Detail"}),
                     hide_index=True, width="stretch",
                     column_config={"When": st.column_config.DatetimeColumn("When", format="DD MMM YYYY, HH:mm")})
