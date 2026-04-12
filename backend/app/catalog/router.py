from fastapi import APIRouter, Depends
from sqlalchemy import distinct, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import UserRole, require_role
from app.catalog.loader import load_catalog
from app.database import get_async_session
from app.models.connectors import SystemCatalog

router = APIRouter(tags=["catalog"])


@router.get("/catalog/domains")
async def list_domains(
    session: AsyncSession = Depends(get_async_session),
    user=Depends(require_role(UserRole.STAFF)),
):
    """List all functional domains in the systems catalog."""
    result = await session.execute(
        select(distinct(SystemCatalog.domain)).order_by(SystemCatalog.domain)
    )
    return {"domains": [row[0] for row in result.fetchall()]}


@router.get("/catalog/systems")
async def list_systems(
    domain: str | None = None,
    session: AsyncSession = Depends(get_async_session),
    user=Depends(require_role(UserRole.STAFF)),
):
    """List systems in the catalog, optionally filtered by domain."""
    query = select(SystemCatalog).order_by(
        SystemCatalog.domain, SystemCatalog.vendor_name
    )
    if domain:
        query = query.where(SystemCatalog.domain == domain)
    result = await session.execute(query)
    systems = result.scalars().all()
    return {
        "systems": [
            {
                "id": s.id,
                "domain": s.domain,
                "vendor_name": s.vendor_name,
                "access_protocol": s.access_protocol,
                "data_shape": s.data_shape,
                "common_record_types": s.common_record_types,
                "redaction_tier": s.redaction_tier,
            }
            for s in systems
        ]
    }


@router.post("/catalog/load", status_code=200)
async def trigger_catalog_load(
    session: AsyncSession = Depends(get_async_session),
    user=Depends(require_role(UserRole.ADMIN)),
):
    """Load or refresh the systems catalog from the bundled JSON."""
    count = await load_catalog(session)
    if count == 0:
        return {"message": "Catalog already loaded at current version", "loaded": 0}
    return {"message": f"Loaded {count} system entries", "loaded": count}
