from flask import Flask, request, jsonify
import joblib
import re
import subprocess
from urllib.parse import urlparse
import os

app = Flask(__name__)

HOSTS_HELPER = "hosts_blocker.py"
MODEL_PATH = "url_model.pkl"

try:
    model = joblib.load(MODEL_PATH)
    print("Model loaded successfully.")
except Exception as e:
    print("Model loading failed:", e)
    model = None

def featurize(url: str):
    u = url.lower()
    return {
        "length": len(u),
        "digits": sum(c.isdigit() for c in u),
        "dots": u.count("."),
        "https": u.startswith("https"),
        "suspicious_words": any(w in u for w in ["login", "verify", "secure", "account"]),
        "has_ip": bool(re.search(r"\\b\\d{1,3}(?:\\.\\d{1,3}){3}\\b", u)),
    }

def get_domain(url):
    try:
        p = urlparse(url)
        h = p.hostname or url
        return h.replace("www.", "") if h else url
    except:
        return url

@app.route("/")
def index():
    return "<h1>AI Website Blocker Running</h1>"

@app.route("/check", methods=["POST"])
def check_url():
    if model is None:
        return jsonify({"error": "Model unavailable"}), 500

    data = request.get_json()
    url = data.get("url", "")
    if not url:
        return jsonify({"error": "Empty URL"}), 400

    feats = featurize(url)
    try:
        prob = float(model.predict_proba([feats])[0][1])
    except Exception as e:
        return jsonify({"error": "Prediction error", "details": str(e)}), 500

    domain = get_domain(url)
    return jsonify({"domain": domain, "score": prob, "block": prob > 0.6})

@app.route("/api/add", methods=["POST"])
def add_domain():
    data = request.get_json()
    domain = data.get("domain", "")
    if not domain:
        return jsonify({"error": "Missing domain"}), 400

    r = subprocess.run(["python3", HOSTS_HELPER, "add", domain], capture_output=True, text=True)
    if r.returncode != 0:
        return jsonify({"error": r.stderr}), 500
    return jsonify({"added": True})

@app.route("/api/remove", methods=["POST"])
def remove_domain():
    data = request.get_json()
    domain = data.get("domain", "")
    if not domain:
        return jsonify({"error": "Missing domain"}), 400

    r = subprocess.run(["python3", HOSTS_HELPER, "remove", domain], capture_output=True, text=True)
    if r.returncode != 0:
        return jsonify({"error": r.stderr}), 500
    return jsonify({"removed": True})

@app.route("/api/list")
def list_blocked():
    r = subprocess.run(["python3", HOSTS_HELPER, "list"], capture_output=True, text=True)
    if r.returncode != 0:
        return jsonify({"error": r.stderr}), 500

    raw_lines = r.stdout.strip().split("\\n")
    domains = []
    for line in raw_lines:
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) >= 2:
            domains.append(parts[-1])

    return jsonify({"blocked": domains})

if __name__ == "__main__":
    app.run(debug=True, port=5001)
