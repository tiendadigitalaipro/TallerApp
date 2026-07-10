# TallerApp 🛠️

Sistema de Gestión Integral para Taller de Reparación de Aires Acondicionados, Neveras y Electrodomésticos.

## Características

- **Dashboard** — Métricas clave en tiempo real con gráficos
- **CRM** — Gestión de clientes con historial de interacciones
- **Inventario** — Control de repuestos con movimientos y alertas de stock bajo
- **Órdenes de Trabajo** — Ciclo completo: diagnóstico → reparación → entrega
- **Presupuestos** — Creación profesional con cálculo automático de IVA
- **Facturación** — Facturas con registro de pagos y control de saldos
- **Licitaciones** — Seguimiento de licitaciones públicas/privadas
- **Usuarios** — Múltiples roles (Admin, Técnico, Recepcionista, Contador)
- **Reportes** — Análisis de reparaciones, rendimiento y rentabilidad

## Tecnologías

- Python + FastAPI
- SQLAlchemy + SQLite
- Jinja2 + Tailwind CSS + Alpine.js + Chart.js
- JWT Authentication

## Instalación

```bash
git clone https://github.com/tu-usuario/tallerapp.git
cd tallerapp
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Login por defecto

- **Usuario:** admin
- **Contraseña:** admin123
