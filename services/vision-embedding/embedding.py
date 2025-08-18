import torch
import torch.nn.functional as F
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import numpy as np
from typing import Tuple, Optional
from common_py.logging_config import configure_logging

logger = configure_logging("vision-embedding")

from config_loader import config

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
    
    async def extract_embeddings_with_mask(self, image_path: str, mask_path: str) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """Extract RGB and grayscale embeddings from an image with mask applied"""
        try:
            # Load and preprocess image
            image = Image.open(image_path).convert('RGB')
            
            # Resize image to config.IMG_SIZE
            if image.size != config.IMG_SIZE:
                image = image.resize(config.IMG_SIZE, Image.LANCZOS) # Using LANCZOS for better quality resizing
            
            # Load mask
            mask = Image.open(mask_path).convert('L')
            
            # Resize mask to match image size if needed
            if mask.size != config.IMG_SIZE:
                mask = mask.resize(config.IMG_SIZE, Image.NEAREST)
            
            # Apply mask to image
            masked_image = self._apply_mask_to_image(image, mask)
            
            if self.initialized:
                # Real CLIP embeddings with mask
                return await self._extract_clip_embeddings(masked_image)
            else:
                # Mock embeddings for MVP with mask
                return await self._extract_mock_embeddings(masked_image)
                
        except Exception as e:
            logger.error("Failed to extract embeddings with mask", 
                        image_path=image_path, mask_path=mask_path, error=str(e))
            return None, None
    
    def _apply_mask_to_image(self, image: Image.Image, mask: Image.Image) -> Image.Image:
        """Apply mask to image, setting background to black"""
        # Convert mask to numpy array
        mask_array = np.array(mask)
        
        # Normalize mask to 0-1 range
        mask_normalized = mask_array.astype(np.float32) / 255.0
        
        # Convert image to numpy array
        image_array = np.array(image)
        
        # Apply mask to each channel
        masked_array = image_array.copy()
        for channel in range(3):  # RGB channels
            masked_array[:, :, channel] = masked_array[:, :, channel] * mask_normalized
        
        # Convert back to PIL Image
        masked_image = Image.fromarray(masked_array.astype(np.uint8))
        
        return masked_image