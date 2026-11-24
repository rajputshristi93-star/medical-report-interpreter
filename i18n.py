"""Languages for MediLens AI.

* t(key)            fixed interface text. English and Hindi are written by hand. Other languages are read from
                    translations/<code>.json (made by build_translations.py) and fall back to English.
* localize(texts)   translates report-dependent text (patterns, tips, doctor advice) with the AI, in one batch,
                    and remembers the results so each sentence is translated only once per language.
* render_language_selector() puts the language box in the top bar and stores the choice in the session.
"""
import json
import re
from pathlib import Path

HERE = Path(__file__).parent
TR_DIR = HERE / "translations"

# code, native name, English name (used in AI prompts), right-to-left?
_L = [
    ("en", "English", "English", False), ("hi", "हिन्दी", "Hindi", False),
    # Indian languages (the 22 scheduled languages)
    ("as", "অসমীয়া", "Assamese", False), ("bn", "বাংলা", "Bengali", False), ("brx", "बड़ो", "Bodo", False),
    ("doi", "डोगरी", "Dogri", False), ("gu", "ગુજરાતી", "Gujarati", False), ("kn", "ಕನ್ನಡ", "Kannada", False),
    ("ks", "کٲشُر", "Kashmiri", True), ("kok", "कोंकणी", "Konkani", False), ("mai", "मैथिली", "Maithili", False),
    ("ml", "മലയാളം", "Malayalam", False), ("mni", "মৈতৈলোন্", "Manipuri (Meitei)", False),
    ("mr", "मराठी", "Marathi", False), ("ne", "नेपाली", "Nepali", False), ("or", "ଓଡ଼ିଆ", "Odia", False),
    ("pa", "ਪੰਜਾਬੀ", "Punjabi", False), ("sa", "संस्कृतम्", "Sanskrit", False), ("sat", "ᱥᱟᱱᱛᱟᱲᱤ", "Santali", False),
    ("sd", "سنڌي", "Sindhi", True), ("ta", "தமிழ்", "Tamil", False), ("te", "తెలుగు", "Telugu", False),
    ("ur", "اردو", "Urdu", True),
    # major world languages
    ("ar", "العربية", "Arabic", True), ("zh", "中文", "Simplified Chinese", False), ("nl", "Nederlands", "Dutch", False),
    ("fr", "Français", "French", False), ("de", "Deutsch", "German", False), ("id", "Bahasa Indonesia", "Indonesian", False),
    ("it", "Italiano", "Italian", False), ("ja", "日本語", "Japanese", False), ("ko", "한국어", "Korean", False),
    ("ms", "Bahasa Melayu", "Malay", False), ("fa", "فارسی", "Persian", True), ("pl", "Polski", "Polish", False),
    ("pt", "Português", "Portuguese", False), ("ru", "Русский", "Russian", False), ("es", "Español", "Spanish", False),
    ("sw", "Kiswahili", "Swahili", False), ("th", "ไทย", "Thai", False), ("tr", "Türkçe", "Turkish", False),
    ("vi", "Tiếng Việt", "Vietnamese", False),
]
LANGS = [dict(code=c, native=n, english=e, rtl=r) for c, n, e, r in _L]
BY_CODE = {l["code"]: l for l in LANGS}

EN = {
    "nav.home": "Home", "nav.interpreter": "Interpreter", "nav.reports": "My Reports", "nav.doctor": "Find a Doctor",
    "nav.admin": "Admin", "nav.account": "Account", "nav.signed_in": "Signed in as", "nav.logout": "Log out",
    "lang.label": "Language",
    "hero.eyebrow": "AI-assisted lab report explainer", "hero.title1": "Understand your lab results",
    "hero.title2": "in plain language",
    "hero.lead": "Upload a report, take a photo, or type your values. Get colour-coded results, simple charts and clear next steps you can take to your doctor.",
    "hero.cta1": "Interpret my report", "hero.cta2": "Find a doctor", "hero.card_title": "Blood test",
    "hero.example": "Example only", "ex.hb": "Hemoglobin", "ex.wbc": "White cells", "ex.plt": "Platelets",
    "ex.ldl": "LDL cholesterol",
    "status.low": "Low", "status.normal": "Normal", "status.high": "High", "status.unknown": "Unknown",
    "status.unverified": "Unverified",
    "how.eyebrow": "HOW IT WORKS", "how.title": "Three simple steps",
    "step1.title": "Add your report", "step1.text": "Upload a PDF or a photo, or type the values yourself. Files up to 10 MB.",
    "step2.title": "We read and check it", "step2.text": "The numbers are extracted and checked against the report. Anything unclear is marked, never guessed.",
    "step3.title": "Understand the result", "step3.text": "Colour-coded table, charts, a plain-language explanation and questions for your doctor.",
    "feat.eyebrow": "WHAT YOU GET", "feat.title": "Made to be clear and careful",
    "f1.title": "Colour-coded results", "f1.text": "Normal, low and high are easy to spot at a glance.",
    "f2.title": "Charts that explain", "f2.text": "See where each value sits inside its normal range.",
    "f3.title": "Plain language", "f3.text": "Short explanations of what flagged tests measure. No diagnosing.",
    "f4.title": "Healthy-habit tips", "f4.text": "What to do, eat more of and limit for your results.",
    "f5.title": "Find the right doctor", "f5.text": "Which specialist fits your report, and search links near you.",
    "f6.title": "Private by design", "f6.text": "Your file is never stored. Saving a report is always your choice.",
    "demo.eyebrow": "SEE IT IN ACTION", "demo.title": "What the charts look like",
    "demo.note": "Example data, not a real patient.",
    "faq.title": "Common questions",
    "faq1.q": "Does this diagnose anything?",
    "faq1.a": "No. It explains what the numbers mean in general terms. Only a doctor who knows your history can interpret them for you.",
    "faq2.q": "Is my report stored?",
    "faq2.a": "Your uploaded file is never stored. Results are saved only if you log in and choose Save to my account. The file or its extracted text is still sent to an AI service to produce the results.",
    "faq3.q": "Which files can I upload?",
    "faq3.a": "PDF, PNG or JPG up to 10 MB. Lab test results (blood, urine, lipid, thyroid and similar) are supported. X-ray, ultrasound and ECG reports are not yet.",
    "faq4.q": "How accurate is it?",
    "faq4.a": "It can make mistakes, especially with blurry photos. Always compare the values with your original report.",
    "footer.disclaimer": "Medical disclaimer: this app is for information only and does not provide medical advice, diagnosis, or treatment. It can make mistakes, so always check values against your original report and consult a qualified doctor.",
    "ch.eyebrow": "VISUAL SUMMARY", "ch.title": "Your results at a glance",
    "ch.tab1": "Overview", "ch.tab2": "Where your values sit", "ch.tab3": "Biggest gaps",
    "ch.cap1": "Each slice is a group of tests. The centre shows how many tests are inside their normal range.",
    "ch.cap2": "Green is the normal range printed on your report. The diamond is your value. Diamonds outside the green band are low or high.",
    "ch.cap3": "How far each out-of-range value is from its nearest limit. Longer bars are bigger gaps.",
    "ch.need_limits": "This chart needs tests that have both a low and a high limit.",
    "ch.no_gaps": "Nothing is outside its reference range, so there are no gaps to show.",
    "ch.in_range": "in range", "ch.axis_low": "LOW", "ch.axis_normal": "NORMAL RANGE", "ch.axis_high": "HIGH",
    "ch.gap_axis": "% outside the reference limit (left = below, right = above)",
}

HI = {
    "nav.home": "होम", "nav.interpreter": "रिपोर्ट समझें", "nav.reports": "मेरी रिपोर्ट", "nav.doctor": "डॉक्टर खोजें",
    "nav.admin": "एडमिन", "nav.account": "खाता", "nav.signed_in": "इस खाते से लॉग इन", "nav.logout": "लॉग आउट",
    "lang.label": "भाषा",
    "hero.eyebrow": "AI की मदद से लैब रिपोर्ट की व्याख्या", "hero.title1": "अपनी लैब रिपोर्ट को समझें",
    "hero.title2": "आसान भाषा में",
    "hero.lead": "रिपोर्ट अपलोड करें, फ़ोटो लें या अपने मान खुद लिखें। रंगों से दिखाए गए नतीजे, सरल चार्ट और डॉक्टर के पास ले जाने के लिए साफ़ अगले कदम पाएँ।",
    "hero.cta1": "मेरी रिपोर्ट समझें", "hero.cta2": "डॉक्टर खोजें", "hero.card_title": "ब्लड टेस्ट",
    "hero.example": "केवल उदाहरण", "ex.hb": "हीमोग्लोबिन", "ex.wbc": "सफ़ेद रक्त कोशिकाएँ", "ex.plt": "प्लेटलेट्स",
    "ex.ldl": "LDL कोलेस्ट्रॉल",
    "status.low": "कम", "status.normal": "सामान्य", "status.high": "अधिक", "status.unknown": "अज्ञात",
    "status.unverified": "असत्यापित",
    "how.eyebrow": "यह कैसे काम करता है", "how.title": "तीन आसान कदम",
    "step1.title": "अपनी रिपोर्ट जोड़ें", "step1.text": "PDF या फ़ोटो अपलोड करें, या मान खुद लिखें। फ़ाइल 10 MB तक।",
    "step2.title": "हम पढ़ते और जाँचते हैं", "step2.text": "संख्याएँ निकालकर रिपोर्ट से मिलाई जाती हैं। जो साफ़ नहीं है उसे चिह्नित किया जाता है, अंदाज़ा नहीं लगाया जाता।",
    "step3.title": "नतीजे को समझें", "step3.text": "रंगीन तालिका, चार्ट, आसान भाषा में व्याख्या और डॉक्टर से पूछने के सवाल।",
    "feat.eyebrow": "आपको क्या मिलता है", "feat.title": "साफ़ और सावधानी से बनाया गया",
    "f1.title": "रंगों में नतीजे", "f1.text": "सामान्य, कम और अधिक मान एक नज़र में दिख जाते हैं।",
    "f2.title": "समझाने वाले चार्ट", "f2.text": "देखें कि हर मान अपनी सामान्य सीमा में कहाँ है।",
    "f3.title": "आसान भाषा", "f3.text": "चिह्नित जाँचें क्या मापती हैं, इसकी छोटी व्याख्या। कोई निदान नहीं।",
    "f4.title": "स्वस्थ आदतों के सुझाव", "f4.text": "आपके नतीजों के लिए क्या करें, क्या ज़्यादा खाएँ और किससे बचें।",
    "f5.title": "सही डॉक्टर खोजें", "f5.text": "आपकी रिपोर्ट के लिए कौन-सा विशेषज्ञ उपयुक्त है, और आपके पास खोज के लिंक।",
    "f6.title": "गोपनीयता पहले", "f6.text": "आपकी फ़ाइल कभी सहेजी नहीं जाती। रिपोर्ट सहेजना हमेशा आपकी पसंद है।",
    "demo.eyebrow": "इसे काम करते देखें", "demo.title": "चार्ट कैसे दिखते हैं",
    "demo.note": "उदाहरण के आँकड़े, असली मरीज़ नहीं।",
    "faq.title": "आम सवाल",
    "faq1.q": "क्या यह कोई निदान करता है?",
    "faq1.a": "नहीं। यह सामान्य तौर पर बताता है कि संख्याओं का क्या मतलब है। केवल वही डॉक्टर इन्हें सही समझा सकता है जो आपका इतिहास जानता हो।",
    "faq2.q": "क्या मेरी रिपोर्ट सहेजी जाती है?",
    "faq2.a": "आपकी अपलोड की गई फ़ाइल कभी सहेजी नहीं जाती। नतीजे तभी सहेजे जाते हैं जब आप लॉग इन करके “मेरे खाते में सहेजें” चुनते हैं। नतीजे बनाने के लिए फ़ाइल या उससे निकला टेक्स्ट फिर भी एक AI सेवा को भेजा जाता है।",
    "faq3.q": "कौन-सी फ़ाइलें अपलोड कर सकते हैं?",
    "faq3.a": "PDF, PNG या JPG, 10 MB तक। लैब जाँच के नतीजे (खून, पेशाब, लिपिड, थायरॉइड आदि) समर्थित हैं। एक्स-रे, अल्ट्रासाउंड और ECG रिपोर्ट अभी नहीं।",
    "faq4.q": "यह कितना सटीक है?",
    "faq4.a": "इसमें गलतियाँ हो सकती हैं, खासकर धुंधली फ़ोटो में। हमेशा मानों को अपनी मूल रिपोर्ट से मिलाएँ।",
    "footer.disclaimer": "चिकित्सा अस्वीकरण: यह ऐप केवल जानकारी के लिए है और चिकित्सा सलाह, निदान या इलाज नहीं देता। इसमें गलतियाँ हो सकती हैं, इसलिए मानों को हमेशा अपनी मूल रिपोर्ट से मिलाएँ और योग्य डॉक्टर से सलाह लें।",
    "ch.eyebrow": "दृश्य सार", "ch.title": "आपके नतीजे एक नज़र में",
    "ch.tab1": "सारांश", "ch.tab2": "आपके मान कहाँ हैं", "ch.tab3": "सबसे बड़े अंतर",
    "ch.cap1": "हर हिस्सा जाँचों का एक समूह है। बीच में दिखता है कि कितनी जाँचें सामान्य सीमा के भीतर हैं।",
    "ch.cap2": "हरा हिस्सा आपकी रिपोर्ट में छपी सामान्य सीमा है। हीरा आपका मान है। हरे हिस्से के बाहर का हीरा कम या अधिक मान दिखाता है।",
    "ch.cap3": "सीमा से बाहर का हर मान अपनी नज़दीकी सीमा से कितना दूर है। जितनी लंबी पट्टी, उतना बड़ा अंतर।",
    "ch.need_limits": "इस चार्ट के लिए ऐसी जाँचें चाहिए जिनमें निचली और ऊपरी दोनों सीमाएँ हों।",
    "ch.no_gaps": "कोई भी मान अपनी सामान्य सीमा से बाहर नहीं है, इसलिए दिखाने के लिए कोई अंतर नहीं है।",
    "ch.in_range": "सीमा में", "ch.axis_low": "कम", "ch.axis_normal": "सामान्य सीमा", "ch.axis_high": "अधिक",
    "ch.gap_axis": "% संदर्भ सीमा से बाहर (बाएँ = नीचे, दाएँ = ऊपर)",
}

from strings_extra import EN_X, HI_X  # noqa: E402  (text of the Interpreter, doctor, login and reports pages)

EN.update(EN_X)
HI.update(HI_X)

_STATIC, _DYN = {}, {}


def current_lang():
    try:
        import streamlit as st
        code = st.session_state.get("lang", "en")
    except Exception:
        code = "en"
    return code if code in BY_CODE else "en"


def ai_language():
    return BY_CODE[current_lang()]["english"]


def is_rtl():
    return BY_CODE[current_lang()]["rtl"]


def _load_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return {}


def _static(code):
    if code not in _STATIC:
        _STATIC[code] = HI if code == "hi" else _load_json(TR_DIR / f"{code}.json")
    return _STATIC[code]


def t(key, **kw):
    """Fixed interface text in the chosen language. Falls back to English."""
    code = current_lang()
    text = (_static(code).get(key) if code != "en" else None) or EN.get(key, key)
    return text.format(**kw) if kw else text


def has_translation(code):
    return code == "en" or code == "hi" or (TR_DIR / f"{code}.json").exists()


# ---------------------------------------------------------------- dynamic text
def _parse_object(raw):
    raw = (raw or "").strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        m = re.search(r"\{.*\}", raw, re.S)
        try:
            return json.loads(m.group(0)) if m else {}
        except Exception:
            return {}


def _translate_into(cache, missing, code, step=None):
    from interpreter import ask_llm  # uses your Gemini / Groq setup
    language = BY_CODE[code]["english"]
    for i in range(0, len(missing), 25):
        if step:
            step(i // 25 + 1)
        part = missing[i:i + 25]
        payload = {str(n): s for n, s in enumerate(part)}
        prompt = (
            f"You are a careful medical translator. Translate every value of this JSON object from English into "
            f"{language}.\nRules: keep the meaning exact and simple; keep numbers, units, lab test names and "
            f"abbreviations (for example HbA1c, LDL, eGFR, mg/dL) unchanged; keep Markdown symbols and emojis; "
            f"do not add or remove advice. Return ONLY a JSON object with the same keys.\n\n"
            + json.dumps(payload, ensure_ascii=False)
        )
        got = _parse_object(ask_llm(prompt, json_mode=True))
        for n, s in enumerate(part):
            val = got.get(str(n))
            if isinstance(val, str) and val.strip():
                cache[s] = val.strip()


def localize(texts):
    """Returns {english text: translated text}. English, or any failure, returns the text unchanged."""
    uniq = list(dict.fromkeys(s for s in texts if isinstance(s, str) and s.strip()))
    code = current_lang()
    if code == "en" or not uniq:
        return {s: s for s in uniq}
    path = TR_DIR / "_dynamic" / f"{code}.json"
    if code not in _DYN:
        _DYN[code] = _load_json(path)
    cache = _DYN[code]
    missing = [s for s in uniq if s not in cache]
    if missing:
        try:
            from loader import loading
            n = -(-len(missing) // 25)
            steps = [(t("ld.tr_text"), t("ld.tr_text_s"), int(100 * (k + 1) / (n + 1))) for k in range(n)]
            with loading(steps, "globe") as step:
                _translate_into(cache, missing, code, step)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
        except Exception as e:
            print("localize failed:", str(e)[:150])
    return {s: cache.get(s, s) for s in uniq}


def translate_keys(keys, language):
    """Translates interface strings (by key) into a language with the AI. Returns {key: translation}."""
    from interpreter import ask_llm  # uses your Gemini / Groq setup

    payload = {k: EN[k] for k in keys}
    prompt = (
        f"You are a careful translator for a health information app. Translate every value of this JSON object "
        f"from English into {language}.\nRules: keep the meaning exact and simple; keep numbers, units, lab test names "
        f"and abbreviations (for example PDF, JPG, MB, LDL, ECG) unchanged; keep placeholders in curly braces such as "
        f"{{name}} or {{n}} exactly as they are; keep any emojis; use natural wording a local patient would understand. "
        f"Return ONLY a JSON object with the same keys.\n\n" + json.dumps(payload, ensure_ascii=False)
    )
    got = _parse_object(ask_llm(prompt, json_mode=True))
    out = {}
    for k, v in got.items():
        if k in payload and isinstance(v, str) and v.strip():
            # a translation must keep every placeholder of the English text, otherwise it would break the page
            if set(re.findall(r"\{(\w+)\}", payload[k])) == set(re.findall(r"\{(\w+)\}", v)):
                out[k] = v.strip()
    return out


def ensure_language():
    """Makes sure translations/<code>.json has every interface key. Missing ones are translated once and saved,
    so the first person who picks a language waits about a minute and everyone after that gets it instantly."""
    import streamlit as st

    code = current_lang()
    if code in ("en", "hi"):
        return
    data = _static(code)
    missing = [k for k in EN if k not in data]
    flag = f"_tr_try_{code}"
    if not missing or st.session_state.get(flag):
        return
    st.session_state[flag] = True  # one attempt per visit, so a failure never loops
    from loader import run_cancellable

    language = BY_CODE[code]["english"]
    n = -(-len(missing) // 40)
    steps = [(t("ld.tr_app", lang=language), t("ld.tr_app_s"), int(100 * (k + 1) / (n + 1)), "globe") for k in range(n)]

    def work(progress):  # runs in the background; the X button stops waiting at once
        got = {}
        for k in range(n):
            progress(k + 1)
            got.update(translate_keys(missing[k * 40:(k + 1) * 40], language))
        return got

    status, value = run_cancellable(steps, work, "globe")
    if status == "done":
        data.update(value)
        TR_DIR.mkdir(exist_ok=True)
        (TR_DIR / f"{code}.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    else:
        print("ensure_language failed:", repr(value)[:150])


# ---------------------------------------------------------------- widgets
def render_language_selector():
    import streamlit as st

    st.session_state.setdefault("lang", "en")
    st.selectbox(
        "Language", [l["code"] for l in LANGS], key="lang", label_visibility="collapsed",
        format_func=lambda c: BY_CODE[c]["native"] if c == "en" else f"{BY_CODE[c]['native']} · {BY_CODE[c]['english']}",
    )
    st.session_state["lang_ai"] = BY_CODE[st.session_state["lang"]]["english"]


def inject_rtl():
    """Right-to-left text for Arabic, Urdu, Persian, Sindhi and Kashmiri. The top bar keeps its layout."""
    import streamlit as st

    if current_lang() != "en":  # letter spacing and tight lines break Indic and other non-Latin scripts
        st.markdown("<style>.t-eyebrow{letter-spacing:0 !important; text-transform:none !important;}"
                    ".t-display{line-height:1.3 !important;} .t-h1,.t-h2{line-height:1.35 !important;}</style>",
                    unsafe_allow_html=True)
    if is_rtl():
        st.markdown(
            "<style>[data-testid='stMarkdownContainer'], [data-testid='stCaptionContainer'], [data-testid='stAlert'],"
            "[data-testid='stExpander'] summary, .card3d, .hero-copy, .t-h2, .t-eyebrow{direction:rtl; text-align:right;}"
            ".st-key-topnav [data-testid='stMarkdownContainer']{direction:ltr;}</style>",
            unsafe_allow_html=True,
        )
