"""
wavely_ui.py  -  the look of the Wavely app (colors, background, logo, hero picture).

It only draws things. It does not touch the gesture logic.
  inject(dark)  -> adds the CSS (light or dark mode)
  nav_html()    -> the logo + name at the top
  hero_html()   -> the big title with the hand, waves and camera picture
"""
import base64
import math

import streamlit as st

PINK_DARK, PINK_LIGHT, BLUE = "#EEAABD", "#E4A1B4", "#859CE9"


def _b64(svg):
    return base64.b64encode(svg.encode("utf-8")).decode("ascii")


# ---------------------------------------------------------------- pictures (SVG)
def _finger(px, py, a, w, l):
    return ('<rect x="%s" y="%s" width="%s" height="%s" rx="%s" '
            'transform="translate(%s,%s) rotate(%s)"/>'
            % (-w / 2, -l, w, l + 26, w / 2, px, py, a))


def _hand_shapes():
    s = '<rect x="62" y="104" width="88" height="76" rx="34"/>'
    s += _finger(86, 112, -11, 21, 74)
    s += _finger(106, 106, -2, 22, 84)
    s += _finger(126, 108, 7, 21, 76)
    s += _finger(143, 120, 16, 19, 58)
    s += _finger(70, 146, -46, 22, 50)
    return s


def _waves_arcs(cx, cy, radii, width, a=38):
    s = '<g fill="none" stroke="url(#g)" stroke-linecap="round" stroke-width="%s">' % width
    for r, op in radii:
        a0, a1 = math.radians(-a), math.radians(a)
        x0, y0 = cx + r * math.cos(a0), cy + r * math.sin(a0)
        x1, y1 = cx + r * math.cos(a1), cy + r * math.sin(a1)
        s += '<path d="M%.1f %.1f A%s %s 0 0 1 %.1f %.1f" opacity="%s"/>' % (x0, y0, r, r, x1, y1, op)
    return s + "</g>"


def logo_icon_svg(pink):
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 260 220">'
            '<defs><linearGradient id="g" gradientUnits="userSpaceOnUse" x1="20" y1="190" x2="230" y2="20">'
            '<stop offset="0" stop-color="%s"/><stop offset="1" stop-color="%s"/></linearGradient>'
            '<mask id="m" maskUnits="userSpaceOnUse" x="0" y="0" width="260" height="220">'
            '<g fill="#fff">%s</g></mask></defs>'
            '<rect width="260" height="220" fill="url(#g)" mask="url(#m)"/>%s</svg>'
            % (pink, BLUE, _hand_shapes(), _waves_arcs(100, 118, ((96, 1), (122, .75), (148, .5)), 7)))


def camera_lens(cx, cy, r):
    """A camera lens: rings + 6 blades."""
    s = '<g transform="translate(%s,%s)">' % (cx, cy)
    s += '<circle r="%s" fill="#0F0F2B" stroke="url(#g)" stroke-width="5"/>' % r
    s += '<circle r="%s" fill="none" stroke="url(#g)" stroke-width="2" opacity=".6"/>' % (r * 0.78)
    for k in range(6):
        s += ('<path d="M0 0 L%s %s L%s %s Z" fill="url(#g)" opacity=".55" '
              'transform="rotate(%s)"/>' % (r * 0.55, -r * 0.15, r * 0.30, r * 0.50, k * 60))
    s += '<circle r="%s" fill="#0F0F2B"/>' % (r * 0.22)
    s += '<circle cx="%s" cy="%s" r="%s" fill="#fff" opacity=".85"/>' % (-r * 0.35, -r * 0.4, r * 0.09)
    return s + "</g>"


def hero_art_svg(pink):
    s = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 560 440">'
         '<defs><linearGradient id="g" gradientUnits="userSpaceOnUse" x1="40" y1="420" x2="520" y2="20">'
         '<stop offset="0" stop-color="%s"/><stop offset="1" stop-color="%s"/></linearGradient>'
         '<radialGradient id="glow"><stop offset="0" stop-color="%s" stop-opacity=".30"/>'
         '<stop offset="1" stop-color="%s" stop-opacity="0"/></radialGradient>'
         '<mask id="m" maskUnits="userSpaceOnUse" x="0" y="0" width="260" height="220">'
         '<g fill="#fff">%s</g></mask></defs>' % (pink, BLUE, BLUE, BLUE, _hand_shapes()))
    s += '<circle cx="280" cy="230" r="210" fill="url(#glow)"/>'
    # wave bands under the hand
    for i, op in enumerate((.9, .55, .3)):
        y = 330 + i * 26
        s += ('<path d="M20 %s C 110 %s, 170 %s, 280 %s S 450 %s, 540 %s" fill="none" '
              'stroke="url(#g)" stroke-width="%s" stroke-linecap="round" opacity="%s"/>'
              % (y, y - 34, y + 34, y, y - 34, y, 9 - i * 2, op))
    # the hand (big)
    s += ('<g transform="translate(70,-10) scale(1.75)"><rect width="260" height="220" '
          'fill="url(#g)" mask="url(#m)"/>')
    # fingertip points, like the MediaPipe points
    for x, y in ((74, 41), (104, 26), (133, 41), (156, 60), (27, 118)):
        s += '<circle cx="%s" cy="%s" r="5" fill="#fff"/>' % (x, y)
    s += "</g>"
    # waves from the hand
    s += _waves_arcs(250, 190, ((205, 1), (245, .7), (285, .45)), 8, 34)
    # camera lens + dotted link to the hand
    s += ('<path d="M392 118 C 360 150, 330 120, 300 132" fill="none" stroke="url(#g)" '
          'stroke-width="3" stroke-dasharray="2 9" stroke-linecap="round"/>')
    s += camera_lens(430, 92, 54)
    s += '<circle cx="498" cy="188" r="6" fill="url(#g)"/><circle cx="60" cy="90" r="4" fill="url(#g)" opacity=".7"/>'
    return s + "</svg>"


def page_waves_svg(pink):
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 420" preserveAspectRatio="none">'
            '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="0">'
            '<stop offset="0" stop-color="%s"/><stop offset="1" stop-color="%s"/></linearGradient></defs>'
            '<path d="M0 250 C 260 140, 520 360, 820 250 S 1380 150, 1600 250 L1600 420 L0 420 Z" '
            'fill="url(#g)" opacity=".16"/>'
            '<path d="M0 310 C 300 220, 560 400, 860 310 S 1400 230, 1600 320 L1600 420 L0 420 Z" '
            'fill="url(#g)" opacity=".12"/>'
            '<path d="M0 365 C 320 300, 600 420, 900 360 S 1420 310, 1600 370 L1600 420 L0 420 Z" '
            'fill="url(#g)" opacity=".10"/></svg>' % (pink, BLUE))


# ---------------------------------------------------------------- html pieces
def nav_html(dark):
    pink = PINK_DARK if dark else PINK_LIGHT
    return ('<div class="wv-brand"><img src="data:image/svg+xml;base64,%s" alt="">'
            '<span>Wavely</span></div>' % _b64(logo_icon_svg(pink)))


def hero_html(dark):
    pink = PINK_DARK if dark else PINK_LIGHT
    art = _b64(hero_art_svg(pink))
    return ('<div class="wv-hero"><div class="wv-hero-text">'
            '<div class="wv-pill">HAND GESTURE CONTROL</div>'
            '<h1>Control your computer with a <span>wave of your hand.</span></h1>'
            '<p>Wavely turns your webcam into a touch-free keyboard and mouse. '
            'No extra device is needed.</p>'
            '<div class="wv-chips"><span>Webcam only</span><span>7 trained gestures</span>'
            '<span>97%% accuracy on a new session</span></div></div>'
            '<div class="wv-hero-art"><img src="data:image/svg+xml;base64,%s" alt=""></div></div>' % art)


# ---------------------------------------------------------------- css
def _vars(dark):
    if dark:
        return dict(bg1="#15153A", bg2="#1E1E43", text="#EDEDFB", muted="#A9A9CF",
                    card="rgba(255,255,255,0.06)", card2="rgba(255,255,255,0.10)",
                    border="rgba(255,255,255,0.13)", input="rgba(255,255,255,0.08)",
                    pink=PINK_DARK, blue=BLUE, ga=PINK_DARK, gb=BLUE, btntext="#14123A", shadow="0 18px 50px rgba(0,0,0,.35)",
                    menu="#252552")
    return dict(bg1="#FBFBFE", bg2="#EDEBFF", text="#14123A", muted="#5B5A80",
                card="rgba(255,255,255,0.80)", card2="rgba(238,237,255,0.9)",
                border="rgba(20,18,58,0.10)", input="#FFFFFF",
                pink=PINK_LIGHT, blue=BLUE, ga="#D07A9A", gb="#6A82E2", btntext="#14123A", shadow="0 18px 50px rgba(60,50,140,.12)",
                menu="#FFFFFF")


def inject(dark=True):
    v = _vars(dark)
    pink = PINK_DARK if dark else PINK_LIGHT
    waves = _b64(page_waves_svg(pink))
    css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap');
:root{--bg1:%(bg1)s;--bg2:%(bg2)s;--text:%(text)s;--muted:%(muted)s;--card:%(card)s;--card2:%(card2)s;
--border:%(border)s;--input:%(input)s;--pink:%(pink)s;--blue:%(blue)s;--ga:%(ga)s;--gb:%(gb)s;--btntext:%(btntext)s;--menu:%(menu)s;}
html,body,.stApp,[data-testid="stAppViewContainer"]{font-family:'Poppins','Segoe UI',system-ui,sans-serif!important;}
.stApp{
  background:
    url("data:image/svg+xml;base64,%(waves)s") bottom center/100%% 360px no-repeat fixed,
    radial-gradient(900px 500px at 88%% -5%%, rgba(133,156,233,.28), transparent 60%%),
    radial-gradient(700px 480px at 0%% 8%%, rgba(238,170,189,.20), transparent 60%%),
    linear-gradient(160deg,var(--bg1),var(--bg2)) fixed !important;
  color:var(--text)!important;}
/* hide the Streamlit look */
#MainMenu,footer,[data-testid="stToolbar"],[data-testid="stDecoration"],[data-testid="stStatusWidget"]{display:none!important}
header[data-testid="stHeader"]{background:transparent!important;height:0!important}
.block-container{padding:1.2rem 2rem 4rem!important;max-width:1240px!important}
/* text */
.stApp h1,.stApp h2,.stApp h3,.stApp h4,.stApp p,.stApp label,.stApp li,.stApp td,.stApp th,
.stApp [data-testid="stMarkdownContainer"],.stApp [data-testid="stWidgetLabel"]{color:var(--text)!important}
.stApp [data-testid="stCaptionContainer"],.stApp .stCaption,.stApp small{color:var(--muted)!important}
.stApp h3{font-weight:600!important;letter-spacing:-.2px}
/* top bar */
.wv-brand{display:flex;align-items:center;gap:12px}
.wv-brand img{height:46px}
.wv-brand span{font-size:26px;font-weight:700;letter-spacing:-.5px;color:var(--text)}
.st-key-nav{align-items:center}
.st-key-nav [data-testid="stHorizontalBlock"]{align-items:center}
/* hero */
.wv-hero{display:flex;align-items:center;justify-content:space-between;gap:20px;margin:10px 0 26px}
.wv-hero-text{flex:1 1 55%%}
.wv-hero-art{flex:1 1 45%%;text-align:right}
.wv-hero-art img{width:100%%;max-width:520px;filter:drop-shadow(0 20px 40px rgba(133,156,233,.25))}
.wv-pill{display:inline-block;padding:6px 14px;border-radius:999px;font-size:12px;font-weight:600;
  letter-spacing:2px;color:var(--text);background:var(--card2);border:1px solid var(--border)}
.wv-hero h1{font-size:50px!important;line-height:1.12!important;font-weight:700!important;margin:16px 0 12px!important;
  letter-spacing:-1.2px;padding:0!important}
.wv-hero h1 span{background:linear-gradient(90deg,var(--ga),var(--gb));-webkit-background-clip:text;
  background-clip:text;-webkit-text-fill-color:transparent;color:transparent}
.wv-hero p{font-size:18px!important;color:var(--muted)!important;max-width:520px;margin:0 0 18px!important}
.wv-chips span{display:inline-block;margin:0 8px 8px 0;padding:7px 14px;border-radius:999px;font-size:13px;
  font-weight:500;background:var(--card);border:1px solid var(--border);color:var(--text)}
.wv-section{font-size:13px;font-weight:600;letter-spacing:2px;color:var(--muted);margin:6px 2px 8px}
/* cards: containers made with a key that starts with "card" */
[class*="st-key-card"]{background:var(--card)!important;border:1px solid var(--border)!important;
  border-radius:22px!important;padding:20px 22px!important;box-shadow:%(shadow)s;backdrop-filter:blur(14px);
  -webkit-backdrop-filter:blur(14px)}
[data-testid="stImage"] img{border-radius:16px;border:1px solid var(--border)}
/* buttons */
.stApp .stButton>button,.stApp .stFormSubmitButton>button,.stApp [data-testid="stPopover"]>button,
.stApp [data-testid="stPopover"] button{
  background:linear-gradient(135deg,var(--pink),var(--blue))!important;color:var(--btntext)!important;
  border:none!important;border-radius:14px!important;font-weight:600!important;padding:.55rem 1rem!important;
  box-shadow:0 8px 22px rgba(133,156,233,.30);transition:transform .15s ease, box-shadow .15s ease}
.stApp .stButton>button:hover,.stApp .stFormSubmitButton>button:hover,.stApp [data-testid="stPopover"] button:hover{
  transform:translateY(-1px);box-shadow:0 12px 28px rgba(133,156,233,.42);color:var(--btntext)!important}
.stApp .stButton>button p,.stApp .stFormSubmitButton>button p,.stApp [data-testid="stPopover"] button p{
  color:var(--btntext)!important;font-weight:600}
.stApp [data-testid="stPopover"]>button{width:46px;height:46px;border-radius:50%%!important;padding:0!important;font-size:20px}
[data-testid="stPopoverBody"],[data-baseweb="popover"]>div{background:var(--menu)!important;
  border:1px solid var(--border)!important;border-radius:18px!important;color:var(--text)!important}
/* inputs */
.stApp [data-baseweb="input"],.stApp [data-baseweb="select"]>div,.stApp [data-baseweb="base-input"],
.stApp textarea{background:var(--input)!important;border-color:var(--border)!important;border-radius:12px!important}
.stApp input,.stApp [data-baseweb="select"] *{color:var(--text)!important}
.stApp [data-baseweb="select"] svg{fill:var(--text)!important}
[data-baseweb="menu"],[data-baseweb="menu"] li{background:var(--menu)!important;color:var(--text)!important}
[data-baseweb="menu"] li:hover{background:var(--card2)!important}
/* expander */
.stApp [data-testid="stExpander"]{background:var(--card2)!important;border:1px solid var(--border)!important;
  border-radius:16px!important}
.stApp [data-testid="stExpander"] summary,.stApp [data-testid="stExpander"] summary *{color:var(--text)!important}
/* table */
.stApp [data-testid="stTable"] table{width:100%%;border-collapse:collapse;border-radius:12px;overflow:hidden}
.stApp [data-testid="stTable"] th{background:var(--card2)!important;font-weight:600}
.stApp [data-testid="stTable"] td,.stApp [data-testid="stTable"] th{border:1px solid var(--border)!important;
  padding:8px 12px!important;color:var(--text)!important}
/* popover / table text: the popover lives OUTSIDE .stApp, so these rules do not use it */
[data-baseweb="popover"] [data-testid="stPopoverBody"],[data-testid="stPopoverBody"]{background:var(--menu)!important;color:var(--text)!important}
[data-testid="stPopoverBody"] *,[data-testid="stTable"] *,[data-testid="stTable"] td,[data-testid="stTable"] th,
[data-testid="stTable"] p{color:var(--text)!important}
[data-testid="stTable"] table{width:100%%;border-collapse:collapse}
[data-testid="stTable"] td,[data-testid="stTable"] th{border:1px solid var(--border)!important;padding:8px 12px!important;background:transparent}
[data-testid="stTable"] th{background:var(--card2)!important}
/* form fields (boxes, drop-downs, expander): a SOLID color so the text is always readable */
.stApp [data-baseweb="select"] > div,.stApp [data-baseweb="select"] > div > div,
.stApp [data-baseweb="input"],.stApp [data-baseweb="input"] > div,.stApp [data-baseweb="base-input"],
.stApp input,.stApp textarea{background:var(--menu)!important;background-color:var(--menu)!important;
  color:var(--text)!important;-webkit-text-fill-color:var(--text)!important;border-color:var(--border)!important}
.stApp [data-baseweb="select"] span,.stApp [data-baseweb="select"] div{color:var(--text)!important}
.stApp input::placeholder{color:var(--muted)!important;-webkit-text-fill-color:var(--muted)!important}
.stApp [data-testid="stExpander"],.stApp [data-testid="stExpander"] details,
.stApp [data-testid="stExpander"] summary{background:var(--card2)!important;color:var(--text)!important}
.stApp [data-testid="stExpander"] summary:hover{background:var(--card)!important}
.stApp [data-testid="stForm"]{background:transparent!important;border:1px solid var(--border)!important;border-radius:16px!important}
.stApp label,.stApp label p,.stApp [data-testid="stWidgetLabel"] p{color:var(--text)!important}
@media (max-width:900px){.wv-hero{flex-direction:column}.wv-hero h1{font-size:36px!important}.wv-hero-art{text-align:center}}
</style>
""" % dict(v, waves=waves)
    st.markdown(css, unsafe_allow_html=True)


def card(name):
    """A card box. 'name' becomes the class st-key-card_<name> in new Streamlit versions."""
    try:
        return st.container(key="card_" + name)
    except TypeError:                       # old Streamlit: a plain bordered box
        try:
            return st.container(border=True)
        except TypeError:
            return st.container()


def nav_box():
    """The top bar box (class st-key-nav in new Streamlit versions)."""
    try:
        return st.container(key="nav")
    except TypeError:
        return st.container()
