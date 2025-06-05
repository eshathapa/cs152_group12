# This is to test if the supabase works 

from datetime import datetime
from supabase_helper import insert_victim_log, insert_perpetrator_log

def main():
    print("Testing Supabase connection and new functionality...")
    
    # Test original victim log with perpetrator info
    victim_name = "Test Victim"
    perpetrator_id = "123456789"
    perpetrator_name = "Test Perpetrator"
    timestamp = datetime.now()
    
    print(f"Inserting victim log: {victim_name} with perpetrator: {perpetrator_name}")
    insert_victim_log(victim_name, timestamp, perpetrator_id, perpetrator_name)
    
    # Test new perpetrator log
    print(f"Inserting perpetrator log: {perpetrator_name}")
    insert_perpetrator_log(perpetrator_id, perpetrator_name, timestamp, victim_name)
    
    print("Test completed!")

if __name__ == "__main__":
    main() 