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
def parse_code_string(code_str):
    """Parse a code string like 'B55A x2' into (item_no, quantity)."""
    print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🔍 Parsing code string: '{code_str}'")
    code_str = code_str.strip()
    if 'x' in code_str:
        parts = code_str.split('x')
        if len(parts) == 2:
            code = parts[0].strip()
            try:
                quantity = int(parts[1].strip())
                print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ✅ Parsed: code='{code}', quantity={quantity}")
                return code, quantity
            except ValueError:
                print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ❌ Failed to parse quantity in '{code_str}'")
    else:
        print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ⚠️ No 'x' found in '{code_str}', assuming quantity 1")
    return code_str, 1  # Default quantity is 1 if no 'x' or parsing fails

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

def create_sales_order(sell_to_customer_no, prescriber, original_order_date, request_delivery_date, auto_doc_ref, final_codes=None, patient_name=None):
    print(f"Starting create_sales_order for customer {sell_to_customer_no}")
    
    error_messages = []
    sales_order_no = None

    filter_soa = "$filter=startswith(No,'GB-SOA0')&$orderby=No desc&$top=1"
    get_url = f"{nav_url}/Company('{encoded_company}')/SalesOrderService?{filter_soa}"
    response = requests.get(get_url, headers=headers, auth=auth)
    
    if response.status_code != 200:
        print(f"Failed to get last SOA order: {response.status_code}")
        error_messages.append(f"Failed to get last SOA order: {response.text}")
        return {'success': False, 'sales_order_no': None, 'error_messages': error_messages}
    
    orders = response.json()['value']
    if orders:
        last_soa = orders[0]['No']
        print(f"Last SOA order: {last_soa}")
    else:
        last_soa = "GB-SOA000000"
        print("No SOA orders found. Starting from default.")

    match = re.match(r"(GB-SOA)(\d+)", last_soa)
    if not match:
        print(f"Could not parse SOA number: {last_soa}")
        error_messages.append("Could not parse SOA number.")
        return {'success': False, 'sales_order_no': None, 'error_messages': error_messages}
    
    prefix, number = match.groups()
    next_no = f"{prefix}{int(number)+1:06d}"
    print(f"Generated next order number: {next_no}")

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
        "Pad_No": auto_doc_ref,
        "Patient_Name": patient_name if patient_name else "Unknown"
    }

    post_url = f"{nav_url}/Company('{encoded_company}')/SalesOrderService"
    create_response = requests.post(post_url, headers=headers, data=json.dumps(order_data), auth=auth)
    
    if create_response.status_code != 201:
        print(f"Failed to create sales order: {create_response.status_code}")
        error_messages.append(f"Failed to create sales order: {create_response.text}")
        return {'success': False, 'sales_order_no': None, 'error_messages': error_messages}
    
    print(f"Created Sales Order: {next_no}")
    sales_order_no = next_no

    medical_details = [
        { 
            "Operation": "Special Instructions",
            "Medical_Detail_Text": "Refer to Prescription form" 
        }
    ]
    medical_url = f"{nav_url}/Company('{encoded_company}')/MedicalDetails"
    for med in medical_details:
        payload = {"Document_No": next_no, "Line_No": 20000, **med}
        response = requests.post(medical_url, headers=headers, data=json.dumps(payload), auth=auth)
        if response.status_code != 201:
            print(f"Failed to add medical detail: {response.status_code}")
            error_messages.append(f"Failed to add medical detail: {response.text}")

    lines_url = f"{nav_url}/Company('{encoded_company}')/SalesOrderLineService"
    if final_codes and len(final_codes) > 0:
        print(f"Adding {len(final_codes)} sales order lines")
        item_lines = [parse_code_string(code_str) for code_str in final_codes]
        base_line_no = 100000
        for i, (item_no, quantity) in enumerate(item_lines):
            line_data = {
                "Document_Type": "Order",
                "Document_No": next_no,
                "Line_No": base_line_no + i * 20000,
                "Type": "Item",
                "No": item_no,
                "Quantity": quantity,
                "Location_Code": "WAREHOUSE",
                "Unit_of_Measure_Code": "EACH"
            }
            response = requests.post(lines_url, headers=headers, data=json.dumps(line_data), auth=auth)
            if response.status_code != 201:
                print(f"Failed to add line {item_no}: {response.status_code}")
                error_messages.append(f"Failed to add line: {response.text}")
    else:
        print("No final codes provided")

    success = len(error_messages) == 0
    print(f"Finished create_sales_order. Success: {success}")
    return {'success': success, 'sales_order_no': sales_order_no, 'error_messages': error_messages}