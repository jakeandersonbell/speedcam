import os
from dotenv import load_dotenv
from supabase import create_client

# Load the hidden .env file
load_dotenv()

URL = os.getenv("SUPABASE_URL")
# The Pi uses the SERVICE KEY to bypass RLS for writing
KEY = os.getenv("SUPABASE_SERVICE_KEY")

db = create_client(URL, KEY)

def upload_observation(lane, speed, width, ratio):
    data = {
        "speed_mph": round(speed, 1),
        "lane_direction": lane,
        "pixel_width": int(width),
        "aspect_ratio": round(ratio, 2)
    }
    try:
        db.table("observations").insert(data).execute()
    except Exception as e:
        print(f"❌ Supabase Speed Error: {e}")

def upload_env_data(env_dict):
    formatted_env = {
        "brightness_lux": round(env_dict['lux'], 2),
        "precipitation_mm": env_dict['rain'],
        "temperature_c": env_dict['temp'],
        "cloud_cover_pct": env_dict['cloud'],
        "weather_condition": env_dict['cond']
    }
    try:
        db.table("weather_research").insert(formatted_env).execute()
    except Exception as e:
        print(f"❌ Supabase Weather Error: {e}")