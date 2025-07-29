"""
general.py

General user models for the shoppersky application.
Contains User and UserVerification models.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from .base import Base


class User(Base):
    """
    User model for regular users (customers).
    
    Attributes:
        user_id: Unique identifier for the user
        username_hash: Hashed username (unique)
        first_name_hash: Encrypted first name
        last_name_hash: Encrypted last name
        email_hash: Hashed email address (unique)
        phone_number_hash: Hashed phone number (unique)
        password_hash: Hashed password
        login_status: Login status (0=active, 1=locked)
        successful_logins: Count of successful login attempts
        failed_logins: Count of failed login attempts
        last_login: Timestamp of last successful login
        account_locked_at: Timestamp when account was locked
        days_180_flag: 180-day flag from system configuration
        created_at: Timestamp when user was created
        updated_at: Timestamp when user was last updated
        is_active: Whether the user account is active
    """
    
    __tablename__ = "users"
    
    # Primary key
    user_id: Mapped[str] = mapped_column(
        String(6), primary_key=True, index=True
    )
    
    # Encrypted user data (for retrieval)
    username: Mapped[str] = mapped_column(
        Text, nullable=False
    )
    first_name: Mapped[str] = mapped_column(
        Text, nullable=False
    )
    last_name: Mapped[str] = mapped_column(
        Text, nullable=False
    )
    email: Mapped[str] = mapped_column(
        Text, nullable=False
    )
    phone_number: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    
    # Hashed user data (for uniqueness checks)
    username_hash: Mapped[str] = mapped_column(
        Text, unique=True, index=True, nullable=False
    )
    email_hash: Mapped[str] = mapped_column(
        Text, unique=True, index=True, nullable=False
    )
    phone_number_hash: Mapped[Optional[str]] = mapped_column(
        Text, unique=True, index=True, nullable=True
    )
    password_hash: Mapped[str] = mapped_column(
        Text, nullable=False
    )
    
    # Login tracking
    login_status: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False  # 0=active, 1=locked
    )
    successful_logins: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    failed_logins: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    last_login: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    account_locked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    
    # System flags
    days_180_flag: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(), 
        nullable=False
    )
    
    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    
    # Relationships
    password_resets: Mapped[list["UserPasswordReset"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class UserVerification(Base):
    """
    User verification model for email and phone verification.
    
    Attributes:
        user_id: Foreign key to User model
        email_verification_token: Token for email verification
        email_token_expires_at: Expiration time for email token
        email_verified: Whether email is verified
        phone_verification_token: Token for phone verification
        phone_token_expires_at: Expiration time for phone token
        phone_verified: Whether phone is verified
        created_at: Timestamp when verification record was created
        updated_at: Timestamp when verification record was last updated
    """
    
    __tablename__ = "user_verifications"
    
    # Primary key (same as user_id)
    user_id: Mapped[str] = mapped_column(
        String(6), primary_key=True, index=True
    )
    
    # Email verification
    email_verification_token: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    email_token_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    email_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    
    # Phone verification
    phone_verification_token: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    phone_token_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    phone_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(), 
        nullable=False
    )

class UserPasswordReset(Base):
    """
    Password reset model for regular users.
    
    Attributes:
        id: Primary key
        user_id: Foreign key to User model
        token: Unique reset token
        expires_at: Token expiration timestamp
        is_used: Whether the token has been used
        created_at: Timestamp when token was created
        used_at: Timestamp when token was used
    """
    
    __tablename__ = "user_password_resets"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.user_id"), nullable=False
    )
    token: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
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
    user: Mapped["User"] = relationship(back_populates="password_resets")