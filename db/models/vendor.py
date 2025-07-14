# from datetime import datetime

# from sqlalchemy import Boolean, DateTime, Integer, String, func
# from sqlalchemy.orm import Mapped, mapped_column

# from db.models.base import Base

# class VendorSignup(Base):
#     __tablename__ = "ven_signup"
#     sno: Mapped[int] = mapped_column(Integer, autoincrement= True)
#     signup_id: Mapped[str] = mapped_column(
#         String(length=6), primary_key=True, unique=True
#     )
#     name: Mapped[str] = mapped_column(String, nullable=False)
#     email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
#     password: Mapped[str] = mapped_column(String, unique= True)
#     email_token: Mapped[str] = mapped_column(String, unique=True)
#     email_flag: Mapped[bool] = mapped_column(Boolean, default=False)
#     category: Mapped[str] = mapped_column(String, nullable=False)
#     timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    
# class VendorLogin(Base):
#     __tablename__ = "ven_login"
#     sno: Mapped[int] = mapped_column(Integer, autoincrement= True)
#     user_id: Mapped[str] = mapped_column(
#         String(length=6), primary_key=True, unique=True
#     )
#     name: Mapped[str] = mapped_column(String, nullable=False)
#     email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
#     password: Mapped[str] = mapped_column(String, unique= True)
  
#     is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
#     business_profile_id: Mapped[str] = mapped_column(
#         String(length=6), primary_key=True, unique=True
#     )
#     user_profile_id: Mapped[str] = mapped_column(
#         String(length=6), primary_key=True, unique=True
#     )
#     category: Mapped[str] = mapped_column(String, nullable=False)
#     login_attempts: Mapped[int] = mapped_column(Integer, default=0)
#     login_failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
#     timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
#     created_at: Mapped[datetime] = mapped_column(
#         DateTime(timezone=True), server_default=func.now()
#     )


# class BusinessProfile(Base):
#     __tablename__ = "ven_businessprofile"
#     sno: Mapped[int] = mapped_column(Integer, autoincrement= True)
#     profile_ref_id: Mapped[str] = mapped_column(
#         String(length=6), primary_key=True, unique=True
#     )
#     name: Mapped[str] = mapped_column(String, nullable=False)
#     email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
#     password: Mapped[str] = mapped_column(String, unique= True)
#     email_token: Mapped[str] = mapped_column(String, unique=True)
#     email_flag: Mapped[bool] = mapped_column(Boolean, default=False)
#     category: Mapped[str] = mapped_column(String, nullable=False)
#     timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


