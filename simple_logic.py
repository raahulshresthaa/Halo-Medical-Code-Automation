# simple_logic.py
import datetime
import os
import xml.etree.ElementTree as ET
from tkinter import messagebox, simpledialog

# Get the path of the directory where this Python script is located
current_dir = os.path.dirname(os.path.abspath(__file__))


class InsolePricingLogic:
    def __init__(self, pair=False, form_type=None, base=None, modifications=None, postings=None,
                 left_additions=None, right_additions=None,
                 covers_from_xml=0, linings_from_xml=0):
        self.pair = pair
        self.form_type = form_type
        self.base = base
        self.modifications = modifications or []
        self.postings = postings or []
        self.left_additions = left_additions or []
        self.right_additions = right_additions or []
        self.covers_from_xml = covers_from_xml
        self.linings_from_xml = linings_from_xml
        self.codes = []

    def apply_pair_handling(self, code):
        """Applies pair handling logic by adding ' x2' if applicable."""
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
            "Shore65": "B54c"
        }

        if self.base in base_code_mapping:
            code = base_code_mapping[self.base]
            self.codes.append(self.apply_pair_handling(code))
        else:
            print(f"No base code mapping found for base material: {self.base}")

    def modification_section(self):
        """Adds code BNS45 for each modification selected."""
        for modification in self.modifications:
            if modification:
                self.codes.append("BNS45")

    def postings_section(self):
        """Adds posting codes based on the selections."""
        for posting in self.postings:
            if posting:
                self.codes.append("B56")

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

        total_additions = self.left_additions + self.right_additions
        code_counts = {}
        for addition in total_additions:
            code = additions_mapping.get(addition)
            if code:
                code_counts[code] = code_counts.get(code, 0) + 1

        for code, count in code_counts.items():
            if count > 1:
                self.codes.append(f"{code} x{count}")
            else:
                self.codes.append(code)

    def coverings_and_linings_section(self):
        """Adds codes based on the number of covers and linings."""
        if self.form_type == "simple":
            total_covers = self.covers_from_xml
        else:
            total_covers = self.covers_from_xml
        print(total_covers, "   ", self.linings_from_xml)
        y = total_covers + self.linings_from_xml

        if y == 2:
            code = "B55a"
        elif y == 3:
            code = "B55b"
        elif y >= 4:
            code = "B55c"
        else:
            code = None

        if code:
            code = self.apply_pair_handling(code)
            print(f"Code before adding to codes list: {code}")
            self.codes.append(code)
        print(y)

    def process_logic(self):
        """Processes all sections to generate the correct codes."""
        self.modelling_section()
        self.modification_section()
        self.postings_section()
        self.additions_section()
        self.coverings_and_linings_section()

        seen = set()
        unique_codes = []
        for code in self.codes:
            if code not in seen:
                unique_codes.append(code)
                seen.add(code)
        self.codes = unique_codes

        return self.codes


def read_xml_file(xml_file_path):
    try:
        with open(xml_file_path, 'r', encoding='utf-8') as file:
            xml_content = file.read()
        return xml_content
    except Exception as e:
        messagebox.showerror("Error", f"Error reading XML file: {str(e)}")
        return None


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

        type_mapping = {
            'TCI': 'tci',
            'Simple': 'simple',
            'Cradle': 'cradle',
            'HandMold': 'handmold'
        }

        selected_types = []

        for type_option in type_element:
            tag = type_option.tag
            text = type_option.text.strip() if type_option.text else ''
            print(f"Checking type: {tag}, value: '{text}'")

            if text.lower() == 'yes':
                form_type = type_mapping.get(tag)
                if form_type:
                    selected_types.append(form_type)
                else:
                    print(f"No mapping found for tag '{tag}'")

        if not selected_types:
            messagebox.showerror("Error", "No form type marked 'Yes' found in the XML file.")
            return None
        elif len(selected_types) > 1:
            selected_type = simpledialog.askstring(
                "Multiple Types Selected",
                f"Multiple form types are selected: {', '.join(selected_types)}.\nPlease enter the type you want to process:"
            )
            if selected_type and selected_type.lower() in [t.lower() for t in selected_types]:
                return selected_type.lower()
            else:
                messagebox.showerror("Error", "Invalid type selected.")
                return None
        else:
            print(f"Selected form type: {selected_types[0]}")
            return selected_types[0]
    except Exception as e:
        messagebox.showerror("Error", f"Error parsing XML content: {str(e)}")
        return None


def extract_auto_doc_reference_from_xml_string(xml_content):
    try:
        root = ET.fromstring(xml_content)
        auto_doc_ref_element = root.find('.//AutoDocRef')
        if auto_doc_ref_element is not None and auto_doc_ref_element.text:
            return auto_doc_ref_element.text.strip()
        else:
            return None
    except Exception as e:
        messagebox.showerror("Error", f"Error extracting auto doc reference: {str(e)}")
        return None


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


def process_xml_and_get_codes(xml_content, form_type):
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        messagebox.showerror("Error", f"Error parsing XML content: {str(e)}")
        return []

    pair = False
    base_material = None
    modifications = []
    postings = []
    left_additions = []
    right_additions = []
    covers_from_xml = 0
    linings_from_xml = 0

    top_cover_elements = root.findall('.//TopCover')
    print(f"Number of TopCover elements found: {len(top_cover_elements)}")

    if not top_cover_elements:
        print("No TopCover elements found. Check XML structure and element names.")

    for top_cover in top_cover_elements:
        material = top_cover.findtext('TopCoverMaterial')
        print(f"TopCoverMaterial found: {material}")
        if material:
            material = material.strip()
            if material == 'Spenco (Green)':
                covers_from_xml += 2
                print(f"Added 2 to covers_from_xml, new value: {covers_from_xml}")
            else:
                covers_from_xml += 1
                print(f"Added 1 to covers_from_xml, new value: {covers_from_xml}")
        else:
            print("TopCoverMaterial is missing or empty.")

    insole_side = root.find('.//InsoleSide')
    if insole_side is not None:
        pair = insole_side.findtext('Pair') == 'Yes'
        left = insole_side.findtext('Left') == 'Yes'
        right = insole_side.findtext('Right') == 'Yes'
        if left and right:
            pair = True
        elif left or right:
            pair = False

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
            base_material = 'Shore65'

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

    left_modifications = root.find('.//Left/Modification')
    if left_modifications is not None:
        for name, xml_tag in modifications_list:
            if left_modifications.findtext(xml_tag) == 'Yes':
                modifications.append(name)

    right_modifications = root.find('.//Right/Modification')
    if right_modifications is not None:
        for name, xml_tag in modifications_list:
            if right_modifications.findtext(xml_tag) == 'Yes':
                modifications.append(name)

    postings_tags = {
        "Rearfoot": ['MedialRearfootPosting', 'LateralRearfootPosting'],
        "Forefoot": ['MedialForefootPosting', 'LateralForefootPosting']
    }

    if left_modifications is not None:
        for posting_type, tags in postings_tags.items():
            for tag in tags:
                if left_modifications.findtext(tag) == 'Yes':
                    postings.append(posting_type)

    if right_modifications is not None:
        for posting_type, tags in postings_tags.items():
            for tag in tags:
                if right_modifications.findtext(tag) == 'Yes':
                    postings.append(posting_type)

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

    left_additions_section = root.find('.//Left/Additions')
    if left_additions_section is not None:
        for i in range(1, 5):
            addition = left_additions_section.findtext(f'Addition{i}')
            if addition and addition.strip() in additions_mapping_values:
                left_additions.append(addition.strip())

    right_additions_section = root.find('.//Right/Additions')
    if right_additions_section is not None:
        for i in range(1, 5):
            addition = right_additions_section.findtext(f'Addition{i}')
            if addition and addition.strip() in additions_mapping_values:
                right_additions.append(addition.strip())

    lining_elements = root.findall('.//Lining')
    for lining in lining_elements:
        linings_from_xml += 1

    logic = InsolePricingLogic(
        pair=pair,
        form_type=form_type,
        base=base_material,
        modifications=modifications,
        postings=postings,
        left_additions=left_additions,
        right_additions=right_additions,
        covers_from_xml=covers_from_xml,
        linings_from_xml=linings_from_xml
    )

    result_codes = logic.process_logic()
    return result_codes


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
