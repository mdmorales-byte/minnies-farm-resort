from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from extensions import db, bcrypt, mail
from dotenv import load_dotenv
from flask_mail import Message
from extensions import mail
import secrets, time
import os

load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
        f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT', 3306)}/{os.getenv('DB_NAME')}"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "dev-secret")
    
    # Mail configuration
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = 'moralesmickdaniel7@gmail.com'
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = ("Minnie's Farm Resort", 'moralesmickdaniel7@gmail.com')

    db.init_app(app)
    bcrypt.init_app(app)
    mail.init_app(app)
    JWTManager(app)
    CORS(app, origins=["http://127.0.0.1:5500", "http://localhost:5500", "https://mdmorales-byte.github.io"])

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

    @app.route("/api/health")
    def health():
        return {"status": "ok", "resort": "Minnies Farm Resort"}, 200

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
            role="staff"
        )
        db.session.add(new_staff)
        db.session.commit()
        return {"status": "Staff created!"}, 200

    @app.route("/api/seed-all")
    def seed_all():
        from models import User, Room, Service
        db.drop_all()
        db.create_all()
        users = [
            User(name="Mick Daniel Morales", email="staff@resort.com", password=bcrypt.generate_password_hash("staff123").decode(), role="staff"),
            User(name="Althea Louise Camano", email="guest@resort.com", password=bcrypt.generate_password_hash("guest123").decode(), role="guest"),
        ]
        db.session.add_all(users)
        db.session.commit()
        return {"status": "Database seeded!"}, 200

    with app.app_context():
        db.create_all()

    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)