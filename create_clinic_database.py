import sqlite3
import csv
import os

# Define paths
script_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(script_dir, 'clinic_nav_sell_to.db')
csv_path = os.path.join(script_dir, 'sales_orders_with_customers.csv')

# Check if the CSV file exists
if not os.path.exists(csv_path):
    print(f"Error: CSV file not found at {csv_path}")
    exit(1)

try:
    # Connect to the database (creates the file if it doesn't exist)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create the customers table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            Docuware_Clinic_Name TEXT PRIMARY KEY,
            Sell_to_Customer_No TEXT NOT NULL
        )
    ''')

    # Read the CSV file and insert data into the table
    with open(csv_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            clinic_name = row['Docuware Clinic Name']
            customer_no = row['Sell_to_Customer_No']
            cursor.execute("INSERT OR REPLACE INTO customers (Docuware_Clinic_Name, Sell_to_Customer_No) VALUES (?, ?)", (clinic_name, customer_no))

    # Commit the changes
    conn.commit()

    # Verify the number of records inserted
    cursor.execute("SELECT COUNT(*) FROM customers")
    record_count = cursor.fetchone()[0]
    print(f"Successfully inserted/replaced {record_count} records into the customers table.")

except sqlite3.Error as e:
    print(f"Database error: {e}")
except Exception as e:
    print(f"An error occurred: {e}")
finally:
    if 'conn' in locals():
        conn.close()