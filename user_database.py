import sqlite3
from pathlib import Path
import bcrypt
import time

from defs import BASE_DELAY, MAX_RETRIES

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
    
    for attempt in range(MAX_RETRIES):
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
            if "locked" in str(e).lower() and attempt < MAX_RETRIES - 1:
                wait_time = BASE_DELAY * (2 ** attempt)  # Exponential backoff: 0.1s, 0.2s, 0.4s, 0.8s, 1.6s
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
        assigned_vendor_id INTEGER,
        is_active BOOLEAN DEFAULT 1,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        last_login DATETIME,
        password_reset_token TEXT,
        token_expiry DATETIME
    )
    """)

    conn.commit()
    conn.close()
    
    # Create default admin user if none exists
    # For testing purposes only. Remove when deploying to production.
    admin_exists = _execute_select_one("SELECT id FROM users WHERE username = ?", ("admin",))
    if not admin_exists:
        create_user(
            username="admin",
            email="admin@admin.com",
            password="admin123",
            full_name="Administrator",
            role="admin"
        )


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


def create_user(
    username: str,
    email: str,
    password: str,
    full_name: str = None,
    role: str = "viewer",
    assigned_vendor_id: int | None = None,
) -> int | None:
    """Create a new user account.

    Args:
        username (str): Unique username.
        email (str): Unique email address.
        password (str): Plain text password (will be hashed).
        full_name (str): User's full name (optional).
        role (str): User role - "admin", "analyst", "client", or "viewer" (default: "viewer").
        assigned_vendor_id (int | None): Vendor ID the user is restricted to (client users).

    Returns:
        int | None: Newly created user ID, or None if creation failed.
    """
    from backend.models import UserRole
    
    # Validate role
    valid_roles = [r.value for r in UserRole]
    if role not in valid_roles:
        print(f"❌ Invalid role: {role}. Must be one of: {', '.join(valid_roles)}")
        return None

    # client users must have a valid assigned vendor
    if role == UserRole.CLIENT.value:
        if assigned_vendor_id is None:
            print("❌ client users must have an assigned_vendor_id")
            return None

        from backend.vendor_database import get_vendor_model_by_id
        if get_vendor_model_by_id(assigned_vendor_id) is None:
            print(f"❌ Vendor with id={assigned_vendor_id} does not exist")
            return None
    else:
        assigned_vendor_id = None
    
    password_hash = hash_password(password)
    
    try:
        user_id = _execute_update(
            """
            INSERT INTO users (username, email, password_hash, full_name, role, assigned_vendor_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (username, email, password_hash, full_name, role, assigned_vendor_id)
        )
        print(
            f"User created: {username} (ID: {user_id}, Role: {role}, Assigned Vendor: {assigned_vendor_id})"
        )
        return user_id
    except sqlite3.IntegrityError:
        print(f"User creation failed: Username or email already exists")
        return None


def authenticate_user(username: str, password: str) -> User | None:
    """Authenticate a user and return typed User object."""
    query = """SELECT id, username, email, full_name, role, assigned_vendor_id, is_active, created_at, last_login, password_hash 
               FROM users WHERE username = ?"""
    row = _execute_select_one(query, (username,), use_row_factory=True)
    
    if not row:
        return None
    
    password_hash = row['password_hash']
    if not verify_password(password, password_hash):
        return None
    
    # Convert row to User model
    return User(
        id=row['id'],
        username=row['username'],
        email=row['email'],
        full_name=row['full_name'],
        role=UserRole(row['role']),  # Convert string to enum
        assigned_vendor_id=row['assigned_vendor_id'],
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


def get_user_display_name(user_id: int) -> str:
    """Get the display name for a user.

    Args:
        user_id (int): User identifier.

    Returns:
        str: User's full name if available, otherwise username, or "Unknown User" if not found.
    """
    user = get_user_by_id(user_id)
    if not user:
        return "Unknown User"
    
    # Prefer full_name if available, otherwise use username
    return user['full_name'] if user['full_name'] else user['username']


def get_all_users() -> list[User]:
    """Fetch all users with all their information.

    Returns:
        list[User]: List of User model objects, or empty list if no users found.
    """
    query = """SELECT id, username, email, full_name, role, assigned_vendor_id, is_active, created_at, last_login
               FROM users ORDER BY created_at DESC"""
    rows = _execute_select(query, use_row_factory=True)
    
    users = []
    for row in rows:
        user = User(
            id=row['id'],
            username=row['username'],
            email=row['email'],
            full_name=row['full_name'],
            role=UserRole(row['role']),
            assigned_vendor_id=row['assigned_vendor_id'],
            is_active=row['is_active'],
            created_at=row['created_at'],
            last_login=row['last_login'],
        )
        users.append(user)
    
    return users


def delete_user(user_id: int) -> bool:
    """Delete a user by their ID.

    Args:
        user_id (int): User ID to delete.

    Returns:
        bool: True if deletion succeeded, False otherwise.
    """
    try:
        # Check if user exists
        user = get_user_by_id(user_id)
        if not user:
            print(f"❌ User with ID {user_id} not found")
            return False
        
        # Delete the user
        rows_affected = _execute_update(
            "DELETE FROM users WHERE id = ?",
            (user_id,)
        )
        
        if rows_affected > 0:
            print(f"User deleted: {user['username']} (ID: {user_id})")
            return True
        else:
            print(f"Failed to delete user with ID {user_id}")
            return False
            
    except sqlite3.Error as e:
        print(f"Database error while deleting user: {e}")
        return False


def update_user_role(user_id: int, new_role: str) -> bool:
    """Update a user's role.

    Args:
        user_id (int): User ID to update.
        new_role (str): New role to assign ("admin", "analyst", "client", or "viewer").

    Returns:
        bool: True if update succeeded, False otherwise.
    """
    try:
        # Validate role
        valid_roles = [r.value for r in UserRole]
        if new_role not in valid_roles:
            print(f"Invalid role: {new_role}. Must be one of: {', '.join(valid_roles)}")
            return False
        
        # Check if user exists
        user = get_user_by_id(user_id)
        if not user:
            print(f"User with ID {user_id} not found")
            return False
        
        # Update the user's role
        rows_affected = _execute_update(
            "UPDATE users SET role = ? WHERE id = ?",
            (new_role, user_id)
        )
        
        if rows_affected > 0:
            print(f"User role updated: {user['username']} (ID: {user_id}) -> {new_role}")
            return True
        else:
            print(f"Failed to update user role with ID {user_id}")
            return False
            
    except sqlite3.Error as e:
        print(f"Database error while updating user role: {e}")
        return False


def update_user_assigned_vendor(user_id: int, vendor_id: int | None) -> bool:
    """Update a user's assigned vendor.

    Args:
        user_id (int): User ID to update.
        vendor_id (int | None): Vendor ID to assign, or None to unassign.

    Returns:
        bool: True if update succeeded, False otherwise.
    """
    try:
        # Check if user exists
        user = get_user_by_id(user_id)
        if not user:
            print(f"User with ID {user_id} not found")
            return False
        
        # Update the user's assigned vendor
        rows_affected = _execute_update(
            "UPDATE users SET assigned_vendor_id = ? WHERE id = ?",
            (vendor_id, user_id)
        )
        
        if rows_affected > 0:
            vendor_desc = f"Vendor {vendor_id}" if vendor_id else "None"
            print(f"User assigned vendor updated: {user['username']} (ID: {user_id}) -> {vendor_desc}")
            return True
        else:
            print(f"Failed to update user assigned vendor with ID {user_id}")
            return False
            
    except sqlite3.Error as e:
        print(f"Database error while updating user assigned vendor: {e}")
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
            print(f"Role: {row['role']}")
            print(f"Assigned Vendor ID: {row['assigned_vendor_id'] if row['assigned_vendor_id'] is not None else 'N/A'}")
            print(f"Active: {'Yes' if row['is_active'] else 'No'}")
            print(f"Created: {row['created_at']}")
            print(f"Last Login: {row['last_login'] or 'Never'}")
            print("-" * 120)
            
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    # Initialize the database
    init_user_db()
    
    # Print all users
    print_users_table()
