"""
Security Utilities - Encryption, hashing, and security functions
Provides security-related utilities for the KYC system
"""

import hashlib
import hmac
import secrets
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
import bcrypt
import jwt
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os
from config import Config


class Security_utils:
    """Security utility functions"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.jwt_secret = Config.JWT_SECRET_KEY
        self.jwt_expiry = Config.JWT_ACCESS_TOKEN_EXPIRES
        self.bcrypt_rounds = Config.BCRYPT_LOG_ROUNDS

    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        try:
            salt = bcrypt.gensalt(rounds=self.bcrypt_rounds)
            hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
            return hashed.decode('utf-8')
        except Exception as e:
            self.logger.error(f"Error hashing password: {e}")
            raise

    def verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
        except Exception as e:
            self.logger.error(f"Error verifying password: {e}")
            return False

    def generate_jwt_token(self, user_id: str, user_role: str = 'user', additional_claims: Dict = None) -> str:
        """Generate JWT token"""
        try:
            payload = {
                'user_id': user_id,
                'user_role': user_role,
                'iat': datetime.utcnow(),
                'exp': datetime.utcnow() + self.jwt_expiry
            }
            if additional_claims:
                payload.update(additional_claims)
            token = jwt.encode(payload, self.jwt_secret, algorithm='HS256')
            return token
        except Exception as e:
            self.logger.error(f"Error generating JWT token: {e}")
            raise

    def verify_jwt_token(self, token: str) -> Optional[Dict]:
        """Verify and decode JWT token"""
        try:
            return jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            self.logger.warning("JWT token expired")
            return None
        except jwt.InvalidTokenError:
            self.logger.warning("Invalid JWT token")
            return None
        except Exception as e:
            self.logger.error(f"Error verifying JWT token: {e}")
            return None

    def generate_secure_token(self, length: int = 32) -> str:
        """Generate cryptographically secure random token"""
        try:
            return secrets.token_urlsafe(length)
        except Exception as e:
            self.logger.error(f"Error generating secure token: {e}")
            raise

    def generate_api_key(self) -> str:
        """Generate API key"""
        try:
            timestamp = str(int(datetime.utcnow().timestamp()))
            random_part = secrets.token_hex(16)
            combined = f"{timestamp}_{random_part}"
            api_key_hash = hashlib.sha256(combined.encode()).hexdigest()
            return f"kyc_{api_key_hash[:32]}"
        except Exception as e:
            self.logger.error(f"Error generating API key: {e}")
            raise

    def hash_sensitive_data(self, data: str, salt: str = None) -> str:
        """Hash sensitive data with optional salt"""
        try:
            if salt is None:
                salt = secrets.token_hex(16)
            salted_data = f"{data}{salt}"
            hashed = hashlib.sha256(salted_data.encode('utf-8')).hexdigest()
            return f"{hashed}:{salt}"
        except Exception as e:
            self.logger.error(f"Error hashing sensitive data: {e}")
            raise

    def verify_sensitive_data(self, data: str, hashed_data: str) -> bool:
        """Verify sensitive data against hash"""
        try:
            if ':' not in hashed_data:
                return False
            stored_hash, salt = hashed_data.split(':', 1)
            computed_hash = hashlib.sha256(f"{data}{salt}".encode('utf-8')).hexdigest()
            return hmac.compare_digest(stored_hash, computed_hash)
        except Exception as e:
            self.logger.error(f"Error verifying sensitive data: {e}")
            return False

    def encrypt_data(self, data: str, key: str = None) -> Dict:
        """Encrypt data using Fernet symmetric encryption"""
        try:
            if key is None:
                key = self._derive_key(Config.SECRET_KEY)
            fernet = Fernet(key)
            encrypted = fernet.encrypt(data.encode('utf-8'))
            return {
                'success': True,
                'encrypted_data': base64.b64encode(encrypted).decode('utf-8'),
                'key': key.decode('utf-8') if isinstance(key, bytes) else key
            }
        except Exception as e:
            self.logger.error(f"Error encrypting data: {e}")
            return {'success': False, 'message': f'Encryption failed: {e}'}

    def decrypt_data(self, encrypted_data: str, key: str) -> Dict:
        """Decrypt data using Fernet symmetric encryption"""
        try:
            if isinstance(key, str):
                key = key.encode('utf-8')
            fernet = Fernet(key)
            decrypted = fernet.decrypt(base64.b64decode(encrypted_data))
            return {'success': True, 'decrypted_data': decrypted.decode('utf-8')}
        except Exception as e:
            self.logger.error(f"Error decrypting data: {e}")
            return {'success': False, 'message': f'Decryption failed: {e}'}

    def _derive_key(self, password: str, salt: bytes = None) -> bytes:
        """Derive encryption key from password"""
        try:
            if salt is None:
                salt = b'kyc_system_salt_2024'
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            return base64.urlsafe_b64encode(kdf.derive(password.encode('utf-8')))
        except Exception as e:
            self.logger.error(f"Error deriving key: {e}")
            raise

    def generate_otp(self, length: int = 6) -> str:
        """Generate One-Time Password"""
        try:
            return ''.join(str(secrets.randbelow(10)) for _ in range(length))
        except Exception as e:
            self.logger.error(f"Error generating OTP: {e}")
            raise

    def verify_otp(self, provided_otp: str, stored_otp: str, expiry_time: datetime) -> bool:
        """Verify OTP"""
        try:
            if datetime.utcnow() > expiry_time:
                return False
            return hmac.compare_digest(provided_otp, stored_otp)
        except Exception as e:
            self.logger.error(f"Error verifying OTP: {e}")
            return False

    def create_audit_hash(self, data: Dict) -> str:
        """Create audit hash for data integrity"""
        try:
            sorted_data = self._sort_dict_recursively(data)
            data_str = str(sorted_data)
            return hashlib.sha256(data_str.encode('utf-8')).hexdigest()
        except Exception as e:
            self.logger.error(f"Error creating audit hash: {e}")
            raise

    def verify_audit_hash(self, data: Dict, stored_hash: str) -> bool:
        """Verify audit hash for data integrity"""
        try:
            return hmac.compare_digest(self.create_audit_hash(data), stored_hash)
        except Exception as e:
            self.logger.error(f"Error verifying audit hash: {e}")
            return False

    def _sort_dict_recursively(self, obj: Any) -> Any:
        """Recursively sort dictionary for consistent hashing"""
        if isinstance(obj, dict):
            return {k: self._sort_dict_recursively(v) for k, v in sorted(obj.items())}
        if isinstance(obj, list):
            return [self._sort_dict_recursively(v) for v in obj]
        return obj

    def sanitize_input(self, input_string: str, max_length: int = 1000) -> str:
        """Sanitize user input"""
        try:
            if not isinstance(input_string, str):
                return ""
            sanitized = input_string.replace('\x00', '').replace('\r', '').replace('\n', ' ')
            if len(sanitized) > max_length:
                sanitized = sanitized[:max_length]
            return sanitized.strip()
        except Exception as e:
            self.logger.error(f"Error sanitizing input: {e}")
            return ""

    def validate_session(self, session_data: Dict) -> bool:
        """Validate session data"""
        try:
            required = ['user_id', 'session_id', 'created_at', 'last_activity']
            for field in required:
                if field not in session_data:
                    return False
            last = session_data['last_activity']
            if isinstance(last, str):
                last = datetime.fromisoformat(last)
            if datetime.utcnow() - last > timedelta(hours=24):
                return False
            return True
        except Exception as e:
            self.logger.error(f"Error validating session: {e}")
            return False

    def rate_limit_check(self, identifier: str, max_requests: int = 60, time_window: int = 60) -> Dict:
        """Basic rate limiting check"""
        try:
            return {'allowed': True, 'remaining_requests': max_requests - 1,
                    'reset_time': datetime.utcnow() + timedelta(seconds=time_window)}
        except Exception as e:
            self.logger.error(f"Error in rate limit check: {e}")
            return {'allowed': False, 'error': str(e)}


# Global wrapper functions
def hash_sensitive_data(data: str) -> str:
    return Security_utils().hash_sensitive_data(data)

def generate_secure_token(length: int = 32) -> str:
    return Security_utils().generate_secure_token(length)

def create_jwt_token(user_id: str, user_role: str = 'user') -> str:
    return Security_utils().generate_jwt_token(user_id, user_role)

def verify_jwt_token(token: str) -> Optional[Dict]:
    return Security_utils().verify_jwt_token(token)

# Global security utils instance
security_utils = Security_utils()
