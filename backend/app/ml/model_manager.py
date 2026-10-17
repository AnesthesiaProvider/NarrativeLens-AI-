"""ModelManager for lazy-loading, device selection, caching, and lifecycle management of ML models."""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.schemas.common import ModelStatusItem, ModelStatusResponse

logger = logging.getLogger(__name__)


class ModelManager:
    """
    Manages ML model lifecycle:
    - Lazy loading
    - Device selection (cuda/cpu/auto)
    - Loading/unloading models
    - Memory tracking
    - Model status reporting
    """

    def __init__(self) -> None:
        self.device_str = self._resolve_device(settings.DEVICE)
        self.cache_dir = settings.MODEL_CACHE_DIR
        self._models: Dict[str, Any] = {}
        self._tokenizers: Dict[str, Any] = {}
        initial_hate_model = (
            settings.CLASSIFIER_CHECKPOINT_PATH
            if (settings.CLASSIFIER_CHECKPOINT_PATH and os.path.exists(settings.CLASSIFIER_CHECKPOINT_PATH))
            else settings.HATE_SPEECH_MODEL_ID
        )
        self._model_metadata: Dict[str, Dict[str, Any]] = {
            "hate_speech": {
                "model_id": initial_hate_model,
                "model_type": "hate_speech",
                "status": "uninitialized",
                "device": self.device_str,
                "memory_mb": 0.0,
                "loaded_at": None,
            },
            "embedding": {
                "model_id": settings.EMBEDDING_MODEL_ID,
                "model_type": "embedding",
                "status": "uninitialized",
                "device": self.device_str,
                "memory_mb": 0.0,
                "loaded_at": None,
            },
            "multimodal": {
                "model_id": settings.MULTIMODAL_MODEL_ID,
                "model_type": "multimodal",
                "status": "uninitialized",
                "device": self.device_str,
                "memory_mb": 0.0,
                "loaded_at": None,
            },
        }

    def _resolve_device(self, configured_device: str) -> str:
        """Resolve device to cuda or cpu based on configuration and hardware availability."""
        if configured_device.lower() == "auto":
            try:
                import torch
                if torch.cuda.is_available():
                    return "cuda"
            except ImportError:
                pass
            return "cpu"
        elif configured_device.lower().startswith("cuda"):
            try:
                import torch
                if torch.cuda.is_available():
                    return configured_device.lower()
            except ImportError:
                pass
            logger.warning("CUDA requested but not available. Falling back to CPU.")
            return "cpu"
        return "cpu"

    def get_memory_usage(self) -> Dict[str, float]:
        """Track current device memory usage in MB."""
        memory_stats: Dict[str, float] = {"ram_mb": 0.0, "gpu_mb": 0.0}

        # Check process RAM
        try:
            import psutil
            process = psutil.Process(os.getpid())
            memory_stats["ram_mb"] = round(process.memory_info().rss / (1024 * 1024), 2)
        except Exception:
            pass

        # Check CUDA GPU memory
        if self.device_str.startswith("cuda"):
            try:
                import torch
                if torch.cuda.is_available():
                    memory_stats["gpu_mb"] = round(
                        torch.cuda.memory_allocated() / (1024 * 1024), 2
                    )
            except Exception:
                pass

        return memory_stats

    def load_model(self, model_key: str) -> bool:
        """
        Lazily load a specific model by key ('hate_speech', 'embedding', 'multimodal').
        Returns True if loaded successfully, False otherwise.
        """
        if model_key in self._models and self._models[model_key] is not None:
            return True

        if model_key not in self._model_metadata:
            logger.error(f"Unknown model key requested: {model_key}")
            return False

        meta = self._model_metadata[model_key]
        model_id = meta["model_id"]
        meta["status"] = "loading"

        try:
            if model_key == "hate_speech":
                from transformers import AutoModelForSequenceClassification, AutoTokenizer

                checkpoint_path = getattr(settings, "CLASSIFIER_CHECKPOINT_PATH", "")
                if checkpoint_path and os.path.exists(checkpoint_path):
                    target_model = checkpoint_path
                    logger.info(f"Loading fine-tuned hate speech model from checkpoint '{target_model}' on {self.device_str}...")
                else:
                    target_model = settings.HATE_SPEECH_MODEL_ID
                    logger.info(f"Loading base hate speech model '{target_model}' on {self.device_str}...")

                meta["model_id"] = target_model
                tokenizer = AutoTokenizer.from_pretrained(target_model, cache_dir=self.cache_dir)
                try:
                    model = AutoModelForSequenceClassification.from_pretrained(
                        target_model, cache_dir=self.cache_dir
                    )
                except Exception:
                    id2label = {i: lbl for i, lbl in enumerate(settings.CLASSIFIER_LABELS)}
                    label2id = {lbl: i for i, lbl in id2label.items()}
                    model = AutoModelForSequenceClassification.from_pretrained(
                        target_model,
                        cache_dir=self.cache_dir,
                        num_labels=settings.CLASSIFIER_NUM_LABELS,
                        id2label=id2label,
                        label2id=label2id,
                    )

                # Ensure id2label is properly standardized
                if not hasattr(model.config, "id2label") or not model.config.id2label:
                    model.config.id2label = {i: lbl for i, lbl in enumerate(settings.CLASSIFIER_LABELS)}
                    model.config.label2id = {lbl: i for i, lbl in model.config.id2label.items()}
                elif any("LABEL_" in str(v) for v in model.config.id2label.values()):
                    if len(model.config.id2label) == len(settings.CLASSIFIER_LABELS):
                        model.config.id2label = {i: lbl for i, lbl in enumerate(settings.CLASSIFIER_LABELS)}
                        model.config.label2id = {lbl: i for i, lbl in model.config.id2label.items()}

                model.to(self.device_str)
                model.eval()

                self._models[model_key] = model
                self._tokenizers[model_key] = tokenizer

            elif model_key == "embedding":
                from sentence_transformers import SentenceTransformer
                logger.info(f"Loading embedding model '{model_id}' on {self.device_str}...")
                model = SentenceTransformer(model_id, cache_folder=self.cache_dir, device=self.device_str)
                self._models[model_key] = model

            elif model_key == "multimodal":
                from transformers import AutoProcessor, AutoModelForZeroShotImageClassification
                logger.info(f"Loading multimodal model '{model_id}' on {self.device_str}...")
                processor = AutoProcessor.from_pretrained(model_id, cache_dir=self.cache_dir)
                model = AutoModelForZeroShotImageClassification.from_pretrained(
                    model_id, cache_dir=self.cache_dir
                )
                model.to(self.device_str)
                model.eval()

                self._models[model_key] = model
                self._tokenizers[model_key] = processor

            meta["status"] = "ready"
            meta["loaded_at"] = datetime.now(timezone.utc)
            mem = self.get_memory_usage()
            meta["memory_mb"] = mem["gpu_mb"] if self.device_str == "cuda" else mem["ram_mb"]
            logger.info(f"Model '{model_key}' successfully loaded.")
            return True

        except Exception as exc:
            logger.warning(
                f"Could not load ML model '{model_key}' ({model_id}): {exc}. "
                "The server will continue in fallback mode."
            )
            meta["status"] = f"unavailable: {str(exc)[:100]}"
            return False

    def unload_model(self, model_key: str) -> bool:
        """Unload a model from memory and free GPU/RAM cache."""
        if model_key in self._models:
            del self._models[model_key]
            if model_key in self._tokenizers:
                del self._tokenizers[model_key]

            # Clear PyTorch CUDA cache if applicable
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except Exception:
                pass

            if model_key in self._model_metadata:
                self._model_metadata[model_key]["status"] = "uninitialized"
                self._model_metadata[model_key]["loaded_at"] = None
                self._model_metadata[model_key]["memory_mb"] = 0.0

            logger.info(f"Model '{model_key}' unloaded successfully.")
            return True
        return False

    def is_model_ready(self, model_key: str) -> bool:
        """Check if a model is currently loaded in memory and ready."""
        return model_key in self._models and self._models[model_key] is not None

    def get_model(self, model_key: str) -> Optional[Any]:
        """Get model instance if ready, attempting lazy load if not."""
        if not self.is_model_ready(model_key):
            self.load_model(model_key)
        return self._models.get(model_key)

    def get_tokenizer(self, model_key: str) -> Optional[Any]:
        """Get tokenizer/processor instance for the given model key."""
        if not self.is_model_ready(model_key):
            self.load_model(model_key)
        return self._tokenizers.get(model_key)

    def _explain_prediction(
        self,
        model: Any,
        tokenizer: Any,
        text: str,
        predicted_idx: int,
    ) -> Optional[Dict[str, Any]]:
        """
        Compute real token attribution using Captum LayerIntegratedGradients.
        Falls back to gradient of predicted class w.r.t input embeddings if Captum is unavailable.
        """
        try:
            import torch

            inputs = tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=settings.MAX_SEQUENCE_LENGTH,
                padding=False,
            )
            input_ids = inputs["input_ids"].to(self.device_str)
            attention_mask = inputs.get("attention_mask")
            if attention_mask is not None:
                attention_mask = attention_mask.to(self.device_str)

            token_ids = input_ids[0].tolist()
            tokens = [tokenizer.decode([tid]).strip() for tid in token_ids]
            special_tokens = {
                getattr(tokenizer, "cls_token", "[CLS]"),
                getattr(tokenizer, "sep_token", "[SEP]"),
                getattr(tokenizer, "pad_token", "<pad>"),
                getattr(tokenizer, "unk_token", "<unk>"),
                "<s>",
                "</s>",
                "<pad>",
                "",
            }

            attribution_scores = None
            attribution_method = "captum_layer_integrated_gradients"

            # 1. Attempt Captum LayerIntegratedGradients
            try:
                from captum.attr import LayerIntegratedGradients

                embedding_layer = None
                if hasattr(model, "get_input_embeddings"):
                    embedding_layer = model.get_input_embeddings()
                elif hasattr(model, "roberta") and hasattr(model.roberta, "embeddings"):
                    embedding_layer = model.roberta.embeddings.word_embeddings

                if embedding_layer is not None:
                    def forward_func(inp, mask=None):
                        out = model(input_ids=inp, attention_mask=mask)
                        return out.logits

                    lig = LayerIntegratedGradients(forward_func, embedding_layer)
                    attributions = lig.attribute(
                        inputs=input_ids,
                        additional_forward_args=(attention_mask,) if attention_mask is not None else None,
                        target=predicted_idx,
                        n_steps=20,
                    )
                    # L2 norm across embedding dimension
                    token_norms = torch.norm(attributions.squeeze(0), dim=-1)
                    attribution_scores = token_norms.detach().cpu().numpy()
            except Exception as captum_err:
                logger.info(f"Captum attribution unavailable or failed ({captum_err}); falling back to input gradient.")
                attribution_scores = None

            # 2. Fallback: Gradient w.r.t input embeddings
            if attribution_scores is None:
                attribution_method = "gradient_input_embeddings"
                try:
                    embedding_layer = (
                        model.get_input_embeddings()
                        if hasattr(model, "get_input_embeddings")
                        else None
                    )
                    if embedding_layer is not None:
                        embeds = embedding_layer(input_ids).clone().detach().requires_grad_(True)
                        outputs = model(inputs_embeds=embeds, attention_mask=attention_mask)
                        logits = outputs.logits
                        target_logit = logits[0, predicted_idx]
                        model.zero_grad()
                        target_logit.backward()
                        if embeds.grad is not None:
                            token_norms = torch.norm(embeds.grad.squeeze(0), dim=-1)
                            attribution_scores = token_norms.detach().cpu().numpy()
                except Exception as grad_err:
                    logger.warning(f"Gradient attribution fallback failed: {grad_err}")
                    attribution_scores = None

            # Process scores into token-level attribution rankings
            if attribution_scores is not None and len(attribution_scores) == len(tokens):
                import numpy as np

                max_score = float(np.max(attribution_scores)) if len(attribution_scores) > 0 else 1.0
                norm_scores = (
                    (attribution_scores / max_score).tolist()
                    if max_score > 0
                    else attribution_scores.tolist()
                )

                all_features = []
                for tok, sc in zip(tokens, norm_scores):
                    if tok and tok not in special_tokens and not tok.isspace():
                        all_features.append({"token": tok, "score": round(float(sc), 4)})

                # Sort top features descending
                ranked = sorted(all_features, key=lambda x: x["score"], reverse=True)
                return {
                    "tokens": tokens,
                    "method": attribution_method,
                    "top_features": ranked[:8],
                    "all_token_attributions": all_features,
                }
        except Exception as exc:
            logger.warning(f"Error computing token attribution: {exc}")

        return None

    def predict_hate_speech(
        self, text: str, explain: bool = False
    ) -> Dict[str, Any]:
        """
        Run hate speech inference on text with 3 classes: normal, offensive, hate.
        Uses fine-tuned checkpoint if available, falling back to base model or rule-based heuristic.
        """
        model = self.get_model("hate_speech")
        tokenizer = self.get_tokenizer("hate_speech")

        if model is not None and tokenizer is not None:
            try:
                import torch

                inputs = tokenizer(
                    text,
                    return_tensors="pt",
                    truncation=True,
                    max_length=settings.MAX_SEQUENCE_LENGTH,
                    padding=True,
                )
                inputs = {k: v.to(self.device_str) for k, v in inputs.items()}

                with torch.no_grad():
                    outputs = model(**inputs)
                    probs = torch.nn.functional.softmax(outputs.logits, dim=-1).squeeze().tolist()

                if isinstance(probs, float):
                    probs = [1.0 - probs, probs]

                # Use actual id2label from model.config
                raw_id2label = getattr(model.config, "id2label", None)
                if not raw_id2label or any("LABEL_" in str(v) for v in raw_id2label.values()):
                    id2label = {i: lbl for i, lbl in enumerate(settings.CLASSIFIER_LABELS)}
                else:
                    id2label = {int(k): str(v) for k, v in raw_id2label.items()}

                class_probs = {
                    id2label.get(i, f"class_{i}"): round(float(prob), 4)
                    for i, prob in enumerate(probs)
                }
                predicted_idx = int(max(range(len(probs)), key=lambda i: probs[i]))
                predicted_label = id2label.get(predicted_idx, "normal")
                confidence = float(probs[predicted_idx])

                explanation_data = None
                if explain:
                    explanation_data = self._explain_prediction(
                        model=model,
                        tokenizer=tokenizer,
                        text=text,
                        predicted_idx=predicted_idx,
                    )

                active_model_id = self._model_metadata["hate_speech"].get(
                    "model_id", settings.HATE_SPEECH_MODEL_ID
                )

                return {
                    "predicted_label": predicted_label,
                    "confidence": round(confidence, 4),
                    "class_probabilities": class_probs,
                    "explanation": explanation_data,
                    "model_id": active_model_id,
                    "is_available": True,
                }
            except Exception as exc:
                logger.warning(f"Error during hate speech model forward pass: {exc}")

        # Fallback heuristic prediction when model weights aren't loaded (clearly labeled)
        lowered = text.lower()
        hate_terms = {"kill", "threat", "attack", "destroy", "scum", "vermin", "subhuman", "genocide"}
        offensive_terms = {"hate", "idiot", "stupid", "dumb", "ugly", "shut up", "crap", "damn", "fool"}

        has_hate = any(term in lowered for term in hate_terms)
        has_offensive = any(term in lowered for term in offensive_terms)

        if has_hate:
            label = "hate"
            conf = 0.85
            probs = {"normal": 0.05, "offensive": 0.15, "hate": 0.80}
        elif has_offensive:
            label = "offensive"
            conf = 0.75
            probs = {"normal": 0.15, "offensive": 0.75, "hate": 0.10}
        else:
            label = "normal"
            conf = 0.90
            probs = {"normal": 0.90, "offensive": 0.08, "hate": 0.02}

        return {
            "predicted_label": label,
            "confidence": conf,
            "class_probabilities": probs,
            "explanation": {
                "method": "heuristic_fallback",
                "note": "ML model not currently loaded in memory; rule-based heuristic baseline used.",
                "status": "model_uninitialized",
            } if explain else None,
            "model_id": f"{settings.HATE_SPEECH_MODEL_ID} (heuristic/standby)",
            "is_available": False,
        }


    def get_status_summary(self) -> ModelStatusResponse:
        """Return the overall status across all registered models."""
        items: List[ModelStatusItem] = []
        loaded_count = 0

        for key, meta in self._model_metadata.items():
            is_loaded = key in self._models and self._models[key] is not None
            if is_loaded:
                loaded_count += 1
                status = "ready"
            else:
                status = meta["status"]

            items.append(
                ModelStatusItem(
                    model_id=meta["model_id"],
                    model_type=meta["model_type"],
                    status=status,
                    device=meta["device"],
                    memory_mb=meta["memory_mb"],
                    loaded_at=meta["loaded_at"],
                )
            )

        overall = "ready" if loaded_count > 0 else "standby"
        return ModelStatusResponse(
            status=overall,
            models=items,
            total_loaded=loaded_count,
            device=self.device_str,
        )


# Global singleton instance
model_manager = ModelManager()
