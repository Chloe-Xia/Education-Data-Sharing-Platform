from flask import current_app
# Organization Status Constants
PENDING_APPROVAL = "pending_eadmin_approval"
ACTIVE = "active"
REJECTED = "rejected"
NOT_SUBMITTED = "not_submitted"

def allowed_file_for_proof(filename: str) -> bool:
    allowed_extensions = current_app.config.get('ALLOWED_EXTENSIONS_DOCS', {'pdf'})
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def allowed_file_for_excel(filename: str) -> bool:
    allowed_extensions = current_app.config.get('ALLOWED_EXCEL_EXTENSIONS', {'xlsx', 'xls'})
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions