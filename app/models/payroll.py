from sqlalchemy import Column, Integer, String, Boolean, Date, DateTime, Numeric, Text, ForeignKey, func, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base


class PayrollConcept(Base):
    """Configurable payroll concept (jubilación, obra social, SAC, etc.)"""
    __tablename__ = "payroll_concepts"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)           # remunerativo, no_remunerativo, deduccion
    category = Column(String, nullable=True)        # jubilacion, obra_social, pami, sindicato, ganancias, sac, vacaciones, otro
    calc_mode = Column(String, nullable=False, default="porcentaje")  # porcentaje, fijo
    default_rate = Column(Numeric(8, 4), nullable=True)  # e.g. 11.0000 for 11%
    applies_to = Column(String, nullable=False, default="employee")  # employee, employer, both
    is_mandatory = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())

    items = relationship("PayrollSlipItem", back_populates="concept")


class PayrollPeriod(Base):
    """Monthly payroll period"""
    __tablename__ = "payroll_periods"

    id = Column(Integer, primary_key=True, index=True)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    description = Column(String, nullable=True)     # e.g. "Marzo 2026", "SAC 1er semestre"
    period_type = Column(String, nullable=False, default="monthly")  # monthly, sac_1, sac_2, vacation
    status = Column(String, nullable=False, default="draft")  # draft, confirmed, paid
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (UniqueConstraint('year', 'month', 'period_type', name='uq_period_year_month_type'),)

    slips = relationship("PayrollSlip", back_populates="period", cascade="all, delete-orphan")


class PayrollSlip(Base):
    """Individual payroll slip (recibo de sueldo)"""
    __tablename__ = "payroll_slips"

    id = Column(Integer, primary_key=True, index=True)
    period_id = Column(Integer, ForeignKey("payroll_periods.id", ondelete="CASCADE"), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)

    gross_salary = Column(Numeric(14, 2), nullable=False, default=0)
    total_remunerativo = Column(Numeric(14, 2), nullable=False, default=0)
    total_no_remunerativo = Column(Numeric(14, 2), nullable=False, default=0)
    total_deductions = Column(Numeric(14, 2), nullable=False, default=0)
    net_salary = Column(Numeric(14, 2), nullable=False, default=0)
    total_employer_cost = Column(Numeric(14, 2), nullable=False, default=0)

    status = Column(String, nullable=False, default="draft")  # draft, confirmed, paid
    payment_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (UniqueConstraint('period_id', 'employee_id', name='uq_slip_period_employee'),)

    period = relationship("PayrollPeriod", back_populates="slips")
    employee = relationship("Employee")
    items = relationship("PayrollSlipItem", back_populates="slip", cascade="all, delete-orphan")


class PayrollSlipItem(Base):
    """Line item in a payroll slip"""
    __tablename__ = "payroll_slip_items"

    id = Column(Integer, primary_key=True, index=True)
    slip_id = Column(Integer, ForeignKey("payroll_slips.id", ondelete="CASCADE"), nullable=False, index=True)
    concept_id = Column(Integer, ForeignKey("payroll_concepts.id", ondelete="SET NULL"), nullable=True)

    concept_code = Column(String, nullable=True)
    concept_name = Column(String, nullable=False)
    type = Column(String, nullable=False)   # remunerativo, no_remunerativo, deduccion, employer_cost
    rate = Column(Numeric(8, 4), nullable=True)      # percentage rate used
    base_amount = Column(Numeric(14, 2), nullable=True)  # base for percentage calc
    amount = Column(Numeric(14, 2), nullable=False, default=0)
    sort_order = Column(Integer, default=0)

    slip = relationship("PayrollSlip", back_populates="items")
    concept = relationship("PayrollConcept", back_populates="items")
