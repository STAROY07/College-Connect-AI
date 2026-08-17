from flask import (
    Flask, render_template, request, jsonify,
    redirect, url_for, session, flash
)
import os
import json
import uuid
from datetime import datetime
from functools import wraps
from werkzeug.security import check_password_hash
from knowledge_engine import KnowledgeEngine

app = Flask(__name__)

# ─── Load admin config from secure server-side file ──────────────────────────
def load_admin_config():
    config_path = os.path.join(os.path.dirname(__file__), "admin_config.json")
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)

_admin_cfg = load_admin_config()
app.config['SECRET_KEY'] = _admin_cfg.get("session_secret_key", "fallback-secret-key")
ADMIN_USERNAME = _admin_cfg.get("admin_username", "admin")
ADMIN_PASSWORD_HASH = _admin_cfg.get("admin_password_hash", "")

# ─── Knowledge Engine ─────────────────────────────────────────────────────────
engine = KnowledgeEngine()

# ─── Admin Auth Decorator ─────────────────────────────────────────────────────
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("admin_logged_in"):
            flash("Please log in to access the Admin panel.", "warning")
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated_function

# ═══════════════════════════════════════════════════════════════════════════════
#  PUBLIC ROUTES  (No login required)
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/")
def home():
    college = engine.college_info.get("college", {})
    updates = engine.get_latest_updates(limit=4)
    faqs = engine.faqs.get("faqs", [])[:5]
    services_sample = engine.services.get("services", [])[:6]
    ug_count = len(engine.programmes.get("ug_programmes", []))
    pg_count = len(engine.programmes.get("pg_programmes", []))
    aicte_count = len(engine.programmes.get("aicte_programmes", []))
    return render_template(
        "index.html",
        college=college,
        updates=updates,
        faqs=faqs,
        ug_count=ug_count,
        pg_count=pg_count,
        aicte_count=aicte_count,
        services_sample=services_sample
    )

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json(force=True, silent=True) or {}
        user_message = data.get("message", "").strip()
        if not user_message:
            return jsonify({
                "reply": "Please type a question about Vande Mataram Degree College.",
                "source": "System",
                "quick_actions": ["Courses", "Admissions", "Scholarships", "Services"]
            })
        response = engine.answer_query(user_message)
        return jsonify(response)
    except Exception as e:
        return jsonify({
            "reply": "Unable to process your query right now. Please try again or visit the college office.",
            "source": "Error"
        }), 500

@app.route("/programmes")
def programmes():
    ug = engine.programmes.get("ug_programmes", [])
    pg = engine.programmes.get("pg_programmes", [])
    aicte = engine.programmes.get("aicte_programmes", [])
    return render_template("programmes.html", ug=ug, pg=pg, aicte=aicte)

@app.route("/courses")
def courses():
    progs = engine.course_structure.get("programmes", {})
    return render_template("courses.html", programmes=progs)

@app.route("/api/courses/<prog_id>")
def api_course_structure(prog_id):
    progs = engine.course_structure.get("programmes", {})
    if prog_id in progs:
        return jsonify({"success": True, "programme": progs[prog_id]})
    return jsonify({"success": False, "message": "Programme not found"}), 404

@app.route("/admissions")
def admissions():
    return render_template("admissions.html", admissions=engine.admissions)

@app.route("/services")
def services():
    serv_list = engine.services.get("services", [])
    return render_template("services.html", services=serv_list)

@app.route("/student-life")
def student_life():
    return render_template("student_life.html", student_life=engine.student_life)

@app.route("/scholarships-welfare")
def welfare():
    return render_template("welfare.html", welfare=engine.welfare)

@app.route("/rules")
def rules():
    return render_template("rules.html", rules=engine.rules)

@app.route("/kaushal-centre")
def kaushal():
    return render_template("kaushal.html", kaushal=engine.kaushal)

@app.route("/updates")
def updates():
    all_updates = engine.get_latest_updates()
    return render_template("updates.html", updates=all_updates)

@app.route("/api/search")
def api_search():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"results": []})
    results = engine.search_all(q)
    return jsonify({"results": results})

# ═══════════════════════════════════════════════════════════════════════════════
#  ADMIN AUTH ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    # If already logged in, redirect to dashboard
    if session.get("admin_logged_in"):
        return redirect(url_for("admin_dashboard"))

    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if username == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD_HASH, password):
            session["admin_logged_in"] = True
            session["admin_username"] = username
            session.permanent = False
            return redirect(url_for("admin_dashboard"))
        else:
            error = "Invalid username or password. Please try again."

    return render_template("admin_login.html", error=error)

@app.route("/admin/logout")
def admin_logout():
    session.clear()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for("admin_login"))

# ─── Legacy /admin route – redirect to login or dashboard ─────────────────────
@app.route("/admin")
def admin_redirect():
    if session.get("admin_logged_in"):
        return redirect(url_for("admin_dashboard"))
    return redirect(url_for("admin_login"))

# ═══════════════════════════════════════════════════════════════════════════════
#  ADMIN PROTECTED ROUTES  (Requires admin login)
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    engine.reload_all()
    stats = {
        "ug_programmes": len(engine.programmes.get("ug_programmes", [])),
        "pg_programmes": len(engine.programmes.get("pg_programmes", [])),
        "aicte_programmes": len(engine.programmes.get("aicte_programmes", [])),
        "total_services": len(engine.services.get("services", [])),
        "total_updates": len(engine.updates.get("updates", [])),
        "active_updates": len([u for u in engine.updates.get("updates", []) if u.get("status") == "Active"]),
        "total_faqs": len(engine.faqs.get("faqs", [])),
        "kaushal_courses": len(engine.kaushal.get("courses", [])),
    }
    recent_updates = engine.get_latest_updates(limit=5)
    all_updates = engine.updates.get("updates", [])
    all_faqs = engine.faqs.get("faqs", [])
    return render_template(
        "admin.html",
        stats=stats,
        recent_updates=recent_updates,
        all_updates=all_updates,
        all_faqs=all_faqs,
        admin_username=session.get("admin_username", "Admin")
    )

@app.route("/admin/api/data/<dataset>", methods=["GET", "POST"])
@admin_required
def admin_data_api(dataset):
    allowed_datasets = [
        "college_info", "college_data", "programmes", "course_structure",
        "admissions", "services", "rules", "welfare", "kaushal",
        "student_life", "updates", "faqs"
    ]
    if dataset not in allowed_datasets:
        return jsonify({"success": False, "message": "Invalid dataset"}), 400
        
    filename = f"{dataset}.json"
    
    if request.method == "GET":
        data = engine._load_json(filename, default={})
        return jsonify({"success": True, "data": data})
        
    if request.method == "POST":
        try:
            data = request.get_json(force=True)
            _save_json(filename, data)
            engine.reload_all()
            return jsonify({"success": True, "message": f"{dataset.replace('_', ' ').title()} updated successfully."})
        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 500

# ─── Helper ────────────────────────────────────────────────────────────────────
def _save_json(filename, data):
    filepath = os.path.join(engine.data_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ─── Error Handlers ────────────────────────────────────────────────────────────
@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({"reply": "Internal server error.", "source": "System"}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)