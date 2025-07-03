import os
from datetime import datetime, timedelta

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


class KeyManager:
    """
    Manages generation, storage, and retrieval of RSA keys.
    """

    def __init__(self, key_dir: str = "keys", key_refresh_days: int = 30):
        """
        Initializes the KeyManager and ensures keys are up-to-date.

        :param key_dir: Directory to store the keys.
        :param key_refresh_days: Number of days after which keys should be refreshed.
        """
        self.key_dir = key_dir
        self.key_refresh_days = key_refresh_days
        self.private_key_path = os.path.join(key_dir, "private_key.pem")
        self.public_key_path = os.path.join(key_dir, "public_key.pem")
        self._ensure_keys()  # Ensure keys are present and valid

    def _ensure_keys(self) -> None:
        """
        Ensures the keys are present and refreshed if necessary.
        """
        if not os.path.exists(self.key_dir):
            os.makedirs(self.key_dir)  # Create directory if it does not exist
        if (
            not os.path.exists(self.private_key_path)
            or self._keys_need_refresh()
        ):
            self._generate_keys()  # Generate new keys if needed

    def _keys_need_refresh(self) -> bool:
        """
        Checks if the keys need to be refreshed based on their last modification time.

        :return: True if keys need refresh, otherwise False.
        """
        if not os.path.exists(self.private_key_path):
            return True
        file_time = datetime.fromtimestamp(
            os.path.getmtime(self.private_key_path)
        )
        # Check if the last modification time is beyond the refresh threshold
        return datetime.now() - file_time > timedelta(
            days=self.key_refresh_days
        )

    def _generate_keys(self) -> None:
        """
        Generates a new RSA key pair and saves them to files.
        """
        private_key = rsa.generate_private_key(
            public_exponent=65537, key_size=2048, backend=default_backend()
        )
        public_key = private_key.public_key()

        # Serialize private key to PEM format
        pem_private = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        # Serialize public key to PEM format
        pem_public = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        # Save the keys to files
        with open(self.private_key_path, "wb") as f:
            f.write(pem_private)
        with open(self.public_key_path, "wb") as f:
            f.write(pem_public)

    def get_private_key(self) -> bytes:
        """
        Retrieves the private key from the file.

        :return: The private key in PEM format.
        """
        with open(self.private_key_path, "rb") as f:
            return f.read()

    def get_public_key(self) -> bytes:
        """
        Retrieves the public key from the file.

        :return: The public key in PEM format.
        """
        with open(self.public_key_path, "rb") as f:
            return f.read()
