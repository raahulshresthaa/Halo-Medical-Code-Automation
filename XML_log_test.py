# openai.api_key = "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"
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import openai
import os
import xml.etree.ElementTree as ET
from PIL import Image, ImageTk  # To handle image loading

# Get your OpenAI API key from environment variable
#openai.api_key = os.getenv("OPENAI_API_KEY")
openai.api_key = "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"

if not openai.api_key:
    messagebox.showerror("Error", "OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")
    exit()

# Get the path of the directory where this Python script is located
current_dir = os.path.dirname(os.path.abspath(__file__))

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
            'Cradle': 'cradle'
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
            temperature=0.1  # Add the temperature value here (adjust as needed)

        )

        # Extract the assistant's response (tariff codes)
        assistant_response = response['choices'][0]['message']['content']
        return assistant_response
    except Exception as e:
        return f"Error: {str(e)}"

# Function to write tariff codes and auto doc reference to the log file
def write_to_log_file(tariff_codes, auto_doc_ref):
    try:
        log_file_path = os.path.join(current_dir, 'log.txt')
        with open(log_file_path, 'a', encoding='utf-8') as log_file:
            log_file.write(f"Auto Doc Reference: {auto_doc_ref}\n")
            log_file.write(f"Tariff Codes:\n{tariff_codes}\n")
            log_file.write("-" * 50 + "\n")  # Separator between entries
        print(f"Successfully wrote to log file at {log_file_path}")
    except Exception as e:
        messagebox.showerror("Error", f"Error writing to log file: {str(e)}")

# Function to handle file upload and send XML content and logic to the API
def upload_file():
    # Open a file dialog for selecting XML files
    xml_file_path = filedialog.askopenfilename(title="Select the XML File", filetypes=[("XML Files", "*.xml")])
    
    if xml_file_path:
        try:
            # Read the XML file content as a string
            xml_content = read_xml_file(xml_file_path)
            if xml_content is None:
                return

            # Extract the form type from the XML string
            form_type = extract_form_type_from_xml_string(xml_content)
            print(f"Extracted form type: {form_type}")
            if not form_type:
                messagebox.showerror("Error", "No form type selected in the XML file.")
                return

            # Extract the auto doc reference from the XML string
            AutoDocRef = extract_auto_doc_reference_from_xml_string(xml_content)
            print(f"Extracted auto doc reference: {AutoDocRef}")
            if not AutoDocRef:
                AutoDocRef = "N/A"  # Default value if not found

            # Sanitize form_type to prevent security issues
            form_type = ''.join(char for char in form_type if char.isalnum() or char in ('_', '-')).lower()
            print(f"Sanitized form type: {form_type}")

            # Construct the logic file name and path based on the form type
            logic_file_mapping = {
                'tci': 'tci_logic.txt',
                'simple': 'simple_insole_logic.txt',
                'cradle': 'cradle_logic.txt'  # Add other mappings as needed
            }

            logic_file_name = logic_file_mapping.get(form_type)
            print(f"Logic file name: {logic_file_name}")
            if not logic_file_name:
                messagebox.showerror("Error", f"No logic file mapping found for form type '{form_type}'.")
                return

            #logic_file_path = os.path.join(current_dir, logic_file_name)
            logic_folder_path = os.path.join(current_dir, 'logic_folder')
            logic_file_path = os.path.join(logic_folder_path, logic_file_name)
            print(f"Logic file path: {logic_file_path}")

            # Read the logic file
            logic_content = read_logic_file(logic_file_path)
            if "Error" in logic_content:
                messagebox.showerror("Error", logic_content)
                return

            # Automatically read the files from the 'context' folder
            file_context = read_files_for_context()
            if "Error" in file_context:
                messagebox.showerror("Error", file_context)
                return

            # Get the tariff codes by sending the XML string, logic, and file context to OpenAI
            tariff_codes = get_tariff_codes_from_xml(xml_content, file_context, logic_content)

            # Display the result
            result_text.config(state=tk.NORMAL)  # Enable editing temporarily
            result_text.delete(1.0, tk.END)  # Clear previous content
            result_text.insert(tk.END, f"Auto Doc Ref:\n{AutoDocRef}\n\n") 
            result_text.insert(tk.END, f"Tariff Codes:\n{tariff_codes}")  # Insert new content
            result_text.config(state=tk.DISABLED)  # Disable editing again

            # Write the tariff codes and auto doc reference to the log file
            write_to_log_file(tariff_codes, AutoDocRef)

        except Exception as e:
            messagebox.showerror("Error", f"Error processing the file: {str(e)}")
    else:
        messagebox.showinfo("No XML File Selected", "Please select an XML file to process.")

# Set up the GUI window
root = tk.Tk()
root.title("Halo Medical Code Automation")
root.geometry("1200x800")

# Load the logo image
try:
    logo_img = Image.open(logo_file_path)
    logo_img = logo_img.resize((200, 80), Image.Resampling.LANCZOS)  # Updated resizing method
    logo_photo = ImageTk.PhotoImage(logo_img)

    # Create a label to display the logo
    logo_label = tk.Label(root, image=logo_photo)
    logo_label.pack(pady=10)
except Exception as e:
    messagebox.showerror("Error", f"Error loading logo: {str(e)}")

# Add a bold title below the logo
title_label = tk.Label(root, text="Code Automation Program", font=("Helvetica", 16, "bold"))
title_label.pack(pady=5)

# Create a frame for the result text and scrollbar
frame = tk.Frame(root)
frame.pack(fill=tk.BOTH, expand=True, pady=10, padx=10)

# Create a scrollable canvas
canvas = tk.Canvas(frame)
canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

# Create a vertical scrollbar
scrollbar = tk.Scrollbar(frame, orient=tk.VERTICAL, command=canvas.yview)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

# Configure the canvas to work with the scrollbar
canvas.configure(yscrollcommand=scrollbar.set)
canvas.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

# Create another frame inside the canvas to hold the content
content_frame = tk.Frame(canvas)
canvas.create_window((0, 0), window=content_frame, anchor="nw")

# Create a text widget inside the content_frame to display the results
result_text = tk.Text(content_frame, wrap=tk.WORD, height=50, width=950)
result_text.pack(fill=tk.BOTH, expand=True)
result_text.config(state=tk.DISABLED)  # Make it read-only

# Create an upload button (green with white text)
upload_button = tk.Button(root, text="Upload XML File", command=upload_file, 
                          bg="green", fg="white", padx=20, pady=10)
upload_button.pack(pady=10)

# Create an exit button (red with white text)
exit_button = tk.Button(root, text="Exit", command=root.quit,
                        bg="red", fg="white", padx=20, pady=10)
exit_button.pack(pady=10)

# Start the GUI event loop
root.mainloop()
