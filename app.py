import streamlit as st
import google.generativeai as genai
from PIL import Image
import io, time, hashlib, random

# ── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="Image Explainer AI", page_icon="🔮", layout="centered")

# ── Styling ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
* { font-family: 'Inter', sans-serif; }
body, .stApp { background: #0a0a0f; color: #e8e4ff; }
.stButton>button {
    background: linear-gradient(135deg,#7c3aed,#a855f7);
    color:white; border:none; border-radius:10px;
    font-weight:700; padding:.55rem 1.4rem;
}
.stButton>button:disabled {
    background: #1e1b2e !important;
    color: #4a456e !important;
}
.stTextInput>div>div>input, .stFileUploader>div {
    background:#110f22 !important; border:1px solid rgba(124,58,237,.3) !important;
    border-radius:10px !important; color:#e8e4ff !important;
}
.stRadio label { color:#9d8fcf !important; }
.result {
    background:#110f22; border:1px solid rgba(124,58,237,.3);
    border-radius:14px; padding:1.4rem; margin-top:1rem;
    line-height:1.8; color:#e8e4ff; white-space:pre-wrap;
}
hr { border-color: rgba(124,58,237,.2) !important; }
</style>
""", unsafe_allow_html=True)

# ── Cached Model Initialization ─────────────────────────────────────────────
@st.cache_resource
def get_gemini_model(api_key):
    genai.configure(api_key=api_key)
    # 2026 Stable Standard: gemini-2.5-flash
    # 2026 Cutting Edge: gemini-3-flash
    return genai.GenerativeModel("gemini-2.5-flash")

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔮 Image Explainer")
    st.divider()
    api_key = st.text_input("Gemini API Key", type="password", placeholder="AIzaSy...")
    st.divider()
    mode = st.radio("Mode", [
        "📖 Story", "📊 Diagram", "📝 Notes", "🧠 Concept", 
        "🧒 ELI10", "🕸️ Mind Map", "📋 Quiz", "🔊 Voice",
    ])

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("## 🔮 Universal Image Explainer")
st.caption("Upload an image · pick a mode · get an instant explanation")
st.divider()

# ── Upload ────────────────────────────────────────────────────────────────────
uploaded = st.file_uploader("Upload image", type=["png","jpg","jpeg","webp"])

if uploaded:
    img = Image.open(uploaded).convert("RGB")
    img.thumbnail((512, 512))
    st.image(img, use_container_width=True)

# ── Prompts ──────────────────────────────────────────────────────────────────
PROMPTS = {
    "📖 Story":    "Write a short 2-paragraph creative story inspired by this image.",
    "📊 Diagram":  "Briefly explain what this chart/diagram shows. Key type, data, and insight only.",
    "📝 Notes":    "Give concise structured notes from this image. Use bullet points.",
    "🧠 Concept":  "Explain the main concept in this image clearly and concisely.",
    "🧒 ELI10":    "Explain this image simply to a 10-year-old in 3-4 short sentences.",
    "🕸️ Mind Map": "List the central topic and 5 key branches as: Central: ...\n- Branch: detail\n- Branch: detail ...",
    "📋 Quiz":     "Write 3 short multiple-choice questions (A B C D) about this image. Include answers.",
    "🔊 Voice":    "Describe this image in 2-3 natural spoken sentences.",
}

# ── Logic ─────────────────────────────────────────────────────────────────────
if uploaded and api_key:
    # Cooldown Logic
    last_call = st.session_state.get("last_call", 0)
    elapsed = time.time() - last_call
    cooldown_limit = 6.0
    wait_remaining = max(0.0, cooldown_limit - elapsed)

    if wait_remaining > 0:
        st.warning(f"⏳ Cooling down: {wait_remaining:.1f}s remaining.")
        run_disabled = True
    else:
        run_disabled = False

    if st.button(f"Run {mode}", use_container_width=True, disabled=run_disabled):
        # Cache check
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=60)
        cache_key = hashlib.md5(buf.getvalue()).hexdigest() + mode

        if cache_key in st.session_state:
            st.success("⚡ From cache")
            st.markdown(f"<div class='result'>{st.session_state[cache_key]}</div>", unsafe_allow_html=True)
        else:
            with st.spinner("Thinking..."):
                try:
                    model = get_gemini_model(api_key)
                    max_retries = 3
                    
                    for attempt in range(max_retries):
                        try:
                            # Set timestamp immediately before call
                            st.session_state["last_call"] = time.time()
                            
                            resp = model.generate_content([PROMPTS[mode], img])
                            text = resp.text
                            
                            # Success: Cache and Display
                            st.session_state[cache_key] = text
                            st.markdown(f"<div class='result'>{text}</div>", unsafe_allow_html=True)

                            if mode == "🔊 Voice":
                                from gtts import gTTS
                                tts = gTTS(text=text, lang="en")
                                audio = io.BytesIO()
                                tts.write_to_fp(audio); audio.seek(0)
                                st.audio(audio.read(), format="audio/mp3")
                            
                            break # Break retry loop on success

                        except Exception as e:
                            err = str(e)
                            if "429" in err and attempt < max_retries - 1:
                                sleep_time = (2 ** (attempt + 1)) + (random.randint(0, 1000) / 1000)
                                st.toast(f"Rate limit hit. Retrying in {sleep_time:.1f}s...", icon="⚠️")
                                time.sleep(sleep_time)
                            else:
                                raise e # Pass to outer error handler

                except Exception as e:
                    err = str(e)
                    if "429" in err:
                        st.error("Rate limit reached even after retries. Please wait 60 seconds.")
                    elif "API_KEY_INVALID" in err:
                        st.error("Invalid API key. Please check your sidebar settings.")
                    else:
                        st.error(f"Something went wrong: {err}")

elif uploaded and not api_key:
    st.info("🔑 Please enter your Gemini API key in the sidebar.")

elif not uploaded:
    st.info("📸 Upload an image to get started.")

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.caption("Built with Streamlit & Gemini Pro Vision")