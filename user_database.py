import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
import secrets
import bcrypt
import time
from backend.models import User, UserRole

BACKEND_DIR = Path(__file__).resolve().parent
STORAGE_DIR = BACKEND_DIR / "Storage"

DB_PATH = STORAGE_DIR / "users.db"


def _execute_select(query: str, params: tuple = (), use_row_factory: bool = False) -> list:
    """Execute a SELECT query and return all rows.

    Args:
        query (str): SQL SELECT query.
        params (tuple): Query parameters.
        use_row_factory (bool): Whether to use sqlite3.Row for column access.

    Returns:
        list: List of query results (rows or tuples).
    """
    conn = sqlite3.connect(DB_PATH)
    if use_row_factory:
        conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"❌ User Database error: {e}")
        return []
    finally:
        conn.close()


def _execute_select_one(query: str, params: tuple = (), use_row_factory: bool = False):
    """Execute a SELECT query and return a single row.

    Args:
        query (str): SQL SELECT query.
        params (tuple): Query parameters.
        use_row_factory (bool): Whether to use sqlite3.Row for column access.

    Returns:
        Single row result or None.
    """
    conn = sqlite3.connect(DB_PATH)
    if use_row_factory:
        conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        return cursor.fetchone()
    except sqlite3.Error as e:
        print(f"❌ User Database error: {e}")
        return None
    finally:
        conn.close()


def _execute_update(query: str, params: tuple = ()) -> int:
    """Execute an INSERT, UPDATE, or DELETE query with exponential backoff retry.
    
    Implements retry logic for database locks that occur under concurrent write load.

    Args:
        query (str): SQL DML query.
        params (tuple): Query parameters.

    Returns:
        int: Number of rows affected (or lastrowid for INSERT).
        
    Raises:
        sqlite3.OperationalError: If database is locked after all retries exhausted.
    """
    max_retries = 5
    base_delay = 0.1  # 100ms base delay
    
    for attempt in range(max_retries):
        try:
            conn = sqlite3.connect(DB_PATH, timeout=5.0)
            cursor = conn.cursor()
            try:
                cursor.execute(query, params)
                conn.commit()
                return cursor.lastrowid if "INSERT" in query.upper() else cursor.rowcount
            finally:
                conn.close()
        except sqlite3.OperationalError as e:
            # If database is locked and we haven't exhausted retries, wait and retry
            if "locked" in str(e).lower() and attempt < max_retries - 1:
                wait_time = base_delay * (2 ** attempt)  # Exponential backoff: 0.1s, 0.2s, 0.4s, 0.8s, 1.6s
                time.sleep(wait_time)
            else:
                # Either not a lock error, or we've exhausted retries
                raise


def init_user_db() -> None:
    """Initialize SQLite user database with role-based access control."""
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Enable WAL mode for better concurrent write handling
    cursor.execute("PRAGMA journal_mode=WAL")
    
    # Create users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        full_name TEXT,
        role TEXT NOT NULL DEFAULT 'viewer',
        is_active BOOLEAN DEFAULT 1,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        last_login DATETIME,
        password_reset_token TEXT,
        token_expiry DATETIME
    )
    """)
    
    # Migration: if is_admin column exists, convert to role field
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]
    if "is_admin" in columns:
        cursor.execute("""
            ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'viewer'
        """)
        cursor.execute("""
            UPDATE users SET role = 'admin' WHERE is_admin = 1
        """)
        # Note: can't drop is_admin in SQLite, but it's now redundant
    
    conn.commit()
    conn.close()


def hash_password(password: str) -> str:
    """Hash a password using bcrypt.

    Args:
        password (str): Plain text password.

    Returns:
        str: Hashed password.
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash.

    Args:
        password (str): Plain text password to verify.
        password_hash (str): Stored password hash.

    Returns:
        bool: True if password matches, False otherwise.
    """
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))


def create_user(username: str, email: str, password: str, full_name: str = None, is_admin: bool = False) -> int | None:
    """Create a new user account.

    Args:
        username (str): Unique username.
        email (str): Unique email address.
        password (str): Plain text password (will be hashed).
        full_name (str): User's full name (optional).
        is_admin (bool): Whether user has admin privileges.

    Returns:
        int | None: Newly created user ID, or None if creation failed.
    """
    password_hash = hash_password(password)
    
    try:
        user_id = _execute_update(
            """
            INSERT INTO users (username, email, password_hash, full_name, is_admin)
            VALUES (?, ?, ?, ?, ?)
            """,
            (username, email, password_hash, full_name, is_admin)
        )
        print(f"✅ User created: {username} (ID: {user_id})")
        return user_id
    except sqlite3.IntegrityError:
        print(f"❌ User creation failed: Username or email already exists")
        return None


def authenticate_user(username: str, password: str) -> User | None:
    """Authenticate a user and return typed User object."""
    query = """SELECT id, username, email, full_name, role, is_active, created_at, last_login 
               FROM users WHERE username = ?"""
    row = _execute_select_one(query, (username,), use_row_factory=True)
    
    if not row:
        return None
    
    password_hash = row['password_hash']  # Get hash in separate query
    if not verify_password(password, password_hash):
        return None
    
    # Convert row to User model
    return User(
        id=row['id'],
        username=row['username'],
        email=row['email'],
        full_name=row['full_name'],
        role=UserRole(row['role']),  # Convert string to enum
        is_active=row['is_active'],
        created_at=row['created_at'],
        last_login=row['last_login'],
    )


def get_user_by_id(user_id: int) -> sqlite3.Row | None:
    """Fetch a user by their ID.

    Args:
        user_id (int): User identifier.

    Returns:
        sqlite3.Row | None: User row, or None if not found.
    """
    return _execute_select_one(
        "SELECT * FROM users WHERE id = ?",
        (user_id,),
        use_row_factory=True
    )


def get_user_by_username(username: str) -> sqlite3.Row | None:
    """Fetch a user by their username.

    Args:
        username (str): Username to search for.

    Returns:
        sqlite3.Row | None: User row, or None if not found.
    """
    return _execute_select_one(
        "SELECT * FROM users WHERE username = ?",
        (username,),
        use_row_factory=True
    )


def get_user_by_email(email: str) -> sqlite3.Row | None:
    """Fetch a user by their email address.

    Args:
        email (str): Email address to search for.

    Returns:
        sqlite3.Row | None: User row, or None if not found.
    """
    return _execute_select_one(
        "SELECT * FROM users WHERE email = ?",
        (email,),
        use_row_factory=True
    )


def get_all_users() -> list[sqlite3.Row]:
    """Fetch all users ordered by creation date (newest first).

    Returns:
        list[sqlite3.Row]: Collection of user rows.
    """
    return _execute_select(
        "SELECT * FROM users ORDER BY created_at DESC",
        use_row_factory=True
    )


def update_user(user_id: int, username: str = None, email: str = None, full_name: str = None) -> bool:
    """Update user information.

    Args:
        user_id (int): User identifier.
        username (str): New username (optional).
        email (str): New email (optional).
        full_name (str): New full name (optional).

    Returns:
        bool: True if update successful, False otherwise.
    """
    # Build dynamic update query based on provided fields
    updates = []
    params = []
    
    if username is not None:
        updates.append("username = ?")
        params.append(username)
    if email is not None:
        updates.append("email = ?")
        params.append(email)
    if full_name is not None:
        updates.append("full_name = ?")
        params.append(full_name)
    
    if not updates:
        return False
    
    params.append(user_id)
    query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
    
    try:
        _execute_update(query, tuple(params))
        return True
    except sqlite3.IntegrityError:
        print(f"❌ Update failed: Username or email already exists")
        return False


def update_password(user_id: int, new_password: str) -> bool:
    """Update a user's password.

    Args:
        user_id (int): User identifier.
        new_password (str): New plain text password (will be hashed).

    Returns:
        bool: True if update successful, False otherwise.
    """
    password_hash = hash_password(new_password)
    rows_affected = _execute_update(
        "UPDATE users SET password_hash = ?, password_reset_token = NULL, token_expiry = NULL WHERE id = ?",
        (password_hash, user_id)
    )
    return rows_affected > 0


def set_user_active_status(user_id: int, is_active: bool) -> bool:
    """Activate or deactivate a user account.

    Args:
        user_id (int): User identifier.
        is_active (bool): Whether user should be active.

    Returns:
        bool: True if update successful, False otherwise.
    """
    rows_affected = _execute_update(
        "UPDATE users SET is_active = ? WHERE id = ?",
        (is_active, user_id)
    )
    return rows_affected > 0


def set_user_admin_status(user_id: int, is_admin: bool) -> bool:
    """Grant or revoke admin privileges for a user.

    Args:
        user_id (int): User identifier.
        is_admin (bool): Whether user should be an admin.

    Returns:
        bool: True if update successful, False otherwise.
    """
    rows_affected = _execute_update(
        "UPDATE users SET is_admin = ? WHERE id = ?",
        (is_admin, user_id)
    )
    return rows_affected > 0


def create_password_reset_token(email: str, expiry_hours: int = 24) -> str | None:
    """Create a password reset token for a user.

    Args:
        email (str): User's email address.
        expiry_hours (int): Hours until token expires (default: 24).

    Returns:
        str | None: Reset token if successful, None if user not found.
    """
    user = get_user_by_email(email)
    if not user:
        return None
    
    # Generate a secure random token
    token = secrets.token_urlsafe(32)
    expiry = datetime.now() + timedelta(hours=expiry_hours)
    
    _execute_update(
        "UPDATE users SET password_reset_token = ?, token_expiry = ? WHERE id = ?",
        (token, expiry.isoformat(), user['id'])
    )
    
    return token


def validate_password_reset_token(token: str) -> sqlite3.Row | None:
    """Validate a password reset token and return the user if valid.

    Args:
        token (str): Password reset token to validate.

    Returns:
        sqlite3.Row | None: User row if token is valid, None otherwise.
    """
    user = _execute_select_one(
        "SELECT * FROM users WHERE password_reset_token = ?",
        (token,),
        use_row_factory=True
    )
    
    if not user or not user['token_expiry']:
        return None
    
    # Check if token has expired
    expiry = datetime.fromisoformat(user['token_expiry'])
    if datetime.now() > expiry:
        # Token expired, clear it
        _execute_update(
            "UPDATE users SET password_reset_token = NULL, token_expiry = NULL WHERE id = ?",
            (user['id'],)
        )
        return None
    
    return user


def delete_user(user_id: int) -> bool:
    """Delete a user account.

    Args:
        user_id (int): User identifier to delete.

    Returns:
        bool: True if deletion successful, False otherwise.
    """
    rows_affected = _execute_update(
        "DELETE FROM users WHERE id = ?",
        (user_id,)
    )
    
    if rows_affected > 0:
        print(f"🗑️ Deleted user ID: {user_id}")
        return True
    return False


def print_users_table() -> None:
    """Print a formatted console view of all users for debugging."""
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM users")
        rows = cursor.fetchall()
        
        if not rows:
            print("\n📭 No users found.")
            return

        print("\n" + "="*120)
        print("USERS TABLE")
        print("="*120)

        for row in rows:
            print(f"\nID: {row['id']}")
            print(f"Username: {row['username']}")
            print(f"Email: {row['email']}")
            print(f"Full Name: {row['full_name'] or 'N/A'}")
            print(f"Active: {'Yes' if row['is_active'] else 'No'}")
            print(f"Admin: {'Yes' if row['is_admin'] else 'No'}")
            print(f"Created: {row['created_at']}")
            print(f"Last Login: {row['last_login'] or 'Never'}")
            print("-" * 120)
            
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
    finally:
        conn.close()


def cleanup_user_database() -> None:
    """Remove all user rows from the database."""

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM users")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='users'")
        conn.commit()

        print("🧹 User database wiped clean!")

    except sqlite3.Error as e:
        print(f"❌ Error during cleanup: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    # Initialize the database
    init_user_db()
    
    # Example: Create a test user
    # create_user("admin", "admin@example.com", "admin123", "Administrator", is_admin=True)
    
    # Print all users
    print_users_table()
