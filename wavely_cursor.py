"""
wavely_cursor.py  -  the glowing Wavely cursor.

What the person sees (on the app page):
  - a small bright dot that is the real pointer
  - a soft light that follows it, with waves (rings) that spread out while Wavely is LIVE
  - a light trail when the pointer moves, and a ripple when it clicks
  - a small tag that tells the hand mode: MOUSE / RIGHT CLICK / SCROLL / VOLUME / ZOOM
  - if the camera is OFF the cursor is calm and dim (no waves), so you can SEE that it is working

How it works (simple):
  Streamlit cannot run JavaScript in a normal st.markdown. So we use st.components.v1.html (an invisible box).
  Its small script puts the cursor code in the real page, and the code reads the text that the app
  already shows ("Hand shape: POINT ...") to know the hand mode. Python does not change.

  inject(enabled, dark)   -> call it once near the top of app_v2.py
"""
import json

import streamlit.components.v1 as components

_CSS = r"""
#wv-dot,#wv-follow,#wv-trail{position:fixed;left:0;top:0;pointer-events:none}
#wv-trail{width:100vw;height:100vh;z-index:2147483645}
#wv-follow{z-index:2147483646;width:0;height:0;opacity:0;transition:opacity .25s}
#wv-dot{z-index:2147483647;width:10px;height:10px;margin:-5px 0 0 -5px;border-radius:50%;opacity:0;
  background:radial-gradient(circle at 35% 35%,#fff,#EEAABD 45%,#859CE9);
  box-shadow:0 0 10px 2px rgba(238,170,189,.9),0 0 22px 6px rgba(133,156,233,.55);transition:opacity .2s,transform .12s}
html.wv-on,html.wv-on *{cursor:none!important}
html.wv-on #wv-dot,html.wv-on #wv-follow{opacity:1}
.wv-aura{position:absolute;width:64px;height:64px;margin:-32px 0 0 -32px;border-radius:50%;
  background:radial-gradient(circle,rgba(238,170,189,.50),rgba(133,156,233,.28) 45%,transparent 70%);
  filter:blur(2px);transition:transform .3s,opacity .3s;opacity:.35;transform:scale(.55)}
.wv-ring{position:absolute;width:30px;height:30px;margin:-15px 0 0 -15px;border-radius:50%;opacity:0;
  border:2px solid transparent;
  background:linear-gradient(135deg,#EEAABD,#859CE9) border-box;
  -webkit-mask:linear-gradient(#000 0 0) padding-box,linear-gradient(#000 0 0);
  -webkit-mask-composite:xor;mask-composite:exclude}
/* LIVE = the camera loop is running: waves spread out */
#wv-cursor.live .wv-aura{opacity:.9;transform:scale(1)}
#wv-cursor.live .wv-ring{animation:wv-wave 2.6s cubic-bezier(.2,.6,.3,1) infinite}
#wv-cursor.live .wv-ring.r2{animation-delay:.85s}
#wv-cursor.live .wv-ring.r3{animation-delay:1.7s}
#wv-cursor.mode .wv-ring{animation-duration:1.6s}
#wv-cursor.mode .wv-aura{transform:scale(1.25)}
@keyframes wv-wave{0%{transform:scale(.4);opacity:.95}100%{transform:scale(3.4);opacity:0}}
.wv-burst{position:fixed;width:30px;height:30px;margin:-15px 0 0 -15px;border-radius:50%;pointer-events:none;
  z-index:2147483646;border:2px solid #EEAABD;box-shadow:0 0 14px rgba(133,156,233,.8);
  animation:wv-burst .65s ease-out forwards}
@keyframes wv-burst{0%{transform:scale(.3);opacity:1}100%{transform:scale(3.2);opacity:0}}
.wv-tag{position:absolute;left:22px;top:20px;padding:3px 10px;border-radius:999px;font:600 11px/1.4 'Poppins','Segoe UI',sans-serif;
  letter-spacing:1.5px;white-space:nowrap;color:#14123A;opacity:0;transform:translateY(4px);
  background:linear-gradient(135deg,#EEAABD,#859CE9);box-shadow:0 6px 18px rgba(133,156,233,.45);
  transition:opacity .2s,transform .2s}
#wv-cursor.mode .wv-tag{opacity:1;transform:none}
#wv-cursor.light #wv-dot{background:radial-gradient(circle at 35% 35%,#fff,#D07A9A 45%,#6A82E2);
  box-shadow:0 0 0 2px rgba(106,130,226,.35),0 0 12px 3px rgba(208,122,154,.7)}
#wv-cursor.light .wv-ring{border-width:2.5px;background:linear-gradient(135deg,#D07A9A,#6A82E2) border-box}
#wv-cursor.light .wv-aura{background:radial-gradient(circle,rgba(208,122,154,.55),rgba(106,130,226,.35) 45%,transparent 70%)}
#wv-cursor.light .wv-tag{color:#fff;background:linear-gradient(135deg,#D07A9A,#6A82E2)}
/* hovering something you can press: the light grows and locks on it */
#wv-cursor.hover .wv-aura{transform:scale(1.9);opacity:.95}
#wv-cursor.hover .wv-ring.r1{animation:none;opacity:.9;transform:scale(1.7)}
#wv-cursor.hover .wv-ring.r2,#wv-cursor.hover .wv-ring.r3{animation:none;opacity:0}
#wv-cursor.hover #wv-dot{transform:scale(.7)}
/* the camera card changes ~20 times a second: no blur behind it (blur is slow) */
[class*="st-key-card"]{backdrop-filter:none!important;-webkit-backdrop-filter:none!important}
@media (pointer:coarse){#wv-dot,#wv-follow,#wv-trail{display:none}}
"""

_JS = r"""
(function(){
  var w = window, d = document;
  if (w.__wavelyCursor) return;
  var cfg = {enabled:true, dark:true};
  var st = d.createElement('style'); st.id = 'wv-cursor-style'; st.textContent = CSS_TEXT; d.head.appendChild(st);

  var root = d.createElement('div'); root.id = 'wv-cursor';
  var dot = d.createElement('div'); dot.id = 'wv-dot';
  var follow = d.createElement('div'); follow.id = 'wv-follow';
  follow.innerHTML = '<div class="wv-aura"></div><div class="wv-ring r1"></div><div class="wv-ring r2"></div>' +
                     '<div class="wv-ring r3"></div><div class="wv-tag"></div>';
  var cv = d.createElement('canvas'); cv.id = 'wv-trail';
  root.appendChild(cv); root.appendChild(follow); root.appendChild(dot);
  d.body.appendChild(root);
  var tag = follow.querySelector('.wv-tag'), ctx = cv.getContext('2d');

  function resize(){ cv.width = w.innerWidth; cv.height = w.innerHeight; }
  resize(); w.addEventListener('resize', resize);

  var lastMx = 0, lastMy = 0, mx = -100, my = -100, fx = -100, fy = -100, lx = null, ly = null, travel = 0, seen = false;
  var COL = [[238,170,189],[133,156,233]];
  var COLL = [[208,122,154],[106,130,226]];

  d.addEventListener('mousemove', function(e){
    mx = e.clientX; my = e.clientY;
    if (!seen){ seen = true; fx = mx; fy = my; lx = mx; ly = my; if (cfg.enabled) d.documentElement.classList.add('wv-on'); }
  }, {passive:true});
  d.addEventListener('mouseout', function(e){ if (!e.relatedTarget){ dot.style.opacity = 0; follow.style.opacity = 0; } });
  d.addEventListener('mouseover', function(){ dot.style.opacity = ''; follow.style.opacity = ''; });
  var CLICKABLE = 'button,a,[role="button"],[role="tab"],[role="switch"],[role="checkbox"],input,select,textarea,label,summary,' +
                  '[data-baseweb="select"],[data-testid="stToggle"],[data-testid="stExpander"] summary,[data-testid="stPopover"]';
  var hov = false;
  d.addEventListener('mouseover', function(e){
    var el = e.target && e.target.closest ? e.target.closest(CLICKABLE) : null;
    hov = !!el;
  }, {passive:true});
  d.addEventListener('mousedown', function(e){
    dot.style.transform = 'scale(.6)';
    if (!cfg.enabled) return;
    var b = d.createElement('div'); b.className = 'wv-burst'; b.style.left = e.clientX + 'px'; b.style.top = e.clientY + 'px';
    d.body.appendChild(b); setTimeout(function(){ b.remove(); }, 700);
  }, true);
  d.addEventListener('mouseup', function(){ dot.style.transform = ''; }, true);

  // ---- what is the hand doing? We read the text the app already shows ----
  var MODES = {POINT:'MOUSE', HORNS:'RIGHT CLICK', TWO:'SCROLL', THREE:'VOLUME'};
  function readState(){
    var live = false, mode = '';
    var els = d.querySelectorAll('[data-testid="stMarkdownContainer"]');
    for (var i = 0; i < els.length; i++){
      var t = els[i].textContent || '';
      if (t.indexOf('Hand shape:') >= 0 || t.indexOf('Seeing:') >= 0 || t.indexOf('No hand seen') >= 0 ||
          t.indexOf('Hand mode:') >= 0){
        live = true;
        var m = /Hand shape:\s*([A-Za-z]+)/.exec(t);
        if (m && MODES[m[1]]) mode = MODES[m[1]];
        if (!mode && /two[_ ]open[_ ]hands/.test(t)) mode = 'ZOOM';
        break;
      }
    }
    return {live:live, mode:mode};
  }
  var lastMode = '';
  setInterval(function(){
    var s = readState();
    root.classList.toggle('live', s.live && cfg.enabled);
    var shown = s.mode || (hov ? 'CLICK' : '');
    root.classList.toggle('hover', hov && cfg.enabled);
    root.classList.toggle('mode', !!shown && cfg.enabled);
    if (shown !== lastMode){ lastMode = shown; if (shown) tag.textContent = shown; }
  }, 300);

  // ---- animation: soft light follows the pointer, light trail behind it ----
  function lerp(a, b, t){ return a + (b - a) * t; }
  var live = 0, lastFx = -1, lastFy = -1;     // live = how many frames the trail still needs
  function frame(){
    fx = lerp(fx, mx, .2); fy = lerp(fy, my, .2);
    if (Math.abs(fx - lastFx) > .05 || Math.abs(fy - lastFy) > .05 || mx !== lastMx || my !== lastMy){
      dot.style.transform = dot.style.transform;  // (keeps the click squeeze)
      dot.style.left = mx + 'px'; dot.style.top = my + 'px';
      follow.style.transform = 'translate(' + fx + 'px,' + fy + 'px)';
      lastFx = fx; lastFy = fy; lastMx = mx; lastMy = my;
    }
    var moved = cfg.enabled && seen && lx !== null && (Math.abs(mx - lx) + Math.abs(my - ly) > 1.5);
    if (moved) live = 70;
    if (live > 0){                                // draw / fade the trail ONLY while it is visible
      live--;
      ctx.globalCompositeOperation = 'destination-out';
      ctx.fillStyle = 'rgba(0,0,0,' + (cfg.dark ? .14 : .12) + ')';
      ctx.fillRect(0, 0, cv.width, cv.height);
      if (live === 0) ctx.clearRect(0, 0, cv.width, cv.height);
    }
    if (moved){
      var dx = mx - lx, dy = my - ly, dist = Math.sqrt(dx*dx + dy*dy);
      travel += dist;
      var t = (Math.sin(travel / 90) + 1) / 2;
      var K = cfg.dark ? COL : COLL;
      var r = Math.round(lerp(K[0][0], K[1][0], t)), g = Math.round(lerp(K[0][1], K[1][1], t)),
          b = Math.round(lerp(K[0][2], K[1][2], t));
      ctx.globalCompositeOperation = 'source-over';
      ctx.lineCap = 'round';
      var lw = Math.min(9, 2.5 + dist / 6);
      ctx.strokeStyle = 'rgba(' + r + ',' + g + ',' + b + ',.28)';   // soft glow = a wide faint line (no slow blur)
      ctx.lineWidth = lw + 7;
      ctx.beginPath(); ctx.moveTo(lx, ly); ctx.lineTo(mx, my); ctx.stroke();
      ctx.strokeStyle = 'rgba(' + r + ',' + g + ',' + b + ',' + (cfg.dark ? .9 : .8) + ')';
      ctx.lineWidth = lw;
      ctx.beginPath(); ctx.moveTo(lx, ly); ctx.lineTo(mx, my); ctx.stroke();
    }
    lx = mx; ly = my;
  w.requestAnimationFrame(frame);
  }
  w.requestAnimationFrame(frame);

  w.__wavelyCursor = {
    config: function(c){
      cfg.enabled = c.enabled !== false; cfg.dark = c.dark !== false;
      d.documentElement.classList.toggle('wv-on', cfg.enabled && seen);
      root.classList.toggle('light', !cfg.dark);
      root.style.display = cfg.enabled ? '' : 'none';
    }
  };
})();
"""


def inject(enabled=True, dark=True):
    """Put the glowing cursor in the page. Call once near the top of the app."""
    code = _JS.replace("CSS_TEXT", json.dumps(_CSS))
    html = (
        "<script>(function(){var p=window.parent;"
        "try{if(!p.__wavelyCursor){var s=p.document.createElement('script');"
        "s.textContent=" + json.dumps(code) + ";p.document.head.appendChild(s);}"
        "if(p.__wavelyCursor)p.__wavelyCursor.config({enabled:" + json.dumps(bool(enabled)) +
        ",dark:" + json.dumps(bool(dark)) + "});}catch(e){}})();</script>"
    )
    components.html(html, height=0)
