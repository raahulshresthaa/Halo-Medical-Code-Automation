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

# Azure Form Recognizer imports
from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient

# --- PdfButtonHandler Class Definition ---

class PdfButtonHandler:
    def __init__(self, root, current_dir, result_text, auto_doc_ref_entry, datetime_entry, clinic_entry, show_loading_popup, close_loading_popup, display_results):
        self.root = root
        self.current_dir = current_dir
        self.result_text = result_text
        self.auto_doc_ref_entry = auto_doc_ref_entry
        self.datetime_entry = datetime_entry
        self.clinic_entry = clinic_entry
        self.show_loading_popup = show_loading_popup
        self.close_loading_popup = close_loading_popup
        self.display_results = display_results

        # Path to the 'context' folder where the additional context files are stored
        self.context_folder_path = os.path.join(self.current_dir, 'context')

        # Reference to the upload PDF button (will be set later)
        self.upload_pdf_button = None

        # Read Azure credentials from files
        self.endpoint = self.read_azure_credential_file('azure_endpoint.txt', 'Azure Endpoint')
        self.key = self.read_azure_credential_file('azure_key.txt', 'Azure Key')
        self.model_id = self.read_azure_credential_file('azure_model_id.txt', 'Azure Model ID')

        # Validate endpoint and key
        if not self.endpoint or not isinstance(self.endpoint, str):
            raise ValueError("Azure endpoint is not set or is not a valid string.")
        if not self.key or not isinstance(self.key, str):
            raise ValueError("Azure key is not set or is not a valid string.")
        if not self.model_id or not isinstance(self.model_id, str):
            raise ValueError("Azure model ID is not set or is not a valid string.")

        # Initialize Azure Form Recognizer client
        self.document_analysis_client = DocumentAnalysisClient(
            endpoint=self.endpoint,
            credential=AzureKeyCredential(self.key)
        )

    def set_upload_pdf_button(self, button):
        self.upload_pdf_button = button

    def read_azure_credential_file(self, filename, credential_name):
        """Reads and decodes the Azure credential from a file."""
        file_path = os.path.join(self.current_dir, filename)
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
        file_path = os.path.join(self.current_dir, filename)
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

    def get_tariff_codes_from_content(self, content, file_context, logic_content):
        try:
            # Send the content, logic, and file context to the assistant
            response = openai.ChatCompletion.create(
                model="gpt-4o",  # Use the appropriate model
                messages=[
                    {"role": "system", "content": f"Use the following logic to generate tariff codes:\n\n{logic_content}\n\nOnly output the calculated tariff codes."},
                    {"role": "user", "content": f"Here is the content to process:\n{content}\n\nRelevant file information:\n{file_context}"}
                ],
                max_tokens=1000,  # Adjust as necessary
                temperature=0.1  # Adjust as needed
            )

            # Extract the assistant's response (tariff codes)
            assistant_response = response['choices'][0]['message']['content']
            return assistant_response
        except Exception as e:
            return f"Error: {str(e)}"

    def process_api_call(self, content, file_context, logic_content, AutoDocRef, clinic):
        try:
            # Get the tariff codes by sending the content, logic, and file context to OpenAI
            tariff_codes = self.get_tariff_codes_from_content(content, file_context, logic_content)

            # Debug print to check the content of tariff_codes
            print(f"Tariff codes received: {tariff_codes}")

            # Get the current date and time
            current_datetime = datetime.datetime.now()
            formatted_datetime = current_datetime.strftime('%Y-%m-%d %H:%M:%S')

            # Update the GUI with the results (must be done in the main thread)
            self.root.after(0, self.display_results, formatted_datetime, AutoDocRef, clinic, tariff_codes)

            # Write the tariff codes, auto doc reference, and clinic to the log file
            self.write_to_log_file(tariff_codes, AutoDocRef, clinic)

        except Exception as e:
            # Show error message in the main thread
            self.root.after(0, messagebox.showerror, "Error", f"Error processing the file: {str(e)}")
        finally:
            # Close the loading pop-up when done
            self.root.after(0, self.close_loading_popup)
            # Re-enable the upload button
            self.root.after(0, lambda: self.upload_pdf_button.config(state='normal'))

    def write_to_log_file(self, tariff_codes, auto_doc_ref, clinic):
        try:
            # Ensure the result_logs folder exists
            result_logs_folder = os.path.join(self.current_dir, 'result_logs')
            if not os.path.exists(result_logs_folder):
                os.makedirs(result_logs_folder)

            # Get the current date and time
            current_datetime = datetime.datetime.now()
            formatted_date = current_datetime.strftime('%d_%m_%y')  # Format: DD_MM_YY

            # Construct the log file path
            log_file_name = f"log_{formatted_date}.txt"
            log_file_path = os.path.join(result_logs_folder, log_file_name)

            with open(log_file_path, 'a', encoding='utf-8') as log_file:
                formatted_datetime = current_datetime.strftime('%Y-%m-%d %H:%M:%S')

                log_file.write(f"Date and Time: {formatted_datetime}\n")
                log_file.write(f"Auto Doc Reference: {auto_doc_ref}\n")
                log_file.write(f"Clinic: {clinic}\n")
                log_file.write(f"Tariff Codes:\n{tariff_codes}\n")
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
            # Analyze the PDF using Azure Form Recognizer
            with open(pdf_file_path, "rb") as pdf_file:
                poller = self.document_analysis_client.begin_analyze_document(self.model_id, document=pdf_file)
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

            # Determine form_type based on extracted data
            form_type = self.determine_form_type(fields_data)
            if not form_type:
                raise ValueError("No form type found in the extracted data.")

            # Sanitize form_type
            form_type = ''.join(char for char in form_type if char.isalnum() or char in ('_', '-')).lower()
            print(f"Form type: {form_type}")

            # Construct the logic file name and path based on the form type
            logic_file_mapping = {
                'tci': 'tci_logic.txt',
                'simple': 'simple_insole_logic.txt',
                'cradle': 'cradle_logic.txt',
                'afo': 'afo_logic.txt',
                'kafo': 'kafo_logic.txt',
                'handmold': 'handmold_logic.txt'
            }

            logic_file_name = logic_file_mapping.get(form_type)
            print(f"Logic file name: {logic_file_name}")
            if not logic_file_name:
                raise ValueError(f"No logic file mapping found for form type '{form_type}'.")

            logic_folder_path = os.path.join(self.current_dir, 'logic_folder')
            logic_file_path = os.path.join(logic_folder_path, logic_file_name)
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

# --- Main Application Setup ---

# Get the path of the directory where this Python script is located
current_dir = os.path.dirname(os.path.abspath(__file__))

# Define the list of available themes
theme_list = ['lumen', 'darkly', 'solar', 'cyborg', 'simplex', 'vapor']

# Function to load the saved theme setting
def load_theme_setting():
    settings_file = os.path.join(current_dir, 'settings.txt')
    if os.path.exists(settings_file):
        try:
            with open(settings_file, 'r') as f:
                theme = f.read().strip()
                if theme in theme_list:
                    return theme
                else:
                    return 'darkly'  # Default theme if saved theme is invalid
        except:
            return 'darkly'  # Default theme in case of error
    else:
        return 'darkly'  # Default theme if settings file does not exist

# Function to save the selected theme setting
def save_theme_setting(theme):
    settings_file = os.path.join(current_dir, 'settings.txt')
    with open(settings_file, 'w') as f:
        f.write(theme)

# Load the selected theme at startup
selected_theme = load_theme_setting()

# Function to write the API key in binary (encoded using Base64)
def write_api_key(api_key):
    api_key_file = os.path.join(current_dir, 'api_key.txt')
    # Encode the API key as bytes, then convert it to Base64 for binary storage
    encoded_key = base64.b64encode(api_key.encode('utf-8'))
    with open(api_key_file, 'wb') as f:
        f.write(encoded_key)
    print(f"API key saved to {api_key_file}")

# Function to read and decode the API key from binary (Base64-decoded back to a string)
def read_api_key():
    api_key_file = os.path.join(current_dir, 'api_key.txt')
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
    result_logs_folder = os.path.join(current_dir, 'result_logs')
    if not os.path.exists(result_logs_folder):
        os.makedirs(result_logs_folder)
        print(f"Created 'result_logs' folder at {result_logs_folder}")
    else:
        print(f"'result_logs' folder already exists at {result_logs_folder}")

ensure_result_logs_folder_exists()

# Load and set the custom window icon (top-left)
icon_path = os.path.join(current_dir, 'halo_simple_logo.png')  # Path to your .png file

# Define the path for the logo file
logo_file_path = os.path.join(current_dir, 'HALO(TM)_Logo.png')

# Define the path to the 'context' folder where the additional context files are stored
context_folder_path = os.path.join(current_dir, 'context')

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

# Set the window size and position (800x900 starting at 100px from top and 100px from left)
root.geometry("800x900+100+100")

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
auto_doc_ref_label = ttk.Label(info_frame, text='AutoDocRef:', font=label_font)  # Adjust font size if needed
auto_doc_ref_entry = ttk.Entry(info_frame, width=30)
clinic_label = ttk.Label(info_frame, text='Clinic:', font=label_font)  # Adjust font size if needed
clinic_entry = ttk.Entry(info_frame, width=30)
datetime_label = ttk.Label(info_frame, text='Date and Time:', font=label_font)  # Adjust font size if needed
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

# Function to display results
def display_results(formatted_datetime, AutoDocRef, clinic, tariff_codes):
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

    # Display the tariff codes in the result_text, centered
    result_text.config(state=tk.NORMAL)  # Enable editing temporarily
    result_text.delete('1.0', tk.END)  # Clear previous content

    # Configure the 'center' tag before inserting text
    result_text.tag_configure('center', justify='center')

    # Insert the tariff codes and apply the 'center' tag
    result_text.insert(tk.END, tariff_codes, 'center')

    result_text.config(state=tk.DISABLED)  # Disable editing again

# --- Instantiate PdfButtonHandler and Setup GUI ---

# Create an instance of PdfButtonHandler
pdf_handler = PdfButtonHandler(
    root=root,
    current_dir=current_dir,
    result_text=result_text,
    auto_doc_ref_entry=auto_doc_ref_entry,
    datetime_entry=datetime_entry,
    clinic_entry=clinic_entry,
    show_loading_popup=show_loading_popup,
    close_loading_popup=close_loading_popup,
    display_results=display_results
)

# Create the upload PDF button
upload_pdf_button = ttk.Button(root, text="Upload PDF", command=pdf_handler.upload_pdf_file)
upload_pdf_button.pack(pady=10)

# Set the button reference in the handler
pdf_handler.set_upload_pdf_button(upload_pdf_button)

# Create an exit button using ttk.Button
exit_button = ttk.Button(root, text="Exit", command=root.quit)
exit_button.pack(pady=10)

# Create a bottom frame to hold the theme selection dropdown
bottom_frame = ttk.Frame(root)
bottom_frame.pack(side='bottom', fill='x', padx=10, pady=10)

# Create a label and Combobox for theme selection
theme_label = ttk.Label(bottom_frame, text='Theme:')
theme_label.pack(side='left', padx=(0, 5))

# Set the theme variable to the selected theme
theme_var = tk.StringVar(value=selected_theme)
theme_combobox = ttk.Combobox(bottom_frame, textvariable=theme_var, values=theme_list, state='readonly')
theme_combobox.pack(side='left')

# Bind the selection change event
theme_combobox.bind('<<ComboboxSelected>>', change_theme)

# Start the GUI event loop
root.mainloop()
