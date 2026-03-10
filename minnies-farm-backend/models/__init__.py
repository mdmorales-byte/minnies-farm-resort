"""
models/__init__.py
All SQLAlchemy models for Minnie's Farm Resort
"""

from extensions import db
from datetime import datetime


# ══════════════════════════════════════════════════════════════════════════════
#  USER
# ══════════════════════════════════════════════════════════════════════════════
class User(db.Model):
    __tablename__ = "users"

    id         = db.Column(db.Integer,      primary_key=True, autoincrement=True)
    name       = db.Column(db.String(100),  nullable=False)
    email      = db.Column(db.String(100),  nullable=False, unique=True)
    password   = db.Column(db.String(255),  nullable=False)
    role       = db.Column(db.Enum("guest", "staff"), nullable=False, default="guest")
    is_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime,     default=datetime.utcnow)

    # relationships
    bookings = db.relationship("Booking", backref="user", lazy=True)

    def to_dict(self):
        return {
            "id":         self.id,
            "name":       self.name,
            "email":      self.email,
            "role":       self.role,
            "is_verified": self.is_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ══════════════════════════════════════════════════════════════════════════════
#  ROOM
# ══════════════════════════════════════════════════════════════════════════════
class Room(db.Model):
    __tablename__ = "rooms"

    id               = db.Column(db.Integer,      primary_key=True, autoincrement=True)
    room_number      = db.Column(db.String(10),   nullable=False, unique=True)
    name             = db.Column(db.String(100),  nullable=False)
    type             = db.Column(db.String(50),   nullable=False)   # Standard/Deluxe/Suite/Villa
    capacity         = db.Column(db.Integer,      nullable=False)
    price_per_night  = db.Column(db.Numeric(10,2),nullable=False)
    description      = db.Column(db.Text)
    amenities        = db.Column(db.Text)          # comma-separated string
    image_url        = db.Column(db.String(1000))
    image_url_2      = db.Column(db.String(500))
    image_url_3      = db.Column(db.String(500))
    image_url_4      = db.Column(db.String(500))
    image_url_5      = db.Column(db.String(500))
    sqm              = db.Column(db.Integer)
    is_available     = db.Column(db.Boolean,      default=True)
    room_status      = db.Column(
        db.Enum("available", "fully_booked", "under_maintenance"),
        nullable=False, default="available"
    )

    # relationships
    bookings = db.relationship("Booking", backref="room", lazy=True)

    def amenities_list(self):
        if not self.amenities:
            return []
        return [a.strip() for a in self.amenities.split(",")]

    def to_dict(self):
        return {
            "id":              self.id,
            "room_number":     self.room_number,
            "name":            self.name,
            "type":            self.type,
            "capacity":        self.capacity,
            "price_per_night": float(self.price_per_night),
            "description":     self.description,
            "amenities":       self.amenities_list(),
            "image_url":       self.image_url,
            "image_url_2":     self.image_url_2,
            "image_url_3":     self.image_url_3,
            "image_url_4":     self.image_url_4,
            "image_url_5":     self.image_url_5,
            "sqm":             self.sqm,
            "is_available":    self.is_available,
            "room_status":     self.room_status,
        }


# ══════════════════════════════════════════════════════════════════════════════
#  BOOKING
# ══════════════════════════════════════════════════════════════════════════════
class Booking(db.Model):
    __tablename__ = "bookings"

    id             = db.Column(db.Integer,  primary_key=True, autoincrement=True)
    user_id        = db.Column(db.Integer,  db.ForeignKey("users.id"),  nullable=False)
    room_id        = db.Column(db.Integer,  db.ForeignKey("rooms.id"),  nullable=False)
    check_in_date  = db.Column(db.Date,     nullable=False)
    check_out_date = db.Column(db.Date,     nullable=False)
    num_guests     = db.Column(db.Integer,  nullable=False, default=1)
    total_price    = db.Column(db.Numeric(10,2), nullable=False)
    status         = db.Column(
        db.Enum("pending", "confirmed", "cancelled", "completed"),
        nullable=False, default="confirmed"
    )
    reference_code = db.Column(db.String(20), unique=True)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id":             self.id,
            "user_id":        self.user_id,
            "room_id":        self.room_id,
            "room_name":      self.room.name if self.room else None,
            "guest_name":     self.user.name if self.user else None,
            "check_in_date":  self.check_in_date.isoformat(),
            "check_out_date": self.check_out_date.isoformat(),
            "num_guests":     self.num_guests,
            "total_price":    float(self.total_price),
            "status":         self.status,
            "reference_code": self.reference_code,
            "created_at":     self.created_at.isoformat(),
        }


# ══════════════════════════════════════════════════════════════════════════════
#  SERVICE  (entrance fee, karaoke, etc.)
# ══════════════════════════════════════════════════════════════════════════════
class Service(db.Model):
    __tablename__ = "services"

    id          = db.Column(db.Integer,      primary_key=True, autoincrement=True)
    name        = db.Column(db.String(100),  nullable=False)
    description = db.Column(db.Text)
    price       = db.Column(db.Numeric(10,2),nullable=False)
    category    = db.Column(db.String(50))   # e.g. "day_service"
    is_active   = db.Column(db.Boolean,      default=True)

    def to_dict(self):
        return {
            "id":          self.id,
            "name":        self.name,
            "description": self.description,
            "price":       float(self.price),
            "category":    self.category,
            "is_active":   self.is_active,
        }


# ══════════════════════════════════════════════════════════════════════════════
#  SERVICE AVAIL  (when a guest avails a service)
# ══════════════════════════════════════════════════════════════════════════════
class ServiceAvail(db.Model):
    __tablename__ = "service_avails"

    id           = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id      = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)  # nullable for walk-ins
    service_id   = db.Column(db.Integer, db.ForeignKey("services.id"), nullable=False)
    quantity     = db.Column(db.Integer, nullable=False, default=1)
    total_price  = db.Column(db.Numeric(10,2), nullable=False)
    avail_date   = db.Column(db.Date,    nullable=False)
    status       = db.Column(db.Enum("pending", "confirmed", "cancelled", "completed"), default="confirmed")
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

    service = db.relationship("Service", backref="avails", lazy=True)
    user    = db.relationship("User",    backref="service_avails", lazy=True)

    def to_dict(self):
        return {
            "id":           self.id,
            "user_id":      self.user_id,
            "service_id":   self.service_id,
            "service_name": self.service.name if self.service else None,
            "quantity":     self.quantity,
            "total_price":  float(self.total_price),
            "avail_date":   self.avail_date.isoformat(),
            "status":       self.status,
            "created_at":   self.created_at.isoformat(),
        }


# ══════════════════════════════════════════════════════════════════════════════
#  REVIEW
# ══════════════════════════════════════════════════════════════════════════════
class Review(db.Model):
    __tablename__ = "reviews"

    id         = db.Column(db.Integer,   primary_key=True, autoincrement=True)
    user_id    = db.Column(db.Integer,   db.ForeignKey("users.id"),    nullable=False)
    room_id    = db.Column(db.Integer,   db.ForeignKey("rooms.id"),    nullable=False)
    booking_id = db.Column(db.Integer,   db.ForeignKey("bookings.id"), nullable=False, unique=True)
    rating     = db.Column(db.SmallInteger, nullable=False)   # 1–5
    review     = db.Column(db.Text)
    created_at = db.Column(db.DateTime,  default=datetime.utcnow)

    # relationships
    user    = db.relationship("User",    backref="reviews",  lazy=True)
    room    = db.relationship("Room",    backref="reviews",  lazy=True)
    booking = db.relationship("Booking", backref="review",   lazy=True, uselist=False)

    def to_dict(self):
        return {
            "id":         self.id,
            "user_id":    self.user_id,
            "room_id":    self.room_id,
            "booking_id": self.booking_id,
            "guest_name": self.user.name if self.user else "Guest",
            "rating":     self.rating,
            "review":     self.review,
            "created_at": self.created_at.isoformat(),
        }