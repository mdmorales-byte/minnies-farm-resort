import os
import sys
from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager

# 1. Create the app instance
app = Flask(__name__)
CORS(app)

# 2. Add health check at the very top (no dependencies)
@app.route('/api/health')
def health_check():
    return jsonify({
        "status": "online",
        "python_version": sys.version,
        "env": "production" if os.getenv('VERCEL') else "development"
    })

    # 3. Setup core extensions
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "dev-secret")
    app.config["UPLOAD_FOLDER"] = "/tmp/uploads" # Vercel only allows writing to /tmp
    
    if not os.path.exists(app.config["UPLOAD_FOLDER"]):
        os.makedirs(app.config["UPLOAD_FOLDER"])

    # Import extensions from the current package
    try:
        from .extensions import bcrypt
        bcrypt.init_app(app)
    except Exception as e:
        print(f"Extension load error: {e}")

    JWTManager(app)
    CORS(app, supports_credentials=True)

    # 4. Lazy load routes to prevent startup crash
    def init_routes():
        try:
            # Absolute imports within the package
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
            print("Routes registered successfully")
        except Exception as e:
            print(f"Failed to load routes: {e}")

    init_routes()

# Vercel entry point
handler = app

if __name__ == "__main__":
    app.run(debug=True, port=5000)