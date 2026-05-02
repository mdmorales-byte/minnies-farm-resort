import os
from flask import Flask, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from .extensions import bcrypt
from .supabase_client import *
from dotenv import load_dotenv

# Only load .env locally (not on Vercel)
if not os.getenv('VERCEL'):
    load_dotenv()

# Deployed with Supabase integration - v2

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

    from .routes.auth import auth_bp
    from .routes.rooms import rooms_bp
    from .routes.bookings import bookings_bp
    from .routes.services import services_bp
    from .routes.reviews import reviews_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(rooms_bp, url_prefix="/api/rooms")
    app.register_blueprint(bookings_bp, url_prefix="/api/bookings")
    app.register_blueprint(services_bp, url_prefix="/api/services")
    app.register_blueprint(reviews_bp, url_prefix="/api/reviews")

    return app

# Create app and expose handler for Vercel
app = create_app()
handler = app

if __name__ == "__main__":
    app.run(debug=True, port=5000)