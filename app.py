from flask import Flask, request, jsonify
import joblib
import re
import subprocess
from urllib.parse import urlparse
import os

app = Flask(__name__)

HOSTS_HELPER = "hosts_blocker.py"
MODEL_PATH = "url_model.pkl"

# Load ML model
try:
    model = joblib.load(MODEL_PATH)
    print("Model loaded successfully.")
except Exception as e:
    print("Error loading model:", e)
    model = None


# ---------------------------
# Feature extraction function
# ---------------------------
def featurize(url: str):
    u = url.lower()
    return {
        "length": len(u),
        "digits": sum(c.isdigit() for c in u),
        "dots": u.count("."),
        "https": u.startswith("https"),
        "suspicious_words": any(w in u for w in ["login", "verify", "secure", "account"]),
        "has_ip": bool(re.search(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", u)),
    }


# Extract domain
def get_domain(url):
    try:
        parsed = urlparse(url)
        h = parsed.hostname or url
        return h.replace("www.", "") if h else url
    except:
        return url


# ---------------------------
# MAIN UI PAGE
# ---------------------------
HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>AI-Powered Website Blocker</title>
    <style>
        body { font-family: Arial; background: #f2f2f2; padding: 20px; }
        .container { 
            max-width: 600px; margin: auto; 
            background: white; padding: 20px; 
            border-radius: 10px; 
            box-shadow: 0 0 10px #ccc;
        }
        input { width: 70%; padding: 10px; }
        button { padding: 10px 15px; }
        .result { margin-top: 20px; padding: 15px; background: #eef; border-radius: 8px; }
        .safe { color: green; font-weight: bold; }
        .danger { color: red; font-weight: bold; }
    </style>
</head>

<body>

<h2 align="center">AI-Powered Website Blocker</h2>

<div class="container">
    <h3>Scan a URL</h3>

    <input id="url" placeholder="Enter URL to scan">
    <button onclick="checkURL()">Check</button>

    <div id="result"></div>
</div>

<br>

<div class="container">
    <h3>Blocked Websites</h3>
    <div id="blocked"></div>
</div>

<script>

// -----------------------
// CHECK URL USING ML
// -----------------------
async function checkURL() {
    let url = document.getElementById("url").value;

    let res = await fetch('/check', {
        method: 'POST',
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url })
    });

    let data = await res.json();
    let box = document.getElementById("result");

    let risk = (data.score * 100).toFixed(1);

    if (data.block) {
        box.innerHTML = `
            <div class="result">
                <p><b>Domain:</b> ${data.domain}</p>
                <p><b>Risk Score:</b> ${risk}%</p>
                <p class="danger">Recommended: BLOCK</p>
                <button onclick="blockSite('${data.domain}')">Block</button>
            </div>
        `;
    } else {
        box.innerHTML = `
            <div class="result">
                <p><b>Domain:</b> ${data.domain}</p>
                <p><b>Risk Score:</b> ${risk}%</p>
                <p class="safe">Recommended: SAFE</p>
            </div>
        `;
    }
}


// -----------------------
// BLOCK DOMAIN
// -----------------------
async function blockSite(domain) {
    await fetch('/api/add', {
        method: 'POST',
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ domain })
    });
    loadBlocked();
}


// -----------------------
// LOAD BLOCKED LIST
// -----------------------
async function loadBlocked() {
    let res = await fetch('/api/list');
    let data = await res.json();

    let area = document.getElementById("blocked");
    area.innerHTML = "";

    data.blocked.forEach(d => {
        area.innerHTML += `
            <p>${d} <button onclick="unblock('${d}')">Unblock</button></p>
        `;
    });
}
loadBlocked();


// -----------------------
// UNBLOCK DOMAIN
// -----------------------
async function unblock(domain) {
    await fetch('/api/remove', {
        method: 'POST',
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ domain })
    });
    loadBlocked();
}

</script>
</body>
</html>
"""


@app.route("/")
def home():
    return HTML


# ---------------------------
# ML CHECK API
# ---------------------------
@app.route("/check", methods=["POST"])
def check():
    if model is None:
        return jsonify({"error": "Model not loaded"}), 500

    data = request.get_json()
    url = data.get("url", "")

    if not url:
        return jsonify({"error": "Empty URL"}), 400

    feats = featurize(url)
    prob = float(model.predict_proba([feats])[0][1])

    domain = get_domain(url)
    return jsonify({
        "domain": domain,
        "score": prob,
        "block": prob > 0.6
    })


# ---------------------------
# BLOCK DOMAIN
# ---------------------------
@app.route("/api/add", methods=["POST"])
def add():
    data = request.get_json()
    domain = data.get("domain", "")
    if not domain:
        return jsonify({"error": "Missing domain"}), 400

    subprocess.run(["python3", HOSTS_HELPER, "add", domain])
    return jsonify({"status": "added"})


# ---------------------------
# REMOVE DOMAIN
# ---------------------------
@app.route("/api/remove", methods=["POST"])
def remove():
    data = request.get_json()
    domain = data.get("domain", "")
    if not domain:
        return jsonify({"error": "Missing domain"}), 400

    subprocess.run(["python3", HOSTS_HELPER, "remove", domain])
    return jsonify({"status": "removed"})


# ---------------------------
# LIST BLOCKED DOMAINS
# ---------------------------
@app.route("/api/list")
def list_blocked():
    result = subprocess.run(["python3", HOSTS_HELPER, "list"], capture_output=True, text=True)

    lines = result.stdout.strip().split("\n")
    domains = [d.split("\t")[-1] for d in lines if d.strip()]

    return jsonify({"blocked": domains})


if __name__ == "__main__":
    app.run(debug=True, port=5001)
