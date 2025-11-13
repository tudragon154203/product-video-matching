"""
Create mock keypoint fixture files for testing.
Generates .npz files with dummy keypoint data that can be loaded by the matching service.
"""

import numpy as np
from pathlib import Path


def create_mock_keypoints_file(file_path: str, num_keypoints: int = 100):
    """Create a mock .npz file with keypoint data."""
    # Generate random keypoint data
    keypoints = np.random.rand(num_keypoints, 2) * 100  # x, y coordinates
    descriptors = np.random.rand(num_keypoints, 32) * 255  # 32-dimensional descriptors
    scores = np.random.rand(num_keypoints)  # confidence scores

    # Save as .npz file
    np.savez_compressed(
        file_path,
        keypoints=keypoints,
        descriptors=descriptors,
        scores=scores
    )


def create_all_keypoint_fixtures():
    """Create all keypoint fixture files needed for tests."""
    keypoints_dir = Path("O:/product-video-matching/implement-matcher/data/tests/keypoints")
    keypoints_dir.mkdir(exist_ok=True)

    # Create product keypoint files
    for i in range(1, 4):
        file_path = keypoints_dir / f"product_{i:03d}_keypoints.npz"
        create_mock_keypoints_file(str(file_path), num_keypoints=50 + i * 10)
        print(f"Created {file_path}")

    # Create frame keypoint files
    for i in range(1, 4):
        file_path = keypoints_dir / f"frame_{i:03d}_keypoints.npz"
        create_mock_keypoints_file(str(file_path), num_keypoints=80 + i * 5)
        print(f"Created {file_path}")


if __name__ == "__main__":
    create_all_keypoint_fixtures()
    print("All keypoint fixtures created successfully!")
