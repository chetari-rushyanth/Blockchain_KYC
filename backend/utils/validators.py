"""
Validators - Data validation utilities for KYC system
Provides validation functions for various data types and formats
"""

import re
import logging
from datetime import datetime, date
from typing import Dict, List, Any, Optional

class KYCValidators:
    """Validation functions for KYC data"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def validate_email(self, email: str) -> bool:
        """Validate email format"""
        try:
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            return bool(re.match(email_pattern, email))
        except Exception as e:
            self.logger.error(f"Error validating email: {str(e)}")
            return False

    def validate_phone_number(self, phone: str) -> bool:
        """Validate phone number format"""
        try:
            # Remove all non-digit characters
            digits_only = re.sub(r'[^0-9]', '', phone)

            # Check if it has between 10 and 15 digits
            return 10 <= len(digits_only) <= 15
        except Exception as e:
            self.logger.error(f"Error validating phone number: {str(e)}")
            return False

    def validate_date_of_birth(self, dob: str) -> bool:
        """Validate date of birth"""
        try:
            # Parse date in various formats
            date_formats = ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y']

            for fmt in date_formats:
                try:
                    birth_date = datetime.strptime(dob, fmt).date()

                    # Check if date is not in the future
                    if birth_date > date.today():
                        return False

                    # Check if person is not too old (reasonable age limit)
                    age = (date.today() - birth_date).days // 365
                    if age > 150:
                        return False

                    return True
                except ValueError:
                    continue

            return False
        except Exception as e:
            self.logger.error(f"Error validating date of birth: {str(e)}")
            return False

    def validate_full_name(self, name: str) -> bool:
        """Validate full name format"""
        try:
            if not name or len(name.strip()) < 2:
                return False

            # Check for valid characters (letters, spaces, hyphens, apostrophes)
            name_pattern = r"^[a-zA-Z\s\-'\.]+$"

            if not re.match(name_pattern, name):
                return False

            # Check for at least one space (first name and last name)
            if ' ' not in name.strip():
                return False

            return True
        except Exception as e:
            self.logger.error(f"Error validating full name: {str(e)}")
            return False

    def validate_document_number(self, doc_number: str, doc_type: str) -> bool:
        """Validate document number based on document type"""
        try:
            if not doc_number:
                return False

            doc_number = doc_number.strip().upper()

            # Different validation patterns for different document types
            patterns = {
                'passport': r'^[A-Z0-9]{6,9}$',
                'national_id': r'^[A-Z0-9]{8,20}$',
                'aadhaar': r'^[0-9]{12}$',
                'drivers_license': r'^[A-Z0-9]{5,20}$',
                'voter_id': r'^[A-Z0-9]{8,20}$'
            }

            pattern = patterns.get(doc_type.lower())
            if not pattern:
                # Generic pattern for unknown document types
                pattern = r'^[A-Z0-9]{5,20}$'

            return bool(re.match(pattern, doc_number))
        except Exception as e:
            self.logger.error(f"Error validating document number: {str(e)}")
            return False

    def validate_address(self, address: Dict) -> bool:
        """Validate address information"""
        try:
            required_fields = ['street', 'city', 'country']

            for field in required_fields:
                if field not in address or not address[field] or len(address[field].strip()) < 2:
                    return False

            # Validate postal code if provided
            if 'postal_code' in address and address['postal_code']:
                postal_code = address['postal_code'].strip()
                # Basic postal code validation (alphanumeric, 3-10 characters)
                if not re.match(r'^[A-Z0-9\s\-]{3,10}$', postal_code.upper()):
                    return False

            return True
        except Exception as e:
            self.logger.error(f"Error validating address: {str(e)}")
            return False

    def validate_base64_image(self, image_data: str) -> bool:
        """Validate base64 image data"""
        try:
            if not image_data:
                return False

            # Remove data URL prefix if present
            if 'data:image' in image_data:
                image_data = image_data.split(',')[1]

            # Check if it's valid base64
            import base64
            try:
                decoded = base64.b64decode(image_data)

                # Check minimum file size (1KB)
                if len(decoded) < 1024:
                    return False

                # Check maximum file size (10MB)
                if len(decoded) > 10 * 1024 * 1024:
                    return False

                return True
            except Exception:
                return False

        except Exception as e:
            self.logger.error(f"Error validating base64 image: {str(e)}")
            return False

    def validate_nationality(self, nationality: str) -> bool:
        """Validate nationality"""
        try:
            if not nationality or len(nationality.strip()) < 2:
                return False

            # Basic validation - letters only, reasonable length
            nationality_pattern = r'^[a-zA-Z\s]{2,50}$'
            return bool(re.match(nationality_pattern, nationality))
        except Exception as e:
            self.logger.error(f"Error validating nationality: {str(e)}")
            return False

    def validate_gender(self, gender: str) -> bool:
        """Validate gender field"""
        try:
            valid_genders = ['male', 'female', 'other', 'm', 'f', 'o']
            return gender.lower() in valid_genders
        except Exception as e:
            self.logger.error(f"Error validating gender: {str(e)}")
            return False

def validate_kyc_data(kyc_data: Dict, partial: bool = False) -> Dict:
    """Validate complete KYC data"""
    validator = KYCValidators()
    errors = []

    try:
        # Required fields for complete validation
        required_fields = [
            'full_name', 'date_of_birth', 'gender', 'nationality',
            'address', 'phone_number', 'email', 'document_type', 'document_number'
        ]

        # Check required fields (only for complete validation)
        if not partial:
            for field in required_fields:
                if field not in kyc_data or not kyc_data[field]:
                    errors.append(f"Missing required field: {field}")

        # Validate individual fields if present
        if 'full_name' in kyc_data and kyc_data['full_name']:
            if not validator.validate_full_name(kyc_data['full_name']):
                errors.append("Invalid full name format")

        if 'email' in kyc_data and kyc_data['email']:
            if not validator.validate_email(kyc_data['email']):
                errors.append("Invalid email format")

        if 'phone_number' in kyc_data and kyc_data['phone_number']:
            if not validator.validate_phone_number(kyc_data['phone_number']):
                errors.append("Invalid phone number format")

        if 'date_of_birth' in kyc_data and kyc_data['date_of_birth']:
            if not validator.validate_date_of_birth(kyc_data['date_of_birth']):
                errors.append("Invalid date of birth")

        if 'gender' in kyc_data and kyc_data['gender']:
            if not validator.validate_gender(kyc_data['gender']):
                errors.append("Invalid gender value")

        if 'nationality' in kyc_data and kyc_data['nationality']:
            if not validator.validate_nationality(kyc_data['nationality']):
                errors.append("Invalid nationality")

        if 'document_number' in kyc_data and kyc_data['document_number']:
            doc_type = kyc_data.get('document_type', 'national_id')
            if not validator.validate_document_number(kyc_data['document_number'], doc_type):
                errors.append("Invalid document number format")

        if 'address' in kyc_data and kyc_data['address']:
            if isinstance(kyc_data['address'], dict):
                if not validator.validate_address(kyc_data['address']):
                    errors.append("Invalid address information")
            elif isinstance(kyc_data['address'], str):
                if len(kyc_data['address'].strip()) < 10:
                    errors.append("Address too short")

        # Validate images if present
        if 'face_image' in kyc_data and kyc_data['face_image']:
            if not validator.validate_base64_image(kyc_data['face_image']):
                errors.append("Invalid face image data")

        if 'document_image' in kyc_data and kyc_data['document_image']:
            if not validator.validate_base64_image(kyc_data['document_image']):
                errors.append("Invalid document image data")

        if 'document_back_image' in kyc_data and kyc_data['document_back_image']:
            if not validator.validate_base64_image(kyc_data['document_back_image']):
                errors.append("Invalid document back image data")

        return {
            'valid': len(errors) == 0,
            'errors': errors
        }

    except Exception as e:
        logging.getLogger(__name__).error(f"Error validating KYC data: {str(e)}")
        return {
            'valid': False,
            'errors': [f"Validation error: {str(e)}"]
        }

def validate_user_data(user_data: Dict) -> Dict:
    """Validate user registration data"""
    validator = KYCValidators()
    errors = []

    try:
        # Required fields
        required_fields = ['email', 'full_name', 'phone_number']

        for field in required_fields:
            if field not in user_data or not user_data[field]:
                errors.append(f"Missing required field: {field}")

        # Validate email
        if 'email' in user_data and user_data['email']:
            if not validator.validate_email(user_data['email']):
                errors.append("Invalid email format")

        # Validate full name
        if 'full_name' in user_data and user_data['full_name']:
            if not validator.validate_full_name(user_data['full_name']):
                errors.append("Invalid full name format")

        # Validate phone number
        if 'phone_number' in user_data and user_data['phone_number']:
            if not validator.validate_phone_number(user_data['phone_number']):
                errors.append("Invalid phone number format")

        return {
            'valid': len(errors) == 0,
            'errors': errors
        }

    except Exception as e:
        logging.getLogger(__name__).error(f"Error validating user data: {str(e)}")
        return {
            'valid': False,
            'errors': [f"Validation error: {str(e)}"]
        }

def validate_admin_action(action_data: Dict) -> Dict:
    """Validate admin action data"""
    errors = []

    try:
        # Required fields
        required_fields = ['admin_id', 'action_type']

        for field in required_fields:
            if field not in action_data or not action_data[field]:
                errors.append(f"Missing required field: {field}")

        # Validate action type
        valid_actions = ['approve', 'reject', 'revoke', 'update']
        if 'action_type' in action_data:
            if action_data['action_type'] not in valid_actions:
                errors.append(f"Invalid action type. Must be one of: {valid_actions}")

        # Validate admin ID format
        if 'admin_id' in action_data and action_data['admin_id']:
            if len(action_data['admin_id']) < 3:
                errors.append("Admin ID too short")

        return {
            'valid': len(errors) == 0,
            'errors': errors
        }

    except Exception as e:
        logging.getLogger(__name__).error(f"Error validating admin action: {str(e)}")
        return {
            'valid': False,
            'errors': [f"Validation error: {str(e)}"]
        }

# Global validator instance
kyc_validators = KYCValidators()
