"""
KYC Service - Main business logic for KYC operations
Handles KYC submission, verification, and status management
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from database.kyc_repository import kyc_repo
from services.face_verification import face_verification_service
from services.blockchain_service import blockchain_service
from utils.validators import validate_kyc_data
from utils.file_utils import save_uploaded_file, get_file_url
from utils.security_utils import hash_sensitive_data

class KYCService:
    """Service for KYC operations"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.kyc_repo = kyc_repo
        self.face_verification = face_verification_service
        self.blockchain_service = blockchain_service

    def submit_kyc(self, user_id: str, kyc_data: Dict) -> Dict:
        """Submit KYC application"""
        try:
            # Validate KYC data
            validation_result = validate_kyc_data(kyc_data)
            if not validation_result['valid']:
                return {
                    'success': False,
                    'message': f"Validation failed: {validation_result['errors']}"
                }

            # Check if user already has pending or approved KYC
            existing_kyc = self.kyc_repo.get_kyc_submissions_by_user(user_id)
            for kyc in existing_kyc:
                if kyc['status'] in ['pending', 'approved']:
                    return {
                        'success': False,
                        'message': f"User already has {kyc['status']} KYC submission"
                    }

            # Validate face image quality if provided
            if 'face_image' in kyc_data:
                image_validation = self.face_verification.validate_image_quality(kyc_data['face_image'])
                if not image_validation['valid']:
                    return {
                        'success': False,
                        'message': f"Face image validation failed: {image_validation['message']}"
                    }

            # Generate submission ID
            submission_id = str(uuid.uuid4())

            # Prepare KYC submission data
            submission_data = {
                'submission_id': submission_id,
                'user_id': user_id,
                'personal_info': {
                    'full_name': kyc_data.get('full_name'),
                    'date_of_birth': kyc_data.get('date_of_birth'),
                    'gender': kyc_data.get('gender'),
                    'nationality': kyc_data.get('nationality'),
                    'address': kyc_data.get('address'),
                    'phone_number': kyc_data.get('phone_number'),
                    'email': kyc_data.get('email')
                },
                'identity_documents': {
                    'document_type': kyc_data.get('document_type'),
                    'document_number': hash_sensitive_data(kyc_data.get('document_number', '')),
                    'document_image': kyc_data.get('document_image'),
                    'document_back_image': kyc_data.get('document_back_image')
                },
                'face_image': kyc_data.get('face_image'),
                'additional_documents': kyc_data.get('additional_documents', []),
                'status': 'pending',
                'submission_date': datetime.utcnow(),
                'verification_attempts': 0
            }

            # Save KYC submission to database
            kyc_id = self.kyc_repo.create_kyc_submission(submission_data)

            # Log submission
            self.logger.info(f"KYC submission created: {kyc_id} for user: {user_id}")

            return {
                'success': True,
                'message': 'KYC submission created successfully',
                'kyc_id': kyc_id,
                'submission_id': submission_id,
                'status': 'pending'
            }

        except Exception as e:
            self.logger.error(f"Error submitting KYC: {str(e)}")
            return {
                'success': False,
                'message': 'KYC submission failed due to system error'
            }

    def get_kyc_status(self, user_id: str) -> Dict:
        """Get KYC status for a user"""
        try:
            kyc_submissions = self.kyc_repo.get_kyc_submissions_by_user(user_id)

            if not kyc_submissions:
                return {
                    'success': True,
                    'status': 'not_submitted',
                    'message': 'No KYC submission found'
                }

            # Get the most recent submission
            latest_kyc = max(kyc_submissions, key=lambda x: x.get('submission_date', datetime.min))

            return {
                'success': True,
                'status': latest_kyc['status'],
                'kyc_id': latest_kyc['_id'],
                'submission_date': latest_kyc['submission_date'],
                'last_updated': latest_kyc.get('status_updated_at'),
                'admin_notes': latest_kyc.get('admin_notes'),
                'verification_attempts': latest_kyc.get('verification_attempts', 0)
            }

        except Exception as e:
            self.logger.error(f"Error getting KYC status: {str(e)}")
            return {
                'success': False,
                'message': 'Failed to retrieve KYC status'
            }

    def verify_kyc_submission(self, kyc_id: str, admin_id: str, decision: str, notes: str = None) -> Dict:
        """Admin verification of KYC submission"""
        try:
            if decision not in ['approved', 'rejected']:
                return {
                    'success': False,
                    'message': 'Invalid decision. Must be "approved" or "rejected"'
                }

            # Get KYC submission
            kyc_submission = self.kyc_repo.get_kyc_submission_by_id(kyc_id)
            if not kyc_submission:
                return {
                    'success': False,
                    'message': 'KYC submission not found'
                }

            if kyc_submission['status'] != 'pending':
                return {
                    'success': False,
                    'message': f"KYC submission is already {kyc_submission['status']}"
                }

            # Update KYC status
            admin_notes = f"Verified by admin {admin_id}. {notes or ''}"
            update_success = self.kyc_repo.update_kyc_status(kyc_id, decision, admin_notes)

            if not update_success:
                return {
                    'success': False,
                    'message': 'Failed to update KYC status'
                }

            # If approved, store on blockchain
            if decision == 'approved':
                try:
                    blockchain_result = self.blockchain_service.store_kyc_verification(
                        user_id=kyc_submission['user_id'],
                        kyc_id=kyc_id,
                        verification_status=True,
                        admin_id=admin_id
                    )

                    if blockchain_result['success']:
                        self.logger.info(f"KYC verification stored on blockchain: {blockchain_result['transaction_hash']}")
                    else:
                        self.logger.warning(f"Failed to store KYC on blockchain: {blockchain_result['message']}")

                except Exception as blockchain_error:
                    self.logger.error(f"Blockchain storage error: {str(blockchain_error)}")

            self.logger.info(f"KYC {kyc_id} {decision} by admin {admin_id}")

            return {
                'success': True,
                'message': f'KYC submission {decision} successfully',
                'status': decision,
                'admin_notes': admin_notes
            }

        except Exception as e:
            self.logger.error(f"Error verifying KYC submission: {str(e)}")
            return {
                'success': False,
                'message': 'KYC verification failed due to system error'
            }

    def update_kyc_submission(self, kyc_id: str, user_id: str, update_data: Dict) -> Dict:
        """Update existing KYC submission"""
        try:
            # Get existing KYC submission
            kyc_submission = self.kyc_repo.get_kyc_submission_by_id(kyc_id)
            if not kyc_submission:
                return {
                    'success': False,
                    'message': 'KYC submission not found'
                }

            # Verify ownership
            if kyc_submission['user_id'] != user_id:
                return {
                    'success': False,
                    'message': 'Access denied: KYC submission belongs to different user'
                }

            # Only allow updates for pending or rejected submissions
            if kyc_submission['status'] not in ['pending', 'rejected']:
                return {
                    'success': False,
                    'message': f"Cannot update {kyc_submission['status']} KYC submission"
                }

            # Validate update data
            validation_result = validate_kyc_data(update_data, partial=True)
            if not validation_result['valid']:
                return {
                    'success': False,
                    'message': f"Validation failed: {validation_result['errors']}"
                }

            # Validate face image if being updated
            if 'face_image' in update_data:
                image_validation = self.face_verification.validate_image_quality(update_data['face_image'])
                if not image_validation['valid']:
                    return {
                        'success': False,
                        'message': f"Face image validation failed: {image_validation['message']}"
                    }

            # Update submission data
            update_fields = {
                'status': 'pending',  # Reset to pending if was rejected
                'updated_at': datetime.utcnow()
            }

            # Update specific fields
            if 'personal_info' in update_data:
                update_fields['personal_info'] = {**kyc_submission.get('personal_info', {}), **update_data['personal_info']}

            if 'identity_documents' in update_data:
                update_fields['identity_documents'] = {**kyc_submission.get('identity_documents', {}), **update_data['identity_documents']}

            if 'face_image' in update_data:
                update_fields['face_image'] = update_data['face_image']

            if 'additional_documents' in update_data:
                update_fields['additional_documents'] = update_data['additional_documents']

            # Perform update
            collection = self.kyc_repo.kyc_collection
            result = collection.update_one(
                {'_id': kyc_submission['_id']},
                {'$set': update_fields}
            )

            if result.modified_count > 0:
                return {
                    'success': True,
                    'message': 'KYC submission updated successfully',
                    'status': 'pending'
                }
            else:
                return {
                    'success': False,
                    'message': 'No changes were made to KYC submission'
                }

        except Exception as e:
            self.logger.error(f"Error updating KYC submission: {str(e)}")
            return {
                'success': False,
                'message': 'KYC update failed due to system error'
            }

    def get_kyc_details(self, kyc_id: str, user_id: str = None, admin: bool = False) -> Dict:
        """Get detailed KYC submission information"""
        try:
            kyc_submission = self.kyc_repo.get_kyc_submission_by_id(kyc_id)
            if not kyc_submission:
                return {
                    'success': False,
                    'message': 'KYC submission not found'
                }

            # Check access permissions
            if not admin and user_id and kyc_submission['user_id'] != user_id:
                return {
                    'success': False,
                    'message': 'Access denied'
                }

            # Remove sensitive data for non-admin users
            if not admin:
                # Remove document numbers and other sensitive info
                if 'identity_documents' in kyc_submission:
                    kyc_submission['identity_documents'].pop('document_number', None)

                # Remove admin notes
                kyc_submission.pop('admin_notes', None)

            return {
                'success': True,
                'kyc_submission': kyc_submission
            }

        except Exception as e:
            self.logger.error(f"Error getting KYC details: {str(e)}")
            return {
                'success': False,
                'message': 'Failed to retrieve KYC details'
            }

    def get_pending_submissions(self, admin_id: str, limit: int = 50) -> Dict:
        """Get pending KYC submissions for admin review"""
        try:
            pending_submissions = self.kyc_repo.get_pending_kyc_submissions(limit)

            return {
                'success': True,
                'submissions': pending_submissions,
                'count': len(pending_submissions)
            }

        except Exception as e:
            self.logger.error(f"Error getting pending submissions: {str(e)}")
            return {
                'success': False,
                'message': 'Failed to retrieve pending submissions'
            }

    def get_kyc_analytics(self) -> Dict:
        """Get KYC analytics and statistics"""
        try:
            stats = self.kyc_repo.get_kyc_statistics()

            return {
                'success': True,
                'analytics': stats
            }

        except Exception as e:
            self.logger.error(f"Error getting KYC analytics: {str(e)}")
            return {
                'success': False,
                'message': 'Failed to retrieve KYC analytics'
            }

    def perform_face_verification(self, user_id: str, live_image: str) -> Dict:
        """Perform face verification against stored KYC image"""
        try:
            return self.face_verification.verify_face_with_stored_image(user_id, live_image)

        except Exception as e:
            self.logger.error(f"Error performing face verification: {str(e)}")
            return {
                'success': False,
                'message': 'Face verification failed due to system error'
            }

# Global KYC service instance
kyc_service = KYCService()
