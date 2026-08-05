# src/config/crypto.py
from __future__ import annotations

from cryptography.fernet import Fernet


def generate_key() -> str:
    """生成新的 Fernet 密钥并返回 base64 字符串."""
    return Fernet.generate_key().decode("utf-8")


def load_key(data_dir: str) -> str:
    """加载或生成持久化加密密钥.

    优先从 ``data_dir/.encryption_key`` 读取；不存在则生成新密钥并持久化。
    确保每次运行使用同一密钥，避免解密失败。
    """
    from pathlib import Path

    key_path = Path(data_dir) / ".encryption_key"
    if key_path.exists():
        return key_path.read_text(encoding="utf-8").strip()
    key = generate_key()
    key_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.write_text(key, encoding="utf-8")
    return key


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
