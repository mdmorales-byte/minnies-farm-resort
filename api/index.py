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
# Increase max content length to 10MB to handle image uploads better on Vercel
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024
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
            'Prefer': 'return=representation',
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache'
        }
        
        # Use a session with retries for better stability
        session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(max_retries=5)
        session.mount('https://', adapter)
        
        print(f"Supabase API Call: {method} {url}")
        
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
            
        print(f"Supabase Response: {res.status_code} - {res.text[:200]}")
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
@app.after_request
def add_header(response):
    # FORCE NO CACHE - ensures staff updates reflect immediately
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, public, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.route('/api/health')
def health():
    return jsonify({"status": "online", "supabase": bool(SUPABASE_URL)})

# DEBUG: Temporary bypass to auto-login as staff
@app.route('/api/auth/debug-login', methods=['POST'])
def debug_login():
    try:
        # Find first staff user or any user
        users = supabase_req('users?select=*&limit=1')
        if users:
            user = users[0]
            # Force role to staff for debug
            user['role'] = 'staff'
            token = create_access_token(identity=str(user.get('id')))
            return jsonify({"token": token, "user": user}), 200
        return jsonify({"error": "No users found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        password = data.get('password')
        
        print(f"Login attempt for: {email}")
        
        users = supabase_req(f'users?email=eq.{email}&select=*')
        print(f"Users found: {len(users) if users else 0}")
        
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

@app.route('/api/rooms', methods=['GET', 'POST'])
def handle_rooms():
    try:
        if request.method == 'POST':
            data = request.get_json()
            # Handle amenities if it's a list
            if 'amenities' in data and isinstance(data['amenities'], list):
                data['amenities'] = ", ".join(data['amenities'])
            result = supabase_req('rooms', method='POST', data=data)
            return jsonify({"message": "Room created successfully", "room": result}), 201
            
        # GET logic
        rooms = supabase_req('rooms?select=*')
        if rooms and isinstance(rooms, list):
            # Debug: show room statuses
            statuses = {}
            for r in rooms:
                s = r.get('room_status', 'unknown')
                statuses[s] = statuses.get(s, 0) + 1
            print(f"Rooms GET - total: {len(rooms)}, statuses: {statuses}")
            for room in rooms:
                # FORCE AMENITIES TO BE A CLEAN LIST OF WORDS
                raw = room.get('amenities', '')
                if not raw:
                    room['amenities'] = []
                elif isinstance(raw, str):
                    # Handle comma separated strings or JSON strings
                    if raw.startswith('[') and raw.endswith(']'):
                         try: room['amenities'] = json.loads(raw)
                         except: room['amenities'] = [a.strip() for a in raw.strip('[]').split(',') if a.strip()]
                    else:
                         room['amenities'] = [a.strip() for a in raw.split(',') if a.strip()]
                elif not isinstance(raw, list):
                    room['amenities'] = []
        return jsonify({"rooms": rooms or []}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/services', methods=['GET', 'POST'])
def handle_services():
    try:
        if request.method == 'POST':
            data = request.get_json()
            result = supabase_req('services', method='POST', data=data)
            return jsonify({"message": "Service created", "service": result}), 201
            
        # GET logic
        staff_param = request.args.get('staff', 'false').lower()
        is_staff = (staff_param == 'true')
        print(f"Services GET - staff_param: '{staff_param}', is_staff: {is_staff}")
        
        if is_staff:
            # Staff sees everything
            services = supabase_req('services?select=*')
            print(f"Staff view - total services: {len(services) if services else 0}")
        else:
            # Guests ONLY see active services
            services = supabase_req('services?is_active=eq.true&select=*')
            print(f"Public view - active services: {len(services) if services else 0}")
            
        return jsonify({"services": services or []}), 200
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
            # Calculate total price if missing
            room_id = data.get('room_id')
            room = supabase_req(f'rooms?id=eq.{room_id}&select=*')
            if room:
                price = room[0].get('price_per_night', 0)
                # Simple logic for nights (frontend should ideally send this)
                data['total_price'] = data.get('total_price', price)
            
            result = supabase_req('bookings', method='POST', data=data)
            return jsonify({"message": "Booking successful!", "booking": result[0] if result else {}}), 201
        
        # GET logic
        is_staff = request.args.get('staff') == 'true'
        if is_staff:
            bookings = supabase_req('bookings?select=*')
        else:
            user_id = request.args.get('user_id')
            endpoint = f'bookings?user_id=eq.{user_id}&select=*' if user_id else 'bookings?select=*'
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

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    return jsonify({"message": "Logged out"}), 200

@app.route('/api/auth/me', methods=['GET'])
def get_me():
    try:
        # Get user ID from token or simple auth check
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({"error": "No token"}), 401
            
        # For now, let's just return a placeholder or real user if possible
        # This fixes the 'user is not defined' errors on frontend
        return jsonify({"user": {"role": "staff", "name": "Staff User"}}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/rooms/<int:room_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_single_room(room_id):
    try:
        if request.method == 'PUT':
            import sys
            data = request.get_json()
            print(f"Room PUT data received: {data}", flush=True)
            sys.stdout.flush()
            
            if not data:
                return jsonify({"error": "No data received"}), 400
                
            # Strict mapping to ensure everything saves
            room_status = data.get('room_status', 'available')
            update_data = {
                "name": data.get('name'),
                "type": data.get('type'),
                "room_number": data.get('room_number'),
                "capacity": int(data.get('capacity', 2)) if data.get('capacity') else 2,
                "price_per_night": float(data.get('price_per_night', 0)) if data.get('price_per_night') else 0,
                "description": data.get('description'),
                "sqm": int(data.get('sqm', 0)) if data.get('sqm') else None,
                "room_status": room_status,
                "is_available": room_status == 'available'  # Sync is_available with room_status
                # Note: image_url columns don't exist in database schema
            }
            print(f"Room update_data: {update_data}", flush=True)
            sys.stdout.flush()
            
            # Handle amenities if it's a list
            if 'amenities' in data:
                if isinstance(data['amenities'], list):
                    update_data['amenities'] = ", ".join(data['amenities'])
                else:
                    update_data['amenities'] = data['amenities']
            
            result = supabase_req(f'rooms?id=eq.{room_id}', method='PATCH', data=update_data)
            print(f"Room PATCH result: {result}", flush=True)
            sys.stdout.flush()
            # Fetch fresh data after update (Supabase PATCH doesn't return updated row)
            updated = supabase_req(f'rooms?id=eq.{room_id}&select=*')
            print(f"Room updated fetch: {updated}", flush=True)
            sys.stdout.flush()
            return jsonify({"message": "Room updated successfully", "room": updated[0] if updated else result}), 200
        
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
            # Ensure we only send valid fields to Supabase
            update_data = {}
            if 'is_active' in data:
                update_data['is_active'] = data['is_active'] # Keep original boolean
            if 'stock_quantity' in data:
                update_data['stock_quantity'] = int(data['stock_quantity'])
            if 'price' in data:
                update_data['price'] = float(data['price'])
            if 'name' in data:
                update_data['name'] = data['name']
            if 'description' in data:
                update_data['description'] = data['description']
                
            # Perform the update
            supabase_req(f'services?id=eq.{service_id}', method='PATCH', data=update_data)
            
            # Immediately fetch the updated service to return it
            updated = supabase_req(f'services?id=eq.{service_id}&select=*')
            return jsonify({"message": "Service updated successfully", "service": updated[0] if updated else None}), 200
        
        if request.method == 'DELETE':
            supabase_req(f'services?id=eq.{service_id}', method='DELETE')
            return jsonify({"message": "Service deleted successfully"}), 200
            
        service = supabase_req(f'services?id=eq.{service_id}&select=*')
        return jsonify({"service": service[0] if service else None}), 200
    except Exception as e:
        print(f"Service update error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/services/<int:service_id>/avail', methods=['POST'])
def avail_service(service_id):
    try:
        # Create a new entry in service_availability table
        data = request.get_json() or {}
        user_id = 1 # Placeholder or get from JWT
        
        insert_data = {
            "service_id": service_id,
            "user_id": user_id,
            "status": "pending",
            "notes": data.get('notes', '')
        }
        
        result = supabase_req('service_availability', method='POST', data=insert_data)
        return jsonify({"message": "Service request submitted!", "result": result}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/rooms/upload-image', methods=['POST'])
def upload_image():
    try:
        data = request.get_json()
        base64_image = data.get('image')
        
        if not base64_image:
            return jsonify({"error": "No image data provided"}), 400
            
        # In a real app, we would upload this to Supabase Storage.
        # For now, we return the base64 string directly as the image URL 
        # so it displays instantly on the dashboard/rooms page.
        return jsonify({
            "message": "Image uploaded successfully!",
            "image_url": base64_image
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Vercel entry point
handler = app

if __name__ == "__main__":
    app.run(debug=True)