
from bson import ObjectId
from datetime import datetime, timezone
from app.extensions import mongo
from app.main.User import User # Base User class
import logging

logger = logging.getLogger(__name__)

class NotificationService:
    @staticmethod
    def get_org_unread_notifications(organization_name: str):
        """
        Fetches unread notifications for a given organization_name.
        'is_read' is now considered an organization-level flag for the notification.
        """
        logger.debug(f"NotificationService: Querying unread notifications for organization_name: '{organization_name}'")
        # print(organization_name)
        notifications_collection = mongo.db.notifications
        try:
            # Query by organization_name and is_read: False
            unread_notifications = list(notifications_collection.find({
                "organization_name": organization_name,
                "is_read": False 
            }).sort("created_at", -1))

            print(unread_notifications)
            logger.info(f"Found {len(unread_notifications)} unread notifications for organization: {organization_name}")

            for notif in unread_notifications:
                notif["_id"] = str(notif["_id"])
                if isinstance(notif.get("user_id"), ObjectId): # If user_id (original target) was ObjectId
                    notif["user_id"] = str(notif["user_id"])
                if isinstance(notif.get("organization_id"), str): # If org_id was ObjectId
                    notif["organization_id"] = str(notif["organization_id"])
                if isinstance(notif.get("created_at"), datetime):
                    notif["created_at"] = notif["created_at"].isoformat()
            return unread_notifications
        except Exception as e:
            logger.error(f"Error fetching notifications for organization '{organization_name}': {e}", exc_info=True)
            return []

    @staticmethod
    def mark_org_notification_read(current_user: User, notification_id_str: str):
        """
        Marks a specific notification as read.
        The notification is identified by its _id.
        Verifies the notification belongs to the current_user's organization.
        'is_read' becomes an organization-level flag.
        """
        user_org_name = getattr(current_user, 'organization', None)
        if not user_org_name:
            logger.warning(f"mark_org_notification_read: User {current_user.email} has no organization_name.")
            return False, "User not associated with an organization."

        try:
            notif_obj_id_to_match = ObjectId(notification_id_str)
        except Exception:
            logger.warning(f"mark_org_notification_read: Invalid notification_id format: {notification_id_str}")
            return False, "Invalid notification ID format."

        logger.debug(f"NotificationService: Marking notification '{notif_obj_id_to_match}' as read for organization '{user_org_name}' by user '{current_user.email}'.")
        #print(notif_obj_id_to_match)
        notifications_collection = mongo.db.notifications
        try:
            # Find the notification and check if it belongs to the user's organization
            existing_notif = notifications_collection.find_one({"_id": notif_obj_id_to_match})

            if not existing_notif:
                logger.warning(f"Notification '{notif_obj_id_to_match}' not found in database.")
                return False, "Notification not found."
            
            # Verify the notification belongs to the current user's organization
            if existing_notif.get("organization_name") != user_org_name:
                logger.warning(f"Notification '{notif_obj_id_to_match}' (org: {existing_notif.get('organization_name')}) does not belong to user's org '{user_org_name}'.")
                return False, "Notification does not belong to this user's organization."

            if existing_notif.get("is_read"):
                logger.info(f"Notification '{notif_obj_id_to_match}' was already marked as read for organization '{user_org_name}'.")
                return True, "Notification already marked as read."

            # Update the notification to mark it as read (org-level)
            result = notifications_collection.update_one(
                {"_id": notif_obj_id_to_match, "organization_name": user_org_name}, # Ensure it's the correct org
                {"$set": {"is_read": True, "read_at": datetime.now(datetime.now(timezone.utc)), "marked_read_by_user_id": current_user.user_id}} # Optional: log who marked it
            )

            if result.modified_count > 0:
                logger.info(f"Notification '{notif_obj_id_to_match}' marked as read for organization '{user_org_name}'.")
                return True, "Notification marked as read."
            else:
                # This case should be rare if the above checks passed and it wasn't already read
                logger.warning(f"Failed to mark notification '{notif_obj_id_to_match}' as read for organization '{user_org_name}' (no changes made, matched_count: {result.matched_count}).")
                return False, "Failed to mark notification as read (no changes made)."
        except Exception as e:
            logger.error(f"Database error marking notification '{notification_id_str}' as read for organization '{user_org_name}': {e}", exc_info=True)
            return False, "Database error while marking notification."