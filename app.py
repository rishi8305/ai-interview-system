import os
from datetime import datetime
from flask import Flask, render_template, redirect, url_for
from flask_login import LoginManager, current_user

from config import Config
from models import db, User
from routes import auth_bp, candidate_bp, interview_bp, admin_bp
from init_db import seed_database, auto_migrate_columns


def create_app(config_class=Config):
    """Application factory for AI Interview System."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize Database
    db.init_app(app)

    # Automatically ensure SQLite schema columns exist on startup
    # Initialize database and seed default data
    with app.app_context():
        try:
            db.create_all()
            auto_migrate_columns(app)
            seed_database(app)
            app.logger.info("Database initialization and seeding completed.")

        except Exception as e:
            app.logger.exception(f"Database initialization failed: {e}")
   # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please sign in to access this page."
    login_manager.login_message_category = "info"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(candidate_bp)
    app.register_blueprint(interview_bp)
    app.register_blueprint(admin_bp)

    # Landing Page Route
    @app.route("/")
    def index():
        if current_user.is_authenticated:
            if current_user.is_admin:
                return redirect(url_for("admin.dashboard"))
            return redirect(url_for("candidate.dashboard"))
        return render_template("index.html")

    # Global Template Context Processor
    @app.context_processor
    def inject_globals():
        return {
            "app_name": app.config.get("APP_NAME", "AI Interview System"),
            "current_year": datetime.utcnow().year,
            "ai_provider": app.config.get("AI_PROVIDER", "gemini"),
            "evaluation_mode": app.config.get("EVALUATION_MODE", "auto"),
        }

    # Error Handlers
    @app.errorhandler(403)
    def forbidden(error):
        return render_template("base.html", error_code=403, error_message="Access Denied: You do not have permission to view this resource."), 403

    @app.errorhandler(404)
    def not_found(error):
        return render_template("base.html", error_code=404, error_message="Page Not Found: The requested URL was not found on this server."), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template("base.html", error_code=500, error_message="Internal Server Error: An unexpected error occurred on the server."), 500

    return app


# Main application entry point
app = create_app()

if __name__ == "__main__":
    # Ensure database tables and initial seed data exist
    seed_database(app)
    # Run development server (use_reloader=False prevents Windows WinError 10038 socket error)
    app.run(host="127.0.0.1", port=5000, debug=True, use_reloader=False)
