import sqlite3
import os

# Define the database path
db_path = os.path.join('databases', 'clinician_nav_contacts.db')

def connect_to_db():
    """Connect to the SQLite database and return connection and cursor."""
    if not os.path.exists(db_path):
        print(f"Error: Database file not found at {db_path}")
        exit(1)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    return conn, cursor

def test_database_exists():
    """Test 1: Verify that the database file exists."""
    print("Test 1: Checking if database exists...")
    if os.path.exists(db_path):
        print(f"Success: Database found at {db_path}")
    else:
        print(f"Failure: Database not found at {db_path}")
        exit(1)

def test_table_exists():
    """Test 2: Verify that the clinician_contacts table exists."""
    print("\nTest 2: Checking if clinician_contacts table exists...")
    conn, cursor = connect_to_db()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='clinician_contacts'")
    result = cursor.fetchone()
    if result:
        print("Success: Table 'clinician_contacts' exists")
    else:
        print("Failure: Table 'clinician_contacts' not found")
    conn.close()

def test_record_count():
    """Test 3: Count the total number of records in the table."""
    print("\nTest 3: Counting total records...")
    conn, cursor = connect_to_db()
    cursor.execute("SELECT COUNT(*) FROM clinician_contacts")
    count = cursor.fetchone()[0]
    print(f"Success: Found {count} records in clinician_contacts")
    conn.close()

def test_retrieve_all_records():
    """Test 4: Retrieve and display all records (limited to first 5 for brevity)."""
    print("\nTest 4: Retrieving first 5 records...")
    conn, cursor = connect_to_db()
    cursor.execute("SELECT * FROM clinician_contacts LIMIT 5")
    rows = cursor.fetchall()
    if rows:
        print("Success: Retrieved records:")
        for row in rows:
            print(f"  Clinician: {row[0]}, NAV Contact No: {row[1]}")
    else:
        print("Failure: No records found")
    conn.close()

def test_query_specific_clinician():
    """Test 5: Query a specific clinician by name."""
    clinician_name = "Aneesha Chumber"
    print(f"\nTest 5: Querying for clinician '{clinician_name}'...")
    conn, cursor = connect_to_db()
    cursor.execute("SELECT * FROM clinician_contacts WHERE \"Docuware Clinician Name\" = ?", (clinician_name,))
    rows = cursor.fetchall()
    if rows:
        print(f"Success: Found {len(rows)} record(s) for '{clinician_name}':")
        for row in rows:
            print(f"  Clinician: {row[0]}, NAV Contact No: {row[1]}")
    else:
        print(f"Failure: No records found for '{clinician_name}'")
    conn.close()

def test_nonexistent_clinician():
    """Test 6: Query a clinician that doesn't exist."""
    clinician_name = "Nonexistent Clinician"
    print(f"\nTest 6: Querying for nonexistent clinician '{clinician_name}'...")
    conn, cursor = connect_to_db()
    cursor.execute("SELECT * FROM clinician_contacts WHERE \"Docuware Clinician Name\" = ?", (clinician_name,))
    rows = cursor.fetchall()
    if not rows:
        print(f"Success: No records found for '{clinician_name}' (as expected)")
    else:
        print(f"Failure: Unexpectedly found records for '{clinician_name}':")
        for row in rows:
            print(f"  Clinician: {row[0]}, NAV Contact No: {row[1]}")
    conn.close()

def test_duplicate_entries():
    """Test 7: Check for duplicate clinician entries (e.g., Aneesha Chumber)."""
    clinician_name = "Aneesha Chumber"
    print(f"\nTest 7: Checking for duplicate entries for '{clinician_name}'...")
    conn, cursor = connect_to_db()
    cursor.execute("SELECT \"Docuware Clinician Name\", COUNT(*) FROM clinician_contacts WHERE \"Docuware Clinician Name\" = ? GROUP BY \"Docuware Clinician Name\"", (clinician_name,))
    result = cursor.fetchone()
    if result:
        count = result[1]
        print(f"Success: Found {count} entries for '{clinician_name}'")
    else:
        print(f"Failure: No entries found for '{clinician_name}'")
    conn.close()

# Run all tests
if __name__ == "__main__":
    print("Starting tests for clinician_nav_contacts.db...\n")
    test_database_exists()
    test_table_exists()
    test_record_count()
    test_retrieve_all_records()
    test_query_specific_clinician()
    test_nonexistent_clinician()
    test_duplicate_entries()
    print("\nAll tests completed!")