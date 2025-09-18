"""
KYC Routes - API endpoints for KYC operations
Handles KYC submission (with file upload), verification, and status management
"""

import os
import base64
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from services.kyc_service import kyc_service
from services.face_verification import face_verification_service
from utils.security_utils import verify_jwt_token
from utils.validators import validate_kyc_data

print("=== Loading kyc_routes.py ===")


kyc_bp = Blueprint('kyc', __name__, url_prefix='/api/v1/kyc')
logger = logging.getLogger(__name__)

def authenticate_user():
    """Authenticate user from JWT token"""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return None
        token = auth_header.split(' ')[1]
        payload = verify_jwt_token(token)
        if not payload:
            return None
        return {
            'user_id': payload.get('user_id'),
            'user_role': payload.get('user_role', 'user')
        }
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        return None

def require_auth(f):
    """Decorator to require authentication"""
    def decorated_function(*args, **kwargs):
        user = authenticate_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        request.current_user = user
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

def require_admin(f):
    """Decorator to require admin role"""
    def decorated_function(*args, **kwargs):
        user = authenticate_user()
        if not user or user.get('user_role') != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        request.current_user = user
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

def _allowed_file(filename):
    """Check if uploaded file has an allowed extension"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

@kyc_bp.route('/submit', methods=['POST'])
@require_auth
def submit_kyc():
    """Submit KYC application with file uploads"""
    try:
        user_id = request.current_user['user_id']
        # Collect form fields
        data = request.form.to_dict()

        # Handle file uploads
        files = request.files

        def _file_to_base64(file_key):
            f = files.get(file_key)
            if f and _allowed_file(f.filename):
                raw = f.read()
                ext = secure_filename(f.filename).rsplit('.', 1)[1].lower()
                mime = 'image/' + ext if ext in ('jpg', 'jpeg', 'png') else 'application/' + ext
                return f"data:{mime};base64," + base64.b64encode(raw).decode('utf-8')
            return None

        # Encode and attach each file to data
        for key in ('document_image', 'document_back_image', 'face_image'):
            encoded = _file_to_base64(key)
            if encoded:
                data[key] = encoded

        # Validate non-file fields
        validation = validate_kyc_data(data)
        if not validation['valid']:
            return jsonify({'error': f"Validation failed: {validation['errors']}"}), 400

        # Submit via service
        result = kyc_service.submit_kyc(user_id, data)
        status = 201 if result['success'] else 400
        return jsonify(result), status

    except Exception as e:
        logger.error(f"Error in submit_kyc: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@kyc_bp.route('/status', methods=['GET'])
@require_auth
def get_kyc_status():
    """Get KYC status for current user"""
    try:
        user_id = request.current_user['user_id']
        result = kyc_service.get_kyc_status(user_id)
        if result['success']:
            return jsonify(result), 200
        return jsonify({'error': result['message']}), 400
    except Exception as e:
        logger.error(f"Error in get_kyc_status: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@kyc_bp.route('/details/<kyc_id>', methods=['GET'])
@require_auth
def get_kyc_details(kyc_id):
    """Get detailed KYC submission information"""
    try:
        user_id = request.current_user['user_id']
        is_admin = request.current_user['user_role'] == 'admin'
        result = kyc_service.get_kyc_details(kyc_id, None if is_admin else user_id, admin=is_admin)
        if result['success']:
            return jsonify(result), 200
        return jsonify({'error': result['message']}), 400
    except Exception as e:
        logger.error(f"Error in get_kyc_details: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@kyc_bp.route('/update/<kyc_id>', methods=['PUT'])
@require_auth
def update_kyc(kyc_id):
    """Update an existing KYC submission"""
    try:
        user_id = request.current_user['user_id']
        update_data = request.get_json()
        if not update_data:
            return jsonify({'error': 'No data provided'}), 400
        result = kyc_service.update_kyc_submission(kyc_id, user_id, update_data)
        if result['success']:
            return jsonify(result), 200
        return jsonify({'error': result['message']}), 400
    except Exception as e:
        logger.error(f"Error in update_kyc: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@kyc_bp.route('/verify-face', methods=['POST'])
@require_auth
def verify_face():
    """Perform face verification against stored KYC image"""
    try:
        user_id = request.current_user['user_id']
        data = request.get_json()
        if not data or 'live_image' not in data:
            return jsonify({'error': 'Live image data required'}), 400
        result = face_verification_service.verify_face_with_stored_image(user_id, data['live_image'])
        status = 200 if result.get('success') else 400
        return jsonify(result), status
    except Exception as e:
        logger.error(f"Error in verify_face: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@kyc_bp.route('/validate-image', methods=['POST'])
@require_auth
def validate_image():
    """Validate image quality for face verification"""
    try:
        data = request.get_json()
        if not data or 'image_data' not in data:
            return jsonify({'error': 'Image data required'}), 400
        result = face_verification_service.validate_image_quality(data['image_data'])
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error in validate_image: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

# Admin Routes

@kyc_bp.route('/admin/pending', methods=['GET'])
@require_admin
def get_pending_submissions():
    """Get pending KYC submissions for admin review"""
    try:
        admin_id = request.current_user['user_id']
        limit = request.args.get('limit', 50, type=int)
        result = kyc_service.get_pending_submissions(admin_id, limit)
        if result['success']:
            return jsonify(result), 200
        return jsonify({'error': result['message']}), 400
    except Exception as e:
        logger.error(f"Error in get_pending_submissions: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@kyc_bp.route('/admin/verify/<kyc_id>', methods=['POST'])
@require_admin
def admin_verify_kyc(kyc_id):
    """Admin verification of KYC submission"""
    try:
        admin_id = request.current_user['user_id']
        data = request.get_json() or {}
        decision = data.get('decision')
        notes = data.get('notes', '')
        if decision not in ('approved', 'rejected'):
            return jsonify({'error': 'Decision must be "approved" or "rejected"'}), 400
        result = kyc_service.verify_kyc_submission(kyc_id, admin_id, decision, notes)
        status = 200 if result['success'] else 400
        return jsonify(result), status
    except Exception as e:
        logger.error(f"Error in admin_verify_kyc: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@kyc_bp.route('/admin/analytics', methods=['GET'])
@require_admin
def get_analytics():
    """Get KYC analytics and statistics"""
    try:
        result = kyc_service.get_kyc_analytics()
        status = 200 if result.get('success') else 400
        return jsonify(result), status
    except Exception as e:
        logger.error(f"Error in get_analytics: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@kyc_bp.route('/admin/user/<user_id>/kyc', methods=['GET'])
@require_admin
def get_user_kyc_submissions(user_id):
    """Get all KYC submissions for a specific user"""
    try:
        from database.kyc_repository import kyc_repo
        subs = kyc_repo.get_kyc_submissions_by_user(user_id)
        return jsonify({'success': True, 'user_id': user_id, 'submissions': subs, 'count': len(subs)}), 200
    except Exception as e:
        logger.error(f"Error in get_user_kyc_submissions: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@kyc_bp.route('/validate-data', methods=['POST'])
@require_auth
def validate_kyc_data_endpoint():
    """Validate KYC data before submission"""
    try:
        data = request.get_json() or {}
        result = validate_kyc_data(data, partial=True)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error in validate_kyc_data_endpoint: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@kyc_bp.route('/verification-history', methods=['GET'])
@require_auth
def get_verification_history():
    """Get face verification history for current user"""
    try:
        user_id = request.current_user['user_id']
        history = face_verification_service.get_verification_history(user_id)
        return jsonify({'success': True, 'user_id': user_id, 'verification_history': history, 'count': len(history)}), 200
    except Exception as e:
        logger.error(f"Error in get_verification_history: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

# Error Handlers

@kyc_bp.errorhandler(400)
def bad_request(error):
    return jsonify({'error': 'Bad request'}), 400

@kyc_bp.errorhandler(401)
def unauthorized(error):
    return jsonify({'error': 'Unauthorized'}), 401

@kyc_bp.errorhandler(403)
def forbidden(error):
    return jsonify({'error': 'Forbidden'}), 403

@kyc_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@kyc_bp.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

# Health Check

@kyc_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        return jsonify({
            'status': 'healthy',
            'service': 'kyc-service',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0'
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500
