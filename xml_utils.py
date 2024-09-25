# xml_utils.py

import xml.etree.ElementTree as ET
from tkinter import messagebox, simpledialog

def read_xml_file(xml_file_path):
    try:
        with open(xml_file_path, 'r', encoding='utf-8') as file:
            xml_content = file.read()
        return xml_content
    except Exception as e:
        messagebox.showerror("Error", f"Error reading XML file: {str(e)}")
        return None

def extract_form_type_from_xml_string(xml_content):
    try:
        root = ET.fromstring(xml_content)
        modelling = root.find('Modelling')
        if modelling is None:
            messagebox.showerror("Error", "No 'Modelling' element found in XML.")
            return None

        type_element = modelling.find('Type')
        if type_element is None:
            messagebox.showerror("Error", "No 'Type' element found under 'Modelling' in XML.")
            return None

        # Dictionary to map XML tags to form types
        type_mapping = {
            'TCI': 'tci',
            'Simple': 'simple',
            'Cradle': 'cradle',
            'HandMold': 'handmold'
            # Add other mappings as needed
        }

        selected_types = []

        for type_option in type_element:
            tag = type_option.tag
            text = type_option.text.strip() if type_option.text else ''
            print(f"Checking type: {tag}, value: '{text}'")  # Debug statement

            if text.lower() == 'yes':
                form_type = type_mapping.get(tag)
                if form_type:
                    selected_types.append(form_type)
                else:
                    print(f"No mapping found for tag '{tag}'")  # Debug statement

        if not selected_types:
            messagebox.showerror("Error", "No form type marked 'Yes' found in the XML file.")
            return None
        elif len(selected_types) > 1:
            selected_type = simpledialog.askstring(
                "Multiple Types Selected",
                f"Multiple form types are selected: {', '.join(selected_types)}.\nPlease enter the type you want to process:"
            )
            if selected_type and selected_type.lower() in [t.lower() for t in selected_types]:
                return selected_type.lower()
            else:
                messagebox.showerror("Error", "Invalid type selected.")
                return None
        else:
            print(f"Selected form type: {selected_types[0]}")  # Debug statement
            return selected_types[0]
    except Exception as e:
        messagebox.showerror("Error", f"Error parsing XML content: {str(e)}")
        return None

def extract_auto_doc_reference_from_xml_string(xml_content):
    try:
        root = ET.fromstring(xml_content)
        auto_doc_ref_element = root.find('.//AutoDocRef')
        if auto_doc_ref_element is not None and auto_doc_ref_element.text:
            return auto_doc_ref_element.text.strip()
        else:
            return None
    except Exception as e:
        messagebox.showerror("Error", f"Error extracting auto doc reference: {str(e)}")
        return None

def extract_clinic_from_xml_string(xml_content):
    try:
        root = ET.fromstring(xml_content)
        clinic_element = root.find('.//Clinic')
        if clinic_element is not None and clinic_element.text:
            return clinic_element.text.strip()
        else:
            return None
    except Exception as e:
        messagebox.showerror("Error", f"Error extracting clinic: {str(e)}")
        return None
