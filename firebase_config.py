import firebase_admin
from firebase_admin import credentials, db, auth

cred = credentials.Certificate("firebase_key.json")

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred, {
        "databaseURL": "https://mentalmadhilo-6900d-default-rtdb.firebaseio.com/"
    })

def get_db_reference(path):
    return db.reference(path)