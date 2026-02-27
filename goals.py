from groq import Groq
from firebase_config import get_db_reference
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"


def save_goal(user_id: str, goal_text: str):
    ref = get_db_reference(f"goals/{user_id}")
    existing = ref.get() or []
    existing.append({
        "goal": goal_text,
        "created": datetime.now().strftime("%d %b %Y"),
        "deadline": (datetime.now() + timedelta(days=7)).strftime("%d %b %Y"),
        "checkins": [],
        "completed": False,
        "streak": 0
    })
    ref.set(existing)


def load_goals(user_id: str) -> list:
    return get_db_reference(f"goals/{user_id}").get() or []


def checkin_goal(user_id: str, goal_index: int, status: str):
    ref = get_db_reference(f"goals/{user_id}")
    goals = ref.get() or []
    if goal_index >= len(goals):
        return
    if "checkins" not in goals[goal_index]:
        goals[goal_index]["checkins"] = []
    if "streak" not in goals[goal_index]:
        goals[goal_index]["streak"] = 0

    goals[goal_index]["checkins"].append({
        "date": datetime.now().strftime("%d %b %Y"),
        "status": status
    })
    if status == "done":
        goals[goal_index]["streak"] = goals[goal_index].get("streak", 0) + 1
    elif status == "missed":
        goals[goal_index]["streak"] = 0
    ref.set(goals)


def complete_goal(user_id: str, goal_index: int):
    ref = get_db_reference(f"goals/{user_id}")
    goals = ref.get() or []
    if goal_index < len(goals):
        goals[goal_index]["completed"] = True
        ref.set(goals)


def delete_goal(user_id: str, goal_index: int):
    ref = get_db_reference(f"goals/{user_id}")
    goals = ref.get() or []
    if goal_index < len(goals):
        goals.pop(goal_index)
        ref.set(goals)


def generate_goal_encouragement(goal: dict, user_name: str) -> str:
    streak = goal.get("streak", 0)
    checkins = goal.get("checkins", [])
    done = sum(1 for c in checkins if c["status"] == "done")
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a warm accountability partner. Write 1 encouraging sentence about their goal progress. Be specific and address them by name."
                },
                {
                    "role": "user",
                    "content": f"User: {user_name}\nGoal: {goal['goal']}\nStreak: {streak} days\nCompleted {done}/{len(checkins)} check-ins"
                }
            ],
            max_tokens=80, temperature=0.75
        )
        return response.choices[0].message.content.strip()
    except:
        return f"Keep going, {user_name}! Every small step counts. 💙"


def suggest_goal(user_name: str, memory_bullets: list, age: int) -> str:
    memory = "\n".join(memory_bullets[-5:]) if memory_bullets else "No memories yet."
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "Suggest ONE small, specific, achievable 7-day mental health goal based on what you know about the user. Under 15 words. Return ONLY the goal text."
                },
                {"role": "user", "content": f"User: {user_name}, Age: {age}\n{memory}"}
            ],
            max_tokens=40, temperature=0.8
        )
        return response.choices[0].message.content.strip()
    except:
        return "Talk to one person I trust this week"