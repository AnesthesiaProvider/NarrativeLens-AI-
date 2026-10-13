"""SQLAlchemy ORM models for NarrativeLens AI."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Investigation(Base):
    """Investigation entity representing a topic or investigation campaign."""

    __tablename__ = "investigations"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    keywords: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    languages: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    date_range_start: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    date_range_end: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    source_types: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default="active", nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    data_sources: Mapped[List["DataSource"]] = relationship(
        "DataSource", back_populates="investigation", cascade="all, delete-orphan"
    )
    documents: Mapped[List["Document"]] = relationship(
        "Document", back_populates="investigation", cascade="all, delete-orphan"
    )
    narrative_clusters: Mapped[List["NarrativeCluster"]] = relationship(
        "NarrativeCluster", back_populates="investigation", cascade="all, delete-orphan"
    )
    evidence_citations: Mapped[List["EvidenceCitation"]] = relationship(
        "EvidenceCitation", back_populates="investigation", cascade="all, delete-orphan"
    )
    coordination_indicators: Mapped[List["CoordinationIndicator"]] = relationship(
        "CoordinationIndicator",
        back_populates="investigation",
        cascade="all, delete-orphan",
    )


class DataSource(Base):
    """Data source configuration tied to an investigation."""

    __tablename__ = "data_sources"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("investigations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    config: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    investigation: Mapped["Investigation"] = relationship(
        "Investigation", back_populates="data_sources"
    )
    documents: Mapped[List["Document"]] = relationship(
        "Document", back_populates="source", cascade="all, delete-orphan"
    )


class Document(Base):
    """Normalized ingested document for text and multimodal analysis."""

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("investigations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("data_sources.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    author: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), default="text", nullable=False)
    metadata_: Mapped[Dict[str, Any]] = mapped_column(
        "metadata", JSON, default=dict, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    investigation: Mapped["Investigation"] = relationship(
        "Investigation", back_populates="documents"
    )
    source: Mapped[Optional["DataSource"]] = relationship(
        "DataSource", back_populates="documents"
    )
    media_assets: Mapped[List["MediaAsset"]] = relationship(
        "MediaAsset", back_populates="document", cascade="all, delete-orphan"
    )
    classification_results: Mapped[List["ClassificationResult"]] = relationship(
        "ClassificationResult",
        back_populates="document",
        cascade="all, delete-orphan",
    )
    narrative_associations: Mapped[List["NarrativeDocument"]] = relationship(
        "NarrativeDocument", back_populates="document", cascade="all, delete-orphan"
    )
    review_tasks: Mapped[List["ReviewTask"]] = relationship(
        "ReviewTask", back_populates="document", cascade="all, delete-orphan"
    )


class MediaAsset(Base):
    """Media files (images, audio, video) linked to documents."""

    __tablename__ = "media_assets"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    perceptual_hash: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, index=True
    )
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    document: Mapped["Document"] = relationship(
        "Document", back_populates="media_assets"
    )
    ocr_results: Mapped[List["OCRResult"]] = relationship(
        "OCRResult", back_populates="media_asset", cascade="all, delete-orphan"
    )
    classification_results: Mapped[List["ClassificationResult"]] = relationship(
        "ClassificationResult",
        back_populates="media_asset",
        cascade="all, delete-orphan",
    )


class OCRResult(Base):
    """OCR text extracted from image media assets."""

    __tablename__ = "ocr_results"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    media_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("media_assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    extracted_text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    engine: Mapped[str] = mapped_column(String(50), default="tesseract", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    media_asset: Mapped["MediaAsset"] = relationship(
        "MediaAsset", back_populates="ocr_results"
    )


class ClassificationResult(Base):
    """Machine learning predictions and explanations for documents or media."""

    __tablename__ = "classification_results"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    media_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("media_assets.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    model_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    predicted_label: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    class_probabilities: Mapped[Dict[str, float]] = mapped_column(
        JSON, default=dict, nullable=False
    )
    explanation: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    model_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    document: Mapped[Optional["Document"]] = relationship(
        "Document", back_populates="classification_results"
    )
    media_asset: Mapped[Optional["MediaAsset"]] = relationship(
        "MediaAsset", back_populates="classification_results"
    )
    review_tasks: Mapped[List["ReviewTask"]] = relationship(
        "ReviewTask",
        back_populates="classification_result",
        cascade="all, delete-orphan",
    )
    feedbacks: Mapped[List["HumanFeedback"]] = relationship(
        "HumanFeedback",
        back_populates="classification_result",
        cascade="all, delete-orphan",
    )


class ModelRegistry(Base):
    """Registry tracking ML models, versions, checkpoints, and performance."""

    __tablename__ = "model_registry"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    model_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    model_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    checkpoint_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), default="available", nullable=False, index=True
    )
    config: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    metrics: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class NarrativeCluster(Base):
    """Clusters representing cohesive narrative themes discovered across documents."""

    __tablename__ = "narrative_clusters"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("investigations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    representative_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cluster_size: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    investigation: Mapped["Investigation"] = relationship(
        "Investigation", back_populates="narrative_clusters"
    )
    documents: Mapped[List["NarrativeDocument"]] = relationship(
        "NarrativeDocument", back_populates="cluster", cascade="all, delete-orphan"
    )


class NarrativeDocument(Base):
    """Mapping between narrative clusters and associated documents with similarity scores."""

    __tablename__ = "narrative_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    cluster_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("narrative_clusters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    similarity_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Relationships
    cluster: Mapped["NarrativeCluster"] = relationship(
        "NarrativeCluster", back_populates="documents"
    )
    document: Mapped["Document"] = relationship(
        "Document", back_populates="narrative_associations"
    )


class EvidenceCitation(Base):
    """Evidence claims paired with supporting and contradicting sources."""

    __tablename__ = "evidence_citations"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("investigations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    supporting_sources: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON, default=list, nullable=False
    )
    contradicting_sources: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON, default=list, nullable=False
    )
    evidence_status: Mapped[str] = mapped_column(
        String(50), default="unverified", nullable=False
    )
    uncertainty_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    investigation: Mapped["Investigation"] = relationship(
        "Investigation", back_populates="evidence_citations"
    )


class CoordinationIndicator(Base):
    """Signals of coordinated inauthentic or automated behavior."""

    __tablename__ = "coordination_indicators"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("investigations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    indicator_type: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[Dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False
    )
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    involved_documents: Mapped[List[str]] = mapped_column(
        JSON, default=list, nullable=False
    )
    requires_review: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    investigation: Mapped["Investigation"] = relationship(
        "Investigation", back_populates="coordination_indicators"
    )


class ReviewTask(Base):
    """Human-in-the-loop review queue tasks for flagged or ambiguous predictions."""

    __tablename__ = "review_tasks"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    classification_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("classification_results.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False, index=True
    )
    priority: Mapped[str] = mapped_column(
        String(20), default="medium", nullable=False, index=True
    )
    assigned_to: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    classification_result: Mapped[Optional["ClassificationResult"]] = relationship(
        "ClassificationResult", back_populates="review_tasks"
    )
    document: Mapped["Document"] = relationship(
        "Document", back_populates="review_tasks"
    )
    feedbacks: Mapped[List["HumanFeedback"]] = relationship(
        "HumanFeedback", back_populates="review_task", cascade="all, delete-orphan"
    )


class HumanFeedback(Base):
    """Feedback from human analysts correcting or validating model decisions."""

    __tablename__ = "human_feedbacks"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    review_task_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("review_tasks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    classification_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("classification_results.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    corrected_label: Mapped[str] = mapped_column(String(100), nullable=False)
    is_ambiguous: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewer: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    review_task: Mapped[Optional["ReviewTask"]] = relationship(
        "ReviewTask", back_populates="feedbacks"
    )
    classification_result: Mapped[Optional["ClassificationResult"]] = relationship(
        "ClassificationResult", back_populates="feedbacks"
    )


class Dataset(Base):
    """Datasets used for fine-tuning and benchmarking detection models."""

    __tablename__ = "datasets"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    version: Mapped[str] = mapped_column(String(50), default="1.0.0", nullable=False)
    record_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    label_distribution: Mapped[Dict[str, int]] = mapped_column(
        JSON, default=dict, nullable=False
    )
    language_distribution: Mapped[Dict[str, int]] = mapped_column(
        JSON, default=dict, nullable=False
    )
    split_type: Mapped[str] = mapped_column(
        String(50), default="train_val_test", nullable=False
    )
    file_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    training_runs: Mapped[List["TrainingRun"]] = relationship(
        "TrainingRun", back_populates="dataset", cascade="all, delete-orphan"
    )
    evaluation_runs: Mapped[List["EvaluationRun"]] = relationship(
        "EvaluationRun", back_populates="dataset", cascade="all, delete-orphan"
    )


class TrainingRun(Base):
    """Record of a model training or fine-tuning run."""

    __tablename__ = "training_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    model_type: Mapped[str] = mapped_column(String(100), nullable=False)
    config: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False, index=True
    )
    metrics: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    checkpoint_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    dataset: Mapped["Dataset"] = relationship(
        "Dataset", back_populates="training_runs"
    )
    evaluation_runs: Mapped[List["EvaluationRun"]] = relationship(
        "EvaluationRun", back_populates="training_run", cascade="all, delete-orphan"
    )


class EvaluationRun(Base):
    """Evaluation runs and benchmark metric recordings."""

    __tablename__ = "evaluation_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    training_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("training_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    model_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    metrics: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    confusion_matrix: Mapped[List[List[int]]] = mapped_column(
        JSON, default=list, nullable=False
    )
    per_class_metrics: Mapped[Dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    training_run: Mapped[Optional["TrainingRun"]] = relationship(
        "TrainingRun", back_populates="evaluation_runs"
    )
    dataset: Mapped["Dataset"] = relationship(
        "Dataset", back_populates="evaluation_runs"
    )


class AuditEvent(Base):
    """Audit logging for tracking sensitive actions and system events."""

    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )
    details: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
