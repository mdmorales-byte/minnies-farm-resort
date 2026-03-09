"""
routes/bookings.py
GET    /api/bookings        – guest: own bookings | staff: all bookings
GET    /api/bookings/<id>   – get single booking
POST   /api/bookings        – create booking (guests only)
PUT    /api/bookings/<id>   – update dates   (guest owner only)
DELETE /api/bookings/<id>   – cancel/delete booking (guest owner or staff)
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Booking, Room, User
from datetime import date
import random, string

bookings_bp = Blueprint("bookings", __name__)

RESORT_FEE_RATE = 0.10   # 10 % resort fee


def _generate_ref():
    chars = string.ascii_uppercase + string.digits
    return "MFR-" + "".join(random.choices(chars, k=6))


def _calc_nights(ci: date, co: date) -> int:
    return (co - ci).days


def _check_conflict(room_id, ci, co, exclude_booking_id=None):
    q = Booking.query.filter(
        Booking.room_id  == room_id,
        Booking.status.in_(["confirmed", "pending"]),
        Booking.check_in_date  < co,
        Booking.check_out_date > ci,
    )
    if exclude_booking_id:
        q = q.filter(Booking.id != exclude_booking_id)
    return q.first() is not None


# ── GET BOOKINGS ──────────────────────────────────────────────────────────────
@bookings_bp.route("", methods=["GET"])
@jwt_required()
def get_bookings():
    user_id = get_jwt_identity()
    user    = User.query.get_or_404(user_id)

    if user.role == "staff":
        bookings = Booking.query.order_by(Booking.created_at.desc()).all()
    else:
        bookings = Booking.query.filter_by(user_id=user_id).order_by(Booking.created_at.desc()).all()

    return jsonify({"bookings": [b.to_dict() for b in bookings]}), 200


# ── GET SINGLE BOOKING ────────────────────────────────────────────────────────
@bookings_bp.route("/<int:booking_id>", methods=["GET"])
@jwt_required()
def get_booking(booking_id):
    user_id = get_jwt_identity()
    user    = User.query.get_or_404(user_id)
    booking = Booking.query.get_or_404(booking_id)

    if user.role == "guest" and booking.user_id != int(user_id):
        return jsonify({"error": "Access denied."}), 403

    return jsonify({"booking": booking.to_dict()}), 200


# ── CREATE BOOKING (guests only) ──────────────────────────────────────────────
@bookings_bp.route("", methods=["POST"])
@jwt_required()
def create_booking():
    from extensions import db
    user_id = get_jwt_identity()
    user    = User.query.get_or_404(user_id)

    if user.role != "guest":
        return jsonify({"error": "Only guests can make bookings."}), 403

    data = request.get_json()
    required = ["room_id", "check_in_date", "check_out_date", "num_guests"]
    for field in required:
        if data.get(field) is None:
            return jsonify({"error": f"'{field}' is required."}), 400

    try:
        ci = date.fromisoformat(data["check_in_date"])
        co = date.fromisoformat(data["check_out_date"])
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD."}), 400

    if ci < date.today():
        return jsonify({"error": "check_in_date cannot be in the past."}), 400
    if co <= ci:
        return jsonify({"error": "check_out_date must be after check_in_date."}), 400

    room = Room.query.get_or_404(data["room_id"])

    if int(data["num_guests"]) > room.capacity:
        return jsonify({"error": f"Room capacity is {room.capacity} guests max."}), 400

    if _check_conflict(room.id, ci, co):
        return jsonify({"error": "Room is already booked for the selected dates."}), 409

    nights      = _calc_nights(ci, co)
    subtotal    = float(room.price_per_night) * nights
    resort_fee  = round(subtotal * RESORT_FEE_RATE, 2)
    total_price = round(subtotal + resort_fee, 2)

    ref = _generate_ref()
    while Booking.query.filter_by(reference_code=ref).first():
        ref = _generate_ref()

    booking = Booking(
        user_id        = int(user_id),
        room_id        = room.id,
        check_in_date  = ci,
        check_out_date = co,
        num_guests     = int(data["num_guests"]),
        total_price    = total_price,
        status         = "confirmed",
        reference_code = ref,
    )
    db.session.add(booking)
    db.session.commit()

    return jsonify({
        "message": "Booking confirmed! 🎉",
        "booking": booking.to_dict(),
    }), 201


# ── UPDATE BOOKING (change dates) ─────────────────────────────────────────────
@bookings_bp.route("/<int:booking_id>", methods=["PUT"])
@jwt_required()
def update_booking(booking_id):
    from extensions import db
    user_id = get_jwt_identity()
    booking = Booking.query.get_or_404(booking_id)

    if booking.user_id != int(user_id):
        return jsonify({"error": "You can only modify your own bookings."}), 403
    if booking.status != "confirmed":
        return jsonify({"error": "Only confirmed bookings can be modified."}), 400

    data = request.get_json()

    try:
        ci = date.fromisoformat(data.get("check_in_date",  booking.check_in_date.isoformat()))
        co = date.fromisoformat(data.get("check_out_date", booking.check_out_date.isoformat()))
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD."}), 400

    if ci < date.today():
        return jsonify({"error": "check_in_date cannot be in the past."}), 400
    if co <= ci:
        return jsonify({"error": "check_out_date must be after check_in_date."}), 400

    if _check_conflict(booking.room_id, ci, co, exclude_booking_id=booking_id):
        return jsonify({"error": "Room is already booked for those dates."}), 409

    nights      = _calc_nights(ci, co)
    subtotal    = float(booking.room.price_per_night) * nights
    resort_fee  = round(subtotal * RESORT_FEE_RATE, 2)

    booking.check_in_date  = ci
    booking.check_out_date = co
    booking.num_guests     = data.get("num_guests", booking.num_guests)
    booking.total_price    = round(subtotal + resort_fee, 2)
    db.session.commit()

    return jsonify({"message": "Booking updated successfully!", "booking": booking.to_dict()}), 200


# ── DELETE / CANCEL BOOKING ───────────────────────────────────────────────────
@bookings_bp.route("/<int:booking_id>", methods=["DELETE"])
@jwt_required()
def cancel_booking(booking_id):
    from extensions import db
    user_id = get_jwt_identity()
    user    = User.query.get_or_404(user_id)
    booking = Booking.query.get_or_404(booking_id)

    if user.role == "staff":
        # Staff: hard-delete the booking record entirely
        # Also delete any associated review first (foreign key)
        from models import Review
        review = Review.query.filter_by(booking_id=booking_id).first()
        if review:
            db.session.delete(review)
        db.session.delete(booking)
        db.session.commit()
        return jsonify({"message": "Booking deleted successfully."}), 200
    else:
        # Guest: can only cancel their own, and only if not already done
        if booking.user_id != int(user_id):
            return jsonify({"error": "You can only cancel your own bookings."}), 403
        if booking.status in ("cancelled", "completed"):
            return jsonify({"error": f"Booking is already {booking.status}."}), 400
        booking.status = "cancelled"
        db.session.commit()
        return jsonify({"message": "Booking cancelled successfully.", "booking": booking.to_dict()}), 200


# ── UPDATE BOOKING STATUS (staff only) ───────────────────────────────────────
@bookings_bp.route("/<int:booking_id>/status", methods=["PUT"])
@jwt_required()
def update_booking_status(booking_id):
    from extensions import db
    user_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)

    if user.role != "staff":
        return jsonify({"error": "Only staff can update booking status."}), 403

    data = request.get_json()
    status = data.get("status")

    if status not in ("pending", "confirmed", "cancelled", "completed"):
        return jsonify({"error": "Invalid status."}), 400

    booking = Booking.query.get_or_404(booking_id)
    booking.status = status
    db.session.commit()

    return jsonify({"message": "Status updated!", "booking": booking.to_dict()}), 200