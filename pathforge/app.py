import csv
from pathlib import Path
from flask_cors import CORS
from flask import Flask, jsonify, render_template

import config
from pathforge.db.db import init_db
from pathforge.db.profile_manager import iso_now
from pathforge.routes.auth import auth_bp
from pathforge.routes.problems import problems_bp
from pathforge.routes.profile import profile_bp
from pathforge.routes.submissions import submissions_bp


def create_app(test_config=None):
    """Create and configure the PathForge Flask application."""
    app = Flask(__name__)
    CORS(
        app,
        supports_credentials=True,
        origins=[
            "http://localhost:3000"
        ]
    )
    app.config.update(
        SECRET_KEY=config.SECRET_KEY,
        JWT_SECRET=config.JWT_SECRET,
        DATABASE_PATH=config.DATABASE_PATH,
    )
    if test_config:
        app.config.update(test_config)

    connection = init_db(app.config.get("DATABASE_PATH"))
    _seed_problem_bank(connection)

    app.register_blueprint(auth_bp)
    app.register_blueprint(problems_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(submissions_bp)

    @app.route("/")
    def index():
        """Render the landing page."""
        return render_template("index.html")

    @app.route("/practice")
    def practice():
        """Render the practice interface."""
        return render_template("practice.html")

    @app.route("/dashboard")
    def dashboard():
        """Render the learner dashboard."""
        return render_template("dashboard.html")

    @app.errorhandler(404)
    def not_found(_error):
        """Return consistent JSON for API 404s and the landing page for normal 404s."""
        return jsonify({"success": False, "error": "Not found"}), 404

    return app


def _seed_problem_bank(connection):
    """Load the curated CSV problem bank into an empty database."""
    existing = connection.execute("SELECT COUNT(*) AS count FROM problems").fetchone()["count"]
    if existing:
        return
    csv_path = Path(__file__).resolve().parent / "data" / "pathforge_problems_fixed.csv"
    if not csv_path.exists():
        return
    now = iso_now()
    with open(csv_path, newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        rows = [
            (
                int(row["ID"]),
                row["Title"],
                row["Difficulty"],
                row["Topics"],
                row["pattern"],
                row["Example Test Cases"],
                row["Link"],
                float(row["Acceptance Rate (%)"]) if row["Acceptance Rate (%)"] else None,
                1 if row["Premium Only"].upper() == "TRUE" else 0,
                row["Category"],
                int(row["Likes"]) if row["Likes"] else None,
                int(row["Dislikes"]) if row["Dislikes"] else None,
                row["Similar Questions"],
                now,
            )
            for row in reader
        ]
    connection.executemany(
        """
        INSERT OR IGNORE INTO problems (
            id, title, difficulty, topics, pattern, test_cases, link,
            acceptance_rate, premium_only, category, likes, dislikes,
            similar_questions, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    connection.commit()


if __name__ == "__main__":
    create_app().run(debug=True)
