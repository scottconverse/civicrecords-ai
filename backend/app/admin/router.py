from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_role
from app.config import APP_VERSION, settings
from app.database import get_async_session
from app.models.audit import AuditLog
from app.models.document import ModelRegistry
from app.models.user import User, UserRole
from app.schemas.model_registry import ModelRegistryCreate, ModelRegistryRead, ModelRegistryUpdate
from app.schemas.user import UserRead
from app.audit.logger import write_audit_log

router = APIRouter(prefix="/admin", tags=["admin"])


class SystemStatus(BaseModel):
    version: str
    database: str
    ollama: str
    redis: str
    user_count: int
    audit_log_count: int


class OllamaModelInfo(BaseModel):
    name: str
    size: int | None = None
    details: dict | None = None


class OllamaStatus(BaseModel):
    status: str
    models: list[OllamaModelInfo]


@router.get("/status", response_model=SystemStatus)
async def system_status(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(require_role(UserRole.ADMIN)),
):
    import httpx

    try:
        await session.execute(select(func.count(User.id)))
        db_status = "connected"
    except Exception:
        db_status = "error"

    result = await session.execute(select(func.count(User.id)))
    user_count = result.scalar() or 0

    result = await session.execute(select(func.count(AuditLog.id)))
    audit_count = result.scalar() or 0

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.ollama_base_url}/api/tags")
            ollama_status = "connected" if resp.status_code == 200 else "error"
    except Exception:
        ollama_status = "unreachable"

    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.redis_url)
        await r.ping()
        redis_status = "connected"
        await r.aclose()
    except Exception:
        redis_status = "unreachable"

    return SystemStatus(
        version=APP_VERSION,
        database=db_status,
        ollama=ollama_status,
        redis=redis_status,
        user_count=user_count,
        audit_log_count=audit_count,
    )


@router.get("/users", response_model=list[UserRead])
async def list_users(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(require_role(UserRole.ADMIN)),
):
    """List all users. Admin only."""
    result = await session.execute(select(User).order_by(User.created_at.desc()))
    return result.scalars().all()


class AdminUserCreateRequest(BaseModel):
    email: str
    password: str
    full_name: str = ""
    role: str = "staff"


class AdminUserCreateResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool

    model_config = {"from_attributes": True}


@router.post("/users", response_model=AdminUserCreateResponse, status_code=201)
async def create_user(
    body: AdminUserCreateRequest,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Create a new user. Admin only."""
    from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
    from app.auth.manager import UserManager
    from app.schemas.user import AdminUserCreate

    user_db = SQLAlchemyUserDatabase(session, User)
    manager = UserManager(session=session, user_db=user_db)

    try:
        role_enum = UserRole(body.role)
    except ValueError:
        from fastapi import HTTPException as _HTTPException
        raise _HTTPException(status_code=422, detail=f"Invalid role: {body.role}")

    user_create = AdminUserCreate(
        email=body.email,
        password=body.password,
        full_name=body.full_name,
        role=role_enum,
        is_active=True,
        is_verified=True,
    )

    from fastapi import HTTPException as _HTTPException
    try:
        created = await manager.create(user_create)
    except Exception as e:
        raise _HTTPException(status_code=400, detail=str(e))

    return AdminUserCreateResponse(
        id=str(created.id),
        email=created.email,
        full_name=created.full_name,
        role=created.role.value if hasattr(created.role, 'value') else str(created.role),
        is_active=created.is_active,
    )


@router.get("/models", response_model=OllamaStatus)
async def list_models(
    user: User = Depends(require_role(UserRole.ADMIN)),
):
    import httpx

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{settings.ollama_base_url}/api/tags")
            if resp.status_code == 200:
                data = resp.json()
                models = [
                    OllamaModelInfo(
                        name=m.get("name", ""),
                        size=m.get("size"),
                        details=m.get("details"),
                    )
                    for m in data.get("models", [])
                ]
                return OllamaStatus(status="connected", models=models)
    except Exception:
        pass

    return OllamaStatus(status="unreachable", models=[])


@router.get("/models/registry", response_model=list[ModelRegistryRead])
async def list_model_registry(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(require_role(UserRole.ADMIN)),
):
    result = await session.execute(
        select(ModelRegistry).order_by(ModelRegistry.added_at.desc())
    )
    return result.scalars().all()


@router.post("/models/registry", response_model=ModelRegistryRead, status_code=201)
async def register_model(
    data: ModelRegistryCreate,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(require_role(UserRole.ADMIN)),
):
    model = ModelRegistry(
        model_name=data.model_name,
        model_version=data.model_version,
        parameter_count=data.parameter_count,
        license=data.license,
        model_card_url=data.model_card_url,
        context_window_size=data.context_window_size,
        supports_ner=data.supports_ner,
        supports_vision=data.supports_vision,
        is_active=True,
    )
    session.add(model)
    await session.commit()
    await session.refresh(model)

    await write_audit_log(
        session=session, action="register_model", resource_type="model_registry",
        resource_id=str(model.id), user_id=user.id,
        details={"model_name": data.model_name},
    )
    return model


@router.patch("/models/registry/{model_id}", response_model=ModelRegistryRead)
async def update_model_registry(
    model_id: int,
    data: ModelRegistryUpdate,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(require_role(UserRole.ADMIN)),
):
    model = await session.get(ModelRegistry, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(model, field, value)

    await session.commit()
    await session.refresh(model)

    await write_audit_log(
        session=session, action="update_model_registry", resource_type="model_registry",
        resource_id=str(model.id), user_id=user.id,
        details=data.model_dump(exclude_none=True),
    )
    return model


@router.delete("/models/registry/{model_id}", status_code=204)
async def delete_model_registry(
    model_id: int,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(require_role(UserRole.ADMIN)),
):
    model = await session.get(ModelRegistry, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    await session.delete(model)
    await session.commit()

    await write_audit_log(
        session=session, action="delete_model_registry", resource_type="model_registry",
        resource_id=str(model_id), user_id=user.id,
        details={"model_name": model.model_name},
    )
