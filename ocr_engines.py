"""
OCR Engines Module - HYBRID STRATEGY
✅ Tesseract for Left Region
✅ EasyOCR for Right Region
"""

import cv2
import numpy as np
import pytesseract
from typing import Dict, Optional

# EasyOCR
try:
    import easyocr
    EASYOCR_AVAILABLE = True
    _reader = None
except ImportError:
    EASYOCR_AVAILABLE = False
    _reader = None


def get_easyocr_reader():
    """Get or initialize EasyOCR reader (lazy loading)"""
    global _reader
    if _reader is None and EASYOCR_AVAILABLE:
        try:
            _reader = easyocr.Reader(['en'], gpu=False, verbose=False)
        except Exception as e:
            print(f'Warning: Could not initialize EasyOCR: {e}')
    return _reader


def ocr_tesseract(image: np.ndarray) -> str:
    """
    Tesseract OCR
    ✅ Best for: Left Region (white background)
    """
    try:
        config = '--psm 6 --oem 3'
        text = pytesseract.image_to_string(image, lang='eng', config=config)
        return text.strip()
    except Exception as e:
        return f'Tesseract Error: {e}'


def ocr_easyocr(image: np.ndarray) -> str:
    """
    EasyOCR
    ✅ Best for: Right Region (dark background, rotated)
    """
    try:
        reader = get_easyocr_reader()
        if reader is None:
            return 'EasyOCR not available'
        
        # Read text
        results = reader.readtext(image, detail=0, paragraph=True)
        text = ' '.join(results)
        return text.strip()
    except Exception as e:
        return f'EasyOCR Error: {e}'


def ocr_hybrid(left_image: np.ndarray, right_image: np.ndarray) -> Dict[str, str]:
    """
    🏆 HYBRID STRATEGY (RECOMMENDED)
    
    Uses best OCR engine for each region:
    - Tesseract for Left (faster, accurate on white background)
    - EasyOCR for Right (better with rotated/dark text)
    
    Args:
        left_image: Preprocessed left region
        right_image: Preprocessed right region
    
    Returns:
        {
            'left_text': '...',
            'right_text': '...',
            'left_engine': 'tesseract',
            'right_engine': 'easyocr'
        }
    """
    print('\n🔍 OCR Processing (Hybrid Strategy)...')
    
    # Left: Tesseract (fast & accurate)
    print('   📄 Left region → Tesseract...')
    left_text = ocr_tesseract(left_image)
    
    # Right: EasyOCR (better performance)
    print('   📄 Right region → EasyOCR...')
    right_text = ocr_easyocr(right_image)
    
    return {
        'left_text': left_text,
        'right_text': right_text,
        'left_engine': 'tesseract',
        'right_engine': 'easyocr'
    }


def ocr_tesseract_only(left_image: np.ndarray, right_image: np.ndarray) -> Dict[str, str]:
    """
    Tesseract-only approach (fallback)
    ⚠️ Right region may have poor accuracy
    """
    print('\n🔍 OCR Processing (Tesseract only)...')
    
    left_text = ocr_tesseract(left_image)
    right_text = ocr_tesseract(right_image)
    
    return {
        'left_text': left_text,
        'right_text': right_text,
        'left_engine': 'tesseract',
        'right_engine': 'tesseract'
    }


def ocr_easyocr_only(left_image: np.ndarray, right_image: np.ndarray) -> Dict[str, str]:
    """
    EasyOCR-only approach (slower but consistent)
    """
    print('\n🔍 OCR Processing (EasyOCR only)...')
    
    left_text = ocr_easyocr(left_image)
    right_text = ocr_easyocr(right_image)
    
    return {
        'left_text': left_text,
        'right_text': right_text,
        'left_engine': 'easyocr',
        'right_engine': 'easyocr'
    }


def clean_ocr_text(text: str) -> str:
    """
    Clean OCR output
    - Remove extra whitespace
    - Fix common OCR errors
    """
    import re
    
    # Remove multiple spaces
    text = re.sub(r'\s+', ' ', text)
    
    # Common OCR fixes
    text = text.replace('|', 'I')  # Pipe → I
    text = text.replace('0', 'O') if text.isupper() else text  # Context-aware
    
    return text.strip()