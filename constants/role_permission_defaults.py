# constants/role_permission_defaults.py

# Permission and Role Names
PERMISSION_NAMES = ["MANAGE", "EDIT", "VIEW"]
ROLE_NAMES = ["SUPERADMIN", "ADMIN"]

# Mapping: Role → List of Permission Names
ROLE_PERMISSION_NAME_MAP = {
    "SUPERADMIN": ["MANAGE", "EDIT", "VIEW"],
    "ADMIN": ["EDIT", "VIEW"],
    "EDITOR": ["EDIT"],
    "VIEWER": ["VIEW"],
}
