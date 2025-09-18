"""
File Utilities - File handling and processing functions
Handles file upload, storage, and retrieval operations
"""

import os
import uuid
import logging
import base64
import mimetypes
from datetime import datetime
from typing import Dict, Optional, List, Tuple
from PIL import Image
import cv2
import numpy as np
from config import Config

class FileUtils:
    """Utility class for file operations"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.upload_folder = Config.UPLOAD_FOLDER
        self.allowed_extensions = Config.ALLOWED_EXTENSIONS
        self.max_file_size = Config.MAX_CONTENT_LENGTH

        # Ensure upload directory exists
        os.makedirs(self.upload_folder, exist_ok=True)

    def allowed_file(self, filename: str) -> bool:
        """Check if file extension is allowed"""
        try:
            return '.' in filename and \
                   filename.rsplit('.', 1)[1].lower() in self.allowed_extensions
        except Exception as e:
            self.logger.error(f"Error checking file extension: {str(e)}")
            return False

    def generate_unique_filename(self, original_filename: str) -> str:
        """Generate unique filename while preserving extension"""
        try:
            # Extract file extension
            if '.' in original_filename:
                name, ext = original_filename.rsplit('.', 1)
                ext = '.' + ext.lower()
            else:
                ext = ''

            # Generate unique identifier
            unique_id = str(uuid.uuid4())
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

            return f"{timestamp}_{unique_id}{ext}"
        except Exception as e:
            self.logger.error(f"Error generating unique filename: {str(e)}")
            return str(uuid.uuid4())

    def save_base64_file(self, base64_data: str, file_type: str = 'image', 
                        subdirectory: str = None) -> Dict:
        """Save base64 encoded file to disk"""
        try:
            # Remove data URL prefix if present
            if 'data:' in base64_data:
                header, base64_data = base64_data.split(',', 1)
                # Extract file extension from header
                if 'image/' in header:
                    file_ext = header.split('image/')[1].split(';')[0]
                    if file_ext == 'jpeg':
                        file_ext = 'jpg'
                else:
                    file_ext = 'bin'
            else:
                file_ext = 'jpg' if file_type == 'image' else 'bin'

            # Decode base64 data
            file_data = base64.b64decode(base64_data)

            # Check file size
            if len(file_data) > self.max_file_size:
                return {
                    'success': False,
                    'message': 'File size exceeds maximum allowed size'
                }

            # Generate filename
            filename = self.generate_unique_filename(f"file.{file_ext}")

            # Determine save path
            if subdirectory:
                save_dir = os.path.join(self.upload_folder, subdirectory)
                os.makedirs(save_dir, exist_ok=True)
                file_path = os.path.join(save_dir, filename)
            else:
                file_path = os.path.join(self.upload_folder, filename)

            # Save file
            with open(file_path, 'wb') as f:
                f.write(file_data)

            self.logger.info(f"File saved: {file_path}")

            return {
                'success': True,
                'filename': filename,
                'file_path': file_path,
                'file_size': len(file_data),
                'file_type': file_type,
                'file_extension': file_ext
            }

        except Exception as e:
            self.logger.error(f"Error saving base64 file: {str(e)}")
            return {
                'success': False,
                'message': f'Failed to save file: {str(e)}'
            }

    def load_file_as_base64(self, file_path: str) -> Optional[str]:
        """Load file and convert to base64 string"""
        try:
            if not os.path.exists(file_path):
                return None

            with open(file_path, 'rb') as f:
                file_data = f.read()

            # Encode to base64
            base64_data = base64.b64encode(file_data).decode('utf-8')

            # Add data URL prefix for images
            mime_type, _ = mimetypes.guess_type(file_path)
            if mime_type and mime_type.startswith('image/'):
                base64_data = f"data:{mime_type};base64,{base64_data}"

            return base64_data

        except Exception as e:
            self.logger.error(f"Error loading file as base64: {str(e)}")
            return None

    def delete_file(self, file_path: str) -> bool:
        """Delete file from disk"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                self.logger.info(f"File deleted: {file_path}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error deleting file: {str(e)}")
            return False

    def get_file_info(self, file_path: str) -> Dict:
        """Get file information"""
        try:
            if not os.path.exists(file_path):
                return {
                    'exists': False
                }

            stat = os.stat(file_path)
            mime_type, _ = mimetypes.guess_type(file_path)

            return {
                'exists': True,
                'file_path': file_path,
                'file_size': stat.st_size,
                'created_time': datetime.fromtimestamp(stat.st_ctime),
                'modified_time': datetime.fromtimestamp(stat.st_mtime),
                'mime_type': mime_type,
                'is_image': mime_type and mime_type.startswith('image/') if mime_type else False
            }

        except Exception as e:
            self.logger.error(f"Error getting file info: {str(e)}")
            return {
                'exists': False,
                'error': str(e)
            }

    def process_image(self, image_path: str, target_size: Tuple[int, int] = None, 
                     quality: int = 85) -> Dict:
        """Process and optimize image"""
        try:
            # Open image
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')

                # Resize if target size specified
                if target_size:
                    img = img.resize(target_size, Image.Resampling.LANCZOS)

                # Generate processed filename
                base_name = os.path.splitext(os.path.basename(image_path))[0]
                processed_filename = f"{base_name}_processed.jpg"
                processed_path = os.path.join(os.path.dirname(image_path), processed_filename)

                # Save processed image
                img.save(processed_path, 'JPEG', quality=quality, optimize=True)

                return {
                    'success': True,
                    'original_path': image_path,
                    'processed_path': processed_path,
                    'original_size': os.path.getsize(image_path),
                    'processed_size': os.path.getsize(processed_path),
                    'compression_ratio': os.path.getsize(processed_path) / os.path.getsize(image_path)
                }

        except Exception as e:
            self.logger.error(f"Error processing image: {str(e)}")
            return {
                'success': False,
                'message': f'Image processing failed: {str(e)}'
            }

    def extract_image_metadata(self, image_path: str) -> Dict:
        """Extract metadata from image"""
        try:
            # Using PIL for basic metadata
            with Image.open(image_path) as img:
                metadata = {
                    'format': img.format,
                    'mode': img.mode,
                    'size': img.size,
                    'width': img.width,
                    'height': img.height
                }

                # Extract EXIF data if available
                if hasattr(img, '_getexif') and img._getexif():
                    exif_data = img._getexif()
                    metadata['exif'] = exif_data

                return {
                    'success': True,
                    'metadata': metadata
                }

        except Exception as e:
            self.logger.error(f"Error extracting image metadata: {str(e)}")
            return {
                'success': False,
                'message': f'Failed to extract metadata: {str(e)}'
            }

    def validate_image_file(self, file_path: str) -> Dict:
        """Validate image file"""
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                return {
                    'valid': False,
                    'message': 'File does not exist'
                }

            # Check file size
            file_size = os.path.getsize(file_path)
            if file_size > self.max_file_size:
                return {
                    'valid': False,
                    'message': 'File size exceeds maximum allowed size'
                }

            # Try to open as image
            try:
                with Image.open(file_path) as img:
                    # Check image dimensions
                    width, height = img.size
                    if width < 50 or height < 50:
                        return {
                            'valid': False,
                            'message': 'Image dimensions too small'
                        }

                    if width > 10000 or height > 10000:
                        return {
                            'valid': False,
                            'message': 'Image dimensions too large'
                        }

                    return {
                        'valid': True,
                        'width': width,
                        'height': height,
                        'format': img.format,
                        'mode': img.mode,
                        'file_size': file_size
                    }

            except Exception as img_error:
                return {
                    'valid': False,
                    'message': f'Invalid image file: {str(img_error)}'
                }

        except Exception as e:
            self.logger.error(f"Error validating image file: {str(e)}")
            return {
                'valid': False,
                'message': f'Validation error: {str(e)}'
            }

    def cleanup_old_files(self, days_old: int = 30) -> Dict:
        """Clean up old files from upload directory"""
        try:
            deleted_count = 0
            total_size_freed = 0
            current_time = datetime.now()

            for root, dirs, files in os.walk(self.upload_folder):
                for file in files:
                    file_path = os.path.join(root, file)

                    try:
                        # Check file age
                        file_stat = os.stat(file_path)
                        file_age = (current_time - datetime.fromtimestamp(file_stat.st_mtime)).days

                        if file_age > days_old:
                            file_size = file_stat.st_size
                            os.remove(file_path)
                            deleted_count += 1
                            total_size_freed += file_size

                    except Exception as file_error:
                        self.logger.warning(f"Error processing file {file_path}: {str(file_error)}")
                        continue

            return {
                'success': True,
                'deleted_files': deleted_count,
                'size_freed_bytes': total_size_freed,
                'size_freed_mb': total_size_freed / (1024 * 1024)
            }

        except Exception as e:
            self.logger.error(f"Error cleaning up old files: {str(e)}")
            return {
                'success': False,
                'message': f'Cleanup failed: {str(e)}'
            }

    def get_storage_usage(self) -> Dict:
        """Get storage usage statistics"""
        try:
            total_size = 0
            file_count = 0

            for root, dirs, files in os.walk(self.upload_folder):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        total_size += os.path.getsize(file_path)
                        file_count += 1
                    except OSError:
                        continue

            return {
                'success': True,
                'total_files': file_count,
                'total_size_bytes': total_size,
                'total_size_mb': total_size / (1024 * 1024),
                'total_size_gb': total_size / (1024 * 1024 * 1024),
                'upload_folder': self.upload_folder
            }

        except Exception as e:
            self.logger.error(f"Error getting storage usage: {str(e)}")
            return {
                'success': False,
                'message': f'Failed to get storage usage: {str(e)}'
            }

def save_uploaded_file(file_data: str, file_type: str = 'image', subdirectory: str = None) -> Dict:
    """Global function to save uploaded file"""
    file_utils = FileUtils()
    return file_utils.save_base64_file(file_data, file_type, subdirectory)

def get_file_url(file_path: str) -> str:
    """Generate URL for file access"""
    try:
        # In a real application, this would generate a proper URL
        # For now, return relative path
        return f"/files/{os.path.basename(file_path)}"
    except Exception:
        return ""

# Global file utils instance
file_utils = FileUtils()
