import sys
import os
import argparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to path
sys.path.append(os.getcwd())

try:
    from app.services.supabase_client import get_supabase_client
    from app.services.auth_service import hash_password
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)

def create_admin_user(username, password):
    client = get_supabase_client()
    
    # Check if user exists
    try:
        existing = client.table("users").select("id").eq("username", username).execute()
        if existing.data and len(existing.data) > 0:
            print(f"User '{username}' already exists.")
            return
    except Exception as e:
        print(f"Error checking existing user: {e}")
        return

    password_hash = hash_password(password)
    
    data = {
        "username": username,
        "password_hash": password_hash,
        "role": "admin",
        "is_active": True
    }
    
    try:
        response = client.table("users").insert(data).execute()
        # In newer supabase clients, response.data handles the result
        if response.data:
            print(f"Successfully created admin user: {username}")
        else:
             # Fallback if data is empty but no exception raised
             print(f"User creation executed. Please verify in database.")
             
    except Exception as e:
        print(f"Error creating user: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a new admin user.")
    parser.add_argument("username", help="Username for the new admin")
    parser.add_argument("password", help="Password for the new admin")
    
    args = parser.parse_args()
    
    create_admin_user(args.username, args.password)
