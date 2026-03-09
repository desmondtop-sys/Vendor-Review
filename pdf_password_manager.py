"""Secure password storage for PDF documents.

Stores encrypted passwords for locked PDFs so users don't need to re-enter them
every time they generate a report.
"""

import json
import os
from pathlib import Path
from cryptography.fernet import Fernet

BACKEND_DIR = Path(__file__).resolve().parent
STORAGE_DIR = BACKEND_DIR / "Storage"

# Initialize encryption key
ENCRYPTION_KEY_FILE = STORAGE_DIR / ".encryption_key"

def _get_or_create_encryption_key() -> bytes:
    """Get or create the encryption key for storing passwords.
    
    Returns:
        bytes: The encryption key (Fernet key)
    """
    if ENCRYPTION_KEY_FILE.exists():
        with open(ENCRYPTION_KEY_FILE, 'rb') as f:
            return f.read()
    else:
        # Generate a new key
        key = Fernet.generate_key()
        STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        with open(ENCRYPTION_KEY_FILE, 'wb') as f:
            f.write(key)
        # Protect file from other users (Unix only)
        try:
            os.chmod(ENCRYPTION_KEY_FILE, 0o600)
        except:
            pass
        return key

def _encrypt_password(password: str) -> str:
    """Encrypt a password using Fernet symmetric encryption.
    
    Args:
        password (str): Plain text password to encrypt
        
    Returns:
        str: Encrypted password as a hex string
    """
    key = _get_or_create_encryption_key()
    cipher = Fernet(key)
    encrypted = cipher.encrypt(password.encode())
    return encrypted.hex()

def _decrypt_password(encrypted_password: str) -> str:
    """Decrypt an encrypted password.
    
    Args:
        encrypted_password (str): Encrypted password as hex string
        
    Returns:
        str: Decrypted plain text password
    """
    key = _get_or_create_encryption_key()
    cipher = Fernet(key)
    decrypted = cipher.decrypt(bytes.fromhex(encrypted_password))
    return decrypted.decode()

def save_pdf_passwords(vendor_id: int, passwords: dict) -> None:
    """Save encrypted passwords for a vendor's PDFs.
    
    Args:
        vendor_id (int): The vendor ID
        passwords (dict): Dictionary mapping filenames to passwords
    """
    if not passwords:
        return
    
    vendor_dir = STORAGE_DIR / str(vendor_id)
    vendor_dir.mkdir(parents=True, exist_ok=True)
    
    passwords_file = vendor_dir / ".pdf_passwords.json"
    
    # Encrypt all passwords
    encrypted_passwords = {
        filename: _encrypt_password(password)
        for filename, password in passwords.items()
    }
    
    # Save to JSON file
    with open(passwords_file, 'w') as f:
        json.dump(encrypted_passwords, f)
    
    # Protect file from other users (Unix only)
    try:
        os.chmod(passwords_file, 0o600)
    except:
        pass
    
    print(f"✅ Saved passwords for {len(passwords)} PDFs in vendor {vendor_id}")

def load_pdf_passwords(vendor_id: int) -> dict:
    """Load and decrypt saved passwords for a vendor's PDFs.
    
    Args:
        vendor_id (int): The vendor ID
        
    Returns:
        dict: Dictionary mapping filenames to decrypted passwords
    """
    vendor_dir = STORAGE_DIR / str(vendor_id)
    passwords_file = vendor_dir / ".pdf_passwords.json"
    
    if not passwords_file.exists():
        return {}
    
    try:
        with open(passwords_file, 'r') as f:
            encrypted_passwords = json.load(f)
        
        # Decrypt all passwords
        decrypted_passwords = {
            filename: _decrypt_password(encrypted_password)
            for filename, encrypted_password in encrypted_passwords.items()
        }
        
        return decrypted_passwords
    
    except Exception as e:
        print(f"⚠️ Error loading saved passwords for vendor {vendor_id}: {e}")
        return {}

def delete_pdf_passwords(vendor_id: int, filenames: list[str] | None = None) -> None:
    """Delete saved passwords for specific PDFs or all PDFs in a vendor.
    
    Args:
        vendor_id (int): The vendor ID
        filenames (list[str] | None): Specific filenames to delete. If None, delete all.
    """
    vendor_dir = STORAGE_DIR / str(vendor_id)
    passwords_file = vendor_dir / ".pdf_passwords.json"
    
    if not passwords_file.exists():
        return
    
    try:
        with open(passwords_file, 'r') as f:
            encrypted_passwords = json.load(f)
        
        if filenames is None:
            # Delete all passwords
            passwords_file.unlink()
            print(f"✅ Deleted all saved passwords for vendor {vendor_id}")
        else:
            # Delete specific passwords
            for filename in filenames:
                encrypted_passwords.pop(filename, None)
            
            if encrypted_passwords:
                # Update file if there are still passwords left
                with open(passwords_file, 'w') as f:
                    json.dump(encrypted_passwords, f)
            else:
                # Delete file if no passwords left
                passwords_file.unlink()
            
            print(f"✅ Deleted passwords for {len(filenames)} PDFs in vendor {vendor_id}")
    
    except Exception as e:
        print(f"❌ Error deleting passwords for vendor {vendor_id}: {e}")

def get_saved_pdf_filenames(vendor_id: int) -> list[str]:
    """Get list of PDFs with saved passwords.
    
    Args:
        vendor_id (int): The vendor ID
        
    Returns:
        list[str]: List of filenames with saved passwords
    """
    vendor_dir = STORAGE_DIR / str(vendor_id)
    passwords_file = vendor_dir / ".pdf_passwords.json"
    
    if not passwords_file.exists():
        return []
    
    try:
        with open(passwords_file, 'r') as f:
            encrypted_passwords = json.load(f)
        return list(encrypted_passwords.keys())
    except:
        return []
