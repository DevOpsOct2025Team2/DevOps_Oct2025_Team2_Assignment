import sys
import os
import time
from datetime import datetime, timedelta, timezone
import jwt
from dotenv import load_dotenv
from flask import Flask

# Load environment variables
load_dotenv()

# Mock app config
config = {
    "JWT_SECRET_KEY": os.getenv("JWT_SECRET_KEY", "test-secret"),
    "JWT_ACCESS_TOKEN_EXPIRES": int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", 3600))
}

print(f"Config: JWT_ACCESS_TOKEN_EXPIRES = {config['JWT_ACCESS_TOKEN_EXPIRES']}")
print(f"Current System Time (time.time()): {time.time()}")
print(f"Current UTC Time (datetime.now(timezone.utc)): {datetime.now(timezone.utc)}")

def create_token():
    expires_in = config["JWT_ACCESS_TOKEN_EXPIRES"]
    now = datetime.now(timezone.utc)
    payload = {
        "sub": "123",
        "username": "test",
        "role": "admin",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=expires_in)).timestamp()),
    }
    print(f"Token Payload: {payload}")
    token = jwt.encode(payload, config["JWT_SECRET_KEY"], algorithm="HS256")
    return token

def verify_token(token):
    try:
        decoded = jwt.decode(token, config["JWT_SECRET_KEY"], algorithms=["HS256"])
        print("Verification SUCCESS")
        print(f"Decoded: {decoded}")
    except jwt.ExpiredSignatureError:
        print("Verification FAILED: Token expired")
        # Check why
        claims = jwt.decode(token, options={"verify_signature": False})
        exp = claims.get("exp")
        now_ts = time.time()
        print(f"Exp: {exp}, Now: {now_ts}, Diff: {exp - now_ts}")
    except Exception as e:
        print(f"Verification FAILED: {e}")

print("-" * 20)
print("Creating and Verifying Token...")
token = create_token()
verify_token(token)
