"""Database models."""

import json
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import (
    Column, String, Integer, DateTime, Text, Index, ForeignKey, Boolean, BigInteger
)
from sqlalchemy.orm import relationship, declarative_mixin
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class Session(Base, TimestampMixin):
    __tablename__ = "sessions"

    id = Column(String(64), primary_key=True)
    user_id = Column(String(255), nullable=False, index=True)
    email = Column(String(255), nullable=True)
    name = Column(String(255), nullable=True)
    roles = Column(Text, nullable=False, default="[]")  # JSON array
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=False, default="")
    expires_at = Column(BigInteger, nullable=False)  # Unix timestamp

    __table_args__ = (
        Index("ix_sessions_expires_at", "expires_at"),
    )


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(100), nullable=True, index=True)
    resource_id = Column(String(255), nullable=True, index=True)
    details = Column(Text, nullable=True)  # JSON
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)


class Model(Base, TimestampMixin):
    __tablename__ = "models"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    architecture = Column(String(100), nullable=True)  # e.g., "DeepSeek-V4", "Llama-3"
    quantization = Column(String(50), nullable=True)   # e.g., "FP8", "BF16", "INT4", "NVFP4"
    hardware_profile = Column(String(100), nullable=True)  # e.g., "A100-80GB", "H100", "RTX-3090"
    huggingface_repo = Column(String(255), nullable=True, index=True)
    description = Column(Text, nullable=True)
    config_json = Column(Text, nullable=True)  # Full model config from HF
    is_active = Column(Boolean, default=True, nullable=False)

    __table_args__ = (
        Index("ix_models_arch_quant", "architecture", "quantization"),
    )

    benchmarks = relationship("Benchmark", back_populates="model", cascade="all, delete-orphan")


class Benchmark(Base, TimestampMixin):
    __tablename__ = "benchmarks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(Integer, ForeignKey("models.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, default="pending")  # pending, running, completed, failed
    workload_type = Column(String(100), nullable=False)  # synthetic, custom
    config_json = Column(Text, nullable=False)  # Benchmark configuration
    results_json = Column(Text, nullable=True)  # Results when completed
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    model = relationship("Model", back_populates="benchmarks")

    __table_args__ = (
        Index("ix_benchmarks_model_status", "model_id", "status"),
    )


class HardwareProfile(Base, TimestampMixin):
    __tablename__ = "hardware_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    gpu_model = Column(String(100), nullable=False)
    gpu_count = Column(Integer, default=1, nullable=False)
    sm_version = Column(String(20), nullable=True)  # e.g., "8.0", "9.0"
    vram_gb = Column(Integer, nullable=False)
    driver_version = Column(String(50), nullable=True)
    cuda_version = Column(String(20), nullable=True)
    notes = Column(Text, nullable=True)

    compatibility = relationship("ModelHardwareCompatibility", back_populates="hardware", cascade="all, delete-orphan")


class ModelHardwareCompatibility(Base, TimestampMixin):
    __tablename__ = "model_hardware_compatibility"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(Integer, ForeignKey("models.id", ondelete="CASCADE"), nullable=False, index=True)
    hardware_id = Column(Integer, ForeignKey("hardware_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(50), nullable=False)  # compatible, incompatible, untested, partial
    notes = Column(Text, nullable=True)
    tested_at = Column(DateTime(timezone=True), nullable=True)
    tested_by = Column(String(255), nullable=True)

    model = relationship("Model")
    hardware = relationship("HardwareProfile", back_populates="compatibility")

    __table_args__ = (
        Index("ix_compat_model_hardware", "model_id", "hardware_id", unique=True),
    )


async def log_audit(
    db: AsyncSession,
    action: str,
    user_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[dict] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    """Log an audit entry."""
    audit = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=json.dumps(details) if details else None,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(audit)
    await db.flush()