import joblib
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LogisticRegression

def featurize(url: str):
    u = url.lower()
    return {
        "length": len(u),
        "digits": sum(c.isdigit() for c in u),
        "dots": u.count("."),
        "https": u.startswith("https"),
        "suspicious_words": int(any(w in u for w in ["login","verify","secure","account"])),
        "has_ip": int(any(ch.isdigit() for ch in u.split("/")[:1])),
    }

good = ["https://google.com", "https://example.com", "https://github.com"]
bad = ["http://verify-paypal.account-update.com", "http://secure-login-update.bank-alert.com"]

X = [featurize(u) for u in good+bad]
y = [0]*len(good) + [1]*len(bad)

v = DictVectorizer(sparse=False)
Xv = v.fit_transform(X)

clf = LogisticRegression()
clf.fit(Xv, y)

pipeline = (v, clf)
joblib.dump(pipeline, "url_model.pkl")
print("Saved url_model.pkl")
