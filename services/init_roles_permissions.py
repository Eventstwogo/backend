# services/init_roles_permissions.py
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from constants.role_permission_defaults import (
    ROLE_NAMES,
)
from db.models.superadmin import Role
from utils.id_generators import generate_digits_lowercase


async def init_roles_permissions(db: AsyncSession) -> None:
    role_name_id_map: dict[Any, Any] = {}

    # --- Insert Roles ---
    for name in ROLE_NAMES:
        result = await db.execute(select(Role).where(Role.role_name == name))
        role = result.scalar()
        if not role:
            role = Role(
                role_id=generate_digits_lowercase(),
                role_name=name,
                role_status=False,
            )
            db.add(role)
            await db.flush()
        role_name_id_map[name] = role.role_id

    await db.commit()
