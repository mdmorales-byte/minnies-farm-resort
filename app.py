import os
import sys
from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv

# Ensure the api folder is in the path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'api'))

# Only load .env locally (not on Vercel)
if not os.getenv('VERCEL'):
    load_dotenv()

def create_app():
    app = Flask(__name__)

    # Health check route
    @app.route('/api/health')
    def health():
        return jsonify({
            "status": "ok",
            "message": "Backend is running from root",
            "python_version": sys.version
        })

    # Config
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "dev-secret")
    app.config["UPLOAD_FOLDER"] = os.path.join(os.getcwd(), "uploads")
    
    if not os.path.exists(app.config["UPLOAD_FOLDER"]):
        os.makedirs(app.config["UPLOAD_FOLDER"])

    # Initialize extensions from the api folder
    from api.extensions import bcrypt
    bcrypt.init_app(app)

    JWTManager(app)
    CORS(app, supports_credentials=True)

    # Import and register blueprints from the api folder
    from api.routes.auth import auth_bp
    from api.routes.rooms import rooms_bp
    from api.routes.bookings import bookings_bp
    from api.routes.services import services_bp
    from api.routes.reviews import reviews_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(rooms_bp, url_prefix="/api/rooms")
    app.register_blueprint(bookings_bp, url_prefix="/api/bookings")
    app.register_blueprint(services_bp, url_prefix="/api/services")
    app.register_blueprint(reviews_bp, url_prefix="/api/reviews")

    return app

app = create_app()
# Vercel needs 'app' to be exposed
handler = app

if __name__ == "__main__":
    app.run(debug=True, port=5000)