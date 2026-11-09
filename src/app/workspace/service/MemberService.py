from datetime import datetime, timezone
import re # For email validation if used here
from bson import ObjectId
from app.extensions import mongo
from app.models.ActivityRecord import ActivityRecord
from ..models import Workspace, OConvener 
from app.main.User import User 
from datetime import datetime, timezone
import pandas as pd
from io import BytesIO

class MemberService:
    @classmethod
    def add_member(cls, oconvener: OConvener, member_email: str, member_data: dict[str, any]) -> tuple[bool, str]:
        users_collection = mongo.db.users
        existing_user_doc = users_collection.find_one({"email": member_email})

        if existing_user_doc:
            existing_org_id = existing_user_doc.get('organization_id')
            if existing_org_id == oconvener.organization_id:
                return False, f"User {member_email} is already in your organization."
            if existing_org_id is not None:
                return False, f"User {member_email} belongs to another organization."
            
            update_fields = {
                "organization_id": oconvener.organization_id,
                "organization_name": oconvener.organization_name, # Set correct org name
                "last_updated_at": datetime.now(timezone.utc)
            }
            # Ensure role and access_level are correctly handled if provided
            if 'user_role' in member_data:
                role_value = member_data['user_role']
                update_fields['user_role'] = role_value.value if isinstance(role_value, User.Roles) else role_value
            if 'access_level' in member_data: # Use access_level
                update_fields['access_level'] = member_data['access_level']
            if 'membership_fee' in member_data:
                 update_fields['membership_fee'] = member_data['membership_fee']
            if 'username' in member_data and member_data['username']:
                 update_fields['username'] = member_data['username']
            
            try:
                result = users_collection.update_one({"_id": existing_user_doc["_id"]}, {"$set": update_fields})
                if result.modified_count > 0:
                    ActivityRecord(userAccount=oconvener.email, activityName="Member Added (Existing User)", details=f"Org:{oconvener.organization_id}, Member:{member_email}").addRecord()
                    return True, f"Existing user {member_email} added to organization."
                return False, "Failed to associate existing user (no changes made)."
            except Exception as e:
                print(f"DB Error associating existing member: {e}")
                return False, "Server error while adding existing member."
        else:
            # For new user, ensure _id is ObjectId and user_id (string) is consistent with User model
            new_user_object_id = ObjectId()
            new_user_id_str = str(new_user_object_id)

            user_doc_to_insert = {
                "_id": new_user_object_id, 
                "user_id": new_user_id_str, # Store string ID as per User model
                "email": member_email,
                "username": member_data.get('username', member_email.split('@')[0]),
                "user_role": member_data.get('user_role', User.Roles.NORMAL).value,
                "access_level": member_data.get('access_level', [False, False, False]), 
                "membership_fee": member_data.get('membership_fee', 0.0),
                "organization_id": oconvener.organization_id,
                "organization_name": oconvener.organization_name, # Set correct org name
                "created_at": datetime.now(timezone.utc),
                "last_updated_at": datetime.now(timezone.utc),
                "email_verified": False 
            }
            try:
                users_collection.insert_one(user_doc_to_insert)
                ActivityRecord(userAccount=oconvener.email, activityName="Member Added (New User)", details=f"Org:{oconvener.organization_id}, Member:{member_email}, ID:{new_user_id_str}").addRecord()
                return True, f"New member {member_email} created and added to organization."
            except Exception as e:
                print(f"DB Error creating new member: {e}")
                return False, "Server error while creating new member."

    @classmethod
    def _calculate_membership_fee(cls, access_level: list[bool]) -> float:
        fee = 0.0
        if len(access_level) == 3:
            if access_level[0]: fee += 1000.00
            if access_level[1]: fee += 100.00
            if access_level[2]: fee += 0.00 
        return round(fee, 2)
    
    @classmethod
    def add_members_from_excel(cls, oconvener: OConvener, file_stream: BytesIO) -> tuple[bool, str, list[str], list[dict[str, str]]]:
        successful_adds_emails = []
        failed_adds_details = []
        processed_count = 0
        added_or_associated_count = 0

        try:
            df = pd.read_excel(file_stream, engine='openpyxl')
            df.columns = [str(col).strip().lower().replace('_', ' ') for col in df.columns] 
            email_col = 'email'
            username_col = 'username'
            public_col = 'access public'
            consume_col = 'access consume'
            provide_col = 'access provide'
            fee_col = 'membership fee'

            if email_col not in df.columns:
                return False, f"Missing required column in Excel: '{email_col}'.", [], []

            for index, row in df.iterrows():
                processed_count += 1
                current_email = "N/A at row " + str(index + 2) 

                try:
                    email_val = row.get(email_col)
                    if pd.isna(email_val) or not str(email_val).strip():
                        failed_adds_details.append({"email": current_email, "reason": "Email is missing."})
                        continue
                    email = str(email_val).strip().lower()
                    current_email = email 
                    if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email):
                        failed_adds_details.append({"email": email, "reason": "Invalid email format."})
                        continue

                    username = str(row.get(username_col, '')).strip()
                    def parse_bool_excel(value) -> bool:
                        if pd.isna(value): return False # Treat NaN as False
                        if isinstance(value, bool): return value
                        if isinstance(value, (int, float)): return bool(value)
                        if isinstance(value, str):
                            val_lower = value.strip().lower()
                            return val_lower in ['true', 'yes', '1', 't', 'y']
                        return False

                    # Default access levels to False if columns are missing or values are unparseable
                    access_public = parse_bool_excel(row.get(public_col, False))
                    access_consume = parse_bool_excel(row.get(consume_col, False))
                    access_provide = parse_bool_excel(row.get(provide_col, False))
                    access_level = [access_public, access_consume, access_provide]

                    membership_fee = None # Default to None, so it gets calculated
                    if fee_col in df.columns and pd.notna(row.get(fee_col)):
                        try:
                            fee_val = float(row[fee_col])
                            if fee_val < 0:
                                failed_adds_details.append({"email": email, "reason": "Membership fee cannot be negative."})
                                continue
                            membership_fee = round(fee_val, 2)
                        except ValueError:
                            failed_adds_details.append({"email": email, "reason": f"Invalid membership fee format: '{row[fee_col]}'."})
                            continue
                    
                    if membership_fee is None: # If not provided or invalid, calculate it
                        membership_fee = cls._calculate_membership_fee(access_level)

                    member_data = {
                        "username": username, 
                        "user_role": User.Roles.NORMAL, 
                        "access_level": access_level,
                        "membership_fee": membership_fee
                    }

                    success, message = cls.add_member(
                        oconvener=oconvener, 
                        member_email=email, 
                        member_data=member_data)

                    if success:
                        successful_adds_emails.append(email)
                        added_or_associated_count += 1
                    else:
                        failed_adds_details.append({"email": email, "reason": message})

                except Exception as e_row:
                    failed_adds_details.append({"email": current_email, "reason": f"Error processing row: {str(e_row)}"})
                    continue

        except Exception as e_file:
            return False, f"Critical error processing Excel file: {str(e_file)}", [], [{"email": "File Level Error", "reason": str(e_file)}]

        summary_message = f"Processed {processed_count} entries. {added_or_associated_count} members added/associated. {len(failed_adds_details)} failures."
        overall_success = processed_count > 0 
        return overall_success, summary_message, successful_adds_emails, failed_adds_details

    @classmethod
    def remove_member(cls, oconvener: OConvener, member_email_to_remove: str) -> tuple[bool, str]:
        """Removes a member's association."""
        if not oconvener.organization_id:
            return False, "O-Convener is not fully associated with an organization."
        if not member_email_to_remove:
            return False, "Member email for removal is required."

        users_collection = mongo.db.users
        target_email_lower = member_email_to_remove.strip()

        try:
            member_doc = users_collection.find_one({
                "email": target_email_lower,
                "organization_id": oconvener.organization_id
            })
            if not member_doc:
                return False, f"Member {target_email_lower} not found in your organization."

            result = users_collection.update_one(
                {"_id": member_doc["_id"]},
                {"$unset": {"organization_id": "", "organization_name": ""},
                 "$set": {"last_updated_at": datetime.now(timezone.utc)}}
            )
            if result.modified_count > 0:
                #ActivityRecord(userAccount=oconvener.email, activityName="Member Removed", details=f"Org:{oconvener.organization_id}, Member:{target_email_lower}").addRecord()
                return True, f"Member {target_email_lower} removed from organization."
            return False, "Failed to remove member (no changes made)."
        except Exception as e:
            print(f"DB Error removing member: {e}")
            return False, "Server error while removing member."

    @classmethod
    def edit_member(cls, oconvener: OConvener, member_id_to_edit: str, updates: dict[str, any]) -> tuple[bool, str]:
        """Edits details of a member."""
        if not oconvener.organization_id:
            return False, "O-Convener is not fully associated with an organization."
        if not member_id_to_edit or not updates:
            return False, "Member ID and update data are required."

        users_collection = mongo.db.users
        
        allowed_updates = {}
        if 'username' in updates and isinstance(updates['username'], str):
            allowed_updates['username'] = updates['username'].strip()
        
        if 'user_role' in updates:
            role_value = updates['user_role']
            if isinstance(role_value, User.Roles): 
                allowed_updates['user_role'] = role_value.value
            elif isinstance(role_value, (int, str)):
                try: # Try to convert to int if it's a numeric string for role value
                    role_int_value = int(role_value)
                    if any(role_int_value == r.value for r in User.Roles):
                        allowed_updates['user_role'] = role_int_value
                    else: # Try matching by name if not a valid int value
                        if any(str(role_value).upper() == r.name for r in User.Roles):
                           allowed_updates['user_role'] = User.Roles[str(role_value).upper()].value
                except ValueError: # Not an int, try matching by name
                    if any(str(role_value).upper() == r.name for r in User.Roles):
                        allowed_updates['user_role'] = User.Roles[str(role_value).upper()].value


        if 'access_level' in updates and isinstance(updates['access_level'], list) and len(updates['access_level']) == 3:
            allowed_updates['access_level'] = [bool(al) for al in updates['access_level']]

        if 'membership_fee' in updates: 
            try:
                allowed_updates['membership_fee'] = float(updates['membership_fee'])
            except ValueError:
                return False, "Invalid membership fee format."

        if not allowed_updates:
            return False, "No valid updates provided."
        
        allowed_updates["last_updated_at"] = datetime.now(timezone.utc)

        try:
            member_obj_id = ObjectId(member_id_to_edit)
            result = users_collection.update_one(
                {"_id": member_obj_id, "organization_id": oconvener.organization_id},
                {"$set": allowed_updates}
            )
            if result.matched_count == 0:
                return False, "Member not found in your organization or no changes made."
            if result.modified_count > 0:
                member_email_for_log = users_collection.find_one({"_id": member_obj_id}, {"email": 1}).get("email", member_id_to_edit)
                ActivityRecord(userAccount=oconvener.email, activityName="Member Edited", 
                               details=f"Org:{oconvener.organization_id}, MemberID:{member_id_to_edit}, Updates:{allowed_updates}").addRecord()
                return True, f"Member {member_email_for_log} updated successfully."
            return True, "No effective changes applied to the member." 
        except Exception as e:
            print(f"DB Error editing member: {e}")
            return False, "Server error while editing member."

    @classmethod
    def get_organization_members(cls, organization_id: str, exclude_user_id: str | None = None) -> list[User]:
        """Retrieves all members of a given organization."""
        if not organization_id:
            return []
        users_collection = mongo.db.users
        query: dict[str, any] = {"organization_id": organization_id} 
        if exclude_user_id:
            query["_id"] = {"$ne": exclude_user_id}
        
        member_docs = users_collection.find(query)
        return [User(doc) for doc in member_docs] 