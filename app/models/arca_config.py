from sqlalchemy import Column, Integer, String, Boolean, Date
from app.database import Base


class ArcaConfig(Base):
    __tablename__ = "arca_config"

    id = Column(Integer, primary_key=True, index=True)
    cuit = Column(String, nullable=False)                       # CUIT del emisor (sin guiones)
    razon_social = Column(String, nullable=False)               # Razón social
    condicion_iva = Column(Integer, default=1)                  # 1=Resp.Inscripto, 6=Monotributo
    punto_vta = Column(Integer, nullable=False)                 # Punto de venta habilitado
    domicilio_comercial = Column(String, nullable=True)         # Domicilio fiscal
    inicio_actividades = Column(Date, nullable=True)            # Fecha inicio actividades
    cert_path = Column(String, nullable=True)                   # Ruta al certificado .crt
    key_path = Column(String, nullable=True)                    # Ruta a la clave privada .key
    environment = Column(String, default="homologacion")        # "homologacion" / "produccion"
    is_active = Column(Boolean, default=True)
