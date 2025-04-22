#NavApi.py
import requests
from requests_ntlm import HttpNtlmAuth
import json
import urllib.parse
import re
import datetime

# --- NAV Configuration ---
nav_url = "http://HALO-APP-UKUS.HALO.local:7048/TEST_DynamicsNAV110/ODataV4"
company = "TEST Medfac UK"
username = "HALO\\hamish.donaldson"
password = "" #add password here

encoded_company = urllib.parse.quote(company)
headers = {
    "Content-Type": "application/json",
    "Accept": "application/json"
}
auth = HttpNtlmAuth(username, password)

# --- Step 1: Get last SOAI number ---
filter_soai = "$filter=startswith(No,'GB-SOAI')&$orderby=No desc&$top=1"
get_url = f"{nav_url}/Company('{encoded_company}')/SalesOrderService?{filter_soai}"
response = requests.get(get_url, headers=headers, auth=auth)

if response.status_code != 200:
    print("❌ Failed to get last SOAI order number")
    print(response.status_code, response.text)
    exit()

last_soai = response.json()['value'][0]['No']
print(f"🔍 Last SOAI Order No: {last_soai}")

# --- Step 2: Increment the SOAI number ---
match = re.match(r"(GB-SOAI)(\d+)", last_soai)
if not match:
    print("❌ Could not parse SOAI number.")
    exit()

prefix, number = match.groups()
next_no = f"{prefix}{int(number)+1:05d}"
print(f"➡️ Creating Sales Order: {next_no}")

# --- Step 3: POST Sales Order Header ---
external_doc_no = f"RS-AI-ORDER-{next_no[-4:]}"
today = datetime.date.today().strftime("%Y-%m-%d")
order_data = {
    "No": next_no,
    "Sell_to_Customer_No": "GB-CUST02175",
    "Order_Date": "2025-04-16",
    "Posting_Date": "2025-04-16",
    "Document_Date": "2025-04-16",
    "External_Document_No": external_doc_no,
    "Order_Category_Code": "MILLED INSOLES",
    "Prescriber": "GB-CONT02946",
    "Send_For": "Send for Finish",
    "Supporting_Items_Arrived_Date": today,
    "PO_Requested_Date": today,
    "PO_Received_Date": today
}

post_url = f"{nav_url}/Company('{encoded_company}')/SalesOrderService"
create_response = requests.post(post_url, headers=headers, data=json.dumps(order_data), auth=auth)

if create_response.status_code == 201:
    print(f"✅ Created Sales Order {next_no}")
else:
    print("❌ Failed to create sales order header:")
    print(create_response.status_code, create_response.text)
    exit()

# --- Step 4: Add Medical Details ---
medical_details = [
    {
        "Operation": "Model Room",
        "Medical_Detail_Text": "Tes for Fin"
    },
    {
        "Operation": "Pattern Room",
        "Medical_Detail_Text": "Use pattern X for shaping"
    },
    {
        "Operation": "Clicking/Closing Room",
        "Medical_Detail_Text": "Ensure closed seam finish"
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
item_nos = ["B54A", "B54C", "B55A"]
print(f"📦 Adding {len(item_nos)} Sales Order Line(s) to: {next_no}")
base_line_no = 10000

for i, item_no in enumerate(item_nos):
    line_data = {
        "Document_Type": "Order",
        "Document_No": next_no,
        "Line_No": base_line_no + i * 10000 * 2, # needs to be x2 since the descroption runs across 2 lines
        "Type": "Item",
        "No": item_no,
        "Quantity": 1,
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