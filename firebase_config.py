import firebase_admin
from firebase_admin import credentials, db, auth
import streamlit as st

if not firebase_admin._apps:
    firebase_creds = dict(st.secrets["firebase"])
    firebase_creds["private_key"] = firebase_creds["private_key"].replace("\\n", "\n")
    cred = credentials.Certificate(firebase_creds)
    firebase_admin.initialize_app(cred, {
        "databaseURL": "https://mentalmadhilo-6900d-default-rtdb.firebaseio.com/"
    })

def get_db_reference(path):
    return db.reference(path)