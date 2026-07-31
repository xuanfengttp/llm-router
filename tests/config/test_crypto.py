# tests/config/test_crypto.py
import pytest

from src.config.crypto import KeyCipher, generate_key


class TestKeyCipher:
    @pytest.fixture
    def cipher(self):
        key = generate_key()
        return KeyCipher(key)

    def test_encrypt_decrypt_roundtrip(self, cipher):
        plaintext = "sk-test-api-key-abc123"
        encrypted = cipher.encrypt(plaintext)
        assert encrypted != plaintext
        assert isinstance(encrypted, str)
        decrypted = cipher.decrypt(encrypted)
        assert decrypted == plaintext

    def test_encrypt_empty_string(self, cipher):
        encrypted = cipher.encrypt("")
        assert cipher.decrypt(encrypted) == ""

    def test_encrypt_unicode(self, cipher):
        plaintext = "密钥-🔑-テスト"
        encrypted = cipher.encrypt(plaintext)
        assert cipher.decrypt(encrypted) == plaintext

    def test_encrypt_none_returns_none(self, cipher):
        assert cipher.encrypt_none(None) is None
        encrypted = cipher.encrypt_none("sk-key")
        assert encrypted is not None
        assert cipher.decrypt(encrypted) == "sk-key"

    def test_different_keys_produce_different_ciphertexts(self, cipher):
        plaintext = "sk-test-key"
        ct1 = cipher.encrypt(plaintext)
        ct2 = cipher.encrypt(plaintext)
        assert ct1 != ct2  # Fernet uses random IV per encryption

    def test_wrong_key_cannot_decrypt(self, cipher):
        other_cipher = KeyCipher(generate_key())
        encrypted = cipher.encrypt("sk-test-key")
        with pytest.raises(Exception):
            other_cipher.decrypt(encrypted)

    def test_tampered_ciphertext_raises(self, cipher):
        encrypted = cipher.encrypt("sk-test-key")
        tampered = encrypted[:-4] + "AAAA"
        with pytest.raises(Exception):
            cipher.decrypt(tampered)


class TestGenerateKey:
    def test_generate_key_returns_string(self):
        key = generate_key()
        assert isinstance(key, str)
        assert len(key) > 0

    def test_generate_key_is_random(self):
        keys = {generate_key() for _ in range(10)}
        assert len(keys) == 10
