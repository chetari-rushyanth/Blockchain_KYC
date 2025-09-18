"""
Model Loader for Face Recognition System
Handles loading and initialization of CNN and Siamese models
"""

import os
import logging
import tensorflow as tf
from tensorflow import keras
import numpy as np
import cv2
from config import Config

class ModelLoader:
    """Handles loading and management of ML models"""

    def __init__(self):
        self.face_embedding_model = None
        self.siamese_model = None
        self.logger = logging.getLogger(__name__)
        self.models_loaded = False

    def load_face_embedding_model(self):
        """Load the face embedding CNN model"""
        try:
            model_path = Config.FACE_EMBEDDING_MODEL_PATH
            if os.path.exists(model_path):
                self.face_embedding_model = keras.models.load_model(model_path)
                self.logger.info(f"Face embedding model loaded from {model_path}")
            else:
                # If model doesn't exist, create a placeholder model
                self.logger.warning(f"Face embedding model not found at {model_path}, creating placeholder")
                self.face_embedding_model = self._create_placeholder_embedding_model()

            return True
        except Exception as e:
            self.logger.error(f"Error loading face embedding model: {str(e)}")
            return False

    def load_siamese_model(self):
        """Load the Siamese model for face verification"""
        try:
            # Try to load .h5 file first
            model_path = Config.SIAMESE_MODEL_PATH
            if os.path.exists(model_path):
                self.siamese_model = keras.models.load_model(model_path)
                self.logger.info(f"Siamese model loaded from {model_path}")
                return True

            # Try to load .keras file
            keras_path = Config.SIAMESE_KERAS_MODEL_PATH
            if os.path.exists(keras_path):
                self.siamese_model = keras.models.load_model(keras_path)
                self.logger.info(f"Siamese model loaded from {keras_path}")
                return True

            # If neither exists, create placeholder
            self.logger.warning("Siamese model not found, creating placeholder")
            self.siamese_model = self._create_placeholder_siamese_model()
            return True

        except Exception as e:
            self.logger.error(f"Error loading Siamese model: {str(e)}")
            return False

    def _create_placeholder_embedding_model(self):
        """Create a placeholder face embedding model"""
        input_layer = keras.layers.Input(shape=(224, 224, 3))

        # Simple CNN architecture for face embedding
        x = keras.layers.Conv2D(32, (3, 3), activation='relu')(input_layer)
        x = keras.layers.MaxPooling2D((2, 2))(x)
        x = keras.layers.Conv2D(64, (3, 3), activation='relu')(x)
        x = keras.layers.MaxPooling2D((2, 2))(x)
        x = keras.layers.Conv2D(128, (3, 3), activation='relu')(x)
        x = keras.layers.MaxPooling2D((2, 2))(x)

        x = keras.layers.GlobalAveragePooling2D()(x)
        x = keras.layers.Dense(512, activation='relu')(x)
        x = keras.layers.Dropout(0.5)(x)
        embedding = keras.layers.Dense(128, activation=None, name='embedding')(x)

        model = keras.Model(inputs=input_layer, outputs=embedding)
        model.compile(optimizer='adam', loss='mse')

        self.logger.info("Created placeholder face embedding model")
        return model

    def _create_placeholder_siamese_model(self):
        """Create a placeholder Siamese model"""
        # Input layers for two images
        input_a = keras.layers.Input(shape=(224, 224, 3), name='input_a')
        input_b = keras.layers.Input(shape=(224, 224, 3), name='input_b')

        # Shared CNN architecture
        def create_base_network():
            model = keras.Sequential([
                keras.layers.Conv2D(32, (3, 3), activation='relu'),
                keras.layers.MaxPooling2D((2, 2)),
                keras.layers.Conv2D(64, (3, 3), activation='relu'),
                keras.layers.MaxPooling2D((2, 2)),
                keras.layers.Conv2D(128, (3, 3), activation='relu'),
                keras.layers.GlobalAveragePooling2D(),
                keras.layers.Dense(128, activation='relu')
            ])
            return model

        base_network = create_base_network()

        # Process both inputs through the same network
        processed_a = base_network(input_a)
        processed_b = base_network(input_b)

        # Calculate distance between embeddings
        distance = keras.layers.Lambda(
            lambda x: tf.abs(x[0] - x[1])
        )([processed_a, processed_b])

        # Final similarity score
        output = keras.layers.Dense(1, activation='sigmoid')(distance)

        model = keras.Model(inputs=[input_a, input_b], outputs=output)
        model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])

        self.logger.info("Created placeholder Siamese model")
        return model

    def initialize_models(self):
        """Initialize all models"""
        try:
            embedding_loaded = self.load_face_embedding_model()
            siamese_loaded = self.load_siamese_model()

            self.models_loaded = embedding_loaded and siamese_loaded

            if self.models_loaded:
                self.logger.info("All models initialized successfully")
            else:
                self.logger.warning("Some models failed to initialize")

            return self.models_loaded

        except Exception as e:
            self.logger.error(f"Error initializing models: {str(e)}")
            return False

    def get_face_embedding_model(self):
        """Get the face embedding model"""
        if not self.models_loaded:
            self.initialize_models()
        return self.face_embedding_model

    def get_siamese_model(self):
        """Get the Siamese model"""
        if not self.models_loaded:
            self.initialize_models()
        return self.siamese_model

    def preprocess_image(self, image_array, target_size=(224, 224)):
        """Preprocess image for model input"""
        try:
            # Resize image
            image_resized = cv2.resize(image_array, target_size)

            # Normalize pixel values
            image_normalized = image_resized.astype(np.float32) / 255.0

            # Add batch dimension
            image_batch = np.expand_dims(image_normalized, axis=0)

            return image_batch

        except Exception as e:
            self.logger.error(f"Error preprocessing image: {str(e)}")
            return None

    def extract_face_embedding(self, image_array):
        """Extract face embedding from image"""
        try:
            model = self.get_face_embedding_model()
            if model is None:
                return None

            processed_image = self.preprocess_image(image_array)
            if processed_image is None:
                return None

            embedding = model.predict(processed_image)
            return embedding[0]  # Remove batch dimension

        except Exception as e:
            self.logger.error(f"Error extracting face embedding: {str(e)}")
            return None

    def compare_faces(self, image1_array, image2_array):
        """Compare two face images using Siamese model"""
        try:
            model = self.get_siamese_model()
            if model is None:
                return None

            processed_image1 = self.preprocess_image(image1_array)
            processed_image2 = self.preprocess_image(image2_array)

            if processed_image1 is None or processed_image2 is None:
                return None

            similarity_score = model.predict([processed_image1, processed_image2])
            return float(similarity_score[0][0])

        except Exception as e:
            self.logger.error(f"Error comparing faces: {str(e)}")
            return None

# Global model loader instance
model_loader = ModelLoader()

