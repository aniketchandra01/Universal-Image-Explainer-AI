import streamlit as st
import google.generativeai as genai
from PIL import Image
import io, time, hashlib

st.set_page_config(page_title="Image Explainer AI", page_icon="🔮", layout="centered")

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

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔮 Image Explainer")
    st.divider()
    api_key = st.text_input("Gemini API Key", type="password", placeholder="AIzaSy...")
    st.divider()
    mode = st.radio("Mode", [
        "📖 Story",
        "📊 Diagram",
        "📝 Notes",
        "🧠 Concept",
        "🧒 ELI10",
        "🕸️ Mind Map",
        "📋 Quiz",
        "🔊 Voice",
    ])

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("## 🔮 Universal Image Explainer")
st.caption("Upload an image · pick a mode · get an instant explanation")
st.divider()

# ── Upload ────────────────────────────────────────────────────────────────────
uploaded = st.file_uploader("Upload image", type=["png","jpg","jpeg","webp"])

if uploaded:
    img = Image.open(uploaded).convert("RGB")
    # Shrink image to reduce token usage — max 512px on longest side
    img.thumbnail((512, 512))
    st.image(img, use_container_width=True)

# ── Short prompts (keep token count minimal) ──────────────────────────────────
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

# ── Run ───────────────────────────────────────────────────────────────────────
if uploaded and api_key:
    if st.button(f"Run {mode}", use_container_width=True):

        # Cache by image hash + mode so same image never re-calls API
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=60)
        cache_key = hashlib.md5(buf.getvalue()).hexdigest() + mode

        if cache_key in st.session_state:
            st.success("⚡ From cache")
            st.markdown(f"<div class='result'>{st.session_state[cache_key]}</div>",
                        unsafe_allow_html=True)
        else:
            # Enforce 6-second cooldown between API calls (free tier = 15 RPM)
            last = st.session_state.get("last_call", 0)
            wait = 6 - (time.time() - last)
            if wait > 0:
                with st.spinner(f"Cooling down… {int(wait)+1}s"):
                    time.sleep(wait + 0.5)

            with st.spinner("Thinking…"):
                try:
                    st.session_state["last_call"] = time.time()
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel("gemini-2.0-flash-lite")
                    resp  = model.generate_content([PROMPTS[mode], img])
                    text  = resp.text
                    st.session_state[cache_key] = text
                    st.markdown(f"<div class='result'>{text}</div>",
                                unsafe_allow_html=True)

                    if mode == "🔊 Voice":
                        from gtts import gTTS
                        tts = gTTS(text=text, lang="en")
                        audio = io.BytesIO()
                        tts.write_to_fp(audio); audio.seek(0)
                        st.audio(audio.read(), format="audio/mp3")

                except Exception as e:
                    err = str(e)
                    if "429" in err:
                        st.error("Rate limit hit. Wait 60 seconds and try again.")
                    elif "API_KEY_INVALID" in err or "expired" in err:
                        st.error("Invalid or expired API key. Get a new one at aistudio.google.com")
                    else:
                        st.error(f"Error: {err}")

elif uploaded and not api_key:
    st.info("Add your Gemini API key in the sidebar to continue.")
