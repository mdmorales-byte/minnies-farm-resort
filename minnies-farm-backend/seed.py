"""
seed.py  –  Populate the database with starter data
Run once:  python seed.py
"""

from app import create_app, db, bcrypt
from models import User, Room, Service

app = create_app()

with app.app_context():
    # ── Wipe existing data ─────────────────────────────────────────────────────
    db.drop_all()
    db.create_all()
    print("✅  Tables created.")

    # ── Users ──────────────────────────────────────────────────────────────────
    users = [
        User(name="Mick Daniel Morales",       email="staff@resort.com",  password=bcrypt.generate_password_hash("staff123").decode(),  role="staff"),
        User(name="Althea Louise Camano",      email="guest@resort.com",  password=bcrypt.generate_password_hash("guest123").decode(),  role="guest"),
        User(name="Carlos Dela Cruz",  email="carlos@email.com",  password=bcrypt.generate_password_hash("pass1234").decode(),  role="guest"),
    ]
    db.session.add_all(users)
    db.session.commit()
    print(f"✅  {len(users)} users seeded.")

    # ── Rooms ──────────────────────────────────────────────────────────────────
    rooms = [
        Room(
            room_number="R01", name="Coral Standard Room", type="Standard",
            capacity=2, price_per_night=3500, sqm=28, is_available=True,
            description="A cozy standard room with modern amenities, perfect for couples or solo travelers seeking comfort and value.",
            amenities="Free Wi-Fi, Air Conditioning, Flat-screen TV, Mini Fridge",
        ),
        Room(
            room_number="R02", name="Palm Deluxe Room", type="Deluxe",
            capacity=3, price_per_night=5800, sqm=38, is_available=True,
            description="Spacious deluxe room with garden views, premium bedding, and upgraded toiletries.",
            amenities="Free Wi-Fi, Pool View, Bathtub, Minibar, Air Conditioning",
        ),
        Room(
            room_number="R03", name="Azure Ocean Suite", type="Suite",
            capacity=4, price_per_night=9500, sqm=60, is_available=True,
            description="Stunning ocean-facing suite with a private balcony, living area, and premium amenities.",
            amenities="Ocean View, Private Balcony, Jacuzzi, Butler Service, Free Wi-Fi, Minibar",
        ),
        Room(
            room_number="R04", name="Sunset Villa", type="Villa",
            capacity=6, price_per_night=18000, sqm=120, is_available=True,
            description="Exclusive private villa with its own pool, kitchen, and outdoor lounging area.",
            amenities="Private Pool, Full Kitchen, BBQ Area, Butler Service, Free Wi-Fi, Golf Cart",
        ),
        Room(
            room_number="R05", name="Garden Deluxe", type="Deluxe",
            capacity=2, price_per_night=4800, sqm=35, is_available=True,
            description="Tranquil deluxe room surrounded by lush tropical gardens.",
            amenities="Garden View, Free Wi-Fi, Rain Shower, Air Conditioning, Room Service",
        ),
        Room(
            room_number="R06", name="Family Suite", type="Suite",
            capacity=6, price_per_night=12000, sqm=85, is_available=True,
            description="Designed for families with two bedrooms, a living room, and kid-friendly amenities.",
            amenities="2 Bedrooms, Living Area, Kids Club Access, Free Wi-Fi, Pool Access",
        ),
    ]
    db.session.add_all(rooms)
    db.session.commit()
    print(f"✅  {len(rooms)} rooms seeded.")

    # ── Services ───────────────────────────────────────────────────────────────
    services = [
        Service(
            name="Day Entrance",
            description="Access to resort grounds, gardens, farm animal viewing, nature walk, picnic areas, and kids play area. Children 3 and below are FREE.",
            price=100.00,
            category="day_service",
            is_active=True,
        ),
        Service(
            name="Karaoke Room",
            description="Private karaoke room for up to 10 people. Includes 2 wireless microphones, full song library (OPM, Pop, K-pop), and large screen TV. Good for 2 hours. Extension: ₱200/hour.",
            price=500.00,
            category="day_service",
            is_active=True,
        ),
        Service(
            name="Day Fun Bundle (Entrance + Karaoke)",
            description="Combo deal: Day entrance + Karaoke session. Best value for barkadas and family outings!",
            price=550.00,
            category="bundle",
            is_active=True,
        ),
    ]
    db.session.add_all(services)
    db.session.commit()
    print(f"✅  {len(services)} services seeded.")

    print("\n🌿  Minnie's Farm Resort database is ready!")
    print("   Staff login:  staff@resort.com  /  staff123")
    print("   Guest login:  guest@resort.com  /  guest123")
