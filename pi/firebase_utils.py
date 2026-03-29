import firebase_admin
from firebase_admin import credentials, db
import time
import os

# 1. Path to your private key
# Make sure this file is in the same folder as main.py
JSON_KEY_PATH = "pi/serviceAccount.json"

# 2. Initialize the SDK
if not firebase_admin._apps:
    cred = credentials.Certificate(JSON_KEY_PATH)
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://pi-speedcamera-default-rtdb.europe-west1.firebasedatabase.app/'
    })

# 3. Export the database object for use in main.py
# This allows main.py to do 'from firebase_utils import db'
root_ref = db.reference('/')

def upload_observation(lane, speed, width, ratio, img_name=""):
    """
    Sends a single car detection to the 'observations' node.
    """
    try:
        obs_ref = db.reference('observations')
        
        new_data = {
            "s": round(speed, 1),       # Speed in MPH
            "t": int(time.time()),      # Unix Timestamp
            "lane": lane,               # 'near' or 'far'
            "w": int(width),            # Vehicle width
            "r": round(ratio, 2),       # Height/Width ratio
            "img": img_name             # NEW: name of the saved image
        }
        
        obs_ref.push(new_data)
        
    except Exception as e:
        print(f"⚠️ Firebase Upload Failed: {e}")

# Note: You can also export the raw 'db' object so main.py 
# can do summaries or transactions directly.