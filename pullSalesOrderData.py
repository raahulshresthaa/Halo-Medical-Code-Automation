import sqlite3
import os

# Define paths
project_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(project_dir, 'databases', 'clinic_nav_sell_to.db')
output_file = os.path.join(project_dir, 'customer_data_output.txt')

# Check if the database file exists
if not os.path.exists(db_path):
    print(f"Error: Database file not found at {db_path}")
    exit(1)

# Connect to the database
try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # List all tables in the database
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("\nTables in the database:")
    if tables:
        for table in tables:
            print(f"- {table[0]}")
    else:
        print("No tables found in the database.")
        conn.close()
        exit(1)

    # Check if customers table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='customers';")
    if not cursor.fetchone():
        print("\nError: Table 'customers' does not exist.")
        conn.close()
        exit(1)

    # Retrieve all records from customers
    cursor.execute("SELECT * FROM customers")
    rows = cursor.fetchall()

    # Prepare output
    output = ["Contents of customers table:\n"]
    if rows:
        print(f"\nFound {len(rows)} records in customers:")
        output.append(f"Total records: {len(rows)}\n")
        output.append("Docuware_Clinic_Name | Sell_to_Customer_No")
        output.append("-" * 50)
        for row in rows:
            print(f"Clinic: {row[0]}, Customer No: {row[1]}")
            output.append(f"{row[0]} | {row[1]}")
    else:
        print("\nNo records found in customers table.")
        output.append("No records found.")

    # Save output to a text file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output))
    print(f"\nOutput saved to {output_file}")

    # Close the database connection
    conn.close()

except sqlite3.Error as e:
    print(f"Database error: {e}")
except Exception as e:
    print(f"An error occurred: {e}")
finally:
    if 'conn' in locals():
        conn.close()