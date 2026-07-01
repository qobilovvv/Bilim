# Bilim — Architecture & Codebase Reference

> **Version:** 1.0.0  
> **Stack:** Python 3.11 · FastAPI · SQLAlchemy (Async) · PostgreSQL · Alembic · Docker  
> **Last updated:** 2026-07-01

---

## Table of Contents

1. [High-Level Overview](#1-high-level-overview)
2. [Directory Structure](#2-directory-structure)
3. [Layered Architecture](#3-layered-architecture)
4. [Infrastructure Layer](#4-infrastructure-layer)
5. [Database Models](#5-database-models)
6. [Repository Layer](#6-repository-layer)
7. [Service Layer](#7-service-layer)
8. [API Layer](#8-api-layer)
9. [Security & Authentication](#9-security--authentication)
10. [Schemas (DTOs)](#10-schemas-dtos)
11. [Migrations (Alembic)](#11-migrations-alembic)
12. [Docker & Deployment](#12-docker--deployment)
13. [CI/CD Pipeline](#13-cicd-pipeline)
14. [Environment Variables](#14-environment-variables)
15. [Request Lifecycle](#15-request-lifecycle)
16. [Key Dependencies](#16-key-dependencies)

---

## 1. High-Level Overview

**Bilim** is an async REST API built with **FastAPI** that serves as a backend for an educational/marketplace platform. The application follows a **clean, layered architecture** with clear separation between API handlers, business logic (services), data access (repositories), and infrastructure concerns.

```
┌─────────────────────────────────────────────────────────────┐
│                        Client                               │
└──────────────────────────┬──────────────────────────────────┘
                           │  HTTP (JSON)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Application                       │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────────────┐ │
│  │  CORS    │  │ Static   │  │   /healthz                │ │
│  │Middleware│  │  Files   │  │   (Health Check)          │ │
│  └──────────┘  └──────────┘  └───────────────────────────┘ │
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │              API Router  (/api/v1)                      ││
│  │  ┌──────────────────┐  ┌──────────────────────────────┐││
│  │  │  Auth Handlers   │  │  Category Handlers           │││
│  │  │  /api/v1/auth/*  │  │  /api/v1/categories/*       │││
│  │  └────────┬─────────┘  └──────────────┬───────────────┘││
│  └───────────┼───────────────────────────┼────────────────┘│
│              │                           │                  │
│  ┌───────────▼───────────────────────────▼────────────────┐│
│  │                  Service Layer                         ││
│  │  UsersService  │ CategoriesService │ PasswordResetSvc  ││
│  └───────────┬───────────────────────────┬────────────────┘│
│              │                           │                  │
│  ┌───────────▼───────────────────────────▼────────────────┐│
│  │                Repository Layer                        ││
│  │  UsersRepo   │  CategoriesRepo  │  PasswordResetRepo  ││
│  └───────────┬───────────────────────────┬────────────────┘│
│              │                           │                  │
│  ┌───────────▼───────────────────────────▼────────────────┐│
│  │               Infrastructure                           ││
│  │   AsyncSession (SQLAlchemy)  │  EskizClient (SMS)      ││
│  └───────────┬───────────────────────────┬────────────────┘│
└──────────────┼───────────────────────────┼──────────────────┘
               │                           │
       ┌───────▼──────┐          ┌─────────▼────────┐
       │  PostgreSQL   │          │  Eskiz SMS API   │
       │   (asyncpg)   │          │  (External)      │
       └──────────────┘          └──────────────────┘
```

---

## 2. Directory Structure

```
Bilim/
├── .env                          # Environment variables (not committed)
├── .env.example                  # Template for environment configuration
├── .github/
│   └── workflows/
│       └── deploy.yml            # GitHub Actions CD pipeline
├── .gitignore
├── .dockerignore
├── alembic.ini                   # Alembic configuration
├── alembic/
│   ├── env.py                    # Migration environment (async→sync URL conversion)
│   ├── script.py.mako            # Migration template
│   └── versions/                 # Migration files
│       ├── 459b5031b527_initial_migration.py
│       ├── c389eb12818f_initial_migration.py
│       ├── 04af23d24fab_add_username_column_and_make_phone_.py
│       ├── 07be93a1e1e2_add_categories_table.py
│       ├── 1a3cece44193_change_category_name_to_jsonb.py
│       ├── 40c1b21e0f5e_add_seller_profile_table.py
│       └── 5dd6b9efb16e_add_password_reset_codes_table.py
├── docker/
│   ├── Dockerfile                # Python 3.11-slim based image
│   ├── docker-compose.yml        # Development: API + Postgres + Redis
│   ├── docker-compose.prod.yml   # Production: resource limits, restart policies
│   └── .volumes/                 # Persistent data (gitignored)
├── documentation/
│   ├── admin.md                  # Admin user management docs
│   ├── agents.md                 # ← THIS FILE — Architecture reference
│   ├── migration.md              # Database migration guide
│   └── vps_setup.md              # VPS deployment guide
├── requirements.txt              # Python dependencies (pinned versions)
├── scripts/
│   ├── __init__.py
│   └── create_admin.py           # CLI script to create admin users
└── src/
    ├── main.py                   # Application entry point & factory
    ├── api/
    │   ├── routes.py             # Central router aggregation
    │   └── v1/
    │       ├── auth_handlers.py  # Auth & profile endpoints
    │       └── category_handlers.py  # Category CRUD endpoints
    ├── domain/                   # (Reserved — currently empty)
    ├── infrastructure/
    │   ├── config.py             # Pydantic Settings (env-based config)
    │   ├── database.py           # SQLAlchemy async engine, session factory
    │   └── eskiz.py              # Eskiz SMS client (HTTP-based)
    ├── models/
    │   ├── __init__.py           # Model registry (exports all models)
    │   ├── user.py               # User + SellerProfile models
    │   ├── category.py           # Category model (self-referential tree)
    │   └── password_reset.py     # PasswordResetCode model
    ├── repositories/
    │   ├── interfaces.py         # ABC interfaces for all repositories
    │   ├── users_repo.py         # User repository implementation
    │   ├── categories_repo.py    # Category repository implementation
    │   └── password_reset_repo.py # Password reset repository implementation
    ├── schemas/
    │   ├── auth_schemas.py       # Auth/user Pydantic request/response schemas
    │   └── category_schemas.py   # Category Pydantic request/response schemas
    ├── security/
    │   ├── dependencies.py       # FastAPI dependencies (get_current_user, get_current_admin)
    │   ├── localization.py       # Accept-Language header parsing
    │   ├── passwords.py          # Argon2 password hashing/verification
    │   └── tokens.py             # JWT access/refresh token generation & verification
    └── services/
        ├── users_scv.py          # User business logic (registration, login, profile)
        ├── categories_scv.py     # Category business logic (CRUD, hierarchy)
        └── password_reset_scv.py # Password reset flow (SMS code, verify, reset)
```

---

## 3. Layered Architecture

The codebase follows a **4-layer architecture** with one-way dependency flow:

| Layer | Responsibility | Files |
|---|---|---|
| **API (Handlers)** | HTTP request/response, routing, serialization | `src/api/` |
| **Service** | Business logic, validation, orchestration | `src/services/` |
| **Repository** | Data access, SQLAlchemy queries | `src/repositories/` |
| **Infrastructure** | Database engine, config, external clients | `src/infrastructure/` |

**Dependency flow:** `API → Service → Repository → Infrastructure`

Cross-cutting concerns (security, localization) live in `src/security/` and are injected via FastAPI's `Depends()` system.

---

## 4. Infrastructure Layer

### 4.1 Configuration — `src/infrastructure/config.py`

Centralized settings using **Pydantic Settings**. All values are loaded from `.env`:

| Setting | Type | Default | Description |
|---|---|---|---|
| `PROJECT_NAME` | `str` | `"Bilim"` | App display name |
| `VERSION` | `str` | `"1.0.0"` | API version |
| `CORS_ORIGINS` | `list[str]` | `["*"]` | Allowed CORS origins |
| `DATABASE_URL` | `str` | — (required) | PostgreSQL async connection string |
| `JWT_SECRET_KEY` | `str` | `"secrett"` | JWT signing secret |
| `JWT_ALGORITHM` | `str` | `"HS256"` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `int` | `60` | Access token TTL |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `int` | `30` | Refresh token TTL |
| `ESKIZ_BASE_URL` | `str` | `"https://notify.eskiz.uz/api"` | Eskiz SMS API base URL |
| `ESKIZ_EMAIL` | `str` | `""` | Eskiz account email |
| `ESKIZ_PASSWORD` | `str` | `""` | Eskiz account password |
| `ESKIZ_FROM` | `str` | `"4546"` | SMS sender ID |

Singleton instance: `settings = Settings()`

### 4.2 Database — `src/infrastructure/database.py`

- **Engine:** Async SQLAlchemy engine with `asyncpg` driver
  - Connection pool: `pool_size=20`, `max_overflow=10`
  - Connection recycling every 3600s
  - `pool_pre_ping=True` for stale connection detection
- **Session Factory:** `async_sessionmaker` with `expire_on_commit=False`
- **Base:** `declarative_base()` — all models inherit from this
- **Dependency:** `get_db_session()` — async generator yielding a session per request with automatic rollback on error

### 4.3 SMS Client — `src/infrastructure/eskiz.py`

`EskizClient` — HTTP client for the Eskiz SMS gateway:

- **Authentication:** Email/password → Bearer token
- **Token refresh:** Automatic re-authentication on 401 responses
- **SMS sending:** Sends messages via Eskiz API, handles status validation
- Singleton instance: `eskiz_client = EskizClient()`

---

## 5. Database Models

All models inherit from `Base` (SQLAlchemy `declarative_base`) and are registered in `src/models/__init__.py`.

### 5.1 User — `src/models/user.py`

```
┌──────────────────────────────────────┐
│              users                   │
├──────────────────────────────────────┤
│ id          │ Integer (PK)           │
│ first_name  │ String (NOT NULL)      │
│ last_name   │ String (nullable)      │
│ phone       │ String (unique, index) │
│ username    │ String (unique, index) │
│ email       │ String (unique, index) │
│ password    │ String (NOT NULL)      │
│ avatar      │ String (nullable)      │
│ type        │ String (default: user) │
│ is_active   │ Boolean (default: T)   │
│ is_blocked  │ Boolean (default: F)   │
│ is_superuser│ Boolean (default: F)   │
│ created_at  │ DateTime (auto)        │
│ updated_at  │ DateTime (auto)        │
│ last_login  │ DateTime (nullable)    │
└──────────────────────────────────────┘
         │
         │ 1:1 (cascade: all, delete-orphan)
         ▼
┌──────────────────────────────────────┐
│         seller_profiles              │
├──────────────────────────────────────┤
│ id                   │ Integer (PK)  │
│ user_id              │ FK → users.id │
│ years_of_experience  │ Integer       │
│ portfolio            │ String        │
│ description          │ String        │
└──────────────────────────────────────┘
```

**User Types** (defined in `UserType` class):
- `admin` — Full system access, logs in via username
- `author` — Content author (reserved)
- `user` — Regular end user, logs in via phone
- `seller` — Seller with extended profile, logs in via phone

### 5.2 Category — `src/models/category.py`

```
┌──────────────────────────────────────────┐
│             categories                   │
├──────────────────────────────────────────┤
│ id         │ Integer (PK)                │
│ name       │ JSONB (localized dict)      │
│            │ {"ru":"…", "uz":"…","en":"…"}│
│ path       │ String (unique, index)      │
│ parent_id  │ FK → categories.id (self)   │
│ level      │ Integer (1 or 2)            │
│ is_active  │ Boolean (default: T)        │
│ created_at │ DateTime (auto)             │
│ updated_at │ DateTime (auto)             │
└──────────────────────────────────────────┘
         │
         │ self-referential (parent ↔ subcategories)
         │ Max depth: 2 levels
         ▼
```

- **Self-referential tree** with max depth of 2 levels
- `name` uses PostgreSQL **JSONB** for multi-language support (`uz`, `ru`, `en`)
- Cascade delete on parent removal

### 5.3 PasswordResetCode — `src/models/password_reset.py`

```
┌──────────────────────────────────────┐
│       password_reset_codes           │
├──────────────────────────────────────┤
│ id         │ Integer (PK)            │
│ phone      │ String (index)          │
│ code       │ String (6-digit)        │
│ token      │ String (unique, index)  │
│ expires_at │ DateTime                │
│ verified   │ Boolean (default: F)    │
│ created_at │ DateTime (auto)         │
└──────────────────────────────────────┘
```

---

## 6. Repository Layer

Each repository implements an **abstract interface** defined in `src/repositories/interfaces.py`, ensuring testability and separation of concerns.

### 6.1 Interfaces

| Interface | Methods |
|---|---|
| `IUsersRepository` | `get_by_id`, `get_by_phone`, `get_by_username`, `get_by_email`, `create_user`, `update_user` |
| `ICategoriesRepository` | `get_by_id`, `get_by_path`, `list_categories`, `create_category`, `update_category`, `delete_category` |
| `IPasswordResetRepository` | `create_reset_code`, `get_active_code`, `get_active_token`, `update_reset_code` |

### 6.2 Implementations

All repositories receive an `AsyncSession` via constructor injection.

- **`UsersRepository`** — Uses `joinedload(User.seller_profile)` on all queries to eagerly load seller data
- **`CategoriesRepository`** — Uses `joinedload(Category.subcategories)` and `unique()` to handle async deduplication; `list_categories` returns only level-1 (root) categories
- **`PasswordResetRepository`** — Filters by expiration time (`expires_at > now()`) and verification status

---

## 7. Service Layer

Services contain **all business logic** and are instantiated via FastAPI dependency functions.

### 7.1 UsersService — `src/services/users_scv.py`

| Method | Description |
|---|---|
| `register_user(data)` | Register regular user (type: `user`). Checks phone uniqueness. |
| `register_seller(data)` | Register seller (type: `seller`). Creates empty `SellerProfile`. |
| `login_user(data)` | Login by phone + password. Returns `(User, TokenPair)`. |
| `login_admin(data)` | Login by username + password. Validates admin role. |
| `login_seller(data)` | Login user, then validates seller role. |
| `update_profile(user_id, data)` | Updates user fields with uniqueness checks on phone/username/email. Handles seller profile fields. |
| `update_password(user_id, data)` | Verifies old password, hashes and saves new password. |

**Factory:** `get_users_service(db) → UsersService`

### 7.2 CategoriesService — `src/services/categories_scv.py`

| Method | Description |
|---|---|
| `create_category(data)` | Normalizes path, validates uniqueness, enforces max depth (2 levels). |
| `list_categories(active_only)` | Delegates to repository. |
| `update_category(id, data)` | Updates with path uniqueness, parent validation, self-reference guard. |
| `delete_category(id)` | Cascade deletes category and all subcategories. |

**Factory:** `get_categories_service(db) → CategoriesService`

### 7.3 PasswordResetService — `src/services/password_reset_scv.py`

Three-step password reset flow:

| Step | Method | Description |
|---|---|---|
| 1 | `send_reset_code(phone)` | Verifies user exists, generates 6-digit code, sends via SMS (5 min expiry) |
| 2 | `verify_reset_code(phone, code)` | Validates code, marks as verified, generates UUID token (15 min expiry) |
| 3 | `reset_password(phone, token, new_password)` | Validates token, updates password, invalidates token |

**Factory:** `get_password_reset_service(db) → PasswordResetService`

---

## 8. API Layer

### 8.1 Router Configuration

```python
# src/main.py
app.include_router(api_router, prefix="/api/v1")

# src/api/routes.py
api_router.include_router(auth_handlers.router)      # /api/v1/auth/*
api_router.include_router(category_handlers.router)   # /api/v1/categories/*
```

### 8.2 Auth Endpoints — `/api/v1/auth`

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/auth/register` | — | Register a regular user |
| `POST` | `/auth/seller/register` | — | Register a seller |
| `POST` | `/auth/login` | — | User login (phone + password) |
| `POST` | `/auth/admin/login` | — | Admin login (username + password) |
| `POST` | `/auth/seller/login` | — | Seller login (phone + password) |
| `GET` | `/auth/me` | Bearer | Get authenticated user info |
| `GET` | `/auth/profile` | Bearer | Get user profile |
| `PUT` | `/auth/profile` | Bearer | Update user profile & avatar (multipart) |
| `PUT` | `/auth/password` | Bearer | Change password |
| `POST` | `/auth/forgot-password/send-code` | — | Send SMS reset code |
| `POST` | `/auth/forgot-password/verify-code` | — | Verify SMS code → get token |
| `POST` | `/auth/forgot-password/new-password` | — | Reset password with token |

### 8.3 Category Endpoints — `/api/v1/categories`

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/categories` | — | List all categories (supports `active_only` query + `Accept-Language`) |
| `POST` | `/categories` | Admin | Create a new category |
| `PUT` | `/categories/{id}` | Admin | Update a category |
| `DELETE` | `/categories/{id}` | Admin | Delete a category |

### 8.4 Moderation Endpoints — `/api/v1/moderation`

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/moderation/users` | Admin | List users with filters, search, pagination |
| `PUT` | `/moderation/users/{user_id}` | Admin | Update user details (including block status) |
| `DELETE` | `/moderation/users/{user_id}` | Admin | Hard delete a user |

### 8.5 Other Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/healthz` | Health check (returns `"OK"`) |

**Static Files:** Media files served at `/media` from the `media/` directory.

---

## 9. Security & Authentication

### 9.1 Password Hashing — `src/security/passwords.py`

- Algorithm: **Argon2** (via `argon2-cffi`)
- `hash_password(password) → hash`
- `verify_password(password, hash) → bool`

### 9.2 JWT Tokens — `src/security/tokens.py`

**Token Types:**

| Type | Payload Fields | TTL |
|---|---|---|
| Access Token | `sub` (user ID), `role`, `type: "access"`, `iat`, `exp` | 60 minutes |
| Refresh Token | `sub` (user ID), `role`, `type: "refresh"`, `iat`, `exp` | 30 days |

**Key Functions:**
- `create_token_pair(subject, role) → TokenPair`
- `verify_access_token(token) → AccessTokenClaims`
- `verify_refresh_token(token) → AccessTokenClaims`

### 9.3 Auth Dependencies — `src/security/dependencies.py`

| Dependency | Description |
|---|---|
| `get_current_user` | Extracts Bearer token, verifies JWT, loads user from DB, checks `is_active` |
| `get_current_admin` | Chains `get_current_user`, validates `type == "admin"` |

### 9.4 Localization — `src/security/localization.py`

- `get_accept_language` — Parses `Accept-Language` HTTP header
- Supported languages: `uz` (default), `ru`, `en`
- Used to resolve localized category names from JSONB data

---

## 10. Schemas (DTOs)

### 10.1 Auth Schemas — `src/schemas/auth_schemas.py`

**Requests:**
| Schema | Fields |
|---|---|
| `UserLoginRequest` | `phone`, `password` |
| `AdminLoginRequest` | `username`, `password` |
| `UserRegisterRequest` | `first_name`, `phone`, `password` |
| `ProfileUpdateRequest` | `first_name?`, `last_name?`, `phone?`, `username?`, `email?`, `years_of_experience?`, `portfolio?`, `description?` |
| `PasswordUpdateRequest` | `old_password`, `new_password` |
| `ForgotPasswordSendCodeRequest` | `phone` |
| `ForgotPasswordVerifyCodeRequest` | `phone`, `code` |
| `ForgotPasswordResetRequest` | `phone`, `token`, `new_password` |
| `AdminUserUpdateRequest` | `first_name?`, `last_name?`, `phone?`, `email?`, `is_active?`, `is_blocked?` |

**Responses:**
| Schema | Fields |
|---|---|
| `UserResponse` | Full user object with `avatar`, `last_login`, optional `seller_profile` |
| `TokenResponse` | `access_token`, `refresh_token`, `token_type` |
| `AuthResponse` | `user` (UserResponse) + `tokens` (TokenResponse) |
| `SellerProfileResponse` | `years_of_experience?`, `portfolio?`, `description?` |
| `UserListItemResponse` | `id`, `full_name`, `avatar`, `status`, `created_at`, `bought_courses_count`, `last_login` |
| `UserListResponse` | `items[]` (UserListItemResponse), `total`, `page`, `page_size` |

### 10.2 Category Schemas — `src/schemas/category_schemas.py`

| Schema | Type | Fields |
|---|---|---|
| `LocalizedString` | Input | `ru`, `uz`, `en` |
| `CategoryCreateRequest` | Input | `name` (LocalizedString), `path`, `parent_id?`, `is_active` |
| `CategoryUpdateRequest` | Input | All fields optional |
| `CategoryResponse` | Output | Localized `name` (string), `subcategories[]` |
| `SubcategoryResponse` | Output | Same as CategoryResponse without nested subcategories |

---

## 11. Migrations (Alembic)

### Configuration

- **Config file:** `alembic.ini`
- **Environment:** `alembic/env.py` — Converts `postgresql+asyncpg://` URL to `postgresql://` for sync Alembic operations
- **Model registry:** `src/models/__init__.py` is imported in `env.py` to auto-detect models

### Migration History

| Revision | Description |
|---|---|
| `459b5031b527` | Initial migration (users table) |
| `c389eb12818f` | Initial migration (continued) |
| `04af23d24fab` | Add `username` column, make `phone` nullable |
| `07be93a1e1e2` | Add `categories` table |
| `1a3cece44193` | Change category `name` from String to JSONB |
| `40c1b21e0f5e` | Add `seller_profiles` table |
| `5dd6b9efb16e` | Add `password_reset_codes` table |

### Common Commands

```bash
# Create a new migration
alembic revision --autogenerate -m "description"

# Apply all migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

---

## 12. Docker & Deployment

### 12.1 Dockerfile — `docker/Dockerfile`

- Base image: `python:3.11-slim`
- System deps: `build-essential`, `libpq-dev`
- Entrypoint: `uvicorn src.main:app --host 0.0.0.0 --port 8000`

### 12.2 Development — `docker/docker-compose.yml`

| Service | Image | Ports | Notes |
|---|---|---|---|
| `api` | Built from Dockerfile | `8000` | Hot-reload enabled (`--reload`), source mounted as volumes |
| `postgres-db` | `postgres:15-alpine` | `6666:5432` | Health-checked with `pg_isready` |
| `redis-db` | `redis:7-alpine` | `7777:6379` | Health-checked with `redis-cli ping` |

> **Note:** Celery worker/beat services are commented out and prepared for future use.

### 12.3 Production — `docker/docker-compose.prod.yml`

| Service | Differences from Dev |
|---|---|
| `api` | No `--reload`, resource limits (0.75 CPU / 2GB RAM), `restart: always` |
| `postgres-db` | `restart: always` |
| `redis-db` | `restart: always`, `appendonly yes`, `maxmemory 512mb`, LRU eviction |

### 12.4 Volumes

- `media_data` — Persisted uploaded media files
- `.volumes/pgdata` — PostgreSQL data
- `.volumes/redis_data` — Redis persistence

---

## 13. CI/CD Pipeline

### GitHub Actions — `.github/workflows/deploy.yml`

**Trigger:** Push to `master` branch

**Steps:**
1. SSH into production server (`/var/www/bilim`)
2. `git fetch origin master`
3. `git reset --hard origin/master`
4. `git clean -fd`
5. `docker compose -f docker/docker-compose.prod.yml up -d --build`

**Secrets Required:**
- `SERVER_HOST` — Production server IP/hostname
- `SERVER_SSH_KEY` — SSH private key for `root` access

---

## 14. Environment Variables

```env
# Application
APP_HOST_PORT=8000

# PostgreSQL
POSTGRES_DB=app
POSTGRES_USER=app
POSTGRES_PASSWORD=app
POSTGRES_PORT=5432

# Database connection (async)
DATABASE_URL=postgresql+asyncpg://app:app@postgres-db:5432/app

# Redis
REDIS_URL=redis://redis-db:6379/0

# JWT
JWT_SECRET_KEY=secrett

# Eskiz SMS
ESKIZ_BASE_URL=https://notify.eskiz.uz/api
ESKIZ_EMAIL=your_eskiz_email@example.com
ESKIZ_PASSWORD=your_eskiz_password
ESKIZ_FROM=4546
```

---

## 15. Request Lifecycle

A typical authenticated request flows through these stages:

```
1. Client sends HTTP request with Bearer token
           │
2. FastAPI routing dispatches to handler function
           │
3. Depends(get_current_user) is resolved:
   ├─ Extract token from Authorization header
   ├─ verify_access_token() → AccessTokenClaims
   ├─ Inject AsyncSession via get_db_session()
   ├─ UsersRepository.get_by_id(claims.sub)
   └─ Return User (or raise 401/400)
           │
4. Depends(get_*_service) is resolved:
   ├─ Inject AsyncSession via get_db_session()
   ├─ Instantiate Repository with session
   └─ Instantiate Service with repository
           │
5. Handler calls service method with validated data
           │
6. Service executes business logic:
   ├─ Validation & uniqueness checks
   ├─ Call repository for database operations
   └─ Return domain model or raise HTTPException
           │
7. Handler serializes response via Pydantic schema
           │
8. FastAPI returns JSON response to client
```

---

## 16. Key Dependencies

| Package | Version | Purpose |
|---|---|---|
| `fastapi` | 0.136.0 | Web framework |
| `uvicorn` | 0.45.0 | ASGI server |
| `SQLAlchemy` | 2.0.49 | ORM (async) |
| `asyncpg` | 0.31.0 | PostgreSQL async driver |
| `psycopg2-binary` | 2.9.10 | PostgreSQL sync driver (Alembic) |
| `alembic` | 1.18.4 | Database migrations |
| `pydantic` | 2.13.3 | Data validation & schemas |
| `pydantic-settings` | 2.14.0 | Environment-based settings |
| `PyJWT` | 2.10.1 | JWT token handling |
| `argon2-cffi` | 25.1.0 | Password hashing (Argon2) |
| `httpx` | 0.28.1 | Async HTTP client (Eskiz) |
| `openai` | 2.32.0 | OpenAI SDK (installed, not yet used) |
| `starlette` | 1.0.0 | ASGI toolkit (FastAPI base) |

---

## Scripts

### Create Admin — `scripts/create_admin.py`

CLI tool to create admin users in the database:

```bash
# Interactive mode
python -m scripts.create_admin

# Non-interactive mode
python -m scripts.create_admin \
    --username admin \
    --password secret123 \
    --first-name Admin \
    --last-name User \
    --email admin@example.com
```

- Validates username and email uniqueness
- Hashes password with Argon2
- Sets `type=admin`, `is_superuser=True`
