import os
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, Toplevel
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from PIL import Image, ImageTk
import xml.etree.ElementTree as ET
import datetime
import threading

# ===========================
# InsolePricingLogic Class
# ===========================
class InsolePricingLogic:
    def __init__(self, pair=False, form_type=None, base=None, modifications=None, postings=None,
                 left_additions=None, right_additions=None,
                 extra_coverings=0, spenco=False, linings=0):
        self.pair = pair
        self.form_type = form_type
        self.base = base
        self.modifications = modifications or []
        # Postings are handled as a list to accommodate multiple postings
        self.postings = postings or []
        self.left_additions = left_additions or []
        self.right_additions = right_additions or []
        self.extra_coverings = extra_coverings
        self.spenco = spenco
        self.linings = linings
        self.codes = []

    def apply_pair_handling(self, code):
        """Applies pair handling logic by multiplying the code if applicable."""
        if self.pair:
            return f"{code} x2"
        return code

    def modelling_section(self):
        """Adds appropriate codes based on the selected base material."""
        base_code_mapping = {
            "Poron": "B40b",
            "Bontex": "B40a",
            "Leather": "B40a",
            "Carbon Fibre": "B54a",
            "Polypropylene": "B54b",
            "Shore65": "B54c"  # Assuming Shore65 corresponds to B54c
        }

        if self.base in base_code_mapping:
            code = base_code_mapping[self.base]
            self.codes.append(self.apply_pair_handling(code))
        else:
            print(f"No base code mapping found for base material: {self.base}")

    def modification_section(self):
        """Adds code BNS45 for each modification selected."""
        for modification in self.modifications:
            if modification:  # Ensure modification is not empty
                self.codes.append("BNS45")  # No pair handling for modifications

    def postings_section(self):
        """Adds posting codes based on the selections."""
        # Assuming each posting type corresponds to a single code addition
        for posting in self.postings:
            if posting:  # Ensure posting is not empty
                self.codes.append("B56")  # No pair handling for postings

    def additions_section(self):
        """Adds codes based on the selected additions."""
        additions_mapping = {
            "Valgus Pad": "B41", "Metatarsal Pad": "B41", "Metatarsal Bar": "B41",
            "Morton's Extension": "B56", "Reverse Morton's Extension": "B56",
            "Neurological Footplate": "D8a", "Balance Pad": "B41", "Heel Pad": "B41",
            "Cuboid Pad": "B41", "Kinetic Wedge": "B43", "Cobra Pad": "B41",
            "Neuroma Pad": "B41", "Sulcus Crest": "B41", "Poron Forefoot": "B56",
            "Arch Fill": "B41", "Heel Raise": "B43", "Rigid 1st Extension": "B20",
            "Recess": "BNS45", "Hole & Plug": "BNS45", "Partial Toe Block": "B50",
            "Full Toe Block": "B51"
        }

        # Combine left and right additions
        total_additions = self.left_additions + self.right_additions
        code_counts = {}
        for addition in total_additions:
            code = additions_mapping.get(addition)
            if code:
                code_counts[code] = code_counts.get(code, 0) + 1

        # Add codes based on their counts without pair handling
        for code, count in code_counts.items():
            if count > 1:
                self.codes.append(f"{code} x{count}")
            else:
                self.codes.append(code)

    def coverings_and_linings_section(self):
        """Adds codes based on the number of extra coverings and linings."""
        # Determine included covers based on form_type
        if self.form_type == "simple":
            included_cover = 1
        else:
            included_cover = 0

        # Total covers from XML
        total_coverings_from_xml = self.extra_coverings + (2 if self.spenco else 0) + self.linings

        # Actual total covers including the included cover (if any)
        actual_total_coverings = included_cover + total_coverings_from_xml

        if self.form_type == "simple":
            # Simple insoles include one cover by default
            if actual_total_coverings == 1:
                pass  # Nothing to add
            elif actual_total_coverings == 2:
                self.codes.append("B55a")
            elif actual_total_coverings == 3:
                self.codes.append("B55b")
            elif actual_total_coverings > 3:
                self.codes.append("B55c")
        else:
            # Other insoles do not include a default cover
            coverings_mapping = {
                1: "B55a",
                2: "B55b",
                3: "B55c"  # 3 or more coverings
            }

            if total_coverings_from_xml >= 1:
                code = coverings_mapping.get(total_coverings_from_xml, "B55c")  # Default to B55c if >=3
                self.codes.append(self.apply_pair_handling(code))

    def process_logic(self):
        """Processes all sections to generate the correct codes."""
        self.modelling_section()
        self.modification_section()
        self.postings_section()
        self.additions_section()
        self.coverings_and_linings_section()

        # Remove duplicate codes while preserving order
        seen = set()
        unique_codes = []
        for code in self.codes:
            if code not in seen:
                unique_codes.append(code)
                seen.add(code)
        self.codes = unique_codes

        return self.codes

# ===========================
# Main Application Script
# ===========================

# Get the path of the directory where this Python script is located
current_dir = os.path.dirname(os.path.abspath(__file__))

# Define the list of available themes
theme_list = ['lumen', 'darkly', 'solar', 'cyborg', 'journal', 'superhero', 'simplex', 'vapor']

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

# Function to change the theme
def change_theme(event):
    selected = theme_var.get()
    root.style.theme_use(selected)
    save_theme_setting(selected)

# Check if there is a results folder
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

# Function to process the XML and get tariff codes using local functions
def process_xml_and_get_codes(xml_content, form_type):
    # Parse the XML content and extract necessary data
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        messagebox.showerror("Error", f"Error parsing XML content: {str(e)}")
        return []

    # Initialize variables
    pair = False
    base_material = None
    modifications = []
    postings = []  # List to hold postings
    left_additions = []
    right_additions = []
    extra_coverings = 0
    spenco = False
    linings = 0

    # Extract Pair Information
    insole_side = root.find('.//InsoleSide')
    if insole_side is not None:
        pair = insole_side.findtext('Pair') == 'Yes'
        left = insole_side.findtext('Left') == 'Yes'
        right = insole_side.findtext('Right') == 'Yes'
        # If both left and right are selected, it's a pair
        if left and right:
            pair = True
        elif left or right:
            pair = False

    # Extract Base Material
    base = root.find('.//Base')
    if base is not None:
        if base.findtext('Poron') == 'Yes':
            base_material = 'Poron'
        elif base.findtext('Bontex') == 'Yes' or base.findtext('Leather') == 'Yes':
            base_material = 'Bontex'
        elif base.findtext('CarbonFibre') == 'Yes':
            base_material = 'Carbon Fibre'
        elif base.findtext('Polypropylene') == 'Yes':
            base_material = 'Polypropylene'
        elif base.findtext('Shore65') == 'Yes':
            base_material = 'Shore65'  # Adjust based on your logic

    # Extract Modifications
    modifications_list = [
        ("Cut Out and Additions", 'CutOutAndAdditions'),
        ("1st Met Head", 'MetHead1'),
        ("1st Met Ray", 'MetRay1'),
        ("5th Met Ray", 'MetRay5'),
        ("Navicular Sweet Spot", 'NavicularSweetSpot'),
        ("Fascial Accommodation", 'FascialAccommodation'),
        ("Heel Flange Medial", 'HeelFlangeMedial'),
        ("Heel Flange Lateral", 'HeelFlangeLateral'),
    ]

    # Left Foot Modifications
    left_modifications = root.find('.//Left/Modification')
    if left_modifications is not None:
        for name, xml_tag in modifications_list:
            if left_modifications.findtext(xml_tag) == 'Yes':
                modifications.append(name)

    # Right Foot Modifications
    right_modifications = root.find('.//Right/Modification')
    if right_modifications is not None:
        for name, xml_tag in modifications_list:
            if right_modifications.findtext(xml_tag) == 'Yes':
                modifications.append(name)

    # Extract Postings
    postings_tags = {
        "Rearfoot": ['MedialRearfootPosting', 'LateralRearfootPosting'],
        "Forefoot": ['MedialForefootPosting', 'LateralForefootPosting']
    }

    # Left Foot Postings
    if left_modifications is not None:
        for posting_type, tags in postings_tags.items():
            for tag in tags:
                if left_modifications.findtext(tag) == 'Yes':
                    postings.append(posting_type)

    # Right Foot Postings
    if right_modifications is not None:
        for posting_type, tags in postings_tags.items():
            for tag in tags:
                if right_modifications.findtext(tag) == 'Yes':
                    postings.append(posting_type)

    # Extract Additions
    additions_mapping_values = set([
        'Valgus Pad', 'Metatarsal Pad', 'Metatarsal Bar',
        "Morton's Extension", "Reverse Morton's Extension",
        'Neurological Footplate', 'Balance Pad', 'Heel Pad',
        'Cuboid Pad', 'Kinetic Wedge', 'Cobra Pad',
        'Neuroma Pad', 'Sulcus Crest', 'Poron Forefoot',
        'Arch Fill', 'Heel Raise', 'Rigid 1st Extension',
        'Recess', 'Hole & Plug', 'Partial Toe Block',
        'Full Toe Block'
    ])

    # Left Foot Additions
    left_additions_section = root.find('.//Left/Additions')
    if left_additions_section is not None:
        for i in range(1, 5):
            addition = left_additions_section.findtext(f'Addition{i}')
            if addition and addition.strip() in additions_mapping_values:
                left_additions.append(addition.strip())

    # Right Foot Additions
    right_additions_section = root.find('.//Right/Additions')
    if right_additions_section is not None:
        for i in range(1, 5):
            addition = right_additions_section.findtext(f'Addition{i}')
            if addition and addition.strip() in additions_mapping_values:
                right_additions.append(addition.strip())

    # Extract Coverings and Linings
    # As per your logic, set defaults or extract from XML if available
    # Here, setting defaults for demonstration
    extra_coverings = 0  # Adjust based on your actual logic or extract from XML
    linings = 0          # Adjust based on your actual logic or extract from XML
    spenco = False       # Adjust based on your actual logic or extract from XML

    # Check for extra coverings, spenco, and linings in XML if applicable
    # Example extraction (modify according to your XML structure)
    extra_coverings_element = root.find('.//Coverings/ExtraCoverings')
    if extra_coverings_element is not None and extra_coverings_element.text.isdigit():
        extra_coverings = int(extra_coverings_element.text)

    spenco_element = root.find('.//Coverings/Spenco')
    if spenco_element is not None and spenco_element.text.lower() == 'yes':
        spenco = True

    linings_element = root.find('.//Coverings/Linings')
    if linings_element is not None and linings_element.text.isdigit():
        linings = int(linings_element.text)

    # Create an instance of InsolePricingLogic with the extracted data
    logic = InsolePricingLogic(
        pair=pair,
        form_type=form_type,
        base=base_material,
        modifications=modifications,
        postings=postings,
        left_additions=left_additions,
        right_additions=right_additions,
        extra_coverings=extra_coverings,
        spenco=spenco,
        linings=linings
    )

    # Process the logic to get the codes
    result_codes = logic.process_logic()
    return result_codes

# Function to write tariff codes, auto doc reference, and clinic to the log file
def write_to_log_file(tariff_codes, auto_doc_ref, clinic):
    try:
        # Ensure the result_logs folder exists
        result_logs_folder = os.path.join(current_dir, 'result_logs')
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

# Function to show the loading pop-up with moving dots animation on a new line
def show_loading_popup():
    global loading_popup, loading_label, dot_index
    loading_popup = Toplevel(root)
    loading_popup.title("Loading...")

    # Set icon on loading pop-up
    icon_image_loading = None
    try:
        icon_image_loading = ImageTk.PhotoImage(Image.open(icon_path).resize((32, 32), Image.Resampling.LANCZOS))
        loading_popup.iconphoto(False, icon_image_loading)
    except Exception as e:
        messagebox.showerror("Error", f"Error loading icon: {str(e)}")

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

    # Add a label to display the loading message with dots on a new line
    loading_label = ttk.Label(loading_popup, text="Please wait, processing\n", font=("Calibri", 12, "bold"))
    loading_label.pack(expand=True, pady=20)

    dot_index = 0  # Initialize the dot counter
    animate_dots()  # Start the animation

    # Disable the main window while loading
    root.attributes('-disabled', True)

# Function to animate the moving dots
def animate_dots():
    global dot_index
    dots = ['.', '..', '...', '']  # The sequence of dots
    # Update the label text
    loading_label.config(text=f"Please wait, processing\n{dots[dot_index]}")
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
    result_text.insert(tk.END, '\n'.join(tariff_codes), 'center')

    result_text.config(state=tk.DISABLED)  # Disable editing again

# Function to process the XML and get tariff codes using local functions
def process_xml_and_get_codes_interface(xml_content, form_type):
    # This function wraps the process_xml_and_get_codes to handle exceptions
    try:
        return process_xml_and_get_codes(xml_content, form_type)
    except Exception as e:
        messagebox.showerror("Error", f"Error processing XML: {str(e)}")
        return []

# Function to process the XML and get tariff codes
def process_api_call(xml_content, form_type, AutoDocRef, clinic):
    try:
        # Get the tariff codes by processing the XML content using local functions
        tariff_codes = process_xml_and_get_codes_interface(xml_content, form_type)

        # Debug print to check the content of tariff_codes
        print(f"Tariff codes received: {tariff_codes}")

        # Get the current date and time
        current_datetime = datetime.datetime.now()
        formatted_datetime = current_datetime.strftime('%Y-%m-%d %H:%M:%S')

        # Update the GUI with the results (must be done in the main thread)
        root.after(0, display_results, formatted_datetime, AutoDocRef, clinic, tariff_codes)

        # Write the tariff codes, auto doc reference, and clinic to the log file
        write_to_log_file('\n'.join(tariff_codes), AutoDocRef, clinic)

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

            # Show the loading pop-up with animation
            show_loading_popup()

            # Run the processing in a separate thread
            api_thread = threading.Thread(target=process_api_call, args=(xml_content, form_type, AutoDocRef, clinic))
            api_thread.start()

        except Exception as e:
            messagebox.showerror("Error", f"Error processing the file: {str(e)}")
            upload_button.config(state='normal')  # Re-enable the upload button
            close_loading_popup()  # Ensure the loading pop-up is closed if an error occurs
    else:
        messagebox.showinfo("No XML File Selected", "Please select an XML file to process.")

# ===========================
# GUI Setup
# ===========================

# Set up the GUI window with the selected theme
root = ttk.Window(themename=selected_theme)
root.title("Halo Medical Code Automation")

# Load and set the custom window icon (top-left)
icon_image = None
try:
    icon_image = ImageTk.PhotoImage(Image.open(icon_path).resize((32, 32), Image.Resampling.LANCZOS))
    root.iconphoto(False, icon_image)
except Exception as e:
    messagebox.showerror("Error", f"Error loading icon: {str(e)}")

# Load the logo image
try:
    logo_img = Image.open(logo_file_path)
    logo_img = logo_img.resize((200, 100), Image.Resampling.LANCZOS)
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
label_font = ('Calibri', 11)

# Create a frame for the info boxes
info_frame = ttk.Frame(root)
info_frame.pack(pady=10)

# Create labels and entries for AutoDocRef, Clinic, Date and Time
auto_doc_ref_label = ttk.Label(info_frame, text='AutoDocRef:', font=label_font)
auto_doc_ref_entry = ttk.Entry(info_frame, width=30)
clinic_label = ttk.Label(info_frame, text='Clinic:', font=label_font)
clinic_entry = ttk.Entry(info_frame, width=30)
datetime_label = ttk.Label(info_frame, text='Date and Time:', font=label_font)
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

# Set the theme variable to the selected theme
theme_var = tk.StringVar(value=selected_theme)
theme_combobox = ttk.Combobox(bottom_frame, textvariable=theme_var, values=theme_list, state='readonly')
theme_combobox.pack(side='left')

# Bind the selection change event
theme_combobox.bind('<<ComboboxSelected>>', change_theme)

# ===========================
# Start the GUI Event Loop
# ===========================
root.mainloop()
