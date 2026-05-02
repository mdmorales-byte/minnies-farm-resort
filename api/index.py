import os
import sys
import json
import urllib.request
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token
from passlib.hash import pbkdf2_sha256

# --- CONFIG ---
app = Flask(__name__)
CORS(app)
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "dev-secret")
jwt = JWTManager(app)

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# --- HELPERS ---
def supabase_req(endpoint, method='GET', data=None):
    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/{endpoint}"
    headers = {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'Content-Type': 'application/json',
        'Prefer': 'return=representation'
    }
    req_data = json.dumps(data).encode('utf-8') if data else None
    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    with urllib.request.urlopen(req) as res:
        res_body = res.read().decode('utf-8')
        return json.loads(res_body) if res_body else None

# --- ROUTES ---
@app.route('/api/health')
def health():
    return jsonify({"status": "online", "supabase": bool(SUPABASE_URL)})

@app.route('/api/auth/login', methods=['POST'])
def login():
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

@app.route('/api/rooms', methods=['GET'])
def get_rooms():
    rooms = supabase_req('rooms?select=*')
    return jsonify({"rooms": rooms or []}), 200

@app.route('/api/services', methods=['GET'])
def get_services():
    services = supabase_req('services?select=*&is_active=eq.true')
    return jsonify({"services": services or []}), 200

# Vercel entry point
handler = app

if __name__ == "__main__":
    app.run(debug=True)