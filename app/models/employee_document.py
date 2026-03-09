"""Employee document model for digital dossier (legajo digital)."""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, func
from app.database import Base


class EmployeeDocument(Base):
    __tablename__ = "employee_documents"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    document_type = Column(String(50), nullable=False)  # dni, cuil, contrato, titulo, monotributo, cert_domicilio, recibo_sueldo, otro
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=True)  # bytes
    mime_type = Column(String(100), nullable=True)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
