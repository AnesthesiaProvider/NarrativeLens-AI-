"""OCR service for meme and image text extraction using EasyOCR."""

from __future__ import annotations

import io
import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


class OCRService:
    """Manages lazy-loaded OCR extraction with GPU acceleration."""

    def __init__(self) -> None:
        self._reader: Optional[Any] = None
        self._device: str = "cuda"

    def _get_reader(self) -> Optional[Any]:
        """Lazy load EasyOCR reader on demand."""
        if self._reader is not None:
            return self._reader

        try:
            import easyocr
            import torch

            use_gpu = torch.cuda.is_available()
            self._device = "cuda" if use_gpu else "cpu"
            logger.info(f"Initializing EasyOCR reader on {self._device}...")
            # We support English, and can add Hindi / Latin if needed
            self._reader = easyocr.Reader(["en"], gpu=use_gpu, verbose=False)
            logger.info("EasyOCR initialized successfully.")
            return self._reader
        except Exception as exc:
            logger.error(f"Failed to initialize EasyOCR: {exc}")
            return None

    def extract_text(self, image_bytes: bytes) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Extract text from raw image bytes.
        Returns:
            (combined_text, list_of_detected_boxes_with_confidences)
        """
        if not image_bytes:
            return "", []

        try:
            pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            np_img = np.array(pil_img)
        except Exception as exc:
            logger.warning(f"Could not decode image bytes for OCR: {exc}")
            return "", []

        reader = self._get_reader()
        if reader is None:
            return "", []

        try:
            # detail=1 gives (bbox, text, confidence)
            results = reader.readtext(np_img, detail=1)
            segments: List[Dict[str, Any]] = []
            extracted_lines: List[str] = []

            for item in results:
                if len(item) >= 3:
                    bbox, text, conf = item[0], item[1], float(item[2])
                    cleaned = text.strip()
                    if cleaned:
                        extracted_lines.append(cleaned)
                        segments.append({
                            "text": cleaned,
                            "confidence": round(conf, 4),
                            "box": [[int(p[0]), int(p[1])] for p in bbox] if isinstance(bbox, list) else None,
                        })

            merged_text = " ".join(extracted_lines)
            return merged_text, segments
        except Exception as exc:
            logger.warning(f"Error during OCR text extraction: {exc}")
            return "", []


ocr_service = OCRService()
