"""
routes/auth.py
"""

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import (
    create_access_token, jwt_required, get_jwt_identity, get_jwt
)
from models import User
from extensions import db, bcrypt
import secrets, time, threading, os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

auth_bp = Blueprint("auth", __name__)

BLOCKLIST = set()
RESET_TOKENS = {}
VERIFY_TOKENS = {}


# ── HELPER: Send email via SendGrid in background ─────────────────────────────
def send_email_async(to_email, subject, html_content):
    def _send():
        try:
            message = Mail(
                from_email=("Minnie's Farm Resort", "moralesmickdaniel7@gmail.com"),
                to_emails=to_email,
                subject=subject,
                html_content=html_content
            )
            sg = SendGridAPIClient(os.getenv('SENDGRID_API_KEY'))
            sg.send(message)
            print(f"Email sent to {to_email}")
        except Exception as e:
            print(f"Email sending failed: {e}")
    threading.Thread(target=_send).start()


# ── REGISTER ──────────────────────────────────────────────────────────────────
@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    required = ["name", "email", "password"]
    for field in required:
        if not data.get(field):
            return jsonify({"error": f"'{field}' is required."}), 400

    if User.query.filter_by(email=data["email"]).first():
        return jsonify({"error": "Email is already registered."}), 409

    hashed_pw = bcrypt.generate_password_hash(data["password"]).decode("utf-8")
    user = User(
        name        = data["name"],
        email       = data["email"],
        password    = hashed_pw,
        role        = "guest",
        is_verified = False,
    )
    db.session.add(user)
    db.session.commit()

    token = secrets.token_urlsafe(32)
    VERIFY_TOKENS[token] = {'user_id': user.id, 'expires': time.time() + 86400}
    verify_link = f"https://mdmorales-byte.github.io/minnies-farm-resort?verify_token={token}"

    send_email_async(
        data["email"],
        "Verify Your Email - Minnie's Farm Resort",
        f"""
        <div style="font-family: Arial, sans-serif; max-width: 500px; margin: 0 auto;">
            <h2 style="color: #1a2e2a;">🌿 Minnie's Farm Resort</h2>
            <p>Hi {data["name"]},</p>
            <p>Please verify your email to activate your account:</p>
            <a href="{verify_link}" style="display:inline-block;padding:12px 24px;background:#2d6a5f;color:white;text-decoration:none;border-radius:8px;margin:16px 0;">
                Verify My Email
            </a>
            <p style="color:#888;font-size:0.85rem;">This link expires in 24 hours.</p>
        </div>
        """
    )

    return jsonify({"message": "Account created! Please check your email to verify your account."}), 201


# ── LOGIN ─────────────────────────────────────────────────────────────────────
@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    if not data.get("email") or not data.get("password"):
        return jsonify({"error": "Email and password are required."}), 400

    user = User.query.filter_by(email=data["email"]).first()

    if not user or not bcrypt.check_password_hash(user.password, data["password"]):
        return jsonify({"error": "Invalid email or password."}), 401

    if not user.is_verified:
        return jsonify({"error": "Please verify your email before signing in."}), 401

    token = create_access_token(identity=str(user.id))
    return jsonify({
        "message": "Login successful!",
        "token":   token,
        "user":    user.to_dict(),
    }), 200


# ── LOGOUT ────────────────────────────────────────────────────────────────────
@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    jti = get_jwt()["jti"]
    BLOCKLIST.add(jti)
    return jsonify({"message": "Logged out successfully."}), 200


# ── GET CURRENT USER ──────────────────────────────────────────────────────────
@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    user_id = get_jwt_identity()
    user    = User.query.get_or_404(user_id)
    return jsonify({"user": user.to_dict()}), 200


# ── GOOGLE LOGIN ──────────────────────────────────────────────────────────────
@auth_bp.route('/google', methods=['POST'])
def google_login():
    data = request.get_json()
    email = data.get('email')
    name = data.get('name')
    google_id = data.get('google_id')

    if not email or not google_id:
        return jsonify({'error': 'Invalid Google credentials'}), 400

    user = User.query.filter_by(email=email).first()

    if not user:
        user = User(
            name        = name,
            email       = email,
            password    = bcrypt.generate_password_hash(google_id).decode('utf-8'),
            role        = 'guest',
            is_verified = True,
        )
        db.session.add(user)
        db.session.commit()

    token = create_access_token(identity=str(user.id))
    return jsonify({'token': token, 'user': user.to_dict()}), 200


# ── FACEBOOK LOGIN ────────────────────────────────────────────────────────────
@auth_bp.route('/facebook', methods=['POST'])
def facebook_login():
    data = request.get_json()
    email = data.get('email')
    name = data.get('name')
    facebook_id = data.get('facebook_id')

    if not email or not facebook_id:
        return jsonify({'error': 'Invalid Facebook credentials'}), 400

    user = User.query.filter_by(email=email).first()

    if not user:
        user = User(
            name        = name,
            email       = email,
            password    = bcrypt.generate_password_hash(facebook_id).decode('utf-8'),
            role        = 'guest',
            is_verified = True,
        )
        db.session.add(user)
        db.session.commit()

    token = create_access_token(identity=str(user.id))
    return jsonify({'token': token, 'user': user.to_dict()}), 200


# ── FORGOT PASSWORD ───────────────────────────────────────────────────────────
@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json()
    email = data.get('email')

    if not email:
        return jsonify({'error': 'Email is required.'}), 400

    user = User.query.filter_by(email=email).first()

    if user:
        token = secrets.token_urlsafe(32)
        RESET_TOKENS[token] = {'user_id': user.id, 'expires': time.time() + 3600}
        reset_link = f"https://mdmorales-byte.github.io/minnies-farm-resort?reset_token={token}"

        send_email_async(
            email,
            "Reset Your Password - Minnie's Farm Resort",
            f"""
            <div style="font-family: Arial, sans-serif; max-width: 500px; margin: 0 auto;">
                <h2 style="color: #1a2e2a;">🌿 Minnie's Farm Resort</h2>
                <p>Hi {user.name},</p>
                <p>We received a request to reset your password. Click the button below:</p>
                <a href="{reset_link}" style="display:inline-block;padding:12px 24px;background:#2d6a5f;color:white;text-decoration:none;border-radius:8px;margin:16px 0;">
                    Reset My Password
                </a>
                <p style="color:#888;font-size:0.85rem;">This link expires in 1 hour.</p>
            </div>
            """
        )

    return jsonify({'message': 'If that email exists, a reset link has been sent.'}), 200


# ── RESET PASSWORD ────────────────────────────────────────────────────────────
@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json()
    token = data.get('token')
    new_password = data.get('password')

    if not token or not new_password:
        return jsonify({'error': 'Token and password are required.'}), 400

    token_data = RESET_TOKENS.get(token)
    if not token_data:
        return jsonify({'error': 'Invalid or expired reset token.'}), 400

    if time.time() > token_data['expires']:
        del RESET_TOKENS[token]
        return jsonify({'error': 'Reset token has expired.'}), 400

    user = User.query.get(token_data['user_id'])
    if not user:
        return jsonify({'error': 'User not found.'}), 404

    user.password = bcrypt.generate_password_hash(new_password).decode('utf-8')
    db.session.commit()
    del RESET_TOKENS[token]
    return jsonify({'message': 'Password reset successfully!'}), 200


# ── VERIFY EMAIL ──────────────────────────────────────────────────────────────
@auth_bp.route("/verify-email", methods=["GET"])
def verify_email():
    token = request.args.get('token')
    if not token:
        return jsonify({"error": "Token is required."}), 400

    token_data = VERIFY_TOKENS.get(token)
    if not token_data:
        return jsonify({"error": "Invalid or expired token."}), 400

    if time.time() > token_data['expires']:
        del VERIFY_TOKENS[token]
        return jsonify({"error": "Token has expired."}), 400

    user = User.query.get(token_data['user_id'])
    if not user:
        return jsonify({"error": "User not found."}), 404

    user.is_verified = True
    db.session.commit()
    del VERIFY_TOKENS[token]
    return jsonify({"message": "Email verified! You can now sign in."}), 200