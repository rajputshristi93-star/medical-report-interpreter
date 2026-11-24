"""Styles for the My Reports page. Navbar styles live in theme.py and are not touched."""

CSS = """
<style>
:root{--rp-line:#E1ECEA; --rp-soft:#F5FAF9; --rp-ink:#12313A; --rp-mut:#5F7780; --rp-teal:#0F9D8A; --rp-grad:linear-gradient(135deg,#12B5A0,#2B7FF0);
  --rp-shadow:0 1px 2px rgba(16,42,50,.05), 0 10px 26px -14px rgba(16,42,50,.18);}

/* ---------- page header ---------- */
.rp-top{display:flex; align-items:center; gap:1rem; margin:.6rem 0 1.3rem;}
.rp-top .ic{width:52px; height:52px; border-radius:15px; background:var(--rp-grad); display:grid; place-items:center; color:#fff; box-shadow:0 12px 22px -12px #2B7FF0; flex:none;}
.rp-top h1{font-family:'Poppins',sans-serif; font-size:clamp(1.55rem,3.4vw,2rem); font-weight:700; letter-spacing:-.015em; line-height:1.15; margin:0; padding:0; color:var(--rp-ink);}
.rp-top .sub{color:var(--rp-mut); font-size:.9rem; margin-top:.3rem; display:flex; align-items:center; gap:.5rem; flex-wrap:wrap;}
.rp-top .mail{background:#fff; border:1px solid var(--rp-line); border-radius:99px; padding:1px 11px; font-weight:600; color:#0B7A6B; font-size:.78rem;}

/* ---------- stats ---------- */
.rp-stats{display:grid; grid-template-columns:repeat(3,1fr); gap:.9rem;}
@media(max-width:700px){.rp-stats{grid-template-columns:1fr;}}
.rp-st{display:flex; gap:.9rem; align-items:center; padding:1rem 1.15rem; border-radius:16px; background:#fff; border:1px solid var(--rp-line); box-shadow:var(--rp-shadow); animation:fadeUp .5s backwards;}
.rp-st .si{width:44px; height:44px; border-radius:12px; display:grid; place-items:center; flex:none;}
.rp-st:nth-child(1) .si{background:#DDF6EF; color:#0B8F7B;} .rp-st:nth-child(2) .si{background:#E3EEFF; color:#2563C9;} .rp-st:nth-child(3) .si{background:#EFE7FF; color:#6D45D6;}
.rp-st b{display:block; font-family:'Poppins',sans-serif; font-size:1.35rem; line-height:1.15; font-weight:700; color:var(--rp-ink);}
.rp-st span{font-size:.78rem; color:var(--rp-mut); font-weight:600; letter-spacing:.01em;}

/* ---------- search + sort ---------- */
.st-key-rp_tools{margin-top:1.2rem;}
.st-key-rp_tools [data-baseweb="input"], .st-key-rp_tools [data-baseweb="select"] > div{background:#fff !important; border:1px solid #CFE2DF !important; border-radius:12px !important; box-shadow:none !important; transition:border-color .15s, box-shadow .15s;}
.st-key-rp_tools [data-baseweb="input"]:focus-within, .st-key-rp_tools [data-baseweb="select"] > div:focus-within{border-color:var(--rp-teal) !important; box-shadow:0 0 0 3px rgba(15,157,138,.16) !important;}
.st-key-rp_tools input{background:transparent !important; font-size:.92rem;}
.rp-count{margin:.1rem 0 0; font-size:.82rem; color:var(--rp-mut); font-weight:500;}

/* ---------- month heading ---------- */
.rp-month{display:flex; align-items:baseline; gap:.7rem; margin:1.7rem 0 .75rem;}
.rp-month h2{font-family:'Poppins',sans-serif; font-size:.78rem; font-weight:700; letter-spacing:.12em; text-transform:uppercase; margin:0; padding:0; color:var(--rp-ink);}
.rp-month span{font-size:.75rem; font-weight:600; color:var(--rp-mut);}
.rp-month::after{content:""; flex:1; height:1px; background:var(--rp-line); align-self:center;}

/* ---------- report card ---------- */
div[class*="st-key-rpc-"]{background:#fff; border:1px solid var(--rp-line); border-radius:16px; padding:.75rem 1rem; margin-bottom:.7rem; box-shadow:var(--rp-shadow);
  transition:border-color .2s, box-shadow .2s; animation:fadeUp .45s backwards;}
div[class*="st-key-rpc-"]:hover{border-color:#BFE0DA; box-shadow:0 1px 2px rgba(16,42,50,.05), 0 14px 30px -14px rgba(16,42,50,.24);}
div[class*="st-key-rpc-"]:has(.rp-is-open){border-color:#8FD6C9;}

/* header row stays horizontal on phones */
div[class*="st-key-rph-"] [data-testid="stHorizontalBlock"]{flex-wrap:nowrap !important; align-items:center; gap:.7rem;}
div[class*="st-key-rph-"] [data-testid="stColumn"], div[class*="st-key-rph-"] [data-testid="column"]{min-width:0 !important;}
div[class*="st-key-rph-"] [data-testid="stColumn"]:last-child, div[class*="st-key-rph-"] [data-testid="column"]:last-child{flex:0 0 38px !important; width:38px !important;}
.rp-hd{display:flex; align-items:center; gap:.9rem;}
.rp-dt{width:52px; height:56px; border-radius:13px; background:var(--rp-grad); color:#fff; display:grid; place-content:center; text-align:center; flex:none; box-shadow:0 10px 16px -12px #2B7FF0;}
.rp-dt b{font-family:'Poppins',sans-serif; font-size:1.25rem; line-height:1; font-weight:700;}
.rp-dt span{font-size:.62rem; font-weight:600; letter-spacing:.1em; margin-top:3px; opacity:.92;}
.rp-mid{flex:1; min-width:0;}
.rp-mid h3{font-family:'Poppins',sans-serif; font-size:.96rem; font-weight:600; margin:0; padding:0; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; color:var(--rp-ink);}
.rp-mid p{font-size:.78rem; color:var(--rp-mut); margin:2px 0 0;}
.rp-tg{display:flex; gap:6px; flex-wrap:wrap; margin-top:7px;}
.rp-tag{display:inline-flex; align-items:center; gap:5px; font-size:.7rem; font-weight:600; border-radius:99px; padding:2px 9px;}
.rp-tag.hi::before,.rp-tag.lo::before,.rp-tag.ok::before{content:""; width:6px; height:6px; border-radius:50%; background:currentColor;}
.rp-tag.hi{background:#FDECE7; color:#B03A1A;} .rp-tag.lo{background:#E6F0FF; color:#1D5FBF;} .rp-tag.ok{background:#E3F6EC; color:#15704A;}
.rp-tag.nt{background:#EFF4F4; color:#586F77;} .rp-tag.un{background:#EFF4F4; color:#586F77; font-style:italic;}

/* chevron toggle */
div[class*="st-key-rptoggle_"] button{width:36px; height:36px; min-height:0; padding:0; border-radius:50%; border:0; background:#EEF7F5; position:relative; transition:background .2s;}
div[class*="st-key-rptoggle_"] button:hover{background:#D7F0EA;}
div[class*="st-key-rptoggle_"] button p{font-size:0; line-height:0;}
div[class*="st-key-rptoggle_"] button::after{content:""; position:absolute; left:50%; top:50%; width:8px; height:8px; border-right:2.2px solid var(--rp-teal); border-bottom:2.2px solid var(--rp-teal); transform:translate(-50%,-70%) rotate(45deg); transition:transform .25s;}
div[class*="st-key-rpc-"]:has(.rp-is-open) div[class*="st-key-rptoggle_"] button::after{transform:translate(-50%,-30%) rotate(-135deg);}
div[class*="st-key-rpc-"]:has(.rp-is-open) div[class*="st-key-rptoggle_"] button{background:#D7F0EA;}

/* ---------- action buttons ---------- */
div[class*="st-key-rpa-"] button{border-radius:10px; font-weight:600; font-size:.82rem; padding:.4rem .9rem; min-height:0; border:1px solid #CFE2DF; background:#fff; color:#0B7A6B; transition:.15s;}
div[class*="st-key-rpa-"] button:hover{background:#EEF7F5; border-color:#9FD6CB; color:#0B7A6B;}
div[class*="st-key-rpa-"] button[kind="primary"]{border:0; color:#fff; background:var(--rp-grad); box-shadow:0 10px 16px -10px #2B7FF0;}
div[class*="st-key-rpa-"] button[kind="primary"] p{color:#fff;}
div[class*="st-key-rpa-"] button[kind="primary"]:hover{filter:brightness(1.06); color:#fff;}
div[class*="st-key-rpa-del"] button{border-color:#F2C9BD; color:#B03A1A;}
div[class*="st-key-rpa-del"] button:hover{background:#FDECE7; border-color:#F2C9BD; color:#B03A1A;}
div[class*="st-key-rpa-yes"] button{border:0; background:#D9482B; color:#fff;}
div[class*="st-key-rpa-yes"] button p{color:#fff;}
div[class*="st-key-rpa-yes"] button:hover{background:#C23E23; color:#fff;}

/* ---------- details ---------- */
.rp-body{border-top:1px solid var(--rp-line); margin-top:.7rem; padding-top:1rem;}
.rp-sum{display:grid; grid-template-columns:repeat(4,1fr); gap:.6rem; margin-bottom:1rem;}
@media(max-width:560px){.rp-sum{grid-template-columns:repeat(2,1fr);}}
.rp-sum div{background:var(--rp-soft); border:1px solid var(--rp-line); border-radius:12px; padding:.55rem .8rem; font-size:.72rem; color:var(--rp-mut); font-weight:600; text-transform:uppercase; letter-spacing:.05em;}
.rp-sum b{display:block; font-family:'Poppins',sans-serif; font-size:1.2rem; color:var(--rp-ink); text-transform:none; letter-spacing:0; line-height:1.3;}
.rp-sum div.h b{color:#B03A1A;} .rp-sum div.l b{color:#1D5FBF;} .rp-sum div.o b{color:#15704A;}
.rp-tw{overflow-x:auto; border:1px solid var(--rp-line); border-radius:12px;}
.rp-tw table{width:100%; border-collapse:collapse; font-size:.84rem; min-width:480px;}
.rp-tw th{text-align:left; font-size:.68rem; color:var(--rp-mut); background:var(--rp-soft); padding:9px 14px; font-weight:700; text-transform:uppercase; letter-spacing:.08em;}
.rp-tw td{padding:9px 14px; border-top:1px solid #EAF2F1; color:var(--rp-ink);}
.rp-tw tbody tr:hover td{background:#FAFDFC;}
.rp-tw td:nth-child(3){color:var(--rp-mut);}
.rp-info{background:#EDF4FF; border:1px solid #CFE0FA; color:#2F4C7A; border-radius:12px; padding:.75rem .95rem; font-size:.85rem;}
.rp-expl-t{font-family:'Poppins',sans-serif; font-weight:600; color:var(--rp-ink); margin:1.1rem 0 .3rem; font-size:.95rem;}
.rp-ai{font-size:.76rem; color:var(--rp-mut); margin:.7rem 0 .5rem;}
.rp-cf{font-size:.82rem; font-weight:600; color:#B03A1A; padding:.2rem 0 .3rem;}

.rp-empty{text-align:center; padding:2.4rem 1rem; background:#fff; border:1.5px dashed #BFDDD7; border-radius:16px; color:var(--rp-mut); margin-top:1rem;}
.rp-empty .e{font-size:2.3rem;} .rp-empty h3{color:var(--rp-ink); margin:.4rem 0 .3rem; font-size:1.05rem;} .rp-empty p{margin:0;}
.rp-disc{margin-top:2rem; padding-top:1rem; border-top:1px solid var(--rp-line); font-size:.76rem; color:var(--rp-mut); display:flex; gap:.5rem; line-height:1.55;}
@media(prefers-reduced-motion:reduce){.rp-st, div[class*="st-key-rpc-"]{animation:none !important; transition:none !important;}}
</style>
"""

IC_FOLDER = '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></svg>'
IC_DOC = '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M9 13h6M9 17h6"/></svg>'
IC_CAL = '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 10h18"/></svg>'
IC_HEAD = '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></svg>'
