"""
ARCA (ex AFIP) Electronic Invoicing Service
Uses zeep (SOAP) + openssl for WSAA authentication and WSFEv1 invoicing.
Compatible with Python 3.10+
"""
import os
import logging
import subprocess
import base64
import ssl
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional, Dict, Any, List

import requests
from sqlalchemy.orm import Session
from zeep import Client as ZeepClient
from zeep.transports import Transport

from app.models.arca_config import ArcaConfig
from app.models.invoice import Invoice
from app.models.invoice_iva_item import InvoiceIvaItem
from app.schemas.arca import (
    ArcaConfigCreate, ArcaConfigUpdate,
    ArcaEmitRequest, ArcaEmitResponse,
)

logger = logging.getLogger(__name__)

# ARCA Web Service URLs
WSAA_WSDL = {
    "homologacion": "https://wsaahomo.afip.gov.ar/ws/services/LoginCms?wsdl",
    "produccion": "https://wsaa.afip.gov.ar/ws/services/LoginCms?wsdl",
}

WSFEV1_WSDL = {
    "homologacion": "https://wswhomo.afip.gov.ar/wsfev1/service.asmx?WSDL",
    "produccion": "https://servicios1.afip.gov.ar/wsfev1/service.asmx?WSDL",
}

WS_PADRON_WSDL = {
    "homologacion": "https://awshomo.afip.gov.ar/sr-padron/webservices/personaServiceA13?WSDL",
    "produccion": "https://aws.afip.gov.ar/sr-padron/webservices/personaServiceA13?WSDL",
}

# IVA rate descriptions
IVA_TYPES = {
    3: {"desc": "0%", "rate": Decimal("0")},
    4: {"desc": "10.5%", "rate": Decimal("0.105")},
    5: {"desc": "21%", "rate": Decimal("0.21")},
    6: {"desc": "27%", "rate": Decimal("0.27")},
    8: {"desc": "5%", "rate": Decimal("0.05")},
    9: {"desc": "2.5%", "rate": Decimal("0.025")},
}

# Voucher type descriptions
CBTE_TYPES = {
    1: "Factura A",
    2: "Nota de Débito A",
    3: "Nota de Crédito A",
    6: "Factura B",
    7: "Nota de Débito B",
    8: "Nota de Crédito B",
    11: "Factura C",
    12: "Nota de Débito C",
    13: "Nota de Crédito C",
    19: "Factura E (Exportación)",
    51: "Factura M",
}


class _SSLAdapter(requests.adapters.HTTPAdapter):
    """HTTPAdapter with lowered SSL security level (fixes DH_KEY_TOO_SMALL for AFIP)"""
    def init_poolmanager(self, *args, **kwargs):
        ctx = ssl.create_default_context()
        ctx.set_ciphers('DEFAULT:@SECLEVEL=1')
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        kwargs['ssl_context'] = ctx
        return super().init_poolmanager(*args, **kwargs)


class ArcaService:
    """Service for interacting with ARCA (ex AFIP) Web Services using zeep"""

    def __init__(self):
        self._token = None
        self._sign = None
        self._token_expiry = None
        # Separate token for padron service
        self._padron_token = None
        self._padron_sign = None
        self._padron_token_expiry = None
        # Create a requests session with relaxed SSL for AFIP servers (DH_KEY_TOO_SMALL fix)
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        session = requests.Session()
        session.verify = False
        # Mount a custom adapter that sets SSL security level 1
        adapter = _SSLAdapter()
        session.mount('https://', adapter)
        self._transport = Transport(session=session, timeout=30)

    # ─── Configuration CRUD ───────────────────────────────────

    def get_config(self, db: Session) -> Optional[ArcaConfig]:
        return db.query(ArcaConfig).filter(ArcaConfig.is_active == True).first()

    def create_config(self, db: Session, config_in: ArcaConfigCreate) -> ArcaConfig:
        db.query(ArcaConfig).update({"is_active": False})
        config = ArcaConfig(**config_in.model_dump())
        db.add(config)
        db.commit()
        db.refresh(config)
        return config

    def update_config(self, db: Session, config_id: int, config_in: ArcaConfigUpdate) -> ArcaConfig:
        config = db.query(ArcaConfig).filter(ArcaConfig.id == config_id).first()
        if not config:
            raise ValueError("ARCA configuration not found")
        update_data = config_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(config, key, value)
        db.commit()
        db.refresh(config)
        return config

    # ─── WSAA Authentication (using openssl + zeep) ───────────

    def _create_tra(self, service: str = "wsfe", ttl: int = 2400) -> str:
        """Create a TRA (Ticket de Requerimiento de Acceso) XML"""
        now = datetime.now(timezone.utc) - timedelta(hours=3)  # GMT-3
        unique_id = int(now.timestamp())
        generation = (now - timedelta(seconds=ttl)).strftime("%Y-%m-%dT%H:%M:%S")
        expiration = (now + timedelta(seconds=ttl)).strftime("%Y-%m-%dT%H:%M:%S")

        tra_xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<loginTicketRequest version="1.0">'
            '<header>'
            f'<uniqueId>{unique_id}</uniqueId>'
            f'<generationTime>{generation}</generationTime>'
            f'<expirationTime>{expiration}</expirationTime>'
            '</header>'
            f'<service>{service}</service>'
            '</loginTicketRequest>'
        )
        return tra_xml

    def _sign_tra(self, tra_xml: str, cert_path: str, key_path: str) -> str:
        """Sign TRA using openssl smime and return base64 CMS"""
        result = subprocess.run(
            [
                "openssl", "smime", "-sign",
                "-signer", cert_path,
                "-inkey", key_path,
                "-outform", "DER",
                "-nodetach",
            ],
            input=tra_xml.encode("utf-8"),
            capture_output=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"OpenSSL signing failed: {result.stderr.decode()}")

        return base64.b64encode(result.stdout).decode("utf-8")

    def _authenticate(self, config: ArcaConfig) -> bool:
        """Authenticate with WSAA to get Token + Sign"""
        try:
            cert_path = config.cert_path or "arca/certs/certificado.crt"
            key_path = config.key_path or "arca/certs/clave_privada.key"

            if not os.path.exists(cert_path):
                raise FileNotFoundError(f"Certificate not found: {cert_path}")
            if not os.path.exists(key_path):
                raise FileNotFoundError(f"Private key not found: {key_path}")

            # 1. Create TRA
            tra_xml = self._create_tra(service="wsfe")

            # 2. Sign with openssl
            cms = self._sign_tra(tra_xml, cert_path, key_path)

            # 3. Call WSAA via zeep
            wsdl_url = WSAA_WSDL.get(config.environment, WSAA_WSDL["homologacion"])
            wsaa_client = ZeepClient(wsdl=wsdl_url, transport=self._transport)
            ta_xml = wsaa_client.service.loginCms(in0=cms)

            # 4. Parse response to extract token + sign
            root = ET.fromstring(ta_xml)
            self._token = root.find('.//token').text
            self._sign = root.find('.//sign').text
            expiry_text = root.find('.//expirationTime').text
            self._token_expiry = datetime.fromisoformat(expiry_text.replace("Z", "+00:00"))

            logger.info(f"ARCA WSAA auth OK ({config.environment}), expires: {expiry_text}")
            return True

        except Exception as e:
            logger.error(f"ARCA WSAA auth error: {str(e)}")
            raise

    def _ensure_auth(self, config: ArcaConfig):
        """Ensure we have a valid token, re-authenticate if needed"""
        now = datetime.now(timezone.utc)
        if self._token and self._token_expiry and now < self._token_expiry:
            return  # Still valid
        self._authenticate(config)

    def _get_wsfev1_client(self, config: ArcaConfig) -> ZeepClient:
        """Get an authenticated WSFEv1 zeep client"""
        self._ensure_auth(config)
        wsdl_url = WSFEV1_WSDL.get(config.environment, WSFEV1_WSDL["homologacion"])
        return ZeepClient(wsdl=wsdl_url, transport=self._transport)

    def _auth_dict(self, config: ArcaConfig) -> dict:
        """Build the Auth dict required by WSFEv1 methods"""
        return {
            "Token": self._token,
            "Sign": self._sign,
            "Cuit": int(config.cuit),
        }

    # ─── WSFEv1 Operations ────────────────────────────────────

    def test_connection(self, db: Session) -> Dict[str, Any]:
        config = self.get_config(db)
        if not config:
            return {
                "success": False,
                "message": "No ARCA configuration found. Configure ARCA in Settings first.",
                "environment": "unknown",
                "server_time": None,
            }
        try:
            client = self._get_wsfev1_client(config)
            result = client.service.FEDummy()
            return {
                "success": True,
                "message": (
                    f"Connection OK! AppServer: {result.AppServer}, "
                    f"DbServer: {result.DbServer}, AuthServer: {result.AuthServer}"
                ),
                "environment": config.environment,
                "server_time": datetime.now().isoformat(),
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Connection failed: {str(e)}",
                "environment": config.environment,
                "server_time": None,
            }

    def get_last_voucher(self, db: Session, punto_vta: int, cbte_tipo: int) -> Dict[str, int]:
        config = self.get_config(db)
        if not config:
            raise ValueError("No ARCA configuration found")

        arca_nro = 0
        try:
            client = self._get_wsfev1_client(config)
            result = client.service.FECompUltimoAutorizado(
                Auth=self._auth_dict(config),
                PtoVta=punto_vta,
                CbteTipo=cbte_tipo,
            )
            arca_nro = result.CbteNro or 0
        except Exception as e:
            logger.warning(f"ARCA FECompUltimoAutorizado failed: {e}")

        # Fallback: if ARCA returns 0, check local CRM invoices for max number
        if arca_nro == 0:
            from sqlalchemy import func
            # Check arca_cbte_nro field
            local_max = db.query(func.max(Invoice.arca_cbte_nro)).filter(
                Invoice.arca_punto_vta == punto_vta,
                Invoice.arca_cbte_tipo == cbte_tipo,
            ).scalar() or 0

            # Also check invoice_number format "XXXXX-XXXXXXXX"
            pv_prefix = f"{punto_vta:05d}-"
            invoices_with_prefix = db.query(Invoice.invoice_number).filter(
                Invoice.invoice_number.like(f"{pv_prefix}%")
            ).all()
            for (inv_num,) in invoices_with_prefix:
                try:
                    nro_part = int(inv_num.split("-")[1])
                    if nro_part > local_max:
                        local_max = nro_part
                except (ValueError, IndexError):
                    pass

            if local_max > arca_nro:
                logger.info(f"Using local CRM max voucher {local_max} (ARCA returned {arca_nro})")
                arca_nro = local_max

        return {
            "cbte_nro": arca_nro,
            "cbte_tipo": cbte_tipo,
            "punto_vta": punto_vta,
        }

    def get_voucher_types(self, db: Session) -> List[Dict]:
        config = self.get_config(db)
        if not config:
            return [{"id": k, "desc": v} for k, v in CBTE_TYPES.items()]
        try:
            client = self._get_wsfev1_client(config)
            result = client.service.FEParamGetTiposCbte(Auth=self._auth_dict(config))
            if result.ResultGet:
                return [{"id": t.Id, "desc": t.Desc} for t in result.ResultGet.CbteTipo]
        except Exception:
            pass
        return [{"id": k, "desc": v} for k, v in CBTE_TYPES.items()]

    def get_iva_types(self, db: Session) -> List[Dict]:
        return [{"id": k, "desc": v["desc"]} for k, v in IVA_TYPES.items()]

    def get_sale_points(self, db: Session) -> List[Dict]:
        config = self.get_config(db)
        if not config:
            raise ValueError("No ARCA configuration found")
        try:
            client = self._get_wsfev1_client(config)
            result = client.service.FEParamGetPtosVenta(Auth=self._auth_dict(config))
            if result.ResultGet:
                return [
                    {
                        "nro": p.Nro,
                        "emision_tipo": p.EmisionTipo,
                        "bloqueado": p.Bloqueado,
                        "fecha_baja": str(p.FchBaja) if p.FchBaja else None,
                    }
                    for p in result.ResultGet.PtoVenta
                ]
        except Exception:
            pass
        return [{"nro": config.punto_vta, "emision_tipo": "CAE", "bloqueado": "N", "fecha_baja": None}]

    def get_currency_rate(self, db: Session, mon_id: str) -> Dict:
        config = self.get_config(db)
        if not config:
            raise ValueError("No ARCA configuration found")
        client = self._get_wsfev1_client(config)
        result = client.service.FEParamGetCotizacion(
            Auth=self._auth_dict(config), MonId=mon_id
        )
        return {
            "mon_id": mon_id,
            "mon_cotiz": float(result.ResultGet.MonCotiz) if result.ResultGet else 1.0,
            "fecha": datetime.now().strftime("%Y%m%d"),
        }

    def consult_voucher(self, db: Session, punto_vta: int, cbte_tipo: int, cbte_nro: int) -> Dict:
        config = self.get_config(db)
        if not config:
            raise ValueError("No ARCA configuration found")
        client = self._get_wsfev1_client(config)
        result = client.service.FECompConsultar(
            Auth=self._auth_dict(config),
            FeCompConsReq={"CbteTipo": cbte_tipo, "CbteNro": cbte_nro, "PtoVta": punto_vta},
        )
        r = result.ResultGet
        return {
            "cae": r.CodAutorizacion if r else None,
            "cae_vto": r.FchVto if r else None,
            "resultado": r.Resultado if r else None,
            "fecha_cbte": r.CbteFch if r else None,
            "imp_total": float(r.ImpTotal) if r else 0,
            "imp_neto": float(r.ImpNeto) if r else 0,
            "imp_iva": float(r.ImpIVA) if r else 0,
        }

    # ─── Emit Invoice ─────────────────────────────────────────

    def emit_invoice(self, db: Session, request: ArcaEmitRequest) -> ArcaEmitResponse:
        config = self.get_config(db)
        if not config:
            return ArcaEmitResponse(
                success=False, invoice_id=request.invoice_id,
                errores="No ARCA configuration found.",
            )

        invoice = db.query(Invoice).filter(Invoice.id == request.invoice_id).first()
        if not invoice:
            return ArcaEmitResponse(
                success=False, invoice_id=request.invoice_id,
                errores=f"Invoice ID {request.invoice_id} not found.",
            )
        if invoice.cae:
            return ArcaEmitResponse(
                success=False, invoice_id=request.invoice_id,
                errores=f"Invoice already has CAE: {invoice.cae}",
            )

        try:
            client = self._get_wsfev1_client(config)

            # Get next voucher number
            last = client.service.FECompUltimoAutorizado(
                Auth=self._auth_dict(config),
                PtoVta=config.punto_vta,
                CbteTipo=request.cbte_tipo,
            )
            cbte_nro = (last.CbteNro or 0) + 1

            fecha_cbte = request.fecha_cbte or datetime.now().strftime("%Y%m%d")
            fecha_venc_pago = request.fecha_venc_pago or fecha_cbte

            # Build IVA array
            iva_arr = []
            for iva in request.iva_items:
                iva_arr.append({
                    "Id": iva.iva_id,
                    "BaseImp": float(iva.base_imp),
                    "Importe": float(iva.importe),
                })

            # Build detail
            detalle = {
                "Concepto": request.concepto,
                "DocTipo": request.tipo_doc,
                "DocNro": int(request.nro_doc.replace("-", "")),
                "CbteDesde": cbte_nro,
                "CbteHasta": cbte_nro,
                "CbteFch": fecha_cbte,
                "ImpTotal": float(request.imp_total),
                "ImpTotConc": float(request.imp_tot_conc),
                "ImpNeto": float(request.imp_neto),
                "ImpOpEx": float(request.imp_op_ex),
                "ImpTrib": float(request.imp_trib),
                "ImpIVA": float(request.imp_iva),
                "MonId": request.mon_id,
                "MonCotiz": float(request.mon_cotiz),
                "CondicionIVAReceptorId": request.condicion_iva_receptor,
            }

            # Service dates + FchVtoPago (required ONLY for concepto 2 or 3)
            if request.concepto in (2, 3):
                detalle["FchVtoPago"] = fecha_venc_pago
                if request.fecha_serv_desde:
                    detalle["FchServDesde"] = request.fecha_serv_desde
                if request.fecha_serv_hasta:
                    detalle["FchServHasta"] = request.fecha_serv_hasta

            # Add IVA items
            if iva_arr:
                detalle["Iva"] = {"AlicIva": iva_arr}

            # Add associated invoice for credit/debit notes (NC/ND)
            if request.cbte_tipo in (3, 8, 13, 2, 7, 12):
                # CbtesAsoc is MANDATORY for NC/ND per ARCA regulations
                if not request.cbte_asoc_tipo or not request.cbte_asoc_nro:
                    return ArcaEmitResponse(
                        success=False, invoice_id=request.invoice_id,
                        errores="Las Notas de Crédito/Débito requieren un comprobante asociado (CbtesAsoc). "
                                "Seleccione la factura original a la que se asocia esta NC/ND.",
                    )
                detalle["CbtesAsoc"] = {
                    "CbteAsoc": [{
                        "Tipo": request.cbte_asoc_tipo,
                        "PtoVta": request.cbte_asoc_pto_vta or config.punto_vta,
                        "Nro": request.cbte_asoc_nro,
                        "Cuit": request.cbte_asoc_cuit or config.cuit.replace("-", ""),
                        "CbteFch": request.cbte_asoc_fecha or fecha_cbte,
                    }]
                }

            # Build request — FeCAEReq wraps FeCabReq + FeDetReq
            fe_cae_req = {
                "FeCabReq": {
                    "CantReg": 1,
                    "PtoVta": config.punto_vta,
                    "CbteTipo": request.cbte_tipo,
                },
                "FeDetReq": {
                    "FECAEDetRequest": [detalle],
                },
            }

            # Call ARCA
            result = client.service.FECAESolicitar(
                Auth=self._auth_dict(config),
                FeCAEReq=fe_cae_req,
            )

            # Parse response
            det = result.FeDetResp.FECAEDetResponse[0]
            cae = det.CAE
            cae_vto = det.CAEFchVto
            resultado = det.Resultado  # A=Approved, R=Rejected

            obs_list = []
            if det.Observaciones and det.Observaciones.Obs:
                for o in det.Observaciones.Obs:
                    obs_list.append(f"[{o.Code}] {o.Msg}")
            obs_str = "; ".join(obs_list) if obs_list else None

            err_list = []
            if result.Errors and result.Errors.Err:
                for e in result.Errors.Err:
                    err_list.append(f"[{e.Code}] {e.Msg}")
            err_str = "; ".join(err_list) if err_list else None

            # Parse CAE expiry date
            cae_vto_date = None
            if cae_vto:
                try:
                    cae_vto_date = datetime.strptime(str(cae_vto), "%Y%m%d").date()
                except ValueError:
                    pass

            # Update invoice in database
            invoice.arca_cbte_tipo = request.cbte_tipo
            invoice.arca_punto_vta = config.punto_vta
            invoice.arca_cbte_nro = cbte_nro
            invoice.arca_concepto = request.concepto
            invoice.arca_tipo_doc_receptor = request.tipo_doc
            invoice.arca_nro_doc_receptor = request.nro_doc
            invoice.arca_condicion_iva_receptor = request.condicion_iva_receptor
            invoice.cae = cae if resultado == "A" else None
            invoice.cae_vto = cae_vto_date
            invoice.arca_result = resultado
            invoice.arca_obs = obs_str or err_str
            invoice.imp_neto = request.imp_neto
            invoice.imp_iva = request.imp_iva
            invoice.imp_tot_conc = request.imp_tot_conc
            invoice.imp_op_ex = request.imp_op_ex
            invoice.imp_trib = request.imp_trib
            invoice.mon_id = request.mon_id
            invoice.mon_cotiz = request.mon_cotiz
            # Save associated invoice for NC/ND
            if request.cbte_asoc_tipo:
                invoice.cbte_asoc_tipo = request.cbte_asoc_tipo
                invoice.cbte_asoc_pto_vta = request.cbte_asoc_pto_vta
                invoice.cbte_asoc_nro = request.cbte_asoc_nro
                invoice.cbte_asoc_cuit = request.cbte_asoc_cuit or config.cuit.replace("-", "")

            if resultado == "A":
                invoice.invoice_number = f"{config.punto_vta:04d}-{cbte_nro:08d}"

            # Save IVA items
            for iva in request.iva_items:
                db.add(InvoiceIvaItem(
                    invoice_id=invoice.id,
                    iva_id=iva.iva_id,
                    base_imp=iva.base_imp,
                    importe=iva.importe,
                ))

            db.commit()

            logger.info(f"ARCA emit: tipo={request.cbte_tipo} nro={cbte_nro} CAE={cae} result={resultado}")

            return ArcaEmitResponse(
                success=(resultado == "A"),
                cae=cae,
                cae_vto=str(cae_vto) if cae_vto else None,
                cbte_nro=cbte_nro,
                resultado=resultado,
                observaciones=obs_str,
                errores=err_str,
                invoice_id=invoice.id,
            )

        except Exception as e:
            logger.error(f"ARCA emit error: {str(e)}")
            invoice.arca_result = "R"
            invoice.arca_obs = str(e)
            db.commit()
            return ArcaEmitResponse(
                success=False, invoice_id=request.invoice_id, errores=str(e),
            )

    # ─── CUIT Lookup (Padrón A5) ──────────────────────────────

    def _ensure_padron_auth(self, config: ArcaConfig):
        """Ensure we have a valid token for ws_sr_padron_a5"""
        now = datetime.now(timezone.utc)
        if self._padron_token and self._padron_token_expiry and now < self._padron_token_expiry:
            return
        self._authenticate_padron(config)

    def _authenticate_padron(self, config: ArcaConfig):
        """Authenticate with WSAA for ws_sr_padron_a5 service"""
        try:
            cert_path = config.cert_path
            key_path = config.key_path
            tra_xml = self._create_tra(service="ws_sr_padron_a13")
            cms = self._sign_tra(tra_xml, cert_path, key_path)
            wsdl_url = WSAA_WSDL.get(config.environment, WSAA_WSDL["homologacion"])
            wsaa_client = ZeepClient(wsdl=wsdl_url, transport=self._transport)
            ta_xml = wsaa_client.service.loginCms(in0=cms)
            root = ET.fromstring(ta_xml)
            self._padron_token = root.find('.//token').text
            self._padron_sign = root.find('.//sign').text
            expiry_text = root.find('.//expirationTime').text
            self._padron_token_expiry = datetime.fromisoformat(expiry_text.replace("Z", "+00:00"))
            logger.info(f"Padron A13 auth OK, expires: {expiry_text}")
        except Exception as e:
            logger.error(f"Padron A13 auth error: {e}")
            raise

    IVA_CONDITION_MAP = {
        1: "IVA Responsable Inscripto",
        4: "IVA Sujeto Exento",
        5: "Consumidor Final",
        6: "Responsable Monotributo",
        7: "Sujeto No Categorizado",
        8: "Proveedor del Exterior",
        9: "Cliente del Exterior",
        10: "IVA Liberado - Ley Nº 19.640",
        11: "IVA Responsable Inscripto - Ag. de Percepción",
    }

    def lookup_cuit(self, db: Session, cuit: str) -> Dict:
        """
        Lookup taxpayer information by CUIT using AFIP's ws_sr_padron_a13.
        Returns: razon_social, condicion_iva, domicilio, tipo_persona, etc.
        """
        config = self.get_config(db)
        if not config:
            raise ValueError("No ARCA configuration found")

        cuit_clean = cuit.replace("-", "").strip()

        try:
            self._ensure_padron_auth(config)

            wsdl_url = WS_PADRON_WSDL.get(config.environment, WS_PADRON_WSDL["produccion"])
            padron_client = ZeepClient(wsdl=wsdl_url, transport=self._transport)

            result = padron_client.service.getPersona(
                token=self._padron_token,
                sign=self._padron_sign,
                cuitRepresentada=int(config.cuit.replace("-", "")),
                idPersona=int(cuit_clean),
            )

            # A13 returns data in result.persona
            persona = getattr(result, 'persona', None)
            if not persona:
                return {
                    "success": False,
                    "error": f"No se encontró contribuyente con CUIT {cuit}",
                    "cuit": cuit_clean,
                }

            # Extract razón social
            razon_social = ""
            tipo_persona = getattr(persona, 'tipoPersona', '') or ""
            if tipo_persona == "JURIDICA":
                razon_social = getattr(persona, 'razonSocial', '') or ""
            else:
                apellido = getattr(persona, 'apellido', '') or ""
                nombre = getattr(persona, 'nombre', '') or ""
                razon_social = f"{apellido} {nombre}".strip()

            # Extract domicilio (A13 has a list of domicilios)
            domicilio = ""
            domicilios = getattr(persona, 'domicilio', None)
            if domicilios:
                for d in domicilios:
                    if getattr(d, 'tipoDomicilio', '') == "FISCAL":
                        parts = []
                        if getattr(d, 'direccion', ''):
                            parts.append(str(d.direccion))
                        if getattr(d, 'localidad', ''):
                            parts.append(str(d.localidad))
                        if getattr(d, 'descripcionProvincia', ''):
                            parts.append(str(d.descripcionProvincia))
                        domicilio = ", ".join(parts)
                        break
                if not domicilio and domicilios:
                    d = domicilios[0]
                    parts = []
                    if getattr(d, 'direccion', ''):
                        parts.append(str(d.direccion))
                    if getattr(d, 'localidad', ''):
                        parts.append(str(d.localidad))
                    if getattr(d, 'descripcionProvincia', ''):
                        parts.append(str(d.descripcionProvincia))
                    domicilio = ", ".join(parts)

            # Activity (A13 has it directly on persona)
            actividad_principal = getattr(persona, 'descripcionActividadPrincipal', '') or ""

            # Determine condición IVA
            condicion_iva = 5  # Default: Consumidor Final
            condicion_iva_desc = "Consumidor Final"

            datos_rg = getattr(result, 'datosRegimenGeneral', None)
            if datos_rg:
                impuestos = getattr(datos_rg, 'impuesto', None)
                if impuestos:
                    for imp in impuestos:
                        if getattr(imp, 'idImpuesto', 0) == 30:
                            condicion_iva = 1
                            condicion_iva_desc = "IVA Responsable Inscripto"
                            break

            datos_mono = getattr(result, 'datosMonotributo', None)
            if datos_mono:
                condicion_iva = 6
                condicion_iva_desc = "Responsable Monotributo"

            return {
                "success": True,
                "cuit": cuit_clean,
                "razon_social": razon_social,
                "tipo_persona": tipo_persona,
                "condicion_iva": condicion_iva,
                "condicion_iva_desc": condicion_iva_desc,
                "domicilio": domicilio,
                "actividad_principal": actividad_principal,
                "estado": getattr(persona, 'estadoClave', ''),
            }

        except Exception as e:
            logger.error(f"CUIT lookup error: {e}")
            return {
                "success": False,
                "error": str(e),
                "cuit": cuit_clean,
            }


# Singleton
arca_service = ArcaService()

