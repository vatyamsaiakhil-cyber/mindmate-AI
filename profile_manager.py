from firebase_config import get_db_reference


def get_user_profile(user_id: str) -> dict:
    """Fetch full user profile from Firebase."""
    ref = get_db_reference(f"users/{user_id}")
    data = ref.get()
    return data if data else {}


def get_age_group(age: int) -> str:
    """Return age group label based on age."""
    if age <= 19:
        return "teen"
    elif age <= 55:
        return "adult"
    else:
        return "senior"