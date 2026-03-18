from sqlalchemy import Column, Integer, BigInteger, String, Numeric, DateTime, Date, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base

class InvoiceStatus(Base):
    __tablename__ = "invoice_statuses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(String)
    color_code = Column(String, default="#3B82F6")

    invoices = relationship("Invoice", back_populates="status")

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String, unique=True, index=True, nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String, default="ARS", nullable=False)
    exchange_rate = Column(Numeric(12, 6), nullable=True, default=1)  # Rate to ARS (e.g. 1 USD = 1050 ARS)
    amount_ars = Column(Numeric(15, 2), nullable=True)                # Amount converted to ARS
    file_url = Column(String)  # For attachments
    type = Column(String, default="created")  # "created" or "received"
    issue_date = Column(DateTime)
    due_date = Column(DateTime)
    payment_date = Column(DateTime, nullable=True)
    notes = Column(Text)

    # --- ARCA (ex AFIP) Electronic Invoicing Fields ---
    arca_cbte_tipo = Column(Integer, nullable=True)          # Voucher type (1=Factura A, 6=B, 11=C)
    arca_punto_vta = Column(Integer, nullable=True)          # Point of sale
    arca_cbte_nro = Column(BigInteger, nullable=True)        # Voucher number assigned by ARCA
    arca_concepto = Column(Integer, nullable=True)           # 1=Products, 2=Services, 3=Both
    arca_tipo_doc_receptor = Column(Integer, nullable=True)  # Receptor doc type (80=CUIT, 96=DNI)
    arca_nro_doc_receptor = Column(String, nullable=True)    # Receptor document number
    arca_condicion_iva_receptor = Column(Integer, nullable=True)  # Receptor IVA condition (RG5616)
    cae = Column(String(14), nullable=True)                  # Electronic Authorization Code
    cae_vto = Column(Date, nullable=True)                    # CAE expiration date
    arca_result = Column(String(1), nullable=True)           # A=Approved, R=Rejected, P=Partial
    arca_obs = Column(Text, nullable=True)                   # ARCA observations/errors
    imp_neto = Column(Numeric(12, 2), nullable=True)         # Net taxable amount
    imp_iva = Column(Numeric(12, 2), nullable=True)          # Total IVA amount
    imp_tot_conc = Column(Numeric(12, 2), nullable=True)     # Non-taxable amount
    imp_op_ex = Column(Numeric(12, 2), nullable=True)        # Exempt amount
    imp_trib = Column(Numeric(12, 2), nullable=True)         # Other taxes
    mon_id = Column(String(3), nullable=True)                # ARCA currency code (PES, DOL, 060)
    mon_cotiz = Column(Numeric(12, 6), nullable=True)        # Currency exchange rate
    # Associated invoice (for NC/ND)
    cbte_asoc_tipo = Column(Integer, nullable=True)          # Type of associated invoice
    cbte_asoc_pto_vta = Column(Integer, nullable=True)       # PtoVta of associated invoice
    cbte_asoc_nro = Column(BigInteger, nullable=True)        # Number of associated invoice
    cbte_asoc_cuit = Column(String, nullable=True)           # CUIT of associated invoice

    status_id = Column(Integer, ForeignKey("invoice_statuses.id", ondelete="SET NULL"), nullable=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="SET NULL"), nullable=True)
    provider_id = Column(Integer, ForeignKey("providers.id", ondelete="SET NULL"), nullable=True)
    quote_id = Column(Integer, ForeignKey("quotes.id", ondelete="SET NULL"), nullable=True)
    sales_order_id = Column(Integer, ForeignKey("sales_orders.id", ondelete="SET NULL"), nullable=True)
    seller_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    status = relationship("InvoiceStatus", back_populates="invoices")
    client = relationship("Client", back_populates="invoices")
    provider = relationship("Provider", back_populates="invoices")
    quote = relationship("Quote")
    sales_order = relationship("SalesOrder", backref="invoices")
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")
    iva_items = relationship("InvoiceIvaItem", back_populates="invoice", cascade="all, delete-orphan")
