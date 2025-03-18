# main.py
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
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import time
from analysis_tab import create_analysis_tab
import analysis_tab
from generate_code_logic import (
    generate_bespoke_codes,
    generate_insole_codes,
    generate_afo_codes,
    generate_modular_codes
)
# Version number
VERSION = "5.1.3-alpha"

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
        'InsoleFullReaderV6': 'insole',
        'AfoReaderV7': 'afo',
        'BespokeReaderFullV4': 'bespoke',
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
                    {"role": "system", "content": f"Use the following logic to generate price codes:\n\n{logic_content}\n\nThe 'Passed code' section contains codes that have already been generated and should be included in the final output.\n\nWrite your full working out and then write **Final Codes:** and output the final codes each on a new line, including the passed codes."},
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
            if model_id == 'InsoleFullReaderV6':
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

            if model_id == 'InsoleFullReaderV6':
                # Determine form_type based on extracted data
                form_type = self.determine_form_type(fields_data)

                # If still None, show popup. If 'other', skip the popup and default to 'tci'.
                if not form_type:
                    query_message = "No form type found in the extracted data. Please raise a query."
                    self.root.after(0, messagebox.showinfo, "Query", query_message)
                    form_type = 'tci'
                elif form_type == 'other':
                    # If 'insole type other' was present, skip popup & default to TCI (or your chosen fallback).
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
                passed_codes = generate_insole_codes(self, content)
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
                passed_codes = generate_afo_codes(self, content)
                if passed_codes:
                    # Append the passed codes under 'Passed code:' in the content
                    content += f"\n\nPassed code:\n{passed_codes}"
                    print(f"Passed codes added to content: {passed_codes}")
                else:
                    print("No passed codes generated.")

            elif model_id == 'BespokeReaderFullV4':
                logic_file_name = 'bespoke_logic.txt'
                print(f"Logic file name: {logic_file_name}")

                # Call the bespoke code generation method
                passed_codes = generate_bespoke_codes(self, content)
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
                passed_codes = generate_modular_codes(self, content)
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
        """
        Determine the form type based on the extracted data.
        (Now also checks for 'insole type other' if no standard form is found)
        """
        form_type = None

        for key, value in data.items():
            key_lower = key.lower()
            value_lower = value.lower()
            if key_lower == 'insole type tci' and value_lower == 'selected':
                form_type = 'tci'
                break
            elif key_lower == 'insole type simple' and value_lower == 'selected':
                form_type = 'simple'
                break
            elif key_lower == 'insole type hand mould' and value_lower == 'selected':
                form_type = 'handmold'
                break
            elif key_lower == 'insole type cradle' and value_lower == 'selected':
                form_type = 'cradle'
                break
            elif key_lower == 'afo' and value_lower == 'selected':
                form_type = 'afo'
                break
            elif key_lower == 'kafo' and value_lower == 'selected':
                form_type = 'kafo'
                break

        # -- New: If we found nothing, check if 'insole type other' has a value
        if not form_type:
            other_value = data.get('insole type other', '').strip().lower()
            if other_value and other_value != 'unselected':
                # We'll treat "other" as a valid form type and skip the popup
                form_type = 'other'
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

# --- Main Application Setup ---
def create_search_tab(notebook):
    """
    Creates a new tab in the provided ttk.Notebook for searching
    through the 'work_orders' folder by AutoDocRef (case-insensitive),
    with smaller scrollable listbox and text box,
    automatic searching with debouncing on each keystroke,
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
    search_after_id = None

    def live_search():
        """Handle keystrokes with debouncing for live search."""
        nonlocal search_after_id
        query = search_entry.get().strip()
        if not query:
            # Immediately clear the listbox if the query is empty
            results_listbox.delete(0, tk.END)
            file_content_text.config(state='normal')
            file_content_text.delete('1.0', tk.END)
            file_content_text.config(state='disabled')
            if search_after_id:
                root.after_cancel(search_after_id)
            search_after_id = None
        else:
            # Cancel any pending search and schedule a new one
            if search_after_id:
                root.after_cancel(search_after_id)
            search_after_id = root.after(300, perform_search)

    def perform_search():
        """Perform the case-insensitive search after the debounce delay."""
        results_listbox.delete(0, tk.END)
        file_content_text.config(state='normal')
        file_content_text.delete('1.0', tk.END)
        file_content_text.config(state='disabled')

        query = search_entry.get().strip().lower()
        work_orders_folder = os.path.join(os.getcwd(), 'work_orders')
        if not os.path.exists(work_orders_folder):
            return

        for date_folder in os.listdir(work_orders_folder):
            date_path = os.path.join(work_orders_folder, date_folder)
            if os.path.isdir(date_path):
                for filename in os.listdir(date_path):
                    if query in filename.lower():
                        full_path = os.path.join(date_path, filename)
                        results_listbox.insert(tk.END, full_path)

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

def apply_bg_recursively(widget, bg_color):
    """Apply the given bg_color to this widget and all children recursively."""
    try:
        widget.config(bg=bg_color)
    except tk.TclError:
        # Some widgets don’t support a 'bg' config
        pass
    for child in widget.winfo_children():
        apply_bg_recursively(child, bg_color)

def change_theme(event):
    selected_theme = theme_var.get()
    style.theme_use(selected_theme)
    save_theme_setting(selected_theme)

    # (After setting style.theme_use and saving your settings, etc.)

# Reconfigure the analysis frame's background
    style.configure("Analysis.TFrame", background=style.colors.bg)

# Then re-draw the chart with new colors

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
    'Insoles': 'InsoleFullReaderV6',
    'AFOs': 'AfoReaderV7',
    'Bespoke': 'BespokeReaderFullV4',
    'Modular': 'ModularReaderFullV3'
}
model_id_var = tk.StringVar(value='InsoleFullReaderV6')

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

        # Automatically copy the final codes if auto-watch is enabled
    if auto_watch_var.get():
        copy_final_codes()

def copy_final_codes():
    """
    Copies all text from the last occurrence of 'Final Codes'
    (case-sensitive) through the end of the result_text widget,
    and flashes the button instead of showing a popup.
    """
    full_text = result_text.get("1.0", tk.END)

    # Find the last occurrence of "Final Codes"
    last_index = full_text.rfind("Final Codes")
    if last_index == -1:
        # No flash or popup – optionally you could flash in a different color or show a brief label
        return

    # Everything from 'Final Codes' to the end of the text
    final_codes_text = full_text[last_index:]

    # Copy to clipboard
    root.clipboard_clear()
    root.clipboard_append(final_codes_text)

    # Flash the button: create a temporary style with “inverted” colors
    original_style = copy_codes_button.cget("style")
    style.configure(
        "Flash.TButton",
        background=style.colors.fg,     # or any color you like
        foreground=style.colors.bg      # or any color you like
    )
    copy_codes_button.configure(style="Flash.TButton")

    # Revert after 300ms
    def revert_style():
        copy_codes_button.configure(style=original_style)

    root.after(300, revert_style)

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
auto_watch_var = tk.BooleanVar(value=False)

def on_auto_watch_toggled():
    """When the checkbox is ticked ON, we skip any existing PDFs in Downloads."""
    if auto_watch_var.get():
        # user just turned the checkbox ON
        downloads_folder = os.path.join(os.path.expanduser("~"), "Downloads")
        if os.path.isdir(downloads_folder):
            # gather all current .pdf files
            existing_pdfs = {
                f for f in os.listdir(downloads_folder)
                if f.lower().endswith('.pdf')
            }
            # mark them as “already seen”
            known_downloads.update(existing_pdfs)

# We'll track which files we've seen so we don't re-process them
known_downloads = set()
# Store the username for the network Downloads folder path, initially None
downloads_username = None

def on_auto_watch_toggled():
    """Handle the auto-watch checkbox toggle: prompt for username when enabled."""
    global downloads_username  # Access the global username variable
    if auto_watch_var.get():  # If the checkbox is checked (turned on)
        # Prompt user for their username
        username = simpledialog.askstring("Username Required", "Please enter your firstname.lastname for the Downloads folder path:")
        if username:  # If a username was provided
            downloads_username = username  # Store it globally
            # Construct the network path using the username
            downloads_folder = f"\\\\halo-dc\\folderredirects$\\{downloads_username}\\Downloads"
            if os.path.isdir(downloads_folder):  # Check if the folder exists
                # Gather all current PDFs to mark them as already seen
                existing_pdfs = {
                    f for f in os.listdir(downloads_folder)
                    if f.lower().endswith('.pdf')
                }
                known_downloads.update(existing_pdfs)  # Update the set of known files
            else:  # If the folder doesn’t exist
                messagebox.showwarning("Warning", f"Downloads folder not found at {downloads_folder}")
                auto_watch_var.set(False)  # Disable auto-watch
        else:  # If user cancels or enters nothing
            messagebox.showwarning("Warning", "Username is required for auto-watch feature.")
            auto_watch_var.set(False)  # Disable auto-watch

def watch_downloads_folder():
    if auto_watch_var.get() and downloads_username is not None:  # Only proceed if username is set
        downloads_folder = f"\\\\halo-dc\\folderredirects$\\{downloads_username}\\Downloads"
        print(f"Checking folder: {downloads_folder}")
        if not os.path.exists(downloads_folder):
            print(f"Folder does not exist: {downloads_folder}")
            messagebox.showwarning("Warning", f"Downloads folder not found at {downloads_folder}")
            return
        pdf_files = [f for f in os.listdir(downloads_folder) if f.lower().endswith('.pdf')]
        print(f"Found {len(pdf_files)} PDF files")
        if pdf_files:
            pdf_files.sort(key=lambda f: os.path.getmtime(os.path.join(downloads_folder, f)))
            newest_pdf = pdf_files[-1]
            pdf_path = os.path.join(downloads_folder, newest_pdf)
            if newest_pdf not in known_downloads:
                print(f"Processing new PDF: {pdf_path}")
                known_downloads.add(newest_pdf)
                pdf_handler.show_loading_popup()
                pdf_handler.upload_pdf_button.config(state='disabled')
                threading.Thread(target=pdf_handler.process_pdf_and_call_api, args=(pdf_path,)).start()
    root.after(1000, watch_downloads_folder)

auto_watch_check = ttk.Checkbutton(
    main_tab,
    text="Auto-detect new PDF in Downloads (beta)",
    variable=auto_watch_var,
    command=on_auto_watch_toggled
)
auto_watch_check.pack(pady=5)

copy_codes_button = ttk.Button(main_tab, text="Copy to Clipboard", command=copy_final_codes)
copy_codes_button.pack(pady=5)

upload_pdf_button = ttk.Button(main_tab, text="Upload PDF", command=pdf_handler.upload_pdf_file)
upload_pdf_button.pack(pady=5)

pdf_handler.set_upload_pdf_button(upload_pdf_button)

exit_button = ttk.Button(main_tab, text="Exit", command=root.quit)
exit_button.pack(pady=5)

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
# ---------------------------
# RESULTS ANALYSIS TAB
analysis_tab, analysis_handles = create_analysis_tab(notebook, style)

"""def toggle_multi_mode():
    new_state = not analysis_handles["is_multi_mode"]()
    analysis_handles["set_multi_mode"](new_state)
    analysis_handles["refresh_chart"]()

toggle_button = ttk.Button(
    analysis_tab,
    text="Toggle Multi-Line Mode",
    command=toggle_multi_mode
)
toggle_button.pack(pady=5)
"""
# search work orders warning
# Now bind the event to show the warning upon switching to the Search tab
def on_tab_selected(event):
    selected_tab_text = event.widget.tab(event.widget.index("current"), "text")
    if selected_tab_text == "Search Work Orders":
        messagebox.showwarning(
            "Feature WIP",
            "Warning: The 'Search Work Orders' feature is still a work in progress!"
        )
    elif selected_tab_text == "Results Analysis":
        # Recalculate the analysis tab whenever it is clicked
        analysis_handles["refresh_chart"]()

notebook.bind("<<NotebookTabChanged>>", on_tab_selected)

# Start watching the Downloads folder in the background
watch_downloads_folder()

# Start the GUI event loop
root.mainloop()