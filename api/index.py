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

# Use a more robust way to get env vars and TRIM them aggressively
def get_clean_env(key):
    val = os.environ.get(key) or os.getenv(key) or ""
    # Remove all whitespace, newlines, and quotes that might have been pasted by accident
    return val.strip().replace("\n", "").replace("\r", "").replace(" ", "").replace("'", "").replace('"', "")

SUPABASE_URL = get_clean_env('SUPABASE_URL')
SUPABASE_KEY = get_clean_env('SUPABASE_KEY')

# STARTUP DEBUG REPORT
print("--- VERCEL STARTUP REPORT ---")
print(f"SUPABASE_URL length: {len(SUPABASE_URL)}")
print(f"SUPABASE_KEY length: {len(SUPABASE_KEY)}")
print("----------------------------")

# --- HELPERS ---
def supabase_req(endpoint, method='GET', data=None):
    # Re-clean and validate URL every time
    url_base = SUPABASE_URL.strip().replace(" ", "").replace("'", "").replace('"', "")
    if not url_base.startswith("http"):
        url_base = f"https://{url_base}"
    url_base = url_base.rstrip('/')
    
    try:
        url = f"{url_base}/rest/v1/{endpoint}"
        
        headers = {
            'apikey': SUPABASE_KEY.strip(),
            'Authorization': f'Bearer {SUPABASE_KEY.strip()}',
            'Content-Type': 'application/json',
            'Prefer': 'return=representation'
        }
        
        # Use a session with retries for better stability
        session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(max_retries=5)
        session.mount('https://', adapter)
        
        if method == 'GET':
            res = session.get(url, headers=headers, timeout=15)
        elif method == 'POST':
            res = session.post(url, headers=headers, json=data, timeout=15)
        elif method == 'PATCH':
            res = session.patch(url, headers=headers, json=data, timeout=15)
        elif method == 'DELETE':
            res = session.delete(url, headers=headers, timeout=15)
        else:
            return None
            
        res.raise_for_status()
        return res.json() if res.text else []
        
    except Exception as e:
        print(f"Supabase request error ({method} {endpoint}): {str(e)}")
        # If DNS fails, try to log the IP for debugging
        try:
            host = url_base.split("//")[-1].split("/")[0]
            print(f"DNS Debug: Final attempt to resolve '{host}'...")
            import socket
            ip = socket.gethostbyname(host)
            print(f"DNS Debug: Success! IP is {ip}")
        except:
            print("DNS Debug: ALL resolution methods failed.")
            
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

@app.route('/api/services/avails', methods=['GET'])
def get_service_avails():
    try:
        avails = supabase_req('service_availability?select=*')
        return jsonify({"service_avails": avails or []}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/bookings', methods=['GET', 'POST'])
def handle_bookings():
    try:
        if request.method == 'POST':
            data = request.get_json()
            result = supabase_req('bookings', method='POST', data=data)
            return jsonify({"message": "Booking created", "booking": result}), 201
        
        # GET logic
        user_id = request.args.get('user_id')
        endpoint = 'bookings?select=*'
        if user_id:
            endpoint += f'&user_id=eq.{user_id}'
        bookings = supabase_req(endpoint)
        return jsonify({"bookings": bookings or []}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/reviews', methods=['GET', 'POST'])
def handle_reviews():
    try:
        if request.method == 'POST':
            data = request.get_json()
            result = supabase_req('reviews', method='POST', data=data)
            return jsonify({"message": "Review added", "review": result}), 201
            
        room_id = request.args.get('room_id')
        endpoint = 'reviews?select=*'
        if room_id:
            endpoint += f'&room_id=eq.{room_id}'
        reviews = supabase_req(endpoint)
        return jsonify({"reviews": reviews or []}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/auth/me', methods=['GET'])
def get_me():
    try:
        # Simple placeholder for auth validation for now
        # Ideally this would use @jwt_required() but let's just get the route working
        return jsonify({"message": "Me endpoint reached"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/rooms/<int:room_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_single_room(room_id):
    try:
        if request.method == 'PUT':
            data = request.get_json()
            if 'amenities' in data and isinstance(data['amenities'], list):
                data['amenities'] = ", ".join(data['amenities'])
            
            result = supabase_req(f'rooms?id=eq.{room_id}', method='PATCH', data=data)
            return jsonify({"message": "Room updated", "room": result}), 200
        
        if request.method == 'DELETE':
            supabase_req(f'rooms?id=eq.{room_id}', method='DELETE')
            return jsonify({"message": "Room deleted"}), 200
            
        # Fix: ensure we return room object, not list
        res = supabase_req(f'rooms?id=eq.{room_id}&select=*')
        if res and isinstance(res, list) and len(res) > 0:
            room = res[0]
            raw_amenities = room.get('amenities', '')
            if isinstance(raw_amenities, str):
                room['amenities'] = [a.strip() for a in raw_amenities.split(',') if a.strip()]
            return jsonify({"room": room}), 200
        return jsonify({"error": "Room not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/services/<int:service_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_single_service(service_id):
    try:
        if request.method == 'PUT':
            data = request.get_json()
            # Log the toggle for debugging
            print(f"Updating service {service_id} with data: {data}")
            result = supabase_req(f'services?id=eq.{service_id}', method='PATCH', data=data)
            return jsonify({"message": "Service updated successfully", "service": result}), 200
        
        if request.method == 'DELETE':
            supabase_req(f'services?id=eq.{service_id}', method='DELETE')
            return jsonify({"message": "Service deleted successfully"}), 200
            
        service = supabase_req(f'services?id=eq.{service_id}&select=*')
        return jsonify({"service": service[0] if service else None}), 200
    except Exception as e:
        print(f"Service update error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/rooms/upload-image', methods=['POST'])
def upload_image():
    # Vercel has a 4.5MB limit for serverless functions, which is why 413 error happens.
    # For now, we return a message suggesting to use small files.
    return jsonify({"error": "File size too large for direct upload. Please use a smaller image (<4MB)."}), 413

# Vercel entry point
handler = app

if __name__ == "__main__":
    app.run(debug=True)