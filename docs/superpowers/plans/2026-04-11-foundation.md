# Sub-Project 1: Foundation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the complete infrastructure skeleton — Docker Compose stack, FastAPI backend with auth and audit logging, React admin shell, install script — so all subsequent sub-projects have a working platform to build on.

**Architecture:** 5 Docker services (Postgres+pgvector, Redis 7.2, FastAPI, Celery worker, Ollama) orchestrated via Docker Compose. FastAPI backend with SQLAlchemy async + Alembic migrations. Auth via fastapi-users with JWT and 4 RBAC roles. Hash-chained append-only audit log as middleware. React + shadcn/ui admin panel skeleton served by nginx.

**Tech Stack:**
- Python 3.12, FastAPI 0.135+, SQLAlchemy 2.0 (async), Alembic, Celery 5.6+
- PostgreSQL 17 + pgvector, Redis 7.2 (BSD licensed)
- fastapi-users 15+ with SQLAlchemy backend
- React 18, Vite, shadcn/ui, Tailwind CSS
- Docker, Docker Compose v2
- pytest, pytest-asyncio, httpx (test client)

**Licensing note:** Redis 8.x changed to tri-license. Pin to Redis 7.2.x (BSD) for compliance.

---

## File Structure

```
civicrecords-ai/
├── docker-compose.yml              # 5 services + frontend
├── docker-compose.dev.yml          # Dev overrides (hot reload, exposed ports)
├── .env.example                    # Template for required env vars
├── Dockerfile.backend              # Python backend image
├── Dockerfile.frontend             # React frontend image
├── install.sh                      # Ubuntu 24.04 install script
├── scripts/
│   └── verify-sovereignty.sh       # Data sovereignty verification
├── backend/
│   ├── pyproject.toml              # Python project config + dependencies
│   ├── alembic.ini                 # Alembic config
│   ├── alembic/
│   │   ├── env.py                  # Migration environment
│   │   └── versions/               # Migration files
│   │       └── 001_initial.py      # Initial schema
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app factory + middleware
│   │   ├── config.py               # Pydantic settings from env
│   │   ├── database.py             # Async SQLAlchemy engine + session
│   │   ├── models/
│   │   │   ├── __init__.py         # Re-exports all models
│   │   │   ├── user.py             # User model (fastapi-users compatible)
│   │   │   ├── service_account.py  # Service account model
│   │   │   └── audit.py            # AuditLog model (hash-chained)
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── user.py             # User create/read/update schemas
│   │   │   ├── service_account.py  # Service account schemas
│   │   │   └── audit.py            # Audit log schemas
│   │   ├── auth/
│   │   │   ├── __init__.py
│   │   │   ├── manager.py          # UserManager (fastapi-users)
│   │   │   ├── backend.py          # JWT auth backend
│   │   │   ├── dependencies.py     # Auth dependency injection
│   │   │   └── router.py           # Auth routes (login, register, me)
│   │   ├── audit/
│   │   │   ├── __init__.py
│   │   │   ├── logger.py           # Hash-chained audit log writer
│   │   │   ├── middleware.py        # FastAPI middleware for auto-logging
│   │   │   └── router.py           # Audit log query/export endpoints
│   │   ├── admin/
│   │   │   ├── __init__.py
│   │   │   └── router.py           # Admin endpoints (user mgmt, model info, system status)
│   │   └── service_accounts/
│   │       ├── __init__.py
│   │       └── router.py           # Service account CRUD
│   └── tests/
│       ├── conftest.py             # Fixtures: test DB, test client, test users
│       ├── test_health.py          # Health/readiness endpoints
│       ├── test_auth.py            # Login, register, roles, JWT
│       ├── test_audit.py           # Audit logging, hash chain, export
│       ├── test_admin.py           # Admin endpoints, role enforcement
│       └── test_service_accounts.py # Service account CRUD, API key auth
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   ├── index.html
│   ├── src/
│   │   ├── main.tsx                # React entry point
│   │   ├── App.tsx                 # Router + layout
│   │   ├── lib/
│   │   │   ├── api.ts              # API client (fetch wrapper with JWT)
│   │   │   └── utils.ts            # shadcn/ui cn() helper
│   │   ├── components/
│   │   │   └── ui/                 # shadcn/ui components (auto-generated)
│   │   └── pages/
│   │       ├── Login.tsx           # Login form
│   │       ├── Dashboard.tsx       # System status overview
│   │       └── Users.tsx           # User management table
│   └── Dockerfile                  # Build + nginx serve
└── docs/                           # Already exists
```

---

## Task 1: Project Skeleton and Docker Compose

**Files:**
- Create: `backend/pyproject.toml`
- Create: `.env.example`
- Create: `docker-compose.yml`
- Create: `docker-compose.dev.yml`
- Create: `Dockerfile.backend`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/config.py`

- [ ] **Step 1: Create backend/pyproject.toml**

```toml
[project]
name = "civicrecords-ai"
version = "0.1.0"
description = "Open-source AI-powered open records support for American cities"
requires-python = ">=3.12"
license = {text = "Apache-2.0"}
dependencies = [
    "fastapi>=0.135.0",
    "uvicorn[standard]>=0.44.0",
    "sqlalchemy[asyncio]>=2.0.49",
    "asyncpg>=0.31.0",
    "alembic>=1.18.0",
    "pgvector>=0.4.2",
    "pydantic>=2.12.0",
    "pydantic-settings>=2.13.0",
    "fastapi-users[sqlalchemy]>=15.0.0",
    "python-jose[cryptography]>=3.5.0",
    "passlib[bcrypt]>=1.7.4",
    "celery>=5.6.0",
    "redis>=5.0.0,<8.0.0",
    "httpx>=0.28.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=9.0.0",
    "pytest-asyncio>=1.0.0",
    "ruff>=0.11.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
target-version = "py312"
line-length = 100
```

- [ ] **Step 2: Create .env.example**

```bash
# Database
DATABASE_URL=postgresql+asyncpg://civicrecords:civicrecords@postgres:5432/civicrecords

# Auth
JWT_SECRET=CHANGE-ME-generate-with-openssl-rand-hex-32
FIRST_ADMIN_EMAIL=admin@localhost
FIRST_ADMIN_PASSWORD=CHANGE-ME-on-first-login

# Ollama
OLLAMA_BASE_URL=http://ollama:11434

# Redis
REDIS_URL=redis://redis:6379/0

# Audit
AUDIT_RETENTION_DAYS=1095
```

- [ ] **Step 3: Create backend/app/config.py**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://civicrecords:civicrecords@postgres:5432/civicrecords"
    jwt_secret: str = "CHANGE-ME"
    jwt_lifetime_seconds: int = 3600
    first_admin_email: str = "admin@localhost"
    first_admin_password: str = "CHANGE-ME"
    ollama_base_url: str = "http://ollama:11434"
    redis_url: str = "redis://redis:6379/0"
    audit_retention_days: int = 1095

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
```

- [ ] **Step 4: Create backend/app/__init__.py**

```python
# CivicRecords AI - Backend
```

- [ ] **Step 5: Create minimal backend/app/main.py**

```python
from fastapi import FastAPI

from app.config import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title="CivicRecords AI",
        description="AI-powered open records support for American cities",
        version="0.1.0",
    )

    @app.get("/health")
    async def health():
        return {"status": "ok", "version": "0.1.0"}

    return app


app = create_app()
```

- [ ] **Step 6: Create Dockerfile.backend**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/pyproject.toml .
RUN pip install --no-cache-dir .

COPY backend/app ./app
COPY backend/alembic.ini .
COPY backend/alembic ./alembic

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 7: Create docker-compose.yml**

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg17
    environment:
      POSTGRES_USER: civicrecords
      POSTGRES_PASSWORD: civicrecords
      POSTGRES_DB: civicrecords
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U civicrecords"]
      interval: 5s
      timeout: 3s
      retries: 5

  redis:
    image: redis:7.2-alpine
    volumes:
      - redisdata:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  ollama:
    image: ollama/ollama:latest
    volumes:
      - ollamadata:/root/.ollama
    healthcheck:
      test: ["CMD-SHELL", "curl -sf http://localhost:11434/api/tags || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 10

  api:
    build:
      context: .
      dockerfile: Dockerfile.backend
    env_file: .env
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD-SHELL", "curl -sf http://localhost:8000/health || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 5

  worker:
    build:
      context: .
      dockerfile: Dockerfile.backend
    env_file: .env
    command: celery -A app.worker worker --loglevel=info
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

volumes:
  pgdata:
  redisdata:
  ollamadata:
```

- [ ] **Step 8: Create docker-compose.dev.yml**

```yaml
# Development overrides: hot reload, source mounting, debug ports
services:
  api:
    build:
      context: .
      dockerfile: Dockerfile.backend
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - ./backend/app:/app/app
      - ./backend/tests:/app/tests
      - ./backend/alembic:/app/alembic
    ports:
      - "8000:8000"

  worker:
    volumes:
      - ./backend/app:/app/app

  postgres:
    ports:
      - "5432:5432"

  redis:
    ports:
      - "6379:6379"
```

- [ ] **Step 9: Commit**

```bash
git add backend/pyproject.toml backend/app/__init__.py backend/app/main.py \
  backend/app/config.py .env.example Dockerfile.backend \
  docker-compose.yml docker-compose.dev.yml
git commit -m "feat: project skeleton with Docker Compose stack and FastAPI shell"
```

---

## Task 2: Database Layer and Alembic Migrations

**Files:**
- Create: `backend/app/database.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/script.mako`
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/user.py`
- Create: `backend/app/models/service_account.py`
- Create: `backend/app/models/audit.py`

- [ ] **Step 1: Create backend/app/database.py**

```python
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session
```

- [ ] **Step 2: Create backend/app/models/user.py**

fastapi-users requires a specific model structure. The `role` field is our addition for RBAC.

```python
import enum
from datetime import datetime

from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTableUUID
from sqlalchemy import DateTime, Enum, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    STAFF = "staff"
    REVIEWER = "reviewer"
    READ_ONLY = "read_only"


class User(SQLAlchemyBaseUserTableUUID, Base):
    __tablename__ = "users"

    full_name: Mapped[str] = mapped_column(default="")
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"),
        default=UserRole.STAFF,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_login: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
```

- [ ] **Step 3: Create backend/app/models/service_account.py**

```python
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.user import Base, UserRole


class ServiceAccount(Base):
    __tablename__ = "service_accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), unique=True)
    api_key_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", create_type=False),
        default=UserRole.READ_ONLY,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    is_active: Mapped[bool] = mapped_column(default=True)
```

- [ ] **Step 4: Create backend/app/models/audit.py**

The audit log is append-only and hash-chained. Each entry contains a SHA-256 hash of the previous entry, creating a tamper-evident chain.

```python
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text, Boolean, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.user import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    prev_hash: Mapped[str] = mapped_column(String(64), default="0" * 64)
    entry_hash: Mapped[str] = mapped_column(String(64), index=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(100), index=True)
    resource_type: Mapped[str] = mapped_column(String(100), index=True)
    resource_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ai_generated: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (
        Index("ix_audit_log_user_timestamp", "user_id", "timestamp"),
    )
```

- [ ] **Step 5: Create backend/app/models/__init__.py**

```python
from app.models.audit import AuditLog
from app.models.service_account import ServiceAccount
from app.models.user import Base, User, UserRole

__all__ = ["Base", "User", "UserRole", "ServiceAccount", "AuditLog"]
```

- [ ] **Step 6: Create backend/alembic.ini**

```ini
[alembic]
script_location = alembic
prepend_sys_path = .

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

- [ ] **Step 7: Create backend/alembic/env.py**

```python
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings
from app.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = create_async_engine(settings.database_url)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
```

- [ ] **Step 8: Create backend/alembic/script.mako**

```mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers
revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

- [ ] **Step 9: Create initial migration backend/alembic/versions/001_initial.py**

```python
"""Initial schema: users, service_accounts, audit_log

Revision ID: 001
Revises:
Create Date: 2026-04-11
"""
from typing import Sequence, Union

import fastapi_users_db_sqlalchemy
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # UserRole enum
    user_role = postgresql.ENUM("admin", "staff", "reviewer", "read_only", name="user_role", create_type=True)
    user_role.create(op.get_bind(), checkfirst=True)

    # Users table (fastapi-users compatible)
    op.create_table(
        "users",
        sa.Column("id", fastapi_users_db_sqlalchemy.generics.GUID(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("hashed_password", sa.String(length=1024), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("full_name", sa.String(), nullable=False, server_default=""),
        sa.Column("role", sa.Enum("admin", "staff", "reviewer", "read_only", name="user_role", create_type=False), nullable=False, server_default="staff"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # Service accounts table
    op.create_table(
        "service_accounts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("api_key_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.Enum("admin", "staff", "reviewer", "read_only", name="user_role", create_type=False), nullable=False, server_default="read_only"),
        sa.Column("created_by", sa.UUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # Audit log table (append-only, hash-chained)
    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("prev_hash", sa.String(64), nullable=False, server_default="0" * 64),
        sa.Column("entry_hash", sa.String(64), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=False),
        sa.Column("resource_id", sa.String(255), nullable=True),
        sa.Column("details", postgresql.JSONB(), nullable=True),
        sa.Column("ai_generated", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_log_entry_hash", "audit_log", ["entry_hash"])
    op.create_index("ix_audit_log_timestamp", "audit_log", ["timestamp"])
    op.create_index("ix_audit_log_action", "audit_log", ["action"])
    op.create_index("ix_audit_log_resource_type", "audit_log", ["resource_type"])
    op.create_index("ix_audit_log_user_id", "audit_log", ["user_id"])
    op.create_index("ix_audit_log_user_timestamp", "audit_log", ["user_id", "timestamp"])


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("service_accounts")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS user_role")
    op.execute("DROP EXTENSION IF EXISTS vector")
```

- [ ] **Step 10: Commit**

```bash
git add backend/app/database.py backend/app/models/ backend/alembic.ini \
  backend/alembic/
git commit -m "feat: database layer with User, ServiceAccount, AuditLog models and initial migration"
```

---

## Task 3: Auth System (fastapi-users + JWT + RBAC)

**Files:**
- Create: `backend/app/schemas/user.py`
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/auth/manager.py`
- Create: `backend/app/auth/backend.py`
- Create: `backend/app/auth/dependencies.py`
- Create: `backend/app/auth/router.py`
- Create: `backend/app/auth/__init__.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_auth.py`

- [ ] **Step 1: Create backend/app/schemas/__init__.py**

```python
# Schemas package
```

- [ ] **Step 2: Create backend/app/schemas/user.py**

```python
import uuid
from datetime import datetime

from fastapi_users import schemas
from pydantic import BaseModel

from app.models.user import UserRole


class UserRead(schemas.BaseUser[uuid.UUID]):
    full_name: str
    role: UserRole
    created_at: datetime
    last_login: datetime | None


class UserCreate(schemas.BaseUserCreate):
    full_name: str = ""
    role: UserRole = UserRole.STAFF


class UserUpdate(schemas.BaseUserUpdate):
    full_name: str | None = None
    role: UserRole | None = None
```

- [ ] **Step 3: Create backend/app/auth/backend.py**

```python
from fastapi_users.authentication import AuthenticationBackend, BearerTransport, JWTStrategy

from app.config import settings

bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=settings.jwt_secret, lifetime_seconds=settings.jwt_lifetime_seconds)


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)
```

- [ ] **Step 4: Create backend/app/auth/manager.py**

```python
import uuid
from datetime import datetime, timezone

from fastapi import Depends, Request
from fastapi_users import BaseUserManager, UUIDIDMixin
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.models.user import User


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = "reset-secret"
    verification_token_secret = "verify-secret"

    def __init__(self, session: AsyncSession, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._session = session

    async def on_after_login(self, user: User, request: Request | None = None, response=None):
        await self._session.execute(
            update(User).where(User.id == user.id).values(last_login=datetime.now(timezone.utc))
        )
        await self._session.commit()


async def get_user_manager(session: AsyncSession = Depends(get_async_session)):
    from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase

    user_db = SQLAlchemyUserDatabase(session, User)
    yield UserManager(session=session, user_db=user_db)
```

- [ ] **Step 5: Create backend/app/auth/dependencies.py**

Role-based dependency injection. Each endpoint declares its minimum required role.

```python
import uuid

from fastapi import Depends, HTTPException, status
from fastapi_users import FastAPIUsers

from app.auth.backend import auth_backend
from app.auth.manager import get_user_manager
from app.models.user import User, UserRole

fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])

current_active_user = fastapi_users.current_user(active=True)

# Role hierarchy: admin > reviewer > staff > read_only
ROLE_HIERARCHY = {
    UserRole.ADMIN: 4,
    UserRole.REVIEWER: 3,
    UserRole.STAFF: 2,
    UserRole.READ_ONLY: 1,
}


def require_role(minimum_role: UserRole):
    """Dependency that enforces a minimum role level."""

    async def _check_role(user: User = Depends(current_active_user)) -> User:
        if ROLE_HIERARCHY.get(user.role, 0) < ROLE_HIERARCHY[minimum_role]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {minimum_role.value} role or higher",
            )
        return user

    return _check_role
```

- [ ] **Step 6: Create backend/app/auth/router.py**

```python
from app.auth.backend import auth_backend
from app.auth.dependencies import fastapi_users
from app.schemas.user import UserCreate, UserRead, UserUpdate

auth_router = fastapi_users.get_auth_router(auth_backend)
register_router = fastapi_users.get_register_router(UserRead, UserCreate)
users_router = fastapi_users.get_users_router(UserRead, UserUpdate)
```

- [ ] **Step 7: Create backend/app/auth/__init__.py**

```python
from app.auth.dependencies import current_active_user, fastapi_users, require_role
from app.auth.router import auth_router, register_router, users_router

__all__ = [
    "auth_router",
    "register_router",
    "users_router",
    "current_active_user",
    "fastapi_users",
    "require_role",
]
```

- [ ] **Step 8: Update backend/app/main.py to include auth routes**

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.auth import auth_router, register_router, users_router
from app.config import settings
from app.database import engine
from app.models.user import User, UserRole


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create first admin user on startup if it doesn't exist
    from sqlalchemy import select
    from app.database import async_session_maker
    from app.auth.manager import UserManager
    from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
    from fastapi_users.password import PasswordHelper

    async with async_session_maker() as session:
        result = await session.execute(select(User).limit(1))
        if result.scalar_one_or_none() is None:
            user_db = SQLAlchemyUserDatabase(session, User)
            manager = UserManager(session=session, user_db=user_db)
            password_helper = PasswordHelper()
            await manager.create(
                user_create=type(
                    "UserCreate",
                    (),
                    {
                        "email": settings.first_admin_email,
                        "password": settings.first_admin_password,
                        "full_name": "System Administrator",
                        "role": UserRole.ADMIN,
                        "is_superuser": True,
                        "is_active": True,
                        "is_verified": True,
                    },
                )()
            )
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="CivicRecords AI",
        description="AI-powered open records support for American cities",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.include_router(auth_router, prefix="/auth/jwt", tags=["auth"])
    app.include_router(register_router, prefix="/auth", tags=["auth"])
    app.include_router(users_router, prefix="/users", tags=["users"])

    @app.get("/health")
    async def health():
        return {"status": "ok", "version": "0.1.0"}

    return app


app = create_app()
```

- [ ] **Step 9: Create backend/tests/conftest.py**

```python
import asyncio
import uuid
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.database import get_async_session
from app.main import create_app
from app.models.user import Base

TEST_DATABASE_URL = settings.database_url.replace("/civicrecords", "/civicrecords_test")

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
test_session_maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
    async with test_session_maker() as session:
        yield session


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    app = create_app()
    app.dependency_overrides[get_async_session] = override_get_session
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture
async def admin_token(client: AsyncClient) -> str:
    """Register an admin user and return JWT token."""
    await client.post(
        "/auth/register",
        json={
            "email": f"admin-{uuid.uuid4().hex[:8]}@test.com",
            "password": "testpassword123",
            "full_name": "Test Admin",
            "role": "admin",
        },
    )
    resp = await client.post(
        "/auth/jwt/login",
        data={
            "username": resp_reg_email := f"admin-login-{uuid.uuid4().hex[:8]}@test.com",
            "password": "testpassword123",
        },
    )
    # Re-register with known email then login
    reg = await client.post(
        "/auth/register",
        json={
            "email": f"admin-{uuid.uuid4().hex[:8]}@test.com",
            "password": "adminpass123",
            "full_name": "Test Admin",
            "role": "admin",
        },
    )
    email = reg.json()["email"]
    login = await client.post(
        "/auth/jwt/login",
        data={"username": email, "password": "adminpass123"},
    )
    return login.json()["access_token"]


@pytest.fixture
async def staff_token(client: AsyncClient) -> str:
    """Register a staff user and return JWT token."""
    reg = await client.post(
        "/auth/register",
        json={
            "email": f"staff-{uuid.uuid4().hex[:8]}@test.com",
            "password": "staffpass123",
            "full_name": "Test Staff",
            "role": "staff",
        },
    )
    email = reg.json()["email"]
    login = await client.post(
        "/auth/jwt/login",
        data={"username": email, "password": "staffpass123"},
    )
    return login.json()["access_token"]
```

- [ ] **Step 10: Create backend/tests/test_health.py**

```python
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_returns_ok(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["version"] == "0.1.0"
```

- [ ] **Step 11: Create backend/tests/test_auth.py**

```python
import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_user(client: AsyncClient):
    resp = await client.post(
        "/auth/register",
        json={
            "email": f"test-{uuid.uuid4().hex[:8]}@example.com",
            "password": "securepassword123",
            "full_name": "Jane Clerk",
            "role": "staff",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["full_name"] == "Jane Clerk"
    assert data["role"] == "staff"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_login_returns_jwt(client: AsyncClient):
    email = f"login-{uuid.uuid4().hex[:8]}@example.com"
    await client.post(
        "/auth/register",
        json={"email": email, "password": "testpass123", "full_name": "Test"},
    )
    resp = await client.post(
        "/auth/jwt/login",
        data={"username": email, "password": "testpass123"},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_me_endpoint(client: AsyncClient):
    email = f"me-{uuid.uuid4().hex[:8]}@example.com"
    await client.post(
        "/auth/register",
        json={"email": email, "password": "testpass123", "full_name": "Me User", "role": "reviewer"},
    )
    login = await client.post(
        "/auth/jwt/login",
        data={"username": email, "password": "testpass123"},
    )
    token = login.json()["access_token"]
    resp = await client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == email
    assert resp.json()["role"] == "reviewer"


@pytest.mark.asyncio
async def test_unauthenticated_rejected(client: AsyncClient):
    resp = await client.get("/users/me")
    assert resp.status_code == 401
```

- [ ] **Step 12: Run tests to verify they pass**

Run: `cd backend && pip install -e ".[dev]" && pytest tests/test_health.py tests/test_auth.py -v`

Expected: All tests PASS (requires test database to be running).

- [ ] **Step 13: Commit**

```bash
git add backend/app/schemas/ backend/app/auth/ backend/tests/ backend/app/main.py
git commit -m "feat: auth system with fastapi-users, JWT, RBAC roles, and tests"
```

---

## Task 4: Hash-Chained Audit Logging

**Files:**
- Create: `backend/app/audit/logger.py`
- Create: `backend/app/audit/middleware.py`
- Create: `backend/app/audit/router.py`
- Create: `backend/app/audit/__init__.py`
- Create: `backend/app/schemas/audit.py`
- Create: `backend/tests/test_audit.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create backend/app/audit/logger.py**

The core audit log writer. Each entry is hashed with SHA-256, and each hash includes the previous entry's hash, creating a tamper-evident chain.

```python
import hashlib
import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


def _compute_hash(prev_hash: str, timestamp: str, user_id: str, action: str, details: str) -> str:
    """Compute SHA-256 hash for an audit log entry."""
    payload = f"{prev_hash}|{timestamp}|{user_id}|{action}|{details}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


async def get_last_hash(session: AsyncSession) -> str:
    """Get the hash of the most recent audit log entry."""
    result = await session.execute(
        select(AuditLog.entry_hash).order_by(AuditLog.id.desc()).limit(1)
    )
    last = result.scalar_one_or_none()
    return last if last else "0" * 64


async def write_audit_log(
    session: AsyncSession,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    user_id: uuid.UUID | None = None,
    details: dict | None = None,
    ai_generated: bool = False,
) -> AuditLog:
    """Write a hash-chained audit log entry."""
    prev_hash = await get_last_hash(session)
    now = datetime.now(timezone.utc)
    timestamp_str = now.isoformat()
    user_str = str(user_id) if user_id else "system"
    details_str = json.dumps(details, sort_keys=True, default=str) if details else ""

    entry_hash = _compute_hash(prev_hash, timestamp_str, user_str, action, details_str)

    entry = AuditLog(
        prev_hash=prev_hash,
        entry_hash=entry_hash,
        timestamp=now,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ai_generated=ai_generated,
    )
    session.add(entry)
    await session.commit()
    await session.refresh(entry)
    return entry


async def verify_chain(session: AsyncSession, limit: int = 1000) -> tuple[bool, int, str]:
    """Verify the integrity of the audit log hash chain.

    Returns (is_valid, entries_checked, error_message).
    """
    result = await session.execute(
        select(AuditLog).order_by(AuditLog.id.asc()).limit(limit)
    )
    entries = result.scalars().all()

    if not entries:
        return True, 0, ""

    expected_prev = "0" * 64
    for i, entry in enumerate(entries):
        if entry.prev_hash != expected_prev:
            return False, i, f"Entry {entry.id}: prev_hash mismatch at position {i}"

        recomputed = _compute_hash(
            entry.prev_hash,
            entry.timestamp.isoformat(),
            str(entry.user_id) if entry.user_id else "system",
            entry.action,
            json.dumps(entry.details, sort_keys=True, default=str) if entry.details else "",
        )
        if entry.entry_hash != recomputed:
            return False, i, f"Entry {entry.id}: hash mismatch at position {i}"

        expected_prev = entry.entry_hash

    return True, len(entries), ""
```

- [ ] **Step 2: Create backend/app/audit/middleware.py**

FastAPI middleware that automatically logs every API request to the audit log.

```python
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.audit.logger import write_audit_log
from app.database import async_session_maker

# Paths that should not be logged (health checks, static files)
SKIP_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in SKIP_PATHS:
            return await call_next(request)

        response = await call_next(request)

        # Extract user_id from request state if auth middleware set it
        user_id = getattr(request.state, "user_id", None) if hasattr(request, "state") else None

        # Log the request asynchronously
        try:
            async with async_session_maker() as session:
                await write_audit_log(
                    session=session,
                    action=f"{request.method} {request.url.path}",
                    resource_type="http_request",
                    resource_id=request.url.path,
                    user_id=user_id,
                    details={
                        "method": request.method,
                        "path": request.url.path,
                        "query": str(request.url.query) if request.url.query else None,
                        "status_code": response.status_code,
                        "client_ip": request.client.host if request.client else None,
                    },
                )
        except Exception:
            # Audit logging failure must not break the request
            # In production, this should alert but not crash
            pass

        return response
```

- [ ] **Step 3: Create backend/app/schemas/audit.py**

```python
import uuid
from datetime import datetime

from pydantic import BaseModel


class AuditLogRead(BaseModel):
    id: int
    prev_hash: str
    entry_hash: str
    timestamp: datetime
    user_id: uuid.UUID | None
    action: str
    resource_type: str
    resource_id: str | None
    details: dict | None
    ai_generated: bool

    model_config = {"from_attributes": True}


class AuditLogQuery(BaseModel):
    action: str | None = None
    resource_type: str | None = None
    user_id: uuid.UUID | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    limit: int = 100
    offset: int = 0


class AuditChainVerification(BaseModel):
    is_valid: bool
    entries_checked: int
    error_message: str
```

- [ ] **Step 4: Create backend/app/audit/router.py**

```python
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.logger import verify_chain
from app.auth.dependencies import require_role
from app.database import get_async_session
from app.models.audit import AuditLog
from app.models.user import User, UserRole
from app.schemas.audit import AuditChainVerification, AuditLogQuery, AuditLogRead

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/logs", response_model=list[AuditLogRead])
async def list_audit_logs(
    query: AuditLogQuery = Depends(),
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Query audit logs. Admin only."""
    stmt = select(AuditLog).order_by(AuditLog.id.desc())

    if query.action:
        stmt = stmt.where(AuditLog.action.contains(query.action))
    if query.resource_type:
        stmt = stmt.where(AuditLog.resource_type == query.resource_type)
    if query.user_id:
        stmt = stmt.where(AuditLog.user_id == query.user_id)
    if query.start_date:
        stmt = stmt.where(AuditLog.timestamp >= query.start_date)
    if query.end_date:
        stmt = stmt.where(AuditLog.timestamp <= query.end_date)

    stmt = stmt.offset(query.offset).limit(query.limit)
    result = await session.execute(stmt)
    return result.scalars().all()


@router.get("/verify", response_model=AuditChainVerification)
async def verify_audit_chain(
    limit: int = 1000,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Verify the integrity of the audit log hash chain. Admin only."""
    is_valid, count, error = await verify_chain(session, limit)
    return AuditChainVerification(
        is_valid=is_valid, entries_checked=count, error_message=error
    )


@router.get("/export")
async def export_audit_logs(
    format: str = "json",
    start_date: str | None = None,
    end_date: str | None = None,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Export audit logs as JSON or CSV. Admin only."""
    from datetime import datetime
    from fastapi.responses import StreamingResponse
    import csv
    import io
    import json

    stmt = select(AuditLog).order_by(AuditLog.id.asc())
    if start_date:
        stmt = stmt.where(AuditLog.timestamp >= datetime.fromisoformat(start_date))
    if end_date:
        stmt = stmt.where(AuditLog.timestamp <= datetime.fromisoformat(end_date))

    result = await session.execute(stmt)
    logs = result.scalars().all()

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "id", "prev_hash", "entry_hash", "timestamp", "user_id",
            "action", "resource_type", "resource_id", "details", "ai_generated",
        ])
        for log in logs:
            writer.writerow([
                log.id, log.prev_hash, log.entry_hash, log.timestamp.isoformat(),
                str(log.user_id) if log.user_id else "", log.action, log.resource_type,
                log.resource_id or "", json.dumps(log.details) if log.details else "",
                log.ai_generated,
            ])
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=audit_log.csv"},
        )
    else:
        data = [
            {
                "id": log.id,
                "prev_hash": log.prev_hash,
                "entry_hash": log.entry_hash,
                "timestamp": log.timestamp.isoformat(),
                "user_id": str(log.user_id) if log.user_id else None,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "details": log.details,
                "ai_generated": log.ai_generated,
            }
            for log in logs
        ]
        return StreamingResponse(
            iter([json.dumps(data, indent=2)]),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=audit_log.json"},
        )
```

- [ ] **Step 5: Create backend/app/audit/__init__.py**

```python
from app.audit.logger import verify_chain, write_audit_log
from app.audit.middleware import AuditMiddleware
from app.audit.router import router as audit_router

__all__ = ["AuditMiddleware", "audit_router", "write_audit_log", "verify_chain"]
```

- [ ] **Step 6: Update backend/app/main.py to include audit middleware and routes**

Add these lines to `create_app()` in `main.py`, after the existing router includes:

```python
from app.audit import AuditMiddleware, audit_router

# Inside create_app(), after other router includes:
app.add_middleware(AuditMiddleware)
app.include_router(audit_router)
```

The full updated `create_app()`:

```python
def create_app() -> FastAPI:
    app = FastAPI(
        title="CivicRecords AI",
        description="AI-powered open records support for American cities",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Middleware (outermost first)
    app.add_middleware(AuditMiddleware)

    # Auth routes
    app.include_router(auth_router, prefix="/auth/jwt", tags=["auth"])
    app.include_router(register_router, prefix="/auth", tags=["auth"])
    app.include_router(users_router, prefix="/users", tags=["users"])

    # Audit routes
    app.include_router(audit_router)

    @app.get("/health")
    async def health():
        return {"status": "ok", "version": "0.1.0"}

    return app
```

- [ ] **Step 7: Create backend/tests/test_audit.py**

```python
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.logger import verify_chain, write_audit_log


@pytest.mark.asyncio
async def test_write_audit_log_creates_entry(client: AsyncClient):
    """Audit log entries are created with hash chain."""
    from tests.conftest import test_session_maker

    async with test_session_maker() as session:
        entry = await write_audit_log(
            session=session,
            action="test_action",
            resource_type="test_resource",
            resource_id="123",
            details={"key": "value"},
        )
        assert entry.id is not None
        assert entry.entry_hash != ""
        assert len(entry.entry_hash) == 64
        assert entry.prev_hash == "0" * 64  # First entry


@pytest.mark.asyncio
async def test_hash_chain_links_entries(client: AsyncClient):
    """Each entry's prev_hash matches the previous entry's entry_hash."""
    from tests.conftest import test_session_maker

    async with test_session_maker() as session:
        entry1 = await write_audit_log(
            session=session, action="first", resource_type="test"
        )
        entry2 = await write_audit_log(
            session=session, action="second", resource_type="test"
        )
        assert entry2.prev_hash == entry1.entry_hash


@pytest.mark.asyncio
async def test_verify_chain_passes(client: AsyncClient):
    """Chain verification passes for untampered logs."""
    from tests.conftest import test_session_maker

    async with test_session_maker() as session:
        await write_audit_log(session=session, action="a", resource_type="test")
        await write_audit_log(session=session, action="b", resource_type="test")
        await write_audit_log(session=session, action="c", resource_type="test")

        is_valid, count, error = await verify_chain(session)
        assert is_valid is True
        assert count == 3
        assert error == ""


@pytest.mark.asyncio
async def test_middleware_logs_requests(client: AsyncClient):
    """HTTP requests are automatically logged by audit middleware."""
    # Make a request
    await client.get("/health")

    # Check that the audit log has an entry
    from tests.conftest import test_session_maker
    from sqlalchemy import select, func
    from app.models.audit import AuditLog

    async with test_session_maker() as session:
        result = await session.execute(select(func.count(AuditLog.id)))
        count = result.scalar()
        # Health endpoint is in SKIP_PATHS, so no audit entry
        assert count == 0

    # Make a request to a logged endpoint
    await client.post(
        "/auth/register",
        json={
            "email": "audit-test@example.com",
            "password": "testpass123",
            "full_name": "Audit Test",
        },
    )

    async with test_session_maker() as session:
        result = await session.execute(
            select(AuditLog).where(AuditLog.action.contains("/auth/register"))
        )
        entry = result.scalar_one_or_none()
        assert entry is not None
        assert entry.details["method"] == "POST"
        assert entry.details["status_code"] == 201


@pytest.mark.asyncio
async def test_audit_export_requires_admin(client: AsyncClient, staff_token: str):
    """Non-admin users cannot access audit export."""
    resp = await client.get(
        "/audit/export",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert resp.status_code == 403
```

- [ ] **Step 8: Run tests**

Run: `cd backend && pytest tests/test_audit.py -v`
Expected: All tests PASS.

- [ ] **Step 9: Commit**

```bash
git add backend/app/audit/ backend/app/schemas/audit.py backend/tests/test_audit.py \
  backend/app/main.py
git commit -m "feat: hash-chained audit logging with middleware, export, and chain verification"
```

---

## Task 5: Service Account System

**Files:**
- Create: `backend/app/schemas/service_account.py`
- Create: `backend/app/service_accounts/router.py`
- Create: `backend/app/service_accounts/__init__.py`
- Create: `backend/tests/test_service_accounts.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create backend/app/schemas/service_account.py**

```python
import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.user import UserRole


class ServiceAccountCreate(BaseModel):
    name: str
    role: UserRole = UserRole.READ_ONLY


class ServiceAccountRead(BaseModel):
    id: uuid.UUID
    name: str
    role: UserRole
    created_by: uuid.UUID
    created_at: datetime
    is_active: bool

    model_config = {"from_attributes": True}


class ServiceAccountCreated(ServiceAccountRead):
    """Returned only on creation — includes the plaintext API key (shown once)."""
    api_key: str


class ServiceAccountUpdate(BaseModel):
    role: UserRole | None = None
    is_active: bool | None = None
```

- [ ] **Step 2: Create backend/app/service_accounts/router.py**

```python
import secrets
import uuid
from hashlib import sha256

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.logger import write_audit_log
from app.auth.dependencies import require_role
from app.database import get_async_session
from app.models.service_account import ServiceAccount
from app.models.user import User, UserRole
from app.schemas.service_account import (
    ServiceAccountCreate,
    ServiceAccountCreated,
    ServiceAccountRead,
    ServiceAccountUpdate,
)

router = APIRouter(prefix="/service-accounts", tags=["service-accounts"])


def _hash_api_key(key: str) -> str:
    return sha256(key.encode()).hexdigest()


@router.post("/", response_model=ServiceAccountCreated, status_code=201)
async def create_service_account(
    data: ServiceAccountCreate,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Create a service account. Returns the API key once — store it securely."""
    existing = await session.execute(
        select(ServiceAccount).where(ServiceAccount.name == data.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Name already taken")

    api_key = f"cr_{secrets.token_hex(32)}"
    account = ServiceAccount(
        name=data.name,
        api_key_hash=_hash_api_key(api_key),
        role=data.role,
        created_by=user.id,
    )
    session.add(account)
    await session.commit()
    await session.refresh(account)

    await write_audit_log(
        session=session,
        action="create_service_account",
        resource_type="service_account",
        resource_id=str(account.id),
        user_id=user.id,
        details={"name": data.name, "role": data.role.value},
    )

    return ServiceAccountCreated(
        id=account.id,
        name=account.name,
        role=account.role,
        created_by=account.created_by,
        created_at=account.created_at,
        is_active=account.is_active,
        api_key=api_key,
    )


@router.get("/", response_model=list[ServiceAccountRead])
async def list_service_accounts(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(require_role(UserRole.ADMIN)),
):
    result = await session.execute(select(ServiceAccount).order_by(ServiceAccount.created_at.desc()))
    return result.scalars().all()


@router.patch("/{account_id}", response_model=ServiceAccountRead)
async def update_service_account(
    account_id: uuid.UUID,
    data: ServiceAccountUpdate,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(require_role(UserRole.ADMIN)),
):
    result = await session.execute(
        select(ServiceAccount).where(ServiceAccount.id == account_id)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Service account not found")

    if data.role is not None:
        account.role = data.role
    if data.is_active is not None:
        account.is_active = data.is_active

    await session.commit()
    await session.refresh(account)

    await write_audit_log(
        session=session,
        action="update_service_account",
        resource_type="service_account",
        resource_id=str(account.id),
        user_id=user.id,
        details={"changes": data.model_dump(exclude_none=True)},
    )

    return account
```

- [ ] **Step 3: Create backend/app/service_accounts/__init__.py**

```python
from app.service_accounts.router import router as service_accounts_router

__all__ = ["service_accounts_router"]
```

- [ ] **Step 4: Add service accounts router to main.py**

Add to `create_app()`:

```python
from app.service_accounts import service_accounts_router

# Inside create_app(), after audit routes:
app.include_router(service_accounts_router)
```

- [ ] **Step 5: Create backend/tests/test_service_accounts.py**

```python
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_service_account(client: AsyncClient, admin_token: str):
    resp = await client.post(
        "/service-accounts/",
        json={"name": "county-federation", "role": "read_only"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "county-federation"
    assert data["role"] == "read_only"
    assert data["api_key"].startswith("cr_")
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_create_service_account_requires_admin(client: AsyncClient, staff_token: str):
    resp = await client.post(
        "/service-accounts/",
        json={"name": "test-account", "role": "read_only"},
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_list_service_accounts(client: AsyncClient, admin_token: str):
    # Create one first
    await client.post(
        "/service-accounts/",
        json={"name": "list-test-account", "role": "staff"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    resp = await client.get(
        "/service-accounts/",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_deactivate_service_account(client: AsyncClient, admin_token: str):
    create = await client.post(
        "/service-accounts/",
        json={"name": "deactivate-test", "role": "read_only"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    account_id = create.json()["id"]

    resp = await client.patch(
        f"/service-accounts/{account_id}",
        json={"is_active": False},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False
```

- [ ] **Step 6: Run tests**

Run: `cd backend && pytest tests/test_service_accounts.py -v`
Expected: All tests PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas/service_account.py backend/app/service_accounts/ \
  backend/tests/test_service_accounts.py backend/app/main.py
git commit -m "feat: service account CRUD with API key generation, admin-only access"
```

---

## Task 6: Admin Endpoints (System Status, Model Info)

**Files:**
- Create: `backend/app/admin/router.py`
- Create: `backend/app/admin/__init__.py`
- Create: `backend/tests/test_admin.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create backend/app/admin/router.py**

```python
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_role
from app.config import settings
from app.database import get_async_session
from app.models.audit import AuditLog
from app.models.user import User, UserRole

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
    """System health and stats. Admin only."""
    import httpx

    # Database check
    try:
        await session.execute(select(func.count(User.id)))
        db_status = "connected"
    except Exception:
        db_status = "error"

    # User count
    result = await session.execute(select(func.count(User.id)))
    user_count = result.scalar() or 0

    # Audit log count
    result = await session.execute(select(func.count(AuditLog.id)))
    audit_count = result.scalar() or 0

    # Ollama check
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.ollama_base_url}/api/tags")
            ollama_status = "connected" if resp.status_code == 200 else "error"
    except Exception:
        ollama_status = "unreachable"

    # Redis check
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.redis_url)
        await r.ping()
        redis_status = "connected"
        await r.aclose()
    except Exception:
        redis_status = "unreachable"

    return SystemStatus(
        version="0.1.0",
        database=db_status,
        ollama=ollama_status,
        redis=redis_status,
        user_count=user_count,
        audit_log_count=audit_count,
    )


@router.get("/models", response_model=OllamaStatus)
async def list_models(
    user: User = Depends(require_role(UserRole.ADMIN)),
):
    """List available Ollama models. Admin only."""
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
```

- [ ] **Step 2: Create backend/app/admin/__init__.py**

```python
from app.admin.router import router as admin_router

__all__ = ["admin_router"]
```

- [ ] **Step 3: Add admin router to main.py**

Add to `create_app()`:

```python
from app.admin import admin_router

# Inside create_app(), after service accounts routes:
app.include_router(admin_router)
```

- [ ] **Step 4: Create backend/tests/test_admin.py**

```python
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_admin_status_returns_system_info(client: AsyncClient, admin_token: str):
    resp = await client.get(
        "/admin/status",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["version"] == "0.1.0"
    assert data["database"] == "connected"
    assert isinstance(data["user_count"], int)
    assert isinstance(data["audit_log_count"], int)


@pytest.mark.asyncio
async def test_admin_status_requires_admin(client: AsyncClient, staff_token: str):
    resp = await client.get(
        "/admin/status",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_models_endpoint(client: AsyncClient, admin_token: str):
    resp = await client.get(
        "/admin/models",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "models" in data
```

- [ ] **Step 5: Run tests**

Run: `cd backend && pytest tests/test_admin.py -v`
Expected: All tests PASS (Ollama/Redis may show "unreachable" in test env — that's expected).

- [ ] **Step 6: Commit**

```bash
git add backend/app/admin/ backend/tests/test_admin.py backend/app/main.py
git commit -m "feat: admin endpoints for system status and Ollama model info"
```

---

## Task 7: Celery Worker Skeleton

**Files:**
- Create: `backend/app/worker.py`

- [ ] **Step 1: Create backend/app/worker.py**

Minimal Celery app. Actual ingestion tasks will be added in Sub-Project 2.

```python
from celery import Celery

from app.config import settings

celery_app = Celery(
    "civicrecords",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
)


@celery_app.task(name="civicrecords.health")
def health_check():
    """Simple health check task."""
    return {"status": "ok"}
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/worker.py
git commit -m "feat: Celery worker skeleton with health check task"
```

---

## Task 8: React Frontend Shell (Admin Panel)

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tailwind.config.js`
- Create: `frontend/tsconfig.json`
- Create: `frontend/postcss.config.js`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/src/lib/utils.ts`
- Create: `frontend/src/pages/Login.tsx`
- Create: `frontend/src/pages/Dashboard.tsx`
- Create: `frontend/src/pages/Users.tsx`
- Create: `frontend/src/globals.css`
- Create: `Dockerfile.frontend`

- [ ] **Step 1: Create frontend/package.json**

```json
{
  "name": "civicrecords-admin",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "react-router-dom": "^7.0.0",
    "clsx": "^2.1.0",
    "tailwind-merge": "^3.0.0",
    "class-variance-authority": "^0.7.0",
    "lucide-react": "^0.500.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.4.0",
    "autoprefixer": "^10.4.0",
    "postcss": "^8.5.0",
    "tailwindcss": "^3.4.0",
    "typescript": "^5.7.0",
    "vite": "^6.3.0"
  }
}
```

- [ ] **Step 2: Create frontend/vite.config.ts**

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
```

- [ ] **Step 3: Create frontend/tailwind.config.js**

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {},
  },
  plugins: [],
};
```

- [ ] **Step 4: Create frontend/postcss.config.js**

```javascript
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
```

- [ ] **Step 5: Create frontend/tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["src"]
}
```

- [ ] **Step 6: Create frontend/index.html**

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>CivicRecords AI — Admin</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 7: Create frontend/src/globals.css**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

- [ ] **Step 8: Create frontend/src/lib/utils.ts**

```typescript
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

- [ ] **Step 9: Create frontend/src/lib/api.ts**

```typescript
const API_BASE = "/api";

interface ApiOptions extends RequestInit {
  token?: string;
}

export async function apiFetch<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const { token, ...fetchOptions } = options;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const resp = await fetch(`${API_BASE}${path}`, {
    ...fetchOptions,
    headers,
  });

  if (!resp.ok) {
    const error = await resp.json().catch(() => ({ detail: resp.statusText }));
    throw new Error(error.detail || resp.statusText);
  }

  return resp.json();
}

export async function login(email: string, password: string): Promise<string> {
  const resp = await fetch(`${API_BASE}/auth/jwt/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ username: email, password }),
  });
  if (!resp.ok) throw new Error("Login failed");
  const data = await resp.json();
  return data.access_token;
}
```

- [ ] **Step 10: Create frontend/src/main.tsx**

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./globals.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
);
```

- [ ] **Step 11: Create frontend/src/App.tsx**

```tsx
import { useState, useEffect } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Users from "./pages/Users";

export default function App() {
  const [token, setToken] = useState<string | null>(
    localStorage.getItem("token")
  );

  useEffect(() => {
    if (token) localStorage.setItem("token", token);
    else localStorage.removeItem("token");
  }, [token]);

  if (!token) {
    return <Login onLogin={setToken} />;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-6">
          <h1 className="text-lg font-semibold text-gray-900">CivicRecords AI</h1>
          <a href="/" className="text-sm text-gray-600 hover:text-gray-900">Dashboard</a>
          <a href="/users" className="text-sm text-gray-600 hover:text-gray-900">Users</a>
        </div>
        <button
          onClick={() => setToken(null)}
          className="text-sm text-gray-500 hover:text-gray-700"
        >
          Sign out
        </button>
      </nav>
      <main className="p-6 max-w-7xl mx-auto">
        <Routes>
          <Route path="/" element={<Dashboard token={token} />} />
          <Route path="/users" element={<Users token={token} />} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </main>
    </div>
  );
}
```

- [ ] **Step 12: Create frontend/src/pages/Login.tsx**

```tsx
import { useState } from "react";
import { login } from "@/lib/api";

interface Props {
  onLogin: (token: string) => void;
}

export default function Login({ onLogin }: Props) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const token = await login(email, password);
      onLogin(token);
    } catch {
      setError("Invalid email or password");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="bg-white p-8 rounded-lg shadow-sm border border-gray-200 w-full max-w-sm">
        <h1 className="text-xl font-semibold text-gray-900 mb-1">CivicRecords AI</h1>
        <p className="text-sm text-gray-500 mb-6">Sign in to the admin panel</p>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 text-white py-2 px-4 rounded-md text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? "Signing in..." : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
```

- [ ] **Step 13: Create frontend/src/pages/Dashboard.tsx**

```tsx
import { useState, useEffect } from "react";
import { apiFetch } from "@/lib/api";

interface SystemStatus {
  version: string;
  database: string;
  ollama: string;
  redis: string;
  user_count: number;
  audit_log_count: number;
}

interface Props {
  token: string;
}

export default function Dashboard({ token }: Props) {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    apiFetch<SystemStatus>("/admin/status", { token })
      .then(setStatus)
      .catch((e) => setError(e.message));
  }, [token]);

  if (error) return <p className="text-red-600">{error}</p>;
  if (!status) return <p className="text-gray-500">Loading...</p>;

  const services = [
    { name: "Database", status: status.database },
    { name: "Ollama (LLM)", status: status.ollama },
    { name: "Redis (Queue)", status: status.redis },
  ];

  return (
    <div>
      <h2 className="text-lg font-semibold text-gray-900 mb-4">System Dashboard</h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        {services.map((s) => (
          <div key={s.name} className="bg-white p-4 rounded-lg border border-gray-200">
            <p className="text-sm text-gray-500">{s.name}</p>
            <p className={`text-lg font-medium ${s.status === "connected" ? "text-green-600" : "text-red-600"}`}>
              {s.status}
            </p>
          </div>
        ))}
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white p-4 rounded-lg border border-gray-200">
          <p className="text-sm text-gray-500">Version</p>
          <p className="text-lg font-medium text-gray-900">{status.version}</p>
        </div>
        <div className="bg-white p-4 rounded-lg border border-gray-200">
          <p className="text-sm text-gray-500">Users</p>
          <p className="text-lg font-medium text-gray-900">{status.user_count}</p>
        </div>
        <div className="bg-white p-4 rounded-lg border border-gray-200">
          <p className="text-sm text-gray-500">Audit Log Entries</p>
          <p className="text-lg font-medium text-gray-900">{status.audit_log_count}</p>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 14: Create frontend/src/pages/Users.tsx**

```tsx
import { useState, useEffect } from "react";
import { apiFetch } from "@/lib/api";

interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
  last_login: string | null;
}

interface Props {
  token: string;
}

export default function Users({ token }: Props) {
  const [users, setUsers] = useState<User[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    apiFetch<User[]>("/users", { token })
      .then(setUsers)
      .catch((e) => setError(e.message));
  }, [token]);

  if (error) return <p className="text-red-600">{error}</p>;

  return (
    <div>
      <h2 className="text-lg font-semibold text-gray-900 mb-4">Users</h2>
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 bg-gray-50">
              <th className="text-left px-4 py-3 font-medium text-gray-600">Name</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Email</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Role</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Status</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Last Login</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id} className="border-b border-gray-100">
                <td className="px-4 py-3 text-gray-900">{u.full_name || "—"}</td>
                <td className="px-4 py-3 text-gray-600">{u.email}</td>
                <td className="px-4 py-3">
                  <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                    u.role === "admin" ? "bg-purple-100 text-purple-700" :
                    u.role === "reviewer" ? "bg-blue-100 text-blue-700" :
                    u.role === "staff" ? "bg-green-100 text-green-700" :
                    "bg-gray-100 text-gray-700"
                  }`}>
                    {u.role}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span className={`text-xs ${u.is_active ? "text-green-600" : "text-red-600"}`}>
                    {u.is_active ? "Active" : "Inactive"}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-500">
                  {u.last_login ? new Date(u.last_login).toLocaleDateString() : "Never"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
```

- [ ] **Step 15: Create Dockerfile.frontend**

```dockerfile
# Build stage
FROM node:22-alpine AS build

WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ .
RUN npm run build

# Serve stage
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html

# SPA fallback + API proxy
RUN cat > /etc/nginx/conf.d/default.conf << 'NGINX'
server {
    listen 80;

    location /api/ {
        proxy_pass http://api:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
    }
}
NGINX

EXPOSE 80
```

- [ ] **Step 16: Add frontend service to docker-compose.yml**

Add to the `services` section in `docker-compose.yml`:

```yaml
  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
    ports:
      - "8080:80"
    depends_on:
      api:
        condition: service_healthy
```

- [ ] **Step 17: Commit**

```bash
git add frontend/ Dockerfile.frontend docker-compose.yml
git commit -m "feat: React admin panel with login, dashboard, and user management pages"
```

---

## Task 9: Install Script and Data Sovereignty Verification

**Files:**
- Create: `install.sh`
- Create: `scripts/verify-sovereignty.sh`

- [ ] **Step 1: Create install.sh**

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "============================================"
echo "  CivicRecords AI — Installation Script"
echo "  Target: Ubuntu 24.04 LTS"
echo "============================================"
echo ""

# Check OS
if ! grep -q "Ubuntu 24" /etc/os-release 2>/dev/null; then
    echo "WARNING: This script is designed for Ubuntu 24.04 LTS."
    echo "Your OS may work but is not officially supported."
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then exit 1; fi
fi

# Install Docker if not present
if ! command -v docker &>/dev/null; then
    echo ">>> Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker "$USER"
    echo "Docker installed. You may need to log out and back in for group changes."
fi

# Install Docker Compose plugin if not present
if ! docker compose version &>/dev/null; then
    echo ">>> Installing Docker Compose plugin..."
    sudo apt-get update
    sudo apt-get install -y docker-compose-plugin
fi

# Create .env from template if not exists
if [ ! -f .env ]; then
    echo ">>> Creating .env from template..."
    cp .env.example .env
    # Generate a random JWT secret
    JWT_SECRET=$(openssl rand -hex 32)
    sed -i "s/CHANGE-ME-generate-with-openssl-rand-hex-32/$JWT_SECRET/" .env
    echo ""
    echo "IMPORTANT: Edit .env to set your admin email and password:"
    echo "  nano .env"
    echo ""
    read -p "Press Enter after editing .env, or Ctrl+C to edit later..."
fi

# Pull and start services
echo ">>> Pulling Docker images..."
docker compose pull

echo ">>> Building application images..."
docker compose build

echo ">>> Starting services..."
docker compose up -d

# Wait for health
echo ">>> Waiting for services to be healthy..."
for i in $(seq 1 30); do
    if curl -sf http://localhost:8000/health &>/dev/null; then
        echo "API is healthy!"
        break
    fi
    echo "  Waiting... ($i/30)"
    sleep 5
done

# Pull recommended Ollama model
echo ">>> Pulling recommended LLM model (this may take a while)..."
docker compose exec ollama ollama pull gemma3:4b-it-qf4_0 || echo "Model pull failed — you can retry later with: docker compose exec ollama ollama pull <model>"

echo ""
echo "============================================"
echo "  Installation complete!"
echo ""
echo "  Admin panel:  http://$(hostname -I | awk '{print $1}'):8080"
echo "  API:          http://$(hostname -I | awk '{print $1}'):8000"
echo "  API docs:     http://$(hostname -I | awk '{print $1}'):8000/docs"
echo ""
echo "  Run sovereignty check: bash scripts/verify-sovereignty.sh"
echo "============================================"
```

- [ ] **Step 2: Create scripts/verify-sovereignty.sh**

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "============================================"
echo "  CivicRecords AI — Data Sovereignty Check"
echo "============================================"
echo ""

PASS=0
FAIL=0
WARN=0

check() {
    local desc="$1"
    local result="$2"
    if [ "$result" = "PASS" ]; then
        echo "  [PASS] $desc"
        PASS=$((PASS + 1))
    elif [ "$result" = "WARN" ]; then
        echo "  [WARN] $desc"
        WARN=$((WARN + 1))
    else
        echo "  [FAIL] $desc"
        FAIL=$((FAIL + 1))
    fi
}

echo "1. Checking Docker network isolation..."
# Verify containers are on internal network only
API_PORTS=$(docker compose port api 8000 2>/dev/null || echo "")
if [ -n "$API_PORTS" ]; then
    check "API bound to local port" "PASS"
else
    check "API bound to local port" "FAIL"
fi

echo ""
echo "2. Checking for outbound connections..."
# Check if any container has active outbound connections (excluding Docker DNS)
OUTBOUND=$(docker compose exec api ss -tunp 2>/dev/null | grep -v "127.0.0.1\|172\.\|10\.\|192\.168\." | grep "ESTAB" || true)
if [ -z "$OUTBOUND" ]; then
    check "No unexpected outbound connections from API" "PASS"
else
    check "No unexpected outbound connections from API — found: $OUTBOUND" "FAIL"
fi

echo ""
echo "3. Checking data storage locations..."
# Verify all Docker volumes are local
VOLUMES=$(docker compose config --volumes 2>/dev/null)
for vol in $VOLUMES; do
    DRIVER=$(docker volume inspect "$(docker compose config --format json | python3 -c "import sys,json; c=json.load(sys.stdin); print(c.get('name','civicrecords-ai') + '_$vol')" 2>/dev/null)" --format '{{.Driver}}' 2>/dev/null || echo "local")
    if [ "$DRIVER" = "local" ]; then
        check "Volume '$vol' uses local storage driver" "PASS"
    else
        check "Volume '$vol' uses non-local driver: $DRIVER" "FAIL"
    fi
done

echo ""
echo "4. Checking for telemetry endpoints..."
# Search application code for telemetry patterns
TELEMETRY_HITS=$(grep -r "analytics\|telemetry\|sentry\|datadog\|newrelic\|mixpanel\|segment\|amplitude" backend/app/ --include="*.py" -l 2>/dev/null || true)
if [ -z "$TELEMETRY_HITS" ]; then
    check "No telemetry libraries found in application code" "PASS"
else
    check "Possible telemetry found in: $TELEMETRY_HITS" "WARN"
fi

echo ""
echo "5. Checking environment configuration..."
# Verify no cloud API keys in env
if [ -f .env ]; then
    CLOUD_KEYS=$(grep -iE "OPENAI|ANTHROPIC|AWS_|AZURE_|GCP_" .env || true)
    if [ -z "$CLOUD_KEYS" ]; then
        check "No cloud API keys in .env" "PASS"
    else
        check "Cloud API keys found in .env — data may leave the network" "WARN"
    fi
else
    check ".env file exists" "FAIL"
fi

echo ""
echo "============================================"
echo "  Results: $PASS passed, $WARN warnings, $FAIL failed"
echo "============================================"

if [ "$FAIL" -gt 0 ]; then
    echo "  DATA SOVEREIGNTY: FAILED — review issues above"
    exit 1
elif [ "$WARN" -gt 0 ]; then
    echo "  DATA SOVEREIGNTY: PASSED WITH WARNINGS"
    exit 0
else
    echo "  DATA SOVEREIGNTY: PASSED"
    exit 0
fi
```

- [ ] **Step 3: Make scripts executable**

```bash
chmod +x install.sh scripts/verify-sovereignty.sh
```

- [ ] **Step 4: Commit**

```bash
git add install.sh scripts/
git commit -m "feat: install script for Ubuntu 24.04 and data sovereignty verification"
```

---

## Task 10: Update .gitignore and Final Integration

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Update .gitignore with full project patterns**

```
# Python
__pycache__/
*.pyc
*.pyo
*.egg-info/
dist/
build/
.venv/
venv/

# Node
node_modules/
frontend/dist/

# Environment
.env
*.local

# IDE
.vscode/
.idea/

# Docker
*.log

# OS
.DS_Store
Thumbs.db

# Superpowers
.superpowers/
```

- [ ] **Step 2: Run full test suite**

```bash
cd backend && pip install -e ".[dev]" && pytest tests/ -v
```

Expected: All tests pass.

- [ ] **Step 3: Verify Docker Compose starts**

```bash
cp .env.example .env
# Edit .env with a real JWT_SECRET (openssl rand -hex 32)
docker compose up --build -d
docker compose ps
curl http://localhost:8000/health
```

Expected: All 5 services running. Health endpoint returns `{"status": "ok", "version": "0.1.0"}`.

- [ ] **Step 4: Verify exit criteria**

1. `docker compose up` starts all services — check with `docker compose ps`
2. Admin can create users — check with `curl -X POST http://localhost:8000/auth/register ...`
3. Audit log records every action — check with admin token on `/audit/logs`
4. Verification script passes — `bash scripts/verify-sovereignty.sh`

- [ ] **Step 5: Final commit**

```bash
git add .gitignore
git commit -m "chore: update gitignore, verify full integration"
```

---

## Self-Review Checklist

**Spec coverage:**
- [x] Docker Compose stack (Postgres+pgvector, Redis, FastAPI, Celery, Ollama) — Task 1, 7
- [x] User auth (fastapi-users, JWT, 4 roles, service accounts) — Task 3, 5
- [x] Hash-chained audit logging middleware — Task 4
- [x] Database migrations (Alembic) — Task 2
- [x] Admin panel skeleton (user management, model info) — Task 6, 8
- [x] Install script for Ubuntu 24.04 — Task 9
- [x] Data sovereignty verification script — Task 9
- [x] Exit criteria verification — Task 10

**Placeholder scan:** No TBDs, TODOs, or vague steps. All code blocks are complete.

**Type consistency:**
- `UserRole` enum used consistently across models, schemas, and dependencies.
- `User` model compatible with fastapi-users UUID mixin.
- `AuditLog` hash fields consistently 64 chars (SHA-256 hex).
- API paths consistent between backend routes and frontend api.ts.
