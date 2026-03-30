import os
from dotenv import load_dotenv
from supabase import create_client

# Load the .env file from the project root (/home/jake/speedcam/)
load_dotenv()

URL = os.getenv("SUPABASE_URL")
KEY = os.getenv("SUPABASE_SERVICE_KEY")

# Safety check for the environment variables
if not URL or not KEY:
    print("⚠️  CRITICAL: Supabase credentials missing from .env")

# Initialize the 'God Mode' client for the Pi
db = create_client(URL, KEY)

def upload_observation(lane, speed, width, ratio):
    """
    Logs a single vehicle detection to the observations table.
    We let the Database handle the 'captured_at' timestamp automatically.
    """
    print(f"📡 DB SEND: {speed}mph | {lane} | {width}px")
    
    data = {
        "speed_mph": round(speed, 1),
        "lane_direction": lane, # 'near' or 'far'
        "pixel_width": int(width),
        "aspect_ratio": round(ratio, 2)
    }
    
    try:
        # The .execute() call is vital to actually commit the data
        db.table("observations").insert(data).execute()
        print("✅ DB SUCCESS")
    except Exception as e:
        print(f"❌ DB ERROR: {e}")

def upload_env_data(env_dict):
    """
    Logs weather research data from wttr.in.
    Matches the 'Research-Grade' schema in Supabase.
    """
    print("📡 DB SEND: Weather Data")
    
    # Mapping the Pi's internal keys to the SQL column names
    formatted_weather = {
        "brightness_lux": env_dict.get('lux'),
        "precipitation_mm": env_dict.get('rain'),
        "temperature_c": env_dict.get('temp'),
        "cloud_cover_pct": env_dict.get('cloud'), # Fixed: previously caused crash
        "weather_condition": env_dict.get('cond')
    }
    
    try:
        db.table("weather_research").insert(formatted_weather).execute()
        print("✅ DB WEATHER SUCCESS")
    except Exception as e:
        print(f"❌ DB WEATHER ERROR: {e}")