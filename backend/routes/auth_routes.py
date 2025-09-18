
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify
from database.kyc_repository import kyc_repo
from utils.validators import validate_user_data
from utils.security_utils import create_jwt_token


logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__, url_prefix='/api/v1/auth')

print("=== Loading auth_routes.py ===")


@auth_bp.route('/register', methods=['POST'])
def register_user():
    """Register a new user"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Validate user data
        validation = validate_user_data(data)
        if not validation['valid']:
            return jsonify({'error': f"Validation failed: {validation['errors']}"}), 400

        # Check if user already exists
        existing = kyc_repo.get_user_by_email(data['email'])
        if existing:
            return jsonify({'error': 'User with this email already exists'}), 409

        # Prepare user record
        user_data = {
            'email': data['email'].lower().strip(),
            'full_name': data['full_name'].strip(),
            'phone_number': data['phone_number'].strip(),
            'registration_date': datetime.utcnow(),
            'is_active': True,
            'email_verified': False,
            'phone_verified': False,
            'kyc_status': 'not_submitted'
        }
        if 'date_of_birth' in data:
            user_data['date_of_birth'] = data['date_of_birth']
        if 'nationality' in data:
            user_data['nationality'] = data['nationality']

        # Insert into database
        user_id = kyc_repo.create_user(user_data)

        # Generate JWT token
        token = create_jwt_token(user_id, 'user')

        return jsonify({
            'message': 'User registered successfully',
            'user_id': user_id,
            'token': token,
            'user': {
                'user_id': user_id,
                'email': user_data['email'],
                'full_name': user_data['full_name'],
                'phone_number': user_data['phone_number'],
                'kyc_status': user_data['kyc_status']
            }
        }), 201

    except Exception as e:
        logger.exception("Error in register_user")
        return jsonify({'error': 'Registration failed due to system error'}), 500


@auth_bp.route('/test', methods=['GET'])
def test_route():
    """Health-check for auth blueprint"""
    return jsonify({
        'message': 'Auth blueprint is successfully registered!',
        'timestamp': datetime.utcnow().isoformat()
    }), 200


@auth_bp.route('/user/<user_id>', methods=['GET'])
def get_user_profile(user_id):
    """Get user profile information"""
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return jsonify({'error': 'Authentication required'}), 401

    user = kyc_repo.get_user_by_id(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    safe_user_data = {
        'user_id': user['_id'],
        'email': user['email'],
        'full_name': user['full_name'],
        'phone_number': user['phone_number'],
        'registration_date': user['registration_date'],
        'is_active': user['is_active'],
        'email_verified': user.get('email_verified', False),
        'phone_verified': user.get('phone_verified', False),
        'kyc_status': user.get('kyc_status', 'not_submitted'),
        'last_login': user.get('last_login'),
        'profile_completed': user.get('profile_completed', False)
    }
    return jsonify({'success': True, 'user': safe_user_data}), 200


@auth_bp.route('/user/<user_id>', methods=['PUT'])
def update_user_profile(user_id):
    """Update user profile information"""
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return jsonify({'error': 'Authentication required'}), 401

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    user = kyc_repo.get_user_by_id(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    updatable_fields = ['full_name', 'phone_number', 'date_of_birth', 'nationality']
    update_data = {f: data[f] for f in updatable_fields if f in data}

    if update_data:
        validation_result = validate_user_data(update_data)
        if not validation_result['valid']:
            return jsonify({'error': f"Validation failed: {validation_result['errors']}"}), 400

        success = kyc_repo.update_user(user_id, update_data)
        if success:
            return jsonify({
                'message': 'User profile updated successfully',
                'updated_fields': list(update_data.keys())
            }), 200
        else:
            return jsonify({'error': 'Failed to update user profile'}), 500

    return jsonify({'message': 'No valid fields to update'}), 200


@auth_bp.route('/revoke-api-key', methods=['POST'])
def revoke_api_key_route():
    """Revoke user's API key"""
    data = request.get_json()
    if not data or 'user_id' not in data:
        return jsonify({'error': 'User ID required'}), 400

    user_id = data['user_id']
    success = kyc_repo.update_user(user_id, {
        'api_key_hash': None,
        'api_key_revoked_at': datetime.utcnow()
    })
    if success:
        return jsonify({'message': 'API key revoked successfully'}), 200

    return jsonify({'error': 'Failed to revoke API key'}), 500


@auth_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'auth-service',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0'
    }), 200


# Error handlers for the blueprint
@auth_bp.errorhandler(400)
def bad_request(error):
    return jsonify({'error': 'Bad request'}), 400


@auth_bp.errorhandler(401)
def unauthorized(error):
    return jsonify({'error': 'Unauthorized'}), 401


@auth_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404


@auth_bp.errorhandler(409)
def conflict(error):
    return jsonify({'error': 'Conflict'}), 409


@auth_bp.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500
