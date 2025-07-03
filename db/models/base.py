"""
base.py

SQLAlchemy Declarative Base class with:
- Constraint naming conventions
- Utility methods for serialization and debugging
- SQLAlchemy 2.0 compliant structure
"""

from typing import Any

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Naming convention for constraints (Alembic migration friendly)
NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(table_name)s_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_label)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_label)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

# Shared metadata object with naming convention
metadata_obj: MetaData = MetaData(naming_convention=NAMING_CONVENTION)


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy ORM models in the shoppersky application.
    Provides automatic metadata and serialization utilities.
    """

    metadata = metadata_obj

    def __repr__(self) -> str:
        """
        Return a string representation of the model instance for debugging.
        Example: <Role(role_id='ADM001', role_name='Admin')>
        """
        values: str = ", ".join(
            f"{col.name}={getattr(self, col.name)!r}"
            for col in self.__table__.columns
        )
        return f"<{self.__class__.__name__}({values})>"

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the model instance to a dictionary.
        Useful for JSON serialization or internal APIs.
        """
        return {
            col.name: getattr(self, col.name) for col in self.__table__.columns
        }
