# generate_code_logic.py
import math
from collections import defaultdict
from tkinter import messagebox
import re
import sqlite3
import os
import sys

# Define the tariff customer number sets outside the functions
tariff_tci_customer_nos = {
    'GB-CUST01700', 'GB-CUST01940', 'GB-CUST01981', 'GB-CUST02090',
    'GB-CUST02295', 'GB-CUST02554', 'GB-CUST02583'
}
tariff_simple_customer_nos = {
    'GB-CUST01700', 'GB-CUST01940', 'GB-CUST01981', 'GB-CUST02090',
    'GB-CUST02295', 'GB-CUST02496', 'GB-CUST02554', 'GB-CUST02583'
}
tariff_polyprop_customer_nos = {
    'GB-CUST01700', 'GB-CUST01940', 'GB-CUST01981', 'GB-CUST02090',
    'GB-CUST02295', 'GB-CUST02554', 'GB-CUST02583'
}
tariff_bespoke_customer_nos = {
    'GB-CUST01700', 'GB-CUST01940', 'GB-CUST01981', 'GB-CUST02554'
}
tariff_afo_customer_nos = {
    'GB-CUST01700', 'GB-CUST01940', 'GB-CUST01981', 'GB-CUST02554'
}
tariff_modular_customer_nos = {
    'GB-CUST01700', 'GB-CUST01940', 'GB-CUST01981', 'GB-CUST02554'
}
tariff_wales_customer_nos = {
    'GB-CUST02743', 'GB-CUST02756', 'GB-CUST02766', 'GB-CUST02781',
    'GB-CUST02805', 'GB-CUST02830', 'GB-CUST02916', 'GB-CUST02917',
    'GB-CUST02918'
}

# Database path
if getattr(sys, 'frozen', False):
    base_path = os.path.dirname(sys.executable)
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

db_path = os.path.join(base_path, 'databases', 'clinic_nav_sell_to.db')

def get_customer_no(clinic_name):
    """Retrieve the Sell_to_Customer_No for a given clinic name."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT Sell_to_Customer_No FROM customers WHERE LOWER(Docuware_Clinic_Name) = LOWER(?)", (clinic_name,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return None

def generate_bespoke_codes(self, content):
    """Generates codes based on the content for the Bespoke model, counting duplicates."""
    passed_codes = defaultdict(float)  # Use float to allow fractional counts

    # Split the content into lines for easier processing
    lines = content.split('\n')

    # Convert lines to a dictionary
    content_dict = {}
    for line in lines:
        if ':' in line:
            key, value = line.split(':', 1)
            content_dict[key.strip().lower()] = value.strip().lower()

    clinic_name = content_dict.get('clinic', '').lower()
    customer_no = get_customer_no(clinic_name)

    # Track if tariffs were added
    bespoke_tariff_added = False

    # Wales Tariff Check for Bespoke
    if customer_no in tariff_wales_customer_nos:
        passed_codes['WALES-BESPOKE'] += 2
        bespoke_tariff_added = True

    # Bespoke Tariff Check
    if customer_no in tariff_bespoke_customer_nos:
        passed_codes['TARIFF BESPOKE'] += 2
        bespoke_tariff_added = True

    # Define style sets
    a1b_styles = {
        'trent', 'selby', 'hallam', 'totnes', 'tenby', 'chelsea', 'galway', 'vienna',
        'truro', 'colwyn', 'lineham', 'hove', 'plymouth', 'drayton', 'sneaker',
        'greenock', 'olympic', 'melton', 'hendon', 'stirling', 'exeter', 'chester',
        'kelso', 'dover', 'shelwyck', 'mowbray', 'shelby'
    }

    a1a_styles = {
        'bumper', 'whitby', 'tralee', 'rockingham', 'perth', 'rockliffe',
        'dundee', 'brigg', 'elgin', 'highland'
    }

    # Get style
    style = content_dict.get('style', '').lower()

    # Determine based on style
    if style in a1a_styles:
        passed_codes['A1A'] += 2
    elif style in a1b_styles:
        passed_codes['A1B'] += 2
    else:
        passed_codes['A1A'] += 2  # Default to A1A if no style matches

    # Add logic for 'pop cast'
    if content_dict.get('pop cast', '') == 'selected':
        passed_codes['A1K'] += 2

    # Stiffeners Checks
    for side in ['left', 'right']:
        a20_count = 0
        for typ in ['high', 'elongated']:
            for pos in ['medial', 'lateral']:
                if content_dict.get(f'stiffener {typ} {side} {pos}', '') == 'selected':
                    a20_count += 1
        if a20_count > 1:
            a20_count = 1
        passed_codes['A20'] += a20_count

        if content_dict.get(f'stiffener padded {side}', '') == 'selected':
            passed_codes['A15'] += 1

    # Sole Additions
    sole_addition_keys = {
        'sole additions left toe tips': 'A23',
        'sole additions right toe tips': 'A23',
        'sole additions left toe caps': 'A24',
        'sole additions right toe caps': 'A24',
        'sole additions left stick on soles': 'A25',
        'sole additions right stick on soles': 'A25'
    }

    for key, code in sole_addition_keys.items():
        if content_dict.get(key, '') == 'selected':
            passed_codes[code] += 2

    # Ankle Height for A17
    ankle_height_key = 'ankle height'
    ankle_height_str = content_dict.get(ankle_height_key, '')
    match = re.search(r'(\d+\.?\d*)\s*(cm|mm)?', ankle_height_str)
    if match:
        try:
            ankle_height = float(match.group(1))
            unit = match.group(2)
            if unit == 'cm':
                ankle_height *= 10  # Convert cm to mm
            if ankle_height > 150:
                excess = ankle_height - 150
                a17_count = math.ceil(excess / 25)
                passed_codes['A17'] += a17_count * 2
        except ValueError:
            # If conversion fails, skip
            pass

    if content_dict.get('easy grip boa', '') == 'selected':
        passed_codes['TWIST FASTEN'] += 2

    if content_dict.get('lining sheepskin', '') == 'selected':
        passed_codes['A18A'] += 2

    if content_dict.get('soling commando', '') == 'selected':
        passed_codes['A6'] += 1.0

    # Sockets
    for side in ['left', 'right']:
        type_a_sockets = ['5/16 round', '1/4 round', '1/16x9/16', 'rizzoli']
        type_b_sockets = ['5/16 backstop', '1/4 backstop']

        has_type_a = any(content_dict.get(f'{side} {socket}', '') == 'selected' for socket in type_a_sockets)
        has_type_b = any(content_dict.get(f'{side} {socket}', '') == 'selected' for socket in type_b_sockets)

        if has_type_a:
            passed_codes['A37A'] += 1
        if has_type_b:
            passed_codes['A37B'] += 1

    # Wedges
    wedges_heel_keys = [
        'left wedges heel medial',
        'left wedges heel lateral',
        'right wedges heel medial',
        'right wedges heel lateral',
    ]

    for key in wedges_heel_keys:
        if content_dict.get(key, '') == 'selected':
            passed_codes['A31'] += 2

    wedges_sole_keys = [
        'left wedges sole medial',
        'left wedges sole lateral',
        'right wedges sole medial',
        'right wedges sole lateral',
    ]

    for key in wedges_sole_keys:
        if content_dict.get(key, '') == 'selected':
            passed_codes['A19'] += 2

    # Floated
    floated_heel_keys = [
        'left floated heel medial',
        'left floated heel lateral',
        'right floated heel medial',
        'right floated heel lateral',
    ]

    for key in floated_heel_keys:
        if content_dict.get(key, '') == 'selected':
            passed_codes['A31'] += 2

    floated_sole_keys = [
        'left floated sole medial',
        'left floated sole lateral',
        'right floated sole medial',
        'right floated sole lateral',
    ]

    for key in floated_sole_keys:
        if content_dict.get(key, '') == 'selected':
            passed_codes['A26'] += 2

    # Raises - to do the 25mm+ codes - need to be updated
    for side in ['left', 'right']:
        raise_inside_key = f'raise {side} inside'
        raise_outside_key = f'raise {side} outside'
        raise_material_key = f'{side} raise material'

        raise_material = content_dict.get(raise_material_key, '')

        if content_dict.get(raise_inside_key, '') == 'selected':
            if raise_material in ('ld eva', 'lightweight p/zote (non-covered)', 'lightweight p/zote (covered)', 'cork'):
                passed_codes['A8'] += 2

        if content_dict.get(raise_outside_key, '') == 'selected':
            if raise_material == 'ld eva':
                passed_codes['A13A'] += 2
            elif raise_material in ('lightweight p/zote (non-covered)', 'lightweight p/zote (covered)'):
                passed_codes['A12A'] += 2

    # Elongations
    for side in ['left', 'right']:
        elongation_types = ['elongation full', 'elongation half', 'elongation med', 'elongation lat']
        if any(content_dict.get(f'{side} {typ}', '') == 'selected' for typ in elongation_types):
            passed_codes['A31'] += 2

    # Rocker
    for side in ['left', 'right']:
        rocker_types = ['standard rocker', 'plr rocker', 'two point rocker']
        if any(content_dict.get(f'{side} {rocker_type}', '') == 'selected' for rocker_type in rocker_types):
            passed_codes['A19'] += 2

    # Straps
    for side in ['left', 'right']:
        if content_dict.get(f'{side} t strap', '') == 'selected' or content_dict.get(f'{side} y strap', '') == 'selected':
            if content_dict.get(f'{side} double decker', '') == 'selected':
                passed_codes['A39'] += 2
            else:
                passed_codes['A38'] += 2
        elif content_dict.get(f'{side} spur retaining strap', '') == 'selected' or content_dict.get(f'{side} heel retaining strap', '') == 'selected':
            passed_codes['A40'] += 2

    # --- Final Filtering Step ---
    bespoke_filter_codes = {
        'A1B', 'A1A', 'A1K', 'A22', 'A23', 'A24', 'A25',
        'TWIST FASTEN', 'A18A', 'A6', 'A15', 'A16', 'A37A',
        'A37B', 'A31', 'A19', 'A26', 'A8', 'A13A', 'A12A',
        'A39', 'A38', 'A40', 'B54B'
    }
    # If bespoke tariff selected, remove bespoke_filter_codes
    if bespoke_tariff_added:
        for c in bespoke_filter_codes:
            if c in passed_codes:
                del passed_codes[c]

    # Call insole logic and update passed_codes
    insole_passed = generate_insole_codes(self, content, return_dict=True)
    for code, count in insole_passed.items():
        passed_codes[code] += count

    # Format output
    formatted_passed_codes = []
    for code, count in passed_codes.items():
        if count.is_integer():
            display_count = int(count)
        else:
            display_count = count
        if display_count > 1:
            formatted_passed_codes.append(f"{code} x{display_count}")
        else:
            formatted_passed_codes.append(code)
    if formatted_passed_codes:
        return ', '.join(formatted_passed_codes)
    else:
        return None
    
def generate_insole_codes(self, content, return_dict=False):
    """Generates insole codes based on the content."""
    passed_codes = defaultdict(int)  # Use defaultdict to count occurrences

    # Split the content into lines
    lines = content.split('\n')

    # Convert lines to a dictionary
    content_dict = {}
    for line in lines:
        if ':' in line:
            key, value = line.split(':', 1)
            content_dict[key.strip().lower()] = value.strip().lower()

    # Determine the selected base
    selected_base = None
    for key, value in content_dict.items():
        if key.startswith('base ') and value == 'selected':
            selected_base = key[5:].strip().lower()
            break

    print(f"Selected base: '{selected_base}'")  # For debugging

    clinic_name = content_dict.get('clinic', '').lower()
    customer_no = get_customer_no(clinic_name)

    # Check if it's a pair
    is_pair = (content_dict.get('pair', '') == 'selected' or 
               content_dict.get('insole pair', '') == 'selected')

    # Determine insole type early for medway logic
    insole_type = None
    if content_dict.get('insole type tci', '') == 'selected' or content_dict.get('cradle', '') == 'selected':
        insole_type = 'tci'
    elif content_dict.get('insole type simple', '') == 'selected':
        insole_type = 'simple'
    elif content_dict.get('insole type hand mould', '') == 'selected':
        insole_type = 'handmould'

    # Wales Tariff Logic for Insoles
    if customer_no in tariff_wales_customer_nos:
        if selected_base == 'poly':
            passed_codes['WALES-POLYPROP'] += 1
        elif insole_type == 'simple':
            passed_codes['WALES-SIMPLE'] += 1
        elif insole_type in ('tci', 'cradle'):
            passed_codes['WALES-TCI'] += 1
        if is_pair:
            for code in list(passed_codes.keys()):
                passed_codes[code] *= 2
        # Remove other codes
        for code in list(passed_codes.keys()):
            if code not in ['WALES-POLYPROP', 'WALES-SIMPLE', 'WALES-TCI']:
                del passed_codes[code]

    # Now unify the three tariff checks in a single block:
    elif customer_no in tariff_polyprop_customer_nos and selected_base == 'poly':
        passed_codes['TARIFF POLYPROPS'] += 1
        if is_pair:
            passed_codes['TARIFF POLYPROPS'] *= 2
        # Remove other codes
        for code in list(passed_codes.keys()):
            if code != 'TARIFF POLYPROPS':
                del passed_codes[code]

    # 2) Else if the customer_no allows "simple" & insole_type == 'simple'
    elif customer_no in tariff_simple_customer_nos and insole_type == 'simple':
        passed_codes['TARIFF SIMPLE INSOLE'] += 1
        if is_pair:
            passed_codes['TARIFF SIMPLE INSOLE'] *= 2
        # Remove other codes
        for code in list(passed_codes.keys()):
            if code != 'TARIFF SIMPLE INSOLE':
                del passed_codes[code]

    # 3) Else if the customer_no is in the TCI list
    elif customer_no in tariff_tci_customer_nos:
        passed_codes['TARIFF TCI\'S'] += 1
        if is_pair:
            passed_codes['TARIFF TCI\'S'] *= 2
        # Remove other codes
        for code in list(passed_codes.keys()):
            if code != 'TARIFF TCI\'S':
                del passed_codes[code]

    # If no tariff matched, proceed with normal logic
    else:
        # Base logic using selected_base
        if selected_base:
            normalized_base = selected_base.replace(' ', '').lower()

            if 'greyporon' in normalized_base:
                passed_codes['B40B'] += 1
            elif normalized_base == 'poly':
                passed_codes['B54B'] += 1
            elif normalized_base in ['a65high', 'a50med', 'a40low']:
                if insole_type == 'simple':
                    passed_codes['B40B'] += 1
                else:
                    passed_codes['B54C'] += 1  # Default if not simple
            elif 'carbon' in normalized_base:
                passed_codes['B54A'] += 1
            else:
                passed_codes['B54C'] += 1

        # Foot modifications -> BNS45
        foot_modifications = [
            'hole and plug', 'custom hole and plug', '1st met head', '1st met ray', '5th met ray', '5th met head', 'all mets',
            'navicular sweet spot', 'fascial accommodation', 'lateral heel flange', 'medial heel flange'
        ]

        left_modifications_count = 0
        right_modifications_count = 0

        for mod in foot_modifications:
            left_key = f"left {mod}"
            right_key = f"right {mod}"
            if content_dict.get(left_key, '') == 'selected':
                left_modifications_count += 1
                passed_codes['BNS45'] += 1
            if content_dict.get(right_key, '') == 'selected':
                right_modifications_count += 1
                passed_codes['BNS45'] += 1

        # Postings
        posting_keys_left = [
            'left medial rearfoot posting', 'left lateral rearfoot posting',
            'left medial forefoot posting', 'left lateral forefoot posting',
        ]
        posting_keys_right = [
            'right medial rearfoot posting', 'right lateral rearfoot posting',
            'right medial forefoot posting', 'right lateral forefoot posting',
        ]

        left_postings_count = 0
        right_postings_count = 0

        for key in posting_keys_left:
            if content_dict.get(key, '') == 'selected':
                left_postings_count += 1
                passed_codes['B56'] += 1

        for key in posting_keys_right:
            if content_dict.get(key, '') == 'selected':
                right_postings_count += 1
                passed_codes['B56'] += 1

        insole_right_as_left = content_dict.get('right as left insole modification', '') == 'selected'

        # Right as Left for modifications
        if insole_right_as_left and ((left_modifications_count == 0 and right_modifications_count > 0) or
                                    (left_modifications_count > 0 and right_modifications_count == 0)):
            passed_codes['BNS45'] *= 2

        # Right as Left for postings
        if insole_right_as_left and 'B56' in passed_codes and passed_codes['B56'] > 0:
            if (left_postings_count == 0 and right_postings_count > 0) or (left_postings_count > 0 and right_postings_count == 0):
                passed_codes['B56'] *= 2


        # Additions
        addition_keys = [
            'left valgus pad 3mm', 'left valgus pad 6mm', 'right valgus pad 3mm',
            'left heel pad 3mm', 'left heel pad 6mm', 'right heel pad 3mm', 'right heel pad 6mm',
            'left mortons extension', 'right mortons extension',
            'left reverse mortons extension', 'right reverse mortons extension',
            'left met bar', 'right met bar',
            'left met dome', 'right met dome',
            'left heel raise', 'right heel raise',
        ]

        for key in addition_keys:
            value = content_dict.get(key, '').strip().lower()
            if value and 'unselected' not in value:
                addition_type_parts = key.split()[1:]  # skip left/right
                addition_str = ' '.join(addition_type_parts).replace(' 3mm', '').replace(' 6mm', '')  # remove thickness
                if addition_str == 'valgus pad':
                    passed_codes['B41'] += 1
                elif addition_str == 'heel pad':
                    passed_codes['B41'] += 1
                elif addition_str == "mortons extension":
                    passed_codes['B56'] += 1
                elif addition_str == "reverse mortons extension":
                    passed_codes['B56'] += 1
                elif addition_str == 'met bar':
                    passed_codes['B41'] += 1
                elif addition_str == 'met dome':
                    passed_codes['B41'] += 1
                elif addition_str == 'heel raise':
                    passed_codes['B43'] += 1
                else:
                    print(f"Warning: Unrecognized addition '{addition_str}' for '{key}'")

        # Insole coding - MATHS
        x = 1
        print(f"Initial value: x = {x}")

        if insole_type == 'simple':
            x -= 1
            print(f"After insole_type 'simple' check: x = {x}")
        if content_dict.get('no lining', '') == 'selected':
            x -= 0
            print(f"After no lining check: x = {x}")
        else:
            x += 1
            print(f"After no lining check (else): x = {x}")

        if content_dict.get('spenco 1.5mm', '') == 'selected' or content_dict.get('spenco 3mm', '') == 'selected':
            x += 1
            print(f"After spenco check: x = {x}")

        if selected_base in ['a40/25/80', 'a30/20/80']:
            x += 1
            print(f"After base check: x = {x}")

        if x >= 3:
            passed_codes['B55C'] += 1
            print(f"x >= 3, incrementing B55C: {passed_codes['B55C']}")
        elif x == 2:
            passed_codes['B55B'] += 1
            print(f"x == 2, incrementing B55B: {passed_codes['B55B']}")
        elif x == 1:
            passed_codes['B55A'] += 1
            print(f"x == 1, incrementing B55A: {passed_codes['B55A']}")
        # CLCH Simple Logic
        if clinic_name == 'clch' and insole_type == 'simple':
            total_posts = (passed_codes['B41'] + passed_codes['B56'] +
                           passed_codes['B43'] + passed_codes['BNS45'])

            # Decide tariff
            if total_posts <= 4:
                chosen_tariff = 'TARIFF INSOLE>4 POST'
            else:
                chosen_tariff = 'TARIFF INSOLE<5 POST'

            passed_codes[chosen_tariff] += 1

            # Remove all non-tariff codes (all except chosen_tariff)
            for code in list(passed_codes.keys()):
                if code != chosen_tariff:
                    del passed_codes[code]

            # Now handle pairs including chosen_tariff
            if is_pair:
                # Double the chosen tariff code if it's still present
                if chosen_tariff in passed_codes:
                    passed_codes[chosen_tariff] *= 2
        else:
            # Normal pair handling if not CLCH simple
            if is_pair:
                codes_to_double_insole = ['B54C', 'B40B', 'B54A', 'B55A', 'B55B', 'B55C', 'B54B']
                for code in codes_to_double_insole:
                    if code in passed_codes:
                        passed_codes[code] *= 2

    if return_dict:
        return passed_codes

    # Format output if not return_dict
    formatted_passed_codes = []
    for code, count in passed_codes.items():
        if count > 1:
            formatted_passed_codes.append(f"{code} x{count}")
        else:
            formatted_passed_codes.append(code)

    if formatted_passed_codes:
        return ', '.join(formatted_passed_codes)
    else:
        return None
            
def generate_afo_codes(self, content):
    """Generates codes based on the content for the AFO model, counting duplicates."""
    """
    from collections import defaultdict
    passed_codes = defaultdict(int)  # Use defaultdict to count occurrences

    # Split the content into lines for easier processing
    lines = content.split('\n')

    # Convert lines to a dictionary for easier lookup with lowercase keys and values
    content_dict = {}
    for line in lines:
        if ':' in line:
            key, value = line.split(':', 1)
            content_dict[key.strip().lower()] = value.strip().lower()

    # Extract the clinic name if it exists in the content
    clinic_name = content_dict.get('clinic', '').lower()
    customer_no = get_customer_no(clinic_name)

    # Check if it's a pair for AFO
    is_pair = content_dict.get('pair', '') == 'selected' or content_dict.get('afo pair', '') == 'selected'

    # Wales Tariff for AFO
    if customer_no in tariff_wales_customer_nos:
        passed_codes['WALES-AFO'] += 1
        if is_pair:
            passed_codes['WALES-AFO'] *= 2
        return 'WALES-AFO' if passed_codes['WALES-AFO'] == 1 else f'WALES-AFO x{passed_codes["WALES-AFO"]}'

    # --- Tariff AFO Check ---
    if customer_no in tariff_afo_customer_nos:
        passed_codes['TARIFF AFO'] += 1
        if is_pair:
            passed_codes['TARIFF AFO'] *= 2
        return 'TARIFF AFO' if passed_codes['TARIFF AFO'] == 1 else f'TARIFF AFO x{passed_codes["TARIFF AFO"]}'

    # --- Start of AFO-specific logic (if not a Tariff AFO clinic) ---
    # Default codes
    default_codes = ['D1C', 'D8U']

    # Determine AFO Type codes with pair handling for 'D8U'
    afo_type = content_dict.get('afo type', '').lower()
    if afo_type in ('normal', 'fixed', 'articulated'):
        passed_codes['D1C'] += 1
        code_count = 1
        if content_dict.get('afo pair', '') == 'selected':
            code_count *= 2
        passed_codes['D8U'] += code_count
    elif afo_type == 'crow boot':
        passed_codes['DNS1'] += 1
    elif afo_type == 'afo/dafo':
        passed_codes['D1C'] += 2
        code_count = 2
        if content_dict.get('afo pair', '') == 'selected':
            code_count *= 2
        passed_codes['D8U'] += code_count
    elif afo_type == 'anterior shell':
        passed_codes['D12M'] += 1
    else:
        # If 'AFO Type' does not exist, use default codes
        passed_codes['D1C'] += 1
        code_count = 1
        if content_dict.get('afo pair', '') == 'selected':
            code_count *= 2
        passed_codes['D8U'] += code_count

    # Check for 'Anterior Shell Height' even if 'AFO Type' is not 'anterior shell'
    if afo_type != 'anterior shell' and content_dict.get('anterior shell height', ''):
        passed_codes['D12M'] += 1

    # Determine Hinge Type codes
    hinge_type = content_dict.get('hinge type', '').lower()
    hinge_code = None
    if hinge_type == 'gillette/tamrack':
        hinge_code = 'D2A'
    elif hinge_type in ('double action', 'camber axis'):
        hinge_code = 'D2D'
    elif hinge_type in ('appalachian/metal', 'appalachian', 'metal'):
        hinge_code = 'D2B'

    if hinge_code:
        code_count = 1
        if content_dict.get('afo pair', '') == 'selected':
            code_count *= 2
        passed_codes[hinge_code] += code_count

    # Heel Posting
    heel_posting_codes = 0
    heel_posting_keys = [
        'left heel posting attached', 'left heel posting blended',
        'left heel posting heel only', 'left heel posting loose',
        'right heel posting attached', 'right heel posting blended',
        'right heel posting heel only', 'right heel posting loose'
    ]
    right_as_left_heel = content_dict.get('ca&t right as left', '') == 'selected'
    left_heel_posting = any(content_dict.get(key, '') == 'selected' for key in heel_posting_keys if 'left' in key)
    right_heel_posting = any(content_dict.get(key, '') == 'selected' for key in heel_posting_keys if 'right' in key)

    if right_as_left_heel and (left_heel_posting != right_heel_posting):
        heel_posting_codes = 2
    else:
        heel_posting_codes = sum([left_heel_posting, right_heel_posting])

    if heel_posting_codes > 0:
        passed_codes['D10E'] += heel_posting_codes

    # PCRO Codes
    pcro_codes = defaultdict(int)
    pcro_right_as_left = content_dict.get('pcro right as left', '') == 'selected'

    # List of PCRO features and their codes
    pcro_features = {
        'varus resist': 'D8D',
        'valgus resist': 'D8D',
        'suctentaculum tali': 'D8H',
        'peroneal notch': 'D8I',
        'metatarsal button': 'B41',
        'neuro plate': 'D8A',
        'toe lift': 'D8U',
        'pcro values': 'D8B'
    }

    for feature, code in pcro_features.items():
        left_key = f'{feature} left'
        right_key = f'{feature} right'

        left_selected = content_dict.get(left_key, '') == 'selected' or content_dict.get(left_key, '').isdigit()
        right_selected = content_dict.get(right_key, '') == 'selected' or content_dict.get(right_key, '').isdigit()

        if pcro_right_as_left and (left_selected != right_selected):
            # If right as left is selected and only one side is filled out, multiply by 2
            total = 2
        else:
            total = sum([left_selected, right_selected])

        if total > 0:
            pcro_codes[code] += total

    # Add PCRO codes to passed_codes
    for code, count in pcro_codes.items():
        passed_codes[code] += count

    # Kirby Skive
    left_kirby_selected = content_dict.get('left kirby skive medial', '') == 'selected' or content_dict.get('left kirby skive lateral', '') == 'selected'
    right_kirby_selected = content_dict.get('right kirby skive medial', '') == 'selected' or content_dict.get('right kirby skive lateral', '') == 'selected'

    if pcro_right_as_left and (left_kirby_selected != right_kirby_selected):
        total_kirby = 2
    else:
        total_kirby = sum([left_kirby_selected, right_kirby_selected])

    if total_kirby > 0:
        passed_codes['D8A'] += total_kirby

    # M&T Codes
    m_and_t_codes = []
    if content_dict.get('carbon ankle reinforcements', '') == 'selected':
        m_and_t_codes.append('D10B')
    if content_dict.get('ribbed ankle reinforcements', '') == 'selected':
        m_and_t_codes.append('D10A')
    if content_dict.get('walking surface', '') == 'selected':
        m_and_t_codes.append('D10G')
    if content_dict.get('transfer 1st choice', ''):
        m_and_t_codes.append('D10I')

    # Add M&T codes
    for code in m_and_t_codes:
        passed_codes[code] += 1

    # AFO Lining (only calf material)
    afo_lining_codes = []

    # Process AFO Calf Material
    afo_calf_material_value = content_dict.get('afo calf material', '').lower()

    if afo_calf_material_value:
        if afo_calf_material_value.startswith('yes'):
            afo_lining_codes.append('D14D')  # Add D14D code for 'yes' override
            # Extract the material after 'yes'
            afo_calf_material = afo_calf_material_value[3:].strip()
        else:
            # If 'yes' is not present, assume the entire value is the material
            afo_calf_material = afo_calf_material_value.strip()
    else:
        afo_calf_material = ''  # No material provided

    # Materials for AFO Lining
    lining_materials = {
        'ld eva': 'D14D',
        "p'zote": 'D14D',
        'chamois': 'D14F',
        'leather': 'D14F',
        'sheepskin': 'D14F'
    }

    # Check and add codes based on calf material
    if afo_calf_material in lining_materials:
        afo_lining_codes.append(lining_materials[afo_calf_material])

    # Add AFO lining codes
    for code in afo_lining_codes:
        passed_codes[code] += 1

    # Pads
    pads_codes = []

    if content_dict.get('arch pads', '').lower() == 'yes':
        pads_codes.append('D14C')
    if content_dict.get('navicular pad', '').lower() == 'yes':
        pads_codes.append('D14C')

    # Add pads codes 
    for code in pads_codes:
        passed_codes[code] += 1

    # Slotted Heel Strap
    sides = ['left', 'right']
    slip_pads = ['slip pad calf', 'slip pad ankle', 'slip pad foot']
    slip_pads_needed = any(content_dict.get(pad, '') == 'yes' for pad in slip_pads)

    for side in sides:
        strap_type_key = f'{side} strap type'
        strap_type = content_dict.get(strap_type_key, '').lower()

        if strap_type == 'y strap':
            passed_codes['D14A'] += 1
            passed_codes['P15'] += 1
        elif strap_type == 'full as part of ankle lining':
            passed_codes['D14A'] += 1
            passed_codes['P15'] += 1
        elif strap_type == 'single slotted fix':
            passed_codes['P1'] += 1
            passed_codes['P4'] += 1
            passed_codes['P15'] += 1
        elif not strap_type and slip_pads_needed:
            passed_codes['P15'] += 1

    # Additional Information
    additional_info_fields = [
        'additional information',
        'ca&t comments',
        'm&t comments',
        'pcro comments'
    ]

    for field in additional_info_fields:
        comments = content_dict.get(field, '').lower()
        
        # Check for 'make multiple' to multiply all codes accordingly
        if 'make multiple' in comments:
            # Try to extract the multiplier from the comments, e.g., 'make multiple 3'
            multiplier = 2  # Default to 2 if not specified
            words = comments.split()
            for i, word in enumerate(words):
                if word == 'multiple' and i + 1 < len(words):
                    try:
                        multiplier = int(words[i + 1])
                    except ValueError:
                        pass  # Keep default multiplier
            # Multiply all codes accordingly
            for code in passed_codes:
                passed_codes[code] *= multiplier

    # --- Pair Handling ---
    # Apply Pair Handling after all codes have been added
    if content_dict.get('afo pair', '') == 'selected':
        # Codes to exclude from pair handling
        codes_to_exclude = ['D10E', 'P1', 'P4', 'D8D','D8H','D8A', 'B41','D8I', 'D8U', 'D8B', 'D2D', 'D2B', 'D2A', 'D8A']
        for code in passed_codes:
            if code not in codes_to_exclude:
                passed_codes[code] *= 2

    # Cap 'D8U' at a maximum of 2
    if 'D8U' in passed_codes and passed_codes['D8U'] > 2:
        passed_codes['D8U'] = 2

    # Format the passed codes with counts
    formatted_passed_codes = []
    for code, count in passed_codes.items():
        if count > 1:
            formatted_passed_codes.append(f"{code} x{count}")
        else:
            formatted_passed_codes.append(code)

    # Return the passed codes as a string
    if formatted_passed_codes:
        return ', '.join(formatted_passed_codes)
    else:
    """
    return None  # Return None if no codes were added
    
def generate_modular_codes(self, content):
    """Generates codes based on the content for the Modular model, with tariff logic."""
    passed_codes = defaultdict(int) # Use defaultdict to count occurrences
    # Split the content into lines
    lines = content.split('\n')
    # Convert lines to a dictionary
    content_dict = {}
    for line in lines:
        if ':' in line:
            key, value = line.split(':', 1)
            content_dict[key.strip().lower()] = value.strip().lower()
    clinic_name = content_dict.get('clinic', '').lower()
    customer_no = get_customer_no(clinic_name)
    # Track if tariffs were added
    modular_tariff_added = False
    # Wales Tariff Check for Modular
    if customer_no in tariff_wales_customer_nos:
        passed_codes['WALES-MODULAR'] += 2
        modular_tariff_added = True
    # Modular Tariff Check (other clinics)
    if customer_no in tariff_modular_customer_nos:
        passed_codes['TARIFF MODULAR'] += 2
        modular_tariff_added = True
    # Style Checks
    style_value = content_dict.get('styles', '')
    style = content_dict.get('styles', '').lower()
    sport_styles = {'sneaker', 'greenock', 'greeock', 'colwyn', 'lineham', 'hove', 'plymouth',
                    'drayton', 'olympic', 'melton', 'kelso', 'dover', 'shelwyck', 'mowbray'}
    shoe_styles = {'trent', 'selby', 'hallam', 'totnes', 'tenby', 'chelsea', 'galway', 'vienna',
                   'truro', 'hendon', 'stirling', 'exeter', 'chester', 'shelby'}
    boot_styles = {'bumper', 'whitby', 'tralee', 'rockingham', 'perth', 'rockliffe',
                   'dundee', 'brigg', 'elgin', 'highland'}
    if style in sport_styles:
        passed_codes['MODULAR SPORTS'] += 2
    elif style in shoe_styles:
        passed_codes['MODULAR SHOES'] += 2
    elif style in boot_styles:
        passed_codes['MODULAR BOOTS'] += 2
    # Velcro logic
    velcro_selected = content_dict.get('r/pull velcro', '') == 'selected' or content_dict.get('lay on velcro', '') == 'selected'
    if velcro_selected:
        passed_codes['VELCRO'] += 2
        x2_styles = {'selby', 'chelsea', 'vienna', 'truro', 'lineham', 'hove', 'plymouth', 'drayton', 'sneaker', 'olympic', 'melton', 'rockingham', 'dover', 'shelwyck', 'mowbray', 'rockliffe', 'dundee'}
        x3_styles = {'bumper', 'whitby', 'perth', 'elgin'}
        if style in x2_styles:
            passed_codes['VELCRO'] *= 2
        elif style in x3_styles:
            passed_codes['VELCRO'] *= 3
    # Sheepskin lining
    if content_dict.get('sheepskin lining', '') == 'selected':
        passed_codes['B14'] += 2
    # Commando soling
    if content_dict.get('commando soling', '') == 'selected':
        passed_codes['BNS62'] += 2
    # Straps
    for side in ['left', 'right']:
        if content_dict.get(f'{side} t strap', '') == 'selected':
            passed_codes['B33'] += 1
        if content_dict.get(f'{side} doubledecker', '') == 'selected':
            passed_codes['B34'] += 1
        if content_dict.get(f'{side} heel retaining', '') == 'selected' or content_dict.get(f'{side} spur retaining', '') == 'selected':
            passed_codes['B8'] += 1
    # Rockers
    for side in ['left', 'right']:
        if content_dict.get(f'{side} rocker standard', '') == 'selected':
            passed_codes['B17'] += 1
            passed_codes['B5'] += 1
        if content_dict.get(f'{side} rocker plr', '') == 'selected':
            passed_codes['B17'] += 1
            passed_codes['B5'] += 1
        if content_dict.get(f'{side} rocker two point', '') == 'selected':
            passed_codes['B17'] += 1
        if content_dict.get(f'{side} rocker toe protector', '') == 'selected':
            passed_codes['B24'] += 1
        if content_dict.get(f'{side} rocker welt protector', '') == 'selected':
            passed_codes['B23'] += 1
    # Sockets
    for side in ['left', 'right']:
        type_a_sockets = ['5/16 round', '1/4 round', '1/16x9/16', 'rizzoli']
        type_b_sockets = ['5/16 backstop', '1/4 backstop']
        has_type_a = any(content_dict.get(f'{side} {socket}', '') == 'selected' for socket in type_a_sockets)
        has_type_b = any(content_dict.get(f'{side} {socket}', '') == 'selected' for socket in type_b_sockets)
        if has_type_a:
            passed_codes['B30'] += 1
        if has_type_b:
            passed_codes['B31'] += 1
    # Floated
    if content_dict.get('left floated heel length', '') != '':
        passed_codes['B25'] += 1
    if content_dict.get('right floated heel length', '') != '':
        passed_codes['B25'] += 1
    if content_dict.get('left floated sole length', '') != '':
        passed_codes['B19'] += 1
    if content_dict.get('right floated sole length', '') != '':
        passed_codes['B19'] += 1
    # Wedges
    if content_dict.get('left wedges heel length', '') != '':
        passed_codes['B25'] += 1
    if content_dict.get('right wedges heel length', '') != '':
        passed_codes['B25'] += 1
    if content_dict.get('left wedges sole length', '') != '':
        passed_codes['B18'] += 1
    if content_dict.get('right wedges sole length', '') != '':
        passed_codes['B18'] += 1
    # Raises (assuming height is provided per side in mm; using a simple regex to extract number)
    for side in ['left', 'right']:
        if content_dict.get(f'{side} heel external raise', '') == 'selected' or content_dict.get(f'{side} sole external raise', '') == 'selected':
            raise_height_str = content_dict.get(f'{side} raise height', '')
            height = 0
            match = re.search(r'(\d+\.?\d*)', raise_height_str)
            if match:
                height = float(match.group(1))
            if height <= 25:
                passed_codes['B3'] += 2
            else:
                passed_codes['B4'] += 2
    # --- Final Filtering Step ---
    modular_filter_codes = {
        '6MM', 'PATTERN', 'BNS62', 'MODULAR SHOES', 'MODULAR BOOTS',
        'MODULAR SPORTS', 'TWIST FASTEN', 'VELCRO', 'B34', 'B33', 'B8',
        'B30', 'B31', 'B25', 'B17', 'B18', 'B19'
    }
    if modular_tariff_added:
        for c in modular_filter_codes:
            if c in passed_codes:
                del passed_codes[c]
    # Call insole logic and update passed_codes
    insole_passed = generate_insole_codes(self, content, return_dict=True)
    for code, count in insole_passed.items():
        passed_codes[code] += count
    # Format output
    formatted_passed_codes = []
    for code, count in passed_codes.items():
        if count > 1:
            formatted_passed_codes.append(f"{code} x{count}")
        else:
            formatted_passed_codes.append(code)
    if formatted_passed_codes:
        return ', '.join(formatted_passed_codes)
    else:
        return None
    
def generate_a_and_r_codes(self, content):
    """
    Generates codes for the 'A&R' (Adapts and Repairs) model type based on content.
    
    Args:
        self: The instance of PdfButtonHandler.
        content (str): The extracted data from the PDF as a string.
    
    Returns:
        str: A comma-separated string of generated codes, or None if no codes are generated.
    """
    # should return nothing
    return

# In generate_code_logic.py
def generate_kafo_codes(handler, content):
    """
    Generate codes for the Kafo form based on the provided content.
    This is a placeholder; adjust logic to match A&R behavior as needed.
    
    Args:
        handler: PdfButtonHandler instance (for potential future use).
        content (str): Extracted data from the form.
    
    Returns:
        str: Generated codes or None if no codes are generated.
    """
    # Example logic (copy from generate_a_and_r_codes and modify if necessary)
    return None  # Return None if no codes are generated