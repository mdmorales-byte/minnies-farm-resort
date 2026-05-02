import os
import sys
from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager

# Add current directory to path for imports
sys.path.append(os.path.dirname(__file__))

try:
    from extensions import bcrypt
    from supabase_client import get_user_by_id
except ImportError:
    from .extensions import bcrypt
    from .supabase_client import get_user_by_id

from dotenv import load_dotenv

# Only load .env locally (not on Vercel)
if not os.getenv('VERCEL'):
    load_dotenv()

def create_app():
    app = Flask(__name__)

    # Health check route for Vercel debugging
    @app.route('/api/health')
    def health():
        return jsonify({
            "status": "ok",
            "supabase_url": bool(os.getenv('SUPABASE_URL')),
            "supabase_key": bool(os.getenv('SUPABASE_KEY'))
        })

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
    
    # CORS configuration
    CORS(app, supports_credentials=True)

    # Import routes
    try:
        from routes.auth import auth_bp
        from routes.rooms import rooms_bp
        from routes.bookings import bookings_bp
        from routes.services import services_bp
        from routes.reviews import reviews_bp
    except ImportError:
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

app = create_app()
handler = app

if __name__ == "__main__":
    app.run(debug=True, port=5000)