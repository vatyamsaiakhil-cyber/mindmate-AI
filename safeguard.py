# ─────────────────────────────────────────────
#  CRISIS DETECTION
# ─────────────────────────────────────────────

_CRISIS_KEYWORDS = [
    "suicide", "suicidal", "kill myself", "end my life",
    "want to die", "wish i was dead", "no reason to live",
    "better off dead", "better off without me",
    "self harm", "self-harm", "hurt myself", "cutting myself",
    "overdose", "hang myself", "end it all", "can't go on",
]

_CRISIS_RESPONSE = """I hear you, and I'm really glad you're talking right now. 💙

What you're feeling is real — and you don't have to face this alone.

Please reach out to someone who can truly help you:

🆘 **iCall (India):** 9152987821
🆘 **Vandrevala Foundation (24/7):** 1860-2662-345
🆘 **AASRA:** 9820466627
🆘 **International:** https://www.iasp.info/resources/Crisis_Centres/

You matter more than you know. Please reach out to them right now. 💙"""


def is_crisis(message: str) -> bool:
    """Returns True if message contains crisis keywords."""
    msg = message.lower()
    return any(k in msg for k in _CRISIS_KEYWORDS)


def get_crisis_response() -> str:
    return _CRISIS_RESPONSE


# ─────────────────────────────────────────────
#  OFF-TOPIC GUARD
# ─────────────────────────────────────────────

_OFF_TOPIC_KEYWORDS = [
    "write code", "write a program", "solve this math",
    "what is the capital", "stock price", "give me a recipe",
    "translate this", "play a game", "who won",
]

_OFF_TOPIC_RESPONSE = (
    "I'm MindMate — I'm here just for your emotional wellbeing 😊 "
    "I'm not built for that kind of request, but I'm all ears "
    "if there's something on your mind you'd like to talk about."
)


def is_off_topic(message: str) -> bool:
    """Returns True if message is clearly off-topic."""
    msg = message.lower()
    return any(k in msg for k in _OFF_TOPIC_KEYWORDS)


def get_off_topic_response() -> str:
    return _OFF_TOPIC_RESPONSE