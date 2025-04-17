# work_order_util.py
import os
import datetime
import csv

# Define base instructions for each form_type and new stages
BASE_INSTRUCTIONS = {
    "insole": {
        "Model Room": ["Prepare insole model"],
        "Pattern Room": ["Create pattern for insole"],
        "Clicking/Closing Room": [],
        "Finishing Room": [],
        "Insole Room": ["Assemble insole components"],
        "AFTER FITTING": ["Verify insole fit"]
    },
    "modular": {
        "Model Room": ["Prepare modular model"],
        "Pattern Room": ["Create pattern for modular parts"],
        "Clicking/Closing Room": [],
        "Finishing Room": [],
        "Insole Room": ["Assemble modular components"],
        "AFTER FITTING": ["Verify modular assembly"]
    },
    "bespoke": {
        "Model Room": ["Prepare bespoke model"],
        "Pattern Room": ["Create pattern for bespoke item"],
        "Clicking/Closing Room": [],
        "Finishing Room": [],
        "Insole Room": ["Assemble bespoke components"],
        "AFTER FITTING": ["Verify bespoke fit"]
    },
    "afo": {
        "Model Room": ["Prepare AFO model"],
        "Pattern Room": ["Create pattern for AFO"],
        "Clicking/Closing Room": [],
        "Finishing Room": [],
        "Insole Room": ["Assemble AFO components"],
        "AFTER FITTING": ["Verify AFO fit"]
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
        dict: A dictionary mapping stages to their instructions
    """
    # Validate form_type
    if form_type not in BASE_INSTRUCTIONS:
        raise ValueError(f"Unknown form_type: {form_type}")
    
    # Initialize stages with base instructions for the given form_type
    stages = {stage: list(BASE_INSTRUCTIONS[form_type].get(stage, [])) 
              for stage in ["Model Room", "Pattern Room", "Clicking/Closing Room", 
                            "Finishing Room", "Insole Room", "AFTER FITTING"]}

    # Add specific instructions based on form_type and data_dict
    if form_type == "insole":
        if data_dict.get("base carbon fibre", "").lower() == "selected":
            stages["Model Room"].append("Use carbon fibre as the base material.")
        if data_dict.get("base poron", "").lower() == "selected":
            stages["Model Room"].append("Use poron for the base material.")
        if data_dict.get("insole length three quarters", "").lower() == "selected":
            stages["Pattern Room"].append("Trim the pattern to three-quarters length.")
        if data_dict.get("heel cup medium", "").lower() == "selected":
            stages["Pattern Room"].append("Form a medium heel cup in pattern.")
        if data_dict.get("left 1st met head", "").lower() == "selected":
            stages["Clicking/Closing Room"].append("Add left 1st met head relief during clicking.")
        top_cover = data_dict.get("insole top cover material", "").lower()
        if "spenco (green)" in top_cover:
            stages["Finishing Room"].append("Adhere Spenco (Green) top cover.")
        if data_dict.get("urgent", "").lower() == "selected":
            stages["Finishing Room"].append("Prioritize finishing due to URGENT status.")
        if "fascial accommodation" in "\n".join(data_dict.keys()).lower():
            stages["AFTER FITTING"].append("Check fascial accommodation is correct.")

    elif form_type == "modular":
        if data_dict.get("modular component A", "").lower() == "selected":
            stages["Model Room"].append("Include component A in the model.")
        if data_dict.get("adjustable joint", "").lower() == "selected":
            stages["Pattern Room"].append("Incorporate adjustable joint in pattern.")
        if data_dict.get("urgent", "").lower() == "selected":
            stages["Finishing Room"].append("Prioritize finishing due to URGENT status.")

    elif form_type == "bespoke":
        if data_dict.get("custom design", "").lower() == "selected":
            stages["Model Room"].append("Follow custom design specifications.")
        if data_dict.get("client measurements", ""):
            stages["Pattern Room"].append(f"Shape pattern to client measurements: {data_dict['client measurements']}")
        if data_dict.get("urgent", "").lower() == "selected":
            stages["Finishing Room"].append("Prioritize finishing due to URGENT status.")

    elif form_type == "afo":
        if data_dict.get("afo type", "").lower() == "solid":
            stages["Model Room"].append("Use solid AFO design.")
        if data_dict.get("patient height", ""):
            stages["Pattern Room"].append(f"Adjust pattern height to {data_dict['patient height']} cm.")
        if data_dict.get("urgent", "").lower() == "selected":
            stages["Finishing Room"].append("Prioritize finishing due to URGENT status.")

    return stages

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

    # Build the ticket if data_dict is provided; otherwise use empty instructions
    if data_dict:
        stages = build_work_ticket(form_type, data_dict)
    else:
        stages = {stage: [] for stage in ["Model Room", "Pattern Room", "Clicking/Closing Room", 
                                         "Finishing Room", "Insole Room", "AFTER FITTING"]}

    # Write out a CSV with stages in column A and instructions in column D
    with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        # Write each stage and its instructions
        for stage_name in ["Model Room", "Pattern Room", "Clicking/Closing Room", 
                           "Finishing Room", "Insole Room", "AFTER FITTING"]:
            instructions = stages.get(stage_name, [])
            if instructions:
                for instruction in instructions:
                    writer.writerow([stage_name, "", "", instruction])
            else:
                writer.writerow([stage_name, "", "", "(No instructions for this stage)"])

    # Print the file path
    print(f"Work order CSV created at: {file_path}")