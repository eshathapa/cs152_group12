import os
from datetime import datetime, timezone
from dotenv import load_dotenv
import json
from math import exp

# Load environment variables from .env.local or .env
load_dotenv(dotenv_path='.env.local')
if not (os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_KEY")):
    load_dotenv()

# Define SUPABASE_URL and SUPABASE_KEY after loading .env files
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

try:
    from supabase import create_client, Client
except ImportError:
    print("ImportError")
    create_client = None
    Client = None

client = None
if create_client and SUPABASE_URL and SUPABASE_KEY:
    try:
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print("Could not create client")
        client = None
elif not (SUPABASE_URL and SUPABASE_KEY):
    print("Missing SUPABASE URL and/or key")

# Insert a victim log row
def insert_victim_log(victim_name: str, timestamp: datetime, perpetrator_id: str = None, perpetrator_name: str = None):
    if client is None:
        print("insert_victim_log error: no client")
        return
    try:
        data_to_insert = {
            "victim_name": victim_name,
            "reported_at": timestamp.isoformat(),
        }
        response = client.table("victims").insert(data_to_insert).execute()
    except Exception as e:
        print(f"insert_victim_log error: insert failed") 

# Insert a perpetrator log row (separate tracking for consequences)
def insert_perpetrator_log(perpetrator_id: str, perpetrator_name: str, timestamp: datetime, victim_name: str = None, severity: int = 1):
    if client is None:
        print("insert_perpetrator_log error: no client")
        return
    try:
        data_to_insert = {
            "perpetrator_id": perpetrator_id,
            "perpetrator_name": perpetrator_name,
            "reported_at": timestamp.isoformat(),
            "victim_name": victim_name,
            "severity": severity
        }
        response = client.table("perpetrators").insert(data_to_insert).execute()
    except Exception as e:
        print(f"insert_perpetrator_log error: insert failed")

# Get perpetrator harassment count from database (alternative to in-memory count.py)
def get_perpetrator_score(perpetrator_id: str):
    if client is None:
        print("get_perpetrator_score error: no client")
        return 0
    try:
        response = client.table("perpetrators").select("reported_at", "severity").eq("perpetrator_id", perpetrator_id).execute()
        score = 0
        now = datetime.now(timezone.utc)
        for entry in json.loads(response.json())["data"]:
            time = entry["reported_at"]
            severity = entry["severity"]
            try:
                difference = now - datetime.fromisoformat(time)
                score += severity * exp(-0.0990 * (difference.days * (24*60*60) + difference.seconds) / (24*60*60))
            except Exception as e:
                print(e)
        return score
    except Exception as e:
        print(f"get_perpetrator_score error: query failed")
        print(e)
        return 0

def victim_score(victim_name: str):
    if client is None:
        print("victim_score error: no client")
        return
    try:
        response = client.table("victims").select("reported_at").eq("victim_name", victim_name).execute() 
        score = 0
        now = datetime.now(timezone.utc)
        for entry in json.loads(response.json())["data"]:
            time = entry["reported_at"]
            difference = now - datetime.fromisoformat(time)
            score += exp(-0.0990 * (difference.days * (24*60*60) + difference.seconds) / (24*60*60))
        return score
    except Exception as e:
        print(f"victim_score error: query failed")
        return 0