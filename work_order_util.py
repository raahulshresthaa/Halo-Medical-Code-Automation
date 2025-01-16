
import os
import datetime

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
    #   If we have a “base carbon fibre: selected,” then add a line about using carbon fibre
    if data_dict.get("base carbon fibre", "").lower() == "selected":
        stages["Modelling"].append("Use carbon fibre as the base material.")

    #   If we have “base poron: selected,” then add a line about using Poron
    if data_dict.get("base poron", "").lower() == "selected":
        stages["Modelling"].append("Use poron for the base material.")

    # 2) Shaping
    #   If “insole length three quarters: selected” is present
    if data_dict.get("insole length three quarters", "").lower() == "selected":
        stages["Shaping"].append("Trim the insole to three-quarters length.")

    #   If “heel cup medium: selected”
    if data_dict.get("heel cup medium", "").lower() == "selected":
        stages["Shaping"].append("Form a medium heel cup.")

    # 3) Additions / Modification
    #   If we see left 1st met head: selected
    if data_dict.get("left 1st met head", "").lower() == "selected":
        stages["Additions/Modification"].append("Add left 1st met head relief.")
    #   And so on for right 1st met head, 5th met ray, navicular sweet spot, etc.

    # 4) Sticking
    #   If “insole top cover material: Spenco (Green)” is present
    top_cover = data_dict.get("insole top cover material", "").lower()
    if "spenco (green)" in top_cover:
        stages["Sticking"].append("Adhere Spenco (Green) top cover.")

    # 5) Finishing
    #   If “urgent: selected”
    if data_dict.get("urgent", "").lower() == "selected":
        stages["Finishing"].append("Prioritize finishing due to URGENT status.")

    # 6) Quality Check
    #   This is just an example, you might do a final check on certain fields
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
            # In case a stage is empty, you can either skip or show something
            lines.append("  (No instructions for this stage)")
        lines.append("")  # blank line after each stage

    # Join them into a single string
    return "\n".join(lines)


def create_work_order_file(auto_doc_ref, form_type, data_dict=None):
    """
    Creates a text file named 'work_order_<auto_doc_ref>_<form_type>.txt'
    in a folder structure: work_orders/YYYY-MM-DD/work_order_<auto_doc_ref>_<form_type>.txt
    
    By default, writes a work ticket built from the extracted data (if provided).
    """

    # 1. Generate today's date string (e.g. '2025-01-08')
    date_str = datetime.datetime.now().strftime('%Y-%m-%d')

    # 2. Construct the parent folder paths
    work_orders_folder = os.path.join(os.getcwd(), 'work_orders')
    date_folder_path = os.path.join(work_orders_folder, date_str)

    # 3. Create the date folder if it doesn't exist
    if not os.path.exists(date_folder_path):
        os.makedirs(date_folder_path)

    # 4. Build the file name, e.g. "work_order_02342_insole.txt"
    file_name = f"work_order_{auto_doc_ref}_{form_type}.txt"
    file_path = os.path.join(date_folder_path, file_name)

    # Optionally build the ticket if data_dict is given
    work_ticket_text = "test complete, work order written to successfully\n"
    if data_dict:
        # Build the multi-stage instructions
        instructions = build_work_ticket(data_dict)
        work_ticket_text += "\n"
        work_ticket_text += instructions

    # 5. Write our text into the file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(work_ticket_text)

    # 6. Print or return the file path
    print(f"Work order file created at: {file_path}")
