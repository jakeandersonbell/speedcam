import os
import requests
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime

load_dotenv()

SUP_URL = os.getenv("SUPABASE_URL")
SUP_KEY = os.getenv("SUPABASE_SERVICE_KEY")
FB_BASE = os.getenv("FIREBASE_URL")

db = create_client(SUP_URL, SUP_KEY)

def convert_time(unix_ts):
    if unix_ts is None:
        return None
    try:
        return datetime.fromtimestamp(int(unix_ts)).isoformat()
    except (ValueError, TypeError):
        return None

def migrate_data(node_name, table_name, mapping_func):
    print(f"🛰️ Migrating {node_name}...")
    response = requests.get(f"{FB_BASE}/{node_name}.json")
    data = response.json()
    
    if not data:
        print(f"❓ No data found in {node_name}. Skipping.")
        return
    
    batch = []
    skipped = 0
    
    for key, val in data.items():
        # Skip if the record isn't a dictionary (happens with weird Firebase metadata)
        if not isinstance(val, dict):
            skipped += 1
            continue
            
        mapped = mapping_func(val)
        
        # Only add to batch if we successfully got a timestamp
        if mapped and mapped.get("captured_at"):
            batch.append(mapped)
        else:
            skipped += 1
    
    if batch:
        print(f"🚀 Pushing {len(batch)} records to {table_name}...")
        db.table(table_name).insert(batch).execute()
        print(f"✅ Migration successful. (Skipped {skipped} broken records)")
    else:
        print(f"⚠️ No valid records found to migrate in {node_name}.")

# Mappings with safety checks
def obs_map(v):
    t_val = v.get('t')
    iso_time = convert_time(t_val)
    if not iso_time: return None
    
    return {
        "captured_at": iso_time,
        "speed_mph": v.get('s', 0),
        "lane_direction": v.get('lane', 'near'),
        "pixel_width": v.get('w', 0),
        "aspect_ratio": v.get('r', 0)
    }

def env_map(v):
    t_val = v.get('t')
    iso_time = convert_time(t_val)
    if not iso_time: return None
    
    return {
        "captured_at": iso_time,
        "brightness_lux": v.get('lux', 0),
        "precipitation_mm": v.get('rain', 0),
        "temperature_c": v.get('temp', 0),
        "cloud_cover_pct": v.get('cloud', 0),
        "weather_condition": v.get('cond', 'unknown')
    }

if __name__ == "__main__":
    migrate_data("observations", "observations", obs_map)
    migrate_data("weather_research", "weather_research", env_map)