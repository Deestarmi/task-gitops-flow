from flask import Flask
import os

app = Flask(__name__)

@app.route("/")
def home():
    return f"Hello from task-gitops-flow! ENV={os.getenv('APP_ENV', 'local')}"

@app.route("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)