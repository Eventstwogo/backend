from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy import Boolean, DateTime, Integer, String, Text, ForeignKey, Enum as SQLAlchemyEnum, UniqueConstraint, func, event
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from slugify import slugify
from db.models.base import Base
from enum import Enum



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
        String(length=6), primary_key=True, unique=True
    )
    industry_id: Mapped[str] = mapped_column(
        String(length=6), nullable= False
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

    products: Mapped[list["Product"]] = relationship(
    back_populates="category", cascade="all, delete-orphan"
)


class SubCategory(Base):
    __tablename__ = "sa_subcategories"

    id: Mapped[str] = mapped_column(String, primary_key=True, unique=True)
    subcategory_id: Mapped[str] = mapped_column(String(length=6), unique=True)
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

    products: Mapped[list["Product"]] = relationship(
    back_populates="subcategory", cascade="all, delete-orphan"
)



class AdminUser(Base):
    __tablename__ = "sa_adminusers"

    user_id: Mapped[str] = mapped_column(
        String(6), primary_key=True, unique=True
    )
    role_id: Mapped[str] = mapped_column(
        ForeignKey("sa_roles.role_id"), nullable=False
    )

    username: Mapped[str] = mapped_column(
        String(500), nullable=False, unique=True
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    email_hash: Mapped[str]= mapped_column(String(255), unique=True, nullable=False)
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
    # Login status: 0 (active), 1 (locked)
    login_status: Mapped[int] = mapped_column(Integer, default=0)
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
    password_resets: Mapped[list["PasswordReset"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("username", "email", name="unique_username_email"),
    )


class PasswordReset(Base):
    __tablename__ = "sa_password_resets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("sa_adminusers.user_id"), nullable=False, unique=True
    )
    token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    is_used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), default=None
    )

    # Relationships
    user: Mapped["AdminUser"] = relationship(back_populates="password_resets")


class VendorPasswordReset(Base):
    __tablename__ = "ven_password_reset"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("ven_login.user_id"), nullable=False, unique=True
    )
    token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    is_used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), default=None
    )

    # Relationships
    vendor: Mapped["VendorLogin"] = relationship(back_populates="password_resets")


class SessionLog(Base):
    __tablename__ = "session_log"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(length=6), nullable=False)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    user_agent: Mapped[Optional[str]] = mapped_column(String(512))
    browser_name: Mapped[Optional[str]] = mapped_column(String(100))
    browser_version: Mapped[Optional[str]] = mapped_column(String(50))
    os: Mapped[Optional[str]] = mapped_column(String(100))
    device_type: Mapped[Optional[str]] = mapped_column(String(50))  # e.g., mobile, desktop
    login_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    logout_time: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None)
    login_success: Mapped[bool] = mapped_column(Boolean, default=True)
    failure_reason: Mapped[Optional[str]] = mapped_column(String(255), default=None)
    location: Mapped[Optional[str]] = mapped_column(String(255), default=None)  # if using geo IP


class VendorSignup(Base):
    __tablename__ = "ven_signup"
    sno: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement= True)
    signup_id: Mapped[str] = mapped_column(
        String(length=6), unique=True
    )
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    email_hash: Mapped[str]= mapped_column(String, unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String, unique= True)
    email_token: Mapped[str] = mapped_column(String, unique=True, nullable=True)
    email_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    email_token_timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    
class VendorLogin(Base):
    __tablename__ = "ven_login"
 
    sno: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(length=6), unique=True)
    username: Mapped[str] = mapped_column(String, nullable=False)
    username_hash: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    email_hash: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String, unique=True)
    is_verified: Mapped[int] = mapped_column(Integer, default=False)
    business_profile_id: Mapped[str] = mapped_column(
        String(length=6),
        unique=True
    )
    user_profile_id: Mapped[str] = mapped_column(String(length=6), unique=True)
    login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    login_failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    login_status: Mapped[int] = mapped_column(Integer, default=0)
    locked_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), default=None)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), default=None)
    role: Mapped[Optional[str]] = mapped_column(ForeignKey("sa_roles.role_id"), nullable=True)
    vendor_ref_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, default="unknown")
    profile_pic: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
 
    # Relationships
    role_details: Mapped[Optional["Role"]] = relationship("Role", foreign_keys=[role])
 
    business_profile: Mapped[Optional["BusinessProfile"]] = relationship(
        "BusinessProfile",
        back_populates="vendor_login",
        uselist=False,
        primaryjoin="VendorLogin.business_profile_id == foreign(BusinessProfile.profile_ref_id)"
    )
    
    password_resets: Mapped[list["VendorPasswordReset"]] = relationship(
        back_populates="vendor", cascade="all, delete-orphan"
    )
 
 
class BusinessProfile(Base):
    __tablename__ = "ven_businessprofile"
 
    sno: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    abn_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    abn_hash: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    profile_ref_id: Mapped[str] = mapped_column(
        String(length=6),
        ForeignKey("ven_login.business_profile_id"),
        unique=True
    )
    profile_details: Mapped[dict] = mapped_column(JSONB, nullable=False)
    business_logo: Mapped[str] = mapped_column(String, nullable=True)
    payment_preference: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=True)
    store_name: Mapped[str] = mapped_column(String, nullable=True)
    store_slug: Mapped[str] = mapped_column(String, nullable=True, unique=True)
    store_url: Mapped[str] = mapped_column(String, nullable=True)
    industry: Mapped[str] = mapped_column(
        String,
        ForeignKey("ven_industries.industry_id"),
        nullable=True
    )
    location: Mapped[str] = mapped_column(String, nullable=True)
    ref_number: Mapped[str] = mapped_column(String(length=6), unique=True)
    purpose: Mapped[dict] = mapped_column(JSONB, nullable=False)
    is_approved: Mapped[int] = mapped_column(Integer, default=False)
    reviewer_comment: Mapped[str] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    approved_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    
    industry_obj: Mapped["Industries"] = relationship(
        "Industries", back_populates="business_profiles", lazy="joined"
    )
    vendor_login: Mapped["VendorLogin"] = relationship(
        "VendorLogin",
        back_populates="business_profile",
        uselist=False
    )


# Event listener to automatically generate store_slug from store_name
@event.listens_for(BusinessProfile.store_name, 'set')
def generate_store_slug(target, value, oldvalue, initiator):
    """
    Automatically generate store_slug when store_name is set or updated.
    """
    if value and value != oldvalue:
        # Generate base slug from store name
        base_slug = slugify(value)
        
        # If the slug is empty (e.g., non-ASCII characters only), use a fallback
        if not base_slug:
            base_slug = f"store-{target.profile_ref_id}" if target.profile_ref_id else "store"
        
        # For new records or when slug changes, we'll set it directly
        # The unique constraint will handle duplicates at the database level
        target.store_slug = base_slug


# Alternative method to generate unique slug with database session
def generate_unique_store_slug(session, store_name: str, profile_ref_id: str = None, exclude_id: str = None) -> str:
    """
    Generate a unique store slug by checking against existing slugs in the database.
    
    Args:
        session: SQLAlchemy session
        store_name: The store name to slugify
        profile_ref_id: The profile reference ID for fallback
        exclude_id: Profile ID to exclude from uniqueness check (for updates)
    
    Returns:
        A unique slug string
    """
    base_slug = slugify(store_name) if store_name else f"store-{profile_ref_id}" if profile_ref_id else "store"
    
    if not base_slug:
        base_slug = f"store-{profile_ref_id}" if profile_ref_id else "store"
    
    # Check if slug exists
    query = session.query(BusinessProfile).filter(BusinessProfile.store_slug == base_slug)
    if exclude_id:
        query = query.filter(BusinessProfile.profile_ref_id != exclude_id)
    
    if not query.first():
        return base_slug
    
    # If slug exists, append a number
    counter = 1
    while True:
        new_slug = f"{base_slug}-{counter}"
        query = session.query(BusinessProfile).filter(BusinessProfile.store_slug == new_slug)
        if exclude_id:
            query = query.filter(BusinessProfile.profile_ref_id != exclude_id)
        
        if not query.first():
            return new_slug
        counter += 1

 

class Industries(Base):
    __tablename__ = "ven_industries"

    sno: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    industry_id:Mapped[str] = mapped_column(
        String(length=6), unique=True
    )
    industry_name: Mapped[str] = mapped_column(String, unique=True, nullable=False) 
    industry_slug: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    business_profiles: Mapped[list["BusinessProfile"]] = relationship(
        "BusinessProfile", back_populates="industry_obj"
    )


class VendorCategoryManagement(Base):
    __tablename__ = "ven_categorymanagement"

    sno: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vendor_ref_id:Mapped[str] = mapped_column(
        String(length=6)
    )
    category_id: Mapped[str] = mapped_column(String(length=6), nullable=False) 
    subcategory_id: Mapped[str] = mapped_column(String(length=6), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)



class Product(Base):
    __tablename__ = "ven_products"

    product_id: Mapped[str] = mapped_column(String, primary_key=True, unique=True)

    vendor_id: Mapped[str] = mapped_column(String, nullable=False)

    category_id: Mapped[str] = mapped_column(
        ForeignKey("sa_categories.category_id"), nullable=False
    )
    subcategory_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("sa_subcategories.subcategory_id"), nullable=True
    )

    slug: Mapped[str] = mapped_column(String, unique=True, nullable=False)

    identification: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    descriptions: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB)
    pricing: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB)
    inventory: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB)
    physical_attributes: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB)
    images: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB)
    tags_and_relationships: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB)

    status_flags: Mapped[Dict[str, bool]] = mapped_column(
        MutableDict.as_mutable(JSONB),
        default=lambda: {
            "featured_product": False,
            "published_product": False,
            "product_status": False,
        },
    )

    timestamp: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    category: Mapped["Category"] = relationship(back_populates="products")
    subcategory: Mapped[Optional["SubCategory"]] = relationship(back_populates="products")


class EnquiryStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"
 
   
class Enquiry(Base):
    __tablename__ = "user_contact_us"
 
    enquiry_id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True
    )
    firstname: Mapped[str] = mapped_column(String(100), nullable=False)
    lastname: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(20), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    enquiry_status: Mapped[EnquiryStatus] = mapped_column(
        SQLAlchemyEnum(EnquiryStatus),
        default=EnquiryStatus.PENDING,
        nullable=False,
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), server_default=func.now()
    )


class QueryStatus(Enum):
    QUERY_OPEN = "open"
    QUERY_IN_PROGRESS = "in_progress"
    QUERY_ANSWERED = "answered"
    QUERY_CLOSED = "closed"


class VendorQuery(Base):
    __tablename__ = "vendor_queries"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    sender_user_id: Mapped[str] = mapped_column(
        String, nullable=False
    )  # who raised the query
    receiver_user_id: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )  # admin who handles
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)

    # The full threaded messages between vendor <-> admin
    thread: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB,  # using JSONB for PostgreSQL
        default=list,
        nullable=False,
    )

    query_status: Mapped[QueryStatus] = mapped_column(
        SQLAlchemyEnum(QueryStatus),
        default=QueryStatus.QUERY_OPEN,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
    )
