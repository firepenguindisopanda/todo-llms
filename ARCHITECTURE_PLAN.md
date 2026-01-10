# FastAPI Todo Application - Architecture & Implementation Plan

## Table of Contents
1. [What is Clean Architecture?](#what-is-clean-architecture)
2. [Project Structure](#project-structure)
3. [Feature Breakdown](#feature-breakdown)
4. [Database Design](#database-design)
5. [Implementation Phases](#implementation-phases)
6. [Technology Stack](#technology-stack)
7. [Next Steps](#next-steps)

---

## What is Clean Architecture?

Clean Architecture (also known as Onion Architecture or Hexagonal Architecture) is a software design philosophy that separates concerns into distinct layers. The key principles are:

### Core Principles

1. **Independence of Frameworks** - The architecture doesn't depend on any external library or framework
2. **Testability** - Business rules can be tested without UI, database, or external services
3. **Independence of UI** - The UI can change without changing the rest of the system
4. **Independence of Database** - You can swap databases without affecting business rules
5. **Independence of External Agencies** - Business rules don't know anything about the outside world

### The Layers (Inside → Outside)

```
┌─────────────────────────────────────────────────────────────────┐
│                        EXTERNAL LAYER                           │
│   (Frameworks, Drivers, UI, Database, External Services)        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                  INTERFACE ADAPTERS                      │   │
│  │    (Controllers, Gateways, Presenters, Repositories)     │   │
│  │  ┌─────────────────────────────────────────────────┐    │   │
│  │  │              APPLICATION LAYER                   │    │   │
│  │  │         (Use Cases / Application Services)       │    │   │
│  │  │  ┌─────────────────────────────────────────┐    │    │   │
│  │  │  │           DOMAIN LAYER                   │    │    │   │
│  │  │  │   (Entities, Value Objects, Domain       │    │    │   │
│  │  │  │    Services, Domain Events)              │    │    │   │
│  │  │  └─────────────────────────────────────────┘    │    │   │
│  │  └─────────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Dependency Rule
**Dependencies always point inward.** The inner layers know nothing about outer layers.

---

## Project Structure

```
fastapi_todo_api/
│
├── app/
│   │
│   ├── main.py                     # FastAPI application entry point
│   ├── config.py                   # Application configuration (env vars)
│   │
│   ├── domain/                     # DOMAIN LAYER (Innermost)
│   │   ├── __init__.py
│   │   ├── entities/               # Core business objects
│   │   │   ├── __init__.py
│   │   │   ├── user.py             # User entity
│   │   │   ├── todo.py             # Todo entity
│   │   │   ├── subscription.py     # Subscription entity
│   │   │   └── invoice.py          # Invoice entity
│   │   │
│   │   ├── value_objects/          # Immutable domain concepts
│   │   │   ├── __init__.py
│   │   │   ├── email.py
│   │   │   ├── password.py
│   │   │   └── money.py
│   │   │
│   │   ├── services/               # Domain services (business logic)
│   │   │   ├── __init__.py
│   │   │   ├── subscription_service.py
│   │   │   └── llm_usage_service.py
│   │   │
│   │   ├── events/                 # Domain events
│   │   │   ├── __init__.py
│   │   │   ├── user_events.py
│   │   │   └── subscription_events.py
│   │   │
│   │   └── exceptions/             # Domain-specific exceptions
│   │       ├── __init__.py
│   │       └── domain_exceptions.py
│   │
│   ├── application/                # APPLICATION LAYER (Use Cases)
│   │   ├── __init__.py
│   │   │
│   │   ├── interfaces/             # Abstract interfaces (ports)
│   │   │   ├── __init__.py
│   │   │   ├── repositories/       # Repository interfaces
│   │   │   │   ├── __init__.py
│   │   │   │   ├── user_repository.py
│   │   │   │   ├── todo_repository.py
│   │   │   │   └── subscription_repository.py
│   │   │   │
│   │   │   ├── services/           # External service interfaces
│   │   │   │   ├── __init__.py
│   │   │   │   ├── email_service.py
│   │   │   │   ├── payment_service.py
│   │   │   │   └── llm_service.py
│   │   │   │
│   │   │   └── unit_of_work.py     # Transaction management interface
│   │   │
│   │   ├── use_cases/              # Application business logic
│   │   │   ├── __init__.py
│   │   │   ├── user/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── register_user.py
│   │   │   │   ├── login_user.py
│   │   │   │   ├── refresh_token.py
│   │   │   │   ├── reset_password.py
│   │   │   │   └── update_profile.py
│   │   │   │
│   │   │   ├── todo/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── create_todo.py
│   │   │   │   ├── update_todo.py
│   │   │   │   ├── delete_todo.py
│   │   │   │   ├── get_todos.py
│   │   │   │   └── search_todos.py
│   │   │   │
│   │   │   ├── subscription/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── create_subscription.py
│   │   │   │   ├── cancel_subscription.py
│   │   │   │   ├── update_subscription.py
│   │   │   │   └── apply_coupon.py
│   │   │   │
│   │   │   └── llm/
│   │   │       ├── __init__.py
│   │   │       ├── generate_completion.py
│   │   │       └── check_usage_limits.py
│   │   │
│   │   ├── dto/                    # Data Transfer Objects
│   │   │   ├── __init__.py
│   │   │   ├── user_dto.py
│   │   │   ├── todo_dto.py
│   │   │   └── subscription_dto.py
│   │   │
│   │   └── common/
│   │       ├── __init__.py
│   │       └── pagination.py
│   │
│   ├── infrastructure/             # INFRASTRUCTURE LAYER (Adapters)
│   │   ├── __init__.py
│   │   │
│   │   ├── database/
│   │   │   ├── __init__.py
│   │   │   ├── connection.py       # Database connection setup
│   │   │   ├── models/             # SQLAlchemy/ORM models
│   │   │   │   ├── __init__.py
│   │   │   │   ├── user_model.py
│   │   │   │   ├── todo_model.py
│   │   │   │   ├── subscription_model.py
│   │   │   │   └── invoice_model.py
│   │   │   │
│   │   │   └── repositories/       # Repository implementations
│   │   │       ├── __init__.py
│   │   │       ├── sqlalchemy_user_repository.py
│   │   │       ├── sqlalchemy_todo_repository.py
│   │   │       └── sqlalchemy_subscription_repository.py
│   │   │
│   │   ├── external_services/
│   │   │   ├── __init__.py
│   │   │   ├── stripe/             # Stripe integration
│   │   │   │   ├── __init__.py
│   │   │   │   ├── stripe_payment_service.py
│   │   │   │   ├── stripe_webhook_handler.py
│   │   │   │   └── stripe_models.py
│   │   │   │
│   │   │   ├── email/              # Email service (SendGrid/SES)
│   │   │   │   ├── __init__.py
│   │   │   │   └── smtp_email_service.py
│   │   │   │
│   │   │   └── llm/                # LLM service (OpenAI/Anthropic)
│   │   │       ├── __init__.py
│   │   │       └── openai_llm_service.py
│   │   │
│   │   ├── security/
│   │   │   ├── __init__.py
│   │   │   ├── jwt_handler.py      # JWT token management
│   │   │   ├── password_hasher.py  # Password hashing
│   │   │   └── csrf_protection.py  # CSRF token handling
│   │   │
│   │   ├── cache/
│   │   │   ├── __init__.py
│   │   │   └── redis_cache.py      # Redis caching
│   │   │
│   │   └── background/
│   │       ├── __init__.py
│   │       └── celery_worker.py    # Background task processing
│   │
│   ├── api/                        # API LAYER (Presentation)
│   │   ├── __init__.py
│   │   │
│   │   ├── v1/                     # API versioning
│   │   │   ├── __init__.py
│   │   │   ├── router.py           # Main v1 router
│   │   │   │
│   │   │   ├── endpoints/          # Route handlers
│   │   │   │   ├── __init__.py
│   │   │   │   ├── auth.py         # Authentication endpoints
│   │   │   │   ├── users.py        # User management endpoints
│   │   │   │   ├── todos.py        # Todo CRUD endpoints
│   │   │   │   ├── subscriptions.py # Subscription endpoints
│   │   │   │   ├── webhooks.py     # Webhook handlers (Stripe)
│   │   │   │   ├── llm.py          # LLM service endpoints
│   │   │   │   └── admin.py        # Admin dashboard endpoints
│   │   │   │
│   │   │   └── schemas/            # Pydantic request/response schemas
│   │   │       ├── __init__.py
│   │   │       ├── auth_schemas.py
│   │   │       ├── user_schemas.py
│   │   │       ├── todo_schemas.py
│   │   │       └── subscription_schemas.py
│   │   │
│   │   ├── dependencies/           # FastAPI dependencies
│   │   │   ├── __init__.py
│   │   │   ├── auth.py             # Authentication dependencies
│   │   │   ├── database.py         # Database session dependency
│   │   │   ├── rate_limiter.py     # Rate limiting dependency
│   │   │   └── pagination.py       # Pagination dependency
│   │   │
│   │   └── middleware/
│   │       ├── __init__.py
│   │       ├── logging_middleware.py
│   │       ├── cors_middleware.py
│   │       ├── rate_limit_middleware.py
│   │       └── error_handler_middleware.py
│   │
│   ├── web/                        # WEB LAYER (Jinja Templates)
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── pages.py            # Page routes
│   │   │   └── admin.py            # Admin dashboard routes
│   │   │
│   │   ├── templates/              # Jinja2 templates
│   │   │   ├── base.html
│   │   │   ├── layouts/
│   │   │   │   ├── main.html
│   │   │   │   └── admin.html
│   │   │   ├── pages/
│   │   │   │   ├── home.html
│   │   │   │   ├── login.html
│   │   │   │   ├── register.html
│   │   │   │   ├── dashboard.html
│   │   │   │   └── pricing.html
│   │   │   ├── components/         # Reusable components
│   │   │   │   ├── navbar.html
│   │   │   │   ├── footer.html
│   │   │   │   └── todo_card.html
│   │   │   ├── macros/             # Template macros
│   │   │   │   ├── forms.html
│   │   │   │   └── pagination.html
│   │   │   ├── errors/
│   │   │   │   ├── 404.html
│   │   │   │   ├── 500.html
│   │   │   │   └── 403.html
│   │   │   └── emails/
│   │   │       ├── welcome.html
│   │   │       ├── password_reset.html
│   │   │       └── invoice.html
│   │   │
│   │   └── static/                 # Static assets
│   │       ├── css/
│   │       ├── js/
│   │       └── images/
│   │
│   └── cli/                        # CLI Commands
│       ├── __init__.py
│       ├── commands.py
│       └── fake_data.py            # Seed/fake data generation
│
├── migrations/                     # Alembic database migrations
│   ├── env.py
│   ├── versions/
│   └── alembic.ini
│
├── tests/                          # Test suite
│   ├── __init__.py
│   ├── conftest.py                 # Pytest fixtures
│   ├── unit/
│   │   ├── domain/
│   │   ├── application/
│   │   └── infrastructure/
│   ├── integration/
│   │   ├── api/
│   │   └── database/
│   └── e2e/
│
├── scripts/                        # Utility scripts
│   ├── setup.py
│   └── deploy.py
│
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── docker-compose.dev.yml
│
├── frontend/                       # Frontend assets (Webpack)
│   ├── src/
│   │   ├── js/
│   │   │   ├── main.js
│   │   │   └── components/
│   │   └── scss/
│   │       ├── main.scss
│   │       └── components/
│   ├── webpack.config.js
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   └── package.json
│
├── .env.example
├── .gitignore
├── pyproject.toml
├── README.md
└── Makefile
```

---

## Feature Breakdown

### Phase 1: Core Infrastructure (Week 1-2)

| Feature | Description | Priority |
|---------|-------------|----------|
| Project Restructure | Implement clean architecture folder structure | 🔴 Critical |
| Configuration Management | Environment variables, settings validation | 🔴 Critical |
| Database Setup | PostgreSQL + SQLAlchemy + Alembic migrations | 🔴 Critical |
| Logging | Structured logging with correlation IDs | 🟡 High |
| Exception Handling | Global exception handler, custom error pages | 🟡 High |
| Middleware | CORS, request logging, error handling | 🟡 High |

### Phase 2: Authentication & Authorization (Week 2-3)

| Feature | Description | Priority |
|---------|-------------|----------|
| User Registration | Email/password registration with validation | 🔴 Critical |
| User Login | JWT access tokens | 🔴 Critical |
| Refresh Tokens | Secure refresh token rotation | 🔴 Critical |
| Password Reset | Email-based password reset workflow | 🟡 High |
| CSRF Protection | CSRF tokens for form submissions | 🟡 High |
| Authorization | Role-based access control (RBAC) | 🟡 High |

### Phase 3: Todo Management (Week 3-4)

| Feature | Description | Priority |
|---------|-------------|----------|
| Todo CRUD | Create, Read, Update, Delete todos | 🔴 Critical |
| User-Todo Association | Todos belong to users | 🔴 Critical |
| Pagination | Cursor/offset pagination for lists | 🟡 High |
| Search & Sort | Search todos, sort by date/priority | 🟡 High |
| Form Validation | Server-side validation with clear errors | 🟡 High |

### Phase 4: Stripe Integration (Week 4-6)

| Feature | Description | Priority |
|---------|-------------|----------|
| Stripe Setup | API keys, webhook configuration | 🔴 Critical |
| Subscription Plans | Define subscription tiers | 🔴 Critical |
| Checkout Flow | Stripe Checkout integration | 🔴 Critical |
| Webhook Handling | Process Stripe events | 🔴 Critical |
| Subscription Management | Upgrade/downgrade/cancel | 🟡 High |
| Recurring Billing | Handle recurring payments | 🟡 High |
| Coupon Codes | Discount code functionality | 🟢 Medium |
| Invoicing | Generate and email invoices | 🟢 Medium |
| Microtransactions | Pay-per-use LLM credits | 🟢 Medium |

### Phase 5: LLM Service (Week 6-7)

| Feature | Description | Priority |
|---------|-------------|----------|
| LLM Integration | OpenAI/Anthropic API integration | 🔴 Critical |
| Usage Tracking | Track API calls per user | 🔴 Critical |
| Rate Limiting | Per-user, per-tier rate limits | 🔴 Critical |
| Background Workers | Async LLM processing with Celery | 🟡 High |

### Phase 6: Frontend & UX (Week 7-8)

| Feature | Description | Priority |
|---------|-------------|----------|
| Jinja Templates | Server-rendered HTML templates | 🟡 High |
| Template Macros | Reusable form/pagination macros | 🟡 High |
| TailwindCSS | Utility-first CSS framework | 🟡 High |
| Webpack Build | ES6 JS, SCSS compilation | 🟡 High |
| AJAX Requests | Async form submissions | 🟡 High |
| JSON Responses | API responses for AJAX | 🟡 High |

### Frontend Styling (Bootstrap CDN)

This project uses **Bootstrap** via CDN for styles and interactive components. The base layout includes the Bootstrap CSS and JS via jsDelivr, so local development does not require a Node build step. If you later migrate to a local build pipeline, consider adding hashed filenames and a CDN-backed storage bucket for static assets.

Notes:
- Templates reference static assets through `STATIC_URL` for local files or can be pointed to a CDN in production.
- If you need more advanced custom CSS, add a small stylesheet under `app/web/static/` and reference it in the layout.

### Jinja Templates — Setup & Usage 

This project uses **Jinja2** for server-rendered pages (login, register, main dashboard, admin UI). The templates live under `app/web/templates` and follow a componentized structure (layouts, pages, components, macros). Use Jinja templates for pages that benefit from server-side rendering (initial page load, emails, admin pages), and keep API endpoints returning JSON for SPA/AJAX interactions.

File structure (recommended):

```
app/web/templates/
├── layouts/
│   └── main.html # base layout with blocks: title, head, content, scripts
├── components/
│   ├── navbar.html
│   └── footer.html
├── macros/
│   └── forms.html        # form & input macros
├── pages/
│   ├── home.html
│   ├── auth/
│   │   ├── login.html
│   │   └── register.html
│   ├── dashboard.html
│   └── admin/
│       ├── index.html
│       └── users.html
└── emails/
    └── welcome.html
```

FastAPI integration

- Mount static files in `app/main.py`:

```py
from starlette.staticfiles import StaticFiles
app.mount("/static", StaticFiles(directory="app/web/static"), name="static")
```

- Configure Jinja templates using FastAPI's helper:

```py
from fastapi.templating import Jinja2Templates
templates = Jinja2Templates(directory="app/web/templates")

@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("pages/home.html", {"request": request, "user": None})
```

Templates & layouts

- Use a base layout (`layouts/main.html`) that defines common HTML head, navigation, and footer. Child pages extend it and fill blocks:

```jinja
{% extends "layouts/main.html" %}
{% block title %}Home{% endblock %}
{% block content %}
  <h1>Welcome</h1>
{% endblock %}
```

Authentication pages

- `pages/auth/login.html` and `pages/auth/register.html` contain secure forms that POST to `/api/v1/auth/login` and `/api/v1/auth/register` respectively. Prefer storing refresh tokens in **HttpOnly Secure** cookies set by the server on successful login:

```py
response.set_cookie("refresh_token", refresh_token, httponly=True, secure=True, samesite="lax")
```

- For CSRF protection when using forms, either add CSRF tokens to forms (e.g., via a server-side token stored in a cookie and validated on POST) or require SameSite cookies and short-lived access tokens; consider integrating an existing CSRF middleware.

Admin vs normal users

- Protect admin pages with a dependency (`get_current_active_admin`) that verifies the user's role and returns 403 if unauthorized.

```py
@router.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request, admin: User = Depends(get_current_active_admin)):
    return templates.TemplateResponse("pages/admin/index.html", {"request": request, "admin": admin})
```

Static assets and asset URLs

- Reference static assets in templates using `request.url_for("static", filename="css/main.css")`:

```jinja
<link rel="stylesheet" href="{{ request.url_for('static', filename='css/main.css') }}">
```

Template testing

- Use `TestClient` or `httpx.AsyncClient` with `ASGITransport` to perform requests against the rendered pages and assert presence of expected HTML and forms.

Forms & validation

- Use Pydantic models for server-side validation of POSTed form data. Return template with error messages embedded when validation fails.
- Use macros (e.g., `macros/forms.html`) to consistently render form fields and validation errors.

Performance & caching

- In production, disable Jinja auto-reload and consider template caching or using a CDN for static assets. Keep templates simple and cache costly fragments if necessary.

Security notes

- Always mark auth cookies as `HttpOnly`, `Secure` and appropriate `SameSite` attribute.
- Sanitize any data rendered into templates and avoid mixing untrusted markup. Prefer to escape unless explicitly marking safe.

---

### Phase 7: Admin & Operations (Week 8-9)

| Feature | Description | Priority |
|---------|-------------|----------|
| Admin Dashboard | User/subscription management | 🟡 High |
| Database Queries | Optimized queries, N+1 prevention | 🟡 High |
| Profiling | Performance profiling tools | 🟢 Medium |
| Fake Data Generation | Seed data for development | 🟢 Medium |
| CLI Scripts | Management commands | 🟢 Medium |

### Phase 8: Production Readiness (Week 9-10)

| Feature | Description | Priority |
|---------|-------------|----------|
| Writing Tests | Unit, integration, E2E tests | 🔴 Critical |
| Internationalization | i18n support | 🟢 Medium |
| Email Service | Transactional emails | 🟡 High |
| Debugging Tools | Debug toolbar, error tracking | 🟢 Medium |
| Dependency Management | Lock files, security updates | 🟡 High |

---

## Database Design

### Entity Relationship Diagram

```
┌─────────────────┐       ┌─────────────────┐
│     users       │       │   refresh_tokens│
├─────────────────┤       ├─────────────────┤
│ id (PK)         │───┐   │ id (PK)         │
│ email           │   │   │ user_id (FK)    │──┐
│ password_hash   │   │   │ token_hash      │  │
│ first_name      │   │   │ expires_at      │  │
│ last_name       │   │   │ created_at      │  │
│ is_active       │   │   │ revoked_at      │  │
│ is_verified     │   │   └─────────────────┘  │
│ role            │   │                        │
│ created_at      │   └────────────────────────┘
│ updated_at      │
└─────────────────┘
        │
        │ 1:N
        ▼
┌─────────────────┐
│     todos       │
├─────────────────┤
│ id (PK)         │
│ user_id (FK)    │
│ title           │
│ description     │
│ completed       │
│ priority        │
│ due_date        │
│ created_at      │
│ updated_at      │
└─────────────────┘

┌─────────────────┐       ┌─────────────────┐
│     users       │       │  subscriptions  │
├─────────────────┤       ├─────────────────┤
│ id (PK)         │──┐    │ id (PK)         │
└─────────────────┘  │    │ user_id (FK)    │──┘
                     │    │ stripe_sub_id   │
                     │    │ stripe_cust_id  │
                     │    │ plan_id (FK)    │──┐
                     │    │ status          │  │
                     │    │ current_period  │  │
                     │    │ cancel_at       │  │
                     │    │ created_at      │  │
                     │    └─────────────────┘  │
                     │                         │
                     │    ┌─────────────────┐  │
                     │    │subscription_plans│ │
                     │    ├─────────────────┤  │
                     │    │ id (PK)         │◄─┘
                     │    │ name            │
                     │    │ stripe_price_id │
                     │    │ price           │
                     │    │ llm_requests/mo │
                     │    │ features (JSON) │
                     │    └─────────────────┘
                     │
                     │    ┌─────────────────┐
                     │    │   llm_usage     │
                     │    ├─────────────────┤
                     └───►│ id (PK)         │
                          │ user_id (FK)    │
                          │ tokens_used     │
                          │ request_type    │
                          │ cost            │
                          │ created_at      │
                          └─────────────────┘

┌─────────────────┐       ┌─────────────────┐
│    invoices     │       │   coupons       │
├─────────────────┤       ├─────────────────┤
│ id (PK)         │       │ id (PK)         │
│ user_id (FK)    │       │ code            │
│ stripe_inv_id   │       │ discount_type   │
│ amount          │       │ discount_value  │
│ status          │       │ max_uses        │
│ paid_at         │       │ current_uses    │
│ pdf_url         │       │ expires_at      │
│ created_at      │       │ created_at      │
└─────────────────┘       └─────────────────┘

┌─────────────────┐
│   rate_limits   │
├─────────────────┤
│ id (PK)         │
│ user_id (FK)    │
│ endpoint        │
│ requests_count  │
│ window_start    │
└─────────────────┘
```

### Subscription Plans Example

| Plan | Price | LLM Requests/Month | Features |
|------|-------|-------------------|----------|
| Free | $0 | 10 | Basic todo management |
| Pro | $9.99/mo | 500 | Priority support, advanced features |
| Enterprise | $29.99/mo | Unlimited | API access, custom integrations |

---

## Technology Stack

### Backend
| Category | Technology |
|----------|------------|
| Framework | FastAPI |
| Database | PostgreSQL |
| ORM | SQLAlchemy 2.0 |
| Migrations | Alembic |
| Authentication | python-jose (JWT) |
| Password Hashing | passlib[bcrypt] |
| Validation | Pydantic v2 |
| Background Tasks | Celery + Redis |
| Caching | Redis |
| Rate Limiting | slowapi / custom Redis-based |
| Email | SMTP / SendGrid |
| Payments | Stripe Python SDK |
| LLM | OpenAI SDK / Anthropic SDK |
| Testing | pytest, pytest-asyncio, httpx |

### Frontend
| Category | Technology |
|----------|------------|
| Templates | Jinja2 |
| CSS | TailwindCSS |
| Build Tool | Webpack 5 |
| JavaScript | ES6+ |
| Styling | SCSS |

### DevOps
| Category | Technology |
|----------|------------|
| Containerization | Docker |
| CI/CD | GitHub Actions |
| Monitoring | Sentry |
| Logging | structlog |

---

## Implementation Phases

### 🚀 Phase 1: Foundation (Start Here)

#### Step 1: Project Setup
```bash
# Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install core dependencies
pip install fastapi[standard] sqlalchemy[asyncio] alembic psycopg2-binary
pip install pydantic-settings python-dotenv
pip install python-jose[cryptography] passlib[bcrypt]
```

#### Step 2: Create Directory Structure
Create the folder structure outlined above.

#### Step 3: Configuration Setup
Create `app/config.py` with environment variable management.

#### Step 4: Database Models
Set up SQLAlchemy models in `infrastructure/database/models/`.

#### Step 5: Run Migrations
```bash
alembic init migrations
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

### 📋 Detailed Next Steps (First Week)

1. **Day 1-2: Project Restructure**
   - [ ] Create all directories following clean architecture
   - [ ] Move existing `Todo` model to `domain/entities/todo.py`
   - [ ] Create `app/config.py` for settings management
   - [ ] Set up `.env` file with configuration

2. **Day 3-4: Database Layer**
   - [ ] Install and configure SQLAlchemy
   - [ ] Create database models in `infrastructure/database/models/`
   - [ ] Set up Alembic for migrations
   - [ ] Create User and Todo tables
   - [ ] Implement repository pattern

3. **Day 5-7: Authentication Foundation**
   - [ ] Create User entity and repository
   - [ ] Implement JWT token service
   - [ ] Create registration endpoint
   - [ ] Create login endpoint
   - [ ] Implement refresh token logic

---

## Dependencies to Add (pyproject.toml)

```toml
[project]
name = "fastapi-todo-api"
version = "0.1.0"
description = "A full-featured FastAPI todo application with clean architecture"
readme = "README.md"
requires-python = ">=3.10"
dependencies = [
    # Core
    "fastapi[standard]>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    
    # Database
    "sqlalchemy[asyncio]>=2.0.0",
    "asyncpg>=0.29.0",
    "alembic>=1.13.0",
    
    # Authentication
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4",
    
    # Payments
    "stripe>=8.0.0",
    
    # Background Tasks
    "celery[redis]>=5.3.0",
    "redis>=5.0.0",
    
    # Email
    "aiosmtplib>=3.0.0",
    "email-validator>=2.0.0",
    
    # Rate Limiting
    "slowapi>=0.1.9",
    
    # LLM
    "openai>=1.0.0",
    "anthropic>=0.18.0",
    
    # Templates
    "jinja2>=3.1.0",
    "python-multipart>=0.0.9",
    
    # Utils
    "python-dotenv>=1.0.0",
    "structlog>=24.0.0",
    "httpx>=0.27.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.1.0",
    "httpx>=0.27.0",
    "faker>=24.0.0",
    "black>=24.0.0",
    "ruff>=0.3.0",
    "mypy>=1.9.0",
]
```

---

## Quick Reference: Clean Architecture Mappings

| Your Feature | Clean Architecture Layer | Location |
|--------------|-------------------------|----------|
| User, Todo entities | Domain | `domain/entities/` |
| Business rules | Domain Services | `domain/services/` |
| CRUD operations | Use Cases | `application/use_cases/` |
| Repository interfaces | Application | `application/interfaces/` |
| SQLAlchemy models | Infrastructure | `infrastructure/database/models/` |
| Repository implementations | Infrastructure | `infrastructure/database/repositories/` |
| Stripe integration | Infrastructure | `infrastructure/external_services/stripe/` |
| JWT handling | Infrastructure | `infrastructure/security/` |
| API endpoints | API/Presentation | `api/v1/endpoints/` |
| Pydantic schemas | API/Presentation | `api/v1/schemas/` |
| Rate limiting | Middleware | `api/middleware/` |
| Jinja templates | Web/Presentation | `web/templates/` |

---

## Recommended Learning Resources

1. **Clean Architecture**: "Clean Architecture" by Robert C. Martin
2. **FastAPI**: [FastAPI Documentation](https://fastapi.tiangolo.com)
3. **SQLAlchemy 2.0**: [SQLAlchemy Documentation](https://docs.sqlalchemy.org)
4. **Stripe**: [Stripe Developer Docs](https://stripe.com/docs)
5. **JWT**: [JWT.io Introduction](https://jwt.io/introduction)

---

## Summary

This plan transforms your simple todo API into a production-ready SaaS application with:

-  Clean Architecture for maintainability and testability
-  User authentication with JWT + refresh tokens
-  Stripe integration for subscriptions and payments
-  LLM service with usage tracking and rate limiting
-  Modern frontend with TailwindCSS and Webpack
-  Comprehensive admin dashboard
-  Production-ready infrastructure (logging, monitoring, tests)

**Estimated Timeline**: 8-10 weeks for full implementation

**Start with**: Phase 1 (Foundation) → Create the directory structure and set up configuration management.

