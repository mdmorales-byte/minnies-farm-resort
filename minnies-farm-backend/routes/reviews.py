"""
routes/reviews.py
GET  /api/reviews?room_id=<id>  – fetch reviews + avg rating for a room
POST /api/reviews               – submit a review (JWT required)
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Review, Booking, User

reviews_bp = Blueprint("reviews", __name__)


# ── GET REVIEWS FOR A ROOM ────────────────────────────────────────────────────
@reviews_bp.route("", methods=["GET"])
def get_reviews():
    room_id = request.args.get("room_id", type=int)
    if not room_id:
        return jsonify({"error": "room_id query parameter is required."}), 400

    reviews = (
        Review.query
        .filter_by(room_id=room_id)
        .order_by(Review.created_at.desc())
        .all()
    )

    total   = len(reviews)
    average = round(sum(r.rating for r in reviews) / total, 1) if total else 0

    return jsonify({
        "reviews":        [r.to_dict() for r in reviews],
        "average_rating": average,
        "total_reviews":  total,
    }), 200


# ── SUBMIT A REVIEW ───────────────────────────────────────────────────────────
@reviews_bp.route("", methods=["POST"])
@jwt_required()
def submit_review():
    from app import db

    user_id = get_jwt_identity()
    user    = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found."}), 404

    data       = request.get_json()
    room_id    = data.get("room_id")
    booking_id = data.get("booking_id")
    rating     = data.get("rating")
    review_txt = data.get("review", "")

    # --- basic validation ---
    if not room_id or not booking_id or not rating:
        return jsonify({"error": "room_id, booking_id, and rating are required."}), 400

    if not isinstance(rating, int) or not (1 <= rating <= 5):
        return jsonify({"error": "rating must be an integer between 1 and 5."}), 400

    # --- verify the booking belongs to this user and is completed ---
    booking = Booking.query.get(booking_id)
    if not booking:
        return jsonify({"error": "Booking not found."}), 404
    if int(booking.user_id) != int(user_id):
        return jsonify({"error": "You can only review your own bookings."}), 403
    if booking.room_id != room_id:
        return jsonify({"error": "Booking does not match the specified room."}), 400
    if booking.status != "completed":
        return jsonify({"error": "You can only review completed stays."}), 400

    # --- prevent duplicate reviews (also enforced by DB UNIQUE on booking_id) ---
    existing = Review.query.filter_by(booking_id=booking_id).first()
    if existing:
        return jsonify({"error": "You have already reviewed this booking."}), 409

    review = Review(
        user_id    = user_id,
        room_id    = room_id,
        booking_id = booking_id,
        rating     = rating,
        review     = review_txt,
    )
    db.session.add(review)
    db.session.commit()

    return jsonify({
        "message": "Review submitted successfully!",
        "review":  review.to_dict(),
    }), 201