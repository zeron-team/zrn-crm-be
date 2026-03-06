<![CDATA[<div align="center">

# 🏢 Zeron CRM

**Sistema de Gestión de Relaciones con Clientes de nivel empresarial**
*Diseñado para empresas de infraestructura y desarrollo de software con mentalidad de software factory.*

[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19.2-61DAFB?logo=react)](https://react.dev)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?logo=postgresql)](https://postgresql.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.9-3178C6?logo=typescript)](https://typescriptlang.org)
[![TailwindCSS](https://img.shields.io/badge/Tailwind_CSS-3.4-06B6D4?logo=tailwindcss)](https://tailwindcss.com)

---

[English](README.md) · **Español**

</div>

## 📋 Tabla de Contenidos

- [Descripción General](#descripción-general)
- [Arquitectura](#arquitectura)
- [Stack Tecnológico](#stack-tecnológico)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Módulos](#módulos)
- [Primeros Pasos](#primeros-pasos)
- [Variables de Entorno](#variables-de-entorno)
- [Migraciones de Base de Datos](#migraciones-de-base-de-datos)
- [Referencia de la API](#referencia-de-la-api)
- [Autenticación](#autenticación)
- [Internacionalización (i18n)](#internacionalización-i18n)
- [Sistema de Diseño](#sistema-de-diseño)
- [Workflows de Desarrollo](#workflows-de-desarrollo)

---

## Descripción General

Zeron CRM es un sistema CRM full-stack diseñado para empresas que operan como software factories y proveedores de infraestructura. Proporciona gestión completa del ciclo de vida desde la captación de prospectos hasta la facturación, con un dashboard personalizable, análisis financiero y una interfaz 100% bilingüe (Inglés / Español).

### Funcionalidades Principales

| Funcionalidad | Descripción |
|---|---|
| 🔐 **Autenticación JWT** | Login seguro con email/contraseña y sesiones basadas en tokens |
| 📊 **Dashboard Personalizable** | KPIs, tablas de datos y gráficos configurables por usuario |
| 👥 **Gestión de Prospectos** | Seguimiento de leads desde el primer contacto hasta la conversión |
| 📝 **Presupuestos** | Generación y gestión de cotizaciones con items detallados |
| 🧾 **Facturación** | Facturas emitidas y recibidas con seguimiento de estados |
| 💰 **Análisis Financiero** | Gráficos de Ingresos vs Gastos, distribución de flujo de caja |
| 📅 **Calendario y Eventos** | Seguimiento de actividades con gestión de vencimientos |
| 🏷️ **Productos y Servicios** | Catálogo con tipos: Producto, Servicio y Mano de Obra |
| 🤝 **Gestión de Cuentas y Proveedores** | Base de datos de contactos con asignación de servicios |
| 🌐 **100% Bilingüe (EN/ES)** | i18n completo con selector de idioma |
| 📱 **Diseño Responsivo** | Mobile-first con sidebar colapsable |

---

## Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                      CLIENTE (Navegador)                        │
│  React 19 + TypeScript + TailwindCSS + Recharts + React Router  │
│  Puerto: 5173 (dev) / Archivos estáticos (prod)                 │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP/REST (JSON)
                             │ Authorization: Bearer <JWT>
┌────────────────────────────▼────────────────────────────────────┐
│                      BACKEND (Servidor API)                     │
│                   FastAPI + Uvicorn (ASGI)                       │
│                        Puerto: 8000                             │
│                                                                 │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐  │
│  │  Endpoints  │──│ Repositorios │──│  SQLAlchemy ORM        │  │
│  │  (Routers)  │  │  (DAL)       │  │  + Migraciones Alembic │  │
│  └─────────────┘  └──────────────┘  └───────────┬────────────┘  │
│                                                  │              │
│  ┌─────────────┐  ┌──────────────┐               │              │
│  │  Schemas    │  │  Servicios   │               │              │
│  │  (Pydantic) │  │  (Negocio)   │               │              │
│  └─────────────┘  └──────────────┘               │              │
└──────────────────────────────────────────────────┼──────────────┘
                                                   │
                                        TCP :5432  │
┌──────────────────────────────────────────────────▼──────────────┐
│                    BASE DE DATOS (PostgreSQL 15)                │
│                Contenedor Docker: zeron_crm_db                  │
│                                                                 │
│  Tablas: users, clients, contacts, products, providers,         │
│          invoices, invoice_items, invoice_statuses, quotes,     │
│          quote_items, leads, calendar_events, client_services,  │
│          provider_services, dashboard_configs                   │
└─────────────────────────────────────────────────────────────────┘
```

### Capas del Backend

| Capa | Ubicación | Responsabilidad |
|---|---|---|
| **Endpoints** | `api/endpoints/` | Manejo de requests HTTP, ruteo, validación de entrada |
| **Schemas** | `schemas/` | Modelos Pydantic para serialización request/response |
| **Repositorios** | `repositories/` | Acceso a datos (operaciones CRUD via SQLAlchemy) |
| **Servicios** | `services/` | Lógica de negocio (cálculos de facturas, etc.) |
| **Modelos** | `models/` | Definiciones de tablas ORM con SQLAlchemy |
| **Core** | `core/` | Configuración, seguridad (JWT, bcrypt) |

---

## Stack Tecnológico

### Backend

| Tecnología | Versión | Propósito |
|---|---|---|
| **Python** | 3.12 | Runtime |
| **FastAPI** | 0.109 | Framework de API REST |
| **Uvicorn** | 0.27 | Servidor ASGI |
| **SQLAlchemy** | 2.0 | ORM y toolkit de base de datos |
| **Alembic** | 1.13 | Migraciones de base de datos |
| **Pydantic** | 2.6 | Validación de datos y serialización |
| **python-jose** | 3.3 | Creación y decodificación de tokens JWT |
| **passlib + bcrypt** | 1.7 / 3.2 | Hashing de contraseñas (bcrypt) |
| **psycopg2-binary** | 2.9 | Adaptador PostgreSQL |
| **PostgreSQL** | 15 | Base de datos relacional (Docker) |

### Frontend

| Tecnología | Versión | Propósito |
|---|---|---|
| **React** | 19.2 | Framework de UI |
| **TypeScript** | 5.9 | Seguridad de tipos |
| **Vite** | 7.3 | Herramienta de build y servidor de desarrollo |
| **TailwindCSS** | 3.4 | CSS utilitario |
| **React Router** | 7.13 | Ruteo del lado del cliente |
| **Axios** | 1.13 | Cliente HTTP con interceptor JWT |
| **Recharts** | 3.7 | Visualización de datos (gráficos) |
| **Lucide React** | 0.575 | Librería de íconos |
| **react-i18next** | 16.5 | Internacionalización (EN/ES) |
| **date-fns** | 4.1 | Formateo de fechas |

### Infraestructura

| Tecnología | Propósito |
|---|---|
| **Docker Compose** | Orquestación del contenedor PostgreSQL |
| **Alembic** | Control de versiones del esquema de BD |
| **Let's Encrypt** | Certificados SSL/TLS automáticos |
| **systemd** | Servicio del backend (auto-start, auto-restart) |

---

## Estructura del Proyecto

```
zeron_crm/
├── docker-compose.yml              # Contenedor de base de datos PostgreSQL
├── README.md                       # Documentación en inglés
├── README_ES.md                    # Documentación en español (este archivo)
│
├── backend/
│   ├── alembic/                    # Scripts de migración de BD
│   │   ├── env.py
│   │   └── versions/               # Archivos de migración auto-generados
│   ├── alembic.ini
│   ├── .env                        # Variables de entorno (producción)
│   ├── venv/                       # Entorno virtual Python
│   └── app/
│       ├── main.py                 # Punto de entrada de FastAPI
│       ├── database.py             # Motor y sesión SQLAlchemy
│       ├── core/
│       │   ├── config.py           # Configuración (URL BD, secreto JWT, etc.)
│       │   └── security.py         # Utilidades JWT y hashing de contraseñas
│       ├── models/                 # Modelos ORM SQLAlchemy
│       │   ├── user.py             # Usuarios y Roles
│       │   ├── client.py           # Cuentas/Clientes
│       │   ├── contact.py          # Contactos de clientes
│       │   ├── product.py          # Productos, Servicios y Mano de Obra
│       │   ├── provider.py         # Proveedores externos
│       │   ├── invoice.py          # Facturas emitidas y recibidas
│       │   ├── invoice_item.py     # Items de factura
│       │   ├── quote.py            # Presupuestos/Cotizaciones
│       │   ├── quote_item.py       # Items de presupuesto
│       │   ├── lead.py             # Prospectos de venta
│       │   ├── calendar.py         # Eventos del calendario
│       │   ├── client_service.py   # Rels. Cliente ↔ Servicio
│       │   ├── provider_service.py # Rels. Proveedor ↔ Servicio
│       │   └── dashboard_config.py # Config de widgets por usuario
│       ├── schemas/                # Modelos Pydantic (request/response)
│       ├── repositories/           # Capa de acceso a datos (CRUD)
│       ├── services/               # Capa de lógica de negocio
│       └── api/
│           ├── api.py              # Agregador de routers
│           └── endpoints/          # Handlers de endpoints REST
│
└── frontend/
    ├── index.html                  # Punto de entrada
    ├── package.json                # Dependencias
    ├── tailwind.config.js          # Configuración TailwindCSS
    └── src/
        ├── main.tsx                # Entrada de React
        ├── App.tsx                 # Router y AuthProvider
        ├── i18n.ts                 # Configuración i18next
        ├── api/
        │   └── client.ts           # Instancia Axios (URL base + interceptor)
        ├── context/
        │   └── AuthContext.tsx      # Gestión de estado de autenticación JWT
        ├── locales/
        │   ├── en.json              # Traducciones en inglés (329 keys)
        │   └── es.json              # Traducciones en español (329 keys)
        ├── components/
        │   ├── Layout.tsx           # Shell principal (sidebar + header)
        │   ├── ProtectedRoute.tsx   # Guard de autenticación
        │   ├── DashboardCustomizer.tsx  # Modal de selección de widgets
        │   └── ...                  # Modales de servicios, notificaciones
        └── pages/
            ├── Login.tsx            # Página de inicio de sesión JWT
            ├── Dashboard.tsx        # Dashboard personalizable
            ├── Clients.tsx          # Gestión de cuentas
            ├── Contacts.tsx         # Directorio de contactos
            ├── Products.tsx         # Catálogo de productos/servicios
            ├── Providers.tsx        # Gestión de proveedores
            ├── Billing.tsx          # Gestión de facturas
            ├── Finances.tsx         # Análisis financiero y gráficos
            ├── Quotes.tsx           # Gestión de presupuestos
            ├── Leads.tsx            # Pipeline de prospectos
            ├── Calendar.tsx         # Calendario de actividades
            ├── Users.tsx            # Gestión de usuarios y roles
            └── Settings.tsx         # Configuración del sistema
```

---

## Módulos

### 1. 🔐 Autenticación
- Login basado en JWT (`POST /api/v1/auth/login`)
- Validación de token (`GET /api/v1/auth/me`)
- Hashing de contraseñas con bcrypt
- Interceptor Axios agrega automáticamente el header `Bearer`
- Expiración de tokens: 8 horas (configurable)
- Rutas protegidas redirigen a `/login` si no hay sesión

### 2. 📊 Dashboard
- **8 Tarjetas KPI**: Cuentas, Proveedores, Productos, Usuarios, Facturas Emitidas/Recibidas, Prospectos, Presupuestos
- **4 Tablas de Datos**: Facturas Recientes, Actividades Próximas, Prospectos Recientes, Presupuestos Recientes
- **2 Gráficos**: Ingresos vs Gastos (barra 6 meses), Distribución de Flujo de Caja
- Configuración de widgets por usuario guardada en BD
- Activar/desactivar widgets desde el modal Personalizar

### 3. 👥 Gestión de Prospectos (`/leads`)
- Seguimiento de leads: empresa, contacto, email, teléfono, estado, origen, notas
- Flujo de estados: Nuevo → Contactado → Calificado → Propuesta → Ganado/Perdido
- Conversión rápida a cliente

### 4. 📝 Presupuestos (`/quotes`)
- Crear cotizaciones con items detallados (vinculados al catálogo de Productos)
- Números auto-generados (`QT-XXXXXXXX`)
- Seguimiento de estados: Borrador → Enviado → Aceptado → Rechazado
- Soporte multi-moneda (ARS, USD, EUR)
- Vinculación a prospectos o clientes

### 5. 🏢 Cuentas y Contactos (`/clients`, `/contacts`)
- Gestión completa de cuentas con CUIT/DNI, dirección, teléfono, email
- Página de perfil detallado con asignación de servicios
- Contactos relacionados por cliente
- Gestión de contratos de servicio

### 6. 🧾 Facturación (`/billing`)
- Tipos: Facturas emitidas (ventas) y recibidas (compras)
- Estados personalizados con código de color
- Items con cantidad, precio unitario, impuestos
- Soporte multi-moneda
- Filtrado y gestión de estados

### 7. 💰 Análisis Financiero (`/finances`)
- Gráfico de barras: Ingresos vs Gastos (últimos 6 meses)
- Distribución de flujo de caja con margen de ganancia %
- Resumen de proyección futura
- Seguimiento de presupuestos/suscripciones

### 8. 🏷️ Productos y Servicios (`/products`)
- Tres tipos de items: **Producto**, **Servicio**, **Mano de Obra**
- Nombre, descripción, precio por unidad
- Usados como items en Presupuestos y Facturas

### 9. 🤝 Proveedores (`/providers`)
- Gestión de proveedores externos
- Asignación de servicios (qué servicios ofrece cada proveedor)
- Datos de contacto, CUIT/DNI, dirección

### 10. 📅 Calendario (`/calendar`)
- Seguimiento de actividades y eventos
- Fechas de inicio/fin, descripciones
- Interfaz de calendario visual
- Vinculado al widget de actividades próximas del dashboard

### 11. ⚙️ Configuración (`/settings`)
- Chequeo de salud del sistema (BD, API, Frontend)
- Configuración de la aplicación

### 12. 👤 Usuarios y Roles (`/users`)
- CRUD de usuarios con asignación de roles
- Roles: admin, usuario
- Gestión de contraseñas

---

## Primeros Pasos

### Requisitos Previos

- **Docker & Docker Compose** (para PostgreSQL)
- **Python 3.12+** (backend)
- **Node.js 20+** & **npm** (frontend)

### 1. Clonar e Iniciar la Base de Datos

```bash
cd zeron_crm
docker compose up -d
```

Esto inicia un contenedor PostgreSQL 15 en el puerto `5432` con:
- **Usuario**: `zeron_user`
- **Contraseña**: `zeron_password`
- **Base de datos**: `zeron_crm`

### 2. Configurar el Backend

```bash
cd backend

# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install fastapi uvicorn sqlalchemy alembic psycopg2-binary \
  pydantic-settings python-jose passlib bcrypt python-multipart

# Ejecutar migraciones
alembic upgrade head

# Iniciar el servidor API
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

La API estará disponible en `http://localhost:8000`.
Documentación interactiva: `http://localhost:8000/docs` (Swagger UI).

### 3. Configurar el Frontend

```bash
cd frontend

# Instalar dependencias
npm install

# Iniciar servidor de desarrollo
npm run dev -- --host 0.0.0.0
```

El frontend estará disponible en `http://localhost:5173`.

### 4. Crear el Primer Usuario

Como la app requiere autenticación, crear un usuario vía la API:

```bash
curl -X POST http://localhost:8000/api/v1/users/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@zeron.ovh",
    "password": "tu_contraseña",
    "full_name": "Usuario Admin",
    "role": "admin",
    "is_active": true
  }'
```

Luego ingresar en `http://localhost:5173/login` con esas credenciales.

### 5. Build de Producción

```bash
cd frontend
npm run build
```

Los archivos compilados estarán en `frontend/dist/` — servirlos con Nginx o Apache.

---

## Variables de Entorno

Crear un archivo `.env` en `backend/` para sobreescribir valores por defecto:

| Variable | Valor por Defecto | Descripción |
|---|---|---|
| `DATABASE_URL` | `postgresql://zeron_user:zeron_password@localhost:5432/zeron_crm` | Cadena de conexión PostgreSQL |
| `SECRET_KEY` | Auto-generada | Secreto de firma JWT (¡fijar en producción!) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `480` (8 horas) | Tiempo de vida del token JWT |

> ⚠️ **Importante**: En producción, siempre establecer un `SECRET_KEY` fijo. El valor por defecto auto-genera una nueva clave en cada reinicio, lo que invalida todos los tokens existentes.

---

## Migraciones de Base de Datos

Este proyecto usa **Alembic** para versionado del esquema de BD.

```bash
cd backend
source venv/bin/activate

# Aplicar todas las migraciones pendientes
alembic upgrade head

# Crear una nueva migración tras cambios en modelos
alembic revision --autogenerate -m "descripción de los cambios"

# Revertir una migración
alembic downgrade -1

# Ver estado actual
alembic current
```

---

## Referencia de la API

URL Base: `http://localhost:8000/api/v1`

| Método | Endpoint | Descripción |
|---|---|---|
| `POST` | `/auth/login` | Login (email + contraseña → JWT) |
| `GET` | `/auth/me` | Obtener usuario actual del token |
| `GET/POST/PUT/DELETE` | `/users/` | Gestión de usuarios |
| `GET/POST/PUT/DELETE` | `/clients/` | Gestión de cuentas/clientes |
| `GET/POST/PUT/DELETE` | `/contacts/` | Gestión de contactos |
| `GET/POST/PUT/DELETE` | `/products/` | Catálogo de productos y servicios |
| `GET/POST/PUT/DELETE` | `/providers/` | Gestión de proveedores |
| `GET/POST/PUT/DELETE` | `/invoices/` | Gestión de facturas |
| `GET` | `/invoices/statuses/` | Definiciones de estados de factura |
| `GET/POST/PUT/DELETE` | `/quotes/` | Gestión de presupuestos |
| `GET/POST/PUT/DELETE` | `/leads/` | Gestión de prospectos |
| `GET/POST/PUT/DELETE` | `/calendar/` | Eventos del calendario |
| `GET/POST/PUT/DELETE` | `/client-services/` | Asignaciones Cliente ↔ Servicio |
| `GET/POST/PUT/DELETE` | `/provider-services/` | Gestión de servicios de proveedores |
| `GET` | `/dashboard-config/catalog` | Widgets disponibles del dashboard |
| `GET/PUT` | `/dashboard-config/{user_id}` | Configuración de widgets por usuario |

Documentación interactiva completa: `http://localhost:8000/docs`

---

## Autenticación

### Flujo

```
┌──────┐     POST /auth/login       ┌──────────┐
│Client│ ───────────────────────►   │  Backend │
│      │   {email, password}        │          │
│      │                            │ Verificar│
│      │  ◄──────────────────────── │  bcrypt  │
│      │   {access_token, user}     │          │
│      │                            └──────────┘
│      │
│      │     GET /api/v1/...        ┌──────────┐
│      │ ───────────────────────►   │  Backend │
│      │   Authorization:           │          │
│      │   Bearer <token>           │ Decodif. │
│      │                            │  JWT     │
│      │  ◄──────────────────────── │          │
│      │   {datos}                  └──────────┘
└──────┘
```

### Detalles del Token
- **Algoritmo**: HS256
- **Payload**: `{ sub: user_id, email, role, exp }`
- **Expiración**: 8 horas (configurable)
- **Almacenamiento**: `localStorage` clave `zeron_token`
- **Adjunción**: Interceptor Axios agrega `Authorization: Bearer <token>` a todas las peticiones

---

## Internacionalización (i18n)

La aplicación aplica **cumplimiento bilingüe estricto** (Inglés + Español).

### Reglas
1. ❌ **Nunca** colocar texto fijo directamente en los componentes
2. ✅ **Siempre** usar `t('key')` de `react-i18next`
3. ✅ Cada clave debe existir en **ambos** archivos `en.json` Y `es.json`

### Verificar paridad
```bash
cd frontend
node -e 'var en=require("./src/locales/en.json"),es=require("./src/locales/es.json");function c(o,p){var r=[];for(var k of Object.keys(o)){var x=p?p+"."+k:k;if(typeof o[k]==="object")r=r.concat(c(o[k],x));else r.push(x)}return r}var ek=c(en,""),sk=c(es,""),me=ek.filter(function(k){return sk.indexOf(k)<0}),mn=sk.filter(function(k){return ek.indexOf(k)<0});if(me.length)console.log("Faltan en ES:",me);if(mn.length)console.log("Faltan en EN:",mn);if(!me.length&&!mn.length)console.log("OK: "+ek.length+" claves")'
```

---

## Sistema de Diseño

Zeron CRM sigue una filosofía de diseño **Minimalista Moderno**.

### Principios Clave
- **Espacio blanco**: Padding generoso (`p-6`, `p-8`)
- **Profundidad sutil**: Bordes suaves (`border-gray-100`), sombras leves (`shadow-sm`)
- **Geometría redondeada**: `rounded-xl`, `rounded-2xl`
- **Paleta de colores**: Fondo `bg-gray-50`, tarjetas `bg-white`, acento primario `blue-600`
- **Tipografía**: Sans-serif (Inter), `text-gray-900` primario, `text-gray-500` secundario

---

## Workflows de Desarrollo

### Chequeo de Salud (`/health-check`)
Valida el stack completo después de cambios importantes:
```bash
# 1. Conexión a base de datos
docker exec -i zeron_crm_db psql -U zeron_user -d zeron_crm -c "\dt"

# 2. API del Backend
curl -f -s http://localhost:8000/health

# 3. Backend ↔ Base de Datos (ORM)
curl -f -s "http://localhost:8000/api/v1/users/?skip=0&limit=1"

# 4. Build del Frontend
cd frontend && npm run build
```

### Verificación QA (`/qa-verification`)
Checklist manual de verificación visual:
1. ✅ Datos visibles en la UI coinciden con los registros de la BD
2. ✅ Formularios de creación/edición funcionan y persisten al recargar
3. ✅ El selector de idioma traduce el 100% del texto nuevo
4. ✅ Sin errores en consola ni llamadas API fallidas en DevTools
5. ✅ El layout responsivo funciona en viewports móviles

---

## Esquema de Base de Datos

```
┌─────────────┐     ┌──────────────┐     ┌──────────────────┐
│    users     │     │   clients    │────►│    contacts       │
│ (id, email,  │     │ (id, nombre, │     │ (id, client_id,  │
│  password,   │     │  cuit, dir)  │     │  nombre, email)  │
│  rol)        │     └──────┬───────┘     └──────────────────┘
└──────┬───────┘            │
       │                    │ client_services
       │            ┌───────▼──────┐
       │            │  products    │
       │            │ (id, nombre, │◄────── quote_items
       │            │  tipo, prec) │◄────── invoice_items
       │            └──────────────┘
       │
       │  dashboard_configs    ┌──────────────┐
       └──────────────────────►│  invoices     │
                               │ (id, número,  │
┌──────────────┐               │  tipo, monto, │
│  providers   │               │  estado_id)   │
│ (id, nombre, │               └───────────────┘
│  cuit, dir)  │
└──────┬───────┘    ┌──────────────┐    ┌─────────────────┐
       │            │   quotes     │    │ calendar_events  │
       │            │ (id, número, │    │ (id, título,     │
       │            │  estado,     │    │  inicio, fin)    │
provider_services   │  total)      │    └─────────────────┘
                    └──────────────┘
                                        ┌──────────────┐
                                        │    leads      │
                                        │ (id, empresa, │
                                        │  estado,      │
                                        │  origen)      │
                                        └──────────────┘
```

---

## Despliegue en Producción

Zeron CRM está actualmente desplegado en `https://zeron.ovh`:

| Componente | Configuración |
|---|---|
| **Frontend** | Archivos estáticos en `/var/www/html/zeron-crm/` servidos por Apache |
| **Backend** | Servicio systemd `zeron-crm-api` (uvicorn en 127.0.0.1:8000) |
| **Reverse Proxy** | Apache: `/api/v1/` → backend, todo lo demás → `index.html` (SPA) |
| **SSL** | Let's Encrypt con renovación automática |
| **Base de Datos** | PostgreSQL 15 en Docker |

### Comandos Útiles
```bash
# Ver estado del backend
sudo systemctl status zeron-crm-api

# Reiniciar backend
sudo systemctl restart zeron-crm-api

# Ver logs en tiempo real
sudo journalctl -u zeron-crm-api -f

# Re-desplegar frontend tras cambios
cd frontend && npm run build && sudo cp -r dist/* /var/www/html/zeron-crm/
```

---

## Licencia

Privado — Zeron Infraestructura y Desarrollo de Software.

---

<div align="center">
<sub>Construido con ❤️ por el equipo Zeron · 2026</sub>
</div>
]]>
