"""Models API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List
import httpx
import json

from app.core.database import get_db
from app.api.deps import require_operator, require_admin, require_viewer, get_client_ip, get_user_agent
from app.models import Model, AuditLog, log_audit
from app.core.auth import SessionData

router = APIRouter(prefix="/models", tags=["models"])


class ModelCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    architecture: Optional[str] = Field(None, max_length=100)
    quantization: Optional[str] = Field(None, max_length=50)
    hardware_profile: Optional[str] = Field(None, max_length=100)
    huggingface_repo: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None


class ModelUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    architecture: Optional[str] = Field(None, max_length=100)
    quantization: Optional[str] = Field(None, max_length=50)
    hardware_profile: Optional[str] = Field(None, max_length=100)
    huggingface_repo: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class ModelResponse(BaseModel):
    id: int
    name: str
    architecture: Optional[str]
    quantization: Optional[str]
    hardware_profile: Optional[str]
    huggingface_repo: Optional[str]
    description: Optional[str]
    config_json: Optional[str]
    is_active: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class ModelListResponse(BaseModel):
    items: List[ModelResponse]
    total: int
    page: int
    limit: int


@router.get("", response_model=ModelListResponse)
async def list_models(
    request: Request,
    search: Optional[str] = Query(None),
    architecture: Optional[str] = Query(None),
    quantization: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    session: SessionData = Depends(require_viewer),
    db: AsyncSession = Depends(get_db),
):
    """List models with pagination and filters."""
    query = select(Model)
    
    if search:
        query = query.where(or_(
            Model.name.ilike(f"%{search}%"),
            Model.architecture.ilike(f"%{search}%"),
            Model.huggingface_repo.ilike(f"%{search}%"),
        ))
    if architecture:
        query = query.where(Model.architecture == architecture)
    if quantization:
        query = query.where(Model.quantization == quantization)
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0
    
    # Paginate
    query = query.order_by(Model.created_at.desc()).offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    models = result.scalars().all()
    
    return ModelListResponse(
        items=[ModelResponse.model_validate(m) for m in models],
        total=total,
        page=page,
        limit=limit,
    )


@router.get("/{model_id}", response_model=ModelResponse)
async def get_model(
    model_id: int,
    session: SessionData = Depends(require_viewer),
    db: AsyncSession = Depends(get_db),
):
    """Get model by ID."""
    result = await db.execute(select(Model).where(Model.id == model_id))
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return ModelResponse.model_validate(model)


@router.post("", response_model=ModelResponse, status_code=status.HTTP_201_CREATED)
async def create_model(
    model_data: ModelCreate,
    request: Request,
    session: SessionData = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """Create a new model."""
    # Check unique name
    existing = await db.scalar(select(Model).where(Model.name == model_data.name))
    if existing:
        raise HTTPException(status_code=409, detail="Model name already exists")
    
    model = Model(**model_data.model_dump())
    db.add(model)
    await db.flush()
    
    await log_audit(
        db, action="create_model", user_id=session.user_id,
        resource_type="model", resource_id=str(model.id),
        details=model_data.model_dump(), ip_address=get_client_ip(request), user_agent=get_user_agent(request)
    )
    await db.commit()
    await db.refresh(model)
    return ModelResponse.model_validate(model)


@router.patch("/{model_id}", response_model=ModelResponse)
async def update_model(
    model_id: int,
    model_data: ModelUpdate,
    request: Request,
    session: SessionData = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """Update a model."""
    result = await db.execute(select(Model).where(Model.id == model_id))
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    update_data = model_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(model, field, value)
    
    await log_audit(
        db, action="update_model", user_id=session.user_id,
        resource_type="model", resource_id=str(model_id),
        details=update_data, ip_address=get_client_ip(request), user_agent=get_user_agent(request)
    )
    await db.commit()
    await db.refresh(model)
    return ModelResponse.model_validate(model)


@router.delete("/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model(
    model_id: int,
    request: Request,
    session: SessionData = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete a model (admin only)."""
    result = await db.execute(select(Model).where(Model.id == model_id))
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    await log_audit(
        db, action="delete_model", user_id=session.user_id,
        resource_type="model", resource_id=str(model_id),
        details={"name": model.name}, ip_address=get_client_ip(request), user_agent=get_user_agent(request)
    )
    await db.delete(model)
    await db.commit()


@router.post("/import", response_model=ModelResponse, status_code=status.HTTP_201_CREATED)
async def import_model(
    request: Request,
    session: SessionData = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """Import model metadata from HuggingFace Hub."""
    body = await request.json()
    repo = body.get("huggingface_repo")
    if not repo:
        raise HTTPException(status_code=400, detail="huggingface_repo is required")
    
    # Fetch from HF Hub API
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.get(f"https://huggingface.co/api/models/{repo}")
            resp.raise_for_status()
            hf_data = resp.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise HTTPException(status_code=404, detail="Model not found on HuggingFace Hub")
            raise HTTPException(status_code=400, detail=f"HF Hub error: {e.response.text}")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to fetch from HF Hub: {e}")
    
    # Extract relevant fields
    model_name = hf_data.get("modelId", repo).split("/")[-1]
    tags = hf_data.get("tags", [])
    architecture = None
    quantization = None
    for tag in tags:
        if tag in ["llama", "deepseek", "qwen", "mistral", "phi", "gemma", "falcon", "mpt", "bloom", "gpt", "bert"]:
            architecture = tag.capitalize()
        if tag in ["fp8", "bf16", "fp16", "int8", "int4", "gptq", "awq", "nf4", "fp4", "nvfp4"]:
            quantization = tag.upper()
    
    config = hf_data.get("config", {})
    if isinstance(config, dict):
        arch_from_config = config.get("architectures", [None])[0]
        if arch_from_config:
            architecture = arch_from_config.replace("ForCausalLM", "").replace("Model", "")
    
    model_data = ModelCreate(
        name=model_name,
        architecture=architecture,
        quantization=quantization,
        huggingface_repo=repo,
        description=hf_data.get("description", ""),
    )
    
    # Check unique name
    existing = await db.scalar(select(Model).where(Model.name == model_data.name))
    if existing:
        raise HTTPException(status_code=409, detail=f"Model '{model_data.name}' already exists")
    
    model = Model(
        **model_data.model_dump(),
        config_json=json.dumps(hf_data) if hf_data else None,
    )
    db.add(model)
    await db.flush()
    
    await log_audit(
        db, action="import_model", user_id=session.user_id,
        resource_type="model", resource_id=str(model.id),
        details={"huggingface_repo": repo, **model_data.model_dump()},
        ip_address=get_client_ip(request), user_agent=get_user_agent(request)
    )
    await db.commit()
    await db.refresh(model)
    return ModelResponse.model_validate(model)