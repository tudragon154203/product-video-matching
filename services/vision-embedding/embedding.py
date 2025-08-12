import torch
import torch.nn.functional as F
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import numpy as np
from typing import Tuple, Optional
import structlog

logger = structlog.get_logger()


class EmbeddingExtractor:
    """Extracts visual embeddings using CLIP model"""
    
    def __init__(self, model_name: str = "clip-vit-b32"):
        self.model_name = model_name
        self.device = None
        self.model = None
        self.processor = None
        self.initialized = False
    
    async def initialize(self):
        """Initialize the model and processor"""
        try:
            # Detect device
            if torch.cuda.is_available():
                self.device = torch.device("cuda")
                logger.info("Using GPU for embeddings", device=str(self.device))
            else:
                self.device = torch.device("cpu")
                logger.info("Using CPU for embeddings", device=str(self.device))
            
            # Load model and processor
            if self.model_name == "clip-vit-b32":
                model_id = "openai/clip-vit-base-patch32"
            else:
                model_id = self.model_name
            
            logger.info("Loading CLIP model", model_id=model_id)
            
            self.processor = CLIPProcessor.from_pretrained(model_id)
            self.model = CLIPModel.from_pretrained(model_id)
            self.model.to(self.device)
            self.model.eval()
            
            self.initialized = True
            logger.info("CLIP model loaded successfully")
            
        except Exception as e:
            logger.error("Failed to initialize embedding model", error=str(e))
            # Fallback to mock embeddings for MVP
            self.initialized = False
    
    async def extract_embeddings(self, image_path: str) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """Extract RGB and grayscale embeddings from an image"""
        try:
            # Load and preprocess image
            image = Image.open(image_path).convert('RGB')
            
            if self.initialized:
                # Real CLIP embeddings
                return await self._extract_clip_embeddings(image)
            else:
                # Mock embeddings for MVP
                return await self._extract_mock_embeddings(image)
                
        except Exception as e:
            logger.error("Failed to extract embeddings", image_path=image_path, error=str(e))
            return None, None
    
    async def _extract_clip_embeddings(self, image: Image.Image) -> Tuple[np.ndarray, np.ndarray]:
        """Extract real CLIP embeddings"""
        with torch.no_grad():
            # RGB embedding
            rgb_inputs = self.processor(images=image, return_tensors="pt")
            rgb_inputs = {k: v.to(self.device) for k, v in rgb_inputs.items()}
            rgb_features = self.model.get_image_features(**rgb_inputs)
            rgb_embedding = F.normalize(rgb_features, p=2, dim=1).cpu().numpy()[0]
            
            # Grayscale embedding
            gray_image = image.convert('L').convert('RGB')  # Convert to grayscale then back to RGB
            gray_inputs = self.processor(images=gray_image, return_tensors="pt")
            gray_inputs = {k: v.to(self.device) for k, v in gray_inputs.items()}
            gray_features = self.model.get_image_features(**gray_inputs)
            gray_embedding = F.normalize(gray_features, p=2, dim=1).cpu().numpy()[0]
            
            return rgb_embedding, gray_embedding
    
    async def _extract_mock_embeddings(self, image: Image.Image) -> Tuple[np.ndarray, np.ndarray]:
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
    
    async def cleanup(self):
        """Clean up resources"""
        if self.model is not None:
            del self.model
        if self.processor is not None:
            del self.processor
        
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        logger.info("Cleaned up embedding extractor")