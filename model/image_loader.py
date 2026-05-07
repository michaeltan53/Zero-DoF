"""
Image Data Loader
Loads real images and prepares them for authentication evaluation
"""

import os
from typing import List, Tuple, Dict, Any, Optional, Callable
import numpy as np
from PIL import Image
import glob


class ImageDataset:
    """
    Dataset loader for real images.
    
    Supports loading images from directories with labels.
    """
    
    def __init__(
        self,
        image_dir: str,
        label_file: Optional[str] = None,
        image_extensions: List[str] = None,
        preprocess_fn: Optional[Callable] = None
    ):
        """
        Initialize image dataset.
        
        Args:
            image_dir: Directory containing images
            label_file: Optional CSV/JSON file with labels (columns: image_path, label)
            image_extensions: List of image extensions to load (default: ['.jpg', '.png', '.jpeg'])
            preprocess_fn: Optional preprocessing function (image -> image)
        """
        self.image_dir = image_dir
        self.label_file = label_file
        self.image_extensions = image_extensions or ['.jpg', '.png', '.jpeg', '.bmp']
        self.preprocess_fn = preprocess_fn
        
        self.images: List[Dict[str, Any]] = []
        self._load_images()
    
    def _load_images(self):
        """Load images from directory."""
        # Load labels if provided
        labels_dict = {}
        if self.label_file:
            import pandas as pd
            if self.label_file.endswith('.csv'):
                df = pd.read_csv(self.label_file)
                for _, row in df.iterrows():
                    img_path = row.get('image_path', row.get('path', ''))
                    label = row.get('label', row.get('class', ''))
                    labels_dict[img_path] = label
            elif self.label_file.endswith('.json'):
                import json
                with open(self.label_file, 'r') as f:
                    data = json.load(f)
                    labels_dict = data
        
        # Find all images
        image_paths = []
        for ext in self.image_extensions:
            pattern = os.path.join(self.image_dir, f'**/*{ext}')
            image_paths.extend(glob.glob(pattern, recursive=True))
            pattern = os.path.join(self.image_dir, f'**/*{ext.upper()}')
            image_paths.extend(glob.glob(pattern, recursive=True))
        
        # Load images
        for img_path in image_paths:
            rel_path = os.path.relpath(img_path, self.image_dir)
            label = labels_dict.get(rel_path, labels_dict.get(img_path, None))
            
            if label is None:
                # Try to infer from directory structure
                parts = rel_path.split(os.sep)
                if len(parts) > 1:
                    label = parts[0]  # Use first directory as label
            
            self.images.append({
                'path': img_path,
                'rel_path': rel_path,
                'label': self._normalize_label(label) if label else None
            })
    
    def _normalize_label(self, label: str) -> str:
        """Normalize label to Pos/Neg."""
        label_lower = str(label).lower()
        if label_lower in ['pos', 'positive', '1', 'true', 'accept', 'genuine']:
            return 'Pos'
        elif label_lower in ['neg', 'negative', '0', 'false', 'reject', 'spoof', 'fake']:
            return 'Neg'
        return label  # Return as-is if unclear
    
    def load_image(self, idx: int) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Load image by index.
        
        Args:
            idx: Image index
            
        Returns:
            (image_array, metadata) tuple
        """
        img_info = self.images[idx]
        img_path = img_info['path']
        
        # Load image
        img = Image.open(img_path)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        img_array = np.array(img)
        
        # Apply preprocessing if provided
        if self.preprocess_fn:
            img_array = self.preprocess_fn(img_array)
        
        metadata = {
            'path': img_path,
            'rel_path': img_info['rel_path'],
            'label': img_info['label'],
            'size': img_array.shape
        }
        
        return img_array, metadata
    
    def __len__(self):
        return len(self.images)
    
    def __getitem__(self, idx):
        return self.load_image(idx)


class ImageDataGenerator:
    """
    Generator for image evaluation data.
    
    Processes images through authenticator and generates evaluation records.
    """
    
    def __init__(
        self,
        dataset: ImageDataset,
        authenticator: 'ImageAuthenticator',
        tau_computer: Optional['TierATauComputer'] = None
    ):
        """
        Initialize image data generator.
        
        Args:
            dataset: ImageDataset instance
            authenticator: ImageAuthenticator instance
            tau_computer: Optional TierATauComputer for Tier-A tau computation
        """
        self.dataset = dataset
        self.authenticator = authenticator
        self.tau_computer = tau_computer
    
    def generate_evaluation_data(
        self,
        indices: Optional[List[int]] = None,
        use_tier_a_tau: bool = False,
        tau_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate evaluation data from images.
        
        Args:
            indices: Optional list of image indices to process (None = all)
            use_tier_a_tau: If True, use Tier-A tau computation (requires tau_metadata)
            tau_metadata: Optional metadata for Tier-A tau (e.g., LWC, r_eff)
            
        Returns:
            List of evaluation records, each containing:
            {
                'id': sample_id,
                'image': image_array,
                'tau': tau_value,
                'label': 'Pos' or 'Neg',
                'decision': 'ACCEPT'/'REJECT'/'FAIL-SAFE',
                'score': confidence_score,
                'metadata': {...}
            }
        """
        if indices is None:
            indices = list(range(len(self.dataset)))
        
        records = []
        
        for idx in indices:
            # Load image
            image, metadata = self.dataset.load_image(idx)
            
            # Compute tau
            if use_tier_a_tau and self.tau_computer and tau_metadata:
                # Tier-A: Use physical parameters
                lwc = tau_metadata.get('lwc', 0.0)
                r_eff = tau_metadata.get('r_eff', 1e-6)
                tau = self.tau_computer.compute_tau_eff_from_fog(lwc, r_eff, tau_metadata)
            else:
                # Use authenticator's tau computation (may be Tier-B or dummy)
                tau = self.authenticator.compute_tau(image, metadata)
            
            # Authenticate
            decision, score = self.authenticator.authenticate(image, metadata)
            
            # Create record
            record = {
                'id': f"img_{idx}_{metadata['rel_path']}",
                'image': image,
                'tau': tau,
                'label': metadata.get('label', 'Unknown'),
                'decision': decision,
                'score': score,
                'metadata': metadata
            }
            
            records.append(record)
        
        return records


def create_image_dataset_from_directory(
    image_dir: str,
    label_mapping: Optional[Dict[str, str]] = None
) -> ImageDataset:
    """
    Convenience function to create ImageDataset from directory.
    
    Args:
        image_dir: Directory containing images
        label_mapping: Optional dict mapping subdirectory names to labels
        
    Returns:
        ImageDataset instance
    """
    return ImageDataset(image_dir, preprocess_fn=None)
