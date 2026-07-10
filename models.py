"""SQLAlchemy models for TallerApp."""
from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Float, Text, DateTime, Date, Boolean,
    ForeignKey, Enum, JSON, DECIMAL
)
from sqlalchemy.orm import relationship
from database import Base
import enum


# ─── Enums ──────────────────────────────────────────────────────────────

class EquipmentType(str, enum.Enum):
    AC = "Aire Acondicionado"
    FRIDGE = "Nevera"
    COOLER = "Cava"
    WASHER = "Lavadora"
    DRYER = "Secadora"
    OVEN = "Horno"
    STOVE = "Cocina"
    OTHER = "Otro"

class EquipmentStatus(str, enum.Enum):
    PENDING = "Pendiente"
    IN_REPAIR = "En Reparación"
    WAITING_PARTS = "Esperando Repuestos"
    TESTING = "Pruebas"
    REPAIRED = "Reparado"
    DELIVERED = "Entregado"

class WorkOrderStatus(str, enum.Enum):
    DIAGNOSIS = "Diagnóstico"
    WAITING_PARTS = "Esperando Repuestos"
    IN_REPAIR = "En Reparación"
    TESTING = "Pruebas"
    READY = "Listo para Entregar"
    DELIVERED = "Entregado"
    CANCELLED = "Cancelado"

class EstimateStatus(str, enum.Enum):
    DRAFT = "Borrador"
    SENT = "Enviado"
    APPROVED = "Aprobado"
    REJECTED = "Rechazado"
    CONVERTED = "Convertido a OT"

class InvoiceStatus(str, enum.Enum):
    PENDING = "Pendiente"
    PAID = "Pagado"
    PARTIAL = "Pago Parcial"
    OVERDUE = "Vencido"
    CANCELLED = "Anulado"

class BiddingStatus(str, enum.Enum):
    IN_PROGRESS = "En Proceso"
    WON = "Ganada"
    LOST = "Perdida"
    CANCELLED = "Cancelada"

class UserRole(str, enum.Enum):
    ADMIN = "Administrador"
    TECHNICIAN = "Técnico"
    RECEPTIONIST = "Recepcionista"
    ACCOUNTANT = "Contador"

class MovementType(str, enum.Enum):
    IN = "Entrada"
    OUT = "Salida"
    ADJUSTMENT = "Ajuste"

class PartCategory(str, enum.Enum):
    ELECTRONICS = "Electrónica"
    REFRIGERATION = "Refrigeración"
    MECHANICAL = "Mecánica"
    ELECTRICAL = "Eléctrica"
    GAS = "Gas/Refrigerante"
    TOOLS = "Herramientas"
    OTHER = "Otros"


# ─── Users & Auth ──────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(80), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=True)
    full_name = Column(String(150), nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.TECHNICIAN)
    phone = Column(String(20), nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    work_orders = relationship("WorkOrder", back_populates="technician")


# ─── Clients (CRM) ──────────────────────────────────────────────────────

class Client(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    phone = Column(String(20), nullable=True, index=True)
    email = Column(String(120), nullable=True)
    address = Column(Text, nullable=True)
    contact_preference = Column(String(20), default="WhatsApp")  # WhatsApp, Email, Llamada
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    equipment = relationship("Equipment", back_populates="client")
    work_orders = relationship("WorkOrder", back_populates="client")
    estimates = relationship("Estimate", back_populates="client")
    invoices = relationship("Invoice", back_populates="client")
    interactions = relationship("ClientInteraction", back_populates="client", order_by="ClientInteraction.created_at.desc()")
    documents = relationship("ClientDocument", back_populates="client")


class ClientInteraction(Base):
    __tablename__ = "client_interactions"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    interaction_type = Column(String(30))  # llamada, mensaje, visita, correo
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    client = relationship("Client", back_populates="interactions")


class ClientDocument(Base):
    __tablename__ = "client_documents"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    doc_type = Column(String(30))  # factura, garantia, foto
    filename = Column(String(255))
    filepath = Column(String(500))
    description = Column(Text, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    client = relationship("Client", back_populates="documents")


# ─── Equipment (Equipos Recibidos) ──────────────────────────────────────

class Equipment(Base):
    __tablename__ = "equipment"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    equipment_type = Column(Enum(EquipmentType), nullable=False)
    brand = Column(String(100), nullable=True)
    model = Column(String(100), nullable=True)
    serial_number = Column(String(100), nullable=True, index=True)
    year = Column(Integer, nullable=True)
    initial_diagnosis = Column(Text, nullable=True)
    photos = Column(JSON, nullable=True)  # Lista de rutas de fotos
    status = Column(Enum(EquipmentStatus), default=EquipmentStatus.PENDING)
    warranty_until = Column(Date, nullable=True)
    special_tracking = Column(Boolean, default=False)
    entry_date = Column(DateTime, default=datetime.utcnow)
    estimated_delivery = Column(Date, nullable=True)
    delivery_date = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    client = relationship("Client", back_populates="equipment")
    work_orders = relationship("WorkOrder", back_populates="equipment")


# ─── Inventory (Repuestos) ──────────────────────────────────────────────

class Part(Base):
    __tablename__ = "parts"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(Enum(PartCategory), default=PartCategory.OTHER)
    stock = Column(Integer, default=0)
    min_stock = Column(Integer, default=5)
    location = Column(String(100), nullable=True)
    cost_price = Column(DECIMAL(12, 2), default=0)
    sale_price = Column(DECIMAL(12, 2), default=0)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)
    barcode = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    supplier = relationship("Supplier", back_populates="parts")
    movements = relationship("PartMovement", back_populates="part", order_by="PartMovement.created_at.desc()")


class PartMovement(Base):
    __tablename__ = "part_movements"
    id = Column(Integer, primary_key=True, index=True)
    part_id = Column(Integer, ForeignKey("parts.id"), nullable=False)
    movement_type = Column(Enum(MovementType), nullable=False)
    quantity = Column(Integer, nullable=False)
    reference = Column(String(100), nullable=True)  # Factura, OT, etc.
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    part = relationship("Part", back_populates="movements")


class Supplier(Base):
    __tablename__ = "suppliers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    contact = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    email = Column(String(120), nullable=True)
    delivery_time = Column(String(50), nullable=True)  # "2-3 días"
    notes = Column(Text, nullable=True)

    parts = relationship("Part", back_populates="supplier")


# ─── Work Order Parts (many-to-many con cantidad) ──────────────────────

class WorkOrderPart(Base):
    __tablename__ = "work_order_parts"
    id = Column(Integer, primary_key=True)
    work_order_id = Column(Integer, ForeignKey("work_orders.id"), nullable=False)
    part_id = Column(Integer, ForeignKey("parts.id"), nullable=False)
    quantity = Column(Integer, default=1)
    unit_cost = Column(DECIMAL(12, 2), default=0)
    unit_price = Column(DECIMAL(12, 2), default=0)

    work_order = relationship("WorkOrder", back_populates="parts")
    part = relationship("Part")


# ─── Work Orders ────────────────────────────────────────────────────────

class WorkOrder(Base):
    __tablename__ = "work_orders"
    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(20), unique=True, nullable=False, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    equipment_id = Column(Integer, ForeignKey("equipment.id"), nullable=False)
    technician_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    estimate_id = Column(Integer, ForeignKey("estimates.id"), nullable=True)

    status = Column(Enum(WorkOrderStatus), default=WorkOrderStatus.DIAGNOSIS)
    diagnosis = Column(Text, nullable=True)
    resolution = Column(Text, nullable=True)
    labor_hours = Column(Float, default=0)
    labor_rate = Column(DECIMAL(12, 2), default=0)
    total_parts_cost = Column(DECIMAL(12, 2), default=0)
    total_labor = Column(DECIMAL(12, 2), default=0)
    total_amount = Column(DECIMAL(12, 2), default=0)

    start_date = Column(DateTime, nullable=True)
    estimated_end_date = Column(Date, nullable=True)
    completed_date = Column(DateTime, nullable=True)

    internal_notes = Column(Text, nullable=True)
    quality_checklist = Column(JSON, nullable=True)
    incidents = Column(JSON, nullable=True)  # [{desc, date, resolved}]

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    client = relationship("Client", back_populates="work_orders")
    equipment = relationship("Equipment", back_populates="work_orders")
    technician = relationship("User", back_populates="work_orders")
    parts = relationship("WorkOrderPart", back_populates="work_order")
    estimate = relationship("Estimate", back_populates="work_orders")


# ─── Estimates (Presupuestos) ──────────────────────────────────────────

class EstimateItem(Base):
    __tablename__ = "estimate_items"
    id = Column(Integer, primary_key=True)
    estimate_id = Column(Integer, ForeignKey("estimates.id"), nullable=False)
    item_type = Column(String(20))  # part, labor
    description = Column(String(300), nullable=False)
    quantity = Column(Integer, default=1)
    unit_price = Column(DECIMAL(12, 2), default=0)
    total = Column(DECIMAL(12, 2), default=0)
    part_id = Column(Integer, ForeignKey("parts.id"), nullable=True)

    estimate = relationship("Estimate", back_populates="items")
    part = relationship("Part")


class Estimate(Base):
    __tablename__ = "estimates"
    id = Column(Integer, primary_key=True, index=True)
    estimate_number = Column(String(20), unique=True, nullable=False, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    equipment_id = Column(Integer, ForeignKey("equipment.id"), nullable=True)

    status = Column(Enum(EstimateStatus), default=EstimateStatus.DRAFT)
    subtotal = Column(DECIMAL(12, 2), default=0)
    tax_rate = Column(Float, default=16.0)  # IVA %
    tax_amount = Column(DECIMAL(12, 2), default=0)
    discount = Column(DECIMAL(12, 2), default=0)
    discount_type = Column(String(10), default="percent")  # percent, fixed
    total = Column(DECIMAL(12, 2), default=0)
    valid_until = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    terms = Column(Text, nullable=True)
    pdf_path = Column(String(500), nullable=True)
    sent_at = Column(DateTime, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    client = relationship("Client", back_populates="estimates")
    items = relationship("EstimateItem", back_populates="estimate", cascade="all, delete-orphan")
    work_orders = relationship("WorkOrder", back_populates="estimate")


# ─── Invoices ───────────────────────────────────────────────────────────

class InvoiceItem(Base):
    __tablename__ = "invoice_items"
    id = Column(Integer, primary_key=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    description = Column(String(300), nullable=False)
    quantity = Column(Integer, default=1)
    unit_price = Column(DECIMAL(12, 2), default=0)
    total = Column(DECIMAL(12, 2), default=0)

    invoice = relationship("Invoice", back_populates="items")


class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String(20), unique=True, nullable=False, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    work_order_id = Column(Integer, ForeignKey("work_orders.id"), nullable=True)

    status = Column(Enum(InvoiceStatus), default=InvoiceStatus.PENDING)
    subtotal = Column(DECIMAL(12, 2), default=0)
    tax_rate = Column(Float, default=16.0)
    tax_amount = Column(DECIMAL(12, 2), default=0)
    total = Column(DECIMAL(12, 2), default=0)
    amount_paid = Column(DECIMAL(12, 2), default=0)
    notes = Column(Text, nullable=True)
    pdf_path = Column(String(500), nullable=True)
    due_date = Column(Date, nullable=True)
    paid_at = Column(DateTime, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    client = relationship("Client", back_populates="invoices")
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")


# ─── Bidding / Licitaciones ────────────────────────────────────────────

class Bid(Base):
    __tablename__ = "bids"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(300), nullable=False)
    institution = Column(String(200), nullable=True)
    reference = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    requirements_file = Column(String(500), nullable=True)  # PDF/Word path
    extracted_data = Column(JSON, nullable=True)

    estimated_value = Column(DECIMAL(12, 2), nullable=True)
    proposed_value = Column(DECIMAL(12, 2), nullable=True)

    status = Column(Enum(BiddingStatus), default=BiddingStatus.IN_PROGRESS)
    submission_date = Column(Date, nullable=True)
    deadline = Column(Date, nullable=True)
    result_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ─── Shop Settings ───────────────────────────────────────────────────────

class ShopSettings(Base):
    __tablename__ = "shop_settings"
    id = Column(Integer, primary_key=True)
    shop_name = Column(String(200), default="Mi Taller")
    shop_logo = Column(String(500), nullable=True)
    address = Column(Text, nullable=True)
    phone = Column(String(20), nullable=True)
    email = Column(String(120), nullable=True)
    website = Column(String(200), nullable=True)
    social_media = Column(JSON, nullable=True)
    tax_rate = Column(Float, default=16.0)
    currency = Column(String(10), default="Bs")
    labor_rate = Column(DECIMAL(12, 2), default=0)
    invoice_prefix = Column(String(10), default="FAC-")
    estimate_prefix = Column(String(10), default="PRE-")
    order_prefix = Column(String(10), default="OT-")
    next_invoice = Column(Integer, default=1)
    next_estimate = Column(Integer, default=1)
    next_order = Column(Integer, default=1)
    whatsapp_number = Column(String(20), nullable=True)
    whatsapp_api_key = Column(String(255), nullable=True)
    email_smtp = Column(JSON, nullable=True)
    backup_enabled = Column(Boolean, default=True)
    backup_interval = Column(String(20), default="daily")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
