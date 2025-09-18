"""
Admin Routes - Administrative endpoints for KYC system management
Handles admin-specific operations and system management
"""

import logging
from flask import Blueprint, request, jsonify
from datetime import datetime
from database.kyc_repository import kyc_repo
from services.kyc_service import kyc_service
from services.blockchain_service import blockchain_service
from utils.security_utils import verify_jwt_token
from utils.validators import validate_admin_action

# Create admin blueprint
admin_bp = Blueprint('admin', __name__, url_prefix='/api/v1/admin')
logger = logging.getLogger(__name__)

def authenticate_admin():
    """Authenticate admin user from JWT token"""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return None

        token = auth_header.split(' ')[1]
        payload = verify_jwt_token(token)

        if not payload or payload.get('user_role') != 'admin':
            return None

        return {
            'admin_id': payload.get('user_id'),
            'admin_role': payload.get('user_role')
        }
    except Exception as e:
        logger.error(f"Admin authentication error: {str(e)}")
        return None

def require_admin_auth(f):
    """Decorator to require admin authentication"""
    def decorated_function(*args, **kwargs):
        admin = authenticate_admin()
        if not admin:
            return jsonify({'error': 'Admin authentication required'}), 401

        request.current_admin = admin
        return f(*args, **kwargs)

    decorated_function.__name__ = f.__name__
    return decorated_function

# Dashboard and Analytics
@admin_bp.route('/dashboard', methods=['GET'])
@require_admin_auth
def get_dashboard():
    """Get admin dashboard data"""
    try:
        # Get KYC statistics
        kyc_stats = kyc_repo.get_kyc_statistics()

        # Get recent submissions (last 10)
        recent_submissions = kyc_repo.get_pending_kyc_submissions(10)

        # Get blockchain status
        blockchain_status = blockchain_service.get_blockchain_status()

        dashboard_data = {
            'kyc_statistics': kyc_stats,
            'recent_submissions': recent_submissions,
            'blockchain_status': blockchain_status,
            'timestamp': datetime.utcnow().isoformat()
        }

        return jsonify({
            'success': True,
            'dashboard': dashboard_data
        }), 200

    except Exception as e:
        logger.error(f"Error in get_dashboard: {str(e)}")
        return jsonify({'error': 'Failed to load dashboard'}), 500

@admin_bp.route('/analytics', methods=['GET'])
@require_admin_auth
def get_detailed_analytics():
    """Get detailed analytics and reports"""
    try:
        # Date range filters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        # Get comprehensive analytics
        analytics = kyc_service.get_kyc_analytics()

        # Additional analytics could include:
        # - Submission trends over time
        # - Processing time statistics
        # - Face verification success rates
        # - Geographic distribution
        # - Document type analysis

        return jsonify(analytics), 200 if analytics['success'] else 400

    except Exception as e:
        logger.error(f"Error in get_detailed_analytics: {str(e)}")
        return jsonify({'error': 'Failed to generate analytics'}), 500

# User Management
@admin_bp.route('/users', methods=['GET'])
@require_admin_auth
def get_all_users():
    """Get list of all users with pagination"""
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)
        search = request.args.get('search', '')

        # Basic implementation - in production, implement proper pagination
        users_collection = kyc_repo.users_collection

        # Build query
        query = {}
        if search:
            query = {
                '$or': [
                    {'email': {'$regex': search, '$options': 'i'}},
                    {'full_name': {'$regex': search, '$options': 'i'}}
                ]
            }

        # Get users
        skip = (page - 1) * limit
        users = list(users_collection.find(query).skip(skip).limit(limit))
        total_users = users_collection.count_documents(query)

        # Remove sensitive data
        safe_users = []
        for user in users:
            safe_user = {
                'user_id': str(user['_id']),
                'email': user['email'],
                'full_name': user['full_name'],
                'phone_number': user['phone_number'],
                'registration_date': user['registration_date'],
                'is_active': user['is_active'],
                'email_verified': user.get('email_verified', False),
                'phone_verified': user.get('phone_verified', False),
                'kyc_status': user.get('kyc_status', 'not_submitted')
            }
            safe_users.append(safe_user)

        return jsonify({
            'success': True,
            'users': safe_users,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total_users,
                'pages': (total_users + limit - 1) // limit
            }
        }), 200

    except Exception as e:
        logger.error(f"Error in get_all_users: {str(e)}")
        return jsonify({'error': 'Failed to retrieve users'}), 500

@admin_bp.route('/users/<user_id>/deactivate', methods=['POST'])
@require_admin_auth
def deactivate_user(user_id):
    """Deactivate a user account"""
    try:
        admin_id = request.current_admin['admin_id']
        data = request.get_json()
        reason = data.get('reason', '') if data else ''

        # Validate admin action
        action_data = {
            'admin_id': admin_id,
            'action_type': 'deactivate'
        }

        validation_result = validate_admin_action(action_data)
        if not validation_result['valid']:
            return jsonify({'error': f"Validation failed: {validation_result['errors']}"}), 400

        # Deactivate user
        update_data = {
            'is_active': False,
            'deactivated_at': datetime.utcnow(),
            'deactivated_by': admin_id,
            'deactivation_reason': reason
        }

        success = kyc_repo.update_user(user_id, update_data)

        if success:
            logger.info(f"User {user_id} deactivated by admin {admin_id}")
            return jsonify({
                'message': 'User deactivated successfully',
                'user_id': user_id
            }), 200
        else:
            return jsonify({'error': 'Failed to deactivate user'}), 500

    except Exception as e:
        logger.error(f"Error in deactivate_user: {str(e)}")
        return jsonify({'error': 'Failed to deactivate user'}), 500

@admin_bp.route('/users/<user_id>/activate', methods=['POST'])
@require_admin_auth
def activate_user(user_id):
    """Reactivate a user account"""
    try:
        admin_id = request.current_admin['admin_id']

        # Activate user
        update_data = {
            'is_active': True,
            'reactivated_at': datetime.utcnow(),
            'reactivated_by': admin_id
        }

        success = kyc_repo.update_user(user_id, update_data)

        if success:
            logger.info(f"User {user_id} reactivated by admin {admin_id}")
            return jsonify({
                'message': 'User activated successfully',
                'user_id': user_id
            }), 200
        else:
            return jsonify({'error': 'Failed to activate user'}), 500

    except Exception as e:
        logger.error(f"Error in activate_user: {str(e)}")
        return jsonify({'error': 'Failed to activate user'}), 500

# KYC Management
@admin_bp.route('/kyc/submissions', methods=['GET'])
@require_admin_auth
def get_kyc_submissions():
    """Get KYC submissions with filtering and pagination"""
    try:
        # Query parameters
        status = request.args.get('status', 'all')
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)
        sort_by = request.args.get('sort_by', 'submission_date')
        sort_order = request.args.get('sort_order', 'desc')

        # Build query
        query = {}
        if status != 'all':
            query['status'] = status

        # Get submissions
        kyc_collection = kyc_repo.kyc_collection

        # Sort direction
        sort_direction = -1 if sort_order == 'desc' else 1

        skip = (page - 1) * limit
        submissions = list(kyc_collection.find(query)
                          .sort(sort_by, sort_direction)
                          .skip(skip)
                          .limit(limit))

        total_submissions = kyc_collection.count_documents(query)

        # Convert ObjectId to string
        for submission in submissions:
            submission['_id'] = str(submission['_id'])

        return jsonify({
            'success': True,
            'submissions': submissions,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total_submissions,
                'pages': (total_submissions + limit - 1) // limit
            },
            'filters': {
                'status': status,
                'sort_by': sort_by,
                'sort_order': sort_order
            }
        }), 200

    except Exception as e:
        logger.error(f"Error in get_kyc_submissions: {str(e)}")
        return jsonify({'error': 'Failed to retrieve KYC submissions'}), 500

@admin_bp.route('/kyc/bulk-action', methods=['POST'])
@require_admin_auth
def bulk_kyc_action():
    """Perform bulk action on multiple KYC submissions"""
    try:
        admin_id = request.current_admin['admin_id']
        data = request.get_json()

        if not data or 'kyc_ids' not in data or 'action' not in data:
            return jsonify({'error': 'KYC IDs and action required'}), 400

        kyc_ids = data['kyc_ids']
        action = data['action']
        notes = data.get('notes', '')

        if action not in ['approve', 'reject']:
            return jsonify({'error': 'Invalid action. Must be approve or reject'}), 400

        successful_actions = []
        failed_actions = []

        for kyc_id in kyc_ids:
            try:
                decision = 'approved' if action == 'approve' else 'rejected'
                result = kyc_service.verify_kyc_submission(kyc_id, admin_id, decision, notes)

                if result['success']:
                    successful_actions.append(kyc_id)
                else:
                    failed_actions.append({'kyc_id': kyc_id, 'error': result['message']})

            except Exception as e:
                failed_actions.append({'kyc_id': kyc_id, 'error': str(e)})

        return jsonify({
            'message': f'Bulk {action} completed',
            'successful_actions': successful_actions,
            'failed_actions': failed_actions,
            'success_count': len(successful_actions),
            'failure_count': len(failed_actions)
        }), 200

    except Exception as e:
        logger.error(f"Error in bulk_kyc_action: {str(e)}")
        return jsonify({'error': 'Bulk action failed'}), 500

# Blockchain Management
@admin_bp.route('/blockchain/status', methods=['GET'])
@require_admin_auth
def get_blockchain_status():
    """Get blockchain connection and network status"""
    try:
        status = blockchain_service.get_blockchain_status()
        return jsonify(status), 200

    except Exception as e:
        logger.error(f"Error in get_blockchain_status: {str(e)}")
        return jsonify({'error': 'Failed to get blockchain status'}), 500

@admin_bp.route('/blockchain/transactions', methods=['GET'])
@require_admin_auth
def get_blockchain_transactions():
    """Get blockchain transactions with pagination"""
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)

        # Get transactions from database
        blockchain_collection = kyc_repo.blockchain_collection

        skip = (page - 1) * limit
        transactions = list(blockchain_collection.find()
                           .sort('recorded_at', -1)
                           .skip(skip)
                           .limit(limit))

        total_transactions = blockchain_collection.count_documents({})

        # Convert ObjectId to string
        for transaction in transactions:
            transaction['_id'] = str(transaction['_id'])

        return jsonify({
            'success': True,
            'transactions': transactions,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total_transactions,
                'pages': (total_transactions + limit - 1) // limit
            }
        }), 200

    except Exception as e:
        logger.error(f"Error in get_blockchain_transactions: {str(e)}")
        return jsonify({'error': 'Failed to retrieve blockchain transactions'}), 500

# System Management
@admin_bp.route('/system/health', methods=['GET'])
@require_admin_auth
def get_system_health():
    """Get comprehensive system health status"""
    try:
        # Database health
        from database.db_connection import db_connection
        db_health = db_connection.health_check()

        # Blockchain health
        blockchain_health = blockchain_service.get_blockchain_status()

        # Model health (check if models are loaded)
        from models.model_loader import model_loader
        models_health = {
            'models_loaded': model_loader.models_loaded,
            'face_embedding_model': model_loader.face_embedding_model is not None,
            'siamese_model': model_loader.siamese_model is not None
        }

        # Storage health
        from utils.file_utils import file_utils
        storage_health = file_utils.get_storage_usage()

        health_status = {
            'database': {'healthy': db_health, 'status': 'connected' if db_health else 'disconnected'},
            'blockchain': blockchain_health,
            'models': models_health,
            'storage': storage_health,
            'timestamp': datetime.utcnow().isoformat()
        }

        return jsonify({
            'success': True,
            'health': health_status
        }), 200

    except Exception as e:
        logger.error(f"Error in get_system_health: {str(e)}")
        return jsonify({'error': 'Failed to get system health'}), 500

@admin_bp.route('/system/maintenance/cleanup', methods=['POST'])
@require_admin_auth
def cleanup_old_files():
    """Clean up old files and temporary data"""
    try:
        admin_id = request.current_admin['admin_id']
        data = request.get_json()
        days_old = data.get('days_old', 30) if data else 30

        # Clean up old files
        from utils.file_utils import file_utils
        cleanup_result = file_utils.cleanup_old_files(days_old)

        logger.info(f"File cleanup initiated by admin {admin_id}: {cleanup_result}")

        return jsonify({
            'message': 'Cleanup completed successfully',
            'cleanup_result': cleanup_result
        }), 200

    except Exception as e:
        logger.error(f"Error in cleanup_old_files: {str(e)}")
        return jsonify({'error': 'Cleanup failed'}), 500

# Error handlers for the blueprint
@admin_bp.errorhandler(400)
def bad_request(error):
    return jsonify({'error': 'Bad request'}), 400

@admin_bp.errorhandler(401)
def unauthorized(error):
    return jsonify({'error': 'Admin authentication required'}), 401

@admin_bp.errorhandler(403)
def forbidden(error):
    return jsonify({'error': 'Forbidden'}), 403

@admin_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@admin_bp.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

# Health check endpoint
@admin_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for admin service"""
    try:
        return jsonify({
            'status': 'healthy',
            'service': 'admin-service',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0'
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500
