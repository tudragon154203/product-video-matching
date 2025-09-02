import numpy as np
from PIL import Image
from typing import Tuple
from common_py.logging_config import configure_logging

logger = configure_logging("vision-embedding:mock_generator")

class MockEmbeddingGenerator:
    def __init__(self):
        pass

    async def extract_mock_embeddings(self, image: Image.Image) -> Tuple[np.ndarray, np.ndarray]:
        """Extract mock embeddings for MVP testing"""
        # Create deterministic but varied embeddings based on image properties
        width, height = image.size
        
        # Use image properties to create somewhat realistic embeddings
        np.random.seed(hash(str(width * height)) % 2**32)
        
        # Generate 512-dimensional embeddings (CLIP ViT-B/32 dimension)
        rgb_embedding = np.random.normal(0, 0.1, 512).astype(np.float32)
        gray_embedding = np.random.normal(0, 0.1, 512).astype(np.float32)
        
        # Normalize embeddings
        rgb_embedding = rgb_embedding / np.linalg.norm(rgb_embedding)
        gray_embedding = gray_embedding / np.linalg.norm(gray_embedding)
        
        # Add some correlation between RGB and grayscale
        gray_embedding = 0.7 * gray_embedding + 0.3 * rgb_embedding
        gray_embedding = gray_embedding / np.linalg.norm(gray_embedding)
        
        logger.info("Generated mock embeddings", 
                   rgb_dim=rgb_embedding.shape[0], 
                   gray_dim=gray_embedding.shape[0])
        
        return rgb_embedding, gray_embedding
