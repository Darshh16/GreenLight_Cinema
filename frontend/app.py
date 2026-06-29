"""
Greenlight Cinema — Streamlit Dashboard v3
============================================
Massive Cinematic UI Redesign
"""

import streamlit as st
import requests
import pandas as pd
import time
import json
import plotly.express as px

# Configure page
st.set_page_config(
    page_title="Greenlight Cinema",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Constants
API_URL = "http://localhost:8000/api"


# ── Themes & State ──────────────────────────────────────────────────────────
THEMES = {
    "Classic Dark": {
        "bg": "radial-gradient(circle at 50% 0%, #111116 0%, #050508 100%)",
        "bg_animation": "pulseBg 15s ease-in-out infinite alternate",
        "text_main": "#F0EDE8",
        "text_muted": "#D1C9BE",
        "accent_primary": "#C9A84C",
        "accent_primary_dark": "#A68A3D",
        "glass_bg": "rgba(255,255,255,0.04)",
        "glass_border": "rgba(255,255,255,0.05)",
        "glass_shadow": "rgba(0,0,0,0.3)",
        "card_bg": "#1C1612",
        "card_shadow": "rgba(0,0,0,0.5)",
        "talent_border": "rgba(255,255,255,0.1)",
        "talent_bg": "rgba(0,0,0,0.2)",
        "scorecard_bg": "rgba(255,255,255,0.03)",
        "btn_bg": "rgba(255,255,255,0.05)",
        "btn_border": "rgba(255,255,255,0.1)",
        "plotly_template": "plotly_dark"
    },
    "Cyberpunk Noir": {
        "bg": "radial-gradient(circle at 50% 0%, #0c0014 0%, #000000 100%)",
        "bg_animation": "pulseBg 8s ease-in-out infinite alternate",
        "text_main": "#e0f2fe",
        "text_muted": "#bae6fd",
        "accent_primary": "#f0abfc",
        "accent_primary_dark": "#c026d3",
        "glass_bg": "rgba(240, 171, 252, 0.05)",
        "glass_border": "rgba(34, 211, 238, 0.2)",
        "glass_shadow": "rgba(192, 38, 211, 0.2)",
        "card_bg": "#0f172a",
        "card_shadow": "rgba(0,0,0,0.8)",
        "talent_border": "rgba(34, 211, 238, 0.2)",
        "talent_bg": "rgba(0,0,0,0.4)",
        "scorecard_bg": "rgba(34, 211, 238, 0.05)",
        "btn_bg": "rgba(192, 38, 211, 0.1)",
        "btn_border": "rgba(34, 211, 238, 0.3)",
        "plotly_template": "plotly_dark"
    },
    "Nordic Forest": {
        "bg": "radial-gradient(circle at 50% 0%, #0f1714 0%, #020604 100%)",
        "bg_animation": "pulseBg 20s ease-in-out infinite alternate",
        "text_main": "#ecfdf5",
        "text_muted": "#a7f3d0",
        "accent_primary": "#34d399",
        "accent_primary_dark": "#059669",
        "glass_bg": "rgba(52, 211, 153, 0.03)",
        "glass_border": "rgba(52, 211, 153, 0.1)",
        "glass_shadow": "rgba(0,0,0,0.4)",
        "card_bg": "#064e3b",
        "card_shadow": "rgba(0,0,0,0.6)",
        "talent_border": "rgba(52, 211, 153, 0.1)",
        "talent_bg": "rgba(0,0,0,0.3)",
        "scorecard_bg": "rgba(52, 211, 153, 0.05)",
        "btn_bg": "rgba(52, 211, 153, 0.05)",
        "btn_border": "rgba(52, 211, 153, 0.2)",
        "plotly_template": "plotly_dark"
    }
}

if "theme" not in st.session_state:
    st.session_state.theme = "Classic Dark"

t = THEMES[st.session_state.theme]

# Custom CSS for cinematic redesign
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&family=JetBrains+Mono:wght@400;700&family=Playfair+Display:ital,wght@0,600;0,700;1,600&display=swap');

    /* Global Base Theme */
    .stApp {{
        background: {t['bg']};
        background-size: 150% 150%;
        animation: {t['bg_animation']};
        color: {t['text_main']};
        font-family: 'Inter', sans-serif;
    }}
    
    @keyframes pulseBg {{
        0% {{ background-position: 50% 0%; }}
        100% {{ background-position: 50% 100%; }}
    }}
    
    /* Film Grain Background */
    .stApp::before {{
        content: "";
        position: fixed;
        top: 0; left: 0; width: 100vw; height: 100vh;
        background-image: url('https://www.transparenttextures.com/patterns/stardust.png');
        opacity: 0.05;
        pointer-events: none;
        z-index: 9999;
    }}

    /* Hide Default Sidebar */
    [data-testid="stSidebar"] {{ display: none !important; }}
    [data-testid="collapsedControl"] {{ display: none !important; }}
    .block-container {{
        padding-top: 2rem !important;
        padding-bottom: 8rem !important;
        max-width: 1200px;
    }}
    
    /* Typography */
    h1, h2, h3 {{ font-family: 'Playfair Display', serif; }}
    
    /* Hero Banner */
    .hero-banner {{
        width: 100%;
        padding: 40px 0;
        text-align: center;
        border-bottom: 1px solid {t['accent_primary']};
        margin-bottom: 30px;
        position: relative;
        overflow: hidden;
        animation: fadeIn 0.8s ease-out forwards;
    }}
    .hero-title {{
        font-size: 48px;
        font-weight: 700;
        color: {t['accent_primary']};
        margin: 0;
        letter-spacing: -0.5px;
        white-space: nowrap;
        display: inline-block;
    }}
    .hero-subtitle {{
        font-style: italic;
        color: {t['text_muted']};
        font-size: 18px;
        margin-top: 10px;
        opacity: 0;
        animation: fadeUp 1s ease-out 1.2s forwards;
    }}
    
    /* Glass Cards */
    .glass-card {{
        background: {t['glass_bg']};
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid {t['glass_border']};
        border-radius: 12px;
        padding: 24px;
        box-shadow: 0 8px 32px 0 {t['glass_shadow']};
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        margin-bottom: 20px;
    }}
    .glass-card:hover {{
        transform: translateY(-4px);
        box-shadow: 0 12px 40px 0 rgba(0, 0, 0, 0.5);
    }}
    
    /* Metrics */
    .metric-top-border {{ border-top: 3px solid {t['accent_primary']}; }}
    .metric-num {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 36px;
        font-weight: 700;
        color: {t['accent_primary']};
        margin: 10px 0 5px 0;
    }}
    .metric-icon {{ font-size: 20px; margin-bottom: 5px; opacity: 0.8;}}
    
    /* Animated Progress */
    .cinema-progress {{
        background: #0b0b10;
        border-left: 4px solid {t['accent_primary']};
        padding: 16px;
        border-radius: 8px;
        display: flex;
        align-items: center;
        margin-bottom: 20px;
    }}
    .pulse-dot {{
        height: 12px;
        width: 12px;
        background-color: {t['accent_primary']};
        border-radius: 50%;
        margin-right: 15px;
        box-shadow: 0 0 0 0 {t['accent_primary']};
        animation: pulse-gold 1.5s infinite;
    }}
    
    /* Constraint Chips */
    .chip-container {{
        display: flex; gap: 15px; overflow-x: auto; padding-bottom: 10px; scrollbar-width: none;
    }}
    .constraint-chip {{
        background: {t['glass_bg']}; padding: 10px 20px; border-radius: 30px;
        font-size: 14px; white-space: nowrap; border: 1px solid {t['glass_border']};
        transition: all 0.3s ease; display: flex; align-items: center; gap: 8px;
    }}
    .constraint-chip:hover {{
        background: {t['btn_bg']}; border-color: {t['accent_primary']};
        transform: translateY(-2px); box-shadow: 0 4px 12px {t['glass_shadow']};
    }}
    
    /* Talent Column */
    .talent-col {{
        border: 1px solid {t['talent_border']}; border-radius: 8px; padding: 15px; background: {t['talent_bg']};
    }}
    .talent-item {{
        display: flex; align-items: center; gap: 10px; margin-bottom: 8px; font-size: 14px; color: {t['text_muted']};
    }}
    .avatar-circle {{
        width: 30px; height: 30px; border-radius: 50%; background: #333;
        display: flex; align-items: center; justify-content: center;
        font-size: 12px; font-weight: bold; color: #fff;
    }}

    /* Screenplay Synopsis */
    .screenplay-box {{
        background: {t['card_bg']}; padding: 40px; border-radius: 4px; box-shadow: inset 0 0 50px {t['card_shadow']};
        font-family: 'JetBrains Mono', monospace; color: {t['text_muted']}; line-height: 1.8; font-size: 15px;
        animation: fadeUp 1s ease-out forwards;
    }}
    
    /* Critic Speedometer */
    .dial-container {{
        position: relative; width: 150px; height: 150px; display: flex; align-items: center; justify-content: center;
    }}
    .dial-circle {{
        position: absolute; top: 0; left: 0; right: 0; bottom: 0; border-radius: 50%;
        background: conic-gradient(#00E5A0 0%, {t['accent_primary']} 50%, #FF4D6D 100%);
        mask-image: radial-gradient(transparent 60%, black 61%);
        -webkit-mask-image: radial-gradient(transparent 60%, black 61%);
    }}
    .dial-inner {{
        position: relative; font-family: 'JetBrains Mono'; font-size: 32px; font-weight: bold; color: {t['text_main']}; z-index: 2;
    }}
    
    /* Passed/Failed List */
    .scorecard-item {{
        padding: 10px; border-radius: 6px; background: {t['scorecard_bg']}; margin-bottom: 8px;
        display: flex; align-items: flex-start; gap: 10px;
        animation: slideInRight 0.5s ease-out forwards; opacity: 0;
    }}
    .scorecard-item.pass {{ border-left: 3px solid #00E5A0; }}
    .scorecard-item.fail {{ border-left: 3px solid #FF4D6D; }}

    /* Button Styling */
    .stButton>button {{
        background: {t['btn_bg']} !important; color: {t['text_main']} !important; border: 1px solid {t['btn_border']} !important;
        border-radius: 30px !important; transition: all 0.3s ease !important;
    }}
    .stButton>button:hover {{
        transform: translateY(-2px); box-shadow: 0 4px 12px {t['glass_shadow']}; border-color: {t['accent_primary']} !important;
    }}
    .stButton>button[kind="primary"] {{
        background: linear-gradient(135deg, {t['accent_primary']} 0%, {t['accent_primary_dark']} 100%) !important; color: #050508 !important; border: none !important;
    }}
    .stButton>button[kind="primary"]:hover {{
        transform: translateY(-2px) scale(1.02); box-shadow: 0 4px 15px rgba(201, 168, 76, 0.4);
    }}
    
    /* Progress Bar Override */
    .stProgress > div > div > div > div {{
        background-color: {t['accent_primary']} !important;
    }}
    
    /* Animations */
    @keyframes fadeUp {{ from {{ opacity: 0; transform: translateY(20px); }} to {{ opacity: 1; transform: translateY(0); }} }}
    @keyframes fadeIn {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
    @keyframes pulse-gold {{ 
        0% {{ transform: scale(0.95); box-shadow: 0 0 0 0 {t['accent_primary']}; }} 
        70% {{ transform: scale(1); box-shadow: 0 0 0 10px rgba(0, 0, 0, 0); }} 
        100% {{ transform: scale(0.95); box-shadow: 0 0 0 0 rgba(0, 0, 0, 0); }} 
    }}
    @keyframes slideInRight {{ from {{ opacity: 0; transform: translateX(30px); }} to {{ opacity: 1; transform: translateX(0); }} }}

    /* Horizontal Navigation Container */
    div[data-testid="stRadio"] {{
        display: flex; justify-content: center; margin-bottom: 30px;
    }}
    div[data-testid="stRadio"] > div {{
        display: flex; gap: 15px; background: {t['glass_bg']};
        padding: 8px 15px; border-radius: 30px; border: 1px solid {t['glass_border']};
    }}
    /* Hide radio circle */
    div[data-testid="stRadio"] label[data-baseweb="radio"] > div:first-child {{ display: none !important; }}
    div[data-testid="stRadio"] div[role="radio"] {{ display: none !important; }}
    /* Style labels */
    div[data-testid="stRadio"] p {{
        color: {t['text_muted']}; transition: all 0.3s ease; padding: 6px 20px; font-size: 15px; font-weight: 600; margin: 0;
    }}
    div[data-testid="stRadio"] p:hover {{ color: {t['accent_primary']}; }}
    /* Active state */
    div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) p,
    div[data-testid="stRadio"] label[data-baseweb="radio"]:has([aria-checked="true"]) p {{
        color: #050508; background: linear-gradient(135deg, {t['accent_primary']} 0%, {t['accent_primary_dark']} 100%); 
        border-radius: 20px; box-shadow: 0 4px 15px rgba(201,168,76,0.4);
    }}
</style>
""", unsafe_allow_html=True)

# ── Data Fetching ───────────────────────────────────────────────────────────
@st.cache_data(ttl=10)
def fetch_analytics(endpoint: str) -> pd.DataFrame:
    try:
        res = requests.get(f"{API_URL}/analytics/{endpoint}")
        if res.status_code == 200:
            return pd.DataFrame(res.json())
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

# ── State Initialization ────────────────────────────────────────────────────
if "synopsis_result" not in st.session_state: st.session_state.synopsis_result = None
if "simplified_synopsis" not in st.session_state: st.session_state.simplified_synopsis = None
if "is_generating" not in st.session_state: st.session_state.is_generating = False
if "history" not in st.session_state: st.session_state.history = []
if "audio_bytes" not in st.session_state: st.session_state.audio_bytes = None

# Hero Banner
st.markdown("""
<div class="hero-banner">
    <div style="position: absolute; right: 20px; top: 20px; color: #00E5A0; font-family: 'JetBrains Mono'; font-size: 12px; display: flex; align-items: center; gap: 8px;">
        <span style="height: 8px; width: 8px; background: #00E5A0; border-radius: 50%; display: inline-block; box-shadow: 0 0 8px #00E5A0; animation: pulse-gold 1.5s infinite;"></span>
        STUDIO MODE ACTIVE
    </div>
    <h1 class="hero-title">Welcome, DARSH</h1>
    <div class="hero-subtitle">Let's create your next blockbuster</div>
</div>
""", unsafe_allow_html=True)

col_nav, col_theme = st.columns([4, 1])
with col_nav:
    current_page = st.radio("Navigation", ["Studio", "Analytics", "History"], horizontal=True, label_visibility="collapsed")
with col_theme:
    st.session_state.theme = st.selectbox("UI Theme", list(THEMES.keys()), index=list(THEMES.keys()).index(st.session_state.theme), label_visibility="collapsed")


if current_page == "Studio":
    # Inputs
    st.markdown("<h3 style='margin-top:0; margin-bottom: 20px; color: #F2EAE0;'>Production Parameters</h3>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c1:
        genre = st.selectbox("Genre", ["Action", "Sci-Fi", "Horror", "Comedy", "Drama", "Romance", "Crime", "Fantasy"])
    with c2:
        user_prompt = st.text_area("Creative Prompt (Optional)", placeholder="e.g. A retired hitman whose dog gets kidnapped...", height=68)
    with c3:
        budget = st.selectbox("Budget", [5_000_000, 30_000_000, 50_000_000, 100_000_000, 200_000_000], format_func=lambda x: f"${x/1000000:.0f}M", index=3)

    # Generate button
    if st.button("Generate", type="primary"):
        st.session_state.is_generating = True
        st.session_state.synopsis_result = None
        st.session_state.simplified_synopsis = None
        st.session_state.audio_bytes = None

    if st.session_state.is_generating:
        st.markdown('''
<div class="cinema-progress" style="margin-top: 20px;">
    <div class="pulse-dot"></div>
    <div style="font-family: 'JetBrains Mono'; color: #D4AF37;" id="status-text">Initializing multi-agent workflow...</div>
</div>
        ''', unsafe_allow_html=True)
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i in range(1, 90):
            time.sleep(0.05)
            progress_bar.progress(i)
            if i == 10: status_text.markdown("*Querying DuckDB for constraints...*")
            if i == 30: status_text.markdown("*Retrieving script chunks...*")
            if i == 50: status_text.markdown("*Writer Agent drafting...*")
            if i == 70: status_text.markdown("*Critic Agent evaluating...*")
            if i == 80: status_text.markdown("*Refiner Agent polishing...*")
            
        try:
            res = requests.post(
                f"{API_URL}/generate",
                json={"genre": genre, "budget": budget, "user_prompt": user_prompt, "max_iterations": 3},
                timeout=1200
            )
            if res.status_code == 200:
                result_data = res.json()
                st.session_state.synopsis_result = result_data
                st.session_state.history.insert(0, {
                    "timestamp": time.strftime("%I:%M %p"),
                    "genre": genre,
                    "budget": budget,
                    "prompt": user_prompt,
                    "result": result_data,
                    "simplified": None
                })
            else:
                st.error(f"Generation failed: {res.text}")
        except Exception as e:
            st.error(f"Connection error: {e}")
            
        progress_bar.progress(100)
        status_text.empty()
        st.session_state.is_generating = False

    if st.session_state.synopsis_result:
        res = st.session_state.synopsis_result
        score = res.get("score", 0.0)
        cycles = res.get("iterations", 0)
        synopsis = res.get("synopsis", "")
        wc = len(synopsis.split())
        conf = min(int((score / 0.8) * 100), 99) if score > 0 else 0
        
        st.markdown(f"""
<div style="display: flex; gap: 20px; justify-content: space-between; margin-top: 20px;">
    <div class="glass-card metric-top-border" style="flex:1;">
        <div style="color: #6B7280; font-size: 14px;">Market Score</div>
        <div class="metric-num">{score:.2f}</div>
    </div>
    <div class="glass-card metric-top-border" style="flex:1;">
        <div style="color: #6B7280; font-size: 14px;">Cycles</div>
        <div class="metric-num">{cycles}</div>
    </div>
    <div class="glass-card metric-top-border" style="flex:1;">
        <div style="color: #6B7280; font-size: 14px;">Words</div>
        <div class="metric-num">{wc}</div>
    </div>
    <div class="glass-card metric-top-border" style="flex:1;">
        <div style="color: #6B7280; font-size: 14px;">Confidence</div>
        <div class="metric-num" style="color: {'#00E5A0' if conf > 80 else '#D4AF37'};">{conf}%</div>
    </div>
</div>
        """, unsafe_allow_html=True)
        
        con = res.get("constraints", {})
        tags = [
            f"Budget: {con.get('target_budget_tier')}",
            f"Release: {', '.join(con.get('best_release_quarters', []))}",
            f"Target ROI: {con.get('expected_roi_multiplier', 0)}x",
        ]
        tag_html = "".join([f"<div class='constraint-chip'>{t}</div>" for t in tags])
        
        @st.cache_data(show_spinner=False, ttl=86400)
        def get_wiki_image(name):
            import requests, urllib.parse
            try:
                url = f"https://en.wikipedia.org/w/api.php?action=query&titles={urllib.parse.quote(name)}&prop=pageimages&format=json&pithumbsize=200"
                res = requests.get(url, headers={"User-Agent": "GreenlightCinema/1.0"}, timeout=2).json()
                pages = res.get("query", {}).get("pages", {})
                for page in pages.values():
                    if "thumbnail" in page:
                        return page["thumbnail"]["source"]
            except:
                pass
            return None

        def render_avatars(names):
            html = ""
            for n in names[:3]:
                img_url = get_wiki_image(n)
                if img_url:
                    html += f"<div class='talent-item'><img src='{img_url}' class='avatar-circle' style='object-fit: cover;'> {n}</div>"
                else:
                    html += f"<div class='talent-item'><div class='avatar-circle'>{n[0] if n else '?'}</div> {n}</div>"
            return html

        st.markdown(f"""
<div class="glass-card">
<h3 style="margin-top:0;">Market Constraints</h3>
<div class="chip-container">{tag_html}</div>
<div style="display: flex; gap: 15px; margin-top: 15px;">
<div class="talent-col" style="flex:1;">
<div style="color: #6B7280; font-size: 12px; margin-bottom: 10px;">DIRECTORS</div>
{render_avatars(con.get('suggested_directors', []))}
</div>
<div class="talent-col" style="flex:1;">
<div style="color: #6B7280; font-size: 12px; margin-bottom: 10px;">CAST</div>
{render_avatars(con.get('suggested_cast', []))}
</div>
<div class="talent-col" style="flex:1;">
<div style="color: #6B7280; font-size: 12px; margin-bottom: 10px;">EMERGING TALENT</div>
{render_avatars(con.get('emerging_talent', []))}
</div>
</div>
</div>
""", unsafe_allow_html=True)
        
        import re
        tokens = re.split(r'(\s+)', synopsis)
        styled_syn_words = []
        word_idx = 0
        for token in tokens:
            if token.strip():
                styled_syn_words.append(f"<span id='word-{word_idx}' style='transition: background-color 0.1s; padding: 0 2px;'>{token}</span>")
                word_idx += 1
            else:
                styled_syn_words.append(token.replace('\n', '<br>'))
        styled_syn = "".join(styled_syn_words)
        total_words = word_idx
        
        st.markdown(f"""
<div class="screenplay-box">
    {styled_syn}
</div>
        """, unsafe_allow_html=True)
        
        # Audio Player and Simplify Button
        c_a1, c_a2 = st.columns([1, 1])
        with c_a1:
            if st.button("Listen to Synopsis", use_container_width=True):
                with st.spinner("Synthesizing audio..."):
                    from gtts import gTTS
                    from io import BytesIO
                    tts = gTTS(synopsis, lang='en')
                    audio_fp = BytesIO()
                    tts.write_to_fp(audio_fp)
                    st.session_state.audio_bytes = audio_fp.getvalue()
        with c_a2:
            if st.button("Simplify Synopsis", use_container_width=True):
                with st.spinner("Rewriting..."):
                    try:
                        simp_res = requests.post(
                            f"{API_URL}/simplify",
                            json={"synopsis": synopsis},
                            timeout=120
                        )
                        if simp_res.status_code == 200:
                            simp_text = simp_res.json().get("simplified_synopsis", "")
                            st.session_state.simplified_synopsis = simp_text
                            if st.session_state.history:
                                st.session_state.history[0]["simplified"] = simp_text
                    except Exception as e:
                        st.error(f"Simplify failed: {e}")
                        
        if st.session_state.audio_bytes:
            import base64
            b64 = base64.b64encode(st.session_state.audio_bytes).decode()
            
            audio_html = f'''
            <div style="margin-top: 15px; width: 100%;">
                <audio id="synopsis-audio" controls style="width: 100%;">
                    <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
                </audio>
            </div>
            <img src="x" onerror="
                const audio = document.getElementById('synopsis-audio');
                if(audio) {{
                    audio.playbackRate = 1.25;
                    const totalWords = {total_words};
                    let lastWord = -1;
                    audio.addEventListener('timeupdate', () => {{
                        if (!audio.duration) return;
                        const progress = audio.currentTime / audio.duration;
                        const currentWord = Math.floor(progress * totalWords);
                        if (currentWord !== lastWord) {{
                            if (lastWord >= 0) {{
                                let el = window.parent.document.getElementById('word-' + lastWord) || document.getElementById('word-' + lastWord);
                                if(el) {{ el.style.backgroundColor = 'transparent'; el.style.color = 'inherit'; }}
                            }}
                            let el = window.parent.document.getElementById('word-' + currentWord) || document.getElementById('word-' + currentWord);
                            if(el) {{ el.style.backgroundColor = '#D4AF37'; el.style.color = '#170408'; el.style.borderRadius = '3px'; lastWord = currentWord; }}
                        }}
                    }});
                    audio.addEventListener('ended', () => {{
                        if (lastWord >= 0) {{
                            let el = window.parent.document.getElementById('word-' + lastWord) || document.getElementById('word-' + lastWord);
                            if(el) {{ el.style.backgroundColor = 'transparent'; el.style.color = 'inherit'; }}
                        }}
                    }});
                }}
            " style="display:none;">
            '''
            st.markdown(audio_html, unsafe_allow_html=True)
            
        if st.session_state.simplified_synopsis:
            st.info(st.session_state.simplified_synopsis)
        
        crit = res.get("critique", {})
        pc_html = "".join([f"<div class='scorecard-item pass' style='animation-delay: {0.1*i}s'>✓ {pc}</div>" for i, pc in enumerate(crit.get("passed_constraints", []))])
        fc_list = crit.get("failed_constraints", [])
        fc_html = "".join([f"<div class='scorecard-item fail' style='animation-delay: {0.1*i}s'>✗ {fc}</div>" for i, fc in enumerate(fc_list)])
            
        failed_col_html = f"""
<div style="flex: 1;">
    <h4 style="color:#FF4D6D; margin-top:0;">Failed</h4>
    {fc_html}
</div>
""" if fc_list else ""
        
        if not pc_html:
            if not fc_list and score >= 0.8:
                pc_html = "<div style='color: #6B7280; font-style: italic; margin-top: 10px;'>Perfect alignment. All constraints satisfied.</div>"
            else:
                pc_html = "<div style='color: #6B7280; font-style: italic; margin-top: 10px;'>No passed constraints listed.</div>"

        st.markdown(f"""
<div class="glass-card" style="margin-top: 20px; display: flex; gap: 30px;">
<div style="flex: 1; text-align: center; border-right: 1px solid rgba(255,255,255,0.1); display: flex; flex-direction: column; align-items: center; justify-content: center;">
<h3 style="margin-top:0;">Critic Score</h3>
<div class="dial-container">
<div class="dial-circle"></div>
<div class="dial-inner">{score:.2f}</div>
</div>
</div>
<div style="flex: 2; display: flex; gap: 20px;">
<div style="flex: 1;">
<h4 style="color:#00E5A0; margin-top:0;">Passed</h4>
{pc_html}
</div>
{failed_col_html}
</div>
</div>
        """, unsafe_allow_html=True)
        
        sugs = crit.get("suggestions", [])
        if sugs:
            with st.expander("Suggestions for Improvement"):
                for sug in sugs:
                    st.markdown(f"- {sug}")

        # Producer Report
        risk = res.get("risk_score", 0.0)
        budget_brk = res.get("budget_breakdown", {})
        
        # Format budget breakdown
        budget_html = ""
        for k, v in budget_brk.items():
            budget_html += f"""<div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
<span style="color: #6B7280;">{k}</span>
<span style="color: {t['text_main']}; font-family: 'JetBrains Mono';">{v}%</span>
</div>
<div style="background: rgba(255,255,255,0.05); height: 6px; border-radius: 3px; margin-bottom: 15px;">
<div style="background: {t['accent_primary']}; height: 100%; width: {v}%; border-radius: 3px;"></div>
</div>"""

        risk_color = "#00E5A0" if risk < 0.4 else ("#D4AF37" if risk < 0.7 else "#FF4D6D")
        risk_label = "Low Risk" if risk < 0.4 else ("Medium Risk" if risk < 0.7 else "High Risk")

        st.markdown(f"""
<div class="glass-card" style="margin-top: 20px;">
<h3 style="margin-top:0; margin-bottom: 20px;">Producer Report</h3>
<div style="display: flex; gap: 40px;">
<div style="flex: 1; border-right: 1px solid rgba(255,255,255,0.1); padding-right: 40px;">
<h4 style="margin-top:0; color: #6B7280;">Estimated Budget Breakdown</h4>
{budget_html}
</div>
<div style="flex: 1; display: flex; flex-direction: column; justify-content: center; align-items: center;">
<h4 style="margin-top:0; color: #6B7280;">Greenlight Risk Assessment</h4>
<div style="font-size: 64px; font-family: 'JetBrains Mono'; font-weight: bold; color: {risk_color};">
{risk * 100:.0f}%
</div>
<div style="background: rgba(255,255,255,0.05); padding: 8px 20px; border-radius: 20px; color: {risk_color}; border: 1px solid {risk_color}; margin-top: 10px;">
{risk_label}
</div>
</div>
</div>
</div>
        """, unsafe_allow_html=True)

elif current_page == "History":
    st.markdown("<h2 class='hero-title' style='margin-bottom:20px; border:none; animation:none;'>Generation History</h2>", unsafe_allow_html=True)
    if not st.session_state.history:
        st.info("No synopses generated yet in this session.")
    else:
        for idx, item in enumerate(st.session_state.history):
            score = item['result'].get('score', 0)
            with st.expander(f"{item['timestamp']} | {item['genre']} | Score: {score:.2f}"):
                st.caption(f"**Budget:** ${item['budget']/1000000:.0f}M  |  **Prompt:** {item['prompt'] or 'None'}")
                st.markdown(f"**Synopsis:**\n\n{item['result'].get('synopsis', '')}")
                if item.get("simplified"):
                    st.markdown("**Simplified Version:**")
                    st.info(item["simplified"])

elif current_page == "Analytics":
    st.markdown("<h2 class='hero-title' style='margin-bottom:20px; border:none; animation:none;'>Performance Analytics</h2>", unsafe_allow_html=True)
    df_genre = fetch_analytics("genre_roi")
    if not df_genre.empty:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### Top Genres by Median ROI")
            fig = px.bar(df_genre.head(15), x='genre', y='median_roi', color='avg_rating', template=t['plotly_template'])
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.markdown("### Risk vs. Reward")
            fig = px.scatter(df_genre, x='avg_budget', y='median_roi', size='movie_count', color='genre', log_x=True, template=t['plotly_template'])
            st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    c3, c4 = st.columns(2)
    with c3:
        df_dir = fetch_analytics("directors")
        if not df_dir.empty:
            st.markdown("### Top ROI Directors")
            st.dataframe(df_dir[['name', 'median_roi', 'movie_count']].head(10), hide_index=True)
    with c4:
        df_act = fetch_analytics("actors")
        if not df_act.empty:
            st.markdown("### Top ROI Actors")
            st.dataframe(df_act[['name', 'median_roi', 'movie_count']].head(10), hide_index=True)
