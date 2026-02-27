from groq import Groq
from firebase_config import get_db_reference
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"


def save_journal_entry(user_id: str, entry: str, analysis: dict):
    ref = get_db_reference(f"journal/{user_id}")
    existing = ref.get() or []
    existing.append({
        "date": datetime.now().strftime("%d %b %Y, %H:%M"),
        "entry": entry,
        "dominant_emotion": analysis.get("emotion", "neutral"),
        "patterns": analysis.get("patterns", ""),
        "reflection": analysis.get("reflection", ""),
        "encouragement": analysis.get("encouragement", ""),
    })
    existing = existing[-30:]
    ref.set(existing)


def load_journal_entries(user_id: str) -> list:
    return get_db_reference(f"journal/{user_id}").get() or []


def analyse_journal_entry(entry: str, user_name: str) -> dict:
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Analyse this journal entry. Respond in EXACT format:\n"
                        "EMOTION: [anxious/sad/angry/lonely/hopeful/stressed/happy/neutral]\n"
                        "PATTERN: [1 sentence about a theme noticed]\n"
                        "REFLECTION: [1 thoughtful question to go deeper]\n"
                        "ENCOURAGEMENT: [1 warm encouraging sentence by name]\n"
                        "Nothing outside this format."
                    )
                },
                {"role": "user", "content": f"User: {user_name}\n\n{entry}"}
            ],
            max_tokens=200, temperature=0.6
        )
        text = response.choices[0].message.content.strip()
        result = {}
        for line in text.split("\n"):
            for key in ["EMOTION", "PATTERN", "REFLECTION", "ENCOURAGEMENT"]:
                if line.startswith(f"{key}:"):
                    result[key.lower() if key != "PATTERN" else "patterns"] = line.replace(f"{key}:", "").strip()
        # fix key mapping
        if "emotion" not in result: result["emotion"] = "neutral"
        if "pattern" in result:
            result["patterns"] = result.pop("pattern")
        return result
    except Exception as e:
        print(f"[JOURNAL ERROR] {e}")
        return {
            "emotion": "neutral",
            "patterns": "You shared something meaningful today.",
            "reflection": "What feeling stays with you after writing this?",
            "encouragement": f"Thank you for taking time to reflect, {user_name}. 💙"
        }