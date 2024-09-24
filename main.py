import os
import openai
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, Toplevel
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from PIL import Image, ImageTk
import xml.etree.ElementTree as ET
import datetime
import threading
import sys

# Function to read the API key from a file
def load_api_key():
    api_key_file = os.path.join(os.path.dirname(__file__), 'api_key.txt')
    try:
        with open(api_key_file, 'r') as f:
            api_key = f.readline().strip()  # Read and strip any extra whitespace
            if not api_key:
                raise ValueError("API key file is empty")
            return api_key
    except FileNotFoundError:
        messagebox.showerror("Error", "api_key.txt file not found. Please add the OpenAI API key in this file.")
        sys.exit()
    except Exception as e:
        messagebox.showerror("Error", f"Error reading API key: {str(e)}")
        sys.exit()

# Load the API key from the file
openai_api_key = load_api_key()

# Set the OpenAI API key for OpenAI requests
openai.api_key = openai_api_key

# Check if the API key was properly loaded
if not openai.api_key:
    messagebox.showerror("Error", "OpenAI API key not found or invalid. Please set the API key in api_key.txt.")
    sys.exit()

# Get the path of the directory where this Python script is located
current_dir = os.path.dirname(os.path.abspath(__file__))

# Load and set the custom window icon (top-left)
icon_path = os.path.join(current_dir, 'halo_simple_logo.png')  # Path to your .ico file

# Define the path for the logo file
logo_file_path = os.path.join(current_dir, 'HALO(TM)_Logo.png')

# Define the path to the 'context' folder where the additional context files are stored
context_folder_path = os.path.join(current_dir, 'context')

# Function to read the logic file
def read_logic_file(logic_file_path):
    try:
        with open(logic_file_path, 'r', encoding='utf-8') as logic_file:
            logic_content = logic_file.read()
        return logic_content
    except Exception as e:
        return f"Error reading the logic file '{logic_file_path}': {str(e)}"

# Function to automatically read all files in the 'context' folder
def read_files_for_context():
    file_contents = []
    try:
        # Check if the context folder exists
        if not os.path.exists(context_folder_path):
            return "Error: 'context' folder not found."

        # Iterate over all files in the 'context' folder
        for file_name in os.listdir(context_folder_path):
            file_path = os.path.join(context_folder_path, file_name)
            
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

# Function to read the XML file content as a string
def read_xml_file(xml_file_path):
    try:
        with open(xml_file_path, 'r', encoding='utf-8') as file:
            xml_content = file.read()
        return xml_content
    except Exception as e:
        messagebox.showerror("Error", f"Error reading XML file: {str(e)}")
        return None

# Function to find form type
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

        # Iterate over each type (TCI, Simple, Cradle)
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
            # Prompt the user to select one
            selected_type = simpledialog.askstring("Multiple Types Selected",
                                                   f"Multiple form types are selected: {', '.join(selected_types)}.\nPlease enter the type you want to process:")
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
        # Use XPath-like search to find 'AutoDocRef' at any depth
        auto_doc_ref_element = root.find('.//AutoDocRef')
        if auto_doc_ref_element is not None and auto_doc_ref_element.text:
            return auto_doc_ref_element.text.strip()
        else:
            return None
    except Exception as e:
        messagebox.showerror("Error", f"Error extracting auto doc reference: {str(e)}")
        return None

# Function to extract clinic from XML
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

# Function to process XML file and get tariff codes from the assistant using the logic from the text file
def get_tariff_codes_from_xml(xml_string, file_context, logic_content):
    try:
        # Send the XML string, logic, and file context to the assistant
        response = openai.ChatCompletion.create(
            model="gpt-4o",  # Adjust this if you're using a different model
            messages=[
                {"role": "system", "content": f"Use the following logic to generate tariff codes:\n\n{logic_content}\n\nOnly output the calculated tariff codes."},
                {"role": "user", "content": f"Here is the XML content to process:\n{xml_string}\n\nRelevant file information:\n{file_context}"}
            ],
            max_tokens=1000,  # Adjust as necessary
            temperature=0.1  # Adjust as needed
        )

        # Extract the assistant's response (tariff codes)
        assistant_response = response['choices'][0]['message']['content']
        return assistant_response
    except Exception as e:
        return f"Error: {str(e)}"

# Function to write tariff codes, auto doc reference, and clinic to the log file
def write_to_log_file(tariff_codes, auto_doc_ref, clinic):
    try:
        log_file_path = os.path.join(current_dir, 'results_log.txt')
        with open(log_file_path, 'a', encoding='utf-8') as log_file:
            # Get the current date and time
            current_datetime = datetime.datetime.now()
            formatted_datetime = current_datetime.strftime('%Y-%m-%d %H:%M:%S')

            log_file.write(f"Date and Time: {formatted_datetime}\n")
            log_file.write(f"Auto Doc Reference: {auto_doc_ref}\n")
            log_file.write(f"Clinic: {clinic}\n")
            log_file.write(f"Tariff Codes:\n{tariff_codes}\n")
            log_file.write("-" * 50 + "\n")  # Separator between entries
        print(f"Successfully wrote to log file at {log_file_path}")
    except Exception as e:
        messagebox.showerror("Error", f"Error writing to log file: {str(e)}")

# Function to show the loading pop-up
def show_loading_popup():
    global loading_popup
    loading_popup = Toplevel(root)
    loading_popup.title("Loading...")

    # Set icon on loading pop-up
    loading_popup.iconphoto(False, tk.PhotoImage(file=icon_path))  # Set the pop-up window icon

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

    # Add a label to display the loading message
    loading_label = ttk.Label(loading_popup, text="Please wait, processing...", font=("Helvetica", 12, "bold"))
    loading_label.pack(expand=True, pady=20)

    # Disable the main window while loading
    root.attributes('-disabled', True)

# Function to close the loading pop-up
def close_loading_popup():
    loading_popup.destroy()
    root.attributes('-disabled', False)  # Re-enable the main window

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

# Function to process the API call in a separate thread
def process_api_call(xml_content, file_context, logic_content, AutoDocRef, clinic):
    try:
        # Get the tariff codes by sending the XML string, logic, and file context to OpenAI
        tariff_codes = get_tariff_codes_from_xml(xml_content, file_context, logic_content)

        # Debug print to check the content of tariff_codes
        print(f"Tariff codes received: {tariff_codes}")

        # Get the current date and time
        current_datetime = datetime.datetime.now()
        formatted_datetime = current_datetime.strftime('%Y-%m-%d %H:%M:%S')

        # Update the GUI with the results (must be done in the main thread)
        root.after(0, display_results, formatted_datetime, AutoDocRef, clinic, tariff_codes)

        # Write the tariff codes, auto doc reference, and clinic to the log file
        write_to_log_file(tariff_codes, AutoDocRef, clinic)

    except Exception as e:
        # Show error message in the main thread
        root.after(0, messagebox.showerror, "Error", f"Error processing the file: {str(e)}")
    finally:
        # Close the loading pop-up when done
        root.after(0, close_loading_popup)
        # Re-enable the upload button
        root.after(0, lambda: upload_button.config(state='normal'))

# Function to handle file upload and start the process
def upload_file():
    # Open a file dialog for selecting XML files
    xml_file_path = filedialog.askopenfilename(title="Select the XML File", filetypes=[("XML Files", "*.xml")])

    if xml_file_path:
        # Disable the upload button to prevent multiple clicks
        upload_button.config(state='disabled')

        try:
            # Read the XML file content
            xml_content = read_xml_file(xml_file_path)
            if xml_content is None:
                upload_button.config(state='normal')  # Re-enable the upload button
                return

            # Extract the form type from the XML string
            form_type = extract_form_type_from_xml_string(xml_content)
            print(f"Extracted form type: {form_type}")
            if not form_type:
                messagebox.showerror("Error", "No form type selected in the XML file.")
                upload_button.config(state='normal')  # Re-enable the upload button
                return

            # Extract the auto doc reference from the XML string
            AutoDocRef = extract_auto_doc_reference_from_xml_string(xml_content)
            print(f"Extracted auto doc reference: {AutoDocRef}")
            if not AutoDocRef:
                AutoDocRef = "N/A"  # Default value if not found

            # Extract the clinic from the XML string
            clinic = extract_clinic_from_xml_string(xml_content)
            print(f"Extracted clinic: {clinic}")
            if not clinic:
                clinic = "N/A"

            # Sanitize form_type to prevent security issues
            form_type = ''.join(char for char in form_type if char.isalnum() or char in ('_', '-')).lower()
            print(f"Sanitized form type: {form_type}")

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
                messagebox.showerror("Error", f"No logic file mapping found for form type '{form_type}'.")
                upload_button.config(state='normal')  # Re-enable the upload button
                return

            logic_folder_path = os.path.join(current_dir, 'logic_folder')
            logic_file_path = os.path.join(logic_folder_path, logic_file_name)
            print(f"Logic file path: {logic_file_path}")

            # Read the logic file
            logic_content = read_logic_file(logic_file_path)
            if "Error" in logic_content:
                messagebox.showerror("Error", logic_content)
                upload_button.config(state='normal')  # Re-enable the upload button
                return

            # Automatically read the files from the 'context' folder
            file_context = read_files_for_context()
            if "Error" in file_context:
                messagebox.showerror("Error", file_context)
                upload_button.config(state='normal')  # Re-enable the upload button
                return

            # Show the loading pop-up
            show_loading_popup()

            # Run the API call in a separate thread
            api_thread = threading.Thread(target=process_api_call, args=(xml_content, file_context, logic_content, AutoDocRef, clinic))
            api_thread.start()

        except Exception as e:
            messagebox.showerror("Error", f"Error processing the file: {str(e)}")
            upload_button.config(state='normal')  # Re-enable the upload button
            close_loading_popup()  # Ensure the loading pop-up is closed if an error occurs
    else:
        messagebox.showinfo("No XML File Selected", "Please select an XML file to process.")

# Set up the GUI window
root = ttk.Window(themename='darkly')
root.title("Halo Medical Code Automation")
root.geometry("800x900")

# Load and set the custom window icon (top-left)
root.iconphoto(False, tk.PhotoImage(file=icon_path))

# Function to change the theme
def change_theme(event):
    selected_theme = theme_var.get()
    root.style.theme_use(selected_theme)

# Load the logo image
try:
    logo_img = Image.open(logo_file_path)
    logo_img = logo_img.resize((200, 100), Image.Resampling.LANCZOS)
    logo_photo = ImageTk.PhotoImage(logo_img)

    # Create a label to display the logo using ttk.Label
    logo_label = ttk.Label(root, image=logo_photo)
    logo_label.pack(pady=10)
except Exception as e:
    messagebox.showerror("Error", f"Error loading logo: {str(e)}")

# Add a bold title below the logo using ttk.Label
title_label = ttk.Label(root, text="Code Automation Program", font=("Helvetica", 16, "bold"))
title_label.pack(pady=5)

# Create a frame for the info boxes
info_frame = ttk.Frame(root)
info_frame.pack(pady=10)

# Create labels and entries for AutoDocRef, Clinic, Date and Time
auto_doc_ref_label = ttk.Label(info_frame, text='AutoDocRef:')
auto_doc_ref_entry = ttk.Entry(info_frame, width=30)
clinic_label = ttk.Label(info_frame, text='Clinic:')
clinic_entry = ttk.Entry(info_frame, width=30)
datetime_label = ttk.Label(info_frame, text='Date and Time:')
datetime_entry = ttk.Entry(info_frame, width=30)

# Arrange them from left to right
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

# Create an upload button using ttk.Button
upload_button = ttk.Button(root, text="Upload XML File", command=upload_file)
upload_button.pack(pady=10)

# Create an exit button using ttk.Button
exit_button = ttk.Button(root, text="Exit", command=root.quit)
exit_button.pack(pady=10)

# Create a bottom frame to hold the theme selection dropdown
bottom_frame = ttk.Frame(root)
bottom_frame.pack(side='bottom', fill='x', padx=10, pady=10)

# Create a label and Combobox for theme selection
theme_label = ttk.Label(bottom_frame, text='Theme:')
theme_label.pack(side='left', padx=(0, 5))

theme_list = ['lumen', 'darkly', 'solar', 'cyborg', 'journal', 'superhero']
theme_var = tk.StringVar(value='darkly')
theme_combobox = ttk.Combobox(bottom_frame, textvariable=theme_var, values=theme_list, state='readonly')
theme_combobox.pack(side='left')

# Bind the selection change event
theme_combobox.bind('<<ComboboxSelected>>', change_theme)

# Start the GUI event loop
root.mainloop()
