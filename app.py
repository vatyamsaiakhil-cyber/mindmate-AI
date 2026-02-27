import streamlit as st
import requests
import time
from datetime import datetime
from firebase_config import get_db_reference
from firebase_admin import auth

from brain import generate_ai_response, generate_memory_summary
from memory import (
    save_chat_history, load_long_term_memory, save_memory_summary,
    load_memory_bullets, save_mood, load_moods,
    update_last_seen, get_days_since_last_visit
)
from profile_manager import get_user_profile, get_age_group
from therapist import (
    CBT_STEPS, get_cbt_step_question, get_cbt_step_label,
    process_cbt_response, generate_insight_card
)
from journal import save_journal_entry, load_journal_entries, analyse_journal_entry
from goals import (
    save_goal, load_goals, checkin_goal, complete_goal,
    delete_goal, generate_goal_encouragement, suggest_goal
)
from mental_profile import (
    generate_mental_profile, save_profile_snapshot, load_profile_snapshot
)

st.set_page_config(page_title="MindMate AI", layout="wide", initial_sidebar_state="expanded")

API_KEY = os.getenv("FIREBASE_API_KEY")

# ─────────────────────────────────────────────
#  SESSION STATE
# ─────────────────────────────────────────────

DEFAULTS = {
    "user": None, "chat": [], "profile": {},
    "current_emotion": "neutral",
    "cbt_active": False, "cbt_step": 0, "cbt_history": [],
    "cbt_done": False, "cbt_insight": "",
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────────────────────────────
#  AUTH
# ─────────────────────────────────────────────

def signup_user(email, password, name, age):
    try:
        user = auth.create_user(email=email, password=password)
        get_db_reference(f"users/{user.uid}").set({
            "name": name, "email": email,
            "age": int(age), "age_group": get_age_group(int(age))
        })
        return True
    except Exception as e:
        print(f"[SIGNUP ERROR] {e}")
        return False

def login_user(email, password):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}"
    return requests.post(url, json={"email": email, "password": password, "returnSecureToken": True}).json()

def send_password_reset(email):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={API_KEY}"
    return requests.post(url, json={"requestType": "PASSWORD_RESET", "email": email}).json()

# ─────────────────────────────────────────────
#  EMOTION CONFIG
# ─────────────────────────────────────────────

EMOTION_COLORS = {
    "anxious": "#f59e0b", "sad": "#6366f1", "angry": "#ef4444",
    "lonely": "#8b5cf6", "hopeful": "#10b981", "stressed": "#f97316",
    "happy": "#22c55e", "neutral": "#6b7280"
}
EMOTION_EMOJI = {
    "anxious": "😰", "sad": "😢", "angry": "😠", "lonely": "🥺",
    "hopeful": "🌱", "stressed": "😤", "happy": "😊", "neutral": "😐"
}

# ─────────────────────────────────────────────
#  STYLES
# ─────────────────────────────────────────────

def apply_styles(emotion="neutral"):
    accent = EMOTION_COLORS.get(emotion, "#8b5cf6")
    st.markdown(f"""<style>
    .stApp {{ background: #0f0f0f; color: white; font-family: 'Segoe UI', sans-serif; }}
    header, footer {{ visibility: hidden; }}
    [data-testid="stSidebar"] {{
        background: #111111 !important;
        border-right: 1px solid #1f1f1f;
        min-width: 240px !important;
        max-width: 240px !important;
    }}
    .main .block-container {{ padding-top: 1rem; padding-bottom: 100px; max-width: 100%; }}
    [data-testid="stChatInput"] {{
        position: fixed !important; bottom: 0 !important;
        right: 0 !important; left: 240px !important;
        background: #0f0f0f !important; padding: 12px 24px 16px !important;
        z-index: 999 !important; border-top: 1px solid #1f1f1f; width: auto !important;
    }}
    .stChatInput textarea {{
        background: #1a1a1a !important; color: white !important;
        border-radius: 12px !important; border: 1px solid #2a2a2a !important;
    }}
    .stChatInput textarea:focus {{ border: 1px solid {accent} !important; box-shadow: 0 0 8px {accent}40 !important; }}
    .stTabs [data-baseweb="tab-list"] {{ background: #1a1a1a; border-radius: 10px; gap: 4px; padding: 4px; }}
    .stTabs [data-baseweb="tab"] {{ background: transparent; color: #888; border-radius: 8px; padding: 8px 20px; }}
    .stTabs [aria-selected="true"] {{ background: {accent}22 !important; color: {accent} !important; }}
    .message {{ animation: fadeSlide 0.3s ease forwards; }}
    @keyframes fadeSlide {{ from {{ opacity:0; transform:translateY(8px); }} to {{ opacity:1; transform:translateY(0); }} }}
    .typing span {{ height:8px;width:8px;background:#888;border-radius:50%;display:inline-block;margin:0 2px;animation:bounce 1.4s infinite ease-in-out both; }}
    .typing span:nth-child(1) {{ animation-delay:-0.32s; }}
    .typing span:nth-child(2) {{ animation-delay:-0.16s; }}
    @keyframes bounce {{ 0%,80%,100% {{ transform:scale(0); }} 40% {{ transform:scale(1); }} }}
    .card {{ background:#1a1a1a; border-left: 3px solid {accent}; border-radius:10px; padding:16px; margin-bottom:12px; }}
    .goal-card {{ background:#1a1a1a; border-radius:10px; padding:14px; margin-bottom:10px; border: 1px solid #2a2a2a; }}
    .profile-card {{ background:#1a1a1a; border-radius:12px; padding:18px; margin-bottom:14px; border-left: 3px solid {accent}; }}
    .memory-pill {{ background:#1a1a1a; border-left:3px solid {accent}; padding:8px 12px; border-radius:6px; margin-bottom:6px; font-size:13px; }}
    .mood-badge {{ display:inline-block; padding:4px 12px; border-radius:20px; font-size:12px; font-weight:600; background:{accent}22; color:{accent}; border:1px solid {accent}44; }}
    .online-dot {{ height:10px;width:10px;background-color:#22c55e;border-radius:50%;display:inline-block;margin-left:8px; }}
    .disclaimer {{ font-size:11px; color:#555; text-align:center; margin-top:4px; }}
    .insight-box {{ background: linear-gradient(135deg, #1a1a2e, #16213e); border-radius:14px; padding:20px; border:1px solid {accent}44; margin-top:16px; }}
    </style>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  CHAT BUBBLE
# ─────────────────────────────────────────────

def chat_bubble(message, role, emotion=None):
    time_now = datetime.now().strftime("%H:%M")
    if role == "user":
        align = "flex-end"
        bg    = "linear-gradient(45deg,#6366f1,#8b5cf6)"
        seen  = " ✓✓"
        em    = f" {EMOTION_EMOJI.get(emotion,'')}" if emotion else ""
    else:
        align, bg, seen, em = "flex-start", "#1f1f1f", "", ""

    st.markdown(f"""
        <div class="message" style="display:flex;justify-content:{align};margin-bottom:12px;">
            <div style="background:{bg};padding:14px 18px;border-radius:18px;max-width:78%;word-wrap:break-word;">
                {message}{em}
                <div style="font-size:11px;opacity:0.6;margin-top:6px;text-align:right;">{time_now}{seen}</div>
            </div>
        </div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  AUTH SCREEN
# ─────────────────────────────────────────────

if st.session_state.user is None:
    apply_styles()
    _, center, _ = st.columns([1, 2, 1])
    with center:
        st.markdown("""
        <div style="text-align:center;margin-bottom:30px;">
            <h1>🧠 MindMate AI</h1>
            <p style="opacity:0.7;">Your personal AI mental health companion</p>
            <p style="font-size:12px;color:#555;">Not a therapist. In crisis? Call iCall: 9152987821</p>
        </div>""", unsafe_allow_html=True)

        menu = st.radio("", ["Login", "Sign Up", "Forgot Password"], horizontal=True)

        if menu == "Login":
            email    = st.text_input("Email")
            password = st.text_input("Password", type="password")
            if st.button("Login", use_container_width=True):
                result = login_user(email, password)
                if "localId" in result:
                    st.session_state.user = result
                    st.rerun()
                else:
                    st.error("Invalid email or password.")

        elif menu == "Sign Up":
            name     = st.text_input("Full Name")
            age      = st.number_input("Age", min_value=10, max_value=100, step=1)
            email    = st.text_input("Email")
            password = st.text_input("Password", type="password")
            if st.button("Create Account", use_container_width=True):
                if not name or not email or not password:
                    st.error("Please fill in all fields.")
                elif len(password) < 6:
                    st.error("Password must be at least 6 characters.")
                else:
                    if signup_user(email, password, name, age):
                        result = login_user(email, password)
                        if "localId" in result:
                            st.session_state.user = result
                            st.rerun()
                    else:
                        st.error("Signup failed. Email may already exist.")

        elif menu == "Forgot Password":
            email = st.text_input("Enter your email")
            if st.button("Send Reset Email", use_container_width=True):
                result = send_password_reset(email)
                st.success("Reset email sent!") if "email" in result else st.error("Could not send email.")

# ─────────────────────────────────────────────
#  MAIN APP
# ─────────────────────────────────────────────

else:
    user_id = st.session_state.user.get("localId")
    if not user_id:
        st.session_state.user = None
        st.rerun()

    if not st.session_state.profile:
        st.session_state.profile = get_user_profile(user_id)

    profile   = st.session_state.profile
    user_name = profile.get("name", "Friend")
    age       = int(profile.get("age", 25))
    age_group = profile.get("age_group", get_age_group(age))

    apply_styles(st.session_state.current_emotion)

    # ════════════════
    #  SIDEBAR
    # ════════════════
    with st.sidebar:
        st.markdown(f"""
        <div style="text-align:center;padding:16px 0 12px;">
            <div style="font-size:32px;">🧠</div>
            <div style="font-weight:700;font-size:17px;">MindMate</div>
            <div style="font-size:12px;color:#555;">{user_name}</div>
        </div>""", unsafe_allow_html=True)

        badges = {"teen": "🟢 Teen", "adult": "🔵 Adult", "senior": "🟣 Senior"}
        st.markdown(f"<div style='text-align:center;margin-bottom:10px;'><span class='mood-badge'>{badges.get(age_group,'')}</span></div>", unsafe_allow_html=True)
        st.divider()

        # Current mood
        emotion = st.session_state.current_emotion
        color   = EMOTION_COLORS.get(emotion, "#6b7280")
        emoji   = EMOTION_EMOJI.get(emotion, "😐")
        st.markdown(f"""
        <div style="background:#1a1a1a;border-radius:10px;padding:12px;margin-bottom:12px;text-align:center;">
            <div style="font-size:11px;color:#555;margin-bottom:4px;">Current Mood</div>
            <div style="font-size:26px;">{emoji}</div>
            <div style="font-size:13px;color:{color};font-weight:600;">{emotion.capitalize()}</div>
        </div>""", unsafe_allow_html=True)

        # Mood timeline
        moods = load_moods(user_id)
        if moods:
            st.markdown("<div style='font-size:12px;color:#888;margin-bottom:6px;'>📊 Mood Journey</div>", unsafe_allow_html=True)
            recent   = moods[-7:]
            timeline = " → ".join([EMOTION_EMOJI.get(m["emotion"], "😐") for m in recent])
            st.markdown(f"<div style='text-align:center;font-size:18px;padding:8px;background:#1a1a1a;border-radius:8px;margin-bottom:12px;'>{timeline}</div>", unsafe_allow_html=True)

        st.divider()

        # Memory
        st.markdown("<div style='font-size:12px;color:#888;margin-bottom:6px;'>🧬 What I Know</div>", unsafe_allow_html=True)
        bullets = load_memory_bullets(user_id)
        if bullets:
            for b in bullets[-4:]:
                st.markdown(f"<div class='memory-pill'>• {b}</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div style='font-size:12px;color:#333;font-style:italic;padding:6px;'>Keep talking — I'll remember 💙</div>", unsafe_allow_html=True)

        st.divider()

        if st.button("🗑️ Clear Chat", use_container_width=True):
            if len(st.session_state.chat) >= 4:
                summary = generate_memory_summary(st.session_state.chat)
                if summary:
                    save_memory_summary(user_id, summary)
            st.session_state.chat = []
            st.rerun()

        if st.button("Logout", use_container_width=True):
            if len(st.session_state.chat) >= 4:
                summary = generate_memory_summary(st.session_state.chat)
                if summary:
                    save_memory_summary(user_id, summary)
            update_last_seen(user_id)
            for k in ["user", "chat", "profile", "cbt_active", "cbt_step",
                      "cbt_history", "cbt_done", "cbt_insight", "current_emotion"]:
                st.session_state[k] = DEFAULTS.get(k, None)
            st.rerun()

        st.markdown("<div class='disclaimer'>Not a therapist.<br>Crisis? iCall: 9152987821</div>", unsafe_allow_html=True)

    # ════════════════════════════════
    #  TABS
    # ════════════════════════════════
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "💬 Chat",
        "🧘 Therapy Session",
        "📖 Journal",
        "🎯 Goals",
        "🧬 My Profile",
        "🌬️ Breathe"
    ])

    # ══════════════════════════════════════════════
    #  TAB 1 — CHAT
    # ══════════════════════════════════════════════
    with tab1:
        st.markdown(f"""
        <div style="font-size:22px;font-weight:600;margin-bottom:4px;">
            💬 Hey, {user_name} <span class="online-dot"></span>
        </div>""", unsafe_allow_html=True)
        st.divider()

        for message in st.session_state.chat:
            em = message.get("emotion") if message["role"] == "user" else None
            chat_bubble(message["content"], message["role"], em)

        if st.session_state.chat and st.session_state.chat[-1]["role"] == "user":
            typing_placeholder = st.empty()
            typing_placeholder.markdown("""
                <div style="display:flex;justify-content:flex-start;margin-bottom:12px;">
                    <div style="background:#1f1f1f;padding:12px 18px;border-radius:18px;">
                        <div class="typing"><span></span><span></span><span></span></div>
                    </div>
                </div>""", unsafe_allow_html=True)
            time.sleep(1.2)
            typing_placeholder.empty()

            long_term_memory = load_long_term_memory(user_id)
            ai_response = generate_ai_response(
                user_message=st.session_state.chat[-1]["content"],
                age=age,
                chat_history=st.session_state.chat,
                long_term_memory=long_term_memory
            )
            st.session_state.chat.append({"role": "assistant", "content": ai_response})
            save_chat_history(user_id, st.session_state.chat)
            st.rerun()

        user_input = st.chat_input("Share your thoughts...")
        if user_input:
            from brain import detect_emotion
            emotion = detect_emotion(user_input)
            st.session_state.current_emotion = emotion
            save_mood(user_id, emotion)
            st.session_state.chat.append({"role": "user", "content": user_input, "emotion": emotion})
            save_chat_history(user_id, st.session_state.chat)
            st.rerun()

    # ══════════════════════════════════════════════
    #  TAB 2 — CBT THERAPY SESSION
    # ══════════════════════════════════════════════
    with tab2:
        st.markdown("### 🧘 AI Therapy Session")
        st.markdown("<div style='color:#888;margin-bottom:20px;'>A structured 5-step CBT session to help you process your thoughts and feelings.</div>", unsafe_allow_html=True)

        if st.session_state.cbt_done:
            st.markdown("<div class='insight-box'>", unsafe_allow_html=True)
            st.markdown(st.session_state.cbt_insight)
            st.markdown("</div>", unsafe_allow_html=True)
            if st.button("🔄 Start New Session", use_container_width=True):
                st.session_state.cbt_active  = False
                st.session_state.cbt_step    = 0
                st.session_state.cbt_history = []
                st.session_state.cbt_done    = False
                st.session_state.cbt_insight = ""
                st.rerun()

        elif not st.session_state.cbt_active:
            st.markdown("""
            <div class='card'>
            <b>What is a Therapy Session?</b><br><br>
            MindMate will guide you through 5 gentle steps based on Cognitive Behavioral Therapy (CBT):<br><br>
            1️⃣ <b>Situation</b> — What happened?<br>
            2️⃣ <b>Thoughts</b> — What did you think?<br>
            3️⃣ <b>Feelings</b> — How did you feel?<br>
            4️⃣ <b>Reframe</b> — A new perspective<br>
            5️⃣ <b>Action</b> — One small step forward<br><br>
            At the end, you'll receive a personal insight card. 🌱
            </div>""", unsafe_allow_html=True)

            if st.button("▶️ Start Session", use_container_width=True):
                st.session_state.cbt_active  = True
                st.session_state.cbt_step    = 0
                st.session_state.cbt_history = []
                first_q = get_cbt_step_question(0)
                st.session_state.cbt_history.append({"role": "assistant", "content": first_q})
                st.rerun()

        else:
            # Progress bar
            step  = st.session_state.cbt_step
            total = len(CBT_STEPS)
            st.progress((step) / total)
            label = get_cbt_step_label(min(step, total - 1))
            st.caption(f"Step {min(step+1, total)} of {total} — {label}")
            st.divider()

            # Show session history
            for msg in st.session_state.cbt_history:
                chat_bubble(msg["content"], msg["role"])

            # Input for current step
            if step < total:
                user_cbt = st.chat_input("Your response...")
                if user_cbt:
                    st.session_state.cbt_history.append({"role": "user", "content": user_cbt})

                    if step == total - 1:
                        # Final step — generate insight card
                        ai_reply = process_cbt_response(step, user_cbt, st.session_state.cbt_history)
                        st.session_state.cbt_history.append({"role": "assistant", "content": ai_reply})
                        insight = generate_insight_card(st.session_state.cbt_history, user_name)
                        st.session_state.cbt_insight = insight
                        st.session_state.cbt_done    = True
                    else:
                        ai_reply = process_cbt_response(step, user_cbt, st.session_state.cbt_history)
                        st.session_state.cbt_history.append({"role": "assistant", "content": ai_reply})
                        st.session_state.cbt_step += 1

                    st.rerun()

    # ══════════════════════════════════════════════
    #  TAB 3 — JOURNAL
    # ══════════════════════════════════════════════
    with tab3:
        st.markdown("### 📖 My Journal")
        st.markdown("<div style='color:#888;margin-bottom:16px;'>Write freely. MindMate will reflect back what it notices.</div>", unsafe_allow_html=True)

        journal_text = st.text_area("What's on your mind today?", height=180, placeholder="Write anything — there's no wrong way to journal...")

        if st.button("✨ Submit Entry", use_container_width=True):
            if journal_text.strip():
                with st.spinner("MindMate is reading your entry..."):
                    analysis = analyse_journal_entry(journal_text, user_name)
                    save_journal_entry(user_id, journal_text, analysis)

                emotion_detected = analysis.get("emotion", "neutral")
                color            = EMOTION_COLORS.get(emotion_detected, "#6b7280")
                emoji            = EMOTION_EMOJI.get(emotion_detected, "😐")

                st.markdown(f"""
                <div class='card'>
                    <div style="font-size:13px;color:#888;margin-bottom:10px;">MindMate's Reflection</div>
                    <div style="font-size:22px;margin-bottom:6px;">{emoji} <span style="color:{color};font-weight:600;">{emotion_detected.capitalize()}</span></div>
                    <div style="margin-bottom:10px;">🔍 <b>Pattern noticed:</b> {analysis.get('patterns','')}</div>
                    <div style="margin-bottom:10px;">💭 <b>Reflect on this:</b> {analysis.get('reflection','')}</div>
                    <div>💙 {analysis.get('encouragement','')}</div>
                </div>""", unsafe_allow_html=True)
            else:
                st.warning("Please write something before submitting.")

        st.divider()
        st.markdown("#### Past Entries")

        entries = load_journal_entries(user_id)
        if entries:
            for entry in reversed(entries[-10:]):
                em    = entry.get("dominant_emotion", "neutral")
                color = EMOTION_COLORS.get(em, "#6b7280")
                emoji = EMOTION_EMOJI.get(em, "😐")
                with st.expander(f"{emoji} {entry.get('date', '')} — {em.capitalize()}"):
                    st.write(entry.get("entry", ""))
                    if entry.get("patterns"):
                        st.caption(f"🔍 {entry['patterns']}")
                    if entry.get("reflection"):
                        st.caption(f"💭 {entry['reflection']}")
        else:
            st.markdown("<div style='color:#333;font-style:italic;'>No journal entries yet. Write your first one above.</div>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════
    #  TAB 4 — GOALS
    # ══════════════════════════════════════════════
    with tab4:
        st.markdown("### 🎯 My Goals")
        st.markdown("<div style='color:#888;margin-bottom:16px;'>Set small weekly mental health goals. MindMate will check in with you.</div>", unsafe_allow_html=True)

        # Add new goal
        col_input, col_btn = st.columns([4, 1])
        with col_input:
            new_goal = st.text_input("New goal", placeholder="e.g. Sleep before midnight 3 times this week")
        with col_btn:
            st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)
            if st.button("Add", use_container_width=True):
                if new_goal.strip():
                    save_goal(user_id, new_goal.strip())
                    st.rerun()

        # AI goal suggestion
        if st.button("💡 Suggest a goal for me"):
            bullets = load_memory_bullets(user_id)
            suggestion = suggest_goal(user_name, bullets, age)
            st.info(f"How about: **{suggestion}**")

        st.divider()

        goals = load_goals(user_id)
        active_goals    = [g for g in goals if not g.get("completed")]
        completed_goals = [g for g in goals if g.get("completed")]

        if active_goals:
            for i, goal in enumerate(active_goals):
                real_index = goals.index(goal)
                streak     = goal.get("streak", 0)
                checkins   = goal.get("checkins", [])
                done_count = sum(1 for c in checkins if c["status"] == "done")

                st.markdown(f"""
                <div class='goal-card'>
                    <div style="font-weight:600;margin-bottom:6px;">🎯 {goal['goal']}</div>
                    <div style="font-size:12px;color:#888;">
                        Streak: 🔥 {streak} days &nbsp;|&nbsp;
                        Done: ✅ {done_count}/{len(checkins)} check-ins &nbsp;|&nbsp;
                        Deadline: {goal.get('deadline','')}
                    </div>
                </div>""", unsafe_allow_html=True)

                c1, c2, c3, c4 = st.columns([2, 2, 2, 2])
                with c1:
                    if st.button("✅ Done", key=f"done_{i}"):
                        checkin_goal(user_id, real_index, "done")
                        st.rerun()
                with c2:
                    if st.button("⚡ Partial", key=f"partial_{i}"):
                        checkin_goal(user_id, real_index, "partial")
                        st.rerun()
                with c3:
                    if st.button("🏆 Complete", key=f"complete_{i}"):
                        complete_goal(user_id, real_index)
                        st.rerun()
                with c4:
                    if st.button("🗑️ Delete", key=f"delete_{i}"):
                        delete_goal(user_id, real_index)
                        st.rerun()

                if checkins:
                    encouragement = generate_goal_encouragement(goal, user_name)
                    st.caption(f"💙 {encouragement}")

                st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)
        else:
            st.markdown("<div style='color:#333;font-style:italic;'>No active goals. Add one above!</div>", unsafe_allow_html=True)

        if completed_goals:
            st.divider()
            st.markdown("#### 🏆 Completed Goals")
            for goal in completed_goals:
                st.markdown(f"<div style='color:#22c55e;padding:6px 0;'>✅ {goal['goal']}</div>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════
    #  TAB 5 — MENTAL HEALTH PROFILE
    # ══════════════════════════════════════════════
    with tab5:
        st.markdown("### 🧬 My Mental Health Profile")
        st.markdown("<div style='color:#888;margin-bottom:16px;'>MindMate builds a personal profile based on everything you've shared.</div>", unsafe_allow_html=True)

        existing_profile = load_profile_snapshot(user_id)

        if existing_profile:
            gen_date = existing_profile.get("generated_at", "")
            st.caption(f"Last generated: {gen_date}")

            sections = [
                ("⚡ Your Emotional Triggers",  "triggers"),
                ("💪 Your Emotional Strengths",  "strengths"),
                ("🤝 How You Like Support",       "support_style"),
                ("🌱 Your Growth",                "growth"),
            ]
            for label, key in sections:
                if existing_profile.get(key):
                    st.markdown(f"""
                    <div class='profile-card'>
                        <div style="font-size:12px;color:#888;margin-bottom:6px;">{label}</div>
                        <div>{existing_profile[key]}</div>
                    </div>""", unsafe_allow_html=True)

            if existing_profile.get("message"):
                st.markdown(f"""
                <div class='insight-box'>
                    <div style="font-size:13px;color:#888;margin-bottom:8px;">💙 MindMate's Message to You</div>
                    <div style="font-style:italic;">{existing_profile['message']}</div>
                </div>""", unsafe_allow_html=True)

        else:
            st.markdown("<div style='color:#333;font-style:italic;margin-bottom:16px;'>Your profile hasn't been generated yet. The more you talk, journal, and set goals — the more personal this becomes.</div>", unsafe_allow_html=True)

        if st.button("🔄 Generate / Refresh My Profile", use_container_width=True):
            bullets  = load_memory_bullets(user_id)
            moods    = load_moods(user_id)
            journals = load_journal_entries(user_id)
            goals    = load_goals(user_id)

            with st.spinner("MindMate is building your profile..."):
                profile_data = generate_mental_profile(user_name, age, bullets, moods, journals, goals)
                save_profile_snapshot(user_id, profile_data)
            st.rerun()

    # ══════════════════════════════════════════════
    #  TAB 6 — BREATHE
    # ══════════════════════════════════════════════
    with tab6:
        st.markdown("### 🌬️ Breathing Exercises")
        st.markdown("<div style='color:#888;margin-bottom:20px;'>Choose a technique. Follow the circle. Let your mind settle. 💙</div>", unsafe_allow_html=True)

        technique = st.radio(
            "Choose a technique:",
            ["Box Breathing (4-4-4-4)", "4-7-8 Breathing (Anxiety Relief)", "Deep Calm (5-5)"],
            horizontal=True
        )

        if technique == "Box Breathing (4-4-4-4)":
            inhale, hold1, exhale, hold2 = 4, 4, 4, 4
            color    = "#6366f1"
            name     = "Box Breathing"
            benefit  = "Used by Navy SEALs to stay calm under pressure. Perfect for stress and focus."
            steps    = ["Inhale", "Hold", "Exhale", "Hold"]
            durations= [4, 4, 4, 4]
        elif technique == "4-7-8 Breathing (Anxiety Relief)":
            inhale, hold1, exhale, hold2 = 4, 7, 8, 0
            color    = "#8b5cf6"
            name     = "4-7-8 Breathing"
            benefit  = "Dr. Andrew Weil's technique. Activates the parasympathetic nervous system. Best for anxiety and sleep."
            steps    = ["Inhale", "Hold", "Exhale"]
            durations= [4, 7, 8]
        else:
            inhale, hold1, exhale, hold2 = 5, 0, 5, 0
            color    = "#10b981"
            name     = "Deep Calm"
            benefit  = "Simple and powerful. Slows heart rate immediately. Great for beginners and elderly users."
            steps    = ["Inhale", "Exhale"]
            durations= [5, 5]

        st.markdown(f"""
        <div style="background:#1a1a1a;border-left:3px solid {color};border-radius:10px;padding:14px;margin-bottom:20px;">
            <div style="font-weight:600;color:{color};margin-bottom:4px;">{name}</div>
            <div style="font-size:13px;color:#888;">{benefit}</div>
        </div>""", unsafe_allow_html=True)

        # Animated breathing circle
        cycle_labels   = " → ".join([f"{s} ({d}s)" for s, d in zip(steps, durations)])
        total_cycle    = sum(durations)

        st.markdown(f"""
        <div style="text-align:center;margin:20px 0 10px;">
            <div style="font-size:13px;color:#555;margin-bottom:16px;">One cycle: {cycle_labels} = {total_cycle}s</div>
        </div>
        """, unsafe_allow_html=True)

        # Animated SVG breathing circle
        st.markdown(f"""
        <style>
        @keyframes breathe {{
            0%   {{ transform: scale(0.6); opacity:0.5; }}
            {'33%  { transform: scale(1.0); opacity:1.0; }' if len(steps)==3 else ''}
            {'50%  { transform: scale(1.0); opacity:1.0; }' if len(steps)==2 else ''}
            {'66%  { transform: scale(1.0); opacity:0.8; }' if len(steps)==3 else ''}
            100% {{ transform: scale(0.6); opacity:0.5; }}
        }}
        .breath-circle {{
            width: 200px;
            height: 200px;
            border-radius: 50%;
            background: radial-gradient(circle, {color}44, {color}11);
            border: 3px solid {color};
            animation: breathe {total_cycle}s ease-in-out infinite;
            margin: 0 auto;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        @keyframes phase-text {{
            0%   {{ opacity:1; }}
            90%  {{ opacity:1; }}
            100% {{ opacity:0; }}
        }}
        </style>

        <div style="text-align:center;padding:20px 0;">
            <div class="breath-circle">
                <div style="font-size:14px;color:{color};font-weight:600;text-align:center;line-height:1.5;">
                    Breathe<br>with me
                </div>
            </div>
        </div>

        <div id="phase-display" style="text-align:center;margin-top:16px;">
            <div style="font-size:28px;font-weight:700;color:{color};" id="phase-label">●</div>
        </div>

        <script>
        (function() {{
            const steps    = {steps};
            const durations= {durations};
            let step = 0;
            let elapsed = 0;

            function tick() {{
                const label = document.getElementById('phase-label');
                if(label) {{
                    const remaining = durations[step] - elapsed;
                    label.innerText = steps[step] + "... " + remaining;
                    elapsed++;
                    if(elapsed >= durations[step]) {{
                        elapsed = 0;
                        step = (step + 1) % steps.length;
                    }}
                }}
                setTimeout(tick, 1000);
            }}
            tick();
        }})();
        </script>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Guided session
        st.divider()
        st.markdown("#### 🎯 Guided Session")
        st.markdown("<div style='color:#888;font-size:13px;margin-bottom:12px;'>MindMate will guide you through 3 full cycles step by step.</div>", unsafe_allow_html=True)

        if st.button("▶️ Start Guided Session", use_container_width=True):
            progress_bar = st.progress(0)
            phase_display = st.empty()
            cycle_display = st.empty()

            total_cycles = 3
            total_steps  = len(steps)

            for cycle in range(total_cycles):
                cycle_display.markdown(f"<div style='text-align:center;font-size:13px;color:#555;'>Cycle {cycle+1} of {total_cycles}</div>", unsafe_allow_html=True)

                for s_idx, (step_name, duration) in enumerate(zip(steps, durations)):
                    for sec in range(duration):
                        remaining = duration - sec
                        overall   = (cycle * total_steps * max(durations) + s_idx * max(durations) + sec)
                        total_secs= total_cycles * total_steps * max(durations)
                        progress  = min(overall / total_secs, 1.0)
                        progress_bar.progress(progress)

                        if step_name == "Inhale":
                            emoji_phase = "🫁"
                            bg_color    = color
                        elif step_name == "Hold":
                            emoji_phase = "⏸️"
                            bg_color    = "#f59e0b"
                        else:
                            emoji_phase = "💨"
                            bg_color    = "#10b981"

                        phase_display.markdown(f"""
                        <div style="text-align:center;padding:30px;">
                            <div style="font-size:48px;margin-bottom:8px;">{emoji_phase}</div>
                            <div style="font-size:32px;font-weight:700;color:{bg_color};">{step_name}</div>
                            <div style="font-size:48px;font-weight:800;color:{bg_color};margin-top:8px;">{remaining}</div>
                            <div style="font-size:13px;color:#555;margin-top:8px;">seconds</div>
                        </div>""", unsafe_allow_html=True)
                        time.sleep(1)

            progress_bar.progress(1.0)
            phase_display.markdown(f"""
            <div style="text-align:center;padding:30px;">
                <div style="font-size:48px;">✨</div>
                <div style="font-size:22px;font-weight:600;color:{color};margin-top:8px;">Well done, {user_name}!</div>
                <div style="font-size:14px;color:#888;margin-top:6px;">3 cycles complete. Take a moment to notice how you feel. 💙</div>
            </div>""", unsafe_allow_html=True)
            cycle_display.empty()

        # Tips
        st.divider()
        st.markdown("#### 💡 When to Use Each Technique")
        st.markdown("""
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-top:8px;">
            <div style="background:#1a1a1a;border-radius:10px;padding:14px;border-top:3px solid #6366f1;">
                <div style="font-weight:600;color:#6366f1;margin-bottom:6px;">Box Breathing</div>
                <div style="font-size:12px;color:#888;">Before exams, presentations, or any high-pressure situation.</div>
            </div>
            <div style="background:#1a1a1a;border-radius:10px;padding:14px;border-top:3px solid #8b5cf6;">
                <div style="font-weight:600;color:#8b5cf6;margin-bottom:6px;">4-7-8 Breathing</div>
                <div style="font-size:12px;color:#888;">When anxious, panicking, or struggling to sleep at night.</div>
            </div>
            <div style="background:#1a1a1a;border-radius:10px;padding:14px;border-top:3px solid #10b981;">
                <div style="font-weight:600;color:#10b981;margin-bottom:6px;">Deep Calm</div>
                <div style="font-size:12px;color:#888;">Any time you need a quick reset. Simple, gentle, always effective.</div>
            </div>
        </div>
        """, unsafe_allow_html=True)