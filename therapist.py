from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"

CBT_STEPS = [
    {
        "step": 1, "label": "Situation",
        "prompt": "What happened recently that's been bothering you?",
        "system": "You are a compassionate CBT therapist AI. The user described a situation. Acknowledge it warmly in 1-2 sentences, then ask: 'What thoughts went through your mind when this happened?'"
    },
    {
        "step": 2, "label": "Thoughts",
        "prompt": "What thoughts went through your mind when this happened?",
        "system": "You are a compassionate CBT therapist AI. Reflect their thoughts back gently, then ask: 'And how did those thoughts make you feel emotionally?' Name some possible emotions to help them."
    },
    {
        "step": 3, "label": "Feelings",
        "prompt": "How did those thoughts make you feel emotionally?",
        "system": "You are a compassionate CBT therapist AI. Validate their feelings fully. Then gently ask: 'Is there another way to look at this situation? What might a caring friend say to you about it?'"
    },
    {
        "step": 4, "label": "Reframe",
        "prompt": "Is there another way to look at this situation?",
        "system": "You are a compassionate CBT therapist AI. Acknowledge their reframe warmly. Build on it. Then ask: 'What is one small thing you could do today to take care of yourself?'"
    },
    {
        "step": 5, "label": "Action",
        "prompt": "What is one small thing you could do today to take care of yourself?",
        "system": "You are a compassionate CBT therapist AI. This is the final step. Celebrate their insight warmly. Summarise the full session in 3-4 warm sentences. End with specific encouragement."
    }
]


def get_cbt_step_question(step_index: int) -> str:
    return CBT_STEPS[step_index]["prompt"]


def get_cbt_step_label(step_index: int) -> str:
    return CBT_STEPS[step_index]["label"]


def process_cbt_response(step_index: int, user_response: str, session_history: list) -> str:
    step = CBT_STEPS[step_index]
    messages = [{"role": "system", "content": step["system"]}]
    for msg in session_history:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_response})
    try:
        response = client.chat.completions.create(
            model=MODEL, messages=messages, max_tokens=300, temperature=0.75
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[CBT ERROR] {e}")
        return "I'm here with you. Take your time. 💙"


def generate_insight_card(session_history: list, user_name: str) -> str:
    convo = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in session_history])
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Generate a beautiful personal insight card from this CBT session.\n"
                        "Format exactly as:\n"
                        "🌱 **Your Session Insight**\n\n"
                        "**What happened:** [1 sentence]\n"
                        "**What you felt:** [1 sentence]\n"
                        "**A new perspective:** [1 sentence]\n"
                        "**Your action:** [1 sentence]\n\n"
                        "**MindMate says:** [warm encouragement by name]"
                    )
                },
                {"role": "user", "content": f"User: {user_name}\n\n{convo}"}
            ],
            max_tokens=300, temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[INSIGHT ERROR] {e}")
        return f"🌱 **Your Session Insight**\n\nThank you for sharing today, {user_name}. Every step forward counts. 💙"