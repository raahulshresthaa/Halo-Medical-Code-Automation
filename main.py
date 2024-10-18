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

# Version number
VERSION = "2.0.0 pre release"

# To fix blurriness on some displays
try:
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

# Azure Form Recognizer imports
from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient

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

        self.context_folder_path = os.path.join(os.getcwd(), 'context')

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

    def read_files_for_context(self):
        file_contents = []
        try:
            # Check if the context folder exists
            if not os.path.exists(self.context_folder_path):
                return "Error: 'context' folder not found."

            # Iterate over all files in the 'context' folder
            for file_name in os.listdir(self.context_folder_path):
                file_path = os.path.join(self.context_folder_path, file_name)

                # Only process text files
                if file_name.endswith(".txt"):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            file_contents.append(f"File: {file_name}\n{content}")
                    except Exception as e:
                        file_contents.append(f"Error reading {file_name}: {str(e)}")

            return "\n\n".join(file_contents) if file_contents else "No valid files found in the 'context' folder."

        except Exception as e:
            return f"Error reading context files: {str(e)}"

    def get_price_codes_from_content(self, content, file_context, logic_content):
        try:
            # Send the content, logic, and file context to the assistant
            response = openai.ChatCompletion.create(
                model="gpt-4o-2024-08-06",  # Use the appropriate model
                messages=[
                    {"role": "system", "content": f"Use the following logic to generate price codes:\n\n{logic_content}\n\n Write your full working out and then write **Final Codes:** and output the final codes."},
                    {"role": "user", "content": f"Here is the content to process:\n{content}\n\nRelevant file information:\n{file_context}"}
                ],
                max_tokens=1000,  # Adjust as necessary
                temperature=0.1  # Adjust as needed
            )

            # Extract the assistant's response (price codes)
            assistant_response = response['choices'][0]['message']['content']
            return assistant_response
        except Exception as e:
            return f"Error: {str(e)}"

    def process_api_call(self, content, file_context, logic_content, AutoDocRef, clinic):
        try:
            # Get the price codes by sending the content, logic, and file context to OpenAI
            price_codes = self.get_price_codes_from_content(content, file_context, logic_content)

            # Debug print to check the content of price_codes
            print(f"Price codes received: {price_codes}")

            # Get the current date and time
            current_datetime = datetime.datetime.now()
            formatted_datetime = current_datetime.strftime('%Y-%m-%d %H:%M:%S')

            # Determine if we should check for base and special base
            model_id = self.model_id_var.get()
            if model_id == 'insoleFormV5':
                # Check for base in the extracted content and get the query message
                query_message = self.check_for_base(content)

                # Check for special base value and get the warning message
                warning_message = self.check_special_base(content)
            else:
                query_message = None
                warning_message = None

            # Check for clinic tariff and get the message (applies to all models)
            clinic_tariff_message = self.check_clinic_tariff(content)

            # Combine all messages
            messages = []
            if query_message:
                messages.append(query_message)
            if warning_message:
                messages.append(warning_message)
            if clinic_tariff_message:
                messages.append(clinic_tariff_message)
            combined_messages = '\n'.join(messages) if messages else None

            # Update the GUI with the results (must be done in the main thread)
            self.root.after(0, self.display_results, formatted_datetime, AutoDocRef, clinic, price_codes, combined_messages)

            # Write the price codes, auto doc reference, clinic, Azure data, and messages to the log file
            self.write_to_log_file(price_codes, AutoDocRef, clinic, content, combined_messages)

        except Exception as e:
            # Show error message in the main thread
            self.root.after(0, messagebox.showerror, "Error", f"Error processing the file: {str(e)}")
        finally:
            # Close the loading pop-up when done
            self.root.after(0, self.close_loading_popup)
            # Re-enable the upload button
            self.root.after(0, lambda: self.upload_pdf_button.config(state='normal'))

    def write_to_log_file(self, price_codes, auto_doc_ref, clinic, azure_data, messages=None):
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
            log_file_name = f"{sanitized_auto_doc_ref}.txt"
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

            if model_id == 'insoleFormV5':
                # Determine form_type based on extracted data
                form_type = self.determine_form_type(fields_data)
                if not form_type:
                    query_message = "No form type found in the extracted data. Please raise a query."
                    self.root.after(0, messagebox.showinfo, "Query", query_message)
                    # Optionally, you can log this message or handle it as needed
                    # Close the loading pop-up
                    self.root.after(0, self.close_loading_popup)
                    # Re-enable the upload button
                    self.root.after(0, lambda: self.upload_pdf_button.config(state='normal'))
                    return  # Stops further processing

                # Sanitize form_type
                form_type = ''.join(char for char in form_type if char.isalnum() or char in ('_', '-')).lower()
                print(f"Form type: {form_type}")

                # Construct the logic file name and path based on the form type
                logic_file_mapping = {
                    'tci': 'tci_logic.txt',
                    'simple': 'simple_insole_logic.txt',
                    'cradle': 'tci_logic.txt',  # Using tci_logic.txt for cradle
                    'handmold': 'tci_logic.txt'  # Using tci_logic.txt for handmold
                }

                logic_file_name = logic_file_mapping.get(form_type)
                print(f"Logic file name: {logic_file_name}")
                if not logic_file_name:
                    raise ValueError(f"No logic file mapping found for form type '{form_type}'.")

            elif model_id == 'AfoReaderV2':
                logic_file_name = 'afo_logic.txt'
                print(f"Logic file name: {logic_file_name}")

            else:
                raise ValueError(f"Unknown model ID '{model_id}'.")

            logic_file_path = os.path.join(os.getcwd(), 'logic_folder', logic_file_name)
            print(f"Logic file path: {logic_file_path}")

            # Read the logic file
            logic_content = self.read_logic_file(logic_file_path)
            if "Error" in logic_content:
                raise ValueError(logic_content)

            # Read context files
            file_context = self.read_files_for_context()
            if "Error" in file_context:
                raise ValueError(file_context)

            # Call the API with the content
            self.process_api_call(content, file_context, logic_content, AutoDocRef, clinic)

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
            if key.lower() == 'tci' and value.lower() == 'selected':
                form_type = 'tci'
                break
            elif key.lower() == 'tci test' and value.lower() == 'selected':
                form_type = 'tci'
            elif key.lower() == 'simple' and value.lower() == 'selected':
                form_type = 'simple'
                break
            elif key.lower() == 'hand mould' and value.lower() == 'selected':
                form_type = 'handmold'
                break
            elif key.lower() == 'cradle' and value.lower() == 'selected':
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

    def check_special_base(self, data):
        # Initialize variables
        base_value = ''
        spenco_selected = False
        lining_selected = False

        # Split the data into lines and look for the relevant lines
        for line in data.split('\n'):
            line_lower = line.lower().strip()
            if line_lower.startswith('base:'):
                base_value = line[len('base:'):].strip()
            elif line_lower.startswith('top cover material:'):
                value = line[len('top cover material:'):].strip()
                if value.lower() == 'spenco (green)':
                    spenco_selected = True
            elif line_lower.startswith('lining to full:'):
                value = line[len('lining to full:'):].strip()
                if value.lower() == 'selected':
                    lining_selected = True

        # Check if the base_value is '35/20/80 SH' or '45/30/80 SH' (case-insensitive)
        base_value_lower = base_value.strip().lower()
        if base_value_lower in ('35/20/80 sh', '45/30/80 sh'):
            if spenco_selected or lining_selected:
                warning_message = f"Base is {base_value}. Spenco top cover or Lining to full is selected. Use code B55c."
            else:
                warning_message = f"Base is {base_value}. Use code B55b."
            self.root.after(0, messagebox.showwarning, "Special Base Warning", warning_message)
            return warning_message
        else:
            return None  # No warning needed
        
    def check_clinic_tariff(self, data):
        # Initialize clinic_value
        clinic_value = ''
        # Split the data into lines and look for the line that starts with 'Clinic:'
        for line in data.split('\n'):
            if line.lower().startswith('clinic:'):
                clinic_value = line[len('clinic:'):].strip()
                break  # Stop after finding the clinic line

        # List of clinics to check
        clinics_with_tariff = ['Bury CDC', 'East Surrey', 'WS', 'PCH', 'Sudbury', 'Hinchingbrooke']

        # Check the clinic_value and create appropriate message
        if clinic_value in clinics_with_tariff:
            message = f"Tariff: {clinic_value}"
            self.root.after(0, messagebox.showinfo, "Clinic Tariff", message)
            return message
        elif clinic_value == 'Medway':
            message = "Tariff: Medbns72"
            self.root.after(0, messagebox.showinfo, "Clinic Tariff", message)
            return message
        else:
            return None  # No message needed


# --- Main Application Setup ---

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

# Load the logo image
try:
    logo_img = Image.open(logo_file_path)
    logo_img = logo_img.resize((200, 100), Image.LANCZOS)
    logo_photo = ImageTk.PhotoImage(logo_img)
    root.logo_photo = logo_photo  # Keep a reference to prevent garbage collection

    # Create a label to display the logo using ttk.Label
    logo_label = ttk.Label(root, image=logo_photo)
    logo_label.pack(pady=10)
except Exception as e:
    messagebox.showerror("Error", f"Error loading logo: {str(e)}")

# Add a bold title below the logo using ttk.Label
title_label = ttk.Label(root, text="Code Automation Program", font=("Calibri", 16, "bold"))
title_label.pack(pady=5)

# Define the custom font for the labels
label_font = ('Calibri', 11)  # You can adjust the font size as needed

# Create a frame for the info boxes
info_frame = ttk.Frame(root)
info_frame.pack(pady=10)

# Create labels and entries for AutoDocRef, Clinic, Date and Time with the larger font
auto_doc_ref_label = ttk.Label(info_frame, text='AutoDocRef:', font=label_font)
auto_doc_ref_entry = ttk.Entry(info_frame, width=30)
clinic_label = ttk.Label(info_frame, text='Clinic:', font=label_font)
clinic_entry = ttk.Entry(info_frame, width=30)
datetime_label = ttk.Label(info_frame, text='Date and Time:', font=label_font)
datetime_entry = ttk.Entry(info_frame, width=30)

# Arrange them in a grid layout
auto_doc_ref_label.grid(row=0, column=0, padx=5, pady=5)
auto_doc_ref_entry.grid(row=1, column=0, padx=5, pady=5)
clinic_label.grid(row=0, column=1, padx=5, pady=5)
clinic_entry.grid(row=1, column=1, padx=5, pady=5)
datetime_label.grid(row=0, column=2, padx=5, pady=5)
datetime_entry.grid(row=1, column=2, padx=5, pady=5)

# Create a frame to hold the result text widget and scrollbar
result_frame = ttk.Frame(root)
result_frame.pack(pady=10, anchor='center')

# Create a text widget inside the result_frame to display the results
result_text = tk.Text(result_frame, wrap='word', height=25, width=80)
result_text.grid(row=0, column=0)

# Create a vertical scrollbar linked to the result_text widget
result_scrollbar = ttk.Scrollbar(result_frame, orient='vertical', command=result_text.yview)
result_scrollbar.grid(row=0, column=1, sticky='ns')

# Configure the text widget to use the scrollbar
result_text['yscrollcommand'] = result_scrollbar.set

result_text.config(state='disabled')  # Make it read-only

# Make the result_text widget a drop target
result_text.drop_target_register(DND_FILES)

# Function to handle dropped files
def handle_drop(event):
    # event.data contains the list of files dropped
    # It may contain multiple files separated by spaces or newlines
    files = root.tk.splitlist(event.data)
    pdf_files = [f for f in files if f.lower().endswith('.pdf')]
    if pdf_files:
        for pdf_file in pdf_files:
            # Disable the upload button to prevent multiple clicks
            pdf_handler.upload_pdf_button.config(state='disabled')
            try:
                # Show the loading pop-up with animation
                show_loading_popup()

                # Start processing each PDF file in a separate thread
                threading.Thread(target=pdf_handler.process_pdf_and_call_api, args=(pdf_file,)).start()
            except Exception as e:
                messagebox.showerror("Error", f"Error processing the file: {str(e)}")
                pdf_handler.upload_pdf_button.config(state='normal')  # Re-enable the upload button
                close_loading_popup()  # Ensure the loading pop-up is closed if an error occurs
    else:
        messagebox.showinfo("No PDF Files", "Please drop PDF files only.")

# Bind the drop event to the handle_drop function
result_text.dnd_bind('<<Drop>>', handle_drop)

# Define model IDs (replace with your actual model IDs)
model_ids = {
    'Insoles': 'insoleFormV5',  # model id's
    'AFOs': 'AfoReaderV2'   
}

# Set up the model_id_var with default value
model_id_var = tk.StringVar(value='insoleFormV5')  # Set the default model ID

# Create a frame for the model selection
model_frame = ttk.Frame(root)
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

# Function to show the loading pop-up with moving dots animation on a new line
def show_loading_popup():
    global loading_popup, loading_label, dot_index, base_message
    loading_popup = Toplevel(root)
    loading_popup.title("Loading...")

    # Set icon on loading pop-up
    icon_image_loading = load_icon_image(icon_path, size=(32, 32))
    if icon_image_loading:
        loading_popup.iconphoto(False, icon_image_loading)
        loading_popup.icon_image = icon_image_loading  # Keep a reference

    # Make the window non-resizable
    loading_popup.resizable(False, False)
    loading_popup.protocol("WM_DELETE_WINDOW", lambda: None)  # Disable the close button

    # Position the window in the center of the root window
    root.update_idletasks()  # Update "requested size" from geometry manager
    x = root.winfo_x() + (root.winfo_width() // 2) - (300 // 2)
    y = root.winfo_y() + (root.winfo_height() // 2) - (100 // 2)
    loading_popup.geometry(f"300x100+{x}+{y}")

    # Make the window stay on top of the root window
    loading_popup.transient(root)
    loading_popup.grab_set()

    # Set initial base message
    base_message = "Please wait, reading the file"

    # Add a label to display the loading message with dots on a new line
    loading_label = ttk.Label(loading_popup, text=f"{base_message}\n", font=("Calibri", 12, "bold"))
    loading_label.pack(expand=True, pady=20)

    dot_index = 0  # Initialize the dot counter
    animate_dots()  # Start the animation

    # Disable the main window while loading
    root.attributes('-disabled', True)

# Function to animate the moving dots
def animate_dots():
    global dot_index, base_message
    dots = ['.', '..', '...', '']
    # Update the label text
    loading_label.config(text=f"{base_message}\n{dots[dot_index]}")
    dot_index = (dot_index + 1) % len(dots)  # Loop through the dots
    # Update every 500ms (0.5 seconds)
    loading_popup.after(500, animate_dots)

# Function to close the loading pop-up
def close_loading_popup():
    loading_popup.destroy()
    root.attributes('-disabled', False)  # Re-enable the main window
    root.focus_force()  # Bring the main window back to focus

def display_results(formatted_datetime, AutoDocRef, clinic, price_codes, messages=None):
    # Update the entries
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
    if clinic:
        clinic_entry.insert(0, clinic)
    else:
        clinic_entry.insert(0, "N/A")
    clinic_entry.config(state='readonly')

    # Display the price codes in the result_text, centered
    result_text.config(state=tk.NORMAL)  # Enable editing temporarily
    result_text.delete('1.0', tk.END)  # Clear previous content

    # Configure tags
    result_text.tag_configure('center', justify='center')
    result_text.tag_configure('bold', font=('Calibri', 12, 'bold'))
    result_text.tag_configure('bold', font=('Calibri', 12, 'bold'))
    # You can adjust font sizes as needed

    # Split the price_codes into lines
    lines = price_codes.split('\n')

    for line in lines:
        stripped_line = line.strip()
        # Check for bold syntax (**text**)
        if stripped_line.startswith('**') and stripped_line.endswith('**'):
            content = stripped_line.strip('*')
            result_text.insert(tk.END, content + '\n', ('center', 'bold'))
        # Check for italic syntax (*text*)
        elif stripped_line.startswith('*') and stripped_line.endswith('*'):
            content = stripped_line.strip('*')
            result_text.insert(tk.END, content + '\n', ('center', 'bold'))
        else:
            result_text.insert(tk.END, line + '\n', 'center')

    # If there are messages, insert them below the price codes
    if messages:
        # Add a separator or newline
        result_text.insert(tk.END, "\n\n")
        # Configure the 'warning' tag for messages (you can adjust the font or color as needed)
        result_text.tag_configure('warning', justify='center', foreground='red', font=('Calibri', 12, 'bold'))
        # Insert messages with the 'warning' tag
        result_text.insert(tk.END, messages, 'warning')

    # Scroll to the end of the text
    result_text.see(tk.END)

    result_text.config(state=tk.DISABLED)  # Disable editing again

# --- Instantiate PdfButtonHandler and Setup GUI ---

# Create an instance of PdfButtonHandler
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

# Create the upload PDF button
upload_pdf_button = ttk.Button(root, text="Upload PDF", command=pdf_handler.upload_pdf_file)
upload_pdf_button.pack(pady=10)

# Set the button reference in the handler
pdf_handler.set_upload_pdf_button(upload_pdf_button)

# Create an exit button using ttk.Button
exit_button = ttk.Button(root, text="Exit", command=root.quit)
exit_button.pack(pady=10)

# Create a bottom frame to hold the theme selection dropdown and version label
bottom_frame = ttk.Frame(root)
bottom_frame.pack(side='bottom', fill='x', padx=10, pady=10)

# Create a label and Combobox for theme selection
theme_label = ttk.Label(bottom_frame, text='Theme:')
theme_label.pack(side='left', padx=(0, 5))

# Set the theme variable to the selected theme
theme_var = tk.StringVar(value=selected_theme)
theme_combobox = ttk.Combobox(
    bottom_frame, textvariable=theme_var, values=theme_list, state='readonly'
)
theme_combobox.pack(side='left')

# Add a spacer frame to push the version label to the right
spacer = ttk.Frame(bottom_frame)
spacer.pack(side='left', expand=True, fill='x')

# Create a label for the version number using the VERSION variable
version_label = ttk.Label(
    bottom_frame, text=f"Version {VERSION}", font=("Calibri", 10)
)
version_label.pack(side='right')

# Bind the selection change event
theme_combobox.bind('<<ComboboxSelected>>', change_theme)

# Start the GUI event loop
root.mainloop()
