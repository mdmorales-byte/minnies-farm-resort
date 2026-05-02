import os
import threading
from flask import Flask, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from extensions import bcrypt
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# Force reload of .env file
load_dotenv(override=True)

def create_app():
    app = Flask(__name__)

    # Config
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "dev-secret")
    app.config["UPLOAD_FOLDER"] = os.path.join(os.getcwd(), "uploads")
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB limit
    
    # Ensure upload folder exists
    if not os.path.exists(app.config["UPLOAD_FOLDER"]):
        os.makedirs(app.config["UPLOAD_FOLDER"])

    @app.route('/uploads/<filename>')
    def uploaded_file(filename):
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

    bcrypt.init_app(app)
    JWTManager(app)
    
    # Load Supabase config
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')
    if supabase_url and supabase_key:
        print(f"[Supabase] Connected to: {supabase_url}")
    else:
        print("[Warning] SUPABASE_URL or SUPABASE_KEY not set!")
    
    # CORS configuration - allow frontend origins
    CORS(app, 
         origins=[
             "http://127.0.0.1:5500", 
             "http://localhost:5500",
             "https://mdmorales-byte.github.io",
             "https://mdmorales-byte.github.io/",
             "https://minnies-farm-resort.vercel.app",
             "https://minnies-farm-resort.vercel.app/"
         ],
         supports_credentials=True,
         allow_headers=['Content-Type', 'Authorization'])

    # Check if email is properly configured on startup
    if not os.getenv('SENDGRID_API_KEY'):
        print("⚠️  WARNING: SENDGRID_API_KEY environment variable is NOT SET! Email sending will not work.")

    from routes.auth import auth_bp
    from routes.rooms import rooms_bp
    from routes.bookings import bookings_bp
    from routes.services import services_bp
    from routes.reviews import reviews_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(rooms_bp, url_prefix="/api/rooms")
    app.register_blueprint(bookings_bp, url_prefix="/api/bookings")
    app.register_blueprint(services_bp, url_prefix="/api/services")
    app.register_blueprint(reviews_bp, url_prefix="/api/reviews")

    # ── SENDGRID TEST ─────────────────────────────────────────────────────────
    # For debugging/verification only
    @app.route('/api/test-email', methods=['GET'])
    def test_email():
        
        def _send_test():
            try:
                sg_key = os.getenv('SENDGRID_API_KEY')
                from_email = os.getenv('FROM_EMAIL')
                if not sg_key:
                    print("❌ SENDGRID_API_KEY not configured!")
                    return
                
                if not sg_key.startswith('SG.'):
                    print(f"❌ SENDGRID_API_KEY format invalid!")
                    return
                    
                print("📧 Attempting to send test email...")
                sg = SendGridAPIClient(sg_key)
                test_email_addr = os.getenv('TEST_EMAIL', 'staff@resort.com')
                msg = Mail(
                    from_email=from_email or 'staff@resort.com',
                    to_emails=test_email_addr,
                    subject='Test Email - Minnie\'s Farm Resort',
                    html_content='<strong>Email configuration is working!</strong>'
                )
                sg.send(msg)
                print(f"✅ Test email sent to {test_email_addr}")
            except Exception as e:
                print(f"❌ Test email failed: {str(e)}")
                print(f"   Error Type: {type(e).__name__}")
                print(f"   Error: {str(e)}")
                if hasattr(e, 'body'):
                    print(f"   Response Body: {e.body}")
                import traceback
                traceback.print_exc()
        
        # Send in background thread so it doesn't block
        thread = threading.Thread(target=_send_test, daemon=True)
        thread.start()
        
        return {"status": "✅ Test email queued! Check logs and email inbox shortly."}, 200

    @app.route("/api/seed-staff")
    def seed_staff():
        from models import User
        existing = User.query.filter_by(email="staff@resort.com").first()
        if existing:
            existing.password = bcrypt.generate_password_hash("staff123").decode()
            db.session.commit()
            return {"status": "Staff password reset!"}, 200
        new_staff = User(
            name="Mick Daniel Morales",
            email="staff@resort.com",
            password=bcrypt.generate_password_hash("staff123").decode(),
            role="staff",
            is_verified=True
        )
        db.session.add(new_staff)
        db.session.commit()
        return {"status": "Staff created!"}, 200

    @app.route("/api/test-db")
    def test_db():
        """Test database connection and show current config (without sensitive data)"""
        try:
            # Test basic connection
            from sqlalchemy import text
            result = db.session.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            
            # Get connection info
            db_info = {
                "status": "✅ Connected",
                "database_version": version,
                "db_host": db_host,
                "db_port": db_port,
                "db_name": db_name,
                "db_user": db_user,
                "uri_preview": f"postgresql://{db_user}:****@{db_host}:{db_port}/{db_name}" if 'supabase' in db_host.lower() or db_port == '5432' else f"mysql://{db_user}:****@{db_host}:{db_port}/{db_name}"
            }
            return db_info, 200
        except Exception as e:
            return {
                "status": "❌ Connection Failed",
                "error": str(e),
                "error_type": type(e).__name__,
                "db_host": db_host,
                "db_port": db_port,
                "db_name": db_name,
                "db_user": db_user,
                "suggestion": "Check DB_USER format. For Supabase pooler, use 'postgres.yrmmuuaomglqoevooyxu'"
            }, 500

    @app.route("/api/test-supabase")
    def test_supabase():
        """Test Supabase REST API connection using HTTP requests"""
        try:
            import urllib.request
            import json
            
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_KEY')
            
            if not supabase_url or not supabase_key:
                return {"error": "SUPABASE_URL or SUPABASE_KEY not set in .env"}, 500
            
            # Test Supabase REST API directly - try auth health first
            headers = {
                'apikey': supabase_key,
                'Authorization': f'Bearer {supabase_key}'
            }
            
            # Try the auth health endpoint first (usually accessible)
            req = urllib.request.Request(
                f'{supabase_url}/auth/v1/health',
                headers=headers,
                method='GET'
            )
            
            try:
                with urllib.request.urlopen(req, timeout=15) as response:
                    result = json.loads(response.read())
                    return {
                        "status": "✅ Supabase REST API Connected",
                        "url": supabase_url,
                        "auth_health": result,
                        "note": "API is accessible. You need 'service_role' key for full access."
                    }, 200
            except urllib.error.HTTPError as e:
                error_body = e.read().decode()
                if e.code == 401:
                    # API responds but needs service_role key
                    return {
                        "status": "✅ Supabase API Responding (needs service_role key)",
                        "url": supabase_url,
                        "http_code": e.code,
                        "error": json.loads(error_body) if error_body else "Auth required",
                        "solution": "Get the 'service_role' key from Supabase Dashboard > Project Settings > API"
                    }, 200
                else:
                    return {
                        "status": f"⚠️ Supabase API Error (HTTP {e.code})",
                        "url": supabase_url,
                        "error": error_body
                    }, 500
            
        except Exception as e:
            return {
                "status": "❌ Supabase Connection Failed",
                "error": str(e),
                "error_type": type(e).__name__
            }, 500

    @app.route("/api/seed-supabase")
    def seed_supabase():
        """Seed Supabase database using REST API"""
        try:
            import urllib.request
            import json
            import base64
            
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_KEY')
            
            if not supabase_url or not supabase_key:
                return {"error": "SUPABASE_URL or SUPABASE_KEY not set"}, 500
            
            # Debug: Check what key we're using
            key_preview = supabase_key[:30] + '...' if supabase_key else 'None'
            
            # Decode JWT to check role
            jwt_role = 'unknown'
            try:
                parts = supabase_key.split('.')
                if len(parts) == 3:
                    payload = parts[1]
                    payload += '=' * (4 - len(payload) % 4)
                    decoded = base64.b64decode(payload)
                    jwt_data = json.loads(decoded)
                    jwt_role = jwt_data.get('role', 'unknown')
            except Exception as e:
                jwt_role = f'error: {e}'
            
            headers = {
                'apikey': supabase_key,
                'Authorization': f'Bearer {supabase_key}',
                'Content-Type': 'application/json',
                'Prefer': 'return=minimal'
            }
            
            # Try to insert users directly via REST API
            users = [
                {"name": "Mick Daniel Morales", "email": "staff@resort.com", "password": "staff123", "role": "staff", "is_verified": True},
                {"name": "Althea Louise Camano", "email": "guest@resort.com", "password": "guest123", "role": "guest", "is_verified": True}
            ]
            
            results = []
            for user in users:
                try:
                    req = urllib.request.Request(
                        f'{supabase_url}/rest/v1/users',
                        data=json.dumps(user).encode('utf-8'),
                        headers=headers,
                        method='POST'
                    )
                    with urllib.request.urlopen(req, timeout=15) as response:
                        results.append(f"Created user: {user['email']}")
                except urllib.error.HTTPError as e:
                    if e.code == 409:
                        results.append(f"User exists: {user['email']}")
                    else:
                        results.append(f"Error creating {user['email']}: {e.read().decode()}")
            
            return {
                "status": "Seeding attempted via Supabase API",
                "results": results,
                "debug": {
                    "key_preview": key_preview,
                    "jwt_role": jwt_role
                }
            }, 200
            
        except Exception as e:
            return {"error": str(e), "type": type(e).__name__}, 500

    @app.route("/api/seed-all")
    def seed_all():
        from models import User, Room, Service, Booking, ServiceAvail, Review
        try:
            # Use a more robust reset for PostgreSQL/Supabase
            db.reflect()
            db.drop_all()
            db.create_all()
        except Exception as e:
            return {"error": f"Database reset failed: {str(e)}", "type": type(e).__name__}, 500
        users = [
            User(name="Mick Daniel Morales", email="staff@resort.com", password=bcrypt.generate_password_hash("staff123").decode(), role="staff", is_verified=True),
            User(name="Althea Louise Camano", email="guest@resort.com", password=bcrypt.generate_password_hash("guest123").decode(), role="guest", is_verified=True),
        ]
        db.session.add_all(users)
        rooms = [
            Room(room_number="R01", name="Single Room", type="Standard", capacity=1, price_per_night=1000, sqm=28, is_available=True, description="Our Single Room is a refined haven for the independent traveler. Designed to offer a peaceful escape, this room features a plush bed and large windows that invite the morning sun. It is the perfect spot to unplug, enjoy a quiet morning coffee, and recharge in a space that feels entirely your own.", amenities="Free Wi-Fi, Air Conditioning, Flat-screen TV", room_status="available"),
            Room(room_number="R02", name="Kids Room", type="Themed", capacity=5, price_per_night=1500, sqm=38, is_available=True, description="The Kids Room is a vibrant, imaginative space designed specifically for our youngest guests. With playful decor and comfortable twin or bunk beds, it's a room that turns bedtime into part of the vacation fun. It provides a safe, energetic environment where children can relax after a day of outdoor play and discovery.", amenities="Free Wi-Fi, Pool View, Bathtub", room_status="available"),
            Room(room_number="R03", name="Double Room", type="Deluxe", capacity=2, price_per_night=2500, sqm=60, is_available=True, description="Perfect for friends or couples, the Double Room offers a spacious layout with flexible bedding options. Thoughtfully appointed with warm textures and modern comforts, this room serves as a relaxing home base. Whether you're resting between activities or winding down for the night, the cozy ambiance ensures a refreshing stay for two.", amenities="Butler Service, Free Wi-Fi", room_status="available"),
            Room(room_number="R04", name="Family Room", type="Suite", capacity=10, price_per_night=4500, sqm=120, is_available=True, description="Our Family Room is designed for connection and ease, offering ample space for the whole group to gather comfortably. Featuring multiple sleeping areas and a cozy lounge corner, it allows families to stay close while still having room to breathe. It's a generous, welcoming suite built for making memories and sharing stories after a full day of resort fun.", amenities="BBQ Area, Butler Service, Free Wi-Fi", room_status="available"),
        ]
        db.session.add_all(rooms)
        services = [
            Service(name="Day Entrance", description="Access to resort grounds and gardens.", price=100.00, category="day_service", is_active=True),
            Service(name="Karaoke Room", description="Private karaoke room for up to 10 people.", price=500.00, category="day_service", is_active=True),
            Service(name="Day Fun Bundle (Entrance + Karaoke)", description="Combo deal: Day entrance + Karaoke session.", price=550.00, category="bundle", is_active=True),
        ]
        db.session.add_all(services)
        db.session.commit()
        return {"status": "Database seeded with users, rooms and services!"}, 200

    # ── Removed db.create_all() from here to avoid connection on startup ──

    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)