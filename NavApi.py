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

# Define specific work order functions
def work_order_insole(auto_doc_ref):
    target_operation = "Special Instructions"
    target_text = "Refer to Prescription form " + auto_doc_ref
    return target_operation, target_text

def work_order_bespoke(auto_doc_ref):
    target_operation = "Special Instructions"
    target_text = "Refer to Prescription form " + auto_doc_ref
    return target_operation, target_text

def work_order_modular(auto_doc_ref):
    target_operation = "Special Instructions"
    target_text = "Refer to Prescription form " + auto_doc_ref
    return target_operation, target_text

def work_order_afo(auto_doc_ref):
    target_operation = "Special Instructions"
    target_text = "Refer to Prescription form " + auto_doc_ref
    return target_operation, target_text

def work_order_undefined(auto_doc_ref):
    target_operation = "Special Instructions"
    target_text = "Refer to Prescription form " + auto_doc_ref
    return target_operation, target_text

def work_order_a_and_r(auto_doc_ref):
    target_operation = "Special Instructions"
    target_text = "Refer to Prescription form " + auto_doc_ref
    return target_operation, target_text

def create_sales_order(sell_to_customer_no, prescriber, original_order_date, request_delivery_date, auto_doc_ref, order_category_code, form_type, final_codes=None, patient_name=None, gender=None):
    print(f"Starting create_sales_order for customer {sell_to_customer_no} with auto_doc_ref {auto_doc_ref}")
    
    error_messages = []
    sales_order_no = None

    # Check if the sales order already exists
    filter_existing = f"$filter=Pad_No eq '{auto_doc_ref}' and Sell_to_Customer_No eq '{sell_to_customer_no}'"
    check_url = f"{nav_url}/Company('{encoded_company}')/SalesOrderService?{filter_existing}"
    check_response = requests.get(check_url, headers=headers, auth=auth)
    
    if check_response.status_code == 200 and check_response.json()['value']:
        existing_order = check_response.json()['value'][0]
        sales_order_no = existing_order['No']
        print(f"Order {sales_order_no} already exists for auto_doc_ref {auto_doc_ref}. Proceeding to clean up duplicates.")
    else:
        # Get the top two SOA order numbers
        filter_soa = "$filter=startswith(No,'GB-SOA')&$orderby=No desc&$top=2"
        get_url = f"{nav_url}/Company('{encoded_company}')/SalesOrderService?{filter_soa}"
        response = requests.get(get_url, headers=headers, auth=auth)
        
        if response.status_code != 200:
            error_msg = f"Failed to get top SOA orders: {response.status_code} - {response.text}"
            print(f"❌ {error_msg}")
            error_messages.append(error_msg)
            return {'success': False, 'sales_order_no': None, 'error_messages': error_messages}
        
        orders = response.json()['value']
        if len(orders) >= 2:
            last_soa = orders[0]['No']
            second_last_soa = orders[1]['No']
            print(f"Top two SOA orders: {last_soa} and {second_last_soa}")
            
            match_last = re.match(r"(GB-SOA)(\d+)", last_soa)
            match_second = re.match(r"(GB-SOA)(\d+)", second_last_soa)
            
            if match_last and match_second:
                _, last_number = match_last.groups()
                _, second_number = match_second.groups()
                last_num = int(last_number)
                second_num = int(second_number)
                
                if last_num - second_num == 1:
                    print(f"Sequence is correct: {second_last_soa} -> {last_soa}")
                    next_num = last_num + 1
                else:
                    print(f"Sequence discrepancy detected: {second_last_soa} and {last_soa}")
                    next_num = max(last_num, second_num) + 1
            else:
                error_msg = "Could not parse top SOA numbers."
                print(f"❌ {error_msg}")
                error_messages.append(error_msg)
                return {'success': False, 'sales_order_no': None, 'error_messages': error_messages}
        elif len(orders) == 1:
            last_soa = orders[0]['No']
            print(f"Only one SOA order found: {last_soa}")
            match = re.match(r"(GB-SOA)(\d+)", last_soa)
            if match:
                prefix, number = match.groups()
                next_num = int(number) + 1
            else:
                error_msg = f"Could not parse SOA number: {last_soa}"
                print(f"❌ {error_msg}")
                error_messages.append(error_msg)
                return {'success': False, 'sales_order_no': None, 'error_messages': error_messages}
        else:
            print("No SOA orders found. Starting from GB-SOA00001")
            next_num = 1
        
        next_no = f"GB-SOA{next_num:05d}"
        print(f"Generated next order number: {next_no}")

        external_doc_no = f"RS-AI-ORDER-{next_no[-4:]}"
        today = datetime.date.today().strftime("%Y-%m-%d")
        order_data = {
            "No": next_no,
            "Sell_to_Customer_No": sell_to_customer_no,
            "Original_Order_Date": original_order_date,
            "Order_Date": today,
            "Document_Date": today,
            "Order_Category_Code": order_category_code,
            "Prescriber": prescriber,
            "Send_For": "Send for Finish",
            "Requested_Delivery_Date": request_delivery_date,
            "Pad_No": auto_doc_ref,
            "Patient_Name": patient_name if patient_name else "Unknown",
            "Patient_Gender": gender
        }

        post_url = f"{nav_url}/Company('{encoded_company}')/SalesOrderService"
        
        max_attempts = 5
        attempt = 0
        while attempt < max_attempts:
            order_data["No"] = next_no
            print(f"Order Category Code for attempt {attempt + 1}: {order_data['Order_Category_Code']}")
            print(f"Attempt {attempt + 1}: Sending order_data:\n{json.dumps(order_data, indent=2)}")
            create_response = requests.post(post_url, headers=headers, data=json.dumps(order_data), auth=auth)
            if create_response.status_code == 201:
                print(f"✅ Created Sales Order: {next_no}")
                sales_order_no = next_no
                break
            elif create_response.status_code == 400:
                try:
                    error_data = create_response.json()
                    if error_data.get("error", {}).get("code") == "Internal_EntityWithSameKeyExists":
                        print(f"Order number {next_no} already exists. Trying next number.")
                        next_no = increment_order_no(next_no)
                        attempt += 1
                    else:
                        error_msg = f"Failed to create sales order: {create_response.status_code} - {create_response.text}"
                        print(f"❌ {error_msg}")
                        error_messages.append(error_msg)
                        return {'success': False, 'sales_order_no': None, 'error_messages': error_messages}
                except json.JSONDecodeError:
                    error_msg = f"Failed to create sales order: {create_response.status_code} - {create_response.text}"
                    print(f"❌ {error_msg}")
                    error_messages.append(error_msg)
                    return {'success': False, 'sales_order_no': None, 'error_messages': error_messages}
            else:
                error_msg = f"Failed to create sales order: {create_response.status_code} - {create_response.text}"
                print(f"❌ {error_msg}")
                error_messages.append(error_msg)
                return {'success': False, 'sales_order_no': None, 'error_messages': error_messages}
        else:
            error_msg = f"Failed to create sales order after {max_attempts} attempts."
            print(f"❌ {error_msg}")
            error_messages.append(error_msg)
            return {'success': False, 'sales_order_no': None, 'error_messages': error_messages}

    # Retrieve and clean up medical details
    filter_medical = f"$filter=Document_No eq '{sales_order_no}'"
    medical_get_url = f"{nav_url}/Company('{encoded_company}')/MedicalDetails?{filter_medical}"
    medical_response = requests.get(medical_get_url, headers=headers, auth=auth)
    
    work_order_funcs = {
        'insoles': work_order_insole,
        'bespoke': work_order_bespoke,
        'modular': work_order_modular,
        'afos': work_order_afo,
        'a&r': work_order_a_and_r
    }

    work_order_func = work_order_funcs.get(form_type.lower(), work_order_undefined)
    target_operation, target_text = work_order_func(auto_doc_ref)
    
    if medical_response.status_code == 200:
        existing_details = medical_response.json()['value']
        print(f"Existing medical details retrieved: {existing_details}")
        
        matching_details = [
            detail for detail in existing_details
            if detail['Operation'].strip().lower() == target_operation.lower() and
               detail['Medical_Detail_Text'].strip().lower() == target_text.lower()
        ]
        
        if len(matching_details) > 1:
            print(f"Found {len(matching_details)} duplicate medical details. Keeping first, deleting others.")
            for detail in matching_details[1:]:
                delete_url = f"{nav_url}/Company('{encoded_company}')/MedicalDetails(Document_No='{sales_order_no}',Line_No={detail['Line_No']})"
                delete_response = requests.delete(delete_url, headers=headers, auth=auth)
                if delete_response.status_code == 204:
                    print(f"✅ Deleted duplicate medical detail with Line_No: {detail['Line_No']}")
                else:
                    error_msg = f"Failed to delete duplicate: {delete_response.status_code} - {delete_response.text}"
                    print(f"❌ {error_msg}")
                    error_messages.append(error_msg)
        elif len(matching_details) == 0:
            # Use a higher starting Line_No for medical details to avoid overlap
            next_line_no = 100000 if not existing_details else max(detail['Line_No'] for detail in existing_details) + 10000
            medical_url = f"{nav_url}/Company('{encoded_company}')/MedicalDetails"
            payload = {
                "Document_No": sales_order_no,
                "Line_No": next_line_no,
                "Operation": target_operation,
                "Medical_Detail_Text": target_text
            }
            response = requests.post(medical_url, headers=headers, data=json.dumps(payload), auth=auth)
            if response.status_code == 201:
                print(f"✅ Added medical detail with Line_No: {next_line_no}")
            else:
                error_msg = f"Failed to add medical detail: {response.status_code} - {response.text}"
                print(f"❌ {error_msg}")
                error_messages.append(error_msg)
        else:
            print("Exactly one matching medical detail found. No action needed.")
    else:
        error_msg = f"Failed to retrieve medical details: {medical_response.status_code} - {medical_response.text}"
        print(f"❌ {error_msg}")
        error_messages.append(error_msg)

    # Add sales order lines
    lines_url = f"{nav_url}/Company('{encoded_company}')/SalesOrderLineService"
    if final_codes and len(final_codes) > 0:
        print(f"Processing {len(final_codes)} codes for sales order lines")
        valid_codes = [code for code in final_codes if code.strip() != "```"]
        item_lines = [parse_code_string(code_str) for code_str in valid_codes]

        for item_no, quantity in item_lines:
            # Fetch current existing sales order lines to determine the next Line_No
            filter_lines = f"$filter=Document_No eq '{sales_order_no}' and Document_Type eq 'Order'"
            existing_lines_url = f"{lines_url}?{filter_lines}"
            lines_response = requests.get(existing_lines_url, headers=headers, auth=auth)

            if lines_response.status_code == 200:
                existing_lines = lines_response.json()['value']
                print(f"Existing sales lines before adding {item_no}: {[line['Line_No'] for line in existing_lines]}")
                if existing_lines:
                    max_line_no = max(line['Line_No'] for line in existing_lines)
                    next_line_no = max_line_no + 10000
                else:
                    next_line_no = 10000
            else:
                error_msg = f"Failed to retrieve existing lines for {item_no}: {lines_response.status_code} - {lines_response.text}"
                print(f"❌ {error_msg}")
                error_messages.append(error_msg)
                next_line_no = 10000  # Fallback to default

            # Add the line with the determined next_line_no
            line_data = {
                "Document_Type": "Order",
                "Document_No": sales_order_no,
                "Line_No": next_line_no,
                "Type": "Item",
                "No": item_no,
                "Quantity": quantity,
                "Location_Code": "WAREHOUSE",
            }
            response = requests.post(lines_url, headers=headers, data=json.dumps(line_data), auth=auth)
            if response.status_code != 201:
                error_msg = f"Failed to add line {item_no}: {response.status_code} - {response.text}"
                print(f"❌ {error_msg}")
                error_messages.append(error_msg)
            else:
                print(f"✅ Added sales order line: {item_no} x{quantity}")
    else:
        print("No final codes provided")

    success = len(error_messages) == 0
    print(f"Finished create_sales_order. Success: {success}")
    return {'success': success, 'sales_order_no': sales_order_no, 'error_messages': error_messages}

def increment_order_no(order_no):
    match = re.match(r"(GB-SOA)(\d+)", order_no)
    if match:
        prefix, number = match.groups()
        next_number = int(number) + 1
        return f"{prefix}{next_number:05d}"
    else:
        raise ValueError(f"Invalid order number format: {order_no}")