from sqlalchemy import Column, Integer, String, Boolean, JSON, DateTime, func
from app.database import Base


class RoleConfig(Base):
    __tablename__ = "role_configs"

    id = Column(Integer, primary_key=True, index=True)
    role_name = Column(String, unique=True, nullable=False, index=True)  # admin, user, empleado, vendedor
    display_name = Column(String, nullable=False)  # Administrador, Usuario, etc.
    description = Column(String, nullable=True)

    # JSON array of allowed page paths: ["/", "/clients", "/billing", ...]
    allowed_pages = Column(JSON, nullable=False, default=[])

    # If true, users with ONLY this role see only their own data
    own_data_only = Column(Boolean, default=False)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
