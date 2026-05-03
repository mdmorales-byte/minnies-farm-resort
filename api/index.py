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

# Use a more robust way to get env vars and TRIM them
SUPABASE_URL = (os.environ.get('SUPABASE_URL') or os.getenv('SUPABASE_URL') or "").strip()
SUPABASE_KEY = (os.environ.get('SUPABASE_KEY') or os.getenv('SUPABASE_KEY') or "").strip()

# STARTUP DEBUG REPORT
print("--- VERCEL STARTUP REPORT ---")
print(f"SUPABASE_URL present: {bool(SUPABASE_URL)}")
print(f"SUPABASE_KEY present: {bool(SUPABASE_KEY)}")
if SUPABASE_URL: 
    print(f"URL: '{SUPABASE_URL}'") # Added quotes to see hidden spaces
print("----------------------------")

# --- HELPERS ---
def supabase_req(endpoint, method='GET', data=None):
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("Error: Supabase credentials missing during request")
        return None
        
    try:
        base_url = SUPABASE_URL.strip().rstrip('/')
        url = f"{base_url}/rest/v1/{endpoint}"
        
        headers = {
            'apikey': SUPABASE_KEY.strip(),
            'Authorization': f'Bearer {SUPABASE_KEY.strip()}',
            'Content-Type': 'application/json',
            'Prefer': 'return=representation'
        }
        
        if method == 'GET':
            res = requests.get(url, headers=headers)
        elif method == 'POST':
            res = requests.post(url, headers=headers, json=data)
        elif method == 'PATCH':
            res = requests.patch(url, headers=headers, json=data)
        elif method == 'DELETE':
            res = requests.delete(url, headers=headers)
        else:
            return None
            
        res.raise_for_status()
        return res.json() if res.text else []
        
    except Exception as e:
        print(f"Supabase request error ({method} {endpoint}): {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")
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