# src/config/crypto.py
from __future__ import annotations

from cryptography.fernet import Fernet


def generate_key() -> str:
    """生成新的 Fernet 密钥并返回 base64 字符串."""
    return Fernet.generate_key().decode("utf-8")


class KeyCipher:
    """基于 Fernet 的对称加解密，用于 API Key 安全存储.

    用法:
        key = generate_key()
        cipher = KeyCipher(key)
        encrypted = cipher.encrypt("sk-abc123")
        decrypted = cipher.decrypt(encrypted)
    """

    def __init__(self, key: str) -> None:
        self._fernet = Fernet(key.encode("utf-8"))

    def encrypt(self, plaintext: str) -> str:
        """加密明文字符串，返回 base64 密文."""
        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        """解密密文，返回原始明文字符串."""
        return self._fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")

    def encrypt_none(self, plaintext: str | None) -> str | None:
        """加密可选的明文字符串, None 透传."""
        if plaintext is None:
            return None
        return self.encrypt(plaintext)
