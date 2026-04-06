import os
from dotenv import load_dotenv
from supabase import create_client

# Load the .env file from the project root (/home/jake/speedcam/)
load_dotenv()

URL = os.getenv("SUPABASE_URL")
KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not URL or not KEY:
    print("⚠️  CRITICAL: Supabase credentials missing from .env")

# Initialize Supabase client
db = create_client(URL, KEY)

def get_active_calibration_id():
    """Fetches the ID of the currently active calibration from the DB."""
    try:
        response = db.table('calibrations').select("id").eq("active", True).order("created_at", desc=True).limit(1).execute()
        return response.data[0]['id'] if response.data else None
    except Exception as e:
        print(f"❌ DB ERROR fetching calibration: {e}")
        return None

def upload_observation(lane, speed, width, ratio, cal_id):
    """Logs a vehicle detection tagged with a calibration ID."""
    print(f"📡 DB SEND: {speed}mph | {lane} | CalID: {cal_id}")
    
    data = {
        "speed_mph": round(speed, 1),
        "lane_direction": lane,
        "pixel_width": int(width),
        "aspect_ratio": round(ratio, 2),
        "calibration_id": cal_id  # The essential tag for rescaling
    }
    
    try:
        db.table("observations").insert(data).execute()
        print("✅ DB SUCCESS")
    except Exception as e:
        print(f"❌ DB ERROR: {e}")

def upload_env_data(env_dict):
    """Logs weather/light data to the research table."""
    formatted_weather = {
        "brightness_lux": env_dict.get('lux'),
        "precipitation_mm": env_dict.get('rain'),
        "temperature_c": env_dict.get('temp'),
        "cloud_cover_pct": env_dict.get('cloud'),
        "weather_condition": env_dict.get('cond')
    }
    try:
        db.table("weather_research").insert(formatted_weather).execute()
        print("✅ DB WEATHER SUCCESS")
    except Exception as e:
        print(f"❌ DB WEATHER ERROR: {e}")

def upload_calibration(mpp_near, mpp_far, notes="Manual GUI Calibration"):
    """Logs a new calibration session and returns its ID."""
    data = {
        "mpp_near": mpp_near,
        "mpp_far": mpp_far,
        "notes": notes,
        "active": True
    }
    try:
        response = db.table('calibrations').insert(data).execute()
        return response.data[0]['id'] if response.data else None
    except Exception as e:
        print(f"❌ DB CALIBRATION ERROR: {e}")
        return None