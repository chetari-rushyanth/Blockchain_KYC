import logging
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from config import Config

class DatabaseConnection:
    """MongoDB connection manager"""

    def __init__(self):
        self.client = None
        self.db = None
        self.logger = logging.getLogger(__name__)

    def connect(self):
        """Establish connection to MongoDB"""
        try:
            self.client = MongoClient(
                Config.MONGODB_URI,
                serverSelectionTimeoutMS=5000,  # 5 second timeout
                retryWrites=True
            )

            # Test connection
            self.client.admin.command('ismaster')
            self.db = self.client[Config.MONGODB_DB]

            self.logger.info(f"Successfully connected to MongoDB: {Config.MONGODB_DB}")
            return True

        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            self.logger.error(f"Failed to connect to MongoDB: {str(e)}")
            return False

    def disconnect(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            self.logger.info("MongoDB connection closed")

    def get_database(self):
        """Get database instance"""
        if self.db is None:
            if not self.connect():
                raise ConnectionError("Cannot establish database connection")
        return self.db

    def get_collection(self, collection_name):
        """Get specific collection"""
        db = self.get_database()
        return db[collection_name]

    def create_indexes(self):
        """Create necessary database indexes for performance"""
        try:
            db = self.get_database()

            # Users collection indexes
            users_collection = db.users
            users_collection.create_index("email", unique=True)
            users_collection.create_index("phone_number")
            users_collection.create_index("created_at")

            # KYC submissions collection indexes
            kyc_collection = db.kyc_submissions
            kyc_collection.create_index("user_id")
            kyc_collection.create_index("status")
            kyc_collection.create_index("submission_date")
            kyc_collection.create_index([("user_id", 1), ("status", 1)])

            # Blockchain transactions collection indexes
            blockchain_collection = db.blockchain_transactions
            blockchain_collection.create_index("transaction_hash", unique=True)
            blockchain_collection.create_index("user_id")
            blockchain_collection.create_index("block_number")

            # Face verification collection indexes
            face_verification_collection = db.face_verifications
            face_verification_collection.create_index("user_id")
            face_verification_collection.create_index("verification_date")
            face_verification_collection.create_index("status")

            self.logger.info("Database indexes created successfully")

        except Exception as e:
            self.logger.error(f"Error creating indexes: {str(e)}")
            raise

    def health_check(self):
        """Check database health"""
        try:
            db = self.get_database()
            result = db.command("ping")
            return result.get("ok") == 1
        except Exception as e:
            self.logger.error(f"Database health check failed: {str(e)}")
            return False

# Global database connection instance
db_connection = DatabaseConnection()

def get_db():
    """Get database connection"""
    return db_connection.get_database()

def get_collection(collection_name):
    """Get specific collection"""
    return db_connection.get_collection(collection_name)