"""CSS for the Interpreter and Find a Doctor pages. Text that CSS must show (card subtitles, drop-zone text) is
filled in from the chosen language, so it is translated too."""
import json

import streamlit as st

from i18n import t

BASE = """
<style>
/* ===== shared: page header, notices, cards ===== */
.ip-head{text-align:center; margin:.2rem 0 1rem;}
.ip-head h1{font-family:'Poppins',sans-serif; font-weight:800; font-size:clamp(1.8rem,3.6vw,2.6rem); line-height:1.25; color:var(--navy); margin:0 0 .6rem;}
.ip-head p{color:var(--muted); font-size:1.08rem; line-height:1.6; max-width:40rem; margin:0 auto;}
.ip-badges{display:flex; flex-wrap:wrap; gap:.6rem; justify-content:center; margin:1rem 0 1.3rem;}
.ip-badges span{background:#fff; border:1px solid var(--line); border-radius:99px; padding:.35rem .85rem; font-size:.82rem; font-weight:600; color:var(--teal-d); box-shadow:0 4px 10px rgba(18,49,58,.06);}
.nc{display:flex; gap:.85rem; padding:1rem 1.1rem; border-radius:18px; border:1px solid; box-shadow:0 8px 20px rgba(18,49,58,.06); height:100%;}
.nc .ni{flex:0 0 38px; width:38px; height:38px; border-radius:12px; background:#fff; display:grid; place-items:center; font-size:1.2rem; box-shadow:0 4px 10px rgba(18,49,58,.08);}
.nc strong{display:block; font-family:'Poppins',sans-serif; font-size:.98rem; margin-bottom:.15rem;}
.nc p{margin:0; font-size:.9rem; line-height:1.55;}
.nc.info{background:linear-gradient(135deg,#EAF1FF,#E2F2FF); border-color:#CFE0F7; color:#1F3F66;}
.nc.ok{background:linear-gradient(135deg,#E6FAF1,#DDF6EC); border-color:#BDEBD7; color:#0F5B3A;}
.nc.no{background:linear-gradient(135deg,#FFF1E2,#FFEBD6); border-color:#F7D6B8; color:#7A4300;}
.ncg{display:grid; grid-template-columns:1fr 1fr; gap:.9rem; margin:.9rem 0 1.2rem;}
@media (max-width:760px){.ncg{grid-template-columns:1fr;}}

.st-key-pcard, .st-key-fcard, .st-key-dcard, .st-key-rcard{background:#fff; border:1px solid var(--line); border-radius:24px;
  padding:1.5rem 1.5rem 1.2rem; box-shadow:var(--shadow-3d); position:relative; overflow:hidden; margin-bottom:1.2rem; animation:fadeUp .7s backwards;}
.st-key-pcard::before, .st-key-fcard::before, .st-key-dcard::before{content:""; position:absolute; left:0; right:0; top:0; height:6px;
  background:linear-gradient(90deg,#14C4A5,#2B7FF0);}
.card-head{display:flex; align-items:center; gap:.9rem; margin:.2rem 0 1rem;}
.card-head .pic{width:52px; height:52px; border-radius:16px; display:grid; place-items:center; font-size:1.6rem; background:#D9F5EE; box-shadow:0 5px 0 #A5E3D5;}
.card-head h2{font-family:'Poppins',sans-serif; font-size:1.25rem; margin:0; color:var(--navy);}
.card-head p{margin:0; font-size:.88rem; color:var(--muted);}
.card-head .opt{margin-left:auto; background:#D9F5EE; color:var(--teal-d); font-weight:700; font-size:.78rem; padding:.3rem .8rem; border-radius:99px;}
.pnote{display:flex; gap:.6rem; align-items:center; background:#EAF1FF; border:1px solid #D2E2FA; color:#27508A; border-radius:14px; padding:.65rem .9rem; font-size:.85rem; margin:.4rem 0 .2rem;}
.sec-t{font-family:'Poppins',sans-serif; font-size:1.15rem; font-weight:700; color:var(--navy); margin:.1rem 0 .8rem;}
.st-key-pcard input, .st-key-dcard input{background:#F1F8F7 !important; border-radius:14px !important;}

/* ===== results ===== */
.okb{display:flex; align-items:center; gap:.8rem; padding:.9rem 1.2rem; border-radius:20px; color:#fff; font-weight:700; font-size:1.05rem;
  background:linear-gradient(135deg,#12C26A,#2BE08F); box-shadow:0 12px 28px rgba(18,194,106,.32); margin-bottom:1rem; animation:fadeUp .6s backwards;}
.okb i{width:34px; height:34px; border-radius:50%; background:rgba(255,255,255,.28); display:grid; place-items:center; font-style:normal;}
.hero2{position:relative; overflow:hidden; display:grid; grid-template-columns:auto 1fr; gap:1.8rem; align-items:center; background:#fff;
  border-radius:28px; padding:1.8rem 2rem; box-shadow:var(--shadow-3d); border:1px solid var(--line); margin-bottom:1rem; animation:fadeUp .7s backwards;}
.hero2::before{content:""; position:absolute; left:0; right:0; top:0; height:7px; background:linear-gradient(90deg,#14C4A5,#2B7FF0,#A78BFA,#F472B6,#FBBF24);}
.ringw{position:relative; width:170px; height:170px; border-radius:50%; background:radial-gradient(circle,#fff 56%,rgba(34,229,139,.16) 57%);}
.ringw svg{transform:rotate(-90deg);} .ringw .arc{animation:arc 1.6s cubic-bezier(.2,.8,.2,1) both;}
@keyframes arc{from{stroke-dasharray:0 339.3}}
.ringw .mid{position:absolute; inset:0; display:grid; place-content:center; text-align:center;}
.ringw .mid b{font-family:'Poppins',sans-serif; font-size:1.9rem; color:var(--navy); line-height:1.1;} .ringw .mid span{font-size:.82rem; color:var(--muted);}
.hero2 h2{font-family:'Poppins',sans-serif; font-size:2.1rem; font-weight:800; margin:0 0 .8rem; color:var(--navy);}
.tiles{display:grid; grid-template-columns:repeat(3,1fr); gap:.8rem;}
.tile{position:relative; border-radius:18px; padding:.9rem 1rem; color:#fff; box-shadow:0 12px 24px rgba(18,49,58,.16); transition:transform .3s;}
.tile:hover{transform:translateY(-5px) rotate(-.6deg);}
.tile b{display:block; font-family:'Poppins',sans-serif; font-size:2rem; line-height:1.1;} .tile b.long{font-size:1.02rem; padding:.55rem 2rem .45rem 0; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}
.tile span{font-size:.9rem; font-weight:600;} .tile .ti{position:absolute; right:.8rem; top:.7rem; font-size:1.5rem;}
.tile.red{background:linear-gradient(135deg,#F2554B,#FF8A5B);} .tile.green{background:linear-gradient(135deg,#17C97C,#6DE7B0); color:#0B4A2D;}
.tile.amber{background:linear-gradient(135deg,#FFC93C,#FFE08A); color:#6B4A00;} .tile.grey{background:linear-gradient(135deg,#C8D3DA,#E3EAEE); color:#3B4F59;}
.split{display:flex; gap:6px; margin-top:.9rem;} .split i{display:block; height:12px; border-radius:99px;}
.alertb{display:flex; gap:.8rem; align-items:center; padding:.9rem 1.1rem; border-radius:18px; background:linear-gradient(135deg,#FFE9E5,#FFDDD6);
  border-left:6px solid #E5484D; color:#9B1C12; margin:.2rem 0 1.1rem; font-size:.95rem; line-height:1.5;}
.alertb .pulse{animation:pulse 1.6s infinite;} @keyframes pulse{0%,100%{transform:scale(1)} 50%{transform:scale(1.25)}}
.st-key-rail{background:#fff; border:1px solid var(--line); border-radius:24px; padding:.6rem; box-shadow:var(--shadow-3d);}
.st-key-rail button{justify-content:flex-start; text-align:left; border:none !important; background:transparent !important; box-shadow:none !important;
  border-radius:16px; padding:.7rem .8rem; width:100%; color:var(--ink); transition:background .2s, transform .2s;}
.st-key-rail button:hover{background:rgba(15,157,138,.1) !important; transform:translateX(4px);}
.st-key-rail button p{font-weight:600; font-size:.93rem; text-align:left !important;}
.st-key-rail button, .st-key-rail button > div, .st-key-rail button [data-testid="stMarkdownContainer"]{justify-content:flex-start !important; text-align:left !important; width:100%;}
.st-key-rail [class*="_on"] button{color:#fff !important; box-shadow:0 8px 18px rgba(18,49,58,.2) !important;}
.st-key-rail [class*="_on"] button p{color:#fff;}
.st-key-rail .st-key-rail_1_on button{background:linear-gradient(135deg,#14C4A5,#2B7FF0) !important;}
.st-key-rail .st-key-rail_2_on button{background:linear-gradient(135deg,#9B7BFF,#F06AC8) !important;}
.st-key-rail .st-key-rail_3_on button{background:linear-gradient(135deg,#2BC48A,#A3DB3C) !important;}
.st-key-rail .st-key-rail_4_on button{background:linear-gradient(135deg,#3B9DF8,#6C5CE7) !important;}
.st-key-rail .st-key-rail_5_on button{background:linear-gradient(135deg,#FF9A3C,#FFC93C) !important;}
.st-key-rail .st-key-rail_6_on button{background:linear-gradient(135deg,#14C4A5,#22D3EE) !important;}
.st-key-rail .st-key-rail_7_on button{background:linear-gradient(135deg,#F472B6,#F2554B) !important;}
.st-key-rcard{padding:1.3rem 1.4rem;}
.rc-head{display:flex; align-items:center; gap:.7rem; margin-bottom:.9rem;}
.rc-head .ic{width:42px; height:42px; border-radius:13px; display:grid; place-items:center; font-size:1.25rem; background:#D9F5EE;}
.rc-head h3{font-family:'Poppins',sans-serif; font-size:1.2rem; margin:0; color:var(--navy);}
.rcg{display:grid; grid-template-columns:repeat(2,1fr); gap:1rem; margin-top:.8rem;}
@media (max-width:900px){.rcg{grid-template-columns:1fr;} .hero2{grid-template-columns:1fr;} .tiles{grid-template-columns:1fr;}}
.rc{background:#fff; border:1px solid var(--line); border-radius:20px; padding:1rem 1.1rem; box-shadow:0 8px 20px rgba(18,49,58,.07); transition:transform .3s, box-shadow .3s; animation:fadeUp .6s backwards;}
.rc:hover{transform:translateY(-5px); box-shadow:var(--shadow-hover);}
.rc.hi{border-color:#F7C9C6; background:linear-gradient(180deg,#FFF7F6,#fff);} .rc.lo{border-color:#F8DDA8; background:linear-gradient(180deg,#FFFAEE,#fff);}
.rc.ex{border-color:#F59B7A; background:linear-gradient(180deg,#FFF1EA,#fff); box-shadow:0 10px 26px rgba(229,72,77,.2);}
.rc.un{background:#F6F8F9; border-style:dashed;}
.rc .top{display:flex; justify-content:space-between; gap:.6rem; align-items:flex-start;}
.rc .nm{font-weight:600; color:#2B4752; font-size:.95rem; line-height:1.35;}
.rc .pl{flex:0 0 auto; font-size:.74rem; font-weight:700; padding:.25rem .65rem; border-radius:99px;}
.pl.hi{background:#FDE0E1; color:#9D1C20;} .pl.lo{background:#FFF0CF; color:#8A5A00;} .pl.ok{background:#D9F5E5; color:#16703F;} .pl.un{background:#E6EBEE; color:#4B5C66;}
.pl.ex{background:#E5532A; color:#fff;}
.rc .rv{font-family:'Poppins',sans-serif; font-weight:800; font-size:2rem; color:var(--navy); margin:.35rem 0 .6rem; line-height:1.1;}
.rc .rv small{font-family:'Inter',sans-serif; font-size:.85rem; font-weight:600; color:var(--muted); margin-left:.3rem;}
.zb{position:relative; display:flex; height:10px; border-radius:99px; overflow:visible; margin:.2rem 0 .5rem;}
.zb i{display:block; height:100%;} .zb i:nth-child(1){background:#3B9DF8; width:25%; border-radius:99px 0 0 99px;} .zb i:nth-child(2){background:#2FD085; width:50%;}
.zb i:nth-child(3){background:#FF5A4E; width:25%; border-radius:0 99px 99px 0;} .zb.none i{background:#D5DDE2 !important;}
.zb .mk{position:absolute; top:50%; width:20px; height:20px; border-radius:50%; background:#E5484D; border:3px solid #fff; transform:translate(-50%,-50%); box-shadow:0 4px 10px rgba(18,49,58,.35); transition:left 1.2s cubic-bezier(.2,.8,.2,1);}
.zb .mk.lo{background:#3B9DF8;} .zb .mk.ok{background:#12A560;}
.zl{display:grid; grid-template-columns:25% 50% 25%; font-size:.72rem; font-weight:700; text-align:center;}
.zl span:nth-child(1){color:#2B7FF0;} .zl span:nth-child(2){color:#0F8F59;} .zl span:nth-child(3){color:#E5484D;}
.okbx{background:linear-gradient(135deg,#DDF7EC,#E8FAF2); color:#0F6B43; border-radius:16px; padding:.85rem 1.1rem; font-weight:700; margin-top:1rem;}
.who{background:linear-gradient(135deg,#14C4A5,#2B7FF0); color:#fff; border-radius:24px; padding:1.6rem; box-shadow:0 18px 40px rgba(43,127,240,.3);}
.who h3{font-family:'Poppins',sans-serif; color:#fff; margin:0 0 .5rem;} .who p{margin:.4rem 0 1rem; opacity:.95;}
.who .pills{display:flex; flex-wrap:wrap; gap:.5rem; margin-bottom:1rem;} .who .pills span{background:rgba(255,255,255,.22); border:1px solid rgba(255,255,255,.4); padding:.35rem .8rem; border-radius:99px; font-weight:700; font-size:.88rem;}
.st-key-who_cta a{display:inline-flex; width:auto; background:#fff; border-radius:14px; padding:.7rem 1.2rem; box-shadow:0 8px 0 rgba(0,0,0,.12);}
.st-key-who_cta a p{color:#0B7A6B; font-weight:700;}
.exp{display:inline-block; margin-left:.5rem; font-size:.72rem; font-weight:700; padding:.2rem .6rem; border-radius:99px; background:#EFE6FF; color:#5B3FD6; vertical-align:middle;}
.pcs{display:grid; grid-template-columns:repeat(2,1fr); gap:1rem; margin-top:.6rem;} @media (max-width:900px){.pcs{grid-template-columns:1fr;}}
.pc{background:#fff; border:1px solid var(--line); border-top:6px solid #F5A623; border-radius:18px; padding:1rem 1.1rem; box-shadow:0 8px 20px rgba(18,49,58,.07); transition:transform .3s;}
.pc:hover{transform:translateY(-4px);} .pc.urgent{border-top-color:#E5484D; background:#FFF8F7;} .pc.note{border-top-color:#3B9DF8;}
.pc b{display:block; font-family:'Poppins',sans-serif; margin-bottom:.3rem; color:var(--navy);} .pc p{margin:0 0 .5rem; font-size:.9rem; line-height:1.55; color:var(--ink);}
.pc .basis{display:inline-block; font-size:.74rem; font-weight:700; background:#FFF0CF; color:#8A5A00; padding:.2rem .6rem; border-radius:99px;}
.pg-h{font-weight:700; margin:1rem 0 .2rem; color:var(--navy);}
.hb3{display:grid; grid-template-columns:repeat(3,1fr); gap:.9rem; margin-top:.8rem;} @media (max-width:900px){.hb3{grid-template-columns:1fr;}}
.hb{border-radius:18px; padding:1rem 1.1rem;} .hb h4{margin:0 0 .5rem; font-family:'Poppins',sans-serif; font-size:1rem;} .hb ul{margin:0; padding-left:1.1rem;} .hb li{margin-bottom:.4rem; font-size:.9rem; line-height:1.5;}
.hb.do{background:#E3F8EE; color:#0F5B3A;} .hb.eat{background:#E5EEFF; color:#1F3F8F;} .hb.lim{background:#FFEFD9; color:#7A4300;}
.notice{background:#FFF8E1; border:1px solid #F3E0A3; color:#6B5300; border-radius:16px; padding:.8rem 1rem; font-size:.9rem; margin-bottom:.8rem;}
.alertb.small{margin:.4rem 0 .8rem;}
</style>
"""

FORMAT_CSS = """
<style>
.st-key-fmt_m button, .st-key-fmt_p button, .st-key-fmt_i button, .st-key-fmt_m_on button, .st-key-fmt_p_on button, .st-key-fmt_i_on button{
  position:relative; display:flex !important; flex-direction:column; align-items:flex-start !important; justify-content:flex-start !important;
  min-height:136px; height:auto; width:100%; padding:1rem 1.1rem !important; border:2px solid var(--line) !important; border-radius:20px !important;
  background:#fff !important; text-align:left; box-shadow:0 8px 18px rgba(18,49,58,.07) !important;}
.st-key-fmt_m button:hover, .st-key-fmt_p button:hover, .st-key-fmt_i button:hover{border-color:var(--teal) !important;}
.st-key-fmt_m button p, .st-key-fmt_p button p, .st-key-fmt_i button p, .st-key-fmt_m_on button p, .st-key-fmt_p_on button p, .st-key-fmt_i_on button p{
  font-weight:700; font-size:1.02rem; color:var(--navy); text-align:left;}
[class*="st-key-fmt_"] button > div, [class*="st-key-fmt_"] button [data-testid="stMarkdownContainer"]{width:100%; text-align:left !important; justify-content:flex-start !important;}
[class*="st-key-fmt_"] button p{text-align:left !important;}
[class*="st-key-fmt_"] button::before{display:grid; place-items:center; width:46px; height:46px; border-radius:14px; font-size:1.45rem; margin-bottom:.7rem;}
[class*="st-key-fmt_"] button::after{font-size:.82rem; font-weight:500; color:var(--muted); margin-top:.15rem; text-align:left;}
.st-key-fmt_m button::before, .st-key-fmt_m_on button::before{content:"✍️"; background:#FFF0C7;}
.st-key-fmt_p button::before, .st-key-fmt_p_on button::before{content:"📄"; background:#FFE0E0;}
.st-key-fmt_i button::before, .st-key-fmt_i_on button::before{content:"🖼️"; background:#D9F5EE;}
.st-key-fmt_m button::after, .st-key-fmt_m_on button::after{content:@@M@@;}
.st-key-fmt_p button::after, .st-key-fmt_p_on button::after{content:@@P@@;}
.st-key-fmt_i button::after, .st-key-fmt_i_on button::after{content:@@I@@;}
[class*="st-key-fmt_"] button [data-testid="stMarkdownContainer"]::after{content:""; position:absolute; top:14px; right:14px; width:24px; height:24px; border-radius:50%; border:2px solid #C5E3DD; background:#fff;}
[class*="st-key-fmt_"][class*="_on"] button{border-color:var(--teal) !important; background:linear-gradient(180deg,#F3FFFB,#fff) !important;
  box-shadow:0 0 0 5px rgba(15,157,138,.12), 0 16px 30px rgba(15,157,138,.2) !important;}
[class*="st-key-fmt_"][class*="_on"] button [data-testid="stMarkdownContainer"]::after{content:"✓"; background:var(--teal); border-color:var(--teal); color:#fff; display:grid; place-items:center; font-size:.85rem; font-weight:800;}
.st-key-dz [data-testid="stFileUploaderDropzone"]{flex-direction:column; align-items:center; justify-content:center; gap:.5rem; text-align:center; padding:1.6rem 1rem 1.2rem;
  border:2px dashed #6FD3C3; border-radius:22px; background:linear-gradient(135deg,#F0FFFB,#EAF4FF);}
.st-key-dz [data-testid="stFileUploaderDropzoneInstructions"]{display:none;}
.st-key-dz [data-testid="stFileUploaderDropzone"]::before{content:@@ICON@@; display:grid; place-items:center; width:64px; height:64px; border-radius:50%; font-size:1.8rem; color:#fff;
  background:linear-gradient(135deg,#14C4A5,#2B7FF0); box-shadow:0 10px 22px rgba(43,127,240,.35);}
.st-key-dz [data-testid="stFileUploaderDropzone"]::after{content:@@TITLE@@; order:2; font-weight:700; font-size:1.02rem; color:var(--navy); max-width:28rem;}
.st-key-dz [data-testid="stFileUploaderDropzone"] button{order:3; font-size:0 !important; padding:.5rem 1.2rem; border-radius:12px;}
.st-key-dz [data-testid="stFileUploaderDropzone"] button::after{content:@@BROWSE@@; font-size:.92rem; font-weight:700;}
.dz-sub{text-align:center; color:var(--muted); font-size:.88rem; margin:.5rem 0 .3rem;}
.dz-lim{display:table; margin:0 auto .5rem; background:#fff; border:1px solid var(--line); color:var(--teal-d); border-radius:99px; padding:.25rem .9rem; font-size:.8rem; font-weight:700;}
.st-key-go_cta button{height:3.5rem; border-radius:18px !important; margin-top:.6rem;}
.st-key-go_cta button p{font-size:1.15rem !important; font-weight:700 !important; color:#fff;}
.mh{display:grid; grid-template-columns:3.2fr 1.2fr 1.2fr 1.2fr 1.2fr .6fr; gap:.5rem; font-size:.8rem; font-weight:700; color:var(--muted); margin-bottom:.2rem;}
</style>
"""


DOCTOR_CSS = """
<style>
.dr-top{display:flex; align-items:center; gap:1rem; margin:.2rem 0 1rem;}
.dr-top .pic{width:64px; height:64px; border-radius:20px; display:grid; place-items:center; font-size:2rem; color:#fff; background:linear-gradient(135deg,#14C4A5,#2B7FF0); box-shadow:0 7px 0 #0B7A6B, 0 16px 28px rgba(15,157,138,.3);}
.dr-top h1{font-family:'Poppins',sans-serif; font-weight:800; font-size:2.3rem; margin:0; color:var(--navy);} .dr-top p{margin:0; color:var(--muted);}
.dr-ok{margin-top:.6rem; background:#DDF7EC; color:#0F6B43; border:1px solid #BDEBD7; padding:.6rem .9rem; border-radius:14px; font-weight:700; font-size:.9rem;}
.dr-hint{margin-top:.6rem; color:#8A5A00; font-size:.88rem;}
.dr-rep{background:linear-gradient(135deg,#E6FAF1,#E2F2FF); border:1px solid #BDEBD7; border-radius:20px; padding:1rem 1.2rem; margin:.4rem 0 .6rem; color:#0F5B3A;}
.fcs{display:flex; flex-wrap:wrap; gap:.4rem; margin-top:.6rem;}
.fc{display:inline-block; background:#fff; border:1px solid #F3C6C3; color:#9D1C20; font-size:.78rem; font-weight:700; padding:.25rem .7rem; border-radius:99px;}
.fc.red{background:#FFE6E1; border-color:#FFD1C8;}
.dr-note{display:flex; gap:.8rem; align-items:center; background:linear-gradient(135deg,#EAF1FF,#E2F2FF); border:1px solid #CFE0F7; border-radius:18px; padding:.9rem 1.1rem; color:#1F3F66; margin:.2rem 0 .5rem;}
.ni{display:inline-grid; place-items:center; width:38px; height:38px; border-radius:12px; background:#fff; font-size:1.15rem; flex:0 0 38px; box-shadow:0 4px 10px rgba(18,49,58,.08);}
.spg{display:grid; grid-template-columns:repeat(2,1fr); gap:1rem; margin-top:.5rem;} @media (max-width:900px){.spg{grid-template-columns:1fr;}}
.spc{position:relative; overflow:hidden; background:#fff; border:1px solid var(--line); border-radius:24px; padding:1.2rem 1.3rem; box-shadow:var(--shadow-3d); transition:transform .3s; animation:fadeUp .6s backwards;}
.spc:hover{transform:translateY(-6px); box-shadow:var(--shadow-hover);} .spc.plain{box-shadow:none; border:none; padding:.4rem 0;}
.spc::after{content:""; position:absolute; right:-40px; top:-40px; width:130px; height:130px; border-radius:50%; background:rgba(15,157,138,.07);}
.sph{display:flex; align-items:center; gap:.8rem; margin-bottom:.5rem; position:relative; z-index:1;} .sph h3{font-family:'Poppins',sans-serif; font-size:1.08rem; margin:0; color:var(--navy);}
.spi{width:46px; height:46px; border-radius:14px; display:grid; place-items:center; font-size:1.4rem; flex:0 0 46px;}
.spc p{color:var(--muted); font-size:.92rem; line-height:1.55; margin:.2rem 0 .6rem;}
.bc{margin:.4rem 0;} .bc .fc{margin:.15rem .25rem .15rem 0;}
.near{display:inline-block; border:1px solid #BDEBD7; color:#0B7A6B; background:#F2FFFA; border-radius:99px; padding:.25rem .8rem; font-size:.8rem; font-weight:700; margin:.4rem 0;}
.lbs{display:flex; flex-direction:column; align-items:flex-start; gap:.45rem; margin-top:.7rem;}
a.lb, span.lb{display:inline-block; text-decoration:none !important; border:1px solid var(--line); background:#fff; color:#0B7A6B !important; font-weight:700; font-size:.88rem; padding:.5rem .95rem; border-radius:12px; transition:transform .2s, box-shadow .2s;}
a.lb:hover{transform:translateY(-3px); box-shadow:0 10px 18px rgba(15,157,138,.2);} a.lb.pri{background:linear-gradient(135deg,#14C4A5,#2B7FF0); color:#fff !important; border:none; box-shadow:0 5px 0 #0B7A6B;}
span.lb.off{opacity:.45; background:#F3F6F7; color:#6B7F88 !important;}
.doc{background:#fff; border:1px solid var(--line); border-radius:22px; padding:1.1rem 1.3rem .8rem; margin-bottom:.9rem; box-shadow:var(--shadow-3d); display:grid; grid-template-columns:1.6fr 1.2fr auto; gap:1rem; align-items:start; transition:transform .3s; animation:fadeUp .5s backwards;}
.doc:hover{transform:translateY(-4px);} @media (max-width:900px){.doc{grid-template-columns:1fr;}}
.dmain{display:flex; gap:.9rem;} .av{flex:0 0 54px; width:54px; height:54px; border-radius:50%; display:grid; place-items:center; color:#fff; font-weight:800; font-size:1.1rem; background:linear-gradient(135deg,#14C4A5,#2B7FF0); box-shadow:0 8px 16px rgba(43,127,240,.3);}
.dn{font-family:'Poppins',sans-serif; font-weight:700; font-size:1.08rem; color:var(--navy);} .dsp{display:inline-block; background:#D9F5EE; color:#0B7A6B; font-size:.75rem; font-weight:700; padding:.15rem .6rem; border-radius:99px; margin:.2rem 0;}
.dq{font-weight:600; font-size:.88rem; color:var(--ink);} .dm{font-size:.84rem; color:var(--muted);}
.dchips{display:flex; flex-direction:column; gap:.45rem;} .dchip{background:#F1F8F7; border-radius:12px; padding:.5rem .8rem; font-size:.86rem; color:var(--ink);} .dchip.tel{color:#0B7A6B; font-weight:700;}
.dbtn{display:flex; flex-direction:column; gap:.4rem; min-width:128px;} .dbtn a.lb{text-align:center;}
.dfoot{grid-column:1/-1; border-top:1px dashed var(--line); padding-top:.6rem; font-size:.78rem; color:var(--muted);}
.tipg{display:grid; grid-template-columns:repeat(2,1fr); gap:.9rem;} @media (max-width:800px){.tipg{grid-template-columns:1fr;}}
.tip{display:flex; gap:.8rem; align-items:flex-start; border-radius:18px; padding:1rem 1.1rem; border:1px solid rgba(18,49,58,.06);} .tip p{margin:0; font-size:.9rem; line-height:1.55; color:var(--ink);}
.st-key-dcard{padding-top:1.6rem;}
</style>
"""


def _q(text):
    return json.dumps(text, ensure_ascii=False)


def inject_page_css():
    st.markdown(BASE, unsafe_allow_html=True)
    st.markdown(DOCTOR_CSS, unsafe_allow_html=True)
    mode = st.session_state.get("ip_mode", "m")
    icon = {"p": "📄", "i": "🖼️"}.get(mode, "📄")
    css = (FORMAT_CSS.replace("@@M@@", _q(t("ip.fmt_m_s"))).replace("@@P@@", _q(t("ip.fmt_p_s")))
           .replace("@@I@@", _q(t("ip.fmt_i_s"))).replace("@@ICON@@", _q(icon))
           .replace("@@TITLE@@", _q(t("ip.drop_t_img" if mode == "i" else "ip.drop_t_pdf")))
           .replace("@@BROWSE@@", _q(t("ip.browse"))))
    st.markdown(css, unsafe_allow_html=True)
