<![CDATA[<div align="center">

# 🏢 Zeron CRM

**Enterprise-grade Customer Relationship Management System**
*Built for infrastructure & software development companies with a software factory mindset.*

[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19.2-61DAFB?logo=react)](https://react.dev)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?logo=postgresql)](https://postgresql.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.9-3178C6?logo=typescript)](https://typescriptlang.org)
[![TailwindCSS](https://img.shields.io/badge/Tailwind_CSS-3.4-06B6D4?logo=tailwindcss)](https://tailwindcss.com)

---

**English** · [Español](README_ES.md)

</div>

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Modules](#modules)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [Database Migrations](#database-migrations)
- [API Reference](#api-reference)
- [Authentication](#authentication)
- [Internationalization (i18n)](#internationalization-i18n)
- [Design System](#design-system)
- [Development Workflows](#development-workflows)

---

## Overview

Zeron CRM is a full-stack CRM system designed for companies that operate as software factories and infrastructure providers. It provides complete lifecycle management from lead acquisition through invoicing, with a customizable dashboard, financial analytics, and a bilingual interface (English / Spanish).

### Key Features

| Feature | Description |
|---|---|
| 🔐 **JWT Authentication** | Secure email/password login with token-based sessions |
| 📊 **Customizable Dashboard** | Drag-and-drop KPIs, data tables, and charts per user |
| 👥 **Lead Management** | Track prospects from first contact to client conversion |
| 📝 **Quotes & Proposals** | Generate and manage quotes with line items and PDF support |
| 🧾 **Invoicing** | Issued and received invoices with status tracking |
| 💰 **Financial Analytics** | Income vs Expenses charts, cashflow distribution, profit margins |
| 📅 **Calendar & Events** | Activity tracking with deadline management |
| 🏷️ **Products & Services** | Catalog with Product, Service, and Manpower item types |
| 🤝 **Client & Provider Management** | Full contact database with service assignments |
| 🌐 **100% Bilingual (EN/ES)** | Complete i18n with language toggle |
| 📱 **Responsive Design** | Mobile-first layout with collapsible sidebar |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT (Browser)                         │
│  React 19 + TypeScript + TailwindCSS + Recharts + React Router  │
│  Port: 5173 (dev) / Served as static files (prod)               │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP/REST (JSON)
                             │ Authorization: Bearer <JWT>
┌────────────────────────────▼────────────────────────────────────┐
│                      BACKEND (API Server)                       │
│                   FastAPI + Uvicorn (ASGI)                       │
│                        Port: 8000                               │
│                                                                 │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐  │
│  │  Endpoints  │──│  Repositories│──│  SQLAlchemy ORM        │  │
│  │  (Routers)  │  │  (DAL)       │  │  + Alembic Migrations  │  │
│  └─────────────┘  └──────────────┘  └───────────┬────────────┘  │
│                                                  │              │
│  ┌─────────────┐  ┌──────────────┐               │              │
│  │  Schemas    │  │  Services    │               │              │
│  │  (Pydantic) │  │  (Business)  │               │              │
│  └─────────────┘  └──────────────┘               │              │
└──────────────────────────────────────────────────┼──────────────┘
                                                   │
                                        TCP :5432  │
┌──────────────────────────────────────────────────▼──────────────┐
│                      DATABASE (PostgreSQL 15)                   │
│                Docker Container: zeron_crm_db                   │
│                                                                 │
│  Tables: users, clients, contacts, products, providers,         │
│          invoices, invoice_items, invoice_statuses, quotes,     │
│          quote_items, leads, calendar_events, client_services,  │
│          provider_services, dashboard_configs                   │
└─────────────────────────────────────────────────────────────────┘
```

### Backend Layers

| Layer | Location | Responsibility |
|---|---|---|
| **Endpoints** | `api/endpoints/` | HTTP request handling, routing, input validation |
| **Schemas** | `schemas/` | Pydantic models for request/response serialization |
| **Repositories** | `repositories/` | Database access (CRUD operations via SQLAlchemy) |
| **Services** | `services/` | Business logic (invoice calculations, etc.) |
| **Models** | `models/` | SQLAlchemy ORM table definitions |
| **Core** | `core/` | Configuration, security (JWT, bcrypt) |

---

## Tech Stack

### Backend

| Technology | Version | Purpose |
|---|---|---|
| **Python** | 3.12 | Runtime |
| **FastAPI** | 0.109 | REST API framework |
| **Uvicorn** | 0.27 | ASGI server |
| **SQLAlchemy** | 2.0 | ORM & database toolkit |
| **Alembic** | 1.13 | Database migrations |
| **Pydantic** | 2.6 | Data validation & serialization |
| **python-jose** | 3.3 | JWT token creation & decoding |
| **passlib + bcrypt** | 1.7 / 3.2 | Password hashing (bcrypt) |
| **psycopg2-binary** | 2.9 | PostgreSQL adapter |
| **PostgreSQL** | 15 | Relational database (Docker) |

### Frontend

| Technology | Version | Purpose |
|---|---|---|
| **React** | 19.2 | UI framework |
| **TypeScript** | 5.9 | Type safety |
| **Vite** | 7.3 | Build tool & dev server |
| **TailwindCSS** | 3.4 | Utility-first CSS |
| **React Router** | 7.13 | Client-side routing |
| **Axios** | 1.13 | HTTP client with JWT interceptor |
| **Recharts** | 3.7 | Data visualization (charts) |
| **Lucide React** | 0.575 | Icon library |
| **react-i18next** | 16.5 | Internationalization (EN/ES) |
| **date-fns** | 4.1 | Date formatting |

### Infrastructure

| Technology | Purpose |
|---|---|
| **Docker Compose** | PostgreSQL container orchestration |
| **Alembic** | Schema version control & migrations |

---

## Project Structure

```
zeron_crm/
├── docker-compose.yml              # PostgreSQL database container
├── README.md                       # This file
│
├── backend/
│   ├── alembic/                    # Database migration scripts
│   │   ├── env.py
│   │   └── versions/               # Auto-generated migration files
│   ├── alembic.ini
│   ├── venv/                       # Python virtual environment
│   └── app/
│       ├── main.py                 # FastAPI app entry point
│       ├── database.py             # SQLAlchemy engine & session
│       ├── core/
│       │   ├── config.py           # Settings (DB URL, JWT secret, etc.)
│       │   └── security.py         # JWT & password hashing utilities
│       ├── models/                 # SQLAlchemy ORM models
│       │   ├── user.py             # Users & Roles
│       │   ├── client.py           # Accounts/Clients
│       │   ├── contact.py          # Client contacts
│       │   ├── product.py          # Products, Services & Manpower
│       │   ├── provider.py         # External providers
│       │   ├── invoice.py          # Issued & received invoices
│       │   ├── invoice_item.py     # Invoice line items
│       │   ├── quote.py            # Quotes/Proposals
│       │   ├── quote_item.py       # Quote line items
│       │   ├── lead.py             # Sales leads/prospects
│       │   ├── calendar.py         # Calendar events/activities
│       │   ├── client_service.py   # Client ↔ Service assignments
│       │   ├── provider_service.py # Provider ↔ Service assignments
│       │   └── dashboard_config.py # Per-user dashboard widget config
│       ├── schemas/                # Pydantic request/response models
│       ├── repositories/           # Database access layer (CRUD)
│       ├── services/               # Business logic layer
│       └── api/
│           ├── api.py              # Router aggregator
│           └── endpoints/          # REST API endpoint handlers
│               ├── auth.py         # Login, token validation (/me)
│               ├── users.py        # User CRUD
│               ├── clients.py      # Client CRUD
│               ├── contacts.py     # Contact CRUD
│               ├── products.py     # Product/Service CRUD
│               ├── providers.py    # Provider CRUD
│               ├── invoices.py     # Invoice CRUD + statuses
│               ├── quotes.py       # Quote CRUD
│               ├── leads.py        # Lead CRUD
│               ├── calendar.py     # Calendar event CRUD
│               ├── client_services.py    # Service assignments
│               ├── provider_services.py  # Provider service mgmt
│               └── dashboard_config.py   # Widget catalog & config
│
└── frontend/
    ├── index.html                  # App entry point
    ├── package.json                # Dependencies
    ├── tailwind.config.js          # TailwindCSS configuration
    ├── tsconfig.json               # TypeScript configuration
    ├── vite.config.ts              # Vite build configuration
    └── src/
        ├── main.tsx                # React render entry
        ├── App.tsx                 # Router & AuthProvider setup
        ├── App.css                 # Global styles
        ├── i18n.ts                 # i18next configuration
        ├── api/
        │   └── client.ts           # Axios instance (base URL + interceptor)
        ├── context/
        │   └── AuthContext.tsx      # JWT auth state management
        ├── locales/
        │   ├── en.json              # English translations (329 keys)
        │   └── es.json              # Spanish translations (329 keys)
        ├── components/
        │   ├── Layout.tsx           # Main app shell (sidebar + header)
        │   ├── SidebarItem.tsx      # Navigation link component
        │   ├── ProtectedRoute.tsx   # Auth guard for routes
        │   ├── NotificationBell.tsx # Notification dropdown
        │   ├── DashboardCustomizer.tsx    # Widget selection modal
        │   ├── ClientServicesModal.tsx    # Service assignment modal
        │   └── ProviderServicesModal.tsx  # Provider services modal
        └── pages/
            ├── Login.tsx            # JWT login page
            ├── Dashboard.tsx        # Customizable dashboard
            ├── Clients.tsx          # Account management
            ├── ClientProfile.tsx    # Client detail view
            ├── Contacts.tsx         # Contact directory
            ├── Products.tsx         # Product/Service catalog
            ├── Providers.tsx        # Provider management
            ├── Billing.tsx          # Invoice management
            ├── Finances.tsx         # Financial analytics & charts
            ├── Quotes.tsx           # Quote/Proposal management
            ├── Leads.tsx            # Lead pipeline
            ├── Calendar.tsx         # Activity calendar
            ├── Users.tsx            # User & role management
            └── Settings.tsx         # System settings & health
```

---

## Modules

### 1. 🔐 Authentication
- JWT-based login (`POST /api/v1/auth/login`)
- Token validation (`GET /api/v1/auth/me`)
- bcrypt password hashing
- Axios interceptor auto-attaches `Bearer` token
- 8-hour token expiration (configurable)
- Protected routes redirect to `/login` when unauthenticated

### 2. 📊 Dashboard
- **8 KPI Cards**: Clients, Providers, Products, Users, Issued/Received Invoices, Leads, Quotes
- **4 Data Tables**: Recent Invoices, Upcoming Activities, Recent Leads, Recent Quotes
- **2 Charts**: Income vs Expenses (6-month bar chart), Cashflow Distribution
- Per-user widget configuration saved to database
- Toggle widgets on/off via the Customize modal

### 3. 👥 Lead Management (`/leads`)
- Track prospects: company name, contact, email, phone, status, source, notes
- Status workflow: New → Contacted → Qualified → Proposal → Won/Lost
- Quick conversion to client

### 4. 📝 Quotes (`/quotes`)
- Create proposals with line items (linked to Products catalog)
- Auto-generated quote numbers (`QT-XXXXXXXX`)
- Status tracking: Draft → Sent → Accepted → Rejected
- Multi-currency support (ARS, USD, EUR)
- Link to leads or clients

### 5. 🏢 Clients & Contacts (`/clients`, `/contacts`)
- Full account management with CUIT/DNI, address, phone, email
- Client detail profile page with service assignments
- Related contacts per client
- Service contract management via modal

### 6. 🧾 Invoicing (`/billing`)
- Issued (sales) and Received (purchase) invoice types
- Custom invoice statuses with color coding
- Line items with quantity, unit price, tax
- Multi-currency support
- Status management and filtering

### 7. 💰 Financial Analytics (`/finances`)
- Income vs Expenses bar chart (last 6 months)
- Cashflow distribution with profit margin %
- Future projection summary
- Budget/subscription tracking

### 8. 🏷️ Products & Services (`/products`)
- Three item types: **Product**, **Service**, **Manpower**
- Name, description, price per unit
- Used in Quotes and Invoices as line items

### 9. 🤝 Providers (`/providers`)
- External vendor management
- Service assignments (what services each provider offers)
- Contact info, CUIT/DNI, address

### 10. 📅 Calendar (`/calendar`)
- Activity and event tracking
- Start/end dates, descriptions
- Visual calendar interface
- Linked to dashboard upcoming events widget

### 11. ⚙️ Settings (`/settings`)
- System health check (DB, API, Frontend)
- Application configuration

### 12. 👤 Users & Roles (`/users`)
- User CRUD with role assignment
- Roles: admin, user
- Password management

---

## Getting Started

### Prerequisites

- **Docker & Docker Compose** (for PostgreSQL)
- **Python 3.12+** (backend)
- **Node.js 20+** & **npm** (frontend)

### 1. Clone & Start the Database

```bash
cd zeron_crm
docker compose up -d
```

This starts a PostgreSQL 15 container on port `5432` with:
- **User**: `zeron_user`
- **Password**: `zeron_password`
- **Database**: `zeron_crm`

### 2. Set Up the Backend

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install fastapi uvicorn sqlalchemy alembic psycopg2-binary \
  pydantic-settings python-jose passlib bcrypt python-multipart

# Run database migrations
alembic upgrade head

# Start the API server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`.
Interactive docs: `http://localhost:8000/docs` (Swagger UI).

### 3. Set Up the Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start the dev server
npm run dev -- --host 0.0.0.0
```

The frontend will be available at `http://localhost:5173`.

### 4. Create Your First User

Since the app requires authentication, create a user via the API:

```bash
curl -X POST http://localhost:8000/api/v1/users/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@zeron.ovh",
    "password": "your_password",
    "full_name": "Admin User",
    "role": "admin",
    "is_active": true
  }'
```

Then login at `http://localhost:5173/login` with those credentials.

### 5. Production Build

```bash
cd frontend
npm run build
```

The built files will be in `frontend/dist/` — serve them with Nginx or any static file server.

---

## Environment Variables

Create a `.env` file in `backend/` to override defaults:

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql://zeron_user:zeron_password@localhost:5432/zeron_crm` | PostgreSQL connection string |
| `SECRET_KEY` | Auto-generated | JWT signing secret (set a fixed value in production!) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `480` (8 hours) | JWT token lifetime |

Example `.env`:
```env
DATABASE_URL=postgresql://zeron_user:zeron_password@localhost:5432/zeron_crm
SECRET_KEY=your-super-secret-key-here-at-least-32-chars
ACCESS_TOKEN_EXPIRE_MINUTES=480
```

> ⚠️ **Important**: In production, always set a fixed `SECRET_KEY`. The default auto-generates a new key on each restart, which invalidates all existing tokens.

---

## Database Migrations

This project uses **Alembic** for database schema versioning.

```bash
cd backend
source venv/bin/activate

# Apply all pending migrations
alembic upgrade head

# Create a new migration after model changes
alembic revision --autogenerate -m "description of changes"

# Rollback one migration
alembic downgrade -1

# View current migration status
alembic current
```

---

## API Reference

Base URL: `http://localhost:8000/api/v1`

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/auth/login` | Login (email + password → JWT) |
| `GET` | `/auth/me` | Get current user from token |
| `GET/POST/PUT/DELETE` | `/users/` | User management |
| `GET/POST/PUT/DELETE` | `/clients/` | Client/Account management |
| `GET/POST/PUT/DELETE` | `/contacts/` | Contact management |
| `GET/POST/PUT/DELETE` | `/products/` | Product & Service catalog |
| `GET/POST/PUT/DELETE` | `/providers/` | Provider management |
| `GET/POST/PUT/DELETE` | `/invoices/` | Invoice management |
| `GET` | `/invoices/statuses/` | Invoice status definitions |
| `GET/POST/PUT/DELETE` | `/quotes/` | Quote/Proposal management |
| `GET/POST/PUT/DELETE` | `/leads/` | Lead pipeline management |
| `GET/POST/PUT/DELETE` | `/calendar/` | Calendar events |
| `GET/POST/PUT/DELETE` | `/client-services/` | Client ↔ Service assignments |
| `GET/POST/PUT/DELETE` | `/provider-services/` | Provider ↔ Service assignments |
| `GET` | `/dashboard-config/catalog` | Available dashboard widgets |
| `GET/PUT` | `/dashboard-config/{user_id}` | User widget configuration |

Full interactive documentation: `http://localhost:8000/docs`

---

## Authentication

### Flow

```
┌──────┐     POST /auth/login       ┌──────────┐
│Client│ ───────────────────────►   │  Backend │
│      │   {email, password}        │          │
│      │                            │  Verify  │
│      │  ◄──────────────────────── │  bcrypt  │
│      │   {access_token, user}     │          │
│      │                            └──────────┘
│      │
│      │     GET /api/v1/...        ┌──────────┐
│      │ ───────────────────────►   │  Backend │
│      │   Authorization:           │          │
│      │   Bearer <token>           │  Decode  │
│      │                            │  JWT     │
│      │  ◄──────────────────────── │          │
│      │   {data}                   └──────────┘
└──────┘
```

### Token Details
- **Algorithm**: HS256
- **Payload**: `{ sub: user_id, email, role, exp }`
- **Expiration**: 8 hours (configurable)
- **Storage**: `localStorage` key `zeron_token`
- **Attachment**: Axios interceptor adds `Authorization: Bearer <token>` to all requests

---

## Internationalization (i18n)

The app enforces **strict bilingual compliance** (English + Spanish).

### Rules
1. ❌ **Never** hardcode user-facing text in components
2. ✅ **Always** use `t('key')` from `react-i18next`
3. ✅ Every key must exist in **both** `en.json` AND `es.json`

### Structure
```
locales/
├── en.json    # 329 keys
└── es.json    # 329 keys
```

### Key namespaces
| Namespace | Coverage |
|---|---|
| `layout.*` | Sidebar, header, section titles |
| `dashboard.*` | Dashboard widgets, customizer |
| `clients.*` | Client management |
| `invoices.*` | Invoice management |
| `quotes.*` | Quote management |
| `leads.*` | Lead pipeline |
| `products.*` | Product catalog |
| `finances.*` | Financial analytics |
| `calendar.*` | Calendar events |
| `login.*` | Authentication |
| `common.*` | Shared labels |
| `settings.*` | System settings |

### Verify parity
```bash
cd frontend
node -e 'var en=require("./src/locales/en.json"),es=require("./src/locales/es.json");function c(o,p){var r=[];for(var k of Object.keys(o)){var x=p?p+"."+k:k;if(typeof o[k]==="object")r=r.concat(c(o[k],x));else r.push(x)}return r}var ek=c(en,""),sk=c(es,""),me=ek.filter(function(k){return sk.indexOf(k)<0}),mn=sk.filter(function(k){return ek.indexOf(k)<0});if(me.length)console.log("Missing in ES:",me);if(mn.length)console.log("Missing in EN:",mn);if(!me.length&&!mn.length)console.log("OK: "+ek.length+" keys")'
```

---

## Design System

Zeron CRM follows a **Modern Minimalist** design philosophy. See `.agents/workflows/look_and_feel.md` for the full specification.

### Core Principles
- **White space**: Generous padding (`p-6`, `p-8`)
- **Subtle depth**: Soft borders (`border-gray-100`), light shadows (`shadow-sm`)
- **Rounded geometry**: `rounded-xl`, `rounded-2xl`
- **Color palette**: `bg-gray-50` background, `bg-white` cards, `blue-600` primary accent
- **Typography**: Sans-serif (Inter), `text-gray-900` primary, `text-gray-500` secondary

---

## Development Workflows

### Health Check (`/health-check`)
Validates the full stack after major changes:
```bash
# 1. Database connection
docker exec -i zeron_crm_db psql -U zeron_user -d zeron_crm -c "\dt"

# 2. Backend API
curl -f -s http://localhost:8000/health

# 3. Backend ↔ Database (ORM)
curl -f -s "http://localhost:8000/api/v1/users/?skip=0&limit=1"

# 4. Frontend build
cd frontend && npm run build
```

### QA Verification (`/qa-verification`)
Manual checklist for visual verification:
1. ✅ Data visible in UI matches database records
2. ✅ Create/Update forms work and persist on reload
3. ✅ Language toggle translates 100% of new text
4. ✅ No console errors or failed API calls in DevTools
5. ✅ Responsive layout works on mobile viewports

---

## Database Schema

```
┌─────────────┐     ┌──────────────┐     ┌──────────────────┐
│    users     │     │   clients    │────►│    contacts       │
│ (id, email,  │     │ (id, name,   │     │ (id, client_id,  │
│  password,   │     │  cuit, addr) │     │  name, email)    │
│  role)       │     └──────┬───────┘     └──────────────────┘
└──────┬───────┘            │
       │                    │ client_services
       │            ┌───────▼──────┐
       │            │  products    │
       │            │ (id, name,   │◄────── quote_items
       │            │  type, price)│◄────── invoice_items
       │            └──────────────┘
       │
       │  dashboard_configs    ┌──────────────┐
       └──────────────────────►│  invoices     │
                               │ (id, number,  │
┌──────────────┐               │  type, amount,│
│  providers   │               │  status_id)   │
│ (id, name,   │               └───────────────┘
│  cuit, addr) │
└──────┬───────┘    ┌──────────────┐    ┌─────────────────┐
       │            │   quotes     │    │ calendar_events  │
       │            │ (id, number, │    │ (id, title,      │
       │            │  status,     │    │  start, end)     │
provider_services   │  total)      │    └─────────────────┘
                    └──────────────┘
                                        ┌──────────────┐
                                        │    leads      │
                                        │ (id, company, │
                                        │  status,      │
                                        │  source)      │
                                        └──────────────┘
```

---

## License

Private — Zeron Infrastructure & Software Development.

---

<div align="center">
<sub>Built with ❤️ by the Zeron team · 2026</sub>
</div>
]]>
