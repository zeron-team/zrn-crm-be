# ZRN360° — Manual de Instalación Completo

> **Versión**: 3.0.0  
> **Plataforma**: CRM / ERP / RRHH — Gestión empresarial integral 360°  
> **Última actualización**: Marzo 2026

---

## Índice

1. [Requisitos del Sistema](#1-requisitos-del-sistema)
2. [Arquitectura General](#2-arquitectura-general)
3. [Clonar el Repositorio](#3-clonar-el-repositorio)
4. [Base de Datos — PostgreSQL 15 (Docker)](#4-base-de-datos--postgresql-15-docker)
5. [Backend — API FastAPI (Python)](#5-backend--api-fastapi-python)
6. [Frontend — React + Vite](#6-frontend--react--vite)
7. [WhatsApp Service — Microservicio Node.js](#7-whatsapp-service--microservicio-nodejs)
8. [Servidor Web — Apache con SSL](#8-servidor-web--apache-con-ssl)
9. [Servicios Systemd](#9-servicios-systemd)
10. [SSL con Let's Encrypt](#10-ssl-con-lets-encrypt)
11. [Primer Inicio y Configuración](#11-primer-inicio-y-configuración)
12. [Variables de Entorno](#12-variables-de-entorno)
13. [Estructura del Proyecto](#13-estructura-del-proyecto)
14. [Comandos Útiles](#14-comandos-útiles)
15. [Solución de Problemas](#15-solución-de-problemas)

---

## 1. Requisitos del Sistema

### Hardware Mínimo
| Recurso | Mínimo | Recomendado |
|---------|--------|-------------|
| CPU | 2 cores | 4 cores |
| RAM | 4 GB | 8 GB |
| Disco | 20 GB SSD | 50 GB SSD |

### Software Requerido
| Software | Versión | Uso |
|----------|---------|-----|
| **Ubuntu** | 22.04 LTS o superior | Sistema operativo |
| **Python** | 3.10+ | Backend API |
| **Node.js** | 20.x LTS | Frontend build + WhatsApp service |
| **Docker** + Docker Compose | Últimas versiones | PostgreSQL |
| **Apache2** | 2.4+ | Servidor web (reverse proxy + frontend) |
| **Git** | 2.x | Control de versiones |

---

## 2. Arquitectura General

```
┌─────────────────────────────────────────────────────────┐
│                    Internet (HTTPS :443)                 │
└────────────────────────┬────────────────────────────────┘
                         │
                   ┌─────▼─────┐
                   │  Apache2  │  SSL termination
                   │  (proxy)  │  + SPA fallback
                   └─────┬─────┘
                         │
          ┌──────────────┼──────────────┐
          │              │              │
    /api/v1/*      / (static)    /ws (websocket)
          │              │              │
   ┌──────▼──────┐ ┌─────▼─────┐ ┌─────▼─────┐
   │   FastAPI   │ │  React    │ │ WhatsApp  │
   │   :8000     │ │  (dist/)  │ │  :3001    │
   │   Backend   │ │  Frontend │ │  Service  │
   └──────┬──────┘ └───────────┘ └─────┬─────┘
          │                            │
          └────────────┬───────────────┘
                       │
                ┌──────▼──────┐
                │ PostgreSQL  │
                │ :5432       │
                │ (Docker)    │
                └─────────────┘
```

---

## 3. Clonar el Repositorio

```bash
# Clonar desde GitHub
git clone https://github.com/zeron-team/zrn360.git /home/ubuntu/zrn-crm
cd /home/ubuntu/zrn-crm
```

---

## 4. Base de Datos — PostgreSQL 15 (Docker)

### 4.1 Instalar Docker

```bash
# Instalar Docker
sudo apt update
sudo apt install -y docker.io docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
# Cerrar sesión y volver a entrar para que el grupo tome efecto
```

### 4.2 Levantar PostgreSQL

El proyecto incluye un `docker-compose.yml` en la raíz:

```bash
cd /home/ubuntu/zrn-crm
docker compose up -d
```

Contenido del `docker-compose.yml`:
```yaml
version: '3.8'

services:
  db:
    image: postgres:15
    container_name: zeron_crm_db
    restart: always
    environment:
      POSTGRES_USER: zeron_user
      POSTGRES_PASSWORD: zeron_password
      POSTGRES_DB: zeron_crm
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

### 4.3 Verificar conexión

```bash
docker exec -it zeron_crm_db psql -U zeron_user -d zeron_crm -c "SELECT 1;"
```

> **IMPORTANTE**: En producción, cambiar `POSTGRES_PASSWORD` por una contraseña segura y actualizar el `.env` del backend acorde.

---

## 5. Backend — API FastAPI (Python)

### 5.1 Instalar Python 3.10+

```bash
sudo apt install -y python3 python3-pip python3-venv
python3 --version  # Debe ser 3.10+
```

### 5.2 Crear entorno virtual

```bash
cd /home/ubuntu/zrn-crm/backend
python3 -m venv venv
source venv/bin/activate
```

### 5.3 Instalar dependencias

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

Dependencias principales:
- **FastAPI** — Framework web
- **Uvicorn** — Servidor ASGI
- **SQLAlchemy 2.0** — ORM
- **python-jose** — JWT tokens
- **zeep** — Cliente SOAP para ARCA/AFIP
- **httpx** — Cliente HTTP async
- **psycopg2-binary** — Driver PostgreSQL
- **Pillow** — Procesamiento de imágenes
- **openpyxl** — Exportación Excel
- **reportlab** — Generación PDF

### 5.4 Configurar variables de entorno

```bash
cat > /home/ubuntu/zrn-crm/backend/.env << 'EOF'
DATABASE_URL=postgresql://zeron_user:zeron_password@localhost:5432/zeron_crm
SECRET_KEY=CAMBIAR_POR_UNA_CLAVE_SEGURA_DE_64_CARACTERES
ACCESS_TOKEN_EXPIRE_MINUTES=480
EOF
```

> **Para generar un SECRET_KEY seguro:**
> ```bash
> python3 -c "import secrets; print(secrets.token_urlsafe(48))"
> ```

### 5.5 Crear las tablas en la base de datos

```bash
cd /home/ubuntu/zrn-crm/backend
source venv/bin/activate
python3 -c "
from app.database import engine, Base
Base.metadata.create_all(bind=engine)
print('Tablas creadas exitosamente')
"
```

### 5.6 Crear usuario administrador

```bash
python3 -c "
from app.database import SessionLocal
from app.models.user import User
from passlib.context import CryptContext

pwd = CryptContext(schemes=['bcrypt'])
db = SessionLocal()

admin = User(
    email='admin@zeron.ovh',
    full_name='Administrador',
    hashed_password=pwd.hash('Admin123!'),
    role='admin',
    is_active=True
)
db.add(admin)
db.commit()
print(f'Usuario admin creado: admin@zeron.ovh')
db.close()
"
```

### 5.7 Crear directorio de uploads

```bash
mkdir -p /home/ubuntu/zrn-crm/backend/uploads/invoices
```

### 5.8 Verificar que el backend funciona

```bash
cd /home/ubuntu/zrn-crm/backend
source venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000

# En otra terminal:
curl http://localhost:8000/health
# Respuesta esperada: {"status":"ok","message":"Zeron CRM API is running"}
```

Detener con `Ctrl+C` tras verificar.

---

## 6. Frontend — React + Vite

### 6.1 Instalar Node.js 20 LTS

```bash
# Opción A: Usando nvm (recomendado)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
source ~/.bashrc
nvm install 20
nvm use 20
node -v  # Debe ser v20.x

# Opción B: Usando NodeSource
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

### 6.2 Instalar dependencias

```bash
cd /home/ubuntu/zrn-crm/frontend
npm install
```

Dependencias principales:
- **React 19** — UI framework
- **React Router DOM 7** — Routing SPA
- **Recharts 3** — Gráficos y dashboards
- **Lucide React** — Iconos
- **Axios** — Cliente HTTP
- **i18next** — Internacionalización ES/EN
- **@dnd-kit** — Drag & drop (Kanban)
- **date-fns** — Manipulación de fechas

### 6.3 Configurar API URL (opcional)

Si el backend corre en otro host/puerto, editar `frontend/src/api/client.ts`:
```typescript
const api = axios.create({
    baseURL: '/api/v1',  // Usa proxy Apache
});
```

### 6.4 Build de producción

```bash
cd /home/ubuntu/zrn-crm/frontend

# IMPORTANTE: Si el servidor tiene <8GB RAM, detener el API antes de compilar
sudo systemctl stop zeron-crm-api.service 2>/dev/null

# Compilar
NODE_OPTIONS="--max-old-space-size=3072" npm run build

# Copiar al directorio web
sudo mkdir -p /var/www/html/zeron-crm
sudo rm -rf /var/www/html/zeron-crm/*
sudo cp -r dist/* /var/www/html/zeron-crm/
sudo chown -R www-data:www-data /var/www/html/zeron-crm/

# Reiniciar el API si lo detuvimos
sudo systemctl start zeron-crm-api.service
```

> **⚠️ NOTA SOBRE MEMORIA**: El build de Vite puede consumir ~2-3GB de RAM. En servidores con poca memoria, detener servicios no esenciales y agregar swap:
> ```bash
> sudo fallocate -l 2G /swapfile
> sudo chmod 600 /swapfile
> sudo mkswap /swapfile
> sudo swapon /swapfile
> echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
> ```

### 6.5 Desarrollo local

```bash
cd /home/ubuntu/zrn-crm/frontend
npm run dev
# Abre en http://localhost:5173
```

---

## 7. WhatsApp Service — Microservicio Node.js

### 7.1 Instalar dependencias

```bash
cd /home/ubuntu/zrn-crm/whatsapp-service
npm install
```

### 7.2 Instalar Chromium (requerido por whatsapp-web.js)

```bash
sudo apt install -y chromium-browser
# O instalar Puppeteer's Chromium:
npx puppeteer browsers install chrome
```

### 7.3 Crear tablas de WhatsApp en la DB

El servicio crea las tablas automáticamente al iniciar (`wa_conversations`, `wa_messages`).

### 7.4 Verificar que funciona

```bash
cd /home/ubuntu/zrn-crm/whatsapp-service
node server.js
# Debe iniciar en puerto 3001
# Escanear QR desde http://localhost:3001/qr
```

Detener con `Ctrl+C`.

---

## 8. Servidor Web — Apache con SSL

### 8.1 Instalar Apache y módulos

```bash
sudo apt install -y apache2
sudo a2enmod ssl rewrite proxy proxy_http proxy_wstunnel headers
sudo systemctl restart apache2
```

### 8.2 Crear el VirtualHost

```bash
sudo tee /etc/apache2/sites-available/zrn360.conf << 'EOF'
<VirtualHost *:80>
    ServerName TU_DOMINIO.com
    RewriteEngine On
    RewriteRule ^(.*)$ https://%{HTTP_HOST}$1 [R=301,L]
</VirtualHost>
EOF
```

### 8.3 Crear el VirtualHost SSL (después de configurar SSL en paso 10)

```bash
sudo tee /etc/apache2/sites-available/zrn360-ssl.conf << 'CONF'
<IfModule mod_ssl.c>
<VirtualHost *:443>
    ServerAdmin admin@TU_DOMINIO.com
    ServerName TU_DOMINIO.com
    DocumentRoot /var/www/html/zeron-crm

    # No cachear index.html para que los nuevos builds se apliquen inmediatamente
    <FilesMatch "index\.html$">
        Header set Cache-Control "no-cache, no-store, must-revalidate"
        Header set Pragma "no-cache"
        Header set Expires "0"
    </FilesMatch>

    # Reverse proxy para la API backend (FastAPI)
    ProxyPreserveHost On
    ProxyPass /api/v1/ http://127.0.0.1:8000/api/v1/
    ProxyPassReverse /api/v1/ http://127.0.0.1:8000/api/v1/

    # Health check
    ProxyPass /health http://127.0.0.1:8000/health
    ProxyPassReverse /health http://127.0.0.1:8000/health

    # Archivos subidos (facturas PDF, etc.)
    ProxyPass /uploads/ http://127.0.0.1:8000/uploads/
    ProxyPassReverse /uploads/ http://127.0.0.1:8000/uploads/

    # Documentación API (Swagger UI)
    ProxyPass /docs http://127.0.0.1:8000/docs
    ProxyPassReverse /docs http://127.0.0.1:8000/docs
    ProxyPass /openapi.json http://127.0.0.1:8000/openapi.json
    ProxyPassReverse /openapi.json http://127.0.0.1:8000/openapi.json

    # Archivos estáticos del frontend (React SPA)
    <Directory /var/www/html/zeron-crm>
        Options -Indexes +FollowSymLinks
        AllowOverride None
        Require all granted

        # SPA fallback: sirve index.html para todas las rutas que no sean archivos
        RewriteEngine On
        RewriteBase /
        RewriteRule ^index\.html$ - [L]
        RewriteCond %{REQUEST_FILENAME} !-f
        RewriteCond %{REQUEST_FILENAME} !-d
        RewriteRule . /index.html [L]
    </Directory>

    ErrorLog ${APACHE_LOG_DIR}/zrn360_error.log
    CustomLog ${APACHE_LOG_DIR}/zrn360_access.log combined

    # Certificados SSL (configurados por Certbot)
    SSLCertificateFile /etc/letsencrypt/live/TU_DOMINIO.com/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/TU_DOMINIO.com/privkey.pem
    Include /etc/letsencrypt/options-ssl-apache.conf
</VirtualHost>
</IfModule>
CONF
```

### 8.4 Habilitar el sitio

```bash
sudo a2ensite zrn360.conf zrn360-ssl.conf
sudo a2dissite 000-default.conf
sudo apache2ctl configtest  # Debe decir "Syntax OK"
sudo systemctl reload apache2
```

---

## 9. Servicios Systemd

### 9.1 Servicio del Backend API

```bash
sudo tee /etc/systemd/system/zeron-crm-api.service << 'EOF'
[Unit]
Description=ZRN360 API (FastAPI + Uvicorn)
After=network.target docker.service
Wants=docker.service

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

### 9.2 Servicio de WhatsApp

```bash
sudo tee /etc/systemd/system/zeron-whatsapp.service << 'EOF'
[Unit]
Description=ZRN360 WhatsApp Service
After=network.target docker.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/zrn-crm/whatsapp-service
ExecStart=/usr/bin/node server.js
Restart=on-failure
RestartSec=10
LimitNOFILE=65536
Environment=NODE_ENV=production
Environment=HOME=/home/ubuntu
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
```

> **Nota**: Ajustar la ruta de `node` en `ExecStart` si se usa nvm:
> ```bash
> # Encontrar la ruta correcta:
> which node
> # Ejemplo: /home/ubuntu/.nvm/versions/node/v20.19.5/bin/node
> ```

### 9.3 Habilitar e iniciar servicios

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now zeron-crm-api.service
sudo systemctl enable --now zeron-whatsapp.service
```

### 9.4 Verificar servicios

```bash
sudo systemctl status zeron-crm-api.service
sudo systemctl status zeron-whatsapp.service
```

---

## 10. SSL con Let's Encrypt

### 10.1 Instalar Certbot

```bash
sudo apt install -y certbot python3-certbot-apache
```

### 10.2 Obtener certificado

```bash
sudo certbot --apache -d TU_DOMINIO.com
```

Certbot configura automáticamente los certificados y la renovación.

### 10.3 Verificar renovación automática

```bash
sudo certbot renew --dry-run
```

---

## 11. Primer Inicio y Configuración

### 11.1 Verificar que todo funciona

```bash
# 1. Base de datos
docker ps | grep zeron_crm_db

# 2. Backend API
curl http://localhost:8000/health

# 3. Frontend (en el navegador)
# https://TU_DOMINIO.com

# 4. WhatsApp
curl http://localhost:3001/status 2>/dev/null || echo "WhatsApp service no iniciado"
```

### 11.2 Primer login

1. Abrir `https://TU_DOMINIO.com` en el navegador
2. Iniciar sesión con las credenciales del administrador creado en el paso 5.6
3. Ir a **Sistema → Configuración** para ajustar parámetros

### 11.3 Configurar ARCA/AFIP (facturación electrónica)

Para la integración con ARCA se requiere:
1. **Certificado digital** (`.crt`) y **clave privada** (`.key`) de ARCA/AFIP
2. **CUIT** de la empresa
3. **Punto de venta** autorizado
4. Subir los certificados desde **Configuración → ARCA**

> Los certificados se obtienen desde el sitio de ARCA/AFIP con clave fiscal nivel 3+.

---

## 12. Variables de Entorno

### Backend (`backend/.env`)

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `DATABASE_URL` | Conexión PostgreSQL | `postgresql://zeron_user:zeron_password@localhost:5432/zeron_crm` |
| `SECRET_KEY` | Clave para JWT tokens (64+ chars) | `ET5aLUQ...` (generada con `secrets.token_urlsafe(48)`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Duración de sesión en minutos | `480` (8 horas) |

### WhatsApp Service

Las credenciales de PostgreSQL están hardcodeadas en `whatsapp-service/server.js`:
```javascript
const pool = new Pool({
    host: 'localhost',
    port: 5432,
    database: 'zeron_crm',
    user: 'zeron_user',
    password: 'zeron_password',
});
```

> En producción, se recomienda mover estas credenciales a variables de entorno.

---

## 13. Estructura del Proyecto

```
zrn-crm/
├── docker-compose.yml          # PostgreSQL container
├── INSTALL.md                  # Este manual
├── .gitignore
│
├── backend/                    # API FastAPI (Python)
│   ├── .env                    # Variables de entorno (NO se sube a git)
│   ├── requirements.txt        # Dependencias Python
│   ├── venv/                   # Entorno virtual (NO se sube a git)
│   ├── uploads/                # Archivos subidos (facturas PDF, etc.)
│   └── app/
│       ├── main.py             # Entry point FastAPI
│       ├── database.py         # Conexión SQLAlchemy
│       ├── core/
│       │   └── config.py       # Settings (Pydantic)
│       ├── models/             # Modelos SQLAlchemy
│       │   ├── user.py
│       │   ├── client.py
│       │   ├── lead.py
│       │   ├── quote.py
│       │   ├── product.py
│       │   ├── invoice.py
│       │   ├── employee.py
│       │   ├── time_entry.py
│       │   ├── payroll.py
│       │   └── ...
│       ├── api/
│       │   ├── api.py          # Router principal
│       │   └── endpoints/      # Endpoints por módulo
│       │       ├── users.py
│       │       ├── clients.py
│       │       ├── leads.py
│       │       ├── quotes.py
│       │       ├── billing.py
│       │       ├── arca.py     # Integración ARCA/AFIP
│       │       ├── employees.py
│       │       ├── time_entries.py
│       │       ├── payroll.py
│       │       ├── dashboards.py
│       │       └── ...
│       ├── schemas/            # Schemas Pydantic
│       └── services/           # Lógica de negocio
│           ├── invoice_pdf_service.py
│           └── arca_service.py
│
├── frontend/                   # React SPA (TypeScript)
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   ├── dist/                   # Build de producción (NO se sube a git)
│   ├── node_modules/           # Dependencias (NO se sube a git)
│   ├── public/
│   └── src/
│       ├── App.tsx             # Router principal
│       ├── main.tsx            # Entry point
│       ├── api/
│       │   └── client.ts       # Axios instance
│       ├── context/
│       │   └── AuthContext.tsx  # Autenticación JWT
│       ├── components/
│       │   ├── Layout.tsx      # Sidebar + Header
│       │   ├── HeaderClock.tsx  # Reloj de fichadas
│       │   └── ...
│       ├── pages/
│       │   ├── Home.tsx        # Página de inicio v3.0.0
│       │   ├── Dashboard.tsx   # Panel de control
│       │   ├── DashboardHub.tsx # 8 dashboards BI
│       │   ├── Leads.tsx
│       │   ├── Clients.tsx
│       │   ├── Billing.tsx     # Facturación ARCA
│       │   ├── Employees.tsx
│       │   ├── TimeTracking.tsx
│       │   ├── Payroll.tsx     # Liquidación de sueldos
│       │   └── ... (30+ páginas)
│       └── i18n/               # Traducciones ES/EN
│
└── whatsapp-service/           # Microservicio WhatsApp
    ├── package.json
    └── server.js               # Express + whatsapp-web.js + WebSocket
```

---

## 14. Comandos Útiles

### Servicios
```bash
# Ver estado de todos los servicios
sudo systemctl status zeron-crm-api.service
sudo systemctl status zeron-whatsapp.service

# Reiniciar backend
sudo systemctl restart zeron-crm-api.service

# Ver logs del backend
sudo journalctl -u zeron-crm-api.service -f --no-pager

# Ver logs de WhatsApp
sudo journalctl -u zeron-whatsapp.service -f --no-pager
```

### Base de Datos
```bash
# Conectar a PostgreSQL
docker exec -it zeron_crm_db psql -U zeron_user -d zeron_crm

# Backup de la base de datos
docker exec zeron_crm_db pg_dump -U zeron_user zeron_crm > backup_$(date +%Y%m%d).sql

# Restaurar backup
docker exec -i zeron_crm_db psql -U zeron_user -d zeron_crm < backup_20260306.sql
```

### Frontend
```bash
# Compilar y desplegar frontend (workflow completo)
sudo systemctl stop zeron-crm-api.service
cd /home/ubuntu/zrn-crm/frontend
rm -rf dist node_modules/.vite
NODE_OPTIONS="--max-old-space-size=3072" npm run build
sudo rm -rf /var/www/html/zeron-crm/*
sudo cp -r dist/* /var/www/html/zeron-crm/
sudo chown -R www-data:www-data /var/www/html/zeron-crm/
sudo systemctl start zeron-crm-api.service
```

### Git
```bash
# Subir cambios
cd /home/ubuntu/zrn-crm
git add -A
git commit -m "Descripción del cambio"
git push
```

---

## 15. Solución de Problemas

### El build del frontend falla con "Killed" (OOM)

El build de Vite puede consumir mucha memoria. Soluciones:

1. **Detener el API antes de compilar**:
   ```bash
   sudo systemctl stop zeron-crm-api.service
   ```

2. **Agregar swap** si no existe:
   ```bash
   sudo fallocate -l 2G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   ```

3. **Limitar la memoria de Node**:
   ```bash
   NODE_OPTIONS="--max-old-space-size=3072" npm run build
   ```

4. **Usar el script de build**:
   ```bash
   bash /tmp/build_deploy.sh
   ```

### La API no inicia

```bash
# Ver error específico
sudo journalctl -u zeron-crm-api.service -n 50 --no-pager

# Verificar que la DB está corriendo
docker ps | grep zeron_crm_db

# Probar manualmente
cd /home/ubuntu/zrn-crm/backend
source venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Error 502 Bad Gateway en Apache

El backend no está corriendo:
```bash
sudo systemctl start zeron-crm-api.service
sudo systemctl status zeron-crm-api.service
```

### La página muestra una versión vieja después del deploy

Caché del navegador. Solución:
- **Ctrl+Shift+R** (hard reload)
- El `index.html` tiene headers `no-cache` configurados en Apache

### WhatsApp no conecta

```bash
# Ver logs
sudo journalctl -u zeron-whatsapp.service -n 50

# Verificar que Chromium está instalado
chromium-browser --version

# Limpiar sesión anterior
rm -rf /home/ubuntu/zrn-crm/whatsapp-service/.wwebjs_auth
sudo systemctl restart zeron-whatsapp.service
```

### Error de permisos en uploads

```bash
mkdir -p /home/ubuntu/zrn-crm/backend/uploads/invoices
chown -R ubuntu:ubuntu /home/ubuntu/zrn-crm/backend/uploads
```

---

## Módulos Incluidos en ZRN360° v3.0.0

| Módulo | Funcionalidades |
|--------|----------------|
| **Panel de Control** | Dashboard principal, Centro BI (8 dashboards), Notas rápidas |
| **CRM** | Leads, Presupuestos, Cuentas, Proveedores, Contactos, Calendario, Soporte, Vendedores |
| **Proyectos** | Tableros Kanban, Wiki/Documentación |
| **RRHH** | Legajos digitales, Fichadas con reloj, Liquidación de sueldos (ley argentina) |
| **Comunicaciones** | Email corporativo, WhatsApp Business |
| **ERP/Contabilidad** | Facturación ARCA/AFIP, Remitos, Órdenes de pago/compra, Inventario, Depósitos, Tipo de cambio |
| **Catálogo** | Productos/Servicios/Mano de obra, Categorías jerárquicas |
| **Sistema** | Usuarios, Roles y Permisos granulares, Configuración |

---

*ZRN360° — Gestión empresarial integral*
