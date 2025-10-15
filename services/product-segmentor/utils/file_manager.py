"""File management for mask storage operations."""

import os
import asyncio
from pathlib import Path
from typing import Optional
import tempfile
import shutil
import numpy as np
from PIL import Image
from common_py.logging_config import configure_logging

logger = configure_logging("product-segmentor:file_manager")


class FileManager:
    """Manages file operations for mask storage."""

    def __init__(self, foreground_mask_dir_path: str, people_mask_dir_path: str, product_mask_dir_path: str):
        """Initialize file manager.

        Args:
            foreground_mask_dir_path: Base directory for foreground mask storage
            people_mask_dir_path: Base directory for people mask storage
            product_mask_dir_path: Base directory for product mask storage
        """
        self.foreground_mask_base_path = Path(foreground_mask_dir_path)
        self.people_mask_base_path = Path(people_mask_dir_path)
        self.product_mask_base_path = Path(product_mask_dir_path)

        self.foreground_products_dir = self.foreground_mask_base_path / "product_images"
        self.foreground_frames_dir = self.foreground_mask_base_path / "video_frames"

        self.people_products_dir = self.people_mask_base_path / "product_images"
        self.people_frames_dir = self.people_mask_base_path / "video_frames"

        self.product_products_dir = self.product_mask_base_path / "product_images"
        self.product_frames_dir = self.product_mask_base_path / "video_frames"

    async def initialize(self) -> None:
        """Initialize directory structure."""
        try:
            logger.info("Initializing mask directory structure", foreground_base_path=str(self.foreground_mask_base_path))

            # Create directories in executor to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._create_directories)

            logger.info("Mask directories created successfully")

        except Exception as e:
            logger.error("Failed to create mask directories", error=str(e))
            raise

    def _create_directories(self) -> None:
        """Create mask directory structure."""
        self.foreground_mask_base_path.mkdir(parents=True, exist_ok=True)
        self.foreground_products_dir.mkdir(parents=True, exist_ok=True)
        self.foreground_frames_dir.mkdir(parents=True, exist_ok=True)

        self.people_mask_base_path.mkdir(parents=True, exist_ok=True)
        self.people_products_dir.mkdir(parents=True, exist_ok=True)
        self.people_frames_dir.mkdir(parents=True, exist_ok=True)

        self.product_mask_base_path.mkdir(parents=True, exist_ok=True)
        self.product_products_dir.mkdir(parents=True, exist_ok=True)
        self.product_frames_dir.mkdir(parents=True, exist_ok=True)

    async def _ensure_directory_exists(self, directory: Path) -> None:
        """Ensure a directory exists before using it.

        Args:
            directory: Directory path to ensure exists
        """
        if not directory.exists():
            logger.info("Creating missing directory", directory=str(directory))
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, directory.mkdir, True, True)
            logger.debug("Directory created successfully", directory=str(directory))

    async def save_product_mask(self, image_id: str, mask: np.ndarray) -> str:
        """Save product image foreground mask."""
        return await self._save_mask(self.foreground_products_dir, image_id, mask)

    async def save_frame_mask(self, frame_id: str, mask: np.ndarray) -> str:
        """Save video frame foreground mask."""
        return await self._save_mask(self.foreground_frames_dir, frame_id, mask)

    async def save_people_mask(self, image_id: str, mask: np.ndarray, image_type: str) -> str:
        """Save people mask."""
        if image_type == "product":
            return await self._save_mask(self.people_products_dir, image_id, mask)
        else:  # frame
            return await self._save_mask(self.people_frames_dir, image_id, mask)

    async def save_product_final_mask(self, image_id: str, mask: np.ndarray, image_type: str) -> str:
        """Save final product mask (foreground - people)."""
        if image_type == "product":
            return await self._save_mask(self.product_products_dir, image_id, mask)
        else:  # frame
            return await self._save_mask(self.product_frames_dir, image_id, mask)

    async def _save_mask(self, base_dir: Path, image_id: str, mask: np.ndarray) -> str:
        mask_filename = f"{image_id}.png"
        mask_path = base_dir / mask_filename

        try:
            # Ensure the directory exists before saving
            await self._ensure_directory_exists(base_dir)

            logger.debug("Saving mask", image_id=image_id, path=str(mask_path))
            await self._save_mask_atomic(mask, mask_path)
            logger.debug("Mask saved successfully", image_id=image_id)
            return str(mask_path)
        except Exception as e:
            logger.error("Failed to save mask", image_id=image_id, error=str(e))
            raise

    async def _save_mask_atomic(self, mask: np.ndarray, target_path: Path) -> None:
        """Save mask atomically using temporary file.

        Args:
            mask: Binary mask as numpy array
            target_path: Final path for the mask file
        """
        # Create temporary file in the same directory as target
        temp_dir = target_path.parent

        loop = asyncio.get_event_loop()

        # Save to temporary file first
        with tempfile.NamedTemporaryFile(
            dir=temp_dir,
            suffix='.png',
            delete=False
        ) as temp_file:
            temp_path = temp_file.name

        try:
            # Save mask to temporary file in executor
            await loop.run_in_executor(
                None,
                self._save_mask_to_file,
                mask,
                temp_path
            )

            # Atomically move to final location
            await loop.run_in_executor(
                None,
                shutil.move,
                temp_path,
                str(target_path)
            )

        except Exception:
            # Clean up temporary file on error
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise

    def _save_mask_to_file(self, mask: np.ndarray, file_path: str) -> None:
        """Save mask array to file.

        Args:
            mask: Binary mask as numpy array
            file_path: Path to save the mask
        """
        prepared_mask = self._normalize_and_prepare_mask_for_save(mask)
        mask_image = Image.fromarray(prepared_mask, mode='L')
        mask_image.save(file_path, 'PNG', optimize=True)

    def _normalize_and_prepare_mask_for_save(self, mask: np.ndarray) -> np.ndarray:
        # Ensure values are clipped to 0-255 range first
        mask = np.clip(mask, 0, 255)

        # Ensure mask is in correct format (0-255 uint8)
        if mask.dtype != np.uint8:
            mask = mask.astype(np.uint8)

        # Ensure values are 0 or 255 (values >= 128 become 255)
        mask = np.where(mask >= 128, 255, 0).astype(np.uint8)

        # Squeeze the mask to remove single-dimensional entries (e.g., (H, W, 1) -> (H, W))
        if mask.ndim == 3 and mask.shape[2] == 1:
            mask = mask.squeeze(axis=2)
        return mask

    async def mask_exists(self, mask_path: str) -> bool:
        """Check if mask file exists.

        Args:
            mask_path: Path to mask file

        Returns:
            True if mask file exists and is readable
        """
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                lambda: os.path.isfile(mask_path) and os.access(mask_path, os.R_OK)
            )
        except Exception:
            return False

    async def get_mask_size(self, mask_path: str) -> Optional[tuple]:
        """Get mask file dimensions.

        Args:
            mask_path: Path to mask file

        Returns:
            (width, height) tuple or None if file cannot be read
        """
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                self._get_image_size,
                mask_path
            )
        except Exception as e:
            logger.error("Failed to get mask size", path=mask_path, error=str(e))
            return None

    def _get_image_size(self, image_path: str) -> tuple:
        """Get image dimensions."""
        with Image.open(image_path) as img:
            return img.size

    def get_product_mask_path(self, image_id: str) -> str:
        """Get expected path for product mask.

        Args:
            image_id: Image identifier

        Returns:
            Expected mask file path
        """
        return str(self.product_products_dir / f"{image_id}.png")

    def get_frame_mask_path(self, frame_id: str) -> str:
        """Get expected path for frame mask.

        Args:
            frame_id: Frame identifier

        Returns:
            Expected mask file path
        """
        return str(self.product_frames_dir / f"{frame_id}.png")
