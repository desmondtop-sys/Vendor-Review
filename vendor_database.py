import os
import shutil
import sqlite3
from pathlib import Path
import json
import time

from defs import BASE_DELAY, MAX_RETRIES

try:
    from backend.models import SecurityControl, Report, Vendor, DataType
except ModuleNotFoundError:
    from models import SecurityControl, Report, Vendor

BACKEND_DIR = Path(__file__).resolve().parent
STORAGE_DIR = BACKEND_DIR / "Storage"

DB_PATH = STORAGE_DIR / "vendors.db"


def get_vendor_documents_path(vendor_id: int) -> Path:
    """Get the documents folder path for a vendor.

    Args:
        vendor_id (int): Vendor identifier.

    Returns:
        Path: Path to the vendor's documents folder.
    """
    return STORAGE_DIR / str(vendor_id) / "documents"


def get_vendor_reports_path(vendor_id: int) -> Path:
    """Get the reports folder path for a vendor.

    Args:
        vendor_id (int): Vendor identifier.

    Returns:
        Path: Path to the vendor's reports folder.
    """
    return STORAGE_DIR / str(vendor_id) / "reports"


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
        print(f"❌ Database error: {e}")
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
        print(f"❌ Database error: {e}")
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
    # SQLite allows only one writer at a time; short lock windows are expected
    # under concurrent actions, so we retry writes with exponential backoff.
    
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
                print(f"⏳ Database locked, retrying in {wait_time:.2f}s (attempt {attempt + 1}/{MAX_RETRIES})")
                time.sleep(wait_time)
            else:
                # Either not a lock error, or we've exhausted retries
                raise


def init_db() -> None:
    """Initialize SQLite storage and ensure vendors and reports tables exist.
    
    Enables WAL mode for better concurrent write performance.
    """

    # Ensure the storage directory exists before we try to create folders in it
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Enable WAL mode for better concurrent write handling
    cursor.execute("PRAGMA journal_mode=WAL")
    
    # Create vendors table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vendors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        active_report_id INTEGER,
        max_run_number INTEGER DEFAULT 0,
        nda_signed INTEGER NOT NULL DEFAULT 0,
        bitsight_company_guid TEXT,
        bitsight_company_name TEXT,
        bitsight_rating INTEGER,
        bitsight_rating_date TEXT,
        website_URL TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Create vendor_reports table with vendor_id foreign key
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vendor_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vendor_id INTEGER,
        run_number INTEGER,
        version INTEGER DEFAULT 1,
        prompt TEXT,
        vendor_name TEXT NOT NULL,
        overall_score INTEGER,
        possible_score INTEGER,
        summary TEXT,
        data_type TEXT DEFAULT 'Restricted',
        controls_json TEXT,
        file_list_json TEXT,
        storage_path TEXT,
        excluded_json TEXT,
        runtime REAL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (vendor_id) REFERENCES vendors(id)
    )
    """)
    
    # Add unique constraint on (vendor_id, run_number) to prevent duplicate report versions
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_vendor_run_unique ON vendor_reports(vendor_id, run_number)")
    
    conn.commit()
    
    conn.close()


def create_vendor(name: str) -> int:
    """Create a new vendor record and documents folder.

    Args:
        name (str): Vendor name.

    Returns:
        int: Newly created vendor ID.
    """
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check if name already exists and generate a unique one if needed
        original_name = name
        counter = 0 if name != "New Vendor" else 1
        
        while True:
            if counter > 0:
                name = f"{original_name} {counter}"
            try:
                cursor.execute("INSERT INTO vendors (name) VALUES (?)", (name,))
                break  # Success, exit loop
            except sqlite3.IntegrityError:
                # Name already exists, try with a counter
                counter += 1
                name = f"{original_name} {counter}"
        
        vendor_id = cursor.lastrowid
        conn.commit()
        
        # Create documents folder for this vendor
        documents_path = get_vendor_documents_path(vendor_id)
        documents_path.mkdir(parents=True, exist_ok=True)
        
        return vendor_id
    finally:
        conn.close()


def get_all_vendors() -> list[sqlite3.Row]:
    """Fetch all vendors ordered by creation date (newest first).

    Returns:
        list[sqlite3.Row]: Collection of vendor rows.
    """
    return _execute_select("SELECT * FROM vendors ORDER BY id DESC", use_row_factory=True)


def get_vendor_by_id(vendor_id: int) -> sqlite3.Row | None:
    """Fetch a vendor row by ID.

    Args:
        vendor_id (int): Vendor identifier.

    Returns:
        sqlite3.Row | None: Vendor row, or None if not found.
    """
    return _execute_select_one(
        "SELECT * FROM vendors WHERE id = ?",
        (vendor_id,),
        use_row_factory=True,
    )


def generate_vendor_from_db(db_vendor: sqlite3.Row | dict) -> Vendor:
    """Convert a raw database row into a Vendor model instance.

    Args:
        db_vendor (sqlite3.Row | dict): Database row for a vendor.

    Returns:
        Vendor: Hydrated vendor object.
    """
    return Vendor(
        id=db_vendor["id"],
        name=db_vendor["name"],
        nda_signed=bool(db_vendor["nda_signed"]) if "nda_signed" in db_vendor.keys() else False,
        active_report_id=db_vendor["active_report_id"] if "active_report_id" in db_vendor.keys() else None,
        max_run_number=int(db_vendor["max_run_number"]) if "max_run_number" in db_vendor.keys() and db_vendor["max_run_number"] is not None else 0,
        bitsight_company_guid=db_vendor["bitsight_company_guid"] if "bitsight_company_guid" in db_vendor.keys() else None,
        bitsight_company_name=db_vendor["bitsight_company_name"] if "bitsight_company_name" in db_vendor.keys() else None,
        bitsight_rating=db_vendor["bitsight_rating"] if "bitsight_rating" in db_vendor.keys() else None,
        bitsight_rating_date=db_vendor["bitsight_rating_date"] if "bitsight_rating_date" in db_vendor.keys() else None,
        website_URL=db_vendor["website_URL"] if "website_URL" in db_vendor.keys() else None,
        created_at=db_vendor["created_at"] if "created_at" in db_vendor.keys() else None,
    )


def get_vendor_model_by_id(vendor_id: int) -> Vendor | None:
    """Fetch a vendor by ID as a typed Vendor model.

    Args:
        vendor_id (int): Vendor identifier.

    Returns:
        Vendor | None: Vendor model, or None if not found.
    """
    row = get_vendor_by_id(vendor_id)
    return generate_vendor_from_db(row) if row else None


def get_all_vendor_models() -> list[Vendor]:
    """Fetch all vendors as typed Vendor models.

    Returns:
        list[Vendor]: Collection of vendor models.
    """
    rows = get_all_vendors()
    return [generate_vendor_from_db(row) for row in rows]


def update_vendor(vendor_id: int, name: str) -> None:
    """Update a vendor's name.

    Args:
        vendor_id (int): Vendor identifier.
        name (str): New vendor name.
    """
    _execute_update(
        "UPDATE vendors SET name = ? WHERE id = ?",
        (name, vendor_id)
    )


def update_vendor_website_url(vendor_id: int, website_url: str | None) -> None:
    """Update a vendor's website URL.

    Args:
        vendor_id (int): Vendor identifier.
        website_url (str | None): Website URL or None to clear.
    """
    _execute_update(
        "UPDATE vendors SET website_URL = ? WHERE id = ?",
        (website_url, vendor_id)
    )


def set_vendor_nda_signed(vendor_id: int, nda_signed: bool) -> None:
    """Update NDA signed status for a vendor.

    Args:
        vendor_id (int): Vendor identifier.
        nda_signed (bool): True when NDA is signed, False otherwise.
    """
    _execute_update(
        "UPDATE vendors SET nda_signed = ? WHERE id = ?",
        (1 if nda_signed else 0, vendor_id)
    )


def update_vendor_bitsight(
    vendor_id: int,
    company_guid: str | None = None,
    company_name: str | None = None,
    rating: int | None = None,
    rating_date: str | None = None,
) -> None:
    """Update a vendor's Bitsight metadata.

    Args:
        vendor_id (int): Vendor identifier.
        company_guid (str | None): Bitsight company GUID.
        company_name (str | None): Bitsight company name.
        rating (int | None): Bitsight rating value.
        rating_date (str | None): Rating effective date.
    """
    _execute_update(
        """
        UPDATE vendors
        SET bitsight_company_guid = ?,
            bitsight_company_name = ?,
            bitsight_rating = ?,
            bitsight_rating_date = ?
        WHERE id = ?
        """,
        (company_guid, company_name, rating, rating_date, vendor_id),
    )

def set_active_report_for_vendor(vendor_id: int, report_id: int | None) -> None:
    """Save the active report ID for a vendor.

    Args:
        vendor_id (int): Vendor identifier.
        report_id (int | None): Report ID to save as active, or None to clear.
    """
    _execute_update(
        "UPDATE vendors SET active_report_id = ? WHERE id = ?",
        (report_id, vendor_id)
    )


def get_active_report_for_vendor(vendor_id: int) -> int | None:
    """Get the saved active report ID for a vendor.

    Args:
        vendor_id (int): Vendor identifier.

    Returns:
        int | None: The active report ID, or None if not set.
    """
    row = _execute_select_one(
        "SELECT active_report_id FROM vendors WHERE id = ?",
        (vendor_id,)
    )
    return row[0] if row and row[0] else None


def create_report_for_vendor(vendor_id: int) -> int:
    """Create a new blank report for a vendor with retry logic for concurrent creation.

    Args:
        vendor_id (int): Vendor identifier.

    Returns:
        int: Newly created report ID.
    """
    # Creating reports also increments per-vendor run_number; concurrent creates
    # can race, so retry on transient failures / uniqueness conflicts.
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    attempt = 0
    
    while attempt < MAX_RETRIES:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        try:
            # Get vendor info and increment max_run_number
            cursor.execute("SELECT name, max_run_number FROM vendors WHERE id = ?", (vendor_id,))
            vendor_row = cursor.fetchone()
            if not vendor_row:
                return None

            vendor_name = vendor_row[0]
            run_number = (vendor_row[1] or 0) + 1
            
            # Update the vendor's max_run_number
            cursor.execute(
                "UPDATE vendors SET max_run_number = ? WHERE id = ?",
                (run_number, vendor_id)
            )

            # Default values for a new assessment
            prompt = ""
            overall_score = 0
            possible = 100
            summary = "Click Generate Report to create a report."
            controls_json = json.dumps([])
            file_list_json = json.dumps([])
            excluded_json = json.dumps([])

            cursor.execute(
                """
                INSERT INTO vendor_reports 
                (vendor_id, run_number, prompt, vendor_name, overall_score, possible_score, 
                 summary, data_type, controls_json, file_list_json, excluded_json, runtime)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    vendor_id,
                    run_number,
                    prompt,
                    vendor_name,
                    overall_score,
                    possible,
                    summary,
                    "Restricted",
                    controls_json,
                    file_list_json,
                    excluded_json,
                    None,
                ),
            )

            report_id = cursor.lastrowid

            # Create folder using vendor ID and run number for organization
            # Storage/{vendor_id}/reports/{run_number}/
            vendor_reports_folder = get_vendor_reports_path(vendor_id)
            vendor_reports_folder.mkdir(parents=True, exist_ok=True)
            
            report_folder = vendor_reports_folder / str(run_number)
            report_folder.mkdir(parents=True, exist_ok=True)

            cursor.execute(
                "UPDATE vendor_reports SET storage_path = ? WHERE id = ?",
                (str(report_folder), report_id),
            )

            conn.commit()
            conn.close()
            return report_id
            
        except sqlite3.IntegrityError as e:
            # Duplicate run_number due to concurrent creation
            if "idx_vendor_run_unique" in str(e) and attempt < MAX_RETRIES - 1:
                print(f"⏳ Report version conflict (attempt {attempt + 1}/{MAX_RETRIES}), retrying...")
                conn.close()
                attempt += 1
                time.sleep(BASE_DELAY * (2 ** attempt))  # Exponential backoff
            else:
                conn.close()
                raise
        finally:
            if conn:
                conn.close()


def get_latest_report_for_vendor(vendor_id: int) -> sqlite3.Row | None:
    """Fetch the most recent report for a vendor.

    Args:
        vendor_id (int): Vendor identifier.

    Returns:
        sqlite3.Row | None: Latest report row, or None if no reports exist.
    """
    return _execute_select_one(
        "SELECT * FROM vendor_reports WHERE vendor_id = ? ORDER BY timestamp DESC LIMIT 1",
        (vendor_id,),
        use_row_factory=True
    )


def get_all_vendor_reports(vendor_id: int) -> list[sqlite3.Row]:
    """Fetch all reports for a vendor ordered by newest first.

    Args:
        vendor_id (int): Vendor identifier.

    Returns:
        list[sqlite3.Row]: Collection of report rows for the vendor.
    """
    return _execute_select(
        "SELECT * FROM vendor_reports WHERE vendor_id = ? ORDER BY timestamp DESC",
        (vendor_id,),
        use_row_factory=True
    )

def save_report(report: Report) -> int | None:
    """Persist report metadata and serialized controls to the database.
    
    Implements optimistic locking using the version field to detect concurrent edits.
    If another user has modified the report since it was loaded, raises an exception.

    Args:
        report (VendorReport): Report object containing fields to save.

    Returns:
        int | None: Report ID after save, or None when no report ID exists.
        
    Raises:
        RuntimeError: If report version doesn't match DB version (concurrent edit detected)
    """
    # Optimistic locking: write succeeds only if caller's report.version
    # still matches DB version, preventing silent overwrite on concurrent edits.
    if not report.id:
        return None
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check if version still matches (optimistic lock)
        cursor.execute(
            "SELECT version FROM vendor_reports WHERE id = ?",
            (report.id,)
        )
        row = cursor.fetchone()
        if not row:
            conn.close()
            return None
            
        db_version = row[0]
        loaded_version = report.version or 1
        
        if db_version != loaded_version:
            conn.close()
            raise RuntimeError(
                f"Report was modified by another user. "
                f"Your version: {loaded_version}, Current version: {db_version}. "
                f"Please reload the report and try again."
            )
        
        # Prepare update with version increment
        controls_json = json.dumps([c.dict() for c in report.controls])
        file_list_json = json.dumps(report.file_names)
        excluded_json = json.dumps(report.excluded_names)
        path_str = report.storage_path if report.storage_path else ""
        new_version = loaded_version + 1
        
        cursor.execute("""
            UPDATE vendor_reports 
            SET prompt = ?, vendor_name = ?, overall_score = ?, possible_score = ?, 
                summary = ?, data_type = ?, controls_json = ?, file_list_json = ?, storage_path = ?,
                excluded_json = ?, runtime = ?, version = ?
            WHERE id = ?
        """, (report.prompt, report.vendor_name, report.overall_score, report.possible_score, 
              report.summary, report.data_type.value if report.data_type else "Restricted", controls_json, file_list_json, path_str, excluded_json, 
              report.runtime, new_version, report.id))
        
        # Update the report object's version to reflect the new version
        report.version = new_version
        
        conn.commit()
        return report.id
        
    finally:
        conn.close()

def get_report_by_id(report_id: int) -> sqlite3.Row | None:
    """Fetch one report row by primary key.

    Args:
        report_id (int): Report identifier.

    Returns:
        sqlite3.Row | None: Matching row, or "None" if not found or on
        database error.
    """
    return _execute_select_one(
        "SELECT * FROM vendor_reports WHERE id = ?",
        (report_id,),
        use_row_factory=True
    )


def delete_vendor(vendor_id: int) -> None:
    """Delete a vendor and all its reports and documents.

    Args:
        vendor_id (int): Vendor identifier to remove.
    """

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Delete entire vendor folder (Storage/{vendor_id}/)
        vendor_folder = STORAGE_DIR / str(vendor_id)
        if vendor_folder.exists():
            shutil.rmtree(vendor_folder)

        # Delete all reports for this vendor
        cursor.execute("DELETE FROM vendor_reports WHERE vendor_id = ?", (vendor_id,))

        # Delete the vendor
        cursor.execute("DELETE FROM vendors WHERE id = ?", (vendor_id,))

        conn.commit()
        print(f"🗑️ Deleted vendor ID: {vendor_id}")

    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")

    finally:
        conn.close()

def delete_report(vendor_id: int, report_id: int) -> bool:
    """Delete a single report and its associated storage folder, clearing it from active if needed.

    Args:
        vendor_id (int): Vendor identifier that owns the report.
        report_id (int): Report identifier to delete.

    Returns:
        bool: True if deletion succeeded, False otherwise.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        # Get the report to find its storage path
        cursor.execute("SELECT storage_path FROM vendor_reports WHERE id = ? AND vendor_id = ?", (report_id, vendor_id))
        report_row = cursor.fetchone()
        
        if not report_row:
            print(f"⚠️ Report ID {report_id} not found for vendor {vendor_id}")
            return False
        
        storage_path = report_row["storage_path"]
        
        # Delete the report folder if it exists
        if storage_path:
            report_folder = Path(storage_path)
            if report_folder.exists():
                shutil.rmtree(report_folder)
        
        # Delete the report from the database
        cursor.execute("DELETE FROM vendor_reports WHERE id = ? AND vendor_id = ?", (report_id, vendor_id))
        
        # If this was the active report for the vendor, switch to the next available report
        cursor.execute("SELECT active_report_id FROM vendors WHERE id = ?", (vendor_id,))
        vendor_row = cursor.fetchone()
        
        if vendor_row and vendor_row["active_report_id"] == report_id:
            # Find the next available report for this vendor (newest first)
            cursor.execute(
                "SELECT id FROM vendor_reports WHERE vendor_id = ? ORDER BY timestamp DESC LIMIT 1",
                (vendor_id,)
            )
            next_report = cursor.fetchone()
            next_report_id = next_report["id"] if next_report else None
            
            # Update the vendor's active report (or set to NULL if no reports remain)
            cursor.execute(
                "UPDATE vendors SET active_report_id = ? WHERE id = ?",
                (next_report_id, vendor_id)
            )
        
        conn.commit()
        print(f"🗑️ Deleted report ID: {report_id} from vendor {vendor_id}")
        return True

    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        return False

    finally:
        conn.close()

def generate_vendor_report_from_db(db_report: sqlite3.Row | dict) -> Report:
    """Convert a raw database row into a "VendorReport" model instance.

    Args:
        db_report (sqlite3.Row | dict): Database row with serialized JSON fields.

    Returns:
        VendorReport: Hydrated report object with parsed controls and metadata.
    """

    # Parse JSON data safely
    controls_data = json.loads(db_report['controls_json'])
    file_names = json.loads(db_report['file_list_json'])
    excluded_data = json.loads(db_report['excluded_json']) if db_report['excluded_json'] else []
    
    # Parse data_type, defaulting to Restricted if not present
    # Handle both sqlite3.Row and dict types safely
    try:
        data_type_str = db_report['data_type']
    except (KeyError, IndexError):
        data_type_str = 'Restricted'
    
    try:
        data_type = DataType(data_type_str)
    except (ValueError, KeyError):
        data_type = DataType.RESTRICTED

    return Report(
        id=db_report["id"],
        prompt=db_report["prompt"],
        vendor_name=db_report["vendor_name"],
        overall_score=db_report["overall_score"],
        possible_score=db_report["possible_score"],
        summary=db_report["summary"],
        data_type=data_type,
        controls=[SecurityControl(**c) for c in controls_data],
        file_names=file_names,
        storage_path=db_report["storage_path"],
        excluded_names=excluded_data,
        run_number=db_report["run_number"],
        version=int(db_report["version"]) if "version" in db_report.keys() else 1,
        timestamp=db_report["timestamp"],
        runtime=db_report["runtime"] if "runtime" in db_report.keys() else None,
    )


def print_vendors_table() -> None:
    """Print all vendors with Bitsight information."""

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM vendors")
        rows = cursor.fetchall()
        
        if not rows:
            print("\n📭 No vendors found.")
            return

        print("\n" + "="*120)
        print("VENDORS TABLE")
        print("="*120)

        for row in rows:
            print(f"\nID: {row['id']}")
            print(f"Name: {row['name']}")
            print(f"NDA Signed: {'Yes' if row['nda_signed'] else 'No'}")
            print(f"Bitsight Company GUID: {row['bitsight_company_guid'] or 'N/A'}")
            print(f"Bitsight Company Name: {row['bitsight_company_name'] or 'N/A'}")
            print(f"Bitsight Rating: {row['bitsight_rating'] or 'N/A'}")
            print(f"Bitsight Rating Date: {row['bitsight_rating_date'] or 'N/A'}")
            print(f"Website URL: {row['website_URL'] or 'N/A'}")
            print("-" * 120)
            
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
    finally:
        conn.close()

# Probably don't make this function accessible on the website. Will be used to clean up testing entries
def cleanup_database() -> None:
    """Remove all vendor and report rows and delete all report storage directories."""

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # TRUNCATE isn't in SQLite, so we use DELETE
        cursor.execute("DELETE FROM vendor_reports")
        cursor.execute("DELETE FROM vendors")

        # Reset the ID counters so the next entry starts at 1
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='vendor_reports'")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='vendors'")
        conn.commit()

        # Also delete physical folders from the disk
        if STORAGE_DIR.exists():
            for item in STORAGE_DIR.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)

        print("🧹 Database wiped clean!")

    except sqlite3.Error as e:
        print(f"❌ Error during cleanup: {e}")
    finally:
        conn.close()

def get_vendor_upload_metadata_path(vendor_id: int) -> Path:
    """Get the path to the upload metadata file for a vendor.

    Args:
        vendor_id (int): Vendor identifier.

    Returns:
        Path: Path to the vendor's upload_metadata.json file.
    """
    return STORAGE_DIR / str(vendor_id) / "upload_metadata.json"


def save_vendor_upload_metadata(vendor_id: int, metadata: dict) -> None:
    """Save document upload metadata for a vendor.

    Args:
        vendor_id (int): Vendor identifier.
        metadata (dict): Dictionary mapping document types to filenames.
    """
    metadata_path = get_vendor_upload_metadata_path(vendor_id)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)


def load_vendor_upload_metadata(vendor_id: int) -> dict:
    """Load document upload metadata for a vendor.

    Args:
        vendor_id (int): Vendor identifier.

    Returns:
        dict: Dictionary mapping document types to filenames, or empty dict if not found.
    """
    metadata_path = get_vendor_upload_metadata_path(vendor_id)
    
    if not metadata_path.exists():
        return {}
    
    try:
        with open(metadata_path, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


# Nuclear option. Using it in testing to add or remove columns from the database quickly
def delete_database() -> None:
    """Completely remove report data by cleaning records and deleting DB file."""
    
    cleanup_database()

    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
            print(f"✅ Old database file removed: {DB_PATH}")
        except Exception as e:
            print(f"❌ Could not delete DB file (it might be open elsewhere): {e}")
            return


if __name__ == "__main__":

    init_db()

    print_vendors_table()