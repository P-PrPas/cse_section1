"""
Image enhancement utilities for handling harsh lighting conditions.
Applies CLAHE (Contrast Limited Adaptive Histogram Equalization) to improve
face detection in webcam frames with glare, shadows, or washed-out areas.
"""

import cv2
import numpy as np


def apply_clahe(image: np.ndarray, clip_limit: float = 2.0,
                grid_size: tuple = (8, 8)) -> np.ndarray:
    """
    Apply CLAHE enhancement to an image to improve contrast.
    
    Converts to LAB color space, applies CLAHE on the L (lightness) channel,
    then converts back to BGR. This enhances local contrast without
    over-amplifying noise.
    
    Args:
        image: BGR image (numpy array).
        clip_limit: CLAHE clip limit for contrast limiting.
        grid_size: Tile grid size for CLAHE.
    
    Returns:
        Enhanced BGR image.
    """
    if image is None or image.size == 0:
        return image

    # Convert BGR -> LAB
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)

    # Apply CLAHE to L channel
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=grid_size)
    enhanced_l = clahe.apply(l_channel)

    # Merge and convert back
    merged = cv2.merge([enhanced_l, a_channel, b_channel])
    enhanced = cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)

    return enhanced
