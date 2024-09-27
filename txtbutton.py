# txtbutton.py

import os
import threading
import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import openai

class TxtButtonHandler:
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

        # Reference to the upload TXT button (will be set later)
        self.upload_txt_button = None

    def set_upload_txt_button(self, button):
        self.upload_txt_button = button

    # Function to read the logic file
    def read_logic_file(self, logic_file_path):
        try:
            with open(logic_file_path, 'r', encoding='utf-8') as logic_file:
                logic_content = logic_file.read()
            return logic_content
        except Exception as e:
            return f"Error reading the logic file '{logic_file_path}': {str(e)}"

    # Function to automatically read all files in the 'context' folder
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

    def get_tariff_codes_from_txt(self, txt_content, file_context, logic_content):
        try:
            # Send the TXT content, logic, and file context to the assistant
            response = openai.ChatCompletion.create(
                model="gpt-4o",  # Use the appropriate model
                messages=[
                    {"role": "system", "content": f"Use the following logic to generate tariff codes:\n\n{logic_content}\n\nOnly output the calculated tariff codes."},
                    {"role": "user", "content": f"Here is the content to process:\n{txt_content}\n\nRelevant file information:\n{file_context}"}
                ],
                max_tokens=1000,  # Adjust as necessary
                temperature=0.1  # Adjust as needed
            )

            # Extract the assistant's response (tariff codes)
            assistant_response = response['choices'][0]['message']['content']
            return assistant_response
        except Exception as e:
            return f"Error: {str(e)}"

    def process_api_call_txt(self, txt_content, file_context, logic_content, AutoDocRef, clinic):
        try:
            # Get the tariff codes by sending the TXT content, logic, and file context to OpenAI
            tariff_codes = self.get_tariff_codes_from_txt(txt_content, file_context, logic_content)

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
            self.root.after(0, lambda: self.upload_txt_button.config(state='normal'))

    # Function to write tariff codes, auto doc reference, and clinic to the log file
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

    def parse_txt_content(self, txt_content):
        data = {}
        lines = txt_content.strip().split('\n')
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                data[key] = value
        return data

    def upload_txt_file(self):
        # Open a file dialog for selecting TXT files
        txt_file_path = filedialog.askopenfilename(title="Select the TXT File", filetypes=[("Text Files", "*.txt")])

        if txt_file_path:
            # Disable the upload button to prevent multiple clicks
            self.upload_txt_button.config(state='disabled')

            try:
                # Read the TXT file content
                with open(txt_file_path, 'r', encoding='utf-8') as file:
                    txt_content = file.read()
                if not txt_content:
                    messagebox.showerror("Error", "The selected TXT file is empty.")
                    self.upload_txt_button.config(state='normal')  # Re-enable the upload button
                    return

                # Parse the TXT content to extract needed fields
                data = self.parse_txt_content(txt_content)
                print(f"Parsed data: {data}")

                # Extract form_type from data
                # Assuming form_type is indicated by keys like 'tci test' or 'simple test' etc.
                form_type = None
                for key in data:
                    if key == 'tci test' and data[key].lower() == 'selected':
                        form_type = 'tci'
                        break
                    elif key == 'tci' and data[key].lower() == 'selected':
                        form_type = 'tci'
                        break
                    elif key == 'simple test' and data[key].lower() == 'selected':
                        form_type = 'simple'
                        break
                    elif key == 'simple' and data[key].lower() == 'selected':
                        form_type = 'simple'                    
                        break
                    elif key == 'hand mould' and data[key].lower() == 'selected':# note the spelling error
                        form_type = 'handmold'  
                        break
                    # Add other form types as needed
                if not form_type:
                    messagebox.showerror("Error", "No form type found in the TXT file.")
                    self.upload_txt_button.config(state='normal')  # Re-enable the upload button
                    return

                # Extract AutoDocRef and Clinic from data
                AutoDocRef = data.get('autodocref', 'N/A')
                clinic = data.get('clinic', 'N/A')

                # Sanitize form_type to prevent security issues
                form_type = ''.join(char for char in form_type if char.isalnum() or char in ('_', '-')).lower()
                print(f"Form type: {form_type}")
                print(f"AutoDocRef: {AutoDocRef}")
                print(f"Clinic: {clinic}")

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
                    self.upload_txt_button.config(state='normal')  # Re-enable the upload button
                    return

                logic_folder_path = os.path.join(self.current_dir, 'logic_folder')
                logic_file_path = os.path.join(logic_folder_path, logic_file_name)
                print(f"Logic file path: {logic_file_path}")

                # Read the logic file
                logic_content = self.read_logic_file(logic_file_path)
                if "Error" in logic_content:
                    messagebox.showerror("Error", logic_content)
                    self.upload_txt_button.config(state='normal')  # Re-enable the upload button
                    return

                # Automatically read the files from the 'context' folder
                file_context = self.read_files_for_context()
                if "Error" in file_context:
                    messagebox.showerror("Error", file_context)
                    self.upload_txt_button.config(state='normal')  # Re-enable the upload button
                    return

                # Show the loading pop-up with animation
                self.show_loading_popup()

                # Run the API call in a separate thread
                api_thread = threading.Thread(target=self.process_api_call_txt, args=(txt_content, file_context, logic_content, AutoDocRef, clinic))
                api_thread.start()

            except Exception as e:
                messagebox.showerror("Error", f"Error processing the file: {str(e)}")
                self.upload_txt_button.config(state='normal')  # Re-enable the upload button
                self.close_loading_popup()  # Ensure the loading pop-up is closed if an error occurs
        else:
            messagebox.showinfo("No TXT File Selected", "Please select a TXT file to process.")
