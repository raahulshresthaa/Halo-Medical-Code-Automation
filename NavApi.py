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
    code_str = code_str.strip()
    if 'x' in code_str:
        parts = code_str.split('x')
        if len(parts) == 2:
            code = parts[0].strip()
            try:
                quantity = int(parts[1].strip())
                return code, quantity
            except ValueError:
                pass
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
        value = simpledialog.askstring(f"{config_name} Required", f"Please enter your {config_name}:")
        if not value:
            messagebox.showerror("Error", f"No {config_name} entered. The application will exit.")
            sys.exit()
        write_nav_config_file(filename, value.strip())
        return value.strip()

def write_nav_config_file(filename, value):
    file_path = os.path.join(os.getcwd(), filename)
    encoded_data = base64.b64encode(value.encode('utf-8'))
    with open(file_path, 'wb') as f:
        f.write(encoded_data)
    print(f"{filename} saved to {file_path}")

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
    error_messages = []
    sales_order_no = None

    # Check if Pad No. is already used
    filter_pad_no = f"$filter=Pad_No eq '{auto_doc_ref}'"
    get_url = f"{nav_url}/Company('{encoded_company}')/SalesOrderService?{filter_pad_no}"
    response = requests.get(get_url, headers=headers, auth=auth)
    
    if response.status_code == 200 and response.json()['value']:
        existing_order = response.json()['value'][0]
        error_message = f"Pad No. {auto_doc_ref} is already used on Sales Order No. {existing_order['No']}"
        print(f"❌ {error_message}")
        error_messages.append(error_message)
        return {'success': False, 'sales_order_no': None, 'error_messages': error_messages}

    # Get the last SOAI order number
    filter_soai = "$filter=startswith(No,'GB-SOAI')&$orderby=No desc&$top=1"
    get_url = f"{nav_url}/Company('{encoded_company}')/SalesOrderService?{filter_soai}"
    response = requests.get(get_url, headers=headers, auth=auth)
    
    if response.status_code != 200:
        print("❌ Failed to get last SOAI order number")
        print(response.status_code, response.text)
        error_messages.append(f"Failed to get last SOAI order number: {response.status_code} {response.text}")
        return {'success': False, 'sales_order_no': None, 'error_messages': error_messages}
    
    last_soai = response.json()['value'][0]['No'] if response.json()['value'] else "GB-SOAI00000"
    print(f"🔍 Last SOAI Order No: {last_soai}")
    
    match = re.match(r"(GB-SOAI)(\d+)", last_soai)
    if not match:
        print("❌ Could not parse SOAI number.")
        error_messages.append("Could not parse SOAI number.")
        return {'success': False, 'sales_order_no': None, 'error_messages': error_messages}

    # Step 3: Generate the next sales order number
    print(f"🔢 Generating next order number from '{last_soai}'")
    match = re.match(r"(GB-SOAI)(\d+)", last_soai)
    if match:
        prefix, number = match.groups()
        print(f"📋 Parsed prefix: '{prefix}', number: '{number}'")
        next_number = int(number) + 1
        next_no = f"{prefix}{next_number:05d}"
        print(f"➡️ Generated next order number: {next_no}")
    else:
        print(f"❌ Failed to parse '{last_soai}' with regex 'GB-SOAI\\d+'")
        error_messages.append(f"Could not parse order number '{last_soai}'")
        return {'success': False, 'sales_order_no': None, 'error_messages': error_messages}

    # Step 4: Prepare and create the new sales order
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
    print(f"📋 Order data prepared: {json.dumps(order_data, indent=2)}")
    
    post_url = f"{nav_url}/Company('{encoded_company}')/SalesOrderService"
    print(f"🌐 Sending POST request to create order: {post_url}")
    try:
        create_response = requests.post(post_url, headers=headers, data=json.dumps(order_data), auth=auth)
        print(f"📩 Received response: Status {create_response.status_code}")
        print(f"📜 Response content: {create_response.text}")
        
        if create_response.status_code == 201:
            print(f"✅ Successfully created Sales Order: {next_no}")
            sales_order_no = next_no
        else:
            print(f"❌ Failed to create order: {create_response.status_code} - {create_response.text}")
            error_messages.append(f"Failed to create sales order: {create_response.status_code} {create_response.text}")
            return {'success': False, 'sales_order_no': None, 'error_messages': error_messages}
    except Exception as e:
        print(f"💥 Exception creating sales order: {str(e)}")
        error_messages.append(f"Exception creating sales order: {str(e)}")
        return {'success': False, 'sales_order_no': None, 'error_messages': error_messages}

    # If successful, return the result
    print(f"🏁 Process completed. Success: {len(error_messages) == 0}, Order No: {sales_order_no}")
    return {'success': len(error_messages) == 0, 'sales_order_no': sales_order_no, 'error_messages': error_messages}