# work_order_util.py
import os
import datetime
import csv

# Define base instructions for each form_type and stage
BASE_INSTRUCTIONS = {
    "insole": {
        "Modelling": ["Prepare insole base"],
        "Shaping": ["Shape according to standard insole template"],
        "Additions/Modification": [],
        "Sticking": [],
        "Finishing": [],
        "Quality Check": ["Check insole dimensions"]
    },
    "modular": {
        "Modelling": ["Assemble modular components"],
        "Shaping": ["Adjust modular parts as needed"],
        "Additions/Modification": [],
        "Sticking": [],
        "Finishing": [],
        "Quality Check": ["Verify modular assembly"]
    },
    "bespoke": {
        "Modelling": ["Custom modelling for bespoke item"],
        "Shaping": ["Shape according to bespoke specifications"],
        "Additions/Modification": [],
        "Sticking": [],
        "Finishing": [],
        "Quality Check": ["Ensure bespoke requirements are met"]
    },
    "afo": {
        "Modelling": ["Prepare AFO base"],
        "Shaping": ["Shape AFO according to patient measurements"],
        "Additions/Modification": [],
        "Sticking": [],
        "Finishing": [],
        "Quality Check": ["Check AFO fit and function"]
    }
}

def sanitize_filename_part(val):
    """
    Removes any characters from val that aren't alphanumeric, underscore, or dash.
    Returns 'unknown' if everything is stripped out.
    """
    sanitized = ''.join(c for c in val if c.isalnum() or c in ('_', '-'))
    return sanitized if sanitized else 'unknown'

def build_work_ticket(form_type, data_dict):
    """
    Builds a multi-stage work ticket based on the form_type and extracted Azure data.
    
    Args:
        form_type (str): The type of work ticket ('insole', 'modular', 'bespoke', 'afo')
        data_dict (dict): Dictionary containing form data
    
    Returns:
        str: A multi-line string with instructions for each stage
    """
    # Validate form_type
    if form_type not in BASE_INSTRUCTIONS:
        raise ValueError(f"Unknown form_type: {form_type}")
    
    # Initialize stages with base instructions for the given form_type
    stages = {stage: list(BASE_INSTRUCTIONS[form_type].get(stage, [])) 
              for stage in ["Modelling", "Shaping", "Additions/Modification", 
                            "Sticking", "Finishing", "Quality Check"]}

    # Add specific instructions based on form_type and data_dict
    if form_type == "insole":
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

    elif form_type == "modular":
        # Example logic for modular (customize as needed)
        if data_dict.get("modular component A", "").lower() == "selected":
            stages["Modelling"].append("Include component A in the assembly.")
        if data_dict.get("adjustable joint", "").lower() == "selected":
            stages["Shaping"].append("Incorporate adjustable joint.")
        if data_dict.get("urgent", "").lower() == "selected":
            stages["Finishing"].append("Prioritize finishing due to URGENT status.")

    elif form_type == "bespoke":
        # Example logic for bespoke (customize as needed)
        if data_dict.get("custom design", "").lower() == "selected":
            stages["Modelling"].append("Follow custom design specifications.")
        if data_dict.get("client measurements", ""):
            stages["Shaping"].append(f"Shape to client measurements: {data_dict['client measurements']}")
        if data_dict.get("urgent", "").lower() == "selected":
            stages["Finishing"].append("Prioritize finishing due to URGENT status.")

    elif form_type == "afo":
        # Example logic for AFO (customize as needed)
        if data_dict.get("afo type", "").lower() == "solid":
            stages["Modelling"].append("Use solid AFO design.")
        if data_dict.get("patient height", ""):
            stages["Shaping"].append(f"Adjust height to {data_dict['patient height']} cm.")
        if data_dict.get("urgent", "").lower() == "selected":
            stages["Finishing"].append("Prioritize finishing due to URGENT status.")

    # Build the final text output
    lines = []
    lines.append("WORK TICKET INSTRUCTIONS\n")
    for stage_name in ["Modelling", "Shaping", "Additions/Modification", 
                       "Sticking", "Finishing", "Quality Check"]:
        lines.append(f"{stage_name.upper()}:")
        instructions = stages.get(stage_name, [])
        if instructions:
            for step in instructions:
                lines.append(f"  - {step}")
        else:
            lines.append("  (No instructions for this stage)")
        lines.append("")  # Blank line after each stage

    return "\n".join(lines)

def create_work_order_file(auto_doc_ref, form_type, data_dict=None):
    """
    Creates a CSV file named 'work_order_<auto_doc_ref>_<form_type>.csv'
    in a folder structure: work_orders/YYYY-MM-DD/work_order_<auto_doc_ref>_<form_type>.csv
    
    Args:
        auto_doc_ref (str): Reference identifier for the work order
        form_type (str): Type of work ticket to create
        data_dict (dict, optional): Form data to generate the ticket
    
    Returns:
        None (writes to file and prints the file path)
    """
    safe_ref = sanitize_filename_part(auto_doc_ref)

    # Generate today's date string
    date_str = datetime.datetime.now().strftime('%Y-%m-%d')

    # Construct the parent folder paths
    work_orders_folder = os.path.join(os.getcwd(), 'work_orders')
    date_folder_path = os.path.join(work_orders_folder, date_str)

    # Create the date folder if it doesn't exist
    if not os.path.exists(date_folder_path):
        os.makedirs(date_folder_path)

    # Build the CSV file name
    file_name = f"work_order_{safe_ref}_{form_type}.csv"
    file_path = os.path.join(date_folder_path, file_name)

    # Build the ticket if data_dict is provided; otherwise produce an empty string
    if data_dict:
        work_ticket_text = build_work_ticket(form_type, data_dict)
    else:
        work_ticket_text = ""

    # Split the full text into individual lines
    lines_to_write = work_ticket_text.split("\n") if work_ticket_text else []

    # Write out a CSV (one line of text per row)
    with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        for line in lines_to_write:
            writer.writerow([line])

    # Print the file path
    print(f"Work order CSV created at: {file_path}")