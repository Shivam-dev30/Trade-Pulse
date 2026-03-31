import os
import json
import razorpay
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from models import db, User
from flask_login import LoginManager

load_dotenv()

app = Flask(__name__, static_folder='frontend')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///subscriptions.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'algo-trade-pulse-secret-key')

# Razorpay credentials
RAZORPAY_KEY_ID = os.getenv('RAZORPAY_KEY_ID', 'rzp_test_replace_me')
RAZORPAY_KEY_SECRET = os.getenv('RAZORPAY_KEY_SECRET', 'test_secret_replace_me')

# Shared State for Live Monitoring
live_prices = {}

razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

CORS(app)
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)

with app.app_context():
    db.create_all()
    # Mocking first user for development
    if not User.query.filter_by(username='demo_user').first():
        new_user = User(username='demo_user', email='demo@example.com', subscription_tier='ELITE')
        db.session.add(new_user)
        db.session.commit()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Serve Frontend ---
@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(app.static_folder, path)

# --- Subscription API ---
@app.route('/api/user/subscription', methods=['GET'])
def get_subscription_status():
    user = User.query.filter_by(username='demo_user').first()
    if not user:
        return jsonify({"error": "No user found"}), 404
        
    return jsonify({
        "tier": user.subscription_tier,
        "status": user.subscription_status,
        "limits": user.get_tier_limits(),
        "usage": {
            "alerts": user.alerts_created,
            "indicators": user.indicators_active,
            "watchlists": user.watchlists_count
        }
    })

@app.route('/api/create-order', methods=['POST'])
def create_subscription_order():
    data = request.json
    tier = data.get('tier')
    is_annual = data.get('isAnnual', False)
    
    price_map = {
        'STARTER': 14900 if not is_annual else 149000,
        'PRO': 39900 if not is_annual else 399000,
        'ELITE': 79900 if not is_annual else 799000
    }
    
    amount = price_map.get(tier)
    if not amount:
        return jsonify({"error": "Invalid tier"}), 400

    order_payload = {
        'amount': amount,
        'currency': 'INR',
        'payment_capture': '1'
    }
    
    try:
        order = razorpay_client.order.create(data=order_payload)
        return jsonify(order)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/verify-payment', methods=['POST'])
def verify_payment():
    data = request.json
    params_dict = {
        'razorpay_order_id': data.get('razorpay_order_id'),
        'razorpay_payment_id': data.get('razorpay_payment_id'),
        'razorpay_signature': data.get('razorpay_signature')
    }
    tier = data.get('tier')

    try:
        # For testing purposes, you can comment signature verification if using mock keys
        if RAZORPAY_KEY_ID != 'rzp_test_replace_me':
            razorpay_client.utility.verify_payment_signature(params_dict)
        
        user = User.query.filter_by(username='demo_user').first()
        user.subscription_tier = tier
        user.subscription_status = 'active'
        db.session.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "failed", "error": str(e)}), 400

@app.route('/api/user/update-usage', methods=['POST'])
def update_usage():
    data = request.json
    user = User.query.filter_by(username='demo_user').first()
    if data.get('indicators') is not None:
        user.indicators_active = data.get('indicators')
    if data.get('alerts') is not None:
        user.alerts_created = data.get('alerts')
    db.session.commit()
    return jsonify({"status": "success"})

# Original Config API functionality
CONFIG_FILE = 'dynamic_config.json'

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {"indian_enabled": True, "crypto_enabled": True, "indian_indicators": [], "crypto_indicators": []}
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

@app.route('/api/config', methods=['GET'])
def get_config():
    return jsonify(load_config())

@app.route('/api/config', methods=['POST'])
def update_config():
    new_cfg = request.json
    with open(CONFIG_FILE, 'w') as f:
        json.dump(new_cfg, f, indent=4)
    return jsonify({"status": "success"})

@app.route('/api/test_alert', methods=['POST'])
def test_alert():
    try:
        from alerts.email_service import send_alert
        success = send_alert("Frontend Test Alert", "This is an automated test alert requested directly from the web interface.")
        return jsonify({"success": success})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/live-prices')
def get_live_prices():
    return jsonify(live_prices)

def start_server():
    """Helper for main.py to start the server in a separate thread."""
    app.run(host='0.0.0.0', port=5000, use_reloader=False)

if __name__ == '__main__':
    start_server()
