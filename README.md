---
title: TallerApp
emoji: 🔧
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# TallerApp 🔧

Sistema de Gestión Integral para Taller de Reparaciones.

## Login
- **Usuario:** `admin`
- **Contraseña:** `admin123`
- ⚠️ Cambiar esta contraseña apenas entres la primera vez — se crea sola en cada arranque si no existe ningún usuario.

## Variables de entorno (configurar en el dashboard de la plataforma, nunca en el repo)
- `DATABASE_URL` — conexión Postgres (Supabase). Sin esto, la app usa SQLite local, que se borra en cada reinicio del servidor gratis.
- `SECRET_KEY` — clave para firmar los tokens de sesión. En Render se genera sola.

## Características
- Dashboard con métricas y gráficos
- CRM de clientes con historial
- Inventario de repuestos
- Órdenes de Trabajo
- Presupuestos y Facturas
- Licitaciones
- Múltiples usuarios con roles
