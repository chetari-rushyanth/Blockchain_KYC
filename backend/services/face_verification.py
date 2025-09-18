"""
Face Verification Service
Handles face verification logic using loaded models
"""

import logging
import numpy as np
import cv2
import base64
from io import BytesIO
from PIL import Image
from typing import Dict, Tuple, Optional
from models.model_loader import model_loader
from database.kyc_repository import kyc_repo
from config import Config

class FaceVerificationService:
    """Service for face verification operations"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.model_loader = model_loader
        self.kyc_repo = kyc_repo
        self.verification_threshold = Config.FACE_VERIFICATION_THRESHOLD

    def _decode_base64_image(self, base64_string: str) -> Optional[np.ndarray]:
        """Decode base64 image string to numpy array"""
        try:
            # Remove data URL prefix if present
            if 'data:image' in base64_string:
                base64_string = base64_string.split(',')[1]

            # Decode base64
            image_data = base64.b64decode(base64_string)

            # Convert to PIL Image
            image_pil = Image.open(BytesIO(image_data))

            # Convert to RGB if needed
            if image_pil.mode != 'RGB':
                image_pil = image_pil.convert('RGB')

            # Convert to numpy array
            image_array = np.array(image_pil)

            return image_array

        except Exception as e:
            self.logger.error(f"Error decoding base64 image: {str(e)}")
            return None

    def _detect_face(self, image_array: np.ndarray) -> Optional[np.ndarray]:
        """Detect and extract face from image"""
        try:
            # Convert to grayscale for face detection
            gray = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)

            # Load face cascade
            face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )

            # Detect faces
            faces = face_cascade.detectMultiScale(
                gray, 
                scaleFactor=1.1, 
                minNeighbors=5, 
                minSize=(30, 30)
            )

            if len(faces) == 0:
                self.logger.warning("No face detected in image")
                return None

            if len(faces) > 1:
                self.logger.warning(f"Multiple faces detected ({len(faces)}), using largest")

            # Get the largest face
            largest_face = max(faces, key=lambda x: x[2] * x[3])
            x, y, w, h = largest_face

            # Extract face region
            face_region = image_array[y:y+h, x:x+w]

            return face_region

        except Exception as e:
            self.logger.error(f"Error detecting face: {str(e)}")
            return None

    def _preprocess_face(self, face_array: np.ndarray) -> Optional[np.ndarray]:
        """Preprocess face image for model input"""
        try:
            # Resize to model input size
            target_size = Config.IMAGE_PREPROCESSING_SIZE
            face_resized = cv2.resize(face_array, target_size)

            # Normalize pixel values
            face_normalized = face_resized.astype(np.float32) / 255.0

            return face_normalized

        except Exception as e:
            self.logger.error(f"Error preprocessing face: {str(e)}")
            return None

    def verify_face_with_stored_image(self, user_id: str, live_image: str) -> Dict:
        """Verify live face image against stored KYC image"""
        try:
            # Get user's KYC submission
            kyc_submissions = self.kyc_repo.get_kyc_submissions_by_user(user_id)

            if not kyc_submissions:
                return {
                    'success': False,
                    'message': 'No KYC submission found for user',
                    'similarity_score': 0.0
                }

            # Get the most recent approved submission
            approved_kyc = None
            for kyc in kyc_submissions:
                if kyc['status'] == 'approved':
                    approved_kyc = kyc
                    break

            if not approved_kyc or 'face_image' not in approved_kyc:
                return {
                    'success': False,
                    'message': 'No approved KYC submission with face image found',
                    'similarity_score': 0.0
                }

            # Decode images
            live_image_array = self._decode_base64_image(live_image)
            stored_image_array = self._decode_base64_image(approved_kyc['face_image'])

            if live_image_array is None or stored_image_array is None:
                return {
                    'success': False,
                    'message': 'Failed to decode images',
                    'similarity_score': 0.0
                }

            # Perform verification
            result = self.verify_faces(live_image_array, stored_image_array)

            # Store verification result
            verification_data = {
                'user_id': user_id,
                'kyc_submission_id': approved_kyc['_id'],
                'similarity_score': result['similarity_score'],
                'verification_result': result['is_same_person'],
                'threshold_used': self.verification_threshold
            }

            self.kyc_repo.create_face_verification(verification_data)

            return result

        except Exception as e:
            self.logger.error(f"Error verifying face with stored image: {str(e)}")
            return {
                'success': False,
                'message': 'Face verification failed due to system error',
                'similarity_score': 0.0
            }

    def verify_faces(self, image1_array: np.ndarray, image2_array: np.ndarray) -> Dict:
        """Verify if two face images belong to the same person"""
        try:
            # Detect faces in both images
            face1 = self._detect_face(image1_array)
            face2 = self._detect_face(image2_array)

            if face1 is None:
                return {
                    'success': False,
                    'message': 'No face detected in first image',
                    'similarity_score': 0.0,
                    'is_same_person': False
                }

            if face2 is None:
                return {
                    'success': False,
                    'message': 'No face detected in second image',
                    'similarity_score': 0.0,
                    'is_same_person': False
                }

            # Preprocess faces
            processed_face1 = self._preprocess_face(face1)
            processed_face2 = self._preprocess_face(face2)

            if processed_face1 is None or processed_face2 is None:
                return {
                    'success': False,
                    'message': 'Failed to preprocess faces',
                    'similarity_score': 0.0,
                    'is_same_person': False
                }

            # Compare faces using Siamese model
            similarity_score = self.model_loader.compare_faces(processed_face1, processed_face2)

            if similarity_score is None:
                return {
                    'success': False,
                    'message': 'Face comparison failed',
                    'similarity_score': 0.0,
                    'is_same_person': False
                }

            # Determine if it's the same person
            is_same_person = similarity_score > self.verification_threshold

            return {
                'success': True,
                'message': 'Face verification completed successfully',
                'similarity_score': float(similarity_score),
                'is_same_person': is_same_person,
                'threshold_used': self.verification_threshold
            }

        except Exception as e:
            self.logger.error(f"Error verifying faces: {str(e)}")
            return {
                'success': False,
                'message': 'Face verification failed due to system error',
                'similarity_score': 0.0,
                'is_same_person': False
            }

    def extract_face_embedding(self, image_data: str) -> Optional[np.ndarray]:
        """Extract face embedding from image"""
        try:
            # Decode image
            image_array = self._decode_base64_image(image_data)
            if image_array is None:
                return None

            # Detect and extract face
            face_array = self._detect_face(image_array)
            if face_array is None:
                return None

            # Preprocess face
            processed_face = self._preprocess_face(face_array)
            if processed_face is None:
                return None

            # Extract embedding
            embedding = self.model_loader.extract_face_embedding(processed_face)
            return embedding

        except Exception as e:
            self.logger.error(f"Error extracting face embedding: {str(e)}")
            return None

    def validate_image_quality(self, image_data: str) -> Dict:
        """Validate image quality for face verification"""
        try:
            # Decode image
            image_array = self._decode_base64_image(image_data)
            if image_array is None:
                return {
                    'valid': False,
                    'message': 'Failed to decode image'
                }

            # Check image dimensions
            height, width = image_array.shape[:2]
            if height < 100 or width < 100:
                return {
                    'valid': False,
                    'message': 'Image resolution too low (minimum 100x100 pixels)'
                }

            # Check for face detection
            face_array = self._detect_face(image_array)
            if face_array is None:
                return {
                    'valid': False,
                    'message': 'No face detected in image'
                }

            # Check face size
            face_height, face_width = face_array.shape[:2]
            if face_height < 50 or face_width < 50:
                return {
                    'valid': False,
                    'message': 'Detected face is too small'
                }

            # Check image quality (basic blur detection)
            gray = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)
            blur_value = cv2.Laplacian(gray, cv2.CV_64F).var()

            if blur_value < 100:  # Threshold for blur detection
                return {
                    'valid': False,
                    'message': 'Image appears to be blurry'
                }

            return {
                'valid': True,
                'message': 'Image quality is acceptable',
                'image_dimensions': (width, height),
                'face_dimensions': (face_width, face_height),
                'blur_score': float(blur_value)
            }

        except Exception as e:
            self.logger.error(f"Error validating image quality: {str(e)}")
            return {
                'valid': False,
                'message': 'Image quality validation failed'
            }

    def get_verification_history(self, user_id: str) -> list[Dict]:
        """Get face verification history for a user"""
        try:
            return self.kyc_repo.get_face_verifications_by_user(user_id)
        except Exception as e:
            self.logger.error(f"Error getting verification history: {str(e)}")
            return []

# Global face verification service instance
face_verification_service = FaceVerificationService()
