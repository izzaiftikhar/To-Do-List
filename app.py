import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, send_from_directory
from flask_sqlalchemy import SQLAlchemy

load_dotenv()

app = Flask(__name__, static_folder=None)

# Database connection (PostgreSQL)
# Vercel + Neon provide several variable names, so try a few
db_error = None
db_var_used = None
database_url = None
for name in ("DATABASE_URL", "POSTGRES_URL", "DATABASE_URL_UNPOOLED"):
    if os.getenv(name):
        database_url = os.getenv(name)
        db_var_used = name
        break

if not database_url:
    db_error = "No database URL found (DATABASE_URL is not set)."
    database_url = "sqlite:///placeholder.db"  # only so the app can start
else:
    # Providers give "postgres://" or "postgresql://"; tell SQLAlchemy to use
    # the psycopg (v3) driver that is listed in requirements.txt
    for prefix in ("postgres://", "postgresql://"):
        if database_url.startswith(prefix):
            database_url = "postgresql+psycopg://" + database_url[len(prefix):]
            break

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True, "pool_recycle": 300}

db = SQLAlchemy(app)


# Task model
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    completed = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "completed": self.completed,
        }


# Create tables if they don't exist yet
if not db_error:
    try:
        with app.app_context():
            db.create_all()
    except Exception as e:
        db_error = f"{type(e).__name__}: {e}"


# Page
@app.route("/")
def home():
    return render_template("index.html")


# Temporary debugging page: shows whether the database connected
@app.route("/api/health")
def health():
    if db_error:
        return jsonify({"database": "error", "variable_used": db_var_used, "error": db_error}), 500
    return jsonify({"database": "ok", "variable_used": db_var_used})


# Serves public/ files when running locally (Vercel serves them itself)
@app.route("/<path:filename>")
def public_files(filename):
    return send_from_directory("public", filename)


# View all tasks
@app.route("/api/tasks", methods=["GET"])
def view_tasks():
    tasks = Task.query.order_by(Task.created_at.asc()).all()
    return jsonify([task.to_dict() for task in tasks])


# Add a new task
@app.route("/api/tasks", methods=["POST"])
def add_task():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()

    if not title:
        return jsonify({"error": "Task title cannot be empty."}), 400
    if len(title) > 200:
        return jsonify({"error": "Task title must be 200 characters or less."}), 400

    task = Task(title=title)
    db.session.add(task)
    db.session.commit()
    return jsonify(task.to_dict()), 201


# Mark a task as done / not done
@app.route("/api/tasks/<int:task_id>", methods=["PATCH"])
def toggle_task(task_id):
    task = db.get_or_404(Task, task_id)
    task.completed = not task.completed
    db.session.commit()
    return jsonify(task.to_dict())


# Delete a task
@app.route("/api/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    task = db.get_or_404(Task, task_id)
    db.session.delete(task)
    db.session.commit()
    return jsonify({"message": "Task deleted successfully!"})


if __name__ == "__main__":
    app.run(debug=True)
