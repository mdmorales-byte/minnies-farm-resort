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
    ]
    db.session.add_all(users)
    db.session.commit()
    print(f"✅  {len(users)} users seeded.")

    # ── Rooms ──────────────────────────────────────────────────────────────────
    rooms = [
        Room(
            room_number="R01", name="Single Room", type="Standard",
            capacity=2, price_per_night=3500, sqm=28, is_available=True,
            description="Our Single Room is a refined haven for the independent traveler. Designed to offer a peaceful escape, this room features a plush bed and large windows that invite the morning sun. It is the perfect spot to unplug, enjoy a quiet morning coffee, and recharge in a space that feels entirely your own.",
            amenities="Free Wi-Fi, Air Conditioning, Flat-screen TV",
        ),
        Room(
            room_number="R02", name="Kids Room", type="Themed",
            capacity=3, price_per_night=5800, sqm=38, is_available=True,
            description="The Kids Room is a vibrant, imaginative space designed specifically for our youngest guests. With playful decor and comfortable twin or bunk beds, it’s a room that turns bedtime into part of the vacation fun. It provides a safe, energetic environment where children can relax after a day of outdoor play and discovery.",
            amenities="Free Wi-Fi, Pool View, Bathtub, Minibar, Air Conditioning",
        ),
        Room(
            room_number="R03", name="Double Room", type="Deluxe",
            capacity=4, price_per_night=9500, sqm=60, is_available=True,
            description="Perfect for friends or couples, the Double Room offers a spacious layout with flexible bedding options. Thoughtfully appointed with warm textures and modern comforts, this room serves as a relaxing home base. Whether you’re resting between activities or winding down for the night, the cozy ambiance ensures a refreshing stay for two.",
            amenities="Butler Service, Free Wi-Fi",
        ),
        Room(
            room_number="R04", name="Family Room", type="Suite",
            capacity=4, price_per_night=1200, sqm=60, is_available=True,
            description="Our Family Room is designed for connection and ease, offering ample space for the whole group to gather comfortably. Featuring multiple sleeping areas and a cozy lounge corner, it allows families to stay close while still having room to breathe. It’s a generous, welcoming suite built for making memories and sharing stories after a full day of resort fun.",
            amenities="Free Wi-Fi",
        )
    ]
    db.session.add_all(rooms)
    db.session.commit()
    print(f"✅  {len(rooms)} rooms seeded.")

    # ── Services ───────────────────────────────────────────────────────────────
    services = [
        Service(
            name="Day Entrance",
            description="Access to resort grounds, gardens, nature walk, picnic areas, and kids play area. Children 3 and below are FREE.",
            price=100.00,
            category="day_service",
            is_active=True,
        ),
        Service(
            name="Karaoke Room",
            description="Private karaoke room for up to 10 people. Includes 2 microphones, full song library (OPM, Pop, K-pop), and large screen TV. Good for 2 hours. Extension: ₱200/hour.",
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
