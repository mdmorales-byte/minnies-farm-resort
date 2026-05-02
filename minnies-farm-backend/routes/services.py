"""
routes/services.py
GET  /api/services              – list all active services
GET  /api/services/<id>         – get single service
POST /api/services              – create service  (staff only)
PUT  /api/services/<id>         – update service  (staff only)
DELETE /api/services/<id>       – deactivate service (staff only)
POST /api/services/<id>/avail   – guest avails a service
GET  /api/services/avails       – get avail records (staff: all, guest: own)
PUT  /api/services/avails/<id>/status – update avail status (staff only)
DELETE /api/services/avails/<id> – delete avail record (staff only)
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from models import Service, ServiceAvail, User
from datetime import date

services_bp = Blueprint("services", __name__)


def require_staff():
    user_id = get_jwt_identity()
    user    = User.query.get(user_id)
    if not user or user.role != "staff":
        return None, (jsonify({"error": "Staff access required."}), 403)
    return user, None


# ── GET ALL SERVICES ──────────────────────────────────────────────────────────
@services_bp.route("", methods=["GET"])
def get_services():
    try:
        services = Service.query.filter_by(is_active=True).all()
        return jsonify({"services": [s.to_dict() for s in services]}), 200
    except Exception as e:
        print(f"Error fetching services: {str(e)}")
        # If stock_quantity is missing, return services without it
        try:
            services = Service.query.filter_by(is_active=True).all()
            result = []
            for s in services:
                d = {
                    "id": s.id,
                    "name": s.name,
                    "description": s.description,
                    "price": float(s.price),
                    "category": s.category,
                    "stock_quantity": -1, # Default if column missing
                    "is_active": s.is_active
                }
                result.append(d)
            return jsonify({"services": result}), 200
        except Exception as e2:
            return jsonify({"error": str(e2)}), 500


# ── GET SINGLE SERVICE ────────────────────────────────────────────────────────
@services_bp.route("/<int:service_id>", methods=["GET"])
def get_service(service_id):
    service = Service.query.get_or_404(service_id)
    return jsonify({"service": service.to_dict()}), 200


# ── CREATE SERVICE (staff only) ───────────────────────────────────────────────
@services_bp.route("", methods=["POST"])
@jwt_required()
def create_service():
    from app import db
    _, err = require_staff()
    if err:
        return err

    data = request.get_json()
    if not data.get("name") or data.get("price") is None:
        return jsonify({"error": "'name' and 'price' are required."}), 400

    service = Service(
        name           = data["name"],
        description    = data.get("description", ""),
        price          = float(data["price"]),
        category       = data.get("category", "day_service"),
        stock_quantity = int(data.get("stock_quantity", -1)),
        is_active      = data.get("is_active", True),
    )
    db.session.add(service)
    db.session.commit()
    return jsonify({"message": "Service created!", "service": service.to_dict()}), 201


# ── UPDATE SERVICE (staff only) ───────────────────────────────────────────────
@services_bp.route("/<int:service_id>", methods=["PUT"])
@jwt_required()
def update_service(service_id):
    from app import db
    _, err = require_staff()
    if err:
        return err

    service = Service.query.get_or_404(service_id)
    data    = request.get_json()

    service.name        = data.get("name",        service.name)
    service.description = data.get("description", service.description)
    service.price          = data.get("price",          service.price)
    service.category       = data.get("category",       service.category)
    service.stock_quantity = data.get("stock_quantity", service.stock_quantity)
    service.is_active      = data.get("is_active",      service.is_active)
    db.session.commit()
    return jsonify({"message": "Service updated!", "service": service.to_dict()}), 200


# ── DEACTIVATE SERVICE (staff only) ───────────────────────────────────────────
@services_bp.route("/<int:service_id>", methods=["DELETE"])
@jwt_required()
def delete_service(service_id):
    from app import db
    _, err = require_staff()
    if err:
        return err

    service           = Service.query.get_or_404(service_id)
    service.is_active = False
    db.session.commit()
    return jsonify({"message": "Service deactivated."}), 200


# ── AVAIL A SERVICE ───────────────────────────────────────────────────────────
@services_bp.route("/<int:service_id>/avail", methods=["POST"])
def avail_service(service_id):
    from app import db
    """
    Guests can avail while logged in.
    Walk-in guests (no token) can also avail — user_id will be None.
    """
    service = Service.query.get_or_404(service_id)
    if not service.is_active:
        return jsonify({"error": "This service is currently unavailable."}), 400

    data = request.get_json() or {}

    # Optionally get logged-in user
    user_id = None
    try:
        verify_jwt_in_request(optional=True)
        user_id = get_jwt_identity()
    except Exception:
        pass

    quantity   = int(data.get("quantity", 1))
    avail_date = data.get("avail_date", date.today().isoformat())

    try:
        avail_date = date.fromisoformat(avail_date)
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD."}), 400

    total_price = float(service.price) * quantity

    avail = ServiceAvail(
        user_id     = int(user_id) if user_id else None,
        service_id  = service.id,
        quantity    = quantity,
        total_price = total_price,
        avail_date  = avail_date,
        status      = "confirmed",
    )
    db.session.add(avail)
    db.session.commit()

    return jsonify({
        "message":     f"'{service.name}' availed successfully! 🎉",
        "avail":       avail.to_dict(),
        "total_price": total_price,
    }), 201


# ── GET AVAIL RECORDS ─────────────────────────────────────────────────────────
@services_bp.route("/avails", methods=["GET"])
@jwt_required()
def get_avails():
    user_id = get_jwt_identity()
    user    = User.query.get_or_404(user_id)

    if user.role == "staff":
        avails = ServiceAvail.query.order_by(ServiceAvail.created_at.desc()).all()
    else:
        avails = ServiceAvail.query.filter_by(user_id=user_id).order_by(ServiceAvail.created_at.desc()).all()

    result = []
    for a in avails:
        d = a.to_dict()
        guest = User.query.get(a.user_id) if a.user_id else None
        d['guest_name'] = guest.name if guest else 'Walk-in'
        d['service_name'] = a.service.name if a.service else 'Unknown'
        result.append(d)

    return jsonify({"avails": result}), 200


# ── UPDATE AVAIL STATUS (staff only) ─────────────────────────────────────────────
@services_bp.route("/avails/<int:avail_id>/status", methods=["PUT"])
@jwt_required()
def update_avail_status(avail_id):
    from app import db
    _, err = require_staff()
    if err:
        return err

    avail = ServiceAvail.query.get_or_404(avail_id)
    data = request.get_json()
    
    if not data or 'status' not in data:
        return jsonify({"error": "Status is required"}), 400
    
    valid_statuses = ['pending', 'confirmed', 'completed', 'cancelled']
    if data['status'] not in valid_statuses:
        return jsonify({"error": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"}), 400
    
    avail.status = data['status']
    db.session.commit()
    
    return jsonify({
        "message": "Service avail status updated successfully.",
        "avail": avail.to_dict()
    }), 200

# ── DELETE AVAIL RECORD (staff only) ─────────────────────────────────────────────
@services_bp.route("/avails/<int:avail_id>", methods=["DELETE"])
@jwt_required()
def delete_avail(avail_id):
    from app import db
    _, err = require_staff()
    if err:
        return err

    avail = ServiceAvail.query.get_or_404(avail_id)
    db.session.delete(avail)
    db.session.commit()
    return jsonify({"message": "Service avail record deleted."}), 200
