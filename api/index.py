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
jwt = JWTManager(app)

# 4. Lazy load routes to prevent startup crash
def init_routes():
    try:
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
    except Exception as e:
        app.logger.error(f"Failed to load routes: {e}")

init_routes()

# Vercel entry point
handler = app

if __name__ == "__main__":
    app.run(debug=True, port=5000)