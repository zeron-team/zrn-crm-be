---
description: Zeron CRM - Golden Rules & Software Factory Mindset
---

# Zeron CRM - Golden Rules & Software Factory Mindset

These rules define the baseline expectations and architectural mindset for the Zeron CRM. When working on this project, these rules **MUST** be adhered to without needing to be repeated by the user.

## 1. Core Philosophy (Software Factory Mindset)
- **Scalability and Professionalism**: Code must be modular, highly readable, well-documented, and follow standard software engineering patterns (MVC, clean architecture, etc.). MVP code is not an excuse for messy code.
- **Domain Specialization**: The system is tailored for managing **IT Infrastructure and Software Development**. Data models should reflect this (e.g., Tracking server IPs, domains, git repositories, SSL certificates within clients or products).

## 2. Zero Disruption Policy (Vtiger Coexistence)
- **No Overwrites**: The existing `vtiger` installation at `zeron.ovh` (served by Apache) MUST NOT be modified or disrupted during development. 
- **Port Isolation**: New web services and APIs must run on separate, explicit ports (avoid `80`, `443`, `3306`, `9090`, `3000` which are currently in use by Apache, MySQL, Prometheus, Grafana).
- **Data Isolation**: The CRM must use a dedicated, entirely separate database schema. Absolutely no reusing or altering `vtiger` tables.

## 3. Product Features Checklist (MVP Modules)
When extending the system, ensure the core MVP guarantees are met:
1. **Usuarios**: Roles and Users ABM.
2. **Clientes**: ABM of companies.
3. **Contactos**: Associated with clients and providers.
4. **Productos**: ABM of products/services and sales.
5. **Proveedores**: ABM of providers.
6. **Facturación**: Invoices created/received (Desc, note, attachment, amount). Invoices created by ZERON require customizable States (ABM de estados).
7. **Calendarios**: General expiration dates tracking.

## 4. Workflows and Implementation
- **API-First**: Build modules as independent API endpoints first, to allow for a flexible decoupling between backend and UI.
- **Rich Aesthetics**: The frontend must look premium, modern, and utilize vibrant, responsive designs with smooth interactions (refer to dynamic design guidelines).
