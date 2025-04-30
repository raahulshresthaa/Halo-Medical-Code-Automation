#NavApi.py
import requests
from requests_ntlm import HttpNtlmAuth
import json
import urllib.parse
import re
import datetime
import os
import base64
import tkinter as tk
from tkinter import simpledialog, messagebox
import sys

def read_nav_config_file(filename, config_name):
    file_path = os.path.join(os.getcwd(), filename)
    if os.path.exists(file_path):
        try:
            with open(file_path, 'rb') as f:
                encoded_data = f.read()
                decoded_data = base64.b64decode(encoded_data).decode('utf-8').strip()
            if not decoded_data:
                raise ValueError(f"{config_name} file is empty.")
            return decoded_data
        except Exception as e:
            messagebox.showerror("Error", f"Error reading {config_name}: {str(e)}")
            sys.exit()
    else:
        # Prompt the user to enter the config value
        value = simpledialog.askstring(f"{config_name} Required", f"Please enter your {config_name}:")
        if not value:
            messagebox.showerror("Error", f"No {config_name} entered. The application will exit.")
            sys.exit()
        # Write the new config value to the file
        write_nav_config_file(filename, value.strip())
        return value.strip()

def write_nav_config_file(filename, value):
    file_path = os.path.join(os.getcwd(), filename)
    encoded_data = base64.b64encode(value.encode('utf-8'))
    with open(file_path, 'wb') as f:
        f.write(encoded_data)
    print(f"{filename} saved to {file_path}")

# Read NAV configuration from files
nav_url = read_nav_config_file('nav_url.txt', 'NAV URL')
company = read_nav_config_file('nav_company.txt', 'NAV Company')
username = read_nav_config_file('nav_username.txt', 'NAV Username')
password = read_nav_config_file('nav_password.txt', 'NAV Password')

encoded_company = urllib.parse.quote(company)
headers = {
    "Content-Type": "application/json",
    "Accept": "application/json"
}
auth = HttpNtlmAuth(username, password)

def create_sales_order(sell_to_customer_no, prescriber, original_order_date, request_delivery_date, auto_doc_ref):
    filter_soai = "$filter=startswith(No,'GB-SOAI')&$orderby=No desc&$top=1"
    get_url = f"{nav_url}/Company('{encoded_company}')/SalesOrderService?{filter_soai}"
    response = requests.get(get_url, headers=headers, auth=auth)
    
    if response.status_code != 200:
        print("❌ Failed to get last SOAI order number")
        print(response.status_code, response.text)
        return None
    
    last_soai = response.json()['value'][0]['No']
    print(f"🔍 Last SOAI Order No: {last_soai}")
    
    match = re.match(r"(GB-SOAI)(\d+)", last_soai)
    if not match:
        print("❌ Could not parse SOAI number.")
        return None
    
    prefix, number = match.groups()
    next_no = f"{prefix}{int(number)+1:05d}"
    print(f"➡️ Creating Sales Order: {next_no}")
    
    external_doc_no = f"RS-AI-ORDER-{next_no[-4:]}"
    today = datetime.date.today().strftime("%Y-%m-%d")
    order_data = {
        "No": next_no,
        "Sell_to_Customer_No": sell_to_customer_no,
        "Original_Order_Date": original_order_date,
        "Order_Date": today,
        "Document_Date": today,
        "Order_Category_Code": "MILLED INSOLES",
        "Prescriber": prescriber,
        "Send_For": "Send for Finish",
        "Supporting_Items_Arrived_Date": today,
        "PO_Requested_Date": today,
        "Requested_Delivery_Date": request_delivery_date,
        "Pad_No": auto_doc_ref  # Set Pad_No. to the AutoDocRef value
    }
    
    print(f"Sending order_data: {json.dumps(order_data, indent=2)}")  # Debug
    
    post_url = f"{nav_url}/Company('{encoded_company}')/SalesOrderService"
    create_response = requests.post(post_url, headers=headers, data=json.dumps(order_data), auth=auth)
    
    print(f"NAV Response: {create_response.status_code} - {create_response.text}")  # Debug
    
    if create_response.status_code != 201:
        print("❌ Failed to create sales order header:")
        print(create_response.status_code, create_response.text)
        return None
    
    print(f"✅ Created Sales Order {next_no}")
    
    # --- Step 4: Add Medical Details --- (work ticket)
    medical_details = [
        { 
            "Operation": "Special Instructions",
            "Medical_Detail_Text": "Refer to Prescription form" 
        }
    ]
    medical_url = f"{nav_url}/Company('{encoded_company}')/MedicalDetails"
    
    print(f"🧾 Posting {len(medical_details)} Medical Detail lines to: {next_no}")
    
    for i, med in enumerate(medical_details):
        payload = {
            "Document_No": next_no,
            "Line_No": (i + 1) * 10000,
            **med
        }
        response = requests.post(medical_url, headers=headers, data=json.dumps(payload), auth=auth)
        if response.status_code == 201:
            print(f"✅ Added Medical Detail: {med['Operation']} – {med['Medical_Detail_Text']}")
        else:
            print(f"❌ Failed to add Medical Detail for Operation: {med['Operation']}")
            print(response.status_code)
            try:
                print(json.dumps(response.json(), indent=4))
            except:
                print(response.text)
    
    # --- Step 5: Add Sales Order Lines ---
    lines_url = f"{nav_url}/Company('{encoded_company}')/SalesOrderLineService"
    item_nos = ["B54A", "B54C", "B55A"]  # Will need to be mapped in a database
    print(f"📦 Adding {len(item_nos)} Sales Order Line(s) to: {next_no}")
    base_line_no = 10000
    
    for i, item_no in enumerate(item_nos):
        line_data = {
            "Document_Type": "Order", 
            "Document_No": next_no,
            "Line_No": base_line_no + i * 10000 * 2,  # Needs to be x2 since the description runs across 2 lines
            "Type": "Item",
            "No": item_no,
            "Quantity": 1,  # If the final code says x2, this will need to be 2
            "Location_Code": "WAREHOUSE",
            "Unit_of_Measure_Code": "EACH"
        }
        response = requests.post(lines_url, headers=headers, data=json.dumps(line_data), auth=auth)
        if response.status_code == 201:
            print(f"✅ Added Sales Order Line: {item_no} x1")
        else:
            print(f"❌ Failed to add Sales Order Line {item_no}:")
            print(response.status_code)
            try:
                print(json.dumps(response.json(), indent=4))
            except:
                print(response.text)

    return next_no  # Return the sales order number if successful