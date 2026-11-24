"""Loading cards for MediLens AI.

    with loading(steps, icon) as step:            # shows the card while the block runs (no cancel button)
        step(2)
    status, value = run_cancellable(steps, work)  # runs work(progress) in the background, with a Cancel (X) button
    celebrate(title, subtitle)                    # a big animated tick that disappears by itself

steps = [(title, subtitle, percent[, icon]), ...]
"""
import contextlib
import html
import math
import threading
import time

import streamlit as st

from i18n import t

TIPS = ["ld.tip1", "ld.tip2", "ld.tip3", "ld.tip4", "ld.tip5", "ld.tip6"]
TIP_SECONDS = 5

T = 'stroke="#0F9D8A" stroke-width="3.5" fill="none" stroke-linecap="round" stroke-linejoin="round"'
B = 'stroke="#3B7CC0" stroke-width="3.5" fill="none" stroke-linecap="round" stroke-linejoin="round"'
G = 'stroke="#C3D8D4" stroke-width="4" stroke-linecap="round"'
ICONS = {
    "doc": f'<rect x="34" y="24" width="32" height="52" rx="7" {T}/><line x1="41" y1="38" x2="59" y2="38" {G}/><line x1="41" y1="48" x2="54" y2="48" {G}/>'
           f'<line x1="41" y1="58" x2="59" y2="58" {G}/><line x1="41" y1="68" x2="51" y2="68" {G}/>'
           '<rect class="ldr-scan" x="29" y="46" width="42" height="5" rx="2.5" fill="#3B7CC0"/>',
    "search": f'<rect x="28" y="22" width="34" height="52" rx="7" {T}/><line x1="35" y1="36" x2="55" y2="36" {G}/><line x1="35" y1="46" x2="50" y2="46" {G}/>'
              f'<line x1="35" y1="56" x2="55" y2="56" {G}/><g class="ldr-glass"><circle cx="62" cy="62" r="12" fill="rgba(255,255,255,.7)" {B}/>'
              f'<line x1="71" y1="71" x2="80" y2="80" {B}/></g>',
    "shield": f'<g class="ldr-pulse"><path d="M50 22 L74 31 V50 C74 65 63 73 50 79 C37 73 26 65 26 50 V31 Z" {T}/></g>'
              f'<path class="ldr-tick" d="M38 50 L47 59 L63 41" {B}/>',
    "pen": f'<rect x="28" y="24" width="38" height="52" rx="7" {T}/><line class="ldr-wl a" x1="35" y1="38" x2="59" y2="38" {G}/>'
           f'<line class="ldr-wl b" x1="35" y1="48" x2="55" y2="48" {G}/><line class="ldr-wl c" x1="35" y1="58" x2="59" y2="58" {G}/>'
           '<g class="ldr-pencil"><path d="M62 74 l6 -16 l8 6 z" fill="#3B7CC0"/><path d="M68 58 l8 6 l4 -5 l-8 -6 z" fill="#0F9D8A"/></g>',
    "chart": f'<line x1="26" y1="76" x2="74" y2="76" {G}/><rect class="ldr-b1" x="30" y="46" width="11" height="30" rx="3" fill="#0F9D8A"/>'
             '<rect class="ldr-b2" x="45" y="32" width="11" height="44" rx="3" fill="#3B7CC0"/><rect class="ldr-b3" x="60" y="40" width="11" height="36" rx="3" fill="#14C4A5"/>',
    "lock": f'<g class="ldr-pulse"><rect x="33" y="46" width="34" height="28" rx="6" {T}/><path d="M40 46 v-9 a10 10 0 0 1 20 0 v9" {T}/>'
            '<circle cx="50" cy="60" r="3.2" fill="#3B7CC0"/></g>',
    "user": f'<g class="ldr-pulse"><circle cx="50" cy="40" r="11" {T}/><path d="M29 74 a21 19 0 0 1 42 0" {T}/></g>',
    "save": f'<g class="ldr-pulse"><rect x="30" y="28" width="40" height="44" rx="6" {T}/><rect x="38" y="28" width="22" height="13" {T}/>'
            f'<rect x="38" y="54" width="24" height="18" rx="2" {T}/></g>',
    "globe": f'<g class="ldr-pulse"><circle cx="50" cy="50" r="23" {T}/><ellipse class="ldr-turn" cx="50" cy="50" rx="10" ry="23" {T}/><line x1="27" y1="50" x2="73" y2="50" {T}/></g>',
    "trash": f'<g class="ldr-pulse"><path d="M34 36 h32 M44 36 v-6 h12 v6 M37 36 l3 38 h20 l3 -38" {T}/></g>',
}

CSS = """
<style>
[class*="st-key-ldr_back"]{position:fixed !important; inset:0; z-index:100000; width:100vw !important; height:100vh !important; display:flex !important;
  flex-direction:column !important; align-items:center !important; justify-content:center !important; gap:0 !important;
  background:rgba(20,52,58,.55); backdrop-filter:blur(7px); -webkit-backdrop-filter:blur(7px); animation:ldrfade .25s both; padding:0; margin:0;}
[class*="st-key-ldr_wrap"]{position:relative; margin:0 auto !important; width:min(92vw,430px) !important; background:#fff; border-radius:30px; padding:1.5rem 2rem 1.3rem; gap:0 !important;
  box-shadow:0 30px 80px rgba(0,0,0,.35); animation:ldrpop .35s cubic-bezier(.2,.8,.2,1) both;}
[class*="st-key-ldr_x"]{position:absolute !important; top:12px; right:14px; z-index:5; width:auto !important;}
[class*="st-key-ldr_x"] button{width:38px; height:38px; min-height:0; padding:0; border-radius:50% !important; border:1px solid #E3EEEC !important;
  background:#F4F8F8 !important; color:#5C7480 !important; box-shadow:none !important; font-size:1.1rem;}
[class*="st-key-ldr_x"] button:hover{background:#FDE0E1 !important; color:#B3261E !important; transform:rotate(90deg) scale(1.05);}
.ldr-vis{position:relative; width:210px; height:210px; margin:0 auto .6rem;}
.ldr-vis svg{position:absolute; inset:0; width:100%; height:100%;}
.ldr-ring{animation:ldrspin 1.4s linear infinite; transform-origin:50% 50%;}
.ldr-ring2{animation:ldrspin 2.6s linear infinite reverse; transform-origin:50% 50%;}
.ldr-bg{position:absolute; inset:14px; border-radius:50%; background:radial-gradient(circle,#F3FAF9 0%,#E6F2F1 100%);}
.ldr-scan{animation:ldrscan 1.5s ease-in-out infinite alternate;}
.ldr-glass{animation:ldrglass 2s ease-in-out infinite alternate;}
.ldr-tick{stroke-dasharray:50; animation:ldrtick 1.6s ease-in-out infinite;}
.ldr-wl{transform-box:fill-box; transform-origin:left center; animation:ldrwrite 2.4s ease-in-out infinite;} .ldr-wl.b{animation-delay:.5s} .ldr-wl.c{animation-delay:1s}
.ldr-pencil{animation:ldrpencil 2.4s ease-in-out infinite;}
.ldr-b1,.ldr-b2,.ldr-b3{transform-box:fill-box; transform-origin:bottom; animation:ldrbar 1.6s ease-in-out infinite;} .ldr-b2{animation-delay:.2s} .ldr-b3{animation-delay:.4s}
.ldr-pulse{animation:ldrpulse 1.4s ease-in-out infinite; transform-box:fill-box; transform-origin:center;}
.ldr-turn{transform-box:fill-box; transform-origin:center; animation:ldrturn 2.4s ease-in-out infinite;}
.ldr-t{font-family:'Poppins','Inter',sans-serif; font-weight:700; font-size:1.2rem; color:#12313A; margin:.2rem 0 .35rem; text-align:center;}
.ldr-s{color:#5C7480; font-size:.95rem; line-height:1.55; margin:0 auto .8rem; max-width:21rem; text-align:center;}
.ldr-steps{display:flex; justify-content:center; gap:.45rem; margin:.2rem 0 1rem;}
.ldr-steps i{width:26px; height:26px; border-radius:50%; display:grid; place-items:center; font-style:normal; font-size:.7rem; font-weight:800; background:#E3ECEB; color:#8AA0A8;}
.ldr-steps i.done{background:#0F9D8A; color:#fff;} .ldr-steps i.now{background:#fff; color:#0F9D8A; box-shadow:0 0 0 3px #0F9D8A; animation:ldrpulse 1.2s ease-in-out infinite;}
.ldr-bar{height:11px; border-radius:99px; background:#DCE7E5; overflow:hidden; margin-top:.6rem;}
.ldr-bar i{position:relative; display:block; height:100%; border-radius:99px; background:linear-gradient(90deg,#0F9D8A,#1B6FB5); overflow:hidden;}
.ldr-bar i::after{content:""; position:absolute; inset:0; background:linear-gradient(90deg,transparent,rgba(255,255,255,.55),transparent); animation:ldrshine 1.2s linear infinite;}
.ldr-row{display:flex; justify-content:space-between; margin-top:.55rem; font-size:.88rem; color:#5C7480;}
.ldr-tips{position:relative; height:5.1rem; margin-top:1rem; padding:.7rem .9rem; border-radius:16px; background:linear-gradient(135deg,#E8F7F3,#E8F1FD); overflow:hidden;}
.ldr-tips b{display:block; font-size:.72rem; letter-spacing:.12em; text-transform:uppercase; color:#0B7A6B; margin-bottom:.2rem;}
.ldr-tips span{position:absolute; left:.9rem; right:.9rem; top:1.75rem; font-size:.84rem; line-height:1.4; color:#1F3A44; opacity:0;}
.done-ring{stroke-dasharray:210; stroke-dashoffset:210; animation:ldrdraw .7s ease-out .1s forwards;}
.done-tick{stroke-dasharray:60; stroke-dashoffset:60; animation:ldrdraw .5s ease-out .65s forwards;}
.done-pop{animation:ldrbounce .6s cubic-bezier(.2,1.4,.4,1) both;}
.ldr-conf{position:absolute; inset:0; pointer-events:none;} .ldr-conf s{position:absolute; left:50%; top:46%; width:9px; height:9px; border-radius:2px; opacity:0; animation:ldrconf 1.3s ease-out .55s forwards;}
@keyframes ldrfade{from{opacity:0} to{opacity:1}}
@keyframes ldrpop{from{opacity:0; transform:translateY(18px) scale(.96)} to{opacity:1; transform:none}}
@keyframes ldrspin{to{transform:rotate(360deg)}}
@keyframes ldrscan{from{transform:translateY(-22px)} to{transform:translateY(24px)}}
@keyframes ldrglass{from{transform:translate(-26px,-30px)} to{transform:translate(2px,2px)}}
@keyframes ldrtick{0%{stroke-dashoffset:50} 50%,80%{stroke-dashoffset:0} 100%{stroke-dashoffset:-50}}
@keyframes ldrwrite{0%{transform:scaleX(0)} 45%,100%{transform:scaleX(1)}}
@keyframes ldrpencil{0%{transform:translate(-26px,-30px)} 20%{transform:translate(-4px,-30px)} 45%{transform:translate(-14px,-20px)} 70%{transform:translate(-4px,-10px)} 100%{transform:translate(-26px,-30px)}}
@keyframes ldrbar{0%,100%{transform:scaleY(.35)} 50%{transform:scaleY(1)}}
@keyframes ldrpulse{0%,100%{transform:scale(1)} 50%{transform:scale(1.08)}}
@keyframes ldrturn{0%,100%{transform:scaleX(1)} 50%{transform:scaleX(.15)}}
@keyframes ldrshine{from{transform:translateX(-100%)} to{transform:translateX(100%)}}
@keyframes ldrdraw{to{stroke-dashoffset:0}}
@keyframes ldrbounce{from{transform:scale(.3); opacity:0} to{transform:scale(1); opacity:1}}
@keyframes ldrconf{0%{opacity:1; transform:translate(0,0) rotate(0)} 100%{opacity:0; transform:translate(var(--x),var(--y)) rotate(260deg)}}
@media (prefers-reduced-motion: reduce){.ldr-pulse,.ldr-bar i::after,.ldr-conf s{animation:none !important;}}
</style>
"""

_COLORS = ["#0F9D8A", "#1B6FB5", "#F5A623", "#E5484D", "#6C5CE7", "#2FBF71"]


def _tips_html():
    n = len(TIPS)
    total = n * TIP_SECONDS
    show = 100 / n
    keyframes = (f"@keyframes ldrtip{{0%{{opacity:0;transform:translateY(6px)}} 2%,{show - 2.2:.2f}%{{opacity:1;transform:none}} "
                 f"{show - 0.4:.2f}%,100%{{opacity:0}}}}")
    spans = "".join(f'<span style="animation:ldrtip {total}s infinite {i * TIP_SECONDS}s">{html.escape(t(k))}</span>' for i, k in enumerate(TIPS))
    return f'<style>{keyframes}</style><div class="ldr-tips"><b>💡 {html.escape(t("ld.tip_h"))}</b>{spans}</div>'


def _vis(steps, step, icon):
    title, sub = steps[step - 1][0], steps[step - 1][1]
    icon = steps[step - 1][3] if len(steps[step - 1]) > 3 else icon
    ring = ('<svg viewBox="0 0 140 140"><circle cx="70" cy="70" r="62" fill="none" stroke="#DCE7E5" stroke-width="4"/>'
            '<g class="ldr-ring"><circle cx="70" cy="70" r="62" fill="none" stroke="#0F9D8A" stroke-width="4" stroke-linecap="round" stroke-dasharray="150 390" transform="rotate(-100 70 70)"/>'
            '<circle cx="70" cy="70" r="62" fill="none" stroke="#1B6FB5" stroke-width="4" stroke-linecap="round" stroke-dasharray="70 390" stroke-dashoffset="-190" transform="rotate(-100 70 70)"/></g></svg>'
            '<svg viewBox="0 0 140 140"><g class="ldr-ring2"><circle cx="70" cy="70" r="53" fill="none" stroke="#A9D8D1" stroke-width="2" stroke-linecap="round" stroke-dasharray="28 305"/></g></svg>')
    dots = ""
    if len(steps) > 1:
        dots = '<div class="ldr-steps">' + "".join(
            f'<i class="{"done" if k < step else "now" if k == step else ""}">{"✓" if k < step else k}</i>' for k in range(1, len(steps) + 1)) + "</div>"
    return (f'<div class="ldr-vis"><div class="ldr-bg"></div>{ring}<svg viewBox="0 0 100 100">{ICONS.get(icon, ICONS["doc"])}</svg></div>'
            f'<div class="ldr-t">{html.escape(title)}</div><div class="ldr-s">{html.escape(sub)}</div>{dots}')


def _dyn(step, total, pct):
    return (f'<div class="ldr-bar"><i style="width:{pct}%"></i></div>'
            f'<div class="ldr-row"><b>{html.escape(t("ld.step", n=step, total=total))}</b><b>{pct}%</b></div>')


def _counter():
    n = st.session_state.get("_ldr_n", 0) + 1
    st.session_state["_ldr_n"] = n
    return n


def _mark_cancelled():
    st.session_state["ld_cancelled"] = True


def pop_cancelled():
    """True once after the user pressed the X on a loading card."""
    return bool(st.session_state.pop("ld_cancelled", False))


@contextlib.contextmanager
def _card(steps, icon, cancellable):
    n = _counter()
    holder = st.empty()
    with holder.container(key=f"ldr_back_{n}"):
        st.markdown(CSS, unsafe_allow_html=True)
        with st.container(key=f"ldr_wrap_{n}"):
            vis, dyn, tips = st.empty(), st.empty(), st.empty()
            if cancellable:
                with st.container(key=f"ldr_x_{n}"):
                    st.button("✕", key=f"ldr_cancel_{n}", help=t("ld.cancel"), on_click=_mark_cancelled)
            tips.markdown(_tips_html(), unsafe_allow_html=True)
    try:
        yield vis, dyn
    finally:
        try:
            holder.empty()
        except BaseException:
            pass


@contextlib.contextmanager
def loading(steps, icon="doc"):
    """A card while the block runs. step(n) moves to step n. No cancel button (the work runs in the main thread)."""
    total = len(steps)
    with _card(steps, icon, False) as (vis, dyn):
        def step(n):
            n = max(1, min(total, n))
            vis.markdown(_vis(steps, n, icon), unsafe_allow_html=True)
            dyn.markdown(_dyn(n, total, steps[n - 1][2]), unsafe_allow_html=True)

        step(1)
        yield step


def simple(title_key, sub_key, icon, **fmt):
    """A one-step card with translated text."""
    return loading([(t(title_key, **fmt), t(sub_key, **fmt), 60)], icon)


def run_cancellable(steps, work, icon="doc"):
    """Runs work(progress) in a background thread. progress(step, fraction=None) moves the card forward.
    Returns ('done', value), ('error', exception) or ('cancelled', None). Pressing X stops waiting at once.
    work() must not use st.* or st.session_state."""
    total = len(steps)
    state = {"step": 1, "frac": None, "t0": time.time(), "result": None, "error": None, "done": False}

    def progress(step, fraction=None):
        if step != state["step"]:
            state["t0"] = time.time()
        state["step"], state["frac"] = step, fraction

    def runner():
        try:
            state["result"] = work(progress)
        except BaseException as e:  # noqa: BLE001 - handed back to the caller
            state["error"] = e
        finally:
            state["done"] = True

    with _card(steps, icon, True) as (vis, dyn):
        threading.Thread(target=runner, daemon=True).start()
        shown, last = 0, None
        while not state["done"]:
            step = max(1, min(total, state["step"]))
            if step != shown:
                vis.markdown(_vis(steps, step, icon), unsafe_allow_html=True)
                shown = step
            cur = steps[step - 1][2]
            nxt = steps[step][2] if step < total else 99
            if state["frac"] is not None:
                pct = int(cur + (nxt - cur - 1) * min(1.0, state["frac"]))
            else:  # no real progress known: ease towards the next point, never reaching it
                pct = int(cur + (nxt - cur - 1) * 0.95 * (1 - math.exp(-(time.time() - state["t0"]) / 12.0)))
            if (step, pct) != last:
                dyn.markdown(_dyn(step, total, pct), unsafe_allow_html=True)
                last = (step, pct)
            time.sleep(0.25)  # each pass is also a point where the script can be stopped by the X button
    if state["error"] is not None:
        return "error", state["error"]
    return "done", state["result"]


def celebrate(title, subtitle="", seconds=1.7):
    """A full-screen success card with an animated tick. It disappears by itself."""
    n = _counter()
    holder = st.empty()
    confetti = "".join(
        f'<s style="background:{_COLORS[i % len(_COLORS)]};--x:{int(110 * math.cos(i * 0.5236))}px;--y:{int(110 * math.sin(i * 0.5236)) - 20}px"></s>' for i in range(12))
    card = (f'{CSS}<div class="done-card" style="text-align:center">'
            '<div class="ldr-vis" style="width:170px;height:170px"><div class="ldr-bg" style="background:radial-gradient(circle,#EAFBF2,#D8F5E6)"></div>'
            '<svg viewBox="0 0 100 100" class="done-pop"><circle class="done-ring" cx="50" cy="50" r="33" fill="none" stroke="#12A560" stroke-width="5" stroke-linecap="round" transform="rotate(-90 50 50)"/>'
            '<path class="done-tick" d="M35 51 L46 62 L66 38" fill="none" stroke="#12A560" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/></svg>'
            f'<div class="ldr-conf">{confetti}</div></div>'
            f'<div class="ldr-t">{html.escape(title)}</div><div class="ldr-s" style="margin-bottom:.2rem">{html.escape(subtitle)}</div></div>')
    with holder.container(key=f"ldr_back_{n}"):
        with st.container(key=f"ldr_wrap_{n}"):
            st.markdown(card, unsafe_allow_html=True)
    time.sleep(seconds)
    try:
        holder.empty()
    except BaseException:
        pass
