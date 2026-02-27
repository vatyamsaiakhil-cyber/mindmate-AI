from groq import Groq
import os
from dotenv import load_dotenv
from safeguard import is_crisis, get_crisis_response, is_off_topic, get_off_topic_response

load_dotenv()

# Read from .env — if not found, fall back to direct key
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)

MODEL="llama-3.3-70b-versatile"


# ─────────────────────────────────────────────
#  PERSONA BUILDER
# ─────────────────────────────────────────────

def build_system_prompt(age: int, long_term_memory: str = "") -> str:

    if age <= 19:
        base = """
You are MindMate — a warm, supportive best friend for a teenager.
TONE: Casual, relatable, non-judgmental. Like a cool older sibling.
FOCUS: Friendships, identity, academic stress, heartbreak, social anxiety, self-esteem.
RULES:
- Validate their feelings first, always.
- Ask ONE follow-up question at a time.
- Never lecture or be preachy.
- Keep responses short and warm.
- Never give medical advice or diagnose anything.
"""

    elif 20 <= age <= 55:
        base = """
You are MindMate — a calm, grounded emotional support companion for adults.
TONE: Warm but realistic. Treat them as a capable adult with real, complex problems.
FOCUS: Career burnout, relationships, parenting stress, financial anxiety, work-life balance.
RULES:
- Acknowledge the weight of their situation before offering perspective.
- Offer gentle, practical insight when appropriate — never commanding.
- Validate emotions first. Always.
- Avoid toxic positivity.
- Never give medical advice or diagnose anything.
"""

    else:
        base = """
You are MindMate — a warm, patient, and wise companion for elderly users.
TONE: Gentle, slow-paced, deeply respectful of their life experience.
FOCUS: Loneliness, grief and loss, meaning and legacy, spirituality, family relationships.
RULES:
- Be a comforting presence — not a problem-solver.
- Honour their life experience deeply.
- Encourage storytelling and reflection.
- Offer reassurance over advice.
- Never give medical advice or diagnose anything.
"""

    if long_term_memory:
        base += f"\n\n{long_term_memory}"

    return base.strip()


# ─────────────────────────────────────────────
#  MEMORY SUMMARY GENERATOR
# ─────────────────────────────────────────────

def generate_memory_summary(chat_history: list):
    if len(chat_history) < 4:
        return None

    recent = chat_history[-10:]
    convo_text = "\n".join(
        f"{m['role'].upper()}: {m['content']}" for m in recent
    )

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a memory assistant for a mental health AI. "
                        "Extract 1 to 3 short bullet points about what the USER shared — "
                        "their struggles, feelings, or important life context. "
                        "Each point must be under 15 words. "
                        "Output ONLY the bullet points. No preamble."
                    )
                },
                {"role": "user", "content": convo_text}
            ],
            max_tokens=120,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[MEMORY ERROR] {e}")
        return None


# ─────────────────────────────────────────────
#  MAIN RESPONSE GENERATOR
# ─────────────────────────────────────────────

def generate_ai_response(user_message: str, age: int,
                          chat_history: list = None,
                          long_term_memory: str = "") -> str:

    # 1. Crisis check — always first
    if is_crisis(user_message):
        return get_crisis_response()

    # 2. Off-topic check
    if is_off_topic(user_message):
        return get_off_topic_response()

    # 3. Build system prompt with memory
    system_prompt = build_system_prompt(age, long_term_memory)

    # 4. Build messages — full history for context
    messages = [{"role": "system", "content": system_prompt}]

    if chat_history:
        for msg in chat_history[-20:]:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
    else:
        messages.append({"role": "user", "content": user_message})

    # 5. Call Groq — print real error if it fails
    try:
        completion = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.75,
            max_tokens=300,
        )
        return completion.choices[0].message.content.strip()

    except Exception as e:
        print(f"[GROQ ERROR] {e}")  # this will show in your terminal
        return f"⚠️ Groq Error: {str(e)}"  # show real error in chat for debugging

# ─────────────────────────────────────────────
#  EMOTION DETECTOR
# ─────────────────────────────────────────────

def detect_emotion(message: str) -> str:
    """Silently detect emotion from user message."""
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an emotion detector. Given a message, return ONLY one word "
                        "from this list: anxious, sad, angry, lonely, hopeful, stressed, happy, neutral. "
                        "No explanation. No punctuation. Just the single word."
                    )
                },
                {"role": "user", "content": message}
            ],
            max_tokens=5,
            temperature=0.1,
        )
        emotion = response.choices[0].message.content.strip().lower()
        valid = ["anxious", "sad", "angry", "lonely", "hopeful", "stressed", "happy", "neutral"]
        return emotion if emotion in valid else "neutral"
    except Exception as e:
        print(f"[EMOTION ERROR] {e}")
        return "neutral"