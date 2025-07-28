

from flask import Flask, request, jsonify, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
app = Flask(__name__)
from config import Config
from database.db import db
from models.url_model import URL
from models.click_model import Click  # Assuming you track clicks
from routes.shortener_routes import shortener_bp
from middleware.logging_middleware import LoggingMiddleware
import random
import string
from datetime import datetime, timedelta

# Initialize Flask app

app.config.from_object(Config)

# Middleware
app.wsgi_app = LoggingMiddleware(app.wsgi_app)  # Proper middleware attachment

# Database setup
db.init_app(app)
migrate = Migrate(app, db)

# Utility: Generate random shortcode
def generate_shortcode(length=6):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

# Utility: Validate URL
def is_valid_url(url):
    return url.startswith('http://') or url.startswith('https://')

# Route: Create short URL
@app.route('/shorturls', methods=['POST'])
def create_short_url():
    data = request.get_json()
    url = data.get('url')
    validity = data.get('validity', 30)
    shortcode = data.get('shortcode')

    if not url or not is_valid_url(url):
        return jsonify({"error": "Invalid or missing URL."}), 400

    # Handle shortcode uniqueness
    if shortcode:
        if URL.query.filter_by(shortcode=shortcode).first():
            return jsonify({"error": "Shortcode already exists."}), 409
    else:
        shortcode = generate_shortcode()
        while URL.query.filter_by(shortcode=shortcode).first():
            shortcode = generate_shortcode()

    now = datetime.utcnow()
    expiry = now + timedelta(minutes=int(validity))

    new_url = URL(
        original_url=url,
        shortcode=shortcode,
        created_at=now,
        expires_at=expiry
    )
    db.session.add(new_url)
    db.session.commit()

    return jsonify({
        "shortLink": f"http://localhost:5000/{shortcode}",
        "expiry": expiry.isoformat() + 'Z'
    }), 201

# Route: Redirect using shortcode
@app.route('/<shortcode>', methods=['GET'])
def redirect_short_url(shortcode):
    entry = URL.query.filter_by(shortcode=shortcode).first()
    if not entry:
        return jsonify({"error": "Shortcode does not exist."}), 404

    if datetime.utcnow() > entry.expires_at:
        return jsonify({"error": "Shortcode has expired."}), 410

    click = Click(
        url_id=entry.id,
        timestamp=datetime.utcnow(),
        referrer=request.referrer,
        ip_address=request.remote_addr
    )
    db.session.add(click)
    db.session.commit()

    return redirect(entry.original_url, code=302)

# Route: Get stats
@app.route('/shorturls/<shortcode>', methods=['GET'])
def get_stats(shortcode):
    entry = URL.query.filter_by(shortcode=shortcode).first()
    if not entry:
        return jsonify({"error": "Shortcode not found."}), 404

    clicks = entry.clicks  # assuming relationship is set
    return jsonify({
        "original_url": entry.original_url,
        "created_at": entry.created_at.isoformat() + 'Z',
        "expiry": entry.expires_at.isoformat() + 'Z',
        "total_clicks": len(clicks),
        "clicks": [
            {
                "timestamp": click.timestamp.isoformat() + 'Z',
                "referrer": click.referrer,
                "ip_address": click.ip_address
            } for click in clicks
        ]
    }), 200

if __name__ == '__main__':
    app.run(debug=True)
