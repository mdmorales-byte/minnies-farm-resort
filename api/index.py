import os
import sys
import json
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token
from passlib.hash import pbkdf2_sha256

# --- CONFIG ---
app = Flask(__name__)
CORS(app)
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "dev-secret")
jwt = JWTManager(app)

# HARDCODED FOR DEBUGGING - BYPASSING VERCEL VARS
SUPABASE_URL = "https://yrmmuaomglqoevooyxu.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlybW11dWFvbWdscW9ldm9veXh1Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NzY5MzQzMSwiZXhwIjoyMDkzMjY5NDMxfQ.PS3W0IHsEpCfSw7o4tuXMhRrjTGH9EIFYhKWPMfN0y4"

# STARTUP DEBUG REPORT
print("--- VERCEL STARTUP REPORT (HARDCODED) ---")
print(f"URL: '{SUPABASE_URL}'")
print("----------------------------")

# --- HELPERS ---
def supabase_req(endpoint, method='GET', data=None):
    # Re-clean and validate URL every time
    url_base = SUPABASE_URL.strip().replace(" ", "").replace("'", "").replace('"', "")
    if not url_base.startswith("http"):
        url_base = f"https://{url_base}"
    url_base = url_base.rstrip('/')
    
    if "supabase.co" not in url_base:
        print(f"CRITICAL: Invalid Supabase URL detected: '{url_base}'")
        return None
        
    if not SUPABASE_KEY:
        print("Error: SUPABASE_KEY is missing")
        return None
        
    try:
        url = f"{url_base}/rest/v1/{endpoint}"
        
        headers = {
            'apikey': SUPABASE_KEY.strip(),
            'Authorization': f'Bearer {SUPABASE_KEY.strip()}',
            'Content-Type': 'application/json',
            'Prefer': 'return=representation'
        }
        
        if method == 'GET':
            res = requests.get(url, headers=headers, timeout=10)
        elif method == 'POST':
            res = requests.post(url, headers=headers, json=data, timeout=10)
        elif method == 'PATCH':
            res = requests.patch(url, headers=headers, json=data, timeout=10)
        elif method == 'DELETE':
            res = requests.delete(url, headers=headers, timeout=10)
        else:
            return None
            
        res.raise_for_status()
        return res.json() if res.text else []
        
    except Exception as e:
        print(f"Supabase request error ({method} {endpoint}): {str(e)}")
        # If it's a connection error, let's see the hostname it tried to use
        if "Failed to resolve" in str(e):
             import socket
             try:
                 host = url_base.split("//")[-1].split("/")[0]
                 print(f"DNS Debug: Attempting to resolve host '{host}'")
                 socket.gethostbyname(host)
             except Exception as dns_e:
                 print(f"DNS Debug: Manual resolution failed for '{host}': {dns_e}")
        
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response Body: {e.response.text}")
        return None

# --- ROUTES ---
@app.route('/api/health')
def health():
    return jsonify({"status": "online", "supabase": bool(SUPABASE_URL)})

@app.route('/api/auth/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        password = data.get('password')
        
        users = supabase_req(f'users?email=eq.{email}&select=*')
        if not users:
            return jsonify({"error": "Invalid email or password."}), 401
        
        user = users[0]
        stored_pw = user.get('password')
        
        # Check password (handles both hashed and plain)
        is_valid = False
        try:
            is_valid = pbkdf2_sha256.verify(password, stored_pw)
        except:
            is_valid = (password == stored_pw)
            
        if not is_valid:
            return jsonify({"error": "Invalid email or password."}), 401

        token = create_access_token(identity=str(user.get('id')))
        return jsonify({"token": token, "user": user}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/auth/google', methods=['POST'])
def google_login():
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        name = data.get('name')
        google_id = data.get('google_id')

        if not email or not google_id:
            return jsonify({'error': 'Invalid Google credentials'}), 400

        users = supabase_req(f'users?email=eq.{email}&select=*')
        user = users[0] if users else None

        if not user:
            user_data = {
                'name': name,
                'email': email,
                'password': pbkdf2_sha256.hash(google_id),
                'role': 'guest',
                'is_verified': True
            }
            user = supabase_req('users', method='POST', data=user_data)
            if isinstance(user, list): user = user[0]

        token = create_access_token(identity=str(user.get('id')))
        return jsonify({'token': token, 'user': user}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/rooms', methods=['GET'])
def get_rooms():
    try:
        rooms = supabase_req('rooms?select=*')
        if rooms is None:
            return jsonify({"error": "Failed to fetch rooms from database"}), 500
        return jsonify({"rooms": rooms}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/services', methods=['GET'])
def get_services():
    try:
        services = supabase_req('services?select=*&is_active=eq.true')
        if services is None:
            return jsonify({"error": "Failed to fetch services from database"}), 500
        return jsonify({"services": services}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Vercel entry point
handler = app

if __name__ == "__main__":
    app.run(debug=True)