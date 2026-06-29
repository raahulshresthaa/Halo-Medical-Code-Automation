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
    return code_str, 1

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

def work_order_a_and_r(auto_doc_ref):
    target_operation = "Special Instructions"
    target_text = "Refer to Prescription form " + auto_doc_ref
    return target_operation, target_text

def work_order_kafo(auto_doc_ref):
    target_operation = "Special Instructions"
    target_text = "Refer to Prescription form " + auto_doc_ref
    return target_operation, target_text

def parse_pre_app_date(date_str):
    """Parse 'pre app date' from formats 'dd.mm.yy', 'd/m/yyyy', or 'YYYY-MM-DD'. Returns None if invalid."""
    if not date_str:
        return None
    # Remove "Date:" prefix if present
    date_str = re.sub(r'^Date:\s*', '', date_str).strip()
    formats = ["%d.%m.%y", "%d.%m.%Y", "%d/%m/%y", "%d/%m/%Y", "%Y-%m-%d"]
    for fmt in formats:
        try:
            dt = datetime.datetime.strptime(date_str, fmt)
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            continue
    return None

def work_order_repairs(auto_doc_ref):
    target_operation = "Special Instructions"
    target_text = "Refer to Prescription form " + auto_doc_ref
    return target_operation, target_text

def work_order_adapts_and_modifications(auto_doc_ref):
    target_operation = "Special Instructions"
    target_text = "Refer to Prescription form " + auto_doc_ref
    return target_operation, target_text

def create_sales_order(sell_to_customer_no, prescriber, original_order_date, request_delivery_date, auto_doc_ref, order_category_code, form_type, final_codes=None, patient_name=None, gender=None, pre_app_date=None):
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
        message = f"Auto doc reference {auto_doc_ref} has already been uploaded to nav"
        messagebox.showinfo("Information", message)
        return {'success': True, 'sales_order_no': sales_order_no, 'error_messages': [message], 'already_exists': True}
    else:
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
                last_num = int(match_last.groups()[1])
                second_num = int(match_second.groups()[1])
                
                if last_num - second_num == 1:
                    next_num = last_num + 1
                else:
                    next_num = max(last_num, second_num) + 1
            else:
                error_msg = "Could not parse top SOA numbers."
                error_messages.append(error_msg)
                return {'success': False, 'sales_order_no': None, 'error_messages': error_messages}
        elif len(orders) == 1:
            last_soa = orders[0]['No']
            match = re.match(r"(GB-SOA)(\d+)", last_soa)
            if match:
                next_num = int(match.groups()[1]) + 1
            else:
                error_msg = f"Could not parse SOA number: {last_soa}"
                error_messages.append(error_msg)
                return {'success': False, 'sales_order_no': None, 'error_messages': error_messages}
        else:
            next_num = 1
        
        next_no = f"GB-SOA{next_num:05d}"
        external_doc_no = f"RS-AI-ORDER-{next_no[-4:]}"
        today = datetime.date.today().strftime("%Y-%m-%d")
        order_data = {
            "No": next_no,
            "Sell_to_Customer_No": sell_to_customer_no,
            "Original_Order_Date": original_order_date,
            "Order_Date": original_order_date,
            "Document_Date": today,
            "Order_Category_Code": order_category_code,
            "Prescriber": prescriber,
            "Send_For": "Send for Finish",
            "Requested_Delivery_Date": request_delivery_date,
            "Pad_No": auto_doc_ref,
            "Patient_Name": patient_name if patient_name else "Unknown",
            "Patient_Gender": gender,
            "External_Document_No": f"DNI/{auto_doc_ref}" # DNI Calculation
        }
        if pre_app_date:
            print(f"Pre App Date (Formatted): {pre_app_date}")
            order_data["Pre_appointed_Date"] = pre_app_date

        post_url = f"{nav_url}/Company('{encoded_company}')/SalesOrderService"
        
        max_attempts = 5
        attempt = 0
        while attempt < max_attempts:
            order_data["No"] = next_no
            create_response = requests.post(post_url, headers=headers, data=json.dumps(order_data), auth=auth)
            if create_response.status_code == 201:
                sales_order_no = next_no
                break
            elif create_response.status_code == 400:
                try:
                    error_data = create_response.json()
                    if error_data.get("error", {}).get("code") == "Internal_EntityWithSameKeyExists":
                        next_no = increment_order_no(next_no)
                        attempt += 1
                    else:
                        error_msg = f"Failed to create sales order: {create_response.status_code} - {create_response.text}"
                        error_messages.append(error_msg)
                        return {'success': False, 'sales_order_no': None, 'error_messages': error_messages}
                except json.JSONDecodeError:
                    error_msg = f"Failed to create sales order: {create_response.status_code} - {create_response.text}"
                    error_messages.append(error_msg)
                    return {'success': False, 'sales_order_no': None, 'error_messages': error_messages}
            else:
                error_msg = f"Failed to create sales order: {create_response.status_code} - {create_response.text}"
                error_messages.append(error_msg)
                return {'success': False, 'sales_order_no': None, 'error_messages': error_messages}
        else:
            error_msg = f"Failed to create sales order after {max_attempts} attempts."
            error_messages.append(error_msg)
            return {'success': False, 'sales_order_no': None, 'error_messages': error_messages}

    filter_medical = f"$filter=Document_No eq '{sales_order_no}'"
    medical_get_url = f"{nav_url}/Company('{encoded_company}')/MedicalDetails?{filter_medical}"
    medical_response = requests.get(medical_get_url, headers=headers, auth=auth)
    
    work_order_funcs = {
        'insoles': work_order_insole,
        'bespoke': work_order_bespoke,
        'modular': work_order_modular,
        'afos': work_order_afo,
        'a&r': work_order_a_and_r,
        'kafo': work_order_a_and_r,
        'repairs': work_order_repairs,
        'a&m': work_order_adapts_and_modifications
    }
    work_order_func = work_order_funcs.get(form_type.lower())
    target_operation, target_text = work_order_func(auto_doc_ref)
    
    if medical_response.status_code == 200:
        existing_details = medical_response.json()['value']
        matching_details = [
            detail for detail in existing_details
            if detail['Operation'].strip().lower() == target_operation.lower() and
               detail['Medical_Detail_Text'].strip().lower() == target_text.lower()
        ]
        
        if len(matching_details) > 1:
            for detail in matching_details[1:]:
                delete_url = f"{nav_url}/Company('{encoded_company}')/MedicalDetails(Document_No='{sales_order_no}',Line_No={detail['Line_No']})"
                delete_response = requests.delete(delete_url, headers=headers, auth=auth)
                if delete_response.status_code != 204:
                    error_msg = f"Failed to delete duplicate: {delete_response.status_code} - {delete_response.text}"
                    error_messages.append(error_msg)
        elif len(matching_details) == 0:
            next_line_no = 100000 if not existing_details else max(detail['Line_No'] for detail in existing_details) + 10000
            medical_url = f"{nav_url}/Company('{encoded_company}')/MedicalDetails"
            payload = {
                "Document_No": sales_order_no,
                "Line_No": next_line_no,
                "Operation": target_operation,
                "Medical_Detail_Text": target_text
            }
            response = requests.post(medical_url, headers=headers, data=json.dumps(payload), auth=auth)
            if response.status_code != 201:
                error_msg = f"Failed to add medical detail: {response.status_code} - {response.text}"
                error_messages.append(error_msg)
    else:
        error_msg = f"Failed to retrieve medical details: {medical_response.status_code} - {medical_response.text}"
        error_messages.append(error_msg)

    lines_url = f"{nav_url}/Company('{encoded_company}')/SalesOrderLineService"
    if final_codes and len(final_codes) > 0:
        valid_codes = [code for code in final_codes if code.strip() != "```"]
        item_lines = [parse_code_string(code_str) for code_str in valid_codes]

        for item_no, quantity in item_lines:
            filter_lines = f"$filter=Document_No eq '{sales_order_no}' and Document_Type eq 'Order'"
            existing_lines_url = f"{lines_url}?{filter_lines}"
            lines_response = requests.get(existing_lines_url, headers=headers, auth=auth)

            if lines_response.status_code == 200:
                existing_lines = lines_response.json()['value']
                next_line_no = 10000 if not existing_lines else max(line['Line_No'] for line in existing_lines) + 10000
            else:
                error_msg = f"Failed to retrieve existing lines: {lines_response.status_code} - {lines_response.text}"
                error_messages.append(error_msg)
                next_line_no = 10000

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
                error_messages.append(error_msg)

    success = len(error_messages) == 0
    return {'success': success, 'sales_order_no': sales_order_no, 'error_messages': error_messages}

def increment_order_no(order_no):
    match = re.match(r"(GB-SOA)(\d+)", order_no)
    if match:
        prefix, number = match.groups()
        next_number = int(number) + 1
        return f"{prefix}{next_number:05d}"
    else:
        raise ValueError(f"Invalid order number format: {order_no}")
    
def get_next_medical_detail_line_no(document_no, step=10000):
    """Return the next free Line_No for MedicalDetails on the given document.

    Returns `step` if no details exist yet, otherwise the highest existing
    Line_No plus `step`. This prevents work-ticket lines from colliding with
    detail lines already written during create_sales_order (e.g. the
    'Special Instructions' line placed at Line_No 100000).
    """
    filter_medical = f"$filter=Document_No eq '{document_no}'"
    get_url = f"{nav_url}/Company('{encoded_company}')/MedicalDetails?{filter_medical}"
    response = requests.get(get_url, headers=headers, auth=auth)
    if response.status_code == 200:
        existing = response.json().get('value', [])
        if existing:
            return max(detail['Line_No'] for detail in existing) + step
    return step

def post_to_nav_medical_detail(document_no, operation, detail_text, line_no=10000):
    cons_medical_url = f"{nav_url}/Company('{encoded_company}')/MedicalDetails"

    payload = {
        "Document_No": document_no,
        "Line_No": line_no,
        "Operation": operation,
        "Medical_Detail_Text": detail_text
    }

    print(f" Uploading | Document: {document_no} | Operation: {operation}")
    print("Payload being sent:\n" + json.dumps(payload, indent=4))
    response = requests.post(cons_medical_url, headers=headers, data=json.dumps(payload), auth=auth)

    if response.status_code == 201:
        print(f"Successfully uploaded: {operation}")
        return True
    else:
        print(f"Failed to upload: {operation}")
        print(f"Status: {response.status_code}")
        try:
            print(json.dumps(response.json(), indent=4))
        except:
            print(response.text)
        return False