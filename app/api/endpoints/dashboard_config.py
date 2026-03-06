from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.dashboard_config import DashboardConfig
from app.schemas.dashboard_config import (
    DashboardConfigCreate,
    DashboardConfigResponse,
    DEFAULT_WIDGETS,
    WIDGET_CATALOG,
)

router = APIRouter()


@router.get("/catalog")
def get_widget_catalog():
    """Returns the full list of available widgets."""
    return WIDGET_CATALOG


@router.get("/{user_id}", response_model=DashboardConfigResponse)
def get_dashboard_config(user_id: int, db: Session = Depends(get_db)):
    config = db.query(DashboardConfig).filter(DashboardConfig.user_id == user_id).first()
    if not config:
        # Return a virtual default config (not persisted yet)
        return DashboardConfigResponse(
            id=0,
            user_id=user_id,
            widgets=DEFAULT_WIDGETS,
            updated_at=None,
        )
    return config


@router.put("/{user_id}", response_model=DashboardConfigResponse)
def save_dashboard_config(user_id: int, config_in: DashboardConfigCreate, db: Session = Depends(get_db)):
    config = db.query(DashboardConfig).filter(DashboardConfig.user_id == user_id).first()
    if config:
        config.widgets = config_in.widgets
    else:
        config = DashboardConfig(user_id=user_id, widgets=config_in.widgets)
        db.add(config)
    db.commit()
    db.refresh(config)
    return config
