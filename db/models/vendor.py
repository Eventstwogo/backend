from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, Enum as SQLEnum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from db.models.base import Base


class KYCStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class PlanType(str, Enum):
    free = "free"
    premium = "premium"
    enterprise = "enterprise"


class Vendor(Base):
    __tablename__ = "vendors"

    id: Mapped[str] = mapped_column(String, primary_key=True, unique=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    phone: Mapped[str] = mapped_column(String, unique= True)
    abn: Mapped[str] = mapped_column(String, unique=True)
    kyc_status: Mapped[KYCStatus] = mapped_column(SQLEnum(KYCStatus), default=KYCStatus.pending)
    plan: Mapped[PlanType] = mapped_column(SQLEnum(PlanType), default=PlanType.free)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    storefront: Mapped["Storefront"] = relationship(back_populates="vendor", uselist=False)


class Storefront(Base):
    __tablename__ = "storefronts"

    id: Mapped[str] = mapped_column(String, primary_key=True, unique=True)
    vendor_id: Mapped[str] = mapped_column(String, ForeignKey("vendors.id"))
    name: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str] = mapped_column(String, unique=True)
    logo_url: Mapped[str] = mapped_column(String)
    image_urls: Mapped[list[str]] = mapped_column(JSONB, default=list)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False)

    vendor: Mapped["Vendor"] = relationship(back_populates="storefront")




# class Admin(Base):


# class Customer(Base):

# class Profile(Base):
#     address


# class Wishlist(Base):

# class Cart(Base):

# class Orders(Base):



# class OrderHistory(Base):   

# class Transactions(Base):






# class Affiliates(Base):

# class Referrals(Base):