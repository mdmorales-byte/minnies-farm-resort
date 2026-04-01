"""
routes/auth.py
"""

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import (
    create_access_token, jwt_required, get_jwt_identity, get_jwt
)
from models import User
from extensions import db, bcrypt
import secrets, time, threading, os, re
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

auth_bp = Blueprint("auth", __name__)

BLOCKLIST = set()
RESET_TOKENS = {}
VERIFY_TOKENS = {}

# ── EMAIL VALIDATION ──────────────────────────────────────────────────────────
def is_valid_email(email):
    """Validate email format using regex"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


# ── HELPER: Send email via SendGrid in background ─────────────────────────────
def send_email_background(to_email, subject, html_content):
    """Send email asynchronously in background thread via SendGrid"""
    def _send_email():
        try:
            sg_key = os.getenv('SENDGRID_API_KEY')
            if not sg_key:
                print("❌ SENDGRID_API_KEY not set!")
                return
            
            if not sg_key.startswith('SG.'):
                print(f"❌ SENDGRID_API_KEY format invalid! Key starts with: {sg_key[:5]}...")
                return
            
            # Debug: Show we're attempting to send
            print(f"📧 Attempting to send email to {to_email}...")
            print(f"   Subject: {subject}")
            print(f"   From: moralesmickdaniel7@gmail.com")
            
            sg = SendGridAPIClient(sg_key)
            message = Mail(
                from_email='moralesmickdaniel7@gmail.com',
                to_emails=to_email,
                subject=subject,
                html_content=html_content
            )
            response = sg.send(message)
            print(f"✅ Email sent successfully to {to_email} (HTTP {response.status_code})")
        except Exception as e:
            print(f"❌ Email sending failed to {to_email}")
            print(f"   Error Type: {type(e).__name__}")
            print(f"   Error Message: {str(e)}")
            if hasattr(e, 'body'):
                print(f"   Response Body: {e.body}")
            import traceback
            traceback.print_exc()
    
    # Start email sending in background thread (don't wait for it)
    thread = threading.Thread(target=_send_email, daemon=True)
    thread.start()


# ── REGISTER ──────────────────────────────────────────────────────────────────
@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    required = ["name", "email", "password"]
    for field in required:
        if not data.get(field):
            return jsonify({"error": f"'{field}' is required."}), 400

    email = data["email"].strip().lower()
    
    # Validate email format
    if not is_valid_email(email):
        return jsonify({"error": "Please enter a valid email address (e.g., user@example.com)."}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email is already registered."}), 409

    hashed_pw = bcrypt.generate_password_hash(data["password"]).decode("utf-8")
    user = User(
        name        = data["name"],
        email       = email,  # Use normalized email
        password    = hashed_pw,
        role        = "guest",
        is_verified = True,  # Auto-verify on registration
    )
    db.session.add(user)
    db.session.commit()

    # Email verification temporarily disabled - user auto-verified on registration
    # TODO: Re-enable email verification once SendGrid is configured properly

    return jsonify({"message": "Account created! You can now sign in."}), 201


# ── LOGIN ─────────────────────────────────────────────────────────────────────
@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    if not data.get("email") or not data.get("password"):
        return jsonify({"error": "Email and password are required."}), 400

    email = data["email"].strip().lower()
    user = User.query.filter_by(email=email).first()

    if not user or not bcrypt.check_password_hash(user.password, data["password"]):
        return jsonify({"error": "Invalid email or password."}), 401

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

    email = email.strip().lower()
    user = User.query.filter_by(email=email).first()

    if user:
        token = secrets.token_urlsafe(32)
        RESET_TOKENS[token] = {'user_id': user.id, 'expires': time.time() + 3600}
        reset_link = f"https://mdmorales-byte.github.io/minnies-farm-resort?reset_token={token}"

        send_email_background(
            email,
            "Reset Your Password - Minnie's Farm Resort",
            f"""<html><body>
<h2>Minnie's Farm Resort</h2>
<p>Hi {user.name},</p>
<p>We received a request to reset your password. Click the link below:</p>
<p><a href="{reset_link}">Reset My Password</a></p>
<p>This link expires in 1 hour.</p>
</body></html>"""
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