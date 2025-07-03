# services/init_roles_permissions.py
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from constants.role_permission_defaults import (
    PERMISSION_NAMES,
    ROLE_NAMES,
    ROLE_PERMISSION_NAME_MAP,
)
from db.models.superadmin import Role
from utils.id_generators import generate_digits_lowercase


async def init_roles_permissions(db: AsyncSession) -> None:
    permission_name_id_map: dict[Any, Any] = {}
    role_name_id_map: dict[Any, Any] = {}

    # --- Insert Permissions ---
    # for name in PERMISSION_NAMES:
    #     result = await db.execute(
    #         select(Permission).where(Permission.permission_name == name)
    #     )
    #     permission = result.scalar()
    #     if not permission:
    #         permission = Permission(
    #             permission_id=generate_digits_lowercase(),
    #             permission_name=name,
    #             permission_status=False,
    #         )
    #         db.add(permission)
    #         await db.flush()
    #     permission_name_id_map[name] = permission.permission_id

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

    # # --- Insert Role-Permission Mappings ---
    # for role_name, perm_names in ROLE_PERMISSION_NAME_MAP.items():
    #     role_id = role_name_id_map[role_name]
    #     for perm_name in perm_names:
    #         permission_id = permission_name_id_map[perm_name]
    #         result = await db.execute(
    #             select(RolePermission).where(
    #                 RolePermission.role_id == role_id,
    #                 RolePermission.permission_id == permission_id,
    #             )
    #         )
    #         if not result.scalar():
    #             db.add(
    #                 RolePermission(
    #                     role_id=role_id,
    #                     permission_id=permission_id,
    #                     rp_status=False,
    #                 )
    #             )

    await db.commit()
