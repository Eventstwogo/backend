from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base import Base



class Role(Base):
    __tablename__ = "sa_roles"

    role_id: Mapped[str] = mapped_column(
        String(length=6), primary_key=True, unique=True
    )
    role_name: Mapped[str] = mapped_column(String(length=100), nullable=False)
    role_status: Mapped[bool] = mapped_column(Boolean, default=False)
    role_tstamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True, server_default=func.now()
    )

    users: Mapped[list["AdminUser"]] = relationship(
        back_populates="role", cascade="all, delete-orphan"
    )

 

class Config(Base):
    __tablename__ = "sa_config"

    id: Mapped[int] = mapped_column(
        primary_key=True, default=1
    ) 
    default_password: Mapped[str] = mapped_column(
        String(255), nullable=False
    )  
    default_password_hash: Mapped[str] = mapped_column(
        String(255), nullable=False
    )  
    logo_url: Mapped[Optional[str]] = mapped_column(String(255), default=None)
    global_180_day_flag: Mapped[bool] = mapped_column(
        Boolean, default=True
    )  
    config_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )



class Category(Base):
    __tablename__ = "sa_categories"

    category_id: Mapped[str] = mapped_column(
        String, primary_key=True, unique=True
    )
    category_name: Mapped[str] = mapped_column(String, nullable=False)
    category_description: Mapped[str | None] = mapped_column(
        String, nullable=True
    )
    category_slug: Mapped[str] = mapped_column(
        String, nullable=False, unique=True
    )
    category_meta_title: Mapped[str | None] = mapped_column(
        String, nullable=True
    )
    category_meta_description: Mapped[str | None] = mapped_column(
        String, nullable=True
    )
    category_img_thumbnail: Mapped[str | None] = mapped_column(
        String, nullable=True
    )
    featured_category: Mapped[bool | None] = mapped_column(
        Boolean, nullable=True
    )
    show_in_menu: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    category_status: Mapped[bool] = mapped_column(Boolean, default=False)
    category_tstamp: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, server_default=func.now()
    )

    # Relationship to SubCategory
    subcategories: Mapped[list["SubCategory"]] = relationship(
        back_populates="category", cascade="all, delete-orphan"
    )


class SubCategory(Base):
    __tablename__ = "sa_subcategories"

    id: Mapped[str] = mapped_column(String, primary_key=True, unique=True)
    subcategory_id: Mapped[str] = mapped_column(String, unique=True)
    category_id: Mapped[str] = mapped_column(
        ForeignKey(column="sa_categories.category_id"), nullable=False
    )
    subcategory_name: Mapped[str] = mapped_column(String, nullable=False)
    subcategory_description: Mapped[str | None] = mapped_column(
        String, nullable=True
    )
    subcategory_slug: Mapped[str] = mapped_column(
        String, nullable=False, unique=True
    )
    subcategory_meta_title: Mapped[str | None] = mapped_column(
        String, nullable=True
    )
    subcategory_meta_description: Mapped[str | None] = mapped_column(
        String, nullable=True
    )
    subcategory_img_thumbnail: Mapped[str | None] = mapped_column(
        String, nullable=True
    )
    featured_subcategory: Mapped[bool | None] = mapped_column(
        Boolean, nullable=True
    )
    show_in_menu: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    subcategory_status: Mapped[bool] = mapped_column(Boolean, default=False)
    subcategory_tstamp: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, server_default=func.now()
    )

    # Relationship to Category
    category: Mapped["Category"] = relationship(back_populates="subcategories")



class AdminUser(Base):
    __tablename__ = "sa_adminusers"

    user_id: Mapped[str] = mapped_column(
        String(6), primary_key=True, unique=True
    )
    role_id: Mapped[str] = mapped_column(
        ForeignKey("sa_roles.role_id"), nullable=False
    )

    username: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True
    )
    email: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    profile_picture: Mapped[Optional[str]] = mapped_column(
        String(255), default=None
    )

    # 180-day password expiry
    days_180_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    days_180_timestamp: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), default=None
    )

    # Login management
    login_status: Mapped[int] = mapped_column(Integer, default=-1)
    last_login: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), default=None
    )
    login_attempts: Mapped[int] = mapped_column(Integer, default=0)

    # Account lifecycle
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    # Relationships
    role: Mapped["Role"] = relationship(back_populates="users")

    __table_args__ = (
        UniqueConstraint("username", "email", name="unique_username_email"),
    )