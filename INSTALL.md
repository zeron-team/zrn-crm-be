# 🚀 ZeRoN 360° — Guía de Instalación Completa

> **Versión:** 3.0.0  
> **Última actualización:** 2026-03-06  
> **Autor:** Zeron Team  

---

## 📑 Índice

1. [Descripción General](#1-descripción-general)
2. [Arquitectura del Sistema](#2-arquitectura-del-sistema)
3. [Requisitos Previos (Servidor Ubuntu Nuevo)](#3-requisitos-previos-servidor-ubuntu-nuevo)
4. [Instalación del Backend](#4-instalación-del-backend)
5. [Instalación del Frontend](#5-instalación-del-frontend)
6. [Configuración de Base de Datos](#6-configuración-de-base-de-datos)
7. [Configuración del Servidor Web (Apache)](#7-configuración-del-servidor-web-apache)
8. [Servicio Systemd (Backend como servicio)](#8-servicio-systemd-backend-como-servicio)
9. [SSL / HTTPS con Let's Encrypt](#9-ssl--https-con-lets-encrypt)
10. [Despliegue de Producción — Paso a Paso Completo](#10-despliegue-de-producción--paso-a-paso-completo)
11. [Estructura del Proyecto](#11-estructura-del-proyecto)
12. [Módulos y Funcionalidades](#12-módulos-y-funcionalidades)
13. [API Endpoints](#13-api-endpoints)
14. [Internacionalización (i18n)](#14-internacionalización-i18n)
15. [Variables de Entorno](#15-variables-de-entorno)
16. [Comandos Útiles](#16-comandos-útiles)
17. [Solución de Problemas](#17-solución-de-problemas)

---

## 1. Descripción General

**ZeRoN 360°** es una plataforma CRM/ERP integral diseñada para empresas de infraestructura y desarrollo de software con enfoque de *software factory*. Incluye gestión comercial, facturación fiscal (ARCA/AFIP), recursos humanos, liquidación de haberes, gestión de proyectos, soporte por tickets, wiki interna y más.

### Stack Tecnológico

| Componente | Tecnología | Versión |
|------------|-----------|---------|
| **Backend API** | Python + FastAPI + Uvicorn | Python 3.10+ / FastAPI 0.109 |
| **Frontend** | React + TypeScript + Vite | React 19 / Vite 7 |
| **Base de Datos** | PostgreSQL | 15+ |
| **ORM** | SQLAlchemy | 2.0 |
| **Migraciones** | Alembic | 1.13 |
| **Autenticación** | JWT (python-jose + bcrypt) | — |
| **Facturación Fiscal** | PyAfipWs (ARCA/AFIP) | 3.10.0 |
| **PDF** | fpdf2 + Pillow | 2.8.7 |
| **Email SOAP** | zeep + lxml | 4.3.2 |
| **Estilos** | TailwindCSS | 3.4 |
| **Servidor Web** | Apache 2.4 (reverse proxy) | 2.4 |
| **SSL** | Let's Encrypt (Certbot) | — |

---

## 2. Arquitectura del Sistema

```
┌──────────────────────────────────────────────────────────────┐
│                        INTERNET                              │
│                    https://zeron.ovh                          │
└────────────────────────┬─────────────────────────────────────┘
                         │
                    ┌────▼────┐
                    │ Apache  │  Puerto 443 (SSL)
                    │ 2.4     │  Puerto 80 → Redirect HTTPS
                    └────┬────┘
                         │
          ┌──────────────┼──────────────┐
          │              │              │
    /api/v1/*      /uploads/*     /* (Archivos estáticos)
    /health        /docs          SPA Fallback → index.html
    /openapi.json
          │              │              │
    ┌─────▼──────┐       │     ┌────────▼────────┐
    │ Uvicorn    │       │     │ Frontend Build   │
    │ FastAPI    │◄──────┘     │ /var/www/html/   │
    │ :8000      │             │ zeron-crm/       │
    └─────┬──────┘             └─────────────────┘
          │
    ┌─────▼──────┐
    │ PostgreSQL │
    │ :5432      │
    │ zeron_crm  │
    └────────────┘
```

### Flujo de peticiones:
1. El usuario accede a `https://zeron.ovh`
2. Apache sirve los archivos estáticos del frontend (SPA React)
3. Las peticiones a `/api/v1/*` son redirigidas (reverse proxy) a Uvicorn en `127.0.0.1:8000`
4. FastAPI procesa la petición, consulta PostgreSQL y responde JSON
5. El frontend React renderiza la respuesta en el navegador

---

## 3. Requisitos Previos (Servidor Ubuntu Nuevo)

Esta guía asume un servidor **100% nuevo** con **Ubuntu 22.04 LTS** (o superior) recién instalado.

### 3.1 Actualizar el sistema

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y software-properties-common curl wget gnupg2 ca-certificates lsb-release apt-transport-https
```

### 3.2 Instalar Python 3.10+

```bash
sudo apt install -y python3 python3-pip python3-venv python3-dev build-essential
```

### 3.3 Instalar Node.js 20+ y npm

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

### 3.4 Instalar PostgreSQL 15

```bash
sudo apt install -y postgresql postgresql-contrib
sudo systemctl enable postgresql
sudo systemctl start postgresql
```

### 3.5 Instalar Apache 2.4

```bash
sudo apt install -y apache2
sudo systemctl enable apache2
sudo systemctl start apache2
```

### 3.6 Instalar Git

```bash
sudo apt install -y git
```

### 3.7 Instalar Certbot (para SSL)

```bash
sudo apt install -y certbot python3-certbot-apache
```

### 3.8 Instalar dependencias del sistema para PyAfipWs (ARCA)

```bash
sudo apt install -y libxml2-dev libxslt1-dev libffi-dev libssl-dev
```

### 3.9 Verificar versiones instaladas

```bash
python3 --version    # Debe ser 3.10+
node --version       # Debe ser 20+
npm --version        # Debe ser 10+
psql --version       # Debe ser 15+
apache2 -v           # Debe ser 2.4+
git --version        # Cualquier versión reciente
```

---

## 4. Instalación del Backend

### 4.1 Clonar el repositorio

```bash
cd /home/ubuntu
mkdir -p zrn-crm
git clone https://github.com/zeron-team/zrn-crm-be.git zrn-crm/backend
```

### 4.2 Crear el entorno virtual de Python

```bash
cd /home/ubuntu/zrn-crm/backend
python3 -m venv venv
```

### 4.3 Activar el entorno virtual

```bash
source venv/bin/activate
```

### 4.4 Instalar dependencias

```bash
pip install -r requirements.txt
```

#### Dependencias principales:

| Paquete | Función |
|---------|---------|
| `fastapi` | Framework web API REST |
| `uvicorn` | Servidor ASGI para FastAPI |
| `sqlalchemy` | ORM para PostgreSQL |
| `alembic` | Migraciones de base de datos |
| `psycopg2-binary` | Driver PostgreSQL para Python |
| `python-jose` | Generación y validación de tokens JWT |
| `passlib` + `bcrypt` | Hash seguro de contraseñas |
| `pydantic` + `pydantic-settings` | Validación de datos y configuración |
| `python-dotenv` | Carga de archivos `.env` |
| `python-multipart` | Subida de archivos (multipart/form-data) |
| `email-validator` | Validación de emails |
| `PyAfipWs` | Integración con ARCA/AFIP (facturación electrónica) |
| `fpdf2` + `pillow` | Generación de PDFs (facturas, remitos) |
| `zeep` + `lxml` | Cliente SOAP para servicios web fiscales |
| `httpx` | Cliente HTTP async para consultas externas |
| `cryptography` | Manejo de certificados digitales ARCA |

### 4.5 Configurar variables de entorno

Crear el archivo `/home/ubuntu/zrn-crm/backend/.env`:

```bash
cat > /home/ubuntu/zrn-crm/backend/.env << 'EOF'
DATABASE_URL=postgresql://zeron_user:TU_PASSWORD_SEGURA@localhost:5432/zeron_crm
SECRET_KEY=GENERA_UN_SECRET_KEY_ALEATORIO_AQUI
ACCESS_TOKEN_EXPIRE_MINUTES=480
EOF
```

> ⚠️ **IMPORTANTE:** Genera un `SECRET_KEY` seguro con:
> ```bash
> python3 -c "import secrets; print(secrets.token_urlsafe(48))"
> ```

### 4.6 Configurar certificados ARCA (opcional)

Si se va a usar facturación electrónica con ARCA/AFIP:

```bash
mkdir -p /home/ubuntu/zrn-crm/backend/arca/certs
# Copiar los certificados .crt y .key al directorio arca/certs/
# Configurar desde el panel de Administración en el frontend
```

### 4.7 Verificar que el backend carga correctamente

```bash
cd /home/ubuntu/zrn-crm/backend
source venv/bin/activate
python3 -c "import app.main; print('✅ Backend OK')"
```

---

## 5. Instalación del Frontend

### 5.1 Clonar el repositorio

```bash
cd /home/ubuntu/zrn-crm
git clone https://github.com/zeron-team/zrn-crm-fe.git frontend
```

### 5.2 Instalar dependencias

```bash
cd /home/ubuntu/zrn-crm/frontend
npm install
```

#### Dependencias principales:

| Paquete | Función |
|---------|---------|
| `react` + `react-dom` | Librería UI principal |
| `react-router-dom` | Enrutamiento SPA |
| `axios` | Cliente HTTP para consumir la API |
| `recharts` | Gráficos y visualizaciones |
| `lucide-react` | Iconografía moderna |
| `i18next` + `react-i18next` | Internacionalización (ES/EN) |
| `@dnd-kit/core` + `@dnd-kit/sortable` | Drag & Drop para widgets del dashboard |
| `date-fns` | Manipulación de fechas |
| `tailwindcss` | Framework CSS utility-first |
| `typescript` | Tipado estático |
| `vite` | Bundler y dev server |

### 5.3 Build de producción

```bash
cd /home/ubuntu/zrn-crm/frontend
npm run build
```

> ⚠️ **En servidores con poca RAM** (< 2GB), usar swap o limitar memoria de Node:
> ```bash
> NODE_OPTIONS="--max-old-space-size=512" npm run build
> ```

### 5.4 Desplegar el build en el servidor web

```bash
sudo mkdir -p /var/www/html/zeron-crm
sudo rm -rf /var/www/html/zeron-crm/*
sudo cp -r /home/ubuntu/zrn-crm/frontend/dist/* /var/www/html/zeron-crm/
sudo chown -R www-data:www-data /var/www/html/zeron-crm/
```

### 5.5 Configuración del cliente API (`src/api/client.ts`)

El frontend detecta automáticamente el entorno:

```typescript
// En producción: usa el reverse proxy de Apache en /api/v1
// En desarrollo: apunta directamente a localhost:8000
const baseURL = import.meta.env.DEV
    ? `http://${window.location.hostname || "localhost"}:8000/api/v1`
    : "/api/v1";
```

**No requiere configuración manual** para producción.

---

## 6. Configuración de Base de Datos

### 6.1 Crear usuario y base de datos en PostgreSQL

```bash
sudo -u postgres psql
```

Dentro de la consola `psql`:

```sql
-- Crear usuario
CREATE USER zeron_user WITH PASSWORD 'TU_PASSWORD_SEGURA';

-- Crear base de datos
CREATE DATABASE zeron_crm OWNER zeron_user;

-- Otorgar privilegios
GRANT ALL PRIVILEGES ON DATABASE zeron_crm TO zeron_user;

-- Salir
\q
```

### 6.2 Ejecutar migraciones con Alembic

```bash
cd /home/ubuntu/zrn-crm/backend
source venv/bin/activate
alembic upgrade head
```

Esto creará todas las tablas necesarias en la base de datos.

### 6.3 Crear el primer usuario administrador

```bash
cd /home/ubuntu/zrn-crm/backend
source venv/bin/activate
python3 -c "
from app.database import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash

db = SessionLocal()
admin = User(
    email='admin@tudominio.com',
    full_name='Administrador',
    hashed_password=get_password_hash('TuPasswordSegura123'),
    is_active=True,
    role='admin'
)
db.add(admin)
db.commit()
print('✅ Usuario admin creado exitosamente')
db.close()
"
```

> ⚠️ Reemplaza `admin@tudominio.com` y `TuPasswordSegura123` con tus credenciales.

### 6.4 Tablas de la base de datos

El sistema utiliza las siguientes tablas:

| Tabla | Descripción |
|-------|-------------|
| `users` | Usuarios del sistema (autenticación y roles) |
| `role_configs` | Configuración de permisos por rol |
| `clients` | Empresas cliente (datos fiscales CUIT/DNI) |
| `contacts` | Contactos asociados a clientes |
| `providers` | Proveedores de servicios |
| `products` | Productos / Servicios / Mano de obra |
| `families` | Familias de categorías (nivel 1) |
| `categories` | Categorías de productos (nivel 2) |
| `subcategories` | Subcategorías (nivel 3) |
| `invoices` | Facturas emitidas y recibidas |
| `invoice_statuses` | Estados de facturas (personalizables) |
| `invoice_items` | Ítems de facturas |
| `invoice_iva_items` | Desglose de IVA por factura (ARCA) |
| `invoice_audit_logs` | Trazabilidad de cambios en facturas |
| `arca_configs` | Configuración ARCA/AFIP por punto de venta |
| `quotes` | Presupuestos / Cotizaciones |
| `quote_items` | Ítems de presupuestos |
| `quote_installments` | Cuotas de presupuestos (seguimiento de cobro) |
| `leads` | Leads / Prospectos |
| `calendar_events` | Eventos del calendario |
| `activity_notes` | Notas de actividad (por evento) |
| `notes` | Notas generales del sistema |
| `client_services` | Servicios contratados por clientes |
| `provider_services` | Servicios contratados a proveedores |
| `service_payments` | Pagos de servicios |
| `delivery_notes` | Remitos |
| `payment_orders` | Órdenes de pago |
| `purchase_orders` | Órdenes de compra |
| `warehouses` | Depósitos / Almacenes |
| `inventory` | Stock por producto y depósito |
| `exchange_rates` | Tipos de cambio (USD, EUR) |
| `tickets` | Tickets de soporte |
| `projects` | Proyectos (gestión de proyectos) |
| `employees` | Empleados (RRHH) |
| `time_entries` | Registro de horas trabajadas |
| `payrolls` | Liquidaciones de haberes |
| `email_accounts` | Cuentas de email configuradas |
| `email_messages` | Mensajes de email |
| `email_signatures` | Firmas de email |
| `wiki_pages` | Páginas de wiki interna |
| `dashboard_configs` | Configuración de widgets del dashboard (por usuario) |

---

## 7. Configuración del Servidor Web (Apache)

### 7.1 Habilitar módulos necesarios

```bash
sudo a2enmod proxy
sudo a2enmod proxy_http
sudo a2enmod rewrite
sudo a2enmod ssl
sudo a2enmod headers
```

### 7.2 Crear directorio del frontend

```bash
sudo mkdir -p /var/www/html/zeron-crm
sudo chown -R www-data:www-data /var/www/html/zeron-crm
```

### 7.3 Configuración VirtualHost HTTP (puerto 80)

Crear `/etc/apache2/sites-available/zeron-crm.conf`:

```apache
<VirtualHost *:80>
    ServerAdmin admin@tudominio.com
    ServerName tudominio.com
    DocumentRoot /var/www/html/zeron-crm

    # Reverse proxy para la API
    ProxyPreserveHost On
    ProxyPass /api/v1/ http://127.0.0.1:8000/api/v1/
    ProxyPassReverse /api/v1/ http://127.0.0.1:8000/api/v1/

    # Proxy para health check
    ProxyPass /health http://127.0.0.1:8000/health
    ProxyPassReverse /health http://127.0.0.1:8000/health

    # Proxy para archivos subidos
    ProxyPass /uploads/ http://127.0.0.1:8000/uploads/
    ProxyPassReverse /uploads/ http://127.0.0.1:8000/uploads/

    # Proxy para documentación de la API (Swagger)
    ProxyPass /docs http://127.0.0.1:8000/docs
    ProxyPassReverse /docs http://127.0.0.1:8000/docs
    ProxyPass /openapi.json http://127.0.0.1:8000/openapi.json
    ProxyPassReverse /openapi.json http://127.0.0.1:8000/openapi.json

    # Archivos estáticos del frontend
    <Directory /var/www/html/zeron-crm>
        Options -Indexes +FollowSymLinks
        AllowOverride None
        Require all granted

        # SPA fallback: servir index.html para todas las rutas no-archivo
        RewriteEngine On
        RewriteBase /
        RewriteRule ^index\.html$ - [L]
        RewriteCond %{REQUEST_FILENAME} !-f
        RewriteCond %{REQUEST_FILENAME} !-d
        RewriteRule . /index.html [L]
    </Directory>

    ErrorLog ${APACHE_LOG_DIR}/zeron_crm_error.log
    CustomLog ${APACHE_LOG_DIR}/zeron_crm_access.log combined

    # Redirección a HTTPS (descomentar después de configurar SSL)
    # RewriteCond %{SERVER_NAME} =tudominio.com
    # RewriteRule ^ https://%{SERVER_NAME}%{REQUEST_URI} [END,NE,R=permanent]
</VirtualHost>
```

### 7.4 Configuración VirtualHost HTTPS (puerto 443)

Crear `/etc/apache2/sites-available/zeron-crm-le-ssl.conf`:

```apache
<IfModule mod_ssl.c>
<VirtualHost *:443>
    ServerAdmin admin@tudominio.com
    ServerName tudominio.com
    DocumentRoot /var/www/html/zeron-crm

    # No cachear index.html para que los nuevos builds se reflejen inmediatamente
    <FilesMatch "index\.html$">
        Header set Cache-Control "no-cache, no-store, must-revalidate"
        Header set Pragma "no-cache"
        Header set Expires "0"
    </FilesMatch>

    # Reverse proxy para la API
    ProxyPreserveHost On
    ProxyPass /api/v1/ http://127.0.0.1:8000/api/v1/
    ProxyPassReverse /api/v1/ http://127.0.0.1:8000/api/v1/

    ProxyPass /health http://127.0.0.1:8000/health
    ProxyPassReverse /health http://127.0.0.1:8000/health

    ProxyPass /uploads/ http://127.0.0.1:8000/uploads/
    ProxyPassReverse /uploads/ http://127.0.0.1:8000/uploads/

    ProxyPass /docs http://127.0.0.1:8000/docs
    ProxyPassReverse /docs http://127.0.0.1:8000/docs
    ProxyPass /openapi.json http://127.0.0.1:8000/openapi.json
    ProxyPassReverse /openapi.json http://127.0.0.1:8000/openapi.json

    <Directory /var/www/html/zeron-crm>
        Options -Indexes +FollowSymLinks
        AllowOverride None
        Require all granted

        RewriteEngine On
        RewriteBase /
        RewriteRule ^index\.html$ - [L]
        RewriteCond %{REQUEST_FILENAME} !-f
        RewriteCond %{REQUEST_FILENAME} !-d
        RewriteRule . /index.html [L]
    </Directory>

    ErrorLog ${APACHE_LOG_DIR}/zeron_crm_error.log
    CustomLog ${APACHE_LOG_DIR}/zeron_crm_access.log combined

    SSLCertificateFile /etc/letsencrypt/live/tudominio.com/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/tudominio.com/privkey.pem
    Include /etc/letsencrypt/options-ssl-apache.conf
</VirtualHost>
</IfModule>
```

### 7.5 Habilitar los sitios y reiniciar Apache

```bash
sudo a2ensite zeron-crm.conf
sudo a2ensite zeron-crm-le-ssl.conf
sudo a2dissite 000-default.conf    # Deshabilitar sitio por defecto (opcional)
sudo apache2ctl configtest         # Verificar configuración
sudo systemctl restart apache2
```

---

## 8. Servicio Systemd (Backend como servicio)

### 8.1 Crear el archivo de servicio

```bash
sudo tee /etc/systemd/system/zeron-crm-api.service > /dev/null << 'EOF'
[Unit]
Description=Zeron CRM API (FastAPI + Uvicorn)
After=network.target postgresql.service docker.service

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/zrn-crm/backend
EnvironmentFile=/home/ubuntu/zrn-crm/backend/.env
ExecStart=/home/ubuntu/zrn-crm/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```

### 8.2 Habilitar e iniciar el servicio

```bash
sudo systemctl daemon-reload
sudo systemctl enable zeron-crm-api.service
sudo systemctl start zeron-crm-api.service
```

### 8.3 Verificar el estado

```bash
sudo systemctl status zeron-crm-api.service
# Debe mostrar: Active: active (running)

curl http://127.0.0.1:8000/health
# Respuesta esperada: {"status":"ok","message":"Zeron CRM API is running"}
```

---

## 9. SSL / HTTPS con Let's Encrypt

### 9.1 Obtener certificado SSL

```bash
sudo certbot --apache -d tudominio.com
```

### 9.2 Renovación automática

```bash
sudo certbot renew --dry-run
```

---

## 10. Despliegue de Producción — Paso a Paso Completo

```bash
# ═══════════════════════════════════════════════════
# PASO 1: Preparar el sistema (Ubuntu nuevo)
# ═══════════════════════════════════════════════════
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv python3-dev build-essential \
    postgresql postgresql-contrib apache2 git certbot python3-certbot-apache \
    software-properties-common curl wget libxml2-dev libxslt1-dev libffi-dev libssl-dev
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# ═══════════════════════════════════════════════════
# PASO 2: Configurar PostgreSQL
# ═══════════════════════════════════════════════════
sudo systemctl enable postgresql && sudo systemctl start postgresql
sudo -u postgres psql -c "CREATE USER zeron_user WITH PASSWORD 'TU_PASSWORD_SEGURA';"
sudo -u postgres psql -c "CREATE DATABASE zeron_crm OWNER zeron_user;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE zeron_crm TO zeron_user;"

# ═══════════════════════════════════════════════════
# PASO 3: Clonar repositorios
# ═══════════════════════════════════════════════════
mkdir -p /home/ubuntu/zrn-crm && cd /home/ubuntu/zrn-crm
git clone https://github.com/zeron-team/zrn-crm-be.git backend
git clone https://github.com/zeron-team/zrn-crm-fe.git frontend

# ═══════════════════════════════════════════════════
# PASO 4: Configurar Backend
# ═══════════════════════════════════════════════════
cd /home/ubuntu/zrn-crm/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Crear archivo .env
SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))")
cat > .env << ENVEOF
DATABASE_URL=postgresql://zeron_user:TU_PASSWORD_SEGURA@localhost:5432/zeron_crm
SECRET_KEY=$SECRET
ACCESS_TOKEN_EXPIRE_MINUTES=480
ENVEOF

# Ejecutar migraciones
alembic upgrade head

# Crear usuario admin
python3 -c "
from app.database import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash
db = SessionLocal()
admin = User(email='admin@tudominio.com', full_name='Administrador',
    hashed_password=get_password_hash('TuPasswordSegura123'),
    is_active=True, role='admin')
db.add(admin)
db.commit()
print('✅ Usuario admin creado')
db.close()
"
deactivate

# ═══════════════════════════════════════════════════
# PASO 5: Configurar Frontend
# ═══════════════════════════════════════════════════
cd /home/ubuntu/zrn-crm/frontend
npm install
npm run build
sudo mkdir -p /var/www/html/zeron-crm
sudo cp -r dist/* /var/www/html/zeron-crm/
sudo chown -R www-data:www-data /var/www/html/zeron-crm

# ═══════════════════════════════════════════════════
# PASO 6: Configurar Apache
# ═══════════════════════════════════════════════════
sudo a2enmod proxy proxy_http rewrite ssl headers
# Crear los archivos de VirtualHost (ver sección 7.3 y 7.4)
sudo a2ensite zeron-crm.conf
sudo apache2ctl configtest
sudo systemctl restart apache2

# ═══════════════════════════════════════════════════
# PASO 7: Configurar servicio systemd
# ═══════════════════════════════════════════════════
# Crear el archivo de servicio (ver sección 8.1)
sudo systemctl daemon-reload
sudo systemctl enable zeron-crm-api.service
sudo systemctl start zeron-crm-api.service

# ═══════════════════════════════════════════════════
# PASO 8: Configurar SSL
# ═══════════════════════════════════════════════════
sudo certbot --apache -d tudominio.com

# ═══════════════════════════════════════════════════
# PASO 9: Verificar todo
# ═══════════════════════════════════════════════════
curl http://127.0.0.1:8000/health
curl -s -o /dev/null -w "%{http_code}" https://tudominio.com/
sudo systemctl status zeron-crm-api.service
```

---

## 11. Estructura del Proyecto

### Backend (`zrn-crm-be`)

```
backend/
├── .env                          # Variables de entorno (NO subir a git)
├── .gitignore                    # Archivos ignorados por git
├── INSTALL.md                    # Este documento
├── requirements.txt              # Dependencias Python
├── alembic.ini                   # Configuración de Alembic
├── alembic/                      # Migraciones de base de datos
│   ├── env.py
│   ├── script.py.mako
│   └── versions/                 # 30+ archivos de migración
├── arca/                         # Certificados ARCA/AFIP
│   └── certs/                    # .crt y .key
├── docs/                         # Documentación del proyecto
│   ├── INSTALL.md                # Manual general
│   ├── README.md                 # README principal
│   ├── README_ES.md              # README en español
│   ├── golden_rules.md           # Reglas del proyecto
│   └── docker-compose.yml        # Configuración Docker
├── uploads/                      # Archivos subidos
│   ├── invoices/                 # PDFs de facturas
│   └── service_payments/         # Comprobantes de pago
└── app/                          # Código fuente principal
    ├── main.py                   # Punto de entrada FastAPI
    ├── database.py               # Conexión a BD y Base declarativa
    ├── core/
    │   ├── config.py             # Configuración (Settings)
    │   └── security.py           # Hash passwords, JWT tokens
    ├── models/                   # Modelos SQLAlchemy (39 archivos)
    │   ├── user.py               # User
    │   ├── role_config.py        # RoleConfig (permisos)
    │   ├── client.py             # Client
    │   ├── contact.py            # Contact
    │   ├── provider.py           # Provider
    │   ├── product.py            # Product
    │   ├── category.py           # Family, Category, Subcategory
    │   ├── invoice.py            # Invoice, InvoiceStatus
    │   ├── invoice_item.py       # InvoiceItem
    │   ├── invoice_iva_item.py   # InvoiceIvaItem (ARCA)
    │   ├── invoice_audit_log.py  # InvoiceAuditLog
    │   ├── arca_config.py        # ArcaConfig
    │   ├── quote.py              # Quote
    │   ├── quote_item.py         # QuoteItem
    │   ├── quote_installment.py  # QuoteInstallment
    │   ├── lead.py               # Lead
    │   ├── calendar.py           # CalendarEvent
    │   ├── activity_note.py      # ActivityNote
    │   ├── note.py               # Note
    │   ├── client_service.py     # ClientService
    │   ├── provider_service.py   # ProviderService
    │   ├── service_payment.py    # ServicePayment
    │   ├── delivery_note.py      # DeliveryNote (Remito)
    │   ├── payment_order.py      # PaymentOrder
    │   ├── purchase_order.py     # PurchaseOrder
    │   ├── warehouse.py          # Warehouse
    │   ├── inventory.py          # Inventory
    │   ├── exchange_rate.py      # ExchangeRate
    │   ├── ticket.py             # Ticket (soporte)
    │   ├── project.py            # Project
    │   ├── employee.py           # Employee
    │   ├── time_entry.py         # TimeEntry
    │   ├── payroll.py            # Payroll
    │   ├── email_account.py      # EmailAccount
    │   ├── email_message.py      # EmailMessage
    │   ├── email_signature.py    # EmailSignature
    │   ├── wiki.py               # WikiPage
    │   └── dashboard_config.py   # DashboardConfig
    ├── schemas/                  # Schemas Pydantic (18 archivos)
    ├── repositories/             # Capa de acceso a datos (12 archivos)
    ├── services/                 # Lógica de negocio (12 archivos)
    │   ├── arca_service.py       # Integración ARCA/AFIP
    │   └── invoice_pdf_service.py # Generación PDF facturas
    └── api/                      # Capa de API
        ├── api.py                # Router principal
        └── endpoints/            # 36 archivos de endpoints
```

### Frontend (`zrn-crm-fe`)

```
frontend/
├── .gitignore
├── package.json / package-lock.json
├── vite.config.ts / tailwind.config.js
├── tsconfig.json / tsconfig.app.json / tsconfig.node.json
├── index.html
├── public/
└── src/
    ├── main.tsx / App.tsx / i18n.ts
    ├── api/client.ts
    ├── context/AuthContext.tsx
    ├── components/               # 13 componentes
    │   ├── Layout.tsx            # Layout principal (sidebar)
    │   ├── ProtectedRoute.tsx
    │   ├── ArcaConfigPanel.tsx   # Configuración ARCA
    │   ├── ArcaInvoiceModal.tsx  # Modal facturación ARCA
    │   ├── HeaderClock.tsx       # Reloj contextual
    │   ├── NotificationBar.tsx / NotificationBell.tsx
    │   └── ...
    ├── pages/                    # 37 páginas
    │   ├── Home.tsx              # Landing ZeRoN 360°
    │   ├── Login.tsx
    │   ├── Dashboard.tsx / DashboardHub.tsx
    │   ├── Users.tsx / RolePermissions.tsx
    │   ├── Leads.tsx / LeadProfile.tsx
    │   ├── Clients.tsx / ClientProfile.tsx
    │   ├── Contacts.tsx
    │   ├── Products.tsx / Categories.tsx
    │   ├── Providers.tsx / ServicePurchases.tsx
    │   ├── Quotes.tsx
    │   ├── Billing.tsx / Finances.tsx
    │   ├── DeliveryNotes.tsx / PaymentOrders.tsx / PurchaseOrders.tsx
    │   ├── Inventory.tsx / Warehouses.tsx
    │   ├── ExchangeRates.tsx
    │   ├── Calendar.tsx / Notes.tsx
    │   ├── Projects.tsx / ProjectBoard.tsx
    │   ├── Support.tsx (Tickets)
    │   ├── Employees.tsx / TimeTracking.tsx / Payroll.tsx
    │   ├── Sellers.tsx
    │   ├── Email.tsx / WhatsApp.tsx
    │   ├── Wiki.tsx
    │   └── Settings.tsx
    └── locales/
        ├── en.json
        └── es.json
```

---

## 12. Módulos y Funcionalidades

### 12.1 Autenticación y Roles
- Login con email + password, tokens JWT (default: 8 horas)
- Roles: `admin`, `user`; permisos configurables por módulo

### 12.2 Dashboard Hub
- Hub de dashboards: Ventas, Compras, Inventario, Productos, Proveedores, CRM, Cashflow, RRHH
- KPIs dinámicos con widgets arrastrables (drag & drop)

### 12.3 CRM (Leads, Clientes, Contactos)
- Leads: estados New → Contacted → Qualified → Converted → Lost
- Clientes: datos fiscales (CUIT/DNI), condición tributaria, perfil con historial
- Contactos asociados a clientes

### 12.4 Productos y Categorías
- Tipos: Producto, Servicio, Mano de Obra
- Jerarquía: Familia → Categoría → Subcategoría
- Precios con moneda (ARS, USD, EUR)

### 12.5 Facturación y ARCA
- Facturas emitidas/recibidas con estados personalizables
- Integración ARCA/AFIP: emisión electrónica, CAE, padrones
- Generación de PDF conforme RG 4291
- Audit trail de cambios

### 12.6 Presupuestos (Quotes)
- Presupuestos con ítems vinculados a productos
- Sistema de cuotas (installments) con seguimiento de cobro

### 12.7 Proveedores y Servicios
- Servicios de proveedores con ciclos de facturación
- Servicios de clientes, pagos registrados

### 12.8 Documentos Contables
- Remitos (Delivery Notes)
- Órdenes de Pago (Payment Orders)
- Órdenes de Compra (Purchase Orders)

### 12.9 Inventario y Almacenes
- Depósitos con umbrales críticos
- Stock por producto y depósito

### 12.10 Finanzas
- Tipos de cambio USD/EUR
- Reportes financieros consolidados
- Cashflow analysis

### 12.11 Calendario y Notas
- Eventos con colores, estados, follow-ups
- Notas generales del sistema

### 12.12 Gestión de Proyectos
- Proyectos con tablero Kanban
- Seguimiento de tareas

### 12.13 Soporte (Tickets)
- Tickets con estados, prioridades, asignación
- Comentarios con notas internas
- Numeración automática (TK-00001)

### 12.14 RRHH
- Empleados, control horario (Time Tracking)
- Liquidación de haberes (Payroll) conforme legislación argentina
- Dashboard RRHH con análisis demográfico y salarial

### 12.15 Comunicaciones
- Email integrado (cuentas, mensajes, firmas)
- WhatsApp (servicio Node.js separado)

### 12.16 Wiki Interna
- Base de conocimiento con páginas editables

### 12.17 Configuración
- Idioma (ES/EN), tasas de cambio, perfil de usuario
- Configuración ARCA por punto de venta

---

## 13. API Endpoints

Base URL: `/api/v1`

### Autenticación
| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/auth/login` | Iniciar sesión |
| `GET` | `/auth/me` | Obtener usuario actual |

### Usuarios y Roles
| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET/POST` | `/users/` | Listar / Crear usuarios |
| `PUT/DELETE` | `/users/{id}` | Actualizar / Eliminar usuario |
| `GET/POST` | `/role-configs/` | Listar / Crear configuraciones de rol |

### CRM (Clientes, Contactos, Leads)
| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET/POST` | `/clients/` | Listar / Crear clientes |
| `GET/PUT/DELETE` | `/clients/{id}` | CRUD cliente individual |
| `GET/POST/PUT/DELETE` | `/contacts/` | CRUD contactos |
| `GET/POST` | `/leads/` | Listar / Crear leads |
| `GET/PUT/DELETE` | `/leads/{id}` | CRUD lead individual |

### Productos y Categorías
| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET/POST/PUT/DELETE` | `/products/` | CRUD productos |
| `GET` | `/categories/tree` | Árbol completo |
| `GET/POST/PUT/DELETE` | `/categories/` | CRUD categorías |

### Facturación
| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET/POST/PUT/DELETE` | `/invoices/` | CRUD facturas |
| `POST` | `/invoices/{id}/upload` | Subir PDF |
| `GET/POST/PUT/DELETE` | `/invoices/statuses` | CRUD estados |

### ARCA (Facturación Electrónica)
| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/arca/emit` | Emitir factura electrónica |
| `GET` | `/arca/last-voucher` | Último comprobante |
| `GET` | `/arca/taxpayer/{cuit}` | Consulta padrón |
| `GET/POST/PUT` | `/arca/config` | Configuración ARCA |

### Presupuestos y Cuotas
| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET/POST/PUT/DELETE` | `/quotes/` | CRUD presupuestos |
| `GET/POST` | `/quotes/{id}/installments` | Cuotas del presupuesto |

### Documentos Contables
| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET/POST/PUT/DELETE` | `/delivery-notes/` | Remitos |
| `GET/POST/PUT/DELETE` | `/payment-orders/` | Órdenes de pago |
| `GET/POST/PUT/DELETE` | `/purchase-orders/` | Órdenes de compra |

### Servicios y Pagos
| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET/POST/PUT/DELETE` | `/provider-services/` | Servicios de proveedores |
| `GET/POST` | `/client-services/` | Servicios de clientes |
| `GET/POST` | `/service-payments/` | Pagos de servicios |

### Inventario
| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET/POST/PUT/DELETE` | `/warehouses/` | Depósitos |
| `GET/POST/PUT` | `/inventory/` | Stock |

### Calendario y Notas
| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET/POST/PUT/DELETE` | `/calendar/` | Eventos |
| `POST/PUT/DELETE` | `/calendar/{id}/notes` | Notas de evento |
| `GET/POST/PUT/DELETE` | `/notes/` | Notas generales |

### Proyectos y Tickets
| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET/POST/PUT/DELETE` | `/projects/` | Proyectos |
| `GET/POST/PUT/DELETE` | `/tickets/` | Tickets de soporte |

### RRHH
| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET/POST/PUT/DELETE` | `/employees/` | Empleados |
| `GET/POST` | `/time-entries/` | Registro de horas |
| `GET/POST` | `/payroll/` | Liquidaciones |

### Comunicaciones
| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET/POST` | `/email/` | Email |
| `GET/POST` | `/whatsapp/` | WhatsApp |

### Otros
| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET/PUT` | `/dashboard-config/{userId}` | Config widgets |
| `GET` | `/dashboards/{type}` | Datos dashboard por tipo |
| `GET/POST` | `/exchange-rates/` | Tipos de cambio |
| `GET/POST/PUT/DELETE` | `/wiki/` | Wiki interna |
| `GET` | `/sellers/` | Vendedores |
| `GET` | `/notifications/` | Notificaciones |
| `GET` | `/health` | Health check |

### Documentación interactiva
- **Swagger UI**: `https://tudominio.com/docs`
- **OpenAPI JSON**: `https://tudominio.com/openapi.json`

---

## 14. Internacionalización (i18n)

- Idioma por defecto: **Español**
- Soporta: **Español** e **Inglés**
- Cambio desde **Settings** → se guarda en `localStorage`
- Archivos: `src/locales/en.json` y `src/locales/es.json`

---

## 15. Variables de Entorno

### Backend (`.env`)

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `DATABASE_URL` | URL de conexión PostgreSQL | `postgresql://user:pass@localhost:5432/zeron_crm` |
| `SECRET_KEY` | Clave secreta para firmar JWT | `clave-random-segura-base64` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Duración del token JWT (minutos) | `480` (8 horas) |

### Frontend

No requiere variables de entorno. La URL de la API se determina automáticamente:
- **Producción**: `/api/v1` (reverse proxy Apache)
- **Desarrollo**: `http://localhost:8000/api/v1`

---

## 16. Comandos Útiles

### Backend

```bash
# Iniciar en modo desarrollo
cd /home/ubuntu/zrn-crm/backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Migraciones
alembic revision --autogenerate -m "descripción del cambio"
alembic upgrade head
alembic downgrade -1
alembic history
alembic current
```

### Frontend

```bash
cd /home/ubuntu/zrn-crm/frontend
npm run dev          # Desarrollo
npm run build        # Build producción
npm run preview      # Preview del build
npm run lint         # Lint del código
```

### Servicios del sistema

```bash
# Backend API
sudo systemctl start|stop|restart|status zeron-crm-api
sudo journalctl -u zeron-crm-api -f

# Apache
sudo systemctl restart apache2
sudo apache2ctl configtest
sudo tail -f /var/log/apache2/zeron_crm_error.log

# PostgreSQL
sudo systemctl status postgresql
sudo -u postgres psql -d zeron_crm
```

### Despliegue rápido

```bash
# Actualizar frontend
cd /home/ubuntu/zrn-crm/frontend && git pull && npm install && npm run build
sudo rm -rf /var/www/html/zeron-crm/* && sudo cp -r dist/* /var/www/html/zeron-crm/

# Actualizar backend
cd /home/ubuntu/zrn-crm/backend && git pull && source venv/bin/activate
pip install -r requirements.txt && alembic upgrade head && deactivate
sudo systemctl restart zeron-crm-api
```

---

## 17. Solución de Problemas

### El backend no inicia
```bash
sudo journalctl -u zeron-crm-api -n 50 --no-pager
sudo systemctl status postgresql
cd /home/ubuntu/zrn-crm/backend && source venv/bin/activate
python3 -c "from app.database import engine; engine.connect(); print('✅ DB OK')"
```

### Error 502 Bad Gateway
```bash
sudo systemctl start zeron-crm-api
curl http://127.0.0.1:8000/health
```

### El frontend muestra página en blanco
```bash
ls -la /var/www/html/zeron-crm/
cd /home/ubuntu/zrn-crm/frontend && npm run build
sudo cp -r dist/* /var/www/html/zeron-crm/
```

### Error de CORS
En desarrollo el backend permite `allow_origins=["*"]`. En producción se maneja con el reverse proxy de Apache.

### Migraciones fallidas
```bash
alembic current
alembic stamp head
alembic revision --autogenerate -m "fix migration"
alembic upgrade head
```

### Build frontend falla por memoria
```bash
# Crear swap si no existe
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile

# Build con memoria limitada
NODE_OPTIONS="--max-old-space-size=512" npm run build
```

---

> 📝 **Nota:** Este documento cubre la instalación completa de ZeRoN 360° v3.0.0. Para soporte, contactar al equipo en GitHub.
