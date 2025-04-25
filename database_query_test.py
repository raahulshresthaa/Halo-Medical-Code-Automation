import sqlite3

# Connect to the database
conn = sqlite3.connect('sales_orders.db')
cursor = conn.cursor()

# Example: Fetch all rows
cursor.execute('SELECT * FROM sales_orders')
rows = cursor.fetchall()
for row in rows:
    print(row)

# Example: Query specific data
cursor.execute('SELECT Docuware_Clinic_Name FROM sales_orders WHERE Sell_to_Customer_No = "GB-CUST01981"')
clinics = cursor.fetchall()
print("Clinics for GB-CUST01981:", clinics)

# Close the connection
conn.close()