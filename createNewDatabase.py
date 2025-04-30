import requests
from requests_ntlm import HttpNtlmAuth
import urllib.parse

# --- NAV Configuration ---
nav_url = "http://HALO-APP-UKUS.HALO.local:7048/TEST_DynamicsNAV110/ODataV4"
company = "TEST Medfac UK"
username = ""
password = ""

# --- Services ---
header_service = "SalesOrderService"
line_service = "SalesOrderLineService"

# --- Hardcoded Sales Order No ---
order_no = "GB-SO0197388"  # <<< Change this to the Sales Order you want


# --- Encode for URL ---
encoded_company = urllib.parse.quote(company)
encoded_order_no = urllib.parse.quote(order_no)

# --- GET Sales Order Header ---
filter_header = f"$filter=No eq '{order_no}'"
header_url = f"{nav_url}/Company('{encoded_company}')/{header_service}?{filter_header}"

headers = { "Accept": "application/json" }

# --- Fetch Order Header ---
response = requests.get(header_url, headers=headers, auth=HttpNtlmAuth(username, password))

if response.status_code == 200:
    results = response.json().get("value", [])
    if not results:
        print("\n⚠️ Sales Order not found.")
        exit()

    order = results[0]
    print("\n✅ Sales Order Found:")
   
    # Print all fields dynamically
    for key, value in order.items():
        print(f"{key}: {value}")

    # --- GET Sales Lines from separate service using Document_No ---
    filter_lines = f"$filter=Document_No eq '{order_no}'"
    lines_url = f"{nav_url}/Company('{encoded_company}')/{line_service}?{filter_lines}"

    lines_response = requests.get(lines_url, headers=headers, auth=HttpNtlmAuth(username, password))

    if lines_response.status_code == 200:
        lines = lines_response.json().get("value", [])
        print(f"\n📦 Found {len(lines)} Sales Line(s):")
       
        for idx, line in enumerate(lines, start=1):
            print(f"\n🔹 Line {idx}:")
            # Print all fields for each line dynamically
            for key, value in line.items():
                print(f"  {key}: {value}")

    else:
        print("\n❌ Failed to retrieve Sales Lines (separate service):")
        print(lines_response.status_code, lines_response.text)

else:
    print("\n❌ Failed to retrieve Sales Order:")
    print(response.status_code, response.text)