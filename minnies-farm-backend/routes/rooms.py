"""
routes/rooms.py
"""

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
import os
from werkzeug.utils import secure_filename
import uuid
import supabase_client

rooms_bp = Blueprint("rooms", __name__)

VALID_STATUSES = {"available", "fully_booked", "under_maintenance"}
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ── helper: staff guard ───────────────────────────────────────────────────────
def require_staff():
    user_id = get_jwt_identity()
    user = supabase_client.get_user_by_id(user_id)
    if not user or user.get('role') != "staff":
        return None, (jsonify({"error": "Staff access required."}), 403)
    return user, None


# ── GET ALL ROOMS (with optional filters) ─────────────────────────────────────
@rooms_bp.route("", methods=["GET"])
def get_rooms():
    try:
        rooms = supabase_client.get_rooms()
        
        # Apply filters
        room_type = request.args.get("type")
        if room_type:
            rooms = [r for r in rooms if r.get('type') == room_type]
            
        max_price = request.args.get("max_price")
        if max_price:
            rooms = [r for r in rooms if float(r.get('price_per_night', 0)) <= float(max_price)]
            
        capacity = request.args.get("capacity")
        if capacity:
            rooms = [r for r in rooms if int(r.get('capacity', 0)) >= int(capacity)]
            
        return jsonify({"rooms": rooms}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── GET SINGLE ROOM ───────────────────────────────────────────────────────────
@rooms_bp.route("/<int:room_id>", methods=["GET"])
def get_room(room_id):
    room = supabase_client.get_room_by_id(room_id)
    if not room:
        return jsonify({"error": "Room not found"}), 404
    return jsonify({"room": room}), 200



# ── CREATE ROOM (staff only) ──────────────────────────────────────────────────
@rooms_bp.route("", methods=["POST"])
@jwt_required()
def create_room():
    from app import db
    _, err = require_staff()
    if err:
        return err

    data = request.get_json()
    required = ["room_number", "name", "type", "capacity", "price_per_night"]
    for field in required:
        if data.get(field) is None:
            return jsonify({"error": f"'{field}' is required."}), 400

    if Room.query.filter_by(room_number=data["room_number"]).first():
        return jsonify({"error": "Room number already exists."}), 409

    room_status = data.get("room_status", "available")
    if room_status not in VALID_STATUSES:
        return jsonify({"error": f"Invalid room_status. Use: {', '.join(VALID_STATUSES)}"}), 400

    room = Room(
        room_number     = data["room_number"],
        name            = data["name"],
        type            = data["type"],
        capacity        = int(data["capacity"]),
        price_per_night = float(data["price_per_night"]),
        description     = data.get("description", ""),
        amenities       = ", ".join(data["amenities"]) if isinstance(data.get("amenities"), list) else data.get("amenities", ""),
        image_url       = data.get("image_url", ""),
        image_url_2     = data.get("image_url_2", ""),
        image_url_3     = data.get("image_url_3", ""),
        image_url_4     = data.get("image_url_4", ""),
        image_url_5     = data.get("image_url_5", ""),
        sqm             = data.get("sqm"),
        is_available    = room_status == "available",
        room_status     = room_status,
    )
    db.session.add(room)
    db.session.commit()
    return jsonify({"message": "Room created successfully!", "room": room.to_dict()}), 201


# ── UPDATE ROOM (staff only) ──────────────────────────────────────────────────
@rooms_bp.route("/<int:room_id>", methods=["PUT"])
@jwt_required()
def update_room(room_id):
    from app import db
    _, err = require_staff()
    if err:
        return err

    room = Room.query.get_or_404(room_id)
    data = request.get_json()

    room.name            = data.get("name",            room.name)
    room.type            = data.get("type",            room.type)
    room.capacity        = data.get("capacity",        room.capacity)
    room.price_per_night = data.get("price_per_night", room.price_per_night)
    room.description     = data.get("description",     room.description)
    room.sqm             = data.get("sqm",             room.sqm)
    room.image_url       = data.get("image_url",       room.image_url)
    room.image_url_2     = data.get("image_url_2",     room.image_url_2)
    room.image_url_3     = data.get("image_url_3",     room.image_url_3)
    room.image_url_4     = data.get("image_url_4",     room.image_url_4)
    room.image_url_5     = data.get("image_url_5",     room.image_url_5)

    if "room_status" in data:
        room_status = data["room_status"]
        if room_status not in VALID_STATUSES:
            return jsonify({"error": f"Invalid room_status. Use: {', '.join(VALID_STATUSES)}"}), 400
        room.room_status  = room_status
        room.is_available = room_status == "available"

    if "amenities" in data:
        room.amenities = ", ".join(data["amenities"]) if isinstance(data["amenities"], list) else data["amenities"]

    db.session.commit()
    return jsonify({"message": "Room updated successfully!", "room": room.to_dict()}), 200


# ── DELETE ROOM (staff only) ──────────────────────────────────────────────────
@rooms_bp.route("/<int:room_id>", methods=["DELETE"])
@jwt_required()
def delete_room(room_id):
    from app import db
    _, err = require_staff()
    if err:
        return err

    room = Room.query.get_or_404(room_id)

    active = Booking.query.filter_by(room_id=room_id).filter(
        Booking.status.in_(["confirmed", "pending"])
    ).first()
    if active:
        return jsonify({"error": "Cannot delete a room with active bookings."}), 400

    db.session.delete(room)
    db.session.commit()
    return jsonify({"message": "Room deleted successfully."}), 200


# ── CHECK AVAILABILITY ────────────────────────────────────────────────────────
@rooms_bp.route("/<int:room_id>/availability", methods=["POST"])
def check_availability(room_id):
    Room.query.get_or_404(room_id)
    data = request.get_json()

    try:
        ci = date.fromisoformat(data["check_in"])
        co = date.fromisoformat(data["check_out"])
    except (KeyError, ValueError):
        return jsonify({"error": "Provide valid 'check_in' and 'check_out' (YYYY-MM-DD)."}), 400

    if co <= ci:
        return jsonify({"error": "check_out must be after check_in."}), 400

    conflict = Booking.query.filter(
        Booking.room_id  == room_id,
        Booking.status.in_(["confirmed", "pending"]),
        Booking.check_in_date  < co,
        Booking.check_out_date > ci,
    ).first()

    return jsonify({
        "available": conflict is None,
        "room_id":   room_id,
        "check_in":  data["check_in"],
        "check_out": data["check_out"],
    }), 200


# ── UPLOAD IMAGE ──────────────────────────────────────────────────────────────
@rooms_bp.route("/upload-image", methods=["POST"])
@jwt_required()
def upload_room_image():
    _, err = require_staff()
    if err:
        return err

    if 'image' not in request.files:
        return jsonify({"error": "No image file provided."}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({"error": "No selected file."}), 400
    
    if file and allowed_file(file.filename):
        # Generate unique filename
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Return the public URL for the uploaded image
        # Assuming the server is serving /uploads folder at /uploads/
        image_url = f"{request.host_url}uploads/{filename}"
        return jsonify({"message": "Image uploaded successfully!", "image_url": image_url}), 200
    
    return jsonify({"error": "Invalid file type. Allowed: png, jpg, jpeg, gif, webp"}), 400