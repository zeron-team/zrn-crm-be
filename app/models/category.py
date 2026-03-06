from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Family(Base):
    """Top level: Family (e.g. Software, Hardware, Infrastructure)"""
    __tablename__ = "families"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True, index=True)
    code = Column(String, nullable=True, index=True)
    description = Column(String, nullable=True)

    categories = relationship("Category", back_populates="family", cascade="all, delete-orphan")


class Category(Base):
    """Middle level: Category belongs to a Family"""
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    code = Column(String, nullable=True, index=True)
    description = Column(String, nullable=True)
    family_id = Column(Integer, ForeignKey("families.id", ondelete="CASCADE"), nullable=False)

    family = relationship("Family", back_populates="categories")
    subcategories = relationship("Subcategory", back_populates="category", cascade="all, delete-orphan")


class Subcategory(Base):
    """Bottom level: Subcategory belongs to a Category"""
    __tablename__ = "subcategories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    code = Column(String, nullable=True, index=True)
    description = Column(String, nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False)

    category = relationship("Category", back_populates="subcategories")
