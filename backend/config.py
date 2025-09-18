from datetime import timedelta
import os

class Config:
    # Flask Configuration
    SECRET_KEY = ('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DEBUG = os.getenv("FLASK_DEBUG", "False").lower() == "true"

    # MongoDB Configuration
    MONGODB_URI = ('mongodb://localhost:27017/') or 'mongodb://localhost:27017/kyc_system'
    MONGODB_DB = ('MONGODB_DB') or 'kyc_system'

    # Model Paths
    FACE_EMBEDDING_MODEL_PATH = ('models', 'face_embedding_model.h5')
    SIAMESE_MODEL_PATH = ('models', 'best_siamese.h5')
    SIAMESE_KERAS_MODEL_PATH = ('models', 'best_siamese.keras')

    # File Upload Configuration
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'doc', 'docx'}

    # Blockchain Configuration
    BLOCKCHAIN_NETWORK = ('BLOCKCHAIN_NETWORK') or 'development'
    ETHEREUM_NODE_URL = ('HTTP://127.0.0.1:7545')
    PRIVATE_KEY = ('0x2140a9cac737abf11197003b98c3307fb74b4a9b15ee6497ff70608174dd022e') # Replace with actual private key
    CONTRACT_ADDRESS = ('0xcc7AF4DF09518cE8E44A4bC24b1133E3824bdB5d') or '0x' + '0' * 40
    GAS_LIMIT = 3000000

    # Security Configuration
    JWT_SECRET_KEY = ('24c0e28ac11a316634523fc2caec2a340bd1c515a6d464b81210c59a3f12e33a') or 'jwt-secret-change-in-production'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8640)
    BCRYPT_LOG_ROUNDS = 12

    # Face Verification Thresholds
    FACE_VERIFICATION_THRESHOLD = 0.6
    IMAGE_PREPROCESSING_SIZE = (224, 224)

    # Logging Configuration
    LOG_LEVEL = ('LOG_LEVEL') or 'INFO'
    LOG_FILE = 'logs/kyc_system.log'

    # API Configuration
    API_VERSION = 'v1'
    RATE_LIMIT_PER_MINUTE = 60

    @staticmethod
    def init_app(app):
        """Initialize app with configuration"""
        pass

class DevelopmentConfig(Config):
    DEBUG = True
    MONGODB_URI = 'mongodb://localhost:27017/kyc_system_dev'

class ProductionConfig(Config):
    DEBUG = False
    SECRET_KEY = ('24c0e28ac11a316634523fc2caec2a340bd1c515a6d464b81210c59a3f12e33a')
    MONGODB_URI = ('mongodb://localhost:27017/')

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)

class TestingConfig(Config):
    TESTING = True
    MONGODB_URI = 'mongodb://localhost:27017/kyc_system_test'

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}