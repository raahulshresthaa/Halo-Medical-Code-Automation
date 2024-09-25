# main.py

import os
import threading
import datetime
import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk
from PIL import Image, ImageTk

import simple_logic  # Ensure this is all lowercase
import tci_logic     # Import the tci_logic module
import gui
import xml_utils     # Import the xml_utils module

# Initialize paths
current_dir = os.path.dirname(os.path.abspath(__file__))
icon_path = os.path.join(current_dir, 'halo_simple_logo.png')
logo_file_path = os.path.join(current_dir, 'HALO(TM)_Logo.png')

# Ensure result logs folder exists
gui.ensure_result_logs_folder_exists()

# Define themes
theme_list = ['lumen', 'darkly', 'solar', 'cyborg', 'journal', 'superhero', 'simplex', 'vapor']
selected_theme = gui.load_theme_setting(theme_list)

# Set up the GUI window with the selected theme
root = ttk.Window(themename=selected_theme)
root.title("Halo Medical Code Automation")

# Load and set the custom window icon
try:
    icon_image = ImageTk.PhotoImage(
        Image.open(icon_path).resize((32, 32), Image.LANCZOS))
    root.iconphoto(False, icon_image)
except Exception as e:
    messagebox.showerror("Error", f"Error loading icon: {str(e)}")

# Load the logo image
try:
    logo_img = Image.open(logo_file_path)
    logo_img = logo_img.resize((200, 100), Image.LANCZOS)
    logo_photo = ImageTk.PhotoImage(logo_img)
    root.logo_photo = logo_photo

    logo_label = ttk.Label(root, image=logo_photo)
    logo_label.pack(pady=10)
except Exception as e:
    messagebox.showerror("Error", f"Error loading logo: {str(e)}")

title_label = ttk.Label(root, text="Code Automation Program", font=("Calibri", 16, "bold"))
title_label.pack(pady=5)

label_font = ('Calibri', 11)

info_frame = ttk.Frame(root)
info_frame.pack(pady=10)

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

result_frame = ttk.Frame(root)
result_frame.pack(pady=10, anchor='center')

result_text = tk.Text(result_frame, wrap='word', height=25, width=80)
result_text.grid(row=0, column=0)

result_scrollbar = ttk.Scrollbar(result_frame, orient='vertical', command=result_text.yview)
result_scrollbar.grid(row=0, column=1, sticky='ns')

result_text['yscrollcommand'] = result_scrollbar.set
result_text.config(state='disabled')

def change_theme(event):
    gui.change_theme(event, root, theme_var)

def write_to_log_file(tariff_codes, auto_doc_ref, clinic):
    try:
        result_logs_folder = os.path.join(current_dir, 'result_logs')
        if not os.path.exists(result_logs_folder):
            os.makedirs(result_logs_folder)

        current_datetime = datetime.datetime.now()
        formatted_date = current_datetime.strftime('%d_%m_%y')

        log_file_name = f"log_{formatted_date}.txt"
        log_file_path = os.path.join(result_logs_folder, log_file_name)

        with open(log_file_path, 'a', encoding='utf-8') as log_file:
            formatted_datetime = current_datetime.strftime('%Y-%m-%d %H:%M:%S')

            log_file.write(f"Date and Time: {formatted_datetime}\n")
            log_file.write(f"Auto Doc Reference: {auto_doc_ref}\n")
            log_file.write(f"Clinic: {clinic}\n")
            log_file.write(f"Tariff Codes:\n{tariff_codes}\n")
            log_file.write("-" * 50 + "\n")
        print(f"Successfully wrote to log file at {log_file_path}")
    except Exception as e:
        messagebox.showerror("Error", f"Error writing to log file: {str(e)}")

def process_api_call(xml_content, form_type, AutoDocRef, clinic):
    try:
        # Based on form_type, call the appropriate module
        if form_type == 'simple':
            tariff_codes = simple_logic.process_xml_and_get_codes(xml_content, form_type)
        elif form_type == 'tci' or 'handmould':
            tariff_codes = tci_logic.process_xml_and_get_codes(xml_content, form_type)
        else:
            messagebox.showerror("Error", f"Unsupported form type: {form_type}")
            root.after(0, gui.close_loading_popup, root)
            root.after(0, lambda: upload_button.config(state='normal'))
            return

        print(f"Tariff codes received: {tariff_codes}")

        current_datetime = datetime.datetime.now()
        formatted_datetime = current_datetime.strftime('%Y-%m-%d %H:%M:%S')

        root.after(0, gui.display_results, formatted_datetime, AutoDocRef, clinic, tariff_codes,
                   auto_doc_ref_entry, datetime_entry, clinic_entry, result_text)

        # Write the tariff codes, auto doc reference, and clinic to the log file
        write_to_log_file('\n'.join(tariff_codes), AutoDocRef, clinic)

    except Exception as e:
        root.after(0, messagebox.showerror, "Error", f"Error processing the file: {str(e)}")
    finally:
        root.after(0, gui.close_loading_popup, root)
        root.after(0, lambda: upload_button.config(state='normal'))

def upload_file():
    xml_file_path = filedialog.askopenfilename(title="Select the XML File", filetypes=[("XML Files", "*.xml")])

    if xml_file_path:
        upload_button.config(state='disabled')

        try:
            # Use functions from xml_utils
            xml_content = xml_utils.read_xml_file(xml_file_path)
            if xml_content is None:
                upload_button.config(state='normal')
                return

            form_type = xml_utils.extract_form_type_from_xml_string(xml_content)
            print(f"Extracted form type: {form_type}")
            if not form_type:
                messagebox.showerror("Error", "No form type selected in the XML file.")
                upload_button.config(state='normal')
                return

            AutoDocRef = xml_utils.extract_auto_doc_reference_from_xml_string(xml_content)
            print(f"Extracted auto doc reference: {AutoDocRef}")
            if not AutoDocRef:
                AutoDocRef = "N/A"

            clinic = xml_utils.extract_clinic_from_xml_string(xml_content)
            print(f"Extracted clinic: {clinic}")
            if not clinic:
                clinic = "N/A"

            gui.show_loading_popup(root, icon_path)

            api_thread = threading.Thread(target=process_api_call, args=(xml_content, form_type, AutoDocRef, clinic))
            api_thread.start()

        except Exception as e:
            messagebox.showerror("Error", f"Error processing the file: {str(e)}")
            upload_button.config(state='normal')
            gui.close_loading_popup(root)
    else:
        messagebox.showinfo("No XML File Selected", "Please select an XML file to process.")

upload_button = ttk.Button(root, text="Upload XML File", command=upload_file)
upload_button.pack(pady=10)

exit_button = ttk.Button(root, text="Exit", command=root.quit)
exit_button.pack(pady=10)

bottom_frame = ttk.Frame(root)
bottom_frame.pack(side='bottom', fill='x', padx=10, pady=10)

theme_label = ttk.Label(bottom_frame, text='Theme:')
theme_label.pack(side='left', padx=(0, 5))

theme_var = tk.StringVar(value=selected_theme)
theme_combobox = ttk.Combobox(bottom_frame, textvariable=theme_var, values=theme_list, state='readonly')
theme_combobox.pack(side='left')
theme_combobox.bind('<<ComboboxSelected>>', change_theme)

root.mainloop()
