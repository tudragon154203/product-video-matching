import torch
import torch.nn.functional as F
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import numpy as np
from typing import Tuple, Optional
from common_py.logging_config import configure_logging
from embedding_components.clip_processor import CLIPProcessor as CustomCLIPProcessor
from embedding_components.mock_generator import MockEmbeddingGenerator

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
        self.clip_processor_instance = None
        self.mock_generator = MockEmbeddingGenerator()
    
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
            
            self.clip_processor_instance = CustomCLIPProcessor(self.model, self.processor, self.device)

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
                return await self.clip_processor_instance.extract_clip_embeddings(image)
            else:
                # Mock embeddings for MVP
                return await self.mock_generator.extract_mock_embeddings(image)
                
        except Exception as e:
            logger.error("Failed to extract embeddings", image_path=image_path, error=str(e))
            return None, None
    
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
        if self.initialized:
            return await self.clip_processor_instance.extract_embeddings_with_mask(image_path, mask_path, config.IMG_SIZE)
        else:
            # Mock embeddings for MVP with mask
            image = Image.open(image_path).convert('RGB')
            return await self.mock_generator.extract_mock_embeddings(image)
