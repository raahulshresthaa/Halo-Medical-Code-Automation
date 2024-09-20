import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import openai
import json
import os
from PIL import Image, ImageTk  # To handle image loading

# Get your OpenAI API key from environment variable
#openai.api_key = os.getenv("OPENAI_API_KEY") #this is weird it would ivlove making a session - hamish
openai.api_key = ""

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

# Function to extract form type from JSON content
def extract_form_type(json_content):
    modelling = json_content.get('Modelling', {})
    type_dict = modelling.get('Type', {})
    # Iterate over the type_dict to find which type is marked as 'Yes'
    selected_types = [key for key, value in type_dict.items() if value.strip().lower() == 'yes']
    if not selected_types:
        return None  # Or set a default form type
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
        return selected_types[0].lower()

# Function to process JSON file and get tariff codes from the assistant using the logic from the text file
def get_tariff_codes_from_json(json_content, file_context, logic_content):
    try:
        # Convert JSON data to a string for sending to OpenAI
        json_string = json.dumps(json_content, indent=4)
        
        # Send the JSON content, logic, and file context to the assistant
        response = openai.ChatCompletion.create(
            model="gpt-4o",  # Adjust this if you're using a different model
            messages=[
                {"role": "system", "content": f"Use the following logic to generate tariff codes:\n\n{logic_content}\n\nOnly output the calculated tariff codes."},
                {"role": "user", "content": f"Here is the JSON content to process:\n{json_string}\n\nRelevant file information:\n{file_context}"}
            ],
            max_tokens=1000  # Adjust as necessary
        )
        
        # Extract the assistant's response (tariff codes)
        assistant_response = response['choices'][0]['message']['content']
        return assistant_response
    except Exception as e:
        return f"Error: {str(e)}"

# Function to handle file upload and send JSON content and logic to the API
def upload_file():
    # Open a file dialog for selecting JSON files
    json_file_path = filedialog.askopenfilename(title="Select the JSON File", filetypes=[("JSON Files", "*.json")])
    
    if json_file_path:
        try:
            # Read the content of the selected JSON file
            with open(json_file_path, 'r') as file:
                json_content = json.load(file)  # Load JSON content from the file

            # Extract the form type using the new function
            form_type = extract_form_type(json_content)
            if not form_type:
                messagebox.showerror("Error", "No form type selected in the JSON file.")
                return

            # Sanitize form_type to prevent security issues
            form_type = ''.join(char for char in form_type if char.isalnum() or char in ('_', '-'))

            # Construct the logic file name and path based on the form type
            # Option 1: If logic files are named as '{form_type}_logic.txt'
            # logic_file_name = f"{form_type}_logic.txt"

            # Option 2: If logic files have specific names, use a mapping
            logic_file_mapping = {
                'tci': 'tci_logic.txt',
                'simple': 'simple_insole_logic.txt',
                'crade': 'crade_logic.txt'  # Add other mappings as needed
            }

            logic_file_name = logic_file_mapping.get(form_type)
            if not logic_file_name:
                messagebox.showerror("Error", f"No logic file mapping found for form type '{form_type}'.")
                return

            logic_file_path = os.path.join(current_dir, logic_file_name)

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

            # Get the tariff codes by sending the JSON, logic, and file context to OpenAI
            tariff_codes = get_tariff_codes_from_json(json_content, file_context, logic_content)

            # Display the result
            result_text.config(state=tk.NORMAL)  # Enable editing temporarily
            result_text.delete(1.0, tk.END)  # Clear previous content
            result_text.insert(tk.END, f"Tariff Codes:\n{tariff_codes}")  # Insert new content
            result_text.config(state=tk.DISABLED)  # Disable editing again

        except Exception as e:
            messagebox.showerror("Error", f"Error processing the file: {str(e)}")
    else:
        messagebox.showinfo("No JSON File Selected", "Please select a JSON file to process.")




# Set up the GUI window
root = tk.Tk()
root.title("Halo Medical Code Automation")
root.geometry("800x800")

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
upload_button = tk.Button(root, text="Upload JSON File", command=upload_file, 
                          bg="green", fg="white", padx=20, pady=10)
upload_button.pack(pady=10)

# Create an exit button (red with white text)
exit_button = tk.Button(root, text="Exit", command=root.quit,
                        bg="red", fg="white", padx=20, pady=10)
exit_button.pack(pady=10)

# Start the GUI event loop
root.mainloop()
