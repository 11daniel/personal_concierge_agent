import pytest
from app.security import encrypt_value, decrypt_value, get_household_cipher

def test_encryption_roundtrip():
    salt = "household-salt-1"
    secret_text = "Advil 200mg daily dose"

    # Encrypt
    encrypted = encrypt_value(secret_text, salt)
    assert encrypted != secret_text
    assert len(encrypted) > 20

    # Decrypt
    decrypted = decrypt_value(encrypted, salt)
    assert decrypted == secret_text

def test_encryption_isolation():
    salt_a = "salt-household-a"
    salt_b = "salt-household-b"
    secret_text = "Sensitive medical data"

    # Encrypt with A
    enc_a = encrypt_value(secret_text, salt_a)
    
    # Decrypt with B (should fail or return error message)
    dec_b = decrypt_value(enc_a, salt_b)
    assert dec_b == "[Decryption Error]"
    
    # Decrypt with A (should succeed)
    dec_a = decrypt_value(enc_a, salt_a)
    assert dec_a == secret_text
