import os
import openai
import base64
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, Toplevel
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from PIL import Image, ImageTk
import datetime
import threading
import sys
# Import TkinterDnD for drag-and-drop functionality
import tkinterdnd2
from tkinterdnd2 import DND_FILES, TkinterDnD
from collections import defaultdict
from work_order_util import create_work_order_file

# Version number
VERSION = "5.0.0-dev"

# To fix blurriness on some displays
try:
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

# Azure Form Recognizer imports
from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient

 
def get_form_type_from_model_id(model_id):
    """
    Returns a friendly string for naming files, 
    based on the provided model_id.
    """
    mapping = {
        'InsoleReaderFullV3': 'insole',
        'AfoReaderV7': 'afo',
        'BespokeReaderFullV1': 'bespoke',
        'ModularReaderFullV3': 'modular'
    }
    return mapping.get(model_id, 'unknown')

# --- PdfButtonHandler Class Definition ---

class PdfButtonHandler:
    def __init__(self, root, result_text, auto_doc_ref_entry, datetime_entry, clinic_entry,
             show_loading_popup, close_loading_popup, display_results, model_id_var):
        self.root = root
        self.result_text = result_text
        self.auto_doc_ref_entry = auto_doc_ref_entry
        self.datetime_entry = datetime_entry
        self.clinic_entry = clinic_entry
        self.show_loading_popup = show_loading_popup
        self.close_loading_popup = close_loading_popup
        self.display_results = display_results
        self.model_id_var = model_id_var

        # Reference to the upload PDF button (will be set later)
        self.upload_pdf_button = None

        # Read Azure credentials from files
        self.endpoint = self.read_azure_credential_file('azure_endpoint.txt', 'Azure Endpoint')
        self.key = self.read_azure_credential_file('azure_key.txt', 'Azure Key')

        # Validate endpoint and key
        if not self.endpoint or not isinstance(self.endpoint, str):
            raise ValueError("Azure endpoint is not set or is not a valid string.")
        if not self.key or not isinstance(self.key, str):
            raise ValueError("Azure key is not set or is not a valid string.")

        # Initialize Azure Form Recognizer client
        self.document_analysis_client = DocumentAnalysisClient(
            endpoint=self.endpoint,
            credential=AzureKeyCredential(self.key)
        )

    def set_upload_pdf_button(self, button):
        self.upload_pdf_button = button

    def read_azure_credential_file(self, filename, credential_name):
        """Reads and decodes the Azure credential from a file."""
        file_path = os.path.join(os.getcwd(), filename)
        if os.path.exists(file_path):
            try:
                with open(file_path, 'rb') as f:
                    # Read the encoded binary data and decode it back to a string
                    encoded_data = f.read()
                    decoded_data = base64.b64decode(encoded_data).decode('utf-8').strip()
                if not decoded_data:
                    raise ValueError(f"{credential_name} file is empty.")
                return decoded_data
            except Exception as e:
                messagebox.showerror("Error", f"Error reading {credential_name}: {str(e)}")
                sys.exit()
        else:
            # Prompt the user to enter the credential if the file doesn't exist
            credential = simpledialog.askstring(f"{credential_name} Required", f"Please enter your {credential_name}:")
            if not credential:
                messagebox.showerror("Error", f"No {credential_name} entered. The application will exit.")
                sys.exit()
            # Write the new credential to the file
            self.write_azure_credential_file(filename, credential.strip())
            return credential.strip()

    def write_azure_credential_file(self, filename, credential):
        """Encodes and writes the Azure credential to a file."""
        file_path = os.path.join(os.getcwd(), filename)
        # Encode the credential as bytes, then convert it to Base64 for binary storage
        encoded_data = base64.b64encode(credential.encode('utf-8'))
        with open(file_path, 'wb') as f:
            f.write(encoded_data)
        print(f"{filename} saved to {file_path}")

    def read_logic_file(self, logic_file_path):
        try:
            with open(logic_file_path, 'r', encoding='utf-8') as logic_file:
                logic_content = logic_file.read()
            return logic_content
        except Exception as e:
            return f"Error reading the logic file '{logic_file_path}': {str(e)}"

    def get_price_codes_from_content(self, content, logic_content):
        try:
            # Send the content, logic, and file context to the assistant
            response = openai.ChatCompletion.create(
                model="gpt-4o-2024-08-06",  # Use the appropriate model
                messages=[
                    {"role": "system", "content": f"Use the following logic to generate price codes:\n\n{logic_content}\n\nThe 'Passed code' section contains codes that have already been generated and should be included in the final output.\n\nWrite your full working out and then write **Final Codes:** and output the final codes on a single line, including the passed codes."},
                    {"role": "user", "content": f"Here is the content to process:\n{content}"}
                ],
                max_tokens=1000,  # Adjust as necessary
                temperature=0.1  # Adjust as needed
            )

            # Extract the assistant's response (price codes)
            assistant_response = response['choices'][0]['message']['content']
            return assistant_response
        except Exception as e:
            return f"Error: {str(e)}"

    def process_api_call(self, content, logic_content, AutoDocRef, clinic):
        try:
            # Get the price codes by sending the content, logic, and file context to OpenAI
            price_codes = self.get_price_codes_from_content(content, logic_content)

            # Debug print to check the content of price_codes
            print(f"Price codes received: {price_codes}")

            model_id = self.model_id_var.get()
            form_type_for_filename = get_form_type_from_model_id(model_id)

            # Get the current date and time
            current_datetime = datetime.datetime.now()
            formatted_datetime = current_datetime.strftime('%Y-%m-%d %H:%M:%S')

            # Determine if we should check for base and special base
            model_id = self.model_id_var.get()
            if model_id == 'InsoleReaderFullV3':
                # Check for base in the extracted content and get the query message
                query_message = self.check_for_base(content)

            else:
                query_message = None

            # Combine all messages
            messages = []
            if query_message:
                messages.append(query_message)
            combined_messages = '\n'.join(messages) if messages else None

            # Update the GUI with the results (must be done in the main thread)
            self.root.after(0, self.display_results, formatted_datetime, AutoDocRef, clinic, price_codes, combined_messages)

            # Write the price codes, auto doc reference, clinic, Azure data, and messages to the log file
            self.write_to_log_file(price_codes, AutoDocRef, clinic, content, form_type_for_filename, combined_messages)

        except Exception as e:
            # Show error message in the main thread
            self.root.after(0, messagebox.showerror, "Error", f"Error processing the file: {str(e)}")
        finally:
            # Close the loading pop-up when done
            self.root.after(0, self.close_loading_popup)
            # Re-enable the upload button
            self.root.after(0, lambda: self.upload_pdf_button.config(state='normal'))

    def write_to_log_file(self, price_codes, auto_doc_ref, clinic, azure_data, form_type, messages=None):
        try:
            result_logs_folder = os.path.join(os.getcwd(), 'result_logs')
            if not os.path.exists(result_logs_folder):
                os.makedirs(result_logs_folder)

            current_datetime = datetime.datetime.now()
            formatted_date = current_datetime.strftime('%Y-%m-%d')  # Format: YYYY-MM-DD

            # Create a new folder inside 'result_logs' with the day's date
            date_folder_path = os.path.join(result_logs_folder, formatted_date)
            if not os.path.exists(date_folder_path):
                os.makedirs(date_folder_path)

            # Sanitize the auto_doc_ref to create a valid filename
            sanitized_auto_doc_ref = ''.join(c for c in auto_doc_ref if c.isalnum() or c in ('_', '-')).strip()
            if not sanitized_auto_doc_ref:
                sanitized_auto_doc_ref = 'log'

            # Use the auto_doc_ref as the filename
            log_file_name = f"results_log_{sanitized_auto_doc_ref}_{form_type}.txt"
            log_file_path = os.path.join(date_folder_path, log_file_name)

            with open(log_file_path, 'w', encoding='utf-8') as log_file:
                formatted_datetime = current_datetime.strftime('%Y-%m-%d %H:%M:%S')

                log_file.write(f"Date and Time: {formatted_datetime}\n")
                log_file.write(f"Auto Doc Reference: {auto_doc_ref}\n")
                log_file.write(f"Clinic: {clinic}\n\n")
                log_file.write(f"AZURE EXTRACTED DATA:\n\n{azure_data}\n\n")  # Azure log data

                # Include any messages (query or warning) if they exist
                if messages:
                    log_file.write(f"MESSAGES:\n{messages}\n\n")

                log_file.write(f"PRICE CODES:\n\n{price_codes}\n")
                log_file.write("-" * 50 + "\n")  # Separator between entries
            print(f"Successfully wrote to log file at {log_file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Error writing to log file: {str(e)}")

    def parse_extracted_data(self, data_dict):
        """Convert extracted data into a string format suitable for processing."""
        lines = []
        for key, value in data_dict.items():
            lines.append(f"{key}: {value}")
        return "\n".join(lines)

    def upload_pdf_file(self):
        # Open a file dialog for selecting PDF files
        pdf_file_path = filedialog.askopenfilename(title="Select the PDF File", filetypes=[("PDF Files", "*.pdf")])

        if pdf_file_path:
            # Disable the upload button to prevent multiple clicks
            self.upload_pdf_button.config(state='disabled')

            try:
                # Show the loading pop-up with animation
                self.show_loading_popup()

                # Start processing the PDF file in a separate thread
                threading.Thread(target=self.process_pdf_and_call_api, args=(pdf_file_path,)).start()

            except Exception as e:
                messagebox.showerror("Error", f"Error processing the file: {str(e)}")
                self.upload_pdf_button.config(state='normal')  # Re-enable the upload button
                self.close_loading_popup()  # Ensure the loading pop-up is closed if an error occurs
        else:
            messagebox.showinfo("No PDF File Selected", "Please select a PDF file to process.")

    def process_pdf_and_call_api(self, pdf_file_path):
        try:
            # Get the current model_id
            model_id = self.model_id_var.get()
            print(f"Using model ID: {model_id}")  # Debug print

            #   Define form_type_for_filename here
            form_type_for_filename = get_form_type_from_model_id(model_id)

            # Analyze the PDF using Azure Form Recognizer
            with open(pdf_file_path, "rb") as pdf_file:
                poller = self.document_analysis_client.begin_analyze_document(model_id, document=pdf_file)
                result = poller.result()

            # After reading and analyzing the file, update the loading message
            self.root.after(0, self.update_loading_message, "Please wait, calculating the codes")

            # Extract fields from the result
            fields_data = self.extract_fields_from_result(result)

            if not fields_data:
                raise ValueError("No data extracted from the PDF.")

            # Convert extracted data to text format
            content = self.parse_extracted_data(fields_data)
            print(f"Extracted content: {content}")

            # Extract AutoDocRef and Clinic from the data
            AutoDocRef = fields_data.get('AutoDocRef', 'N/A')
            clinic = fields_data.get('Clinic', 'N/A')

            # Logic file mapping based on model_id and form_type
            logic_file_name = None

            if model_id == 'InsoleReaderFullV3':
                # Determine form_type based on extracted data
                form_type = self.determine_form_type(fields_data)
                if not form_type:
                    query_message = "No form type found in the extracted data. Please raise a query."
                    self.root.after(0, messagebox.showinfo, "Query", query_message)          

                    # Instead of returning, default to TCI so that we can still generate codes
                    form_type = 'tci'  


                # Sanitize form_type
                form_type = ''.join(char for char in form_type if char.isalnum() or char in ('_', '-')).lower()
                print(f"Form type: {form_type}")

                # Construct the logic file name based on the form type
                logic_file_mapping = {
                    'tci': 'tci_logic.txt',
                    'simple': 'simple_insole_logic.txt',
                    'cradle': 'tci_logic.txt',   # Using tci_logic.txt for cradle
                    'handmold': 'tci_logic.txt'  # Using tci_logic.txt for handmold
                }

                logic_file_name = logic_file_mapping.get(form_type)
                print(f"Logic file name: {logic_file_name}")
                if not logic_file_name:
                    raise ValueError(f"No logic file mapping found for form type '{form_type}'.")

                # Insert the new code here
                # Call the insole code generation method
                passed_codes = self.generate_insole_codes(content)
                if passed_codes:
                    # Append the passed codes under 'Passed code:' in the content
                    content += f"\n\nPassed code:\n{passed_codes}"
                    print(f"Passed codes added to content: {passed_codes}")
                else:
                    print("No passed codes generated.")

            elif model_id == 'AfoReaderV7':
                logic_file_name = 'afo_logic.txt'
                print(f"Logic file name: {logic_file_name}")

                # Call the AFO code generation method
                passed_codes = self.generate_afo_codes(content)
                if passed_codes:
                    # Append the passed codes under 'Passed code:' in the content
                    content += f"\n\nPassed code:\n{passed_codes}"
                    print(f"Passed codes added to content: {passed_codes}")
                else:
                    print("No passed codes generated.")

            elif model_id == 'BespokeReaderFullV1':
                logic_file_name = 'bespoke_logic.txt'
                print(f"Logic file name: {logic_file_name}")

                # Call the bespoke code generation method
                passed_codes = self.generate_bespoke_codes(content)
                if passed_codes:
                    # Append the passed codes under 'Passed code:' in the content
                    content += f"\n\nPassed code:\n{passed_codes}"
                    print(f"Passed codes added to content: {passed_codes}")
                else:
                    print("No passed codes generated.")

            elif model_id == 'ModularReaderFullV3':
                logic_file_name = 'modular_logic.txt'
                print(f"Logic file name: {logic_file_name}")

                # Call the modular code generation method
                passed_codes = self.generate_modular_codes(content)
                if passed_codes:
                    # Append the passed codes under 'Passed code:' in the content
                    content += f"\n\nPassed code:\n{passed_codes}"
                    print(f"Passed codes added to content: {passed_codes}")
                else:
                    print("No passed codes generated.")

            else:
                raise ValueError(f"Unknown model ID '{model_id}'.")

            logic_file_path = os.path.join(os.getcwd(), 'logic_folder', logic_file_name)
            print(f"Logic file path: {logic_file_path}")

            # Read the logic file
            logic_content = self.read_logic_file(logic_file_path)
            if "Error" in logic_content:
                raise ValueError(logic_content)

            # Call the API with the content
            self.process_api_call(content, logic_content, AutoDocRef, clinic)

            create_work_order_file(AutoDocRef, form_type_for_filename, data_dict=fields_data)

            print(f"Created a work order file automatically for AutoDocRef: {AutoDocRef} and form type: {form_type_for_filename}")

        except Exception as e:
            # Show error message in the main thread
            self.root.after(0, messagebox.showerror, "Error", f"Error processing the PDF file: {str(e)}")
            # Re-enable the upload button
            self.root.after(0, lambda: self.upload_pdf_button.config(state='normal'))
            # Close the loading pop-up
            self.root.after(0, self.close_loading_popup)

    def extract_fields_from_result(self, result):
        """Extract relevant fields from Azure analysis result."""
        fields_data = {}
        for document in result.documents:
            for name, field in document.fields.items():
                field_value = field.value if field.value else field.content
                if field_value and str(field_value).lower() not in ['none', 'unselected']:
                    fields_data[name.strip()] = field_value.strip()
        return fields_data

    def determine_form_type(self, data):
        """Determine the form type based on the extracted data."""
        # Assuming form_type is indicated by keys like 'tci test' or 'simple test' etc.
        form_type = None
        for key, value in data.items():
            if key.lower() == 'insole type tci' and value.lower() == 'selected':
                form_type = 'tci'
                break
            elif key.lower() == 'insole type simple' and value.lower() == 'selected':
                form_type = 'simple'
                break
            elif key.lower() == 'insole type hand mould' and value.lower() == 'selected':
                form_type = 'handmold'
                break
            elif key.lower() == 'insole type cradle' and value.lower() == 'selected':
                form_type = 'cradle'
                break
            elif key.lower() == 'afo' and value.lower() == 'selected':
                form_type = 'afo'
                break
            elif key.lower() == 'kafo' and value.lower() == 'selected':
                form_type = 'kafo'
                break
            # Add other form types as needed
        return form_type

    def update_loading_message(self, new_message):
        """Update the loading pop-up message."""
        global base_message
        base_message = new_message
        loading_label.config(text=f"{base_message}\n{dot_index * '.'}")

    def handle_drop(self, event):
        """Handle files dropped into the result_text widget."""
        # event.data contains the list of files dropped
        # It may contain multiple files separated by spaces or newlines
        files = self.root.tk.splitlist(event.data)
        pdf_files = [f for f in files if f.lower().endswith('.pdf')]
        if pdf_files:
            for pdf_file in pdf_files:
                # Disable the upload button to prevent multiple clicks
                self.upload_pdf_button.config(state='disabled')
                try:
                    # Show the loading pop-up with animation
                    self.show_loading_popup()

                    # Start processing each PDF file in a separate thread
                    threading.Thread(target=self.process_pdf_and_call_api, args=(pdf_file,)).start()
                except Exception as e:
                    messagebox.showerror("Error", f"Error processing the file: {str(e)}")
                    self.upload_pdf_button.config(state='normal')  # Re-enable the upload button
                    self.close_loading_popup()  # Ensure the loading pop-up is closed if an error occurs
        else:
            messagebox.showinfo("No PDF Files", "Please drop PDF files only.")

    def check_for_base(self, data):
        data_lower = data.lower()
        if not any(keyword in data_lower for keyword in ['base:', 'carbon fibre:', 'poron:']):
            query_message = "No base, Carbon Fibre, or Poron found in the form. Please raise a query."
            self.root.after(0, messagebox.showinfo, "Query", query_message)
            return query_message
        else:
            return None  # No query needed
        
    def generate_bespoke_codes(self, content):
        """Generates codes based on the content for the Bespoke model, counting duplicates."""
        from collections import defaultdict
        passed_codes = defaultdict(int)  # Use defaultdict to count occurrences

        # Define lists of clinics for each insole tariff code (edit these lists as needed)
        tariff_tci_clinics = ['east surrey', 'bury cdc', 'ely', 'hinchingbrooke', 'pch', 'peterborough city hospital', 'sudbury', 'w.s.h', 'ws', 'wsh', 'stamford', 'pch diab']
        tariff_simple_clinics = ['bury cdc', 'ely', 'harpenden', 'hinchingbrooke', 'pch', 'peterborough city hospital', 'sudbury', 'w.s.h', 'ws', 'wsh', 'stamford', 'pch diab']
        tariff_polyprop_clinics = ['east surrey', 'bury cdc', 'ely', 'hinchingbrooke', 'pch', 'peterborough city hospital', 'sudbury', 'w.s.h', 'ws', 'wsh', 'stamford', 'pch diab']

        # Define list of clinics for Tariff Bespoke
        tariff_bespoke_clinics = ['bury cdc', 'east surrey', 'sudbury', 'w.s.h', 'ws', 'wsh']

        # Split the content into lines for easier processing
        lines = content.split('\n')

        # Convert lines to a dictionary
        content_dict = {}
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                content_dict[key.strip().lower()] = value.strip().lower()

        clinic_name = content_dict.get('clinic', '').lower()

        # Check if it's a pair
        is_pair = content_dict.get('pair', '') == 'selected' or content_dict.get('insole pair', '') == 'selected'

        # Track if tariffs were added
        bespoke_tariff_added = False
        insole_tariff_added = False

        # Determine insole type
        insole_type = None
        if content_dict.get('insole type tci', '') == 'selected':
            insole_type = 'tci'
        elif content_dict.get('insole type cradle', '') == 'selected':
            insole_type = 'cradle'
        elif content_dict.get('insole type simple', '') == 'selected':
            insole_type = 'simple'
        elif content_dict.get('insole type handmould', '') == 'selected':
            insole_type = 'handmould'

        # --- Medway Tariffs for Bespoke ---
        # If medway:
        # - If simple: add MEDBNS71
        # - Otherwise: add MEDBNS72
        # In all cases: add MEDFOOTWEAR
        # Don't return immediately, continue logic and filter at the end
        if clinic_name == 'medway':
            if insole_type == 'simple':
                passed_codes['MEDBNS71'] += 1
            else:
                passed_codes['MEDBNS72'] += 1
            passed_codes['MEDFOOTWEAR'] += 1
            bespoke_tariff_added = True
            insole_tariff_added = True

        # Bespoke Tariff Check
        if clinic_name in tariff_bespoke_clinics:
            passed_codes['Tariff Bespoke'] += 1
            bespoke_tariff_added = True

        # Insole Tariff Checks
        if clinic_name in tariff_tci_clinics:
            passed_codes['Tariff TCI'] += 1
            if is_pair:
                passed_codes['Tariff TCI'] *= 2
            insole_tariff_added = True
        elif clinic_name in tariff_simple_clinics:
            passed_codes['Tariff Simple'] += 1
            if is_pair:
                passed_codes['Tariff Simple'] *= 2
            insole_tariff_added = True
        elif clinic_name in tariff_polyprop_clinics:
            passed_codes['Tariff Polyprop'] += 1
            if is_pair:
                passed_codes['Tariff Polyprop'] *= 2
            insole_tariff_added = True

        # Style-based logic
        style = content_dict.get('style', '').lower()

        a1b_styles = {
            'trent', 'selby', 'hallam', 'totnes', 'tenby', 'chelsea', 'galway', 'vienna',
            'truro', 'colwyn', 'lineham', 'hove', 'plymouth', 'drayton', 'sneaker',
            'greenock', 'olympic', 'melton', 'hendon', 'stirling', 'exeter', 'chester',
            'kelso', 'dover', 'shelwyck', 'mowbray', 'shelby'
        }

        a1a_styles = {
            'bumper', 'whitby', 'tralee', 'rockingham', 'perth', 'rockliffe',
            'dundee', 'brigg', 'elgin', 'highland'
        }

        if style in a1b_styles:
            passed_codes['A1B'] += 1
        elif style in a1a_styles:
            passed_codes['A1A'] += 1

        # Add logic for 'pop cast'
        if content_dict.get('pop cast', '') == 'selected':
            passed_codes['A1K'] += 1

        # Backup logic for 'A1A' and 'A1B'
        if 'A1A' not in passed_codes and 'A1B' not in passed_codes:
            type_code_mapping = {
                'type boots': 'A1A',
                'type bootee': 'A1A',
                'type shoes': 'A1B',
                'type sports': 'A1B',
            }
            for key, code in type_code_mapping.items():
                if content_dict.get(key, '') == 'selected':
                    passed_codes[code] += 1

        # Default to 'A1A' if neither 'A1A' nor 'A1B' is present
        if 'A1A' not in passed_codes and 'A1B' not in passed_codes:
            passed_codes['A1A'] += 1

        base = content_dict.get('base', '').strip().lower()
        normalized_base = base.replace(' ', '').lower()

        addition_positions = [
            'left 1st addition', 'left 2nd addition', 'left 3rd addition', 'left 4th addition',
            'right 1st addition', 'right 2nd addition', 'right 3rd addition', 'right 4th addition'
        ]

        addition_code_mapping = {
            'A45_B41': {
                'valgus pad', 'metatarsal pad', 'metatarsal bar', 'balance pad',
                'heel pad', 'cuboid pad', 'cobra pad', 'neuroma pad',
                'sulcus crest', 'arch fill'
            },
            'A45_B56': {
                "morton's extension", "reverse morton's extension", 'poron forefoot'
            },
            'A45_B43': {'kinetic wedge', 'heel raise'},
            'D8A': {'neurological footplate'},
            'BNS45': {'recess', 'hole & plug'},
            'A20_B20': {'rigid 1st extension'},
            'A46_B50': {'partial toe block'},
            'A47_B51': {'full toe block'}
        }

        # Additions
        for key in addition_positions:
            addition_value = content_dict.get(key, '')
            if addition_value:
                if addition_value in addition_code_mapping['A45_B41']:
                    code = 'A45' if insole_type == 'cradle' else 'B41'
                    passed_codes[code] += 1
                elif addition_value in addition_code_mapping['A45_B56']:
                    code = 'A45' if insole_type == 'cradle' else 'B56'
                    passed_codes[code] += 1
                elif addition_value in addition_code_mapping['A45_B43']:
                    code = 'A45' if insole_type == 'cradle' else 'B43'
                    passed_codes[code] += 1
                elif addition_value in addition_code_mapping['D8A']:
                    passed_codes['D8A'] += 1
                elif addition_value in addition_code_mapping['BNS45']:
                    passed_codes['BNS45'] += 1
                elif addition_value in addition_code_mapping['A20_B20']:
                    code = 'A20' if insole_type == 'cradle' else 'B20'
                    passed_codes[code] += 1
                elif addition_value in addition_code_mapping['A46_B50']:
                    code = 'A46' if insole_type == 'cradle' else 'B50'
                    passed_codes[code] += 1
                elif addition_value in addition_code_mapping['A47_B51']:
                    code = 'A47' if insole_type == 'cradle' else 'B51'
                    passed_codes[code] += 1

        # Foot modifications
        foot_modifications = [
            'cut out and additions',
            '1st met head',
            '1st met ray',
            '5th met ray',
            'navicular sweet spot',
            'fascial accommodation',
            'heel flange'
        ]

        for side in ['left', 'right']:
            for mod in foot_modifications:
                key = f"{side} {mod}"
                if content_dict.get(key, '') == 'selected':
                    passed_codes['BNS45'] += 1

        posting_keys = [
            'left medial rearfoot posting',
            'left lateral rearfoot posting',
            'right medial rearfoot posting',
            'right lateral rearfoot posting',
            'left medial forefoot posting',
            'left lateral forefoot posting',
            'right medial forefoot posting',
            'right lateral forefoot posting',
        ]

        for key in posting_keys:
            if content_dict.get(key, '') == 'selected':
                code = 'A45' if insole_type == 'cradle' else 'B56'
                passed_codes[code] += 1

        # Sole Stiffeners
        stiffener_keys = {
            'sole stiffeners left carbon fibre': 'A20',
            'sole stiffeners right carbon fibre': 'A20',
            'sole stiffeners left steel': 'A22',
            'sole stiffeners right steel': 'A22'
        }

        for key, code in stiffener_keys.items():
            if content_dict.get(key, '') == 'selected':
                passed_codes[code] += 1

        # Sole Additions
        sole_addition_keys = {
            'sole additions left toe tips': 'A23',
            'sole additions right toe tips': 'A23',
            'sole additions left toe caps': 'A24',
            'sole additions right toe caps': 'A24',
            'sole additions left stick on soles': 'A25',
            'sole additions right stick on soles': 'A25'
        }

        for key, code in sole_addition_keys.items():
            if content_dict.get(key, '') == 'selected':
                passed_codes[code] += 1

        if content_dict.get('fastening', '') == 'boa':
            passed_codes['Twist Fasten'] += 1

        if content_dict.get('lining material', '') == 'white sheepskin':
            passed_codes['A18A'] += 1

        if content_dict.get('sole material', '') == 'commando':
            passed_codes['A6'] += 1

        stiffeners_materials = {
            'stiffeners left materials': 'A15',
            'stiffeners right materials': 'A15'
        }

        for key, code in stiffeners_materials.items():
            if content_dict.get(key, '') in ('grey poron', 'pink poron', 'foam'):
                passed_codes[code] += 1

        # Stiffeners Checks
        # Left side
        left_a16_count = 0
        if content_dict.get('stiffeners left medial', '') == 'selected':
            left_a16_count += 1
        if content_dict.get('stiffeners left lateral', '') == 'selected':
            left_a16_count += 1

        if content_dict.get('stiffeners left type', '') in ('elongated', 'high'):
            if left_a16_count > 1:
                left_a16_count = 1
        if left_a16_count > 0:
            passed_codes['A16'] += left_a16_count

        # Right side
        right_a16_count = 0
        if content_dict.get('stiffeners right medial', '') == 'selected':
            right_a16_count += 1
        if content_dict.get('stiffeners right lateral', '') == 'selected':
            right_a16_count += 1

        if content_dict.get('stiffeners right type', '') in ('elongated', 'high'):
            if right_a16_count > 1:
                right_a16_count = 1
        if right_a16_count > 0:
            passed_codes['A16'] += right_a16_count

        sockets_type_a = {
            'sockets left type': 'A37A',
            'sockets right type': 'A37A'
        }

        for key, code in sockets_type_a.items():
            if content_dict.get(key, '') in (
                '5/16 round socket', '1/4inc round socket', 'small rectangular', 'large rectangular', 'rizzoli'
            ):
                passed_codes[code] += 1

        sockets_type_b = {
            'sockets left type': 'A37B',
            'sockets right type': 'A37B'
        }

        for key, code in sockets_type_b.items():
            if content_dict.get(key, '') in ('5/16 with backstop', '1/4 with backstop'):
                passed_codes[code] += 1

        # Wedges
        wedges_heel_keys = [
            'wedges left heel medial',
            'wedges left heel lateral',
            'wedges right heel medial',
            'wedges right heel lateral',
        ]

        for key in wedges_heel_keys:
            if content_dict.get(key, '') == 'selected':
                passed_codes['A31'] += 1

        wedges_sole_keys = [
            'wedges left sole medial',
            'wedges left sole lateral',
            'wedges right sole medial',
            'wedges right sole lateral',
        ]

        for key in wedges_sole_keys:
            if content_dict.get(key, '') == 'selected':
                passed_codes['A19'] += 1

        # Floated
        floated_heel_keys = [
            'floated left heel medial',
            'floated left heel lateral',
            'floated right heel medial',
            'floated right heel lateral',
        ]

        for key in floated_heel_keys:
            if content_dict.get(key, '') == 'selected':
                passed_codes['A31'] += 1

        floated_sole_keys = [
            'floated left sole medial',
            'floated left sole lateral',
            'floated right sole medial',
            'floated right sole lateral',
        ]

        for key in floated_sole_keys:
            if content_dict.get(key, '') == 'selected':
                passed_codes['A26'] += 1

        # Raises - to do the 25mm+ codes 
        for side in ['left', 'right']:
            raise_inside_key = f'raise {side} inside'
            raise_outside_key = f'raise {side} outside'
            raise_material_key = f'raise {side} material'

            raise_material = content_dict.get(raise_material_key, '')

            if content_dict.get(raise_inside_key, '') == 'selected':
                if raise_material in ('ld eva', 'lightweight p/zote (non-covered)', 'lightweight p/zote (covered)', 'cork'):
                    passed_codes['A8'] += 1

            if content_dict.get(raise_outside_key, '') == 'selected':
                if raise_material == 'ld eva':
                    passed_codes['A13A'] += 1
                elif raise_material in ('lightweight p/zote (non-covered)', 'lightweight p/zote (covered)'):
                    passed_codes['A12A'] += 1

        # Elongations
        elongations_keys = ['elongations left type', 'elongations right type']
        for key in elongations_keys:
            if content_dict.get(key, '') in ('full', 'half'):
                passed_codes['A31'] += 1

        # Rocker
        rocker_keys = ['rocker left type', 'rocker right type']
        for key in rocker_keys:
            if content_dict.get(key, '') in ('plr', 'standard', 'two point'):
                passed_codes['A19'] += 1

        # Straps
        for side in ['left', 'right']:
            strap_type_key = f'straps {side} type'
            strap_double_decker_key = f'straps {side} double decker'

            strap_type = content_dict.get(strap_type_key, '')
            strap_double_decker = content_dict.get(strap_double_decker_key, '')

            if strap_double_decker == 'selected':
                if strap_type in ('t strap', 'y strap'):
                    passed_codes['A39'] += 1
            else:
                if strap_type in ('t strap', 'y strap'):
                    passed_codes['A38'] += 1

            if strap_type in ('spur retaining strap', 'heel retaining strap'):
                passed_codes['A40'] += 1

        # Insole coding section - MATHS!
        x = 0
        if insole_type == 'simple':
            x -= 1
        if content_dict.get('lining to shell', '') == 'selected':
            x += 1
        if content_dict.get('lining to sulcus', '') == 'selected':
            x += 1
        if content_dict.get('lining full', '') == 'selected':
            x += 1
        if content_dict.get('insole top cover material', '') == 'spenco (green)':
            x += 1
        if content_dict.get('base', '') in ('35/20/80 sh', '45/30/80 sh'):
            x += 1

        if x >= 2:
            code = 'A44C' if insole_type == 'cradle' else 'B55C'
            passed_codes[code] += 1
        elif x == 1:
            code = 'A44B' if insole_type == 'cradle' else 'B55B'
            passed_codes[code] += 1
        elif x == 0:
            code = 'A44A' if insole_type == 'cradle' else 'B55A'
            passed_codes[code] += 1

        normalized_base = base.replace(' ', '').lower()
        shore_bases = {'40shore', '50shore', '65shore', '35/20/80sh', '45/30/80sh'}

        if insole_type == 'cradle':
            if normalized_base in shore_bases:
                passed_codes['A10'] += 1
            elif normalized_base == 'polypropylene':
                passed_codes['A10'] += 1
        elif insole_type in ('tci', 'simple', 'handmould'):
            if normalized_base == 'polypropylene':
                passed_codes['B54B'] += 1
            else:
                passed_codes['B54C'] += 1

        if content_dict.get('base poron', '') == 'selected':
            passed_codes['B40B'] += 1

        if content_dict.get('base carbon fibre', '') == 'selected':
            passed_codes['B54A'] += 1

        # Pair Handling for normal codes
        if content_dict.get('insole pair', '') == 'selected':
            codes_to_double_general = [
                'A1K', 'A18A', 'Twist Fasten', 'A6'
            ]
            for code in codes_to_double_general:
                if code in passed_codes:
                    passed_codes[code] *= 2

        if content_dict.get('insole pair', '') == 'selected':
            codes_to_double_insole = [
                'A10', 'B54C', 'B40B', 'B54A',
                'A44A', 'A44B', 'A44C', 'B55A', 'B55B', 'B55C', 'B54B'
            ]
            for code in codes_to_double_insole:
                if code in passed_codes:
                    passed_codes[code] *= 2

        # If it's a pair, double MEDBNS71 or MEDBNS72 if present, but not MEDFOOTWEAR
        if is_pair:
            if 'MEDBNS71' in passed_codes:
                passed_codes['MEDBNS71'] *= 2
            if 'MEDBNS72' in passed_codes:
                passed_codes['MEDBNS72'] *= 2
            # Do not double MEDFOOTWEAR

        # --- Final Filtering Step ---
        insole_filter_codes = {
            'A10', 'B54C', 'B40B', 'B54A', 'A44A', 'A44B', 'A44C',
            'B55A', 'B55B', 'B55C', 'B56', 'A45', 'BNS45', 'A47',
            'B51', 'B50', 'A46', 'A20', 'B20', 'D8A', 'B43', 'B41'
        }

        bespoke_filter_codes = {
            'A1B', 'A1A', 'A1K', 'A22', 'A23', 'A24', 'A25',
            'Twist Fasten', 'A18A', 'A6', 'A15', 'A16', 'A37A',
            'A37B', 'A31', 'A19', 'A26', 'A8', 'A13A', 'A12A',
            'A39', 'A38', 'A40', 'B54B'
        }

        # If insole tariff selected, remove insole_filter_codes
        if insole_tariff_added:
            for c in insole_filter_codes:
                if c in passed_codes:
                    del passed_codes[c]

        # If bespoke tariff selected, remove bespoke_filter_codes
        if bespoke_tariff_added:
            for c in bespoke_filter_codes:
                if c in passed_codes:
                    del passed_codes[c]

        # Format the passed codes with counts
        formatted_passed_codes = []
        for code, count in passed_codes.items():
            if count > 1:
                formatted_passed_codes.append(f"{code} x{count}")
            else:
                formatted_passed_codes.append(code)

        if formatted_passed_codes:
            return ', '.join(formatted_passed_codes)
        else:
            return None

    def generate_insole_codes(self, content):
        """Generates insole codes based on the content."""

        from collections import defaultdict
        passed_codes = defaultdict(int)  # Use defaultdict to count occurrences

        # Define lists of clinics for each insole tariff code (edit these lists as needed)
        tariff_tci_clinics = ['east surrey', 'bury cdc', 'ely', 'hinchingbrooke', 'pch',
                            'peterborough city hospital', 'sudbury', 'w.s.h', 'ws', 'wsh', 'stamford', 'pch diab']
        tariff_simple_clinics = ['bury cdc', 'ely', 'harpenden', 'hinchingbrooke', 'pch',
                                'peterborough city hospital', 'sudbury', 'w.s.h', 'ws', 'wsh', 'stamford', 'pch diab']
        tariff_polyprop_clinics = ['east surrey', 'bury cdc', 'ely', 'hinchingbrooke', 'pch',
                                'peterborough city hospital', 'sudbury', 'w.s.h', 'ws', 'wsh', 'stamford', 'pch diab']

        # Split the content into lines
        lines = content.split('\n')

        # Convert lines to a dictionary
        content_dict = {}
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                content_dict[key.strip().lower()] = value.strip().lower()

        clinic_name = content_dict.get('clinic', '').lower()

        # Check if it's a pair
        is_pair = (content_dict.get('pair', '') == 'selected' or 
                content_dict.get('insole pair', '') == 'selected')

        # Determine insole type early for medway logic
        insole_type = None
        if content_dict.get('insole type tci', '') == 'selected' or content_dict.get('cradle', '') == 'selected':
            insole_type = 'tci'
        elif content_dict.get('insole type simple', '') == 'selected':
            insole_type = 'simple'
        elif content_dict.get('insole type hand mould', '') == 'selected':
            insole_type = 'handmould'

        # --- Medway Tariff Logic ---
        # If clinic is 'medway':
        # - MEDBNS71 for simple
        # - MEDBNS72 for others
        if clinic_name == 'medway':
            if insole_type == 'simple':
                passed_codes['MEDBNS71'] += 1
                if is_pair:
                    passed_codes['MEDBNS71'] *= 2
                return 'MEDBNS71' if passed_codes['MEDBNS71'] == 1 else f'MEDBNS71 x{passed_codes["MEDBNS71"]}'
            else:
                passed_codes['MEDBNS72'] += 1
                if is_pair:
                    passed_codes['MEDBNS72'] *= 2
                return 'MEDBNS72' if passed_codes['MEDBNS72'] == 1 else f'MEDBNS72 x{passed_codes["MEDBNS72"]}'

        # Tariff checks for other clinics
        if clinic_name in tariff_tci_clinics:
            passed_codes['Tariff TCI'] += 1
            if is_pair:
                passed_codes['Tariff TCI'] *= 2
            return 'Tariff TCI' if passed_codes['Tariff TCI'] == 1 else 'Tariff TCI x2'

        elif clinic_name in tariff_simple_clinics:
            passed_codes['Tariff Simple'] += 1
            if is_pair:
                passed_codes['Tariff Simple'] *= 2
            return 'Tariff Simple' if passed_codes['Tariff Simple'] == 1 else f'Tariff Simple x{passed_codes["Tariff Simple"]}'

        elif clinic_name in tariff_polyprop_clinics:
            passed_codes['Tariff Polyprop'] += 1
            if is_pair:
                passed_codes['Tariff Polyprop'] *= 2
            return 'Tariff Polyprop' if passed_codes['Tariff Polyprop'] == 1 else f'Tariff Polyprop x{passed_codes["Tariff Polyprop"]}'

        # Normal logic if no immediate tariff matched
        from collections import defaultdict
        passed_codes = defaultdict(int)

        base = content_dict.get('base', '').strip().lower()
        print(f"Base value: '{base}'")  # For debugging

        if content_dict.get('poron', '').lower() == 'selected':
            passed_codes['B40B'] += 1

        # 2) Otherwise, use the base logic
        else:
            normalized_base = base.replace(' ', '').lower()
            shore_bases = {'40shore', '50shore', '65shore'}

            # Base codes
            if normalized_base == 'polypropylene':
                passed_codes['B54B'] += 1
            elif insole_type == 'simple' and normalized_base in shore_bases:
                passed_codes['B40B'] += 1
            elif normalized_base in ['carbonfibre', 'carbonfiber']:
                passed_codes['B54A'] += 1
            else:
                # If none match, default to B54C
                passed_codes['B54C'] += 1

        # Foot modifications -> BNS45
        foot_modifications = [
            'cut out and additions', '1st met head', '1st met ray', '5th met ray',
            'navicular sweet spot', 'fascial accommodation', 'heel flange'
        ]

        left_modifications_count = 0
        right_modifications_count = 0

        for mod in foot_modifications:
            left_key = f"left {mod}"
            right_key = f"right {mod}"
            if content_dict.get(left_key, '') == 'selected':
                left_modifications_count += 1
                passed_codes['BNS45'] += 1
            if content_dict.get(right_key, '') == 'selected':
                right_modifications_count += 1
                passed_codes['BNS45'] += 1

        # Postings
        posting_keys_left = [
            'left medial rearfoot posting', 'left lateral rearfoot posting',
            'left medial forefoot posting', 'left lateral forefoot posting',
        ]
        posting_keys_right = [
            'right medial rearfoot posting', 'right lateral rearfoot posting',
            'right medial forefoot posting', 'right lateral forefoot posting',
        ]

        left_postings_count = 0
        right_postings_count = 0

        for key in posting_keys_left:
            if content_dict.get(key, '') == 'selected':
                left_postings_count += 1
                passed_codes['B56'] += 1

        for key in posting_keys_right:
            if content_dict.get(key, '') == 'selected':
                right_postings_count += 1
                passed_codes['B56'] += 1

        insole_right_as_left = content_dict.get('right as left insole modification', '') == 'selected'

        # Right as Left for modifications
        if insole_right_as_left and ((left_modifications_count == 0 and right_modifications_count > 0) or
                                    (left_modifications_count > 0 and right_modifications_count == 0)):
            passed_codes['BNS45'] *= 2

        # Right as Left for postings
        if insole_right_as_left and 'B56' in passed_codes and passed_codes['B56'] > 0:
            if (left_postings_count == 0 and right_postings_count > 0) or (left_postings_count > 0 and right_postings_count == 0):
                passed_codes['B56'] *= 2


        # Additions
        addition_positions = [
            'left 1st addition', 'left 2nd addition', 'left 3rd addition', 'left 4th addition',
            'right 1st addition', 'right 2nd addition', 'right 3rd addition', 'right 4th addition'
        ]

        addition_code_mapping = {
            'B41': {'valgus pad', 'metatarsal pad', 'metatarsal bar', 'balance pad',
                    'heel pad', 'cuboid pad', 'cobra pad', 'neuroma pad',
                    'sulcus crest', 'arch fill'},
            'B56': {"morton's extension", "reverse morton's extension", 'poron forefoot'},
            'B43': {'kinetic wedge', 'heel raise'},
            'D8A': {'neurological footplate'},
            'BNS45': {'recess', 'hole & plug'},
            'B20': {'rigid 1st extension'},
            'B50': {'partial toe block'},
            'B51': {'full toe block'}
        }

        for key in addition_positions:
            addition_value = content_dict.get(key, '')
            if addition_value:
                for code, additions in addition_code_mapping.items():
                    if addition_value in additions:
                        passed_codes[code] += 1
                        break
                else:
                    print(f"Warning: Unrecognized addition value '{addition_value}' for '{key}'")

        # Insole coding - MATHS
        x = 0
        if insole_type == 'simple':
            x -= 1
        if content_dict.get('lining to shell', '') == 'selected':
            x += 1
        if content_dict.get('lining to sulcus', '') == 'selected':
            x += 1
        if content_dict.get('lining to full', '') == 'selected':
            x += 1
        if content_dict.get('insole top cover material', '') == 'spenco (green)':
            x += 1
        if content_dict.get('base', '') in ('35/20/80 sh', '45/30/80 sh'):
            x += 1

        if x >= 2:
            passed_codes['B55C'] += 1
        elif x == 1:
            passed_codes['B55B'] += 1
        elif x == 0:
            passed_codes['B55A'] += 1

        # CLCH Simple Logic
        if clinic_name == 'clch' and insole_type == 'simple':
            total_posts = (passed_codes['B41'] + passed_codes['B56'] +
                        passed_codes['B43'] + passed_codes['BNS45'])

            # Decide tariff
            if total_posts <= 4:
                chosen_tariff = 'Tariff insole >4 POST'
            else:
                chosen_tariff = 'Tariff insole <5 POST'

            passed_codes[chosen_tariff] += 1

            # Remove all non-tariff codes (all except chosen_tariff)
            for code in list(passed_codes.keys()):
                if code != chosen_tariff:
                    del passed_codes[code]

            # Now handle pairs including chosen_tariff
            if is_pair:
                # Double the chosen tariff code if it's still present
                if chosen_tariff in passed_codes:
                    passed_codes[chosen_tariff] *= 2
        else:
            # Normal pair handling if not CLCH simple
            if is_pair:
                codes_to_double_insole = ['B54C', 'B40B', 'B54A', 'B55A', 'B55B', 'B55C', 'B54B']
                for code in codes_to_double_insole:
                    if code in passed_codes:
                        passed_codes[code] *= 2

        # Format output
        formatted_passed_codes = []
        for code, count in passed_codes.items():
            if count > 1:
                formatted_passed_codes.append(f"{code} x{count}")
            else:
                formatted_passed_codes.append(code)

        if formatted_passed_codes:
            return ', '.join(formatted_passed_codes)
        else:
            return None
            
    def generate_afo_codes(self, content):
        """Generates codes based on the content for the AFO model, counting duplicates."""
        from collections import defaultdict
        passed_codes = defaultdict(int)  # Use defaultdict to count occurrences

        # Define list of clinics for Tariff AFO (edit this list as needed)
        tariff_afo_clinics = ['bury cdc', 'east surrey', 'sudbury', 'w.s.h', 'ws', 'wsh']

        # Split the content into lines for easier processing
        lines = content.split('\n')

        # Convert lines to a dictionary for easier lookup with lowercase keys and values
        content_dict = {}
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                content_dict[key.strip().lower()] = value.strip().lower()

        # Extract the clinic name if it exists in the content
        clinic_name = content_dict.get('clinic', '').lower()

        # Check if it's a pair for AFO
        is_pair = content_dict.get('pair', '') == 'selected' or content_dict.get('afo pair', '') == 'selected'

        # --- New Medway Tariff ---
        if clinic_name == 'medway':
            passed_codes['MEDDNS2'] += 1
            if is_pair:
                passed_codes['MEDDNS2'] *= 2
            return 'MEDDNS2' if passed_codes['MEDDNS2'] == 1 else f'MEDDNS2 x{passed_codes["MEDDNS2"]}'

        # --- Tariff AFO Check ---
        if clinic_name in tariff_afo_clinics:
            passed_codes['Tariff AFO'] += 1
            if is_pair:
                passed_codes['Tariff AFO'] *= 2
            return 'Tariff AFO' if passed_codes['Tariff AFO'] == 1 else f'Tariff AFO x{passed_codes["Tariff AFO"]}'

        # --- Start of AFO-specific logic (if not a Tariff AFO clinic) ---
        # Default codes
        default_codes = ['D1/C', 'D8/U']

        # Determine AFO Type codes with pair handling for 'D8/U'
        afo_type = content_dict.get('afo type', '').lower()
        if afo_type in ('normal', 'fixed', 'articulated'):
            passed_codes['D1/C'] += 1
            code_count = 1
            if content_dict.get('afo pair', '') == 'selected':
                code_count *= 2
            passed_codes['D8/U'] += code_count
        elif afo_type == 'crow boot':
            passed_codes['DNS 1'] += 1
        elif afo_type == 'afo/dafo':
            passed_codes['D1/C'] += 2
            code_count = 2
            if content_dict.get('afo pair', '') == 'selected':
                code_count *= 2
            passed_codes['D8/U'] += code_count
        elif afo_type == 'anterior shell':
            passed_codes['D12/M'] += 1
        else:
            # If 'AFO Type' does not exist, use default codes
            passed_codes['D1/C'] += 1
            code_count = 1
            if content_dict.get('afo pair', '') == 'selected':
                code_count *= 2
            passed_codes['D8/U'] += code_count

        # Check for 'Anterior Shell Height' even if 'AFO Type' is not 'anterior shell'
        if afo_type != 'anterior shell' and content_dict.get('anterior shell height', ''):
            passed_codes['D12/M'] += 1

        # Determine Hinge Type codes
        hinge_type = content_dict.get('hinge type', '').lower()
        hinge_code = None
        if hinge_type == 'gillette/tamrack':
            hinge_code = 'D2/A'
        elif hinge_type in ('double action', 'camber axis'):
            hinge_code = 'D2/D'
        elif hinge_type in ('appalachian/metal', 'appalachian', 'metal'):
            hinge_code = 'D2/B'

        if hinge_code:
            code_count = 1
            if content_dict.get('afo pair', '') == 'selected':
                code_count *= 2
            passed_codes[hinge_code] += code_count

        # Heel Posting
        heel_posting_codes = 0
        heel_posting_keys = [
            'left heel posting attached', 'left heel posting blended',
            'left heel posting heel only', 'left heel posting loose',
            'right heel posting attached', 'right heel posting blended',
            'right heel posting heel only', 'right heel posting loose'
        ]
        right_as_left_heel = content_dict.get('ca&t right as left', '') == 'selected'
        left_heel_posting = any(content_dict.get(key, '') == 'selected' for key in heel_posting_keys if 'left' in key)
        right_heel_posting = any(content_dict.get(key, '') == 'selected' for key in heel_posting_keys if 'right' in key)

        if right_as_left_heel and (left_heel_posting != right_heel_posting):
            heel_posting_codes = 2
        else:
            heel_posting_codes = sum([left_heel_posting, right_heel_posting])

        if heel_posting_codes > 0:
            passed_codes['D10/E'] += heel_posting_codes

        # PCRO Codes
        pcro_codes = defaultdict(int)
        pcro_right_as_left = content_dict.get('pcro right as left', '') == 'selected'

        # List of PCRO features and their codes
        pcro_features = {
            'varus resist': 'D8/D',
            'valgus resist': 'D8/D',
            'suctentaculum tali': 'D8/H',
            'peroneal notch': 'D8/I',
            'metatarsal button': 'B41',
            'neuro plate': 'D8/A',
            'toe lift': 'D8/U',
            'pcro values': 'D8/D'
        }

        for feature, code in pcro_features.items():
            left_key = f'{feature} left'
            right_key = f'{feature} right'

            left_selected = content_dict.get(left_key, '') == 'selected' or content_dict.get(left_key, '').isdigit()
            right_selected = content_dict.get(right_key, '') == 'selected' or content_dict.get(right_key, '').isdigit()

            if pcro_right_as_left and (left_selected != right_selected):
                # If right as left is selected and only one side is filled out, multiply by 2
                total = 2
            else:
                total = sum([left_selected, right_selected])

            if total > 0:
                pcro_codes[code] += total

        # Add PCRO codes to passed_codes
        for code, count in pcro_codes.items():
            passed_codes[code] += count

        # M&T Codes
        m_and_t_codes = []
        if content_dict.get('carbon ankle reinforcements', '') == 'selected':
            m_and_t_codes.append('D10/B')
        if content_dict.get('ribbed ankle reinforcements', '') == 'selected':
            m_and_t_codes.append('D10/A')
        if content_dict.get('walking surface', '') == 'selected':
            m_and_t_codes.append('D10/G')
        if content_dict.get('transfer 1st choice', ''):
            m_and_t_codes.append('D10/I')

        # Add M&T codes
        for code in m_and_t_codes:
            passed_codes[code] += 1

        # AFO Lining
        afo_lining_codes = []

        # Process AFO Full
        afo_full_material_value = content_dict.get('afo full material', '').lower()

        if afo_full_material_value:
            if afo_full_material_value.startswith('yes'):
                afo_lining_codes.append('D14/E')  # Add D14/E code
                # Extract the material after 'yes'
                afo_full_material = afo_full_material_value[3:].strip()
            else:
                # If 'yes' is not present, assume the entire value is the material
                afo_full_material = afo_full_material_value.strip()
        else:
            afo_full_material = ''  # No material provided

        # Process AFO Calf
        afo_calf_material_value = content_dict.get('afo calf material', '').lower()

        if afo_calf_material_value:
            if afo_calf_material_value.startswith('yes'):
                afo_lining_codes.append('D14/D')  # Add D14/D code
                # Extract the material after 'yes'
                afo_calf_material = afo_calf_material_value[3:].strip()
            else:
                # If 'yes' is not present, assume the entire value is the material
                afo_calf_material = afo_calf_material_value.strip()
        else:
            afo_calf_material = ''  # No material provided

        # Materials for AFO Lining
        lining_materials = {
            'ld eva': 'D14/D',
            "p'zote": 'D14/D',
            'chamois': 'D14/F',
            'leather': 'D14/F',
            'sheepskin': 'D14/F'
        }

        # Check and add codes based on materials
        if afo_full_material in lining_materials:
            afo_lining_codes.append(lining_materials[afo_full_material])

        if afo_calf_material in lining_materials:
            afo_lining_codes.append(lining_materials[afo_calf_material])

        # Add AFO lining codes
        for code in afo_lining_codes:
            passed_codes[code] += 1

        # Pads
        pads_codes = []

        if content_dict.get('arch pads', ''):
            pads_codes.append('D14/C')
        if content_dict.get('navicular pad', ''):
            pads_codes.append('D14/C')

        slip_pads = ['slip pad calf', 'slip pad ankle', 'slip pad foot']
        for pad in slip_pads:
            if content_dict.get(pad, '') == 'yes':
                pads_codes.append('P15')

        # Add pads codes 
        for code in pads_codes:
            passed_codes[code] += 1

        # Ensure 'P15' is added as default if not already added
        if 'P15' not in passed_codes:
            passed_codes['P15'] += 1

        # Apply pair handling for 'P15' independently
        if content_dict.get('afo pair', '') == 'selected':
            passed_codes['P15'] *= 2

        # Slotted Heel Strap
        sides = ['left', 'right']
        for side in sides:
            strap_type_key = f'{side} strap type'
            strap_type = content_dict.get(strap_type_key, '').lower()

            if strap_type == 'y strap':
                passed_codes['D14/A'] += 1
                passed_codes['P15'] += 1
            elif strap_type == 'full as part of ankle lining':
                passed_codes['D14/A'] += 1
                passed_codes['P15'] += 1
            elif strap_type == 'single slotted fix':
                passed_codes['P1'] += 1
                passed_codes['P4'] += 1
                passed_codes['P15'] += 1

        # Additional Information
        additional_info_fields = [
            'additional information',
            'ca&t comments',
            'm&t comments',
            'pcro comments'
        ]
        additional_material_codes = 0
        for field in additional_info_fields:
            comments = content_dict.get(field, '').lower()
            if 'add 3mm' in comments or 'add poron' in comments or 'extend poron' in comments or 'add 3mm poron' in comments:
                additional_material_codes += 1

            # Check for 'make multiple' to multiply all codes accordingly
            if 'make multiple' in comments:
                # Try to extract the multiplier from the comments, e.g., 'make multiple 3'
                multiplier = 2  # Default to 2 if not specified
                words = comments.split()
                for i, word in enumerate(words):
                    if word == 'multiple' and i + 1 < len(words):
                        try:
                            multiplier = int(words[i + 1])
                        except ValueError:
                            pass  # Keep default multiplier
                # Multiply all codes accordingly
                for code in passed_codes:
                    passed_codes[code] *= multiplier

            # Check for any codes in the description not already added
            for word in comments.split():
                if word.upper() in passed_codes:
                    continue
                elif word.upper() in ['D14/C', 'D14C']:
                    passed_codes['D14/C'] += 1

        # Add D14/C code if additional material usage is found
        if additional_material_codes > 0:
            passed_codes['D14/C'] += additional_material_codes

        # --- Pair Handling ---
        # Apply Pair Handling after all codes have been added
        if content_dict.get('afo pair', '') == 'selected':
            # Codes to exclude from pair handling
            codes_to_exclude = ['D10/E', 'D14/A', 'D14/D', 'P1', 'P4', 'D8/D','D8/H','D8/A', 'B41','D8/I', 'D8/U', 'D8/B', 'P15', 'D2/D', 'D2/B', 'D2/A']
            for code in passed_codes:
                if code not in codes_to_exclude:
                    passed_codes[code] *= 2

        # Format the passed codes with counts
        formatted_passed_codes = []
        for code, count in passed_codes.items():
            if count > 1:
                formatted_passed_codes.append(f"{code} x{count}")
            else:
                formatted_passed_codes.append(code)

        # Return the passed codes as a string
        if formatted_passed_codes:
            return ', '.join(formatted_passed_codes)
        else:
            return None  # Return None if no codes were added
        
    def generate_modular_codes(self, content):
        """Generates codes based on the content for the Modular model, with tariff logic."""
        from collections import defaultdict
        passed_codes = defaultdict(int)  # Use defaultdict to count occurrences

        # Define lists of clinics for each insole tariff code (edit these lists as needed)
        tariff_tci_clinics = ['east surrey', 'bury cdc', 'ely', 'hinchingbrooke', 'pch',
                            'peterborough city hospital', 'sudbury', 'w.s.h', 'ws', 'wsh', 'stamford', 'pch diab']
        tariff_simple_clinics = ['bury cdc', 'ely', 'harpenden', 'hinchingbrooke', 'pch',
                                'peterborough city hospital', 'sudbury', 'w.s.h', 'ws', 'wsh', 'stamford', 'pch diab']
        tariff_polyprop_clinics = ['east surrey', 'bury cdc', 'ely', 'hinchingbrooke', 'pch',
                                'peterborough city hospital', 'sudbury', 'w.s.h', 'ws', 'wsh', 'stamford', 'pch diab']

        # Define list of clinics for Tariff Modular
        tariff_modular_clinics = ['bury cdc', 'east surrey', 'sudbury', 'w.s.h', 'ws', 'wsh']

        # Split the content into lines
        lines = content.split('\n')

        # Convert lines to a dictionary
        content_dict = {}
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                content_dict[key.strip().lower()] = value.strip().lower()

        clinic_name = content_dict.get('clinic', '').lower()
        # Check if it's a pair
        is_pair = (content_dict.get('pair', '') == 'selected' or 
                content_dict.get('insole pair', '') == 'selected')

        # Determine insole type for modular logic
        insole_type = None
        if content_dict.get('insole type tci', '') == 'selected':
            insole_type = 'tci'
        elif content_dict.get('insole type cradle', '') == 'selected':
            insole_type = 'cradle'
        elif content_dict.get('insole type simple', '') == 'selected':
            insole_type = 'simple'
        elif content_dict.get('insole type handmould', '') == 'selected':
            insole_type = 'handmould'

        # Get the base value for polyprop check
        base = content_dict.get('base', '').strip().lower()
        normalized_base = base.replace(' ', '').lower()

        # Variables to track tariffs
        modular_tariff_added = False
        insole_tariff_added = False

        # --- Medway Tariffs for Modular ---
        # If medway:
        # - If simple: add MEDBNS71
        # - Otherwise: add MEDBNS72
        # In all cases: add MEDFOOTWEAR
        if clinic_name == 'medway':
            if insole_type == 'simple':
                passed_codes['MEDBNS71'] += 1
            else:
                passed_codes['MEDBNS72'] += 1

            # Add MEDFOOTWEAR in all medway cases
            passed_codes['MEDFOOTWEAR'] += 1
            # Mark modular tariff as added so filters run later
            modular_tariff_added = True
            insole_tariff_added = True

        # Modular Tariff Check (other clinics)
        if clinic_name in tariff_modular_clinics:
            passed_codes['Tariff Modular'] += 1
            modular_tariff_added = True

        # Insole Tariff Checks
        if clinic_name in tariff_tci_clinics:
            passed_codes['Tariff TCI'] += 1
            insole_tariff_added = True
        elif clinic_name in tariff_simple_clinics:
            passed_codes['Tariff Simple'] += 1
            insole_tariff_added = True
        elif clinic_name in tariff_polyprop_clinics:
            passed_codes['Tariff Polyprop'] += 1
            insole_tariff_added = True

        # Note: Continue normal logic to allow code filtering at the end

        # Last Type Checks
        if content_dict.get('last type', '').strip().lower() == 'wide extra deep':
            count = 1
            if is_pair:
                count = 2
            passed_codes['6mm'] += count

        # Insole Allowance Checks
        allowance_codes = {'3mm', '6mm', '9mm', '12mm'}
        pattern_allowances = {'9mm', '12mm'}

        for key in ['left insole allowance', 'right insole allowance']:
            value = content_dict.get(key, '').strip().lower()
            if value in allowance_codes:
                passed_codes[value] += 1
                if value in pattern_allowances:
                    passed_codes['Pattern'] += 1

        # Sole and Style Checks
        sole_value = content_dict.get('sole', '')
        style_value = content_dict.get('styles', '')

        if sole_value in ('(lcr) lightweight commando sole', 'resin commando sole'):
            if style_value not in ('highland', 'rockingham', 'rockcliffe'):
                passed_codes['BNS62'] += 1

        style = content_dict.get('styles', '').lower()

        sport_styles = {
            'sneaker', 'greenock', 'greeock', 'colwyn', 'lineham', 'hove', 'plymouth', 
            'drayton', 'olympic', 'melton', 'kelso', 'dover', 'shelwyck', 'mowbray'
        } 

        shoe_styles = {
            'trent', 'selby', 'hallam', 'totnes', 'tenby', 'chelsea', 'galway', 'vienna',
            'truro', 'hendon', 'stirling', 'exeter', 'chester', 'shelby'
        }

        boot_styles = {
            'bumper', 'whitby', 'tralee', 'rockingham', 'perth', 'rockliffe',
            'dundee', 'brigg', 'elgin', 'highland'
        }

        # If style is recognized use style lists
        if style in sport_styles:
            passed_codes['modular sports'] += 1
        elif style in shoe_styles:
            passed_codes['modular shoes'] += 1
        elif style in boot_styles:
            passed_codes['modular boots'] += 1
        else:
            # --- ADDED WARNING LOGIC HERE ---
            # The style wasn't found in sport, shoe, or boot sets, so fallback to tick boxes.
            # We'll also build a warning message to show the user that we are “guessing.”
            fallback_styles_used = []

            if content_dict.get('shoes', '') == 'selected':
                passed_codes['modular shoes'] += 1
                fallback_styles_used.append('shoes')
            if content_dict.get('boots', '') == 'selected':
                passed_codes['modular boots'] += 1
                fallback_styles_used.append('boots')
            if content_dict.get('trainers', '') == 'selected':
                passed_codes['modular sports'] += 1
                fallback_styles_used.append('trainers')

            if fallback_styles_used:
                # Create a warning message letting the user know we didn't detect the style
                warning_message = (
                    f"Footwear style not detected!\n"
                    f"• Entered style: '{style}' may be spelled incorrectly.\n"
                    f"• Falling back to tick-box selections: {', '.join(fallback_styles_used)}"
                )
                # Show the pop-up in the same way you handle other warnings
                self.root.after(0, messagebox.showinfo, "Warning", warning_message)
            else:
                # If no tick boxes are also selected, you might want a different warning or default assumption.
                warning_message = (
                    f"Footwear style '{style}' not recognized, and no tick boxes selected. "
                    f"Please verify the footwear style."
                )
                self.root.after(0, messagebox.showinfo, "Warning", warning_message)

        # Check boa/velcro 
        if content_dict.get('boa', '') == 'selected':
            passed_codes['twist fasten'] += 1
        if content_dict.get('velcro', '') == 'selected':
            passed_codes['velcro'] += 1

        # Straps Checks
        for side in ['left', 'right']:
            strap_type_key = f'{side} strap type'
            double_decker_key = f'{side} double decker'

            strap_type = content_dict.get(strap_type_key, '')
            double_decker = content_dict.get(double_decker_key, '')

            if double_decker == 'yes':
                passed_codes['B34'] += 1
            else:
                if strap_type in ('t strap', 'y strap'):
                    passed_codes['B33'] += 1
                elif strap_type in ('spur retaining strap', 'heel retaining strap'):
                    passed_codes['B8'] += 1

        # Sockets Type Checks
        socket_keys = ['left socket type', 'right socket type']
        for key in socket_keys:
            value = content_dict.get(key, '')
            if value in ('5/16 round', '1/4 round', 'small rectangular', 'large rectangular', 'rizzoli'):
                passed_codes['B30'] += 1
            elif value in ("5/16 with b'stop", "1/4 with b'stop"):
                passed_codes['B31'] += 1

        # Elongation Type (B25)
        elongation_keys = ['left elongation type', 'right elongation type']
        for key in elongation_keys:
            if content_dict.get(key, '') in ('full', 'half'):
                passed_codes['B25'] += 1

        # Rocker Type (B17)
        rocker_keys = ['left rocker type', 'right rocker type']
        for key in rocker_keys:
            if content_dict.get(key, '') in ('plr', 'standard', 'two point'):
                passed_codes['B17'] += 1

        # Wedges
        wedges_keys = [
            'left wedges heel lateral',
            'left wedges heel medial',
            'right wedges heel medial',
            'right wedges heel lateral',
            'left wedges sole lateral',
            'left wedges sole medial',
            'right wedges sole medial',
            'right wedges sole lateral'
        ]

        for key in wedges_keys:
            if content_dict.get(key, '') == 'selected':
                if 'heel' in key:
                    passed_codes['B25'] += 1
                elif 'sole' in key:
                    passed_codes['B18'] += 1

        # Floated
        floated_keys = [
            'right floated heel lateral',
            'right floated heel medial',
            'left floated heel medial',
            'left floated heel lateral',
            'left floated sole lateral',
            'left floated sole medial',
            'right floated sole lateral',
            'right floated sole medial'
        ]

        for key in floated_keys:
            if content_dict.get(key, '') == 'selected':
                if 'heel' in key:
                    passed_codes['B25'] += 1
                elif 'sole' in key:
                    passed_codes['B19'] += 1

        # beyond this point is the insole logic
        shore_bases = {'40shore', '50shore', '65shore', '35/20/80sh', '45/30/80sh'}
        if insole_type == 'cradle':
            if normalized_base in shore_bases:
                passed_codes['A10'] += 1
            elif normalized_base == 'polypropylene':
                passed_codes['A10'] += 1
        elif insole_type in ('tci', 'simple', 'handmould'):
            if normalized_base == 'polypropylene':
                passed_codes['B54B'] += 1
            else:
                passed_codes['B54C'] += 1

        if content_dict.get('base poron', '') == 'selected':
            passed_codes['B40B'] += 1

        if content_dict.get('base carbon fibre', '') == 'selected':
            passed_codes['B54A'] += 1

        foot_modifications = [
            'cut out and additions',
            '1st met head',
            '1st met ray',
            '5th met ray',
            'navicular sweet spot',
            'fascial accommodation',
            'heel flange'
        ]
        for side in ['left', 'right']:
            for mod in foot_modifications:
                key = f"{side} {mod}"
                if content_dict.get(key, '') == 'selected':
                    passed_codes['BNS45'] += 1

        addition_positions = [
            'left 1st addition', 'left 2nd addition', 'left 3rd addition', 'left 4th addition',
            'right 1st addition', 'right 2nd addition', 'right 3rd addition', 'right 4th addition'
        ]

        addition_code_mapping = {
            'A45_B41': {
                'valgus pad', 'metatarsal pad', 'metatarsal bar', 'balance pad',
                'heel pad', 'cuboid pad', 'cobra pad', 'neuroma pad',
                'sulcus crest', 'arch fill'
            },
            'A45_B56': {
                "morton's extension", "reverse morton's extension", 'poron forefoot'
            },
            'A45_B43': {'kinetic wedge', 'heel raise'},
            'D8A': {'neurological footplate'},
            'BNS45': {'recess', 'hole & plug'},
            'A20_B20': {'rigid 1st extension'},
            'A46_B50': {'partial toe block'},
            'A47_B51': {'full toe block'}
        }

        for key in addition_positions:
            addition_value = content_dict.get(key, '')
            if addition_value:
                if addition_value in addition_code_mapping['A45_B41']:
                    code = 'A45' if insole_type == 'cradle' else 'B41'
                    passed_codes[code] += 1
                elif addition_value in addition_code_mapping['A45_B56']:
                    code = 'A45' if insole_type == 'cradle' else 'B56'
                    passed_codes[code] += 1
                elif addition_value in addition_code_mapping['A45_B43']:
                    code = 'A45' if insole_type == 'cradle' else 'B43'
                    passed_codes[code] += 1
                elif addition_value in addition_code_mapping['D8A']:
                    passed_codes['D8A'] += 1
                elif addition_value in addition_code_mapping['BNS45']:
                    passed_codes['BNS45'] += 1
                elif addition_value in addition_code_mapping['A20_B20']:
                    code = 'A20' if insole_type == 'cradle' else 'B20'
                    passed_codes[code] += 1
                elif addition_value in addition_code_mapping['A46_B50']:
                    code = 'A46' if insole_type == 'cradle' else 'B50'
                    passed_codes[code] += 1
                elif addition_value in addition_code_mapping['A47_B51']:
                    code = 'A47' if insole_type == 'cradle' else 'B51'
                    passed_codes[code] += 1

        posting_keys = [
            'left medial rearfoot posting',
            'left lateral rearfoot posting',
            'right medial rearfoot posting',
            'right lateral rearfoot posting',
            'left medial forefoot posting',
            'left lateral forefoot posting',
            'right medial forefoot posting',
            'right lateral forefoot posting',
        ]

        for key in posting_keys:
            if content_dict.get(key, '') == 'selected':
                code = 'A45' if insole_type == 'cradle' else 'B56'
                passed_codes[code] += 1

        # Insole coding section - MATHS!
        x = 0
        if insole_type == 'simple':
            x -= 1
        if content_dict.get('lining to shell', '') == 'selected':
            x += 1
        if content_dict.get('lining to sulcus', '') == 'selected':
            x += 1
        if content_dict.get('lining full', '') == 'selected':
            x += 1
        if content_dict.get('insole top cover material', '') == 'spenco (green)':
            x += 1
        if content_dict.get('base', '') in ('35/20/80 sh', '45/30/80 sh'):
            x += 1

        if x >= 2:
            code = 'A44C' if insole_type == 'cradle' else 'B55C'
            passed_codes[code] += 1
        elif x == 1:
            code = 'A44B' if insole_type == 'cradle' else 'B55B'
            passed_codes[code] += 1
        elif x == 0:
            code = 'A44A' if insole_type == 'cradle' else 'B55A'
            passed_codes[code] += 1

        if content_dict.get('pair', '') == 'selected':
            codes_to_double_general = [
                'twist fasten', 'BNS62', 'velcro'
            ]
            for code in codes_to_double_general:
                if code in passed_codes:
                    passed_codes[code] *= 2

        if content_dict.get('insole pair', '') == 'selected':
            codes_to_double_insole = [
                'A10', 'B54C', 'B40B', 'B54A',
                'A44A', 'A44B', 'A44C', 'B55A', 'B55B', 'B55C', 'B54B'
            ]
            for code in codes_to_double_insole:
                if code in passed_codes:
                    passed_codes[code] *= 2

        # Now we must double MEDBNS71 or MEDBNS72 if it's a pair, but NOT MEDFOOTWEAR
        if is_pair:
            if 'MEDBNS71' in passed_codes:
                passed_codes['MEDBNS71'] *= 2
            if 'MEDBNS72' in passed_codes:
                passed_codes['MEDBNS72'] *= 2
            # Do not double MEDFOOTWEAR

        # --- Filtering Step ---
        insole_filter_codes = {
            'A10', 'B54C', 'B40B', 'B54A', 'A44A', 'A44B', 'A44C',
            'B55A', 'B55B', 'B55C', 'B56', 'A45', 'BNS45', 'A47',
            'B51', 'B50', 'A46', 'A20', 'B20', 'D8A', 'B43', 'B41', 'B54B'
        }

        modular_filter_codes = {
            '6mm', 'Pattern', 'BNS62', 'modular shoes', 'modular boots',
            'modular sports', 'twist fasten', 'velcro', 'B34', 'B33', 'B8',
            'B30', 'B31', 'B25', 'B17', 'B18', 'B19'
        }

        if insole_tariff_added:
            for c in insole_filter_codes:
                if c in passed_codes:
                    del passed_codes[c]

        if modular_tariff_added:
            for c in modular_filter_codes:
                if c in passed_codes:
                    del passed_codes[c]

        # Format the passed codes with counts
        formatted_passed_codes = []
        for code, count in passed_codes.items():
            if count > 1:
                formatted_passed_codes.append(f"{code} x{count}")
            else:
                formatted_passed_codes.append(code)

        if formatted_passed_codes:
            return ', '.join(formatted_passed_codes)
        else:
            return None

# --- Main Application Setup ---
def create_search_tab(notebook):
    """
    Creates a new tab in the provided ttk.Notebook for searching
    through the 'work_orders' folder by AutoDocRef (case-insensitive),
    with smaller scrollable listbox and text box,
    automatic searching on each keystroke,
    and double-click to open files.
    """
    import tkinter as tk
    from tkinter import ttk, messagebox
    import os

    # Create a frame for the 'Search Work Orders' tab
    search_tab = ttk.Frame(notebook)
    notebook.add(search_tab, text="Search Work Orders")

    # Label + Entry
    search_label = ttk.Label(search_tab, text="Enter AutoDocRef (live search):")
    search_label.pack(pady=5)

    search_entry = ttk.Entry(search_tab, width=30)
    search_entry.pack(pady=5)

    # Frame to hold the listbox + scrollbar
    listbox_frame = ttk.Frame(search_tab)
    listbox_frame.pack(pady=5, fill='both', expand=True)

    listbox_scrollbar = ttk.Scrollbar(listbox_frame, orient='vertical')
    listbox_scrollbar.pack(side='right', fill='y')

    # Make the listbox smaller: width=60, height=15
    results_listbox = tk.Listbox(
        listbox_frame, 
        width=60, height=15, 
        yscrollcommand=listbox_scrollbar.set
    )
    results_listbox.pack(side='left', fill='both', expand=True)

    listbox_scrollbar.config(command=results_listbox.yview)

    # Frame to hold the text widget + scrollbar
    text_frame = ttk.Frame(search_tab)
    text_frame.pack(pady=5, fill='both', expand=True)

    text_scrollbar = ttk.Scrollbar(text_frame, orient='vertical')
    text_scrollbar.pack(side='right', fill='y')

    # Make the text box smaller: width=60, height=15
    file_content_text = tk.Text(
        text_frame,
        wrap='word', width=60, height=15,
        yscrollcommand=text_scrollbar.set
    )
    file_content_text.pack(side='left', fill='both', expand=True)
    file_content_text.config(state='disabled')

    text_scrollbar.config(command=file_content_text.yview)

    # ------------- Functions -------------
    def live_search():
        """Perform a case-insensitive search each time the user types in the entry."""
        results_listbox.delete(0, tk.END)
        file_content_text.config(state='normal')
        file_content_text.delete('1.0', tk.END)
        file_content_text.config(state='disabled')

        query = search_entry.get().strip()
        if not query:
            return  # If empty, just clear out (no message box)
        
        work_orders_folder = os.path.join(os.getcwd(), 'work_orders')
        if not os.path.exists(work_orders_folder):
            return  # Silently ignore or show an error if you prefer

        matches = []
        for date_folder in os.listdir(work_orders_folder):
            date_path = os.path.join(work_orders_folder, date_folder)
            if os.path.isdir(date_path):
                for filename in os.listdir(date_path):
                    if query.lower() in filename.lower():
                        full_path = os.path.join(date_path, filename)
                        matches.append(full_path)

        if matches:
            for m in matches:
                results_listbox.insert(tk.END, m)
        else:
            # If you’d prefer not to show a message on every keystroke,
            # you can remove or comment out this messagebox
            pass

    def open_file():
        """Open the selected file from the listbox and display its contents."""
        selection = results_listbox.curselection()
        if not selection:
            messagebox.showinfo("No File Selected", "Please select a file from the list.")
            return

        selected_file = results_listbox.get(selection[0])

        if not os.path.isfile(selected_file):
            messagebox.showerror("Error", f"File does not exist: {selected_file}")
            return

        try:
            with open(selected_file, 'r', encoding='utf-8') as f:
                content = f.read()
            file_content_text.config(state='normal')
            file_content_text.delete('1.0', tk.END)
            file_content_text.insert(tk.END, content)
            file_content_text.config(state='disabled')
        except Exception as e:
            messagebox.showerror("Error", f"Could not open file:\n{str(e)}")

    def copy_to_clipboard():
        """Copy the displayed file text to the clipboard."""
        file_content_text.config(state='normal')
        contents = file_content_text.get('1.0', tk.END).strip()
        file_content_text.config(state='disabled')

        if contents:
            search_tab.clipboard_clear()
            search_tab.clipboard_append(contents)
            messagebox.showinfo("Copied", "File contents copied to clipboard.")
        else:
            messagebox.showinfo("No Contents", "There is no file text to copy.")

    def on_listbox_double_click(event):
        """Double-click in the listbox -> open the file."""
        open_file()

    # Bind the live search to each key release in the entry
    search_entry.bind("<KeyRelease>", lambda event: live_search())
    # Bind double-click to open file
    results_listbox.bind("<Double-Button-1>", on_listbox_double_click)

    # ------------- Buttons Frame (only Copy for now) -------------
    button_frame = ttk.Frame(search_tab)
    button_frame.pack(pady=5)

    copy_button = ttk.Button(button_frame, text="Copy to Clipboard", command=copy_to_clipboard)
    copy_button.pack(side=tk.LEFT, padx=5)

    return search_tab


# Define the list of available themes
theme_list = ['lumen', 'darkly', 'solar', 'cyborg', 'simplex', 'vapor']

# Function to load the saved theme setting
def load_theme_setting():
    settings_file = os.path.join(os.getcwd(), 'settings.txt')
    if os.path.exists(settings_file):
        try:
            with open(settings_file, 'r') as f:
                theme = f.read().strip()
                if theme in theme_list:
                    return theme
                else:
                    return 'simplex'  # Default theme if saved theme is invalid
        except:
            return 'simplex'  # Default theme in case of error
    else:
        return 'simplex'  # Default theme if settings file does not exist

# Function to save the selected theme setting
def save_theme_setting(theme):
    settings_file = os.path.join(os.getcwd(), 'settings.txt')
    with open(settings_file, 'w') as f:
        f.write(theme)

# Load the selected theme at startup
selected_theme = load_theme_setting()

# Function to write the API key in binary (encoded using Base64)
def write_api_key(api_key):
    api_key_file = os.path.join(os.getcwd(), 'api_key.txt')
    # Encode the API key as bytes, then convert it to Base64 for binary storage
    encoded_key = base64.b64encode(api_key.encode('utf-8'))
    with open(api_key_file, 'wb') as f:
        f.write(encoded_key)
    print(f"API key saved to {api_key_file}")

# Function to read and decode the API key from binary (Base64-decoded back to a string)
def read_api_key():
    api_key_file = os.path.join(os.getcwd(), 'api_key.txt')
    if os.path.exists(api_key_file):
        try:
            with open(api_key_file, 'rb') as f:
                # Read the encoded binary data and decode it back to a string
                encoded_key = f.read()
                api_key = base64.b64decode(encoded_key).decode('utf-8')
            if not api_key:
                raise ValueError("API key file is empty")
            return api_key
        except Exception as e:
            messagebox.showerror("Error", f"Error reading API key: {str(e)}")
            sys.exit()
    else:
        # Prompt the user to enter the API key if the file doesn't exist
        api_key = simpledialog.askstring("API Key Required", "Please enter your OpenAI API key:")
        if not api_key:
            messagebox.showerror("Error", "No API key entered. The application will exit.")
            sys.exit()
        # Write the new API key to the file
        write_api_key(api_key.strip())
        return api_key.strip()

# Load the API key from the file or prompt the user to enter it
openai_api_key = read_api_key()

# Set the OpenAI API key for OpenAI requests
openai.api_key = openai_api_key

# Check if the API key was properly loaded
if not openai.api_key:
    messagebox.showerror("Error", "OpenAI API key not found or invalid.")
    sys.exit()

# Check if there is results folder
def ensure_result_logs_folder_exists():
    result_logs_folder = os.path.join(os.getcwd(), 'result_logs')
    if not os.path.exists(result_logs_folder):
        os.makedirs(result_logs_folder)
        print(f"Created 'result_logs' folder at {result_logs_folder}")
    else:
        print(f"'result_logs' folder already exists at {result_logs_folder}")

ensure_result_logs_folder_exists()

# Load and set the custom window icon (top-left)
icon_path = os.path.join(os.getcwd(), 'images', 'halo_simple_logo.ico')

# Define the path for the logo file
logo_file_path = os.path.join(os.getcwd(), 'images', 'HALO(TM)_Logo.png')

# Function to load and resize the icon image
def load_icon_image(icon_path, size=(32, 32)):
    try:
        icon_img = Image.open(icon_path)
        icon_img = icon_img.resize(size, Image.LANCZOS)
        icon_photo = ImageTk.PhotoImage(icon_img)
        return icon_photo
    except Exception as e:
        messagebox.showerror("Error", f"Error loading icon: {str(e)}")
        return None

# Set up the GUI window with the selected theme

# Initialize TkinterDnD root window
root = TkinterDnD.Tk()

# Apply ttkbootstrap style to the root window
style = ttk.Style('lumen')  # You can set a default theme here
style.theme_use(selected_theme)

root.title("Halo Medical Code Automation - PDF Processing")

# Force Tkinter to calculate window size and layout before setting position
root.update_idletasks()

# Get the scaling factor
scaling_factor = root.tk.call('tk', 'scaling')
print(f"Scaling factor: {scaling_factor}")

# Adjust the window size based on the scaling factor
base_width = 600
base_height = 700
adjusted_width = int(base_width * scaling_factor)
adjusted_height = int(base_height * scaling_factor)

# Set the window size and position (starting at 100px from top and 100px from left)
root.geometry(f"{adjusted_width}x{adjusted_height}+100+100")

# Load and set the custom window icon (top-left)
icon_image = load_icon_image(icon_path, size=(32, 32))
if icon_image:
    root.iconphoto(False, icon_image)
    root.icon_image = icon_image  # Keep a reference to prevent garbage collection

# Function to change the theme
def change_theme(event):
    selected_theme = theme_var.get()
    style.theme_use(selected_theme)
    save_theme_setting(selected_theme)

# Define the custom font for labels (if not already defined)
label_font = ('Calibri', 11)

# ---------------------------------------------------------------------
# Create a Notebook so we can have 2 tabs: Main PDF Processing + Search
# ---------------------------------------------------------------------
notebook = ttk.Notebook(root)
notebook.pack(expand=True, fill='both')

# ---------------------------
# MAIN PDF PROCESSING TAB
# ---------------------------
main_tab = ttk.Frame(notebook)
notebook.add(main_tab, text="Main PDF Processing")

# Load the logo image
try:
    logo_img = Image.open(logo_file_path)
    logo_img = logo_img.resize((200, 100), Image.LANCZOS)
    logo_photo = ImageTk.PhotoImage(logo_img)
    root.logo_photo = logo_photo  # Keep a reference to prevent GC

    # Place the logo in the main_tab
    logo_label = ttk.Label(main_tab, image=logo_photo)
    logo_label.pack(pady=10)
except Exception as e:
    messagebox.showerror("Error", f"Error loading logo: {str(e)}")

# Title label in main_tab
title_label = ttk.Label(main_tab, text="Code Automation Program", font=("Calibri", 16, "bold"))
title_label.pack(pady=5)

# Info frame in main_tab
info_frame = ttk.Frame(main_tab)
info_frame.pack(pady=10)

# Create labels and entries for AutoDocRef, Clinic, Date/Time
auto_doc_ref_label = ttk.Label(info_frame, text='AutoDocRef:', font=label_font)
auto_doc_ref_entry = ttk.Entry(info_frame, width=30)
clinic_label = ttk.Label(info_frame, text='Clinic:', font=label_font)
clinic_entry = ttk.Entry(info_frame, width=30)
datetime_label = ttk.Label(info_frame, text='Date and Time:', font=label_font)
datetime_entry = ttk.Entry(info_frame, width=30)

auto_doc_ref_label.grid(row=0, column=0, padx=5, pady=5)
auto_doc_ref_entry.grid(row=1, column=0, padx=5, pady=5)
clinic_label.grid(row=0, column=1, padx=5, pady=5)
clinic_entry.grid(row=1, column=1, padx=5, pady=5)
datetime_label.grid(row=0, column=2, padx=5, pady=5)
datetime_entry.grid(row=1, column=2, padx=5, pady=5)

# Create a frame to hold the result text widget
result_frame = ttk.Frame(main_tab)
result_frame.pack(pady=10, anchor='center')

# Create a text widget inside result_frame
result_text = tk.Text(result_frame, wrap='word', height=25, width=80)
result_text.grid(row=0, column=0)

# Vertical scrollbar for result_text
result_scrollbar = ttk.Scrollbar(result_frame, orient='vertical', command=result_text.yview)
result_scrollbar.grid(row=0, column=1, sticky='ns')
result_text['yscrollcommand'] = result_scrollbar.set
result_text.config(state='disabled')  # Make it read-only

# Make the result_text a drop target
result_text.drop_target_register(DND_FILES)

# The drop event
def handle_drop(event):
    files = root.tk.splitlist(event.data)
    pdf_files = [f for f in files if f.lower().endswith('.pdf')]
    if pdf_files:
        for pdf_file in pdf_files:
            pdf_handler.upload_pdf_button.config(state='disabled')
            try:
                show_loading_popup()
                threading.Thread(target=pdf_handler.process_pdf_and_call_api, args=(pdf_file,)).start()
            except Exception as e:
                messagebox.showerror("Error", f"Error processing the file: {str(e)}")
                pdf_handler.upload_pdf_button.config(state='normal')
                close_loading_popup()
    else:
        messagebox.showinfo("No PDF Files", "Please drop PDF files only.")

result_text.dnd_bind('<<Drop>>', handle_drop)

# Model IDs
model_ids = {
    'Insoles': 'InsoleReaderFullV3',
    'AFOs': 'AfoReaderV7',
    'Bespoke': 'BespokeReaderFullV1',
    'Modular': 'ModularReaderFullV3'
}
model_id_var = tk.StringVar(value='InsoleReaderFullV3')

model_frame = ttk.Frame(main_tab)
model_frame.pack(pady=10)

model_label = ttk.Label(model_frame, text='Select Form Type:', font=label_font)
model_label.pack(side='left', padx=(0, 5))

for model_name, model_id_value in model_ids.items():
    radio_button = ttk.Radiobutton(
        model_frame,
        text=model_name,
        variable=model_id_var,
        value=model_id_value
    )
    radio_button.pack(side='left', padx=5)

# The loading popup and associated functions
def show_loading_popup():
    global loading_popup, loading_label, dot_index, base_message
    loading_popup = Toplevel(root)
    loading_popup.title("Loading...")
    icon_image_loading = load_icon_image(icon_path, size=(32, 32))
    if icon_image_loading:
        loading_popup.iconphoto(False, icon_image_loading)
        loading_popup.icon_image = icon_image_loading

    loading_popup.resizable(False, False)
    loading_popup.protocol("WM_DELETE_WINDOW", lambda: None)

    root.update_idletasks()
    x = root.winfo_x() + (root.winfo_width() // 2) - (300 // 2)
    y = root.winfo_y() + (root.winfo_height() // 2) - (100 // 2)
    loading_popup.geometry(f"300x100+{x}+{y}")

    loading_popup.transient(root)
    loading_popup.grab_set()

    base_message = "Please wait, reading the file"
    loading_label = ttk.Label(loading_popup, text=f"{base_message}\n", font=("Calibri", 12, "bold"))
    loading_label.pack(expand=True, pady=20)

    dot_index = 0
    animate_dots()
    root.attributes('-disabled', True)

def animate_dots():
    global dot_index, base_message
    dots = ['.', '..', '...', '']
    loading_label.config(text=f"{base_message}\n{dots[dot_index]}")
    dot_index = (dot_index + 1) % len(dots)
    loading_popup.after(500, animate_dots)

def close_loading_popup():
    loading_popup.destroy()
    root.attributes('-disabled', False)
    root.focus_force()

def display_results(formatted_datetime, AutoDocRef, clinic, price_codes, messages=None):
    auto_doc_ref_entry.config(state=tk.NORMAL)
    auto_doc_ref_entry.delete(0, tk.END)
    auto_doc_ref_entry.insert(0, AutoDocRef)
    auto_doc_ref_entry.config(state='readonly')

    datetime_entry.config(state=tk.NORMAL)
    datetime_entry.delete(0, tk.END)
    datetime_entry.insert(0, formatted_datetime)
    datetime_entry.config(state='readonly')

    clinic_entry.config(state=tk.NORMAL)
    clinic_entry.delete(0, tk.END)
    clinic_entry.insert(0, clinic if clinic else "N/A")
    clinic_entry.config(state='readonly')

    result_text.config(state=tk.NORMAL)
    result_text.delete('1.0', tk.END)

    result_text.tag_configure('center', justify='center')
    result_text.tag_configure('bold', font=('Calibri', 12, 'bold'))

    lines = price_codes.split('\n')
    for line in lines:
        stripped_line = line.strip()
        if stripped_line.startswith('**') and stripped_line.endswith('**'):
            content = stripped_line.strip('*')
            result_text.insert(tk.END, content + '\n', ('center', 'bold'))
        elif stripped_line.startswith('*') and stripped_line.endswith('*'):
            content = stripped_line.strip('*')
            result_text.insert(tk.END, content + '\n', ('center', 'bold'))
        else:
            result_text.insert(tk.END, line + '\n', 'center')

    if messages:
        result_text.insert(tk.END, "\n\n")
        result_text.tag_configure('warning', justify='center', foreground='red', font=('Calibri', 12, 'bold'))
        result_text.insert(tk.END, messages, 'warning')

    result_text.see(tk.END)
    result_text.config(state=tk.DISABLED)

# Instantiate PdfButtonHandler
pdf_handler = PdfButtonHandler(
    root=root,
    result_text=result_text,
    auto_doc_ref_entry=auto_doc_ref_entry,
    datetime_entry=datetime_entry,
    clinic_entry=clinic_entry,
    show_loading_popup=show_loading_popup,
    close_loading_popup=close_loading_popup,
    display_results=display_results,
    model_id_var=model_id_var
)

upload_pdf_button = ttk.Button(main_tab, text="Upload PDF", command=pdf_handler.upload_pdf_file)
upload_pdf_button.pack(pady=10)

pdf_handler.set_upload_pdf_button(upload_pdf_button)

exit_button = ttk.Button(main_tab, text="Exit", command=root.quit)
exit_button.pack(pady=10)

# The bottom frame for theme selection
bottom_frame = ttk.Frame(main_tab)
bottom_frame.pack(side='bottom', fill='x', padx=10, pady=10)

theme_label = ttk.Label(bottom_frame, text='Theme:')
theme_label.pack(side='left', padx=(0, 5))

theme_var = tk.StringVar(value=selected_theme)
theme_combobox = ttk.Combobox(
    bottom_frame, textvariable=theme_var, values=theme_list, state='readonly'
)
theme_combobox.pack(side='left')

spacer = ttk.Frame(bottom_frame)
spacer.pack(side='left', expand=True, fill='x')

version_label = ttk.Label(
    bottom_frame, text=f"Version {VERSION}", font=("Calibri", 10)
)
version_label.pack(side='right')

theme_combobox.bind('<<ComboboxSelected>>', change_theme)

# ---------------------------
# SEARCH WORK ORDERS TAB
# ---------------------------
search_tab = create_search_tab(notebook)

# Start the GUI event loop
root.mainloop()
