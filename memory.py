from firebase_config import get_db_reference
from datetime import datetime


# ─────────────────────────────────────────────
#  CHAT HISTORY
# ─────────────────────────────────────────────

def load_chat_history(user_id: str) -> list:
    ref = get_db_reference(f"chats/{user_id}")
    data = ref.get()
    return data if data else []


def save_chat_history(user_id: str, chat: list):
    get_db_reference(f"chats/{user_id}").set(chat)


# ─────────────────────────────────────────────
#  LONG-TERM MEMORY
# ─────────────────────────────────────────────

def load_long_term_memory(user_id: str) -> str:
    summaries = get_db_reference(f"memory/{user_id}/summaries").get()
    if not summaries:
        return ""
    lines = "\n".join(f"• {s}" for s in summaries)
    return f"Here is what you already know about this user from past conversations:\n{lines}"


def load_memory_bullets(user_id: str) -> list:
    return get_db_reference(f"memory/{user_id}/summaries").get() or []


def save_memory_summary(user_id: str, summary: str):
    ref = get_db_reference(f"memory/{user_id}/summaries")
    existing = ref.get() or []
    new_items = [
        line.strip("•- ").strip()
        for line in summary.split("\n")
        if line.strip()
    ]
    existing.extend(new_items)
    existing = existing[-20:]
    ref.set(existing)


# ─────────────────────────────────────────────
#  MOOD TRACKING
# ─────────────────────────────────────────────

def save_mood(user_id: str, emotion: str):
    ref = get_db_reference(f"moods/{user_id}")
    existing = ref.get() or []
    existing.append({
        "emotion": emotion,
        "date": datetime.now().strftime("%d %b %Y"),
        "time": datetime.now().strftime("%H:%M")
    })
    existing = existing[-30:]
    ref.set(existing)


def load_moods(user_id: str) -> list:
    return get_db_reference(f"moods/{user_id}").get() or []


# ─────────────────────────────────────────────
#  LAST SEEN
# ─────────────────────────────────────────────

def update_last_seen(user_id: str):
    get_db_reference(f"users/{user_id}/last_seen").set(
        datetime.now().strftime("%Y-%m-%d")
    )


def get_days_since_last_visit(user_id: str) -> int:
    last_seen = get_db_reference(f"users/{user_id}/last_seen").get()
    if not last_seen:
        return 0
    try:
        return (datetime.now() - datetime.strptime(last_seen, "%Y-%m-%d")).days
    except:
        return 0