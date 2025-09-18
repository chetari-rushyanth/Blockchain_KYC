"""
AI-Enabled Blockchain-Based KYC Verification System for Banks
Main Flask Application Entry Point - COMPLETE FIXED VERSION
"""

import os
import logging
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS
app = Flask(__name__)
CORS(app)  

def create_app():
    """Application factory pattern"""
    
    app = Flask(__name__)
    
    # Basic configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
    app.config['DEBUG'] = True
    app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'pdf', 'doc', 'docx'}
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB
    
    # Configure logging
    setup_logging(app)
    
    # Initialize components (with error handling)
    initialize_database(app)
    initialize_models(app)
    
    # Register blueprints - THIS IS THE KEY PART
    register_blueprints(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Add request handlers
    setup_request_handlers(app)
    
    return app

def setup_logging(app):
    """Setup application logging"""
    try:
        # Create logs directory if it doesn't exist
        log_dir = 'logs'
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/kyc_system.log'),
                logging.StreamHandler()
            ]
        )
        
        app.logger.info("Logging configured successfully")
        
    except Exception as e:
        print(f"Error setting up logging: {str(e)}")

def initialize_database(app):
    """Initialize database connection"""
    try:
        from database.db_connection import db_connection
        if db_connection.connect():
            db_connection.create_indexes()
            app.logger.info("Database initialized successfully")
        else:
            app.logger.warning("Database connection failed - continuing without DB")
    except Exception as e:
        app.logger.warning(f"Database initialization error: {str(e)} - continuing without DB")

def initialize_models(app):
    """Initialize ML models"""
    try:
        from models.model_loader import model_loader
        # Don't block startup if models fail to load
        app.logger.info("Model loader initialized (models will load on demand)")
    except Exception as e:
        app.logger.warning(f"Model initialization error: {str(e)} - continuing without models")

def register_blueprints(app):
    """Register all Flask blueprints"""
    app.logger.info("Starting blueprint registration...")

    # 1) Auth routes first
    try:
        print("=== Loading auth_routes.py ===")
        from routes.auth_routes import auth_bp
        app.register_blueprint(auth_bp)
        app.logger.info("✅ Auth routes registered at /api/v1/auth")
    except Exception as e:
        app.logger.error(f"❌ Failed to register Auth routes: {e}")

    # 2) KYC routes next
    try:
        print("=== Loading kyc_routes.py ===")
        from routes.kyc_routes import kyc_bp
        app.register_blueprint(kyc_bp)
        app.logger.info("✅ KYC routes registered at /api/v1/kyc")
    except Exception as e:
        app.logger.error(f"❌ Failed to register KYC routes: {e}")

    # 3) Admin routes last
    try:
        print("=== Loading admin_routes.py ===")
        from routes.admin_routes import admin_bp
        app.register_blueprint(admin_bp)
        app.logger.info("✅ Admin routes registered at /api/v1/admin")
    except Exception as e:
        app.logger.error(f"❌ Failed to register Admin routes: {e}")

    app.logger.info("Blueprint registration completed")

def register_error_handlers(app):
    """Register global error handlers"""
    
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            'error': 'Bad Request',
            'message': 'The request was invalid or malformed',
            'status_code': 400
        }), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({
            'error': 'Unauthorized',
            'message': 'Authentication is required',
            'status_code': 401
        }), 401
    
    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({
            'error': 'Forbidden',
            'message': 'You do not have permission to access this resource',
            'status_code': 403
        }), 403
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'error': 'Not Found',
            'message': 'The requested resource was not found',
            'status_code': 404
        }), 404
    
    @app.errorhandler(413)
    def request_entity_too_large(error):
        return jsonify({
            'error': 'Request Entity Too Large',
            'message': 'The uploaded file is too large',
            'status_code': 413
        }), 413
    
    @app.errorhandler(500)
    def internal_server_error(error):
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred',
            'status_code': 500
        }), 500

def setup_request_handlers(app):
    """Setup before/after request handlers"""
    
    @app.before_request
    def before_request():
        """Log incoming requests"""
        if not request.path.startswith('/static'):
            app.logger.info(f"Request: {request.method} {request.path} from {request.remote_addr}")
    
    @app.after_request
    def after_request(response):
        """Log outgoing responses and add security headers"""
        if not request.path.startswith('/static'):
            app.logger.info(f"Response: {response.status_code} for {request.method} {request.path}")
        
        # Add security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        return response

# Create the Flask application
app = create_app()

# Root routes (defined after app creation)
@app.route('/')
def index():
    """Root endpoint - API information"""
    return jsonify({
        'message': 'AI-Enabled Blockchain-Based KYC Verification System',
        'version': '1.0.0',
        'status': 'operational',
        'timestamp': datetime.utcnow().isoformat(),
        'endpoints': {
            'auth': '/api/v1/auth',
            'kyc': '/api/v1/kyc',
            'admin': '/api/v1/admin',
            'health': '/health',
            'docs': '/api/docs',
            'routes': '/routes'
        },
        'features': [
            'KYC document submission and verification',
            'AI-powered face recognition',
            'Blockchain-based verification storage',
            'MongoDB data persistence',
            'RESTful API interface'
        ]
    })

@app.route('/health')
def health_check():
    """Comprehensive health check endpoint"""
    try:
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
            'components': {}
        }
        
        # Check database health
        try:
            from database.db_connection import db_connection
            db_healthy = db_connection.health_check()
            health_status['components']['database'] = {
                'status': 'healthy' if db_healthy else 'degraded',
                'details': 'MongoDB connection ' + ('active' if db_healthy else 'failed')
            }
        except Exception as e:
            health_status['components']['database'] = {
                'status': 'degraded',
                'details': f'Database error: {str(e)}'
            }
        
        # Check models health
        try:
            from models.model_loader import model_loader
            models_loaded = getattr(model_loader, 'models_loaded', False)
            health_status['components']['models'] = {
                'status': 'healthy' if models_loaded else 'degraded',
                'details': 'ML models ' + ('loaded' if models_loaded else 'not loaded')
            }
        except Exception as e:
            health_status['components']['models'] = {
                'status': 'degraded',
                'details': f'Models error: {str(e)}'
            }
        
        # Check blockchain health
        try:
            from services.blockchain_service import blockchain_service
            blockchain_status = blockchain_service.get_blockchain_status()
            blockchain_healthy = blockchain_status.get('connected', False)
            
            health_status['components']['blockchain'] = {
                'status': 'healthy' if blockchain_healthy else 'degraded',
                'details': 'Blockchain ' + ('connected' if blockchain_healthy else 'disconnected')
            }
        except Exception as e:
            health_status['components']['blockchain'] = {
                'status': 'degraded',
                'details': f'Blockchain error: {str(e)}'
            }
        
        # Determine overall health
        component_statuses = [comp['status'] for comp in health_status['components'].values()]
        if 'unhealthy' in component_statuses:
            health_status['status'] = 'unhealthy'
        elif 'degraded' in component_statuses:
            health_status['status'] = 'degraded'
        
        status_code = 200 if health_status['status'] in ['healthy', 'degraded'] else 503
        return jsonify(health_status), status_code
        
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e)
        }), 503

@app.route('/api/docs')
def api_documentation():
    """API documentation endpoint"""
    return jsonify({
        'title': 'KYC Verification System API',
        'version': '1.0.0',
        'description': 'AI-Enabled Blockchain-Based KYC Verification System for Banks',
        'base_url': request.host_url,
        'endpoints': {
            'Authentication': {
                'POST /api/v1/auth/register': 'Register new user',
                'GET /api/v1/auth/user/{user_id}': 'Get user profile',
                'PUT /api/v1/auth/user/{user_id}': 'Update user profile',
                'POST /api/v1/auth/verify-email': 'Verify email address',
                'POST /api/v1/auth/verify-phone': 'Verify phone number'
            },
            'KYC Operations': {
                'POST /api/v1/kyc/submit': 'Submit KYC application (with file uploads)',
                'GET /api/v1/kyc/status': 'Get KYC status',
                'GET /api/v1/kyc/details/{kyc_id}': 'Get KYC details',
                'PUT /api/v1/kyc/update/{kyc_id}': 'Update KYC submission',
                'POST /api/v1/kyc/verify-face': 'Verify face against stored image',
                'POST /api/v1/kyc/validate-image': 'Validate image quality',
                'GET /api/v1/kyc/verification-history': 'Get face verification history'
            },
            'Admin Operations': {
                'GET /api/v1/admin/dashboard': 'Get admin dashboard',
                'GET /api/v1/admin/kyc/submissions': 'Get KYC submissions',
                'POST /api/v1/admin/kyc/verify/{kyc_id}': 'Verify KYC submission',
                'GET /api/v1/admin/users': 'Get all users',
                'POST /api/v1/admin/users/{user_id}/activate': 'Activate user',
                'POST /api/v1/admin/users/{user_id}/deactivate': 'Deactivate user',
                'GET /api/v1/admin/analytics': 'Get system analytics'
            }
        },
        'authentication': {
            'type': 'Bearer Token',
            'header': 'Authorization: Bearer <token>',
            'description': 'Get token from /api/v1/auth/register or login endpoint'
        },
        'file_uploads': {
            'method': 'multipart/form-data',
            'supported_formats': ['jpg', 'jpeg', 'png', 'pdf'],
            'max_size': '16MB',
            'fields': ['document_image', 'document_back_image', 'face_image']
        }
    })

@app.route('/routes')
def list_routes():
    """Debug endpoint to list all registered routes"""
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({
            'endpoint': rule.endpoint,
            'methods': list(rule.methods),
            'path': str(rule)
        })
    return jsonify({
        'total_routes': len(routes),
        'routes': sorted(routes, key=lambda x: x['path'])
    })

if __name__ == '__main__':
    """Run the application"""
    try:
        # Get configuration from environment
        host = os.environ.get('FLASK_HOST', '0.0.0.0')
        port = int(os.environ.get('FLASK_PORT', 5000))
        debug = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
        
        print(f"🚀 Starting AI-KYC Verification System")
        print(f"🌐 Server: http://{host}:{port}")
        print(f"🔧 Debug mode: {debug}")
        print(f"🏥 Health check: http://{host}:{port}/health")
        print(f"📋 All routes: http://{host}:{port}/routes")
        print(f"📖 API docs: http://{host}:{port}/api/docs")
        print(f"🔑 Auth endpoint: http://{host}:{port}/api/v1/auth/register")
        print(f"📄 KYC endpoint: http://{host}:{port}/api/v1/kyc/submit")
        
        # Run the application
        app.run(
            host=host,
            port=port,
            debug=debug,
            threaded=True
        )
        
    except Exception as e:
        print(f"❌ Failed to start application: {str(e)}")
        logging.getLogger(__name__).error(f"Application startup error: {str(e)}")