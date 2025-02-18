import os
import datetime
import csv

def sanitize_filename_part(val):
    sanitized = ''.join(c for c in val if c.isalnum() or c in ('_', '-'))
    return sanitized if sanitized else 'unknown'

def build_work_ticket(data_dict):
    stages = {
        "Modelling": [],
        "Shaping": [],
        "Additions/Modification": [],
        "Sticking": [],
        "Finishing": [],
        "Quality Check": []
    }
    if data_dict.get("base carbon fibre", "").lower() == "selected":
        stages["Modelling"].append("Use carbon fibre as the base material.")
    if data_dict.get("base poron", "").lower() == "selected":
        stages["Modelling"].append("Use poron for the base material.")
    if data_dict.get("insole length three quarters", "").lower() == "selected":
        stages["Shaping"].append("Trim the insole to three-quarters length.")
    if data_dict.get("heel cup medium", "").lower() == "selected":
        stages["Shaping"].append("Form a medium heel cup.")
    if data_dict.get("left 1st met head", "").lower() == "selected":
        stages["Additions/Modification"].append("Add left 1st met head relief.")
    top_cover = data_dict.get("insole top cover material", "").lower()
    if "spenco (green)" in top_cover:
        stages["Sticking"].append("Adhere Spenco (Green) top cover.")
    if data_dict.get("urgent", "").lower() == "selected":
        stages["Finishing"].append("Prioritize finishing due to URGENT status.")
    if "fascial accommodation" in "\n".join(data_dict.keys()).lower():
        stages["Quality Check"].append("Check fascial accommodation is correct.")
    lines = []
    lines.append("WORK TICKET INSTRUCTIONS\n")
    for stage_name, instructions in stages.items():
        lines.append(f"{stage_name.upper()}:")
        if instructions:
            for step in instructions:
                lines.append(f"  - {step}")
        else:
            lines.append("  (No instructions for this stage)")
        lines.append("")
    return "\n".join(lines)

def create_work_order_file(auto_doc_ref, form_type, data_dict=None):
    safe_ref = sanitize_filename_part(auto_doc_ref)
    date_str = datetime.datetime.now().strftime('%Y-%m-%d')
    work_orders_folder = os.path.join(os.getcwd(), 'work_orders')
    date_folder_path = os.path.join(work_orders_folder, date_str)
    if not os.path.exists(date_folder_path):
        os.makedirs(date_folder_path)
    file_name = f"work_order_{safe_ref}_{form_type}.csv"
    file_path = os.path.join(date_folder_path, file_name)
    if data_dict:
        work_ticket_text = build_work_ticket(data_dict)
    else:
        work_ticket_text = ""
    lines_to_write = work_ticket_text.split("\n") if work_ticket_text else []
    with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        for line in lines_to_write:
            writer.writerow([line])
    print(f"Work order CSV created at: {file_path}")
