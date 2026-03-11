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
    # Database connection pooling
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_size": 2,
        "max_overflow": 1,
        "pool_timeout": 30,
        "pool_recycle": 1800,
    }
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
            User(name="Mick Daniel Morales", email="staff@resort.com", password=bcrypt.generate_password_hash("staff123").decode(), role="staff", is_verified=True),
            User(name="Althea Louise Camano", email="guest@resort.com", password=bcrypt.generate_password_hash("guest123").decode(), role="guest", is_verified=True),
        ]
        db.session.add_all(users)
        rooms = [
            Room(room_number="R01", name="Single Room", type="Standard", capacity=1, price_per_night=1000, sqm=28, is_available=True, description="Our Single Room is a refined haven for the independent traveler. Designed to offer a peaceful escape, this room features a plush bed and large windows that invite the morning sun. It is the perfect spot to unplug, enjoy a quiet morning coffee, and recharge in a space that feels entirely your own.", amenities="Free Wi-Fi, Air Conditioning, Flat-screen TV", room_status="available"),
            Room(room_number="R02", name="Kids Room", type="Themed", capacity=5, price_per_night=1500, sqm=38, is_available=True, description="The Kids Room is a vibrant, imaginative space designed specifically for our youngest guests. With playful decor and comfortable twin or bunk beds, it’s a room that turns bedtime into part of the vacation fun. It provides a safe, energetic environment where children can relax after a day of outdoor play and discovery.", amenities="Free Wi-Fi, Pool View, Bathtub", room_status="available"),
            Room(room_number="R03", name="Double Room", type="Deluxe", capacity=2, price_per_night=2500, sqm=60, is_available=True, description="Perfect for friends or couples, the Double Room offers a spacious layout with flexible bedding options. Thoughtfully appointed with warm textures and modern comforts, this room serves as a relaxing home base. Whether you’re resting between activities or winding down for the night, the cozy ambiance ensures a refreshing stay for two.", amenities="Butler Service, Free Wi-Fi", room_status="available"),
            Room(room_number="R04", name="Family Room", type="Suite", capacity=10, price_per_night=4500, sqm=120, is_available=True, description="Our Family Room is designed for connection and ease, offering ample space for the whole group to gather comfortably. Featuring multiple sleeping areas and a cozy lounge corner, it allows families to stay close while still having room to breathe. It’s a generous, welcoming suite built for making memories and sharing stories after a full day of resort fun.", amenities="BBQ Area, Butler Service, Free Wi-Fi", room_status="available"),
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

    with app.app_context():
        db.create_all()

    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)