import tkinter as tk
from tkinter import filedialog, messagebox
import openai
import json
import os
from PIL import Image, ImageTk  # To handle image loading

# Set your OpenAI API key
openai.api_key = "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"

# Get the path of the directory where this Python script is located
current_dir = os.path.dirname(os.path.abspath(__file__))

# Define the logic text file name 
logic_file_name = "tariff_code_logic.txt"
logic_file_path = os.path.join(current_dir, logic_file_name)


# Define the path for the logo file
logo_file_path = os.path.join(current_dir, 'HALO(TM)_Logo.png')

# Define the path to the 'context' folder where the additional context files are stored
context_folder_path = os.path.join(current_dir, 'context')

# Function to read the logic file automatically from the same folder
def read_logic_file():
    try:
        with open(logic_file_path, 'r', encoding='utf-8') as logic_file:
            logic_content = logic_file.read()
        return logic_content
    except Exception as e:
        return f"Error reading the logic file: {str(e)}"

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
            
            # Only process text and PDF files 
            if file_name.endswith(".txt") or file_name.endswith(".pdf"):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        file_contents.append(f"File: {file_name}\n{content}")
                except Exception as e:
                    file_contents.append(f"Error reading {file_name}: {str(e)}")
        
        return "\n\n".join(file_contents) if file_contents else "No valid files found in the 'context' folder."
    
    except Exception as e:
        return f"Error reading context files: {str(e)}"

# Function to process JSON file and get tariff codes from the assistant using the logic from the text file
def get_tariff_codes_from_json(json_content, file_context, logic_content):
    try:
        # Convert JSON data to a string for sending to OpenAI
        json_string = json.dumps(json_content, indent=4)
        
        # Send the JSON content, logic, and file context to the assistant
        response = openai.ChatCompletion.create(
            model="gpt-4o",  # Adjust this if you're using a different model
            messages=[
                {"role": "system", "content": f"Use the following logic to generate tariff codes:\n\n{logic_content}. Only print out the caluculate traiff codes"},
                {"role": "user", "content": f"Here is the JSON content I need to process: {json_string}\n\n"
                                            f"Relevant file information: {file_context}"}
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
    # Automatically read the logic file from the same folder as this script
    logic_content = read_logic_file()
    
    if "Error" in logic_content:
        messagebox.showerror("Error", logic_content)
        return

    # Automatically read the files from the 'context' folder
    file_context = read_files_for_context()
    
    if "Error" in file_context:
        messagebox.showerror("Error", file_context)
        return
    
    # Open a file dialog for selecting JSON files
    json_file_path = filedialog.askopenfilename(title="Select the JSON File", filetypes=[("JSON Files", "*.json")])
    
    if json_file_path:
        try:
            # Read the content of the selected JSON file
            with open(json_file_path, 'r') as file:
                json_content = json.load(file)  # Load JSON content from the file
            
            # Get the tariff codes by sending the JSON, logic, and file context to OpenAI
            tariff_codes = get_tariff_codes_from_json(json_content, file_context, logic_content)
            
            # Clear the previous content and insert the new content into the result_text widget
            result_text.config(state=tk.NORMAL)  # Enable editing temporarily
            result_text.delete(1.0, tk.END)  # Clear previous content
            result_text.insert(tk.END, f"Tariff Codes:\n{tariff_codes}")  # Insert new content
            result_text.config(state=tk.DISABLED)  # Disable editing again
        
        except Exception as e:
            messagebox.showerror("Error", f"Error reading file: {str(e)}")
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
