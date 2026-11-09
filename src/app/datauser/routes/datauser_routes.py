from flask import Blueprint, request, jsonify
from flask import current_app as app
from ..models.private_provider import PrivateDataProvider
from ..models.service_config import ServiceConfig
from ..models.course_info import CourseInfo
from ..services.NotificationService import NotificationService
from flask import render_template
from flask import g # Import g (was also 'request' earlier)
from app.main.User import User # Ensure User is correctly imported if needed elsewhere
from ...extensions import mongo
from bson import ObjectId
from datetime import datetime, timezone

datauser_bp = Blueprint("datauser", __name__, url_prefix="/api/datauser")

@datauser_bp.route("/dashboard", methods=["GET"])
def provider_dashboard():
    return render_template("datauser/provider_dashboard.html")

@datauser_bp.route("/private_consumer", methods=["GET"])
def private_consumer():
    return render_template("datauser/private_consumer.html")

@datauser_bp.route("/public_consumer", methods=["GET"])
def public_consumer():
    return render_template("datauser/public_consumer.html")

@datauser_bp.before_request
# FIXED: Renamed function and correctly set g.user, then return None
def set_g_user_for_datauser():
    user_email = request.headers.get("X-User-Email")
    print("📥 Email from header (before_request):", user_email)
    
    if not user_email:
        g.user = None
        return # Allow the request to proceed; view functions can handle missing user

    user_doc = mongo.db.users.find_one({"email": user_email})
    print("🔍 User found (before_request):", user_doc)
    
    if user_doc:
        g.user = PrivateDataProvider(user_doc)
    else:
        g.user = None
    
    return # IMPORTANT: Return None to allow Flask to proceed to the target view function

@datauser_bp.route("/course", methods=["POST"])
def add_course():
    user = g.user # FIXED: Get user from Flask's global context
    if not user or not PrivateDataProvider.is_eligible(user):
        return jsonify({"error": "AUTH_REQUIRED"}), 401

    try:
        # FIXED: 'user' is already a PrivateDataProvider instance, no need to re-instantiate
        course_data = request.json or {}
        result_code = user.add_course(course_data) # Use the method from PrivateDataProvider
        
        if result_code == "COURSE_ADDED":
            return jsonify({"message": "ADDED"})
        elif result_code == "COURSE_ALREADY_EXISTS":
            return jsonify({"message": "DUPLICATE"})
        else:
            return jsonify({"error": result_code}), 400 # Return specific error from the model
    except Exception as e:
        print("❌ ERROR in add_course:", e)
        return jsonify({"error": "SERVER_ERROR", "details": str(e)}), 500


@datauser_bp.route("/course/<course_id>", methods=["PUT"])
def update_course(course_id):
    user = g.user # FIXED: Get user from Flask's global context
    if not user or not PrivateDataProvider.is_eligible(user): # Added eligibility check
        return jsonify({"error": "AUTH_REQUIRED"}), 401

    data = request.json
    # FIXED: Use the method from PrivateDataProvider
    success = user.update_course(course_id, data) 

    if not success:
        return jsonify({"message": "NOT_FOUND"}), 404
    return jsonify({"message": "UPDATED"})


@datauser_bp.route("/course/<course_id>", methods=["DELETE"])
def delete_course(course_id):
    user = g.user # FIXED: Get user from Flask's global context
    if not user or not PrivateDataProvider.is_eligible(user): # Added eligibility check
        return jsonify({"error": "AUTH_REQUIRED"}), 401
    
    print("Trying to delete course:", course_id)
    print("Expected provider_email:", user.email)

    # FIXED: Use the method from PrivateDataProvider
    success = user.delete_course(course_id)
    return jsonify({"message": "DELETED" if success else "NOT_FOUND"})


@datauser_bp.route("/courses", methods=["GET"])
def list_my_courses():
    user = g.user # FIXED: Get user from Flask's global context

    if not user:
        return jsonify({"error": "AUTH_REQUIRED"}), 401

    # FIXED: Use the method from PrivateDataProvider
    results = user.list_courses()
    return jsonify(results)


@datauser_bp.route("/service", methods=["POST"])
def configure_service():
    user = g.user # FIXED: Get user from Flask's global context

    if not user or not PrivateDataProvider.is_eligible(user): # Added eligibility check
        return jsonify({"error": "AUTH_REQUIRED"}), 401

    data = request.json
    required = {"service_name", "base_url", "path", "method", "input", "output"}
    if not data or not required.issubset(data):
        return jsonify({"error": "MISSING_FIELDS"}), 400

    try:
        # FIXED: Use the method from PrivateDataProvider
        result_code = user.add_service_config(data) 
        if result_code == "SERVICE_CONFIGURED":
            return jsonify({"message": "SERVICE_CONFIGURED"})
        else:
            return jsonify({"error": result_code}), 400 # Return specific error from the model
    except Exception as e:
        print("❌ ERROR in configure_service:", e)
        return jsonify({"error": "SERVER_ERROR", "details": str(e)}), 500


@datauser_bp.route("/service/<service_name>", methods=["DELETE"])
def delete_service(service_name):
    user = g.user # FIXED: Get user from Flask's global context

    if not user or not PrivateDataProvider.is_eligible(user): # Added eligibility check
        return jsonify({"error": "AUTH_REQUIRED"}), 401

    # FIXED: Use the method from PrivateDataProvider
    success = user.delete_service_config(service_name)
    return jsonify({"message": "DELETED" if success else "NOT_FOUND"})


@datauser_bp.route("/services", methods=["GET"])
def list_my_services():
    user = g.user # FIXED: Get user from Flask's global context

    if not user:
        return jsonify({"error": "AUTH_REQUIRED"}), 401

    # FIXED: Use the method from PrivateDataProvider
    configs = user.list_service_configs()
    return jsonify(configs)

@datauser_bp.route("/service/test/<service_name>", methods=["POST"])
def test_service(service_name):
    user = g.user # FIXED: Get user from Flask's global context
    if not user or not PrivateDataProvider.is_eligible(user):
        return jsonify({"error": "NOT_ALLOWED"}), 403
    
    # FIXED: 'user' is already a PrivateDataProvider instance
    test_input = request.json or {}
    result = user.test_service_config(service_name, test_input) # Use the method from PrivateDataProvider
    return jsonify(result)

@datauser_bp.route("/api/datauser/notifications", methods=["GET"])
def get_notifications():
    user_email = request.headers.get("X-User-Email")
    if not user_email:
        return jsonify({"error": "AUTH_REQUIRED"}), 401

    user_doc = mongo.db.users.find_one({"email": user_email})
    if not user_doc:
        return jsonify({"error": "USER_NOT_FOUND"}), 404

    user = PrivateDataProvider(user_doc)

    notifications = mongo.db.NOTIFICATIONS.find({"user_email": user.email})
    result = []
    for n in notifications:
        # Ensure ObjectId is converted to string for JSON serialization
        notification_time = n.get("time")
        if isinstance(notification_time, datetime):
            notification_time = notification_time.isoformat()

        result.append({
            "title": n.get("title", "No Title"),
            "message": n.get("message", ""),
            "time": notification_time,
            "_id": str(n["_id"]) if "_id" in n and isinstance(n["_id"], ObjectId) else n.get("_id") # Convert ObjectId to string if applicable
        })

    return jsonify(result or [])

@datauser_bp.route("/api/datauser/notifications/mark-read/<notification_id>", methods=["POST"])
def mark_notification_read(notification_id):
    user_email = request.headers.get("X-User-Email")
    if not user_email:
        return jsonify({"error": "AUTH_REQUIRED"}), 401
    
    try:
        oid_id = ObjectId(notification_id)
        result = mongo.db.NOTIFICATIONS.update_one(
            {"_id": oid_id, "user_email": user_email}, 
            {"$set": {"read": True}}
        )
        if result.matched_count == 0:
            return jsonify({"message": "NOTIFICATION_NOT_FOUND"}), 404
        return jsonify({"message": "MARKED_AS_READ"})
    except Exception as e:
        print("❌ ERROR in mark_notification_read:", e)
        return jsonify({"error": "SERVER_ERROR", "details": str(e)}), 500