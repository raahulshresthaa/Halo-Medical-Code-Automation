import os
import datetime
import csv

def sanitize_filename_part(val):
    """
    Removes any characters from val that aren't alphanumeric, underscore, or dash.
    Returns 'unknown' if everything is stripped out.
    """
    sanitized = ''.join(c for c in val if c.isalnum() or c in ('_', '-'))
    return sanitized if sanitized else 'unknown'

def build_work_ticket(data_dict):
    """
    Builds a multi-stage work ticket (modelling, shaping, additions/modification,
    sticking, finishing, quality check) based on the extracted Azure data.
    
    Returns a multi-line string with instructions for each stage.
    """

    # Initialize a dict to store instructions by stage
    stages = {
        "Modelling": [],
        "Shaping": [],
        "Additions/Modification": [],
        "Sticking": [],
        "Finishing": [],
        "Quality Check": []
    }

    # -------------------------------
    # Example logic (adjust as needed)
    # -------------------------------

    # 1) Modelling
    if data_dict.get("base carbon fibre", "").lower() == "selected":
        stages["Modelling"].append("Use carbon fibre as the base material.")
    if data_dict.get("base poron", "").lower() == "selected":
        stages["Modelling"].append("Use poron for the base material.")

    # 2) Shaping
    if data_dict.get("insole length three quarters", "").lower() == "selected":
        stages["Shaping"].append("Trim the insole to three-quarters length.")
    if data_dict.get("heel cup medium", "").lower() == "selected":
        stages["Shaping"].append("Form a medium heel cup.")

    # 3) Additions / Modification
    if data_dict.get("left 1st met head", "").lower() == "selected":
        stages["Additions/Modification"].append("Add left 1st met head relief.")

    # 4) Sticking
    top_cover = data_dict.get("insole top cover material", "").lower()
    if "spenco (green)" in top_cover:
        stages["Sticking"].append("Adhere Spenco (Green) top cover.")

    # 5) Finishing
    if data_dict.get("urgent", "").lower() == "selected":
        stages["Finishing"].append("Prioritize finishing due to URGENT status.")

    # 6) Quality Check
    if "fascial accommodation" in "\n".join(data_dict.keys()).lower():
        stages["Quality Check"].append("Check fascial accommodation is correct.")

    # -------------------------------
    # Build the final text output
    # -------------------------------
    lines = []
    lines.append("WORK TICKET INSTRUCTIONS\n")
    for stage_name, instructions in stages.items():
        lines.append(f"{stage_name.upper()}:")
        if instructions:
            for step in instructions:
                lines.append(f"  - {step}")
        else:
            lines.append("  (No instructions for this stage)")
        lines.append("")  # blank line after each stage

    return "\n".join(lines)

def create_work_order_file(auto_doc_ref, form_type, data_dict=None):
    """
    Creates a CSV file named 'work_order_<auto_doc_ref>_<form_type>.csv'
    in a folder structure: work_orders/YYYY-MM-DD/work_order_<auto_doc_ref>_<form_type>.csv
    
    By default, it writes one row per text line from the built work ticket.
    """

    safe_ref = sanitize_filename_part(auto_doc_ref)

    # 1. Generate today's date string
    date_str = datetime.datetime.now().strftime('%Y-%m-%d')

    # 2. Construct the parent folder paths
    work_orders_folder = os.path.join(os.getcwd(), 'work_orders')
    date_folder_path = os.path.join(work_orders_folder, date_str)

    # 3. Create the date folder if it doesn't exist
    if not os.path.exists(date_folder_path):
        os.makedirs(date_folder_path)

    # 4. Build the CSV file name
    file_name = f"work_order_{safe_ref}_{form_type}.csv"
    file_path = os.path.join(date_folder_path, file_name)

    # Optionally build the ticket if data_dict is given; otherwise just produce an empty
    if data_dict:
        work_ticket_text = build_work_ticket(data_dict)
    else:
        work_ticket_text = ""

    # Split the full text into individual lines
    lines_to_write = work_ticket_text.split("\n") if work_ticket_text else []

    # 5. Write out a CSV (one line of text per row)
    with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        for line in lines_to_write:
            writer.writerow([line])

    # 6. Print or return the file path
    print(f"Work order CSV created at: {file_path}")
