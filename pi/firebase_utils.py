import firebase_admin
from firebase_admin import credentials, db
import time
import os

# Ensure the path to your key is correct
CERT_PATH = os.path.join(os.path.dirname(__file__), "serviceAccount.json")

# Initialize Firebase if it hasn't been already
if not firebase_admin._apps:
    cred = credentials.Certificate(CERT_PATH)
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://pi-speedcamera-default-rtdb.europe-west1.firebasedatabase.app/'
    })

def upload_observation(lane, speed, width, ratio):
    """ Uploads speed data with optimized keys. """
    try:
        ref = db.reference('observations')
        ref.push({
            "l": "n" if lane == "near" else "f",
            "s": speed,
            "w": width,
            "r": ratio,
            "t": int(time.time())
        })
    except Exception as e:
        print(f"❌ Speed Upload Failed: {e}")

def upload_env_data(env_dict):
    """ Uploads to the separate weather node """
    try:
        ref = db.reference('weather_research')
        ref.push(env_dict)
    except Exception as e:
        print(f"❌ Weather Upload Failed: {e}")