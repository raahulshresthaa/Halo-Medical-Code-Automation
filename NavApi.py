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
    error_messages = []
    sales_order_no = None

    # Step 1: Check for existing orders with the same Pad No.
    print(f"🔍 Starting Pad No. check for '{auto_doc_ref}'")
    filter_pad_no = f"$filter=Pad_No eq '{auto_doc_ref}'"
    get_url = f"{nav_url}/Company('{encoded_company}')/SalesOrderService?{filter_pad_no}"
    print(f"🌐 Sending GET request to check Pad No.: {get_url}")
    try:
        response = requests.get(get_url, headers=headers, auth=auth)
        print(f"📩 Received response: Status {response.status_code}")
        print(f"📜 Response content: {response.text}")
        
        if response.status_code == 200:
            existing_orders = response.json()['value']
            print(f"🔢 Found {len(existing_orders)} orders with Pad No. '{auto_doc_ref}'")
            if existing_orders:
                for order in existing_orders:
                    print(f"❌ Duplicate detected - Order No: {order['No']}, Customer: {order['Sell_to_Customer_No']}, Date: {order.get('Order_Date', 'N/A')}")
                error_message = f"Pad No. {auto_doc_ref} is already used on Sales Order(s): {[order['No'] for order in existing_orders]}"
                error_messages.append(error_message)
                print(f"⛔ Aborting due to duplicate Pad No.: {error_message}")
                return {'success': False, 'sales_order_no': None, 'error_messages': error_messages}
            else:
                print(f"✅ No duplicates found for Pad No. '{auto_doc_ref}'")
        else:
            print(f"❌ API error checking Pad No.: {response.status_code} - {response.text}")
            error_messages.append(f"Failed to check Pad No.: {response.status_code} {response.text}")
            return {'success': False, 'sales_order_no': None, 'error_messages': error_messages}
    except Exception as e:
        print(f"💥 Exception during Pad No. check: {str(e)}")
        error_messages.append(f"Exception checking Pad No.: {str(e)}")
        return {'success': False, 'sales_order_no': None, 'error_messages': error_messages}

    # Step 2: Fetch the last 'GB-SOAI' sales order number
    print(f"🔍 Fetching the last 'GB-SOAI' sales order")
    filter_soai = "$filter=startswith(No,'GB-SOAI')&$orderby=No desc&$top=1"
    get_url = f"{nav_url}/Company('{encoded_company}')/SalesOrderService?{filter_soai}"
    print(f"🌐 Sending GET request for last SOAI order: {get_url}")
    try:
        response = requests.get(get_url, headers=headers, auth=auth)
        print(f"📩 Received response: Status {response.status_code}")
        print(f"📜 Response content: {response.text}")
        
        if response.status_code == 200:
            orders = response.json()['value']
            print(f"🔢 Retrieved {len(orders)} 'GB-SOAI' orders")
            if orders:
                last_soai = orders[0]['No']
                print(f"✅ Successfully found last 'GB-SOAI' order: {last_soai}")
            else:
                last_soai = "GB-SOAI00000"
                print("⚠️ No 'GB-SOAI' orders exist. Defaulting to start at GB-SOAI00001")
        else:
            print(f"❌ Failed to fetch 'GB-SOAI' orders: {response.status_code} - {response.text}")
            error_messages.append(f"Failed to fetch sales orders: {response.status_code} {response.text}")
            return {'success': False, 'sales_order_no': None, 'error_messages': error_messages}
    except Exception as e:
        print(f"💥 Exception fetching last SOAI order: {str(e)}")
        error_messages.append(f"Exception fetching sales orders: {str(e)}")
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