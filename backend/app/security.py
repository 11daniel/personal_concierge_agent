import base64
from datetime import datetime, timedelta
from typing import Dict
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from jose import jwt, JWTError

from app.config import JWT_SECRET, JWT_ALGORITHM, APP_ENCRYPTION_SALT

import bcrypt

# Cache for derived household encryption keys to avoid PBKDF2 overhead on every request
_fernet_cache: Dict[str, Fernet] = {}

def get_password_hash(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        return {}

def get_household_cipher(household_salt: str) -> Fernet:
    """
    Derives an AES key using the household salt combined with the app master key,
    and returns a Fernet cipher instance. Results are cached in-memory.
    """
    if household_salt in _fernet_cache:
        return _fernet_cache[household_salt]

    # Derive a key from the household salt and application salt
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=household_salt.encode(),
        iterations=10000, # Kept reasonable for MVP performance
    )
    key = base64.urlsafe_b64encode(kdf.derive(APP_ENCRYPTION_SALT.encode()))
    cipher = Fernet(key)
    _fernet_cache[household_salt] = cipher
    return cipher

def encrypt_value(value: str, household_salt: str) -> str:
    """Encrypts a string value using the household key and returns a base64 string."""
    if not value:
        return value
    cipher = get_household_cipher(household_salt)
    return cipher.encrypt(value.encode()).decode()

def decrypt_value(encrypted_value: str, household_salt: str) -> str:
    """Decrypts a base64 encrypted string using the household key."""
    if not encrypted_value:
        return encrypted_value
    cipher = get_household_cipher(household_salt)
    try:
        return cipher.decrypt(encrypted_value.encode()).decode()
    except Exception:
        # Fallback in case of decryption failure (e.g. key mismatch)
        return "[Decryption Error]"
