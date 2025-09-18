import logging
from datetime import datetime
from typing import Dict, List, Optional
from bson import ObjectId
from database.db_connection import get_collection

class KYCRepository:
    """Repository for KYC-related database operations"""

    def __init__(self):
        self.users_collection = get_collection('users')
        self.kyc_collection = get_collection('kyc_submissions')
        self.face_verification_collection = get_collection('face_verifications')
        self.blockchain_collection = get_collection('blockchain_transactions')
        self.logger = logging.getLogger(__name__)

    # User Operations
    def create_user(self, user_data: Dict) -> str:
        """Create a new user"""
        try:
            user_data['created_at'] = datetime.utcnow()
            user_data['updated_at'] = datetime.utcnow()
            user_data['is_active'] = True

            result = self.users_collection.insert_one(user_data)
            self.logger.info(f"User created with ID: {result.inserted_id}")
            return str(result.inserted_id)

        except Exception as e:
            self.logger.error(f"Error creating user: {str(e)}")
            raise

    def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        """Get user by ID"""
        try:
            user = self.users_collection.find_one({"_id": ObjectId(user_id)})
            if user:
                user['_id'] = str(user['_id'])
            return user
        except Exception as e:
            self.logger.error(f"Error fetching user by ID {user_id}: {str(e)}")
            return None

    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email"""
        try:
            user = self.users_collection.find_one({"email": email})
            if user:
                user['_id'] = str(user['_id'])
            return user
        except Exception as e:
            self.logger.error(f"Error fetching user by email {email}: {str(e)}")
            return None

    def update_user(self, user_id: str, update_data: Dict) -> bool:
        """Update user information"""
        try:
            update_data['updated_at'] = datetime.utcnow()
            result = self.users_collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": update_data}
            )
            return result.modified_count > 0
        except Exception as e:
            self.logger.error(f"Error updating user {user_id}: {str(e)}")
            return False

    # KYC Submission Operations
    def create_kyc_submission(self, kyc_data: Dict) -> str:
        """Create a new KYC submission"""
        try:
            kyc_data['submission_date'] = datetime.utcnow()
            kyc_data['status'] = 'pending'
            kyc_data['verification_attempts'] = 0

            result = self.kyc_collection.insert_one(kyc_data)
            self.logger.info(f"KYC submission created with ID: {result.inserted_id}")
            return str(result.inserted_id)

        except Exception as e:
            self.logger.error(f"Error creating KYC submission: {str(e)}")
            raise

    def get_kyc_submission_by_id(self, kyc_id: str) -> Optional[Dict]:
        """Get KYC submission by ID"""
        try:
            kyc = self.kyc_collection.find_one({"_id": ObjectId(kyc_id)})
            if kyc:
                kyc['_id'] = str(kyc['_id'])
            return kyc
        except Exception as e:
            self.logger.error(f"Error fetching KYC submission {kyc_id}: {str(e)}")
            return None

    def get_kyc_submissions_by_user(self, user_id: str) -> List[Dict]:
        """Get all KYC submissions for a user"""
        try:
            kyc_submissions = list(self.kyc_collection.find({"user_id": user_id}))
            for kyc in kyc_submissions:
                kyc['_id'] = str(kyc['_id'])
            return kyc_submissions
        except Exception as e:
            self.logger.error(f"Error fetching KYC submissions for user {user_id}: {str(e)}")
            return []

    def update_kyc_status(self, kyc_id: str, status: str, admin_notes: str = None) -> bool:
        """Update KYC submission status"""
        try:
            update_data = {
                'status': status,
                'status_updated_at': datetime.utcnow()
            }
            if admin_notes:
                update_data['admin_notes'] = admin_notes

            result = self.kyc_collection.update_one(
                {"_id": ObjectId(kyc_id)},
                {"$set": update_data}
            )
            return result.modified_count > 0
        except Exception as e:
            self.logger.error(f"Error updating KYC status {kyc_id}: {str(e)}")
            return False

    def get_pending_kyc_submissions(self, limit: int = 50) -> List[Dict]:
        """Get pending KYC submissions for admin review"""
        try:
            submissions = list(self.kyc_collection.find(
                {"status": "pending"}
            ).sort("submission_date", 1).limit(limit))

            for submission in submissions:
                submission['_id'] = str(submission['_id'])
            return submissions
        except Exception as e:
            self.logger.error(f"Error fetching pending KYC submissions: {str(e)}")
            return []

    # Face Verification Operations
    def create_face_verification(self, verification_data: Dict) -> str:
        """Create a face verification record"""
        try:
            verification_data['verification_date'] = datetime.utcnow()

            result = self.face_verification_collection.insert_one(verification_data)
            self.logger.info(f"Face verification created with ID: {result.inserted_id}")
            return str(result.inserted_id)

        except Exception as e:
            self.logger.error(f"Error creating face verification: {str(e)}")
            raise

    def get_face_verifications_by_user(self, user_id: str) -> List[Dict]:
        """Get face verification history for a user"""
        try:
            verifications = list(self.face_verification_collection.find(
                {"user_id": user_id}
            ).sort("verification_date", -1))

            for verification in verifications:
                verification['_id'] = str(verification['_id'])
            return verifications
        except Exception as e:
            self.logger.error(f"Error fetching face verifications for user {user_id}: {str(e)}")
            return []

    # Blockchain Transaction Operations
    def create_blockchain_transaction(self, transaction_data: Dict) -> str:
        """Record a blockchain transaction"""
        try:
            transaction_data['recorded_at'] = datetime.utcnow()

            result = self.blockchain_collection.insert_one(transaction_data)
            self.logger.info(f"Blockchain transaction recorded with ID: {result.inserted_id}")
            return str(result.inserted_id)

        except Exception as e:
            self.logger.error(f"Error recording blockchain transaction: {str(e)}")
            raise

    def get_blockchain_transactions_by_user(self, user_id: str) -> List[Dict]:
        """Get blockchain transactions for a user"""
        try:
            transactions = list(self.blockchain_collection.find(
                {"user_id": user_id}
            ).sort("recorded_at", -1))

            for transaction in transactions:
                transaction['_id'] = str(transaction['_id'])
            return transactions
        except Exception as e:
            self.logger.error(f"Error fetching blockchain transactions for user {user_id}: {str(e)}")
            return []

    def get_transaction_by_hash(self, transaction_hash: str) -> Optional[Dict]:
        """Get blockchain transaction by hash"""
        try:
            transaction = self.blockchain_collection.find_one({"transaction_hash": transaction_hash})
            if transaction:
                transaction['_id'] = str(transaction['_id'])
            return transaction
        except Exception as e:
            self.logger.error(f"Error fetching transaction by hash {transaction_hash}: {str(e)}")
            return None

    # Analytics and Reporting
    def get_kyc_statistics(self) -> Dict:
        """Get KYC submission statistics"""
        try:
            total_submissions = self.kyc_collection.count_documents({})
            pending_submissions = self.kyc_collection.count_documents({"status": "pending"})
            approved_submissions = self.kyc_collection.count_documents({"status": "approved"})
            rejected_submissions = self.kyc_collection.count_documents({"status": "rejected"})

            return {
                "total_submissions": total_submissions,
                "pending_submissions": pending_submissions,
                "approved_submissions": approved_submissions,
                "rejected_submissions": rejected_submissions,
                "approval_rate": (approved_submissions / total_submissions * 100) if total_submissions > 0 else 0
            }
        except Exception as e:
            self.logger.error(f"Error fetching KYC statistics: {str(e)}")
            return {}

# Global repository instance
kyc_repo = KYCRepository()
