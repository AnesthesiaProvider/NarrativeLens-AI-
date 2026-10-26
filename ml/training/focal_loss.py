"""Class-weighted Focal Loss for PyTorch classification tasks.

Focal Loss dynamically scales the cross-entropy loss based on model confidence,
putting higher gradient weight on hard, borderline instances (e.g. offensive vs hate speech)
while preventing easily classified normal examples from dominating optimization.

Reference:
    Lin et al., "Focal Loss for Dense Object Detection", ICCV 2017.
    Formula: FL(p_t) = -alpha_t * (1 - p_t)^gamma * log(p_t)
"""

from __future__ import annotations

from typing import Optional
import torch
import torch.nn as nn
import torch.nn.functional as F


class FocalLoss(nn.Module):
    """Multi-class Focal Loss with optional class weighting."""

    def __init__(
        self,
        gamma: float = 2.0,
        weight: Optional[torch.Tensor] = None,
        reduction: str = "mean",
    ) -> None:
        """Initialize Focal Loss.

        Args:
            gamma: Focusing parameter. Higher gamma increases the penalty on hard examples.
                   Standard value is 2.0.
            weight: Optional class weights tensor of shape (num_classes,).
            reduction: Reduction mode ('mean', 'sum', or 'none').
        """
        super().__init__()
        self.gamma = gamma
        self.weight = weight
        self.reduction = reduction

    def forward(self, inputs: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        """Compute the focal loss.

        Args:
            inputs: Logits tensor of shape (batch_size, num_classes).
            targets: Ground-truth class index tensor of shape (batch_size,).

        Returns:
            Scalar loss tensor if reduction is 'mean' or 'sum'.
        """
        # Calculate standard log-softmax probabilities
        log_probs = F.log_softmax(inputs, dim=-1)
        probs = torch.exp(log_probs)

        # Gather probability of true target class
        target_log_probs = log_probs.gather(dim=-1, index=targets.unsqueeze(1)).squeeze(1)
        target_probs = probs.gather(dim=-1, index=targets.unsqueeze(1)).squeeze(1)

        # Modulating factor: (1 - p_t)^gamma
        focal_weight = torch.pow(1.0 - target_probs, self.gamma)

        # Base focal loss
        loss = -focal_weight * target_log_probs

        # Apply class weights if provided
        if self.weight is not None:
            if self.weight.device != inputs.device:
                self.weight = self.weight.to(inputs.device)
            class_weights = self.weight.gather(dim=0, index=targets)
            loss = loss * class_weights

        if self.reduction == "mean":
            return loss.mean()
        elif self.reduction == "sum":
            return loss.sum()
        return loss
