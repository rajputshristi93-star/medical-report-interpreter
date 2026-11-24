"""Look and feel for MediLens AI: 3D cards, soft shadows, animations, type scale and a top navigation bar."""
import streamlit as st

from i18n import t

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Poppins:wght@500;600;700;800&display=swap');

:root{
  --teal:#0F9D8A; --teal-d:#0B7A6B; --blue:#1B6FB5; --navy:#12313A; --ink:#1F3A44; --muted:#5C7480;
  --card:#FFFFFF; --line:rgba(15,157,138,.16);
  --shadow-3d: 0 2px 4px rgba(18,49,58,.06), 0 12px 24px rgba(18,49,58,.10), 0 28px 48px rgba(15,157,138,.12);
  --shadow-hover: 0 4px 8px rgba(18,49,58,.08), 0 22px 36px rgba(18,49,58,.16), 0 40px 64px rgba(15,157,138,.18);
}
html, body, .stApp, [data-testid="stAppViewContainer"], .stMarkdown, p, label, li, input, textarea, select, button {
  font-family:'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif;
}
.stApp{
  background:
    radial-gradient(1100px 520px at 8% -8%, #D4F2EC 0%, rgba(212,242,236,0) 60%),
    radial-gradient(900px 480px at 100% 0%, #D8E9FA 0%, rgba(216,233,250,0) 58%),
    linear-gradient(180deg,#F8FCFC 0%,#F3F9F9 100%);
}
[data-testid="stHeader"]{background:transparent;}
[data-testid="stToolbar"], #MainMenu, footer{visibility:hidden;}
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"]{display:none;}
.block-container, [data-testid="stMainBlockContainer"]{max-width:1240px !important; padding-top:1.1rem; padding-bottom:3rem;}

/* ---------- type scale ---------- */
h1,h2,h3,h4{font-family:'Poppins','Inter',sans-serif; color:var(--navy); letter-spacing:-.01em;}
h1{font-size:2.4rem; font-weight:800;} h2{font-size:1.75rem; font-weight:700;} h3{font-size:1.3rem; font-weight:600;}
.t-eyebrow{font-size:.78rem; font-weight:600; letter-spacing:.18em; text-transform:uppercase; color:var(--teal);}
.t-display{font-family:'Poppins',sans-serif; font-size:clamp(2.1rem,4.6vw,3.5rem); font-weight:800; line-height:1.1; color:var(--navy); margin:.3rem 0 .6rem;}
.t-h1{font-family:'Poppins',sans-serif; font-size:2.1rem; font-weight:700; color:var(--navy);}
.t-h2{font-family:'Poppins',sans-serif; font-size:1.55rem; font-weight:700; color:var(--navy); margin:2rem 0 .2rem;}
.t-lead{font-size:1.18rem; line-height:1.6; color:var(--muted); max-width:36rem;}
.t-body{font-size:1rem; line-height:1.6; color:var(--ink);}
.t-small{font-size:.85rem; color:var(--muted);}
.grad{background:linear-gradient(90deg,var(--teal),var(--blue)); -webkit-background-clip:text; background-clip:text; color:transparent; -webkit-text-fill-color:transparent;}

/* ---------- animations ---------- */
@keyframes fadeUp{from{opacity:0; transform:translateY(22px)} to{opacity:1; transform:none}}
@keyframes floaty{0%,100%{transform:translateY(0) rotate(0)} 50%{transform:translateY(-20px) rotate(7deg)}}
@keyframes drift{0%,100%{transform:translate(0,0)} 50%{transform:translate(14px,-10px)}}
@keyframes shimmer{0%{background-position:0% 50%} 100%{background-position:200% 50%}}
@keyframes growX{from{width:0} to{width:var(--w)}}
@keyframes pulseGlow{0%,100%{box-shadow:0 6px 0 var(--teal-d), 0 12px 24px rgba(15,157,138,.35)} 50%{box-shadow:0 6px 0 var(--teal-d), 0 16px 34px rgba(27,111,181,.5)}}
.fade-up{animation:fadeUp .7s cubic-bezier(.2,.8,.2,1) backwards;}
.d1{animation-delay:.08s} .d2{animation-delay:.16s} .d3{animation-delay:.24s} .d4{animation-delay:.32s} .d5{animation-delay:.4s}
@media (prefers-reduced-motion: reduce){ .fade-up,.card3d,.hero3d,.hero3d .orb,.hero2,.rc,.spc,.doc,.kpi,.okb,.report3d{animation:none !important; transition:none !important;} }

/* ---------- 3D cards and icons ---------- */
.card3d{background:var(--card); border:1px solid var(--line); border-radius:22px; padding:1.3rem 1.4rem; min-height:232px; margin-bottom:1.1rem;
  box-shadow:var(--shadow-3d); transition:transform .35s cubic-bezier(.2,.8,.2,1), box-shadow .35s; transform:perspective(900px);
  animation:fadeUp .7s cubic-bezier(.2,.8,.2,1) backwards;}
.card3d:hover{transform:perspective(900px) translateY(-9px) rotateX(3deg) rotateY(-3deg); box-shadow:var(--shadow-hover);}
.card3d h4{margin:.9rem 0 .3rem; font-size:1.12rem; font-weight:600;}
.card3d p{margin:0; color:var(--muted); font-size:.95rem; line-height:1.55;}
.icon3d{width:58px; height:58px; border-radius:17px; display:grid; place-items:center; font-size:1.7rem; color:#fff; transform:rotate(-6deg);
  background:linear-gradient(145deg,#1FC8B0,#1B6FB5); box-shadow:0 6px 0 var(--teal-d), 0 14px 22px rgba(15,157,138,.35);}
.icon3d.amber{background:linear-gradient(145deg,#FFC24B,#F5841F); box-shadow:0 6px 0 #B85F0E, 0 14px 22px rgba(245,132,31,.35);}
.icon3d.violet{background:linear-gradient(145deg,#8E7CFF,#5B3FD6); box-shadow:0 6px 0 #3E2A9E, 0 14px 22px rgba(91,63,214,.35);}
.icon3d.rose{background:linear-gradient(145deg,#FF8FA3,#E5484D); box-shadow:0 6px 0 #A92B30, 0 14px 22px rgba(229,72,77,.35);}
.step-no{font-family:'Poppins',sans-serif; font-weight:800; font-size:2.2rem; color:rgba(15,157,138,.22); float:right; line-height:1;}

/* ---------- hero ---------- */
.hero3d{position:relative; overflow:hidden; border-radius:30px; padding:2.6rem 2.4rem; margin:.4rem 0 1.6rem;
  background:linear-gradient(120deg,#EAF8F5 0%,#E3F0FB 55%,#EEF0FF 100%); background-size:200% 200%; animation:shimmer 9s linear infinite alternate;
  box-shadow:var(--shadow-3d); border:1px solid rgba(255,255,255,.8); display:grid; grid-template-columns:1.15fr .85fr; gap:2rem; align-items:center;}
.hero3d .orb{position:absolute; border-radius:50%; filter:blur(.3px); pointer-events:none;}
.hero3d .o1{width:210px; height:210px; right:-50px; top:-60px; background:radial-gradient(circle at 30% 30%,#7FE5D3,#1B6FB5); opacity:.35; animation:floaty 7s ease-in-out infinite;}
.hero3d .o2{width:110px; height:110px; left:42%; bottom:-30px; background:radial-gradient(circle at 30% 30%,#FFD27A,#F5841F); opacity:.4; animation:drift 6s ease-in-out infinite;}
.hero3d .o3{width:60px; height:60px; left:6%; top:12%; background:radial-gradient(circle at 30% 30%,#B9A9FF,#5B3FD6); opacity:.35; animation:floaty 5.5s ease-in-out infinite reverse;}
.hero-copy{position:relative; z-index:2;}
.report3d{position:relative; z-index:2; background:#fff; border-radius:22px; padding:1.2rem 1.3rem; border:1px solid var(--line);
  transform:perspective(1000px) rotateY(-10deg) rotateX(5deg) rotateZ(1deg); transition:transform .5s cubic-bezier(.2,.8,.2,1);
  box-shadow:-18px 24px 48px rgba(18,49,58,.22), 0 2px 4px rgba(18,49,58,.08);}
.report3d:hover{transform:perspective(1000px) rotateY(0) rotateX(0) scale(1.03);}
.report3d .ttl{font-family:'Poppins',sans-serif; font-weight:600; color:var(--navy); margin-bottom:.7rem; display:flex; justify-content:space-between; font-size:.95rem;}
.rrow{margin:.55rem 0;} .rrow .lab{display:flex; justify-content:space-between; font-size:.82rem; color:var(--ink); margin-bottom:.25rem;}
.rbar{height:11px; border-radius:99px; background:#EAF1F2; overflow:hidden;}
.rbar i{display:block; height:100%; border-radius:99px; width:var(--w); animation:growX 1.4s cubic-bezier(.2,.8,.2,1) both .4s;}
.pill{display:inline-block; padding:2px 10px; border-radius:99px; font-size:.72rem; font-weight:600;}
.p-ok{background:#D9F5E5; color:#16703F;} .p-low{background:#FFF0CF; color:#8A5A00;} .p-high{background:#FDE0E1; color:#9D1C20;}
@media (max-width:820px){.hero3d{grid-template-columns:1fr; padding:1.8rem 1.3rem;} .report3d{transform:none;}}

/* ---------- top navigation ---------- */
.st-key-topnav{position:sticky; top:.4rem; z-index:1000; background:rgba(255,255,255,.82); backdrop-filter:blur(16px) saturate(160%);
  -webkit-backdrop-filter:blur(16px) saturate(160%); border:1px solid rgba(255,255,255,.9); border-radius:20px; padding:.35rem .9rem;
  margin:0 0 1.3rem; box-shadow:var(--shadow-3d); animation:fadeUp .6s backwards;}
.st-key-topnav [data-testid="stHorizontalBlock"]{align-items:center; gap:.4rem;}
.brand{display:flex; align-items:center; gap:.6rem; font-family:'Poppins',sans-serif; font-weight:700; font-size:1.2rem; color:var(--navy); white-space:nowrap;}
.brand .logo{width:38px; height:38px; border-radius:12px; display:grid; place-items:center; font-size:1.2rem; color:#fff; transform:rotate(-8deg);
  background:linear-gradient(145deg,#1FC8B0,#1B6FB5); box-shadow:0 4px 0 var(--teal-d), 0 8px 14px rgba(15,157,138,.35); transition:transform .4s;}
.brand:hover .logo{transform:rotate(8deg) scale(1.1);}
.brand b{color:var(--teal);}
.st-key-topnav a[data-testid="stPageLink-NavLink"]{position:relative; border-radius:13px; padding:.5rem .45rem; justify-content:center; white-space:nowrap;
  transition:transform .25s cubic-bezier(.2,.8,.2,1), background .25s, box-shadow .25s; overflow:visible;}
.st-key-topnav a[data-testid="stPageLink-NavLink"] p{font-weight:600; font-size:.9rem; color:var(--ink); transition:color .25s; white-space:nowrap; overflow:visible; text-overflow:clip;}
.st-key-topnav a[data-testid="stPageLink-NavLink"]::after{content:""; position:absolute; left:16px; right:16px; bottom:5px; height:3px; border-radius:3px;
  background:linear-gradient(90deg,var(--teal),var(--blue)); transform:scaleX(0); transform-origin:left; transition:transform .35s cubic-bezier(.2,.8,.2,1);}
.st-key-topnav a[data-testid="stPageLink-NavLink"]:hover{transform:translateY(-3px); background:linear-gradient(135deg,rgba(15,157,138,.13),rgba(27,111,181,.13));
  box-shadow:0 10px 18px rgba(15,157,138,.18);}
.st-key-topnav a[data-testid="stPageLink-NavLink"]:hover::after{transform:scaleX(1);}
.st-key-navitem-active a[data-testid="stPageLink-NavLink"]{background:linear-gradient(135deg,var(--teal),var(--blue)) !important; box-shadow:0 5px 0 var(--teal-d), 0 12px 20px rgba(15,157,138,.3);}
.st-key-navitem-active a[data-testid="stPageLink-NavLink"] p{color:#fff !important;}
.st-key-navitem-active a[data-testid="stPageLink-NavLink"]::after{display:none;}

/* ---------- buttons, inputs, tabs ---------- */
.stButton > button, .stDownloadButton > button, [data-testid="stPopover"] > div > button{
  border-radius:14px; font-weight:600; border:1px solid var(--line); padding:.6rem 1.2rem; background:#fff; color:var(--ink);
  box-shadow:0 3px 0 rgba(18,49,58,.10), 0 10px 18px rgba(18,49,58,.08); transition:transform .2s, box-shadow .2s, background .2s;}
.stButton > button:hover, .stDownloadButton > button:hover{transform:translateY(-3px); box-shadow:0 5px 0 rgba(18,49,58,.12), 0 16px 26px rgba(18,49,58,.14); border-color:var(--teal);}
.stButton > button:active{transform:translateY(2px); box-shadow:0 1px 0 rgba(18,49,58,.12), 0 4px 8px rgba(18,49,58,.1);}
.stButton > button[kind="primary"], .stButton > button[data-testid="stBaseButton-primary"]{
  color:#fff; border:none; background:linear-gradient(135deg,var(--teal),var(--blue)); box-shadow:0 5px 0 var(--teal-d), 0 12px 22px rgba(15,157,138,.32);}
.stButton > button[kind="primary"]:hover, .stButton > button[data-testid="stBaseButton-primary"]:hover{box-shadow:0 8px 0 var(--teal-d), 0 18px 30px rgba(27,111,181,.4);}
.stButton > button[kind="primary"]:active, .stButton > button[data-testid="stBaseButton-primary"]:active{transform:translateY(4px); box-shadow:0 1px 0 var(--teal-d), 0 4px 8px rgba(15,157,138,.3);}
.st-key-cta a[data-testid="stPageLink-NavLink"]{display:inline-flex; width:auto; padding:.85rem 1.7rem; border-radius:16px; color:#fff;
  background:linear-gradient(135deg,var(--teal),var(--blue)); animation:pulseGlow 2.6s ease-in-out infinite; transition:transform .25s;}
.st-key-cta a[data-testid="stPageLink-NavLink"] p{color:#fff; font-weight:700; font-size:1.05rem; white-space:nowrap;}
.st-key-cta2 a[data-testid="stPageLink-NavLink"] p{white-space:nowrap; font-weight:600;}
.st-key-cta a[data-testid="stPageLink-NavLink"]:hover{transform:translateY(-4px) scale(1.03);}
.st-key-cta2 a[data-testid="stPageLink-NavLink"]{display:inline-flex; width:auto; padding:.85rem 1.5rem; border-radius:16px; background:#fff; border:1px solid var(--line);
  box-shadow:0 4px 0 rgba(18,49,58,.1), 0 12px 20px rgba(18,49,58,.08); transition:transform .25s;}
.st-key-cta2 a[data-testid="stPageLink-NavLink"]:hover{transform:translateY(-4px);}
[data-baseweb="input"], [data-baseweb="select"] > div, [data-baseweb="textarea"]{border-radius:12px !important;}
.stTabs [data-baseweb="tab-list"]{gap:.4rem; border-bottom:none;}
.stTabs [data-baseweb="tab"]{border-radius:12px 12px 0 0; padding:.55rem 1.1rem; font-weight:600; transition:background .2s, transform .2s;}
.stTabs [data-baseweb="tab"]:hover{background:rgba(15,157,138,.1); transform:translateY(-2px);}
.stTabs [aria-selected="true"]{background:rgba(15,157,138,.14); color:var(--teal-d);}
.stTabs [data-baseweb="tab-highlight"]{background:linear-gradient(90deg,var(--teal),var(--blue)) !important; height:3px; border-radius:3px;}
[data-testid="stVerticalBlockBorderWrapper"]{border-radius:20px;}
[data-testid="stExpander"]{border-radius:16px; border:1px solid var(--line); box-shadow:0 6px 16px rgba(18,49,58,.06); background:#fff;}
[data-testid="stAlert"]{border-radius:16px;}
[data-testid="stPlotlyChart"]{background:#fff; border-radius:20px; border:1px solid var(--line); box-shadow:0 8px 20px rgba(18,49,58,.10); padding:.3rem; overflow:hidden; margin-bottom:.9rem; animation:fadeUp .7s backwards;}
[data-testid="stPlotlyChart"] > div{border-radius:16px; overflow:hidden;}
[data-testid="stDataFrame"]{border-radius:16px; overflow:hidden; box-shadow:0 8px 20px rgba(18,49,58,.08);}
::-webkit-scrollbar{width:10px;height:10px} ::-webkit-scrollbar-thumb{background:linear-gradient(180deg,var(--teal),var(--blue)); border-radius:10px;}
/* ---------- profile menu ---------- */
.pop{text-align:center; padding:.2rem .2rem .6rem; min-width:230px;}
.pop .pav{width:76px; height:76px; border-radius:50%; margin:.2rem auto .6rem; display:grid; place-items:center; overflow:hidden; color:#fff; font:800 1.6rem 'Poppins',sans-serif;
  background:linear-gradient(135deg,#14C4A5,#2B7FF0); box-shadow:0 10px 24px rgba(18,49,58,.25); border:4px solid #fff;}
.pop .pav img{width:100%; height:100%; object-fit:cover;}
.pop .pn{font-family:'Poppins',sans-serif; font-weight:700; font-size:1.05rem; color:var(--navy);} .pop .pe{font-size:.82rem; color:var(--muted); word-break:break-all;}
.pop .prole{display:inline-block; margin-top:.45rem; padding:.15rem .7rem; border-radius:99px; font-size:.72rem; font-weight:700; background:#D9F5EE; color:#0B7A6B;}
.pop .prole.admin{background:#EFE6FF; color:#5B3FD6;}
.st-key-navuser button{padding-left:.5rem !important;}
.st-key-navuser button p{white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:7rem;}
</style>
"""


def inject_theme():
    st.markdown(CSS, unsafe_allow_html=True)


def render_nav(user, logout_fn, pages, extras=None, active_label=None, profile=None):
    """Sticky top bar. pages = [(path, label, icon)]. profile = {'name', 'avatar' (data address), 'role'}."""
    import html as _h

    profile = profile or {}
    email = getattr(user, "email", "") or ""
    name = profile.get("name") or email.split("@")[0] or "Account"
    uri, role = profile.get("avatar"), profile.get("role") or "user"
    initials = "".join(p[0] for p in name.replace("@", " ").split()[:2]).upper() or "U"
    first = (name.split() or ["Account"])[0][:12]
    # the small round photo (or initials) inside the profile button
    face = (f'background:url("{uri}") center/cover;' if uri else f'background:linear-gradient(135deg,#14C4A5,#2B7FF0);')
    st.markdown(f'<style>.st-key-navuser button::before{{content:"{"" if uri else _h.escape(initials)}"; display:inline-grid; place-items:center; width:30px; height:30px; flex:0 0 30px; '
                f'border-radius:50%; margin-right:.5rem; color:#fff; font:800 .72rem Poppins,sans-serif; border:2px solid #fff; box-shadow:0 3px 8px rgba(18,49,58,.25); {face}}}</style>',
                unsafe_allow_html=True)
    with st.container(key="topnav"):
        link_w = [0.8 + 0.085 * len(label) for _, label, _ in pages]  # wider boxes for longer labels
        widths = [3.0] + link_w + ([1.45] if extras else []) + [1.75]
        cols = st.columns(widths, vertical_alignment="center")
        cols[0].markdown('<div class="brand"><span class="logo">🩺</span><span>MediLens <b>AI</b></span></div>', unsafe_allow_html=True)
        for i, (col, (path, label, icon)) in enumerate(zip(cols[1:], pages)):
            with col, st.container(key="navitem-active" if label == active_label else f"navitem-{i}"):
                st.page_link(path, label=label, icon=icon)
        if extras:
            with cols[-2]:
                extras()
        with cols[-1], st.container(key="navuser"):
            try:
                pop = st.popover(first, width="stretch")
            except TypeError:
                pop = st.popover(first, use_container_width=True)
            with pop:
                avatar = f'<img src="{uri}" alt="">' if uri else _h.escape(initials)
                badge = t("nav.role_admin") if role == "admin" else t("nav.role_user")
                st.markdown(f'<div class="pop"><div class="pav">{avatar}</div><div class="pn">{_h.escape(name)}</div>'
                            f'<div class="pe">{_h.escape(email)}</div><span class="prole {"admin" if role == "admin" else ""}">{_h.escape(badge)}</span></div>',
                            unsafe_allow_html=True)
                st.page_link("views/profile.py", label=t("nav.edit_profile"), icon="✏️")
                if st.button(t("nav.logout"), key="nav_logout", width="stretch"):
                    logout_fn()
                    st.rerun()


def render_footer():
    """Medical disclaimer in the chosen language."""
    head, _, rest = t("footer.disclaimer").partition(":")
    st.markdown(f'<div class="footer">⚕️ <b>{head}:</b>{rest}</div>', unsafe_allow_html=True)
