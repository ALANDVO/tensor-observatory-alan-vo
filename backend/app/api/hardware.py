"""Hardware profiles and compatibility API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel, Field
from typing import Optional, List

from app.core.database import get_db
from app.api.deps import require_operator, require_admin, require_viewer, get_client_ip, get_user_agent
from app.models import HardwareProfile, ModelHardwareCompatibility, Model, AuditLog, log_audit
from app.core.auth import SessionData

router = APIRouter(prefix="/hardware", tags=["hardware"])


class HardwareCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    gpu_model: str = Field(..., min_length=1, max_length=100)
    gpu_count: int = Field(1, ge=1, le=128)
    sm_version: Optional[str] = Field(None, max_length=20)
    vram_gb: int = Field(..., ge=1, le=1024)
    driver_version: Optional[str] = Field(None, max_length=50)
    cuda_version: Optional[str] = Field(None, max_length=20)
    notes: Optional[str] = None


class HardwareResponse(BaseModel):
    id: int
    name: str
    gpu_model: str
    gpu_count: int
    sm_version: Optional[str]
    vram_gb: int
    driver_version: Optional[str]
    cuda_version: Optional[str]
    notes: Optional[str]
    created_at: str
    updated_at: str

    model_config = {'from_attributes': True}


@router.get("", response_model=List[HardwareResponse])
async def list_hardware(
    session: SessionData = Depends(require_viewer),
    db: AsyncSession = Depends(get_db),
):
    """List all hardware profiles."""
    result = await db.execute(select(HardwareProfile).order_by(HardwareProfile.name))
    hardware = result.scalars().all()
    return [HardwareResponse.model_validate(h) for h in hardware]


@router.post("", response_model=HardwareResponse, status_code=status.HTTP_201_CREATED)
async def create_hardware(
    hardware_data: HardwareCreate,
    request: Request,
    session: SessionData = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """Create a hardware profile."""
    existing = await db.scalar(select(HardwareProfile).where(HardwareProfile.name == hardware_data.name))
    if existing:
        raise HTTPException(status_code=409, detail="Hardware profile name already exists")

    hardware = HardwareProfile(**hardware_data.model_dump())
    db.add(hardware)
    await db.flush()

    await log_audit(
        db, action="create_hardware", user_id=session.user_id,
        resource_type="hardware", resource_id=str(hardware.id),
        details=hardware_data.model_dump(), ip_address=get_client_ip(request), user_agent=get_user_agent(request)
    )
    await db.commit()
    await db.refresh(hardware)
    return HardwareResponse.model_validate(hardware)


# Compatibility endpoints
compat_router = APIRouter(prefix="/compatibility", tags=["compatibility"])


class CompatibilityCreate(BaseModel):
    model_id: int = Field(..., gt=0)
    hardware_id: int = Field(..., gt=0)
    status: str = Field(..., pattern="^(compatible|incompatible|untested|partial)$")
    notes: Optional[str] = None

    model_config = {'protected_namespaces': ()}
class CompatibilityResponse(BaseModel):
    id: int
    model_id: int
    hardware_id: int
    status: str
    notes: Optional[str]
    tested_at: Optional[str]
    tested_by: Optional[str]
    created_at: str
    updated_at: str

    model_config = {'protected_namespaces': (), 'from_attributes': True}

@compat_router.get("", response_model=List[CompatibilityResponse])
async def list_compatibility(
    model_id: Optional[int] = Query(None),
    hardware_id: Optional[int] = Query(None),
    session: SessionData = Depends(require_viewer),
    db: AsyncSession = Depends(get_db),
):
    """List compatibility records."""
    query = select(ModelHardwareCompatibility)
    if model_id:
        query = query.where(ModelHardwareCompatibility.model_id == model_id)
    if hardware_id:
        query = query.where(ModelHardwareCompatibility.hardware_id == hardware_id)

    result = await db.execute(query.order_by(ModelHardwareCompatibility.created_at.desc()))
    compat = result.scalars().all()
    return [CompatibilityResponse.model_validate(c) for c in compat]


@compat_router.post("", response_model=CompatibilityResponse, status_code=status.HTTP_201_CREATED)
async def create_compatibility(
    compat_data: CompatibilityCreate,
    request: Request,
    session: SessionData = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """Create a compatibility record."""
    # Validate model and hardware exist
    model = await db.scalar(select(Model).where(Model.id == compat_data.model_id))
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    hardware = await db.scalar(select(HardwareProfile).where(HardwareProfile.id == compat_data.hardware_id))
    if not hardware:
        raise HTTPException(status_code=404, detail="Hardware profile not found")

    # Check for existing
    existing = await db.scalar(
        select(ModelHardwareCompatibility).where(
            ModelHardwareCompatibility.model_id == compat_data.model_id,
            ModelHardwareCompatibility.hardware_id == compat_data.hardware_id
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="Compatibility record already exists")

    from datetime import datetime, timezone
    compat = ModelHardwareCompatibility(
        **compat_data.model_dump(),
        tested_at=datetime.now(timezone.utc),
        tested_by=session.user_id,
    )
    db.add(compat)
    await db.flush()

    await log_audit(
        db, action="create_compatibility", user_id=session.user_id,
        resource_type="compatibility", resource_id=str(compat.id),
        details=compat_data.model_dump(), ip_address=get_client_ip(request), user_agent=get_user_agent(request)
    )
    await db.commit()
    await db.refresh(compat)
    return CompatibilityResponse.model_validate(compat)