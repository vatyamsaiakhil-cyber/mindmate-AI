from groq import Groq
from firebase_config import get_db_reference
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"


def generate_mental_profile(user_name: str, age: int, memory_bullets: list,
                              moods: list, journal_entries: list, goals: list) -> dict:
    mood_list   = ", ".join([m["emotion"] for m in moods[-20:]]) if moods else "No mood data yet"
    memory_text = "\n".join(memory_bullets[-10:]) if memory_bullets else "No memories yet"
    goal_list   = "\n".join([g["goal"] for g in goals if not g.get("completed")]) if goals else "No active goals"
    journal_text= "\n".join([j["entry"][:100] for j in journal_entries[-5:]]) if journal_entries else "No journal entries"

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Generate a personal mental health profile. Respond in EXACT format:\n"
                        "TRIGGERS: [2-3 emotional triggers]\n"
                        "STRENGTHS: [2-3 emotional strengths]\n"
                        "SUPPORT_STYLE: [how they prefer support — 1 sentence]\n"
                        "GROWTH: [one area of growth — 1 sentence]\n"
                        "MESSAGE: [personal warm message by name — 2 sentences]\n"
                        "Nothing outside this format."
                    )
                },
                {
                    "role": "user",
                    "content": (
                        f"User: {user_name}, Age: {age}\n"
                        f"Moods: {mood_list}\n"
                        f"Memories:\n{memory_text}\n"
                        f"Goals:\n{goal_list}\n"
                        f"Journal snippets:\n{journal_text}"
                    )
                }
            ],
            max_tokens=350, temperature=0.7
        )
        text = response.choices[0].message.content.strip()
        result = {}
        for line in text.split("\n"):
            for key in ["TRIGGERS", "STRENGTHS", "SUPPORT_STYLE", "GROWTH", "MESSAGE"]:
                if line.startswith(f"{key}:"):
                    result[key.lower()] = line.replace(f"{key}:", "").strip()
        result["generated_at"] = datetime.now().strftime("%d %b %Y")
        return result
    except Exception as e:
        print(f"[PROFILE ERROR] {e}")
        return {
            "triggers": "Still learning about your triggers",
            "strengths": "Courage to seek support",
            "support_style": "You appreciate warm, non-judgmental conversations",
            "growth": "You're building self-awareness with every conversation",
            "message": f"Thank you for trusting MindMate, {user_name}. 💙",
            "generated_at": datetime.now().strftime("%d %b %Y")
        }


def save_profile_snapshot(user_id: str, profile: dict):
    get_db_reference(f"mental_profile/{user_id}").set(profile)


def load_profile_snapshot(user_id: str) -> dict:
    return get_db_reference(f"mental_profile/{user_id}").get() or {}