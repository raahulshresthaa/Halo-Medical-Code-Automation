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
tariff_medway_customer_nos = {'GB-CUST02158'}

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
    insole_tariff_added = False

    # --- Medway Tariffs for Bespoke ---
    if customer_no in tariff_medway_customer_nos:
        if insole_type == 'simple':
            passed_codes['MEDBNS71'] += 2
        else:
            passed_codes['MEDBNS72'] += 2
        passed_codes['MEDFOOTWEAR'] += 2
        bespoke_tariff_added = True
        insole_tariff_added = True

    # Wales Tariff Check for Bespoke
    if customer_no in tariff_wales_customer_nos:
        passed_codes['WALES-BESPOKE'] += 2
        bespoke_tariff_added = True

    # Bespoke Tariff Check
    if customer_no in tariff_bespoke_customer_nos:
        passed_codes['TARIFF BESPOKE'] += 2
        bespoke_tariff_added = True

    # Determine insole type
    insole_type = None
    if content_dict.get('insole type tci', '') == 'selected':
        insole_type = 'tci'
    elif content_dict.get('insole type cradle', '') == 'selected':
        insole_type = 'cradle'
    elif content_dict.get('insole type simple', '') == 'selected':
        insole_type = 'simple'
    elif content_dict.get('insole type handmould', '') == 'selected':
        insole_type = 'handmould'

    # Wales Insole Tariff Checks
    if customer_no in tariff_wales_customer_nos:
        if insole_type in ('tci', 'cradle'):
            passed_codes['WALES-TCI'] += 2
            insole_tariff_added = True
        elif insole_type == 'simple':
            passed_codes['WALES-SIMPLE'] += 2
            insole_tariff_added = True
        elif insole_type == 'handmould':
            passed_codes['WALES-POLYPROP'] += 2
            insole_tariff_added = True

    # Insole Tariff Checks - Updated to consider both insole_type and customer_no
    if insole_type in ('tci', 'cradle') and customer_no in tariff_tci_customer_nos:
        passed_codes['TARIFF TCI\'S'] += 2
        insole_tariff_added = True
    elif insole_type == 'simple' and customer_no in tariff_simple_customer_nos:
        passed_codes['TARIFF SIMPLE INSOLE'] += 2
        insole_tariff_added = True
    elif insole_type == 'handmould' and customer_no in tariff_polyprop_customer_nos:
        passed_codes['TARIFF POLYPROPS'] += 2
        insole_tariff_added = True

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

    # Type-based logic (trumps style)
    a1a_types = ['type boots', 'type bootee']
    a1b_types = ['type shoes', 'type sports']

    if any(content_dict.get(key, '') == 'selected' for key in a1a_types):
        passed_codes['A1A'] += 2
    elif any(content_dict.get(key, '') == 'selected' for key in a1b_types):
        passed_codes['A1B'] += 2
    else:
        # No type selected, check style
        if style in a1a_styles:
            passed_codes['A1A'] += 2
        elif style in a1b_styles:
            passed_codes['A1B'] += 2
        else:
            passed_codes['A1A'] += 2  # Default to A1A if no type or style matches

    # Add logic for 'pop cast'
    if content_dict.get('pop cast', '') == 'selected':
        passed_codes['A1K'] += 2

    base = content_dict.get('base', '').strip().lower()
    normalized_base = base.replace(' ', '').lower()

    addition_positions = [
        'left 1st addition', 'left 2nd addition', 'left 3rd addition', 'left 4th addition',
        'right 1st addition', 'right 2nd addition', 'right 3rd addition', 'right 4th addition'
    ]

    addition_code_mapping = {
        'A45_B41': {
            'valgus pad', 'metatarsal pad', 'metatarsal bar', 'balance pad',
            'heel pad', 'cuboid pad', 'cobra pad', 'neuroma pad',
            'sulcus crest', 'arch fill'
        },
        'A45_B56': {
            "morton's extension", "reverse morton's extension", 'poron forefoot'
        },
        'A45_B43': {'kinetic wedge', 'heel raise'},
        'D8A': {'neurological footplate'},
        'BNS45': {'recess', 'hole & plug'},
        'A20_B20': {'rigid 1st extension'},
        'A46_B50': {'partial toe block'},
        'A47_B51': {'full toe block'}
    }

    # Additions with special handling for heel raise in cradle
    for key in addition_positions:
        addition_value = content_dict.get(key, '')
        if addition_value:
            if insole_type == 'cradle' and addition_value == 'heel raise':
                # Special logic for heel raise in cradle
                thickness_key = f"{key} thickness"
                thickness_str = content_dict.get(thickness_key, '')
                thickness_match = re.search(r'\d+\.?\d*', thickness_str)
                if thickness_match:
                    thickness = float(thickness_match.group())
                    if thickness > 0:
                        passed_codes['A10'] += 2
                        if thickness > 25:
                            excess = thickness - 25
                            a9_count = math.ceil(excess / 25)
                            passed_codes['A9'] += a9_count * 2
            else:
                # Existing mapping logic
                if addition_value in addition_code_mapping['A45_B41']:
                    code = 'A45' if insole_type == 'cradle' else 'B41'
                    passed_codes[code] += 2
                elif addition_value in addition_code_mapping['A45_B56']:
                    code = 'A45' if insole_type == 'cradle' else 'B56'
                    passed_codes[code] += 2
                elif addition_value in addition_code_mapping['A45_B43']:
                    code = 'A45' if insole_type == 'cradle' else 'B43'
                    passed_codes[code] += 2
                elif addition_value in addition_code_mapping['D8A']:
                    passed_codes['D8A'] += 2
                elif addition_value in addition_code_mapping['BNS45']:
                    passed_codes['BNS45'] += 2
                elif addition_value in addition_code_mapping['A20_B20']:
                    code = 'A20' if insole_type == 'cradle' else 'B20'
                    passed_codes[code] += 2
                elif addition_value in addition_code_mapping['A46_B50']:
                    code = 'A46' if insole_type == 'cradle' else 'B50'
                    passed_codes[code] += 2
                elif addition_value in addition_code_mapping['A47_B51']:
                    code = 'A47' if insole_type == 'cradle' else 'B51'
                    passed_codes[code] += 2

    # Foot modifications
    foot_modifications = [
        'cut out and additions',
        '1st met head',
        '1st met ray',
        '5th met ray',
        'navicular sweet spot',
        'fascial accommodation',
        'heel flange'
    ]

    for side in ['left', 'right']:
        for mod in foot_modifications:
            key = f"{side} {mod}"
            if content_dict.get(key, '') == 'selected':
                passed_codes['BNS45'] += 2

    posting_keys = [
        'left medial rearfoot posting',
        'left lateral rearfoot posting',
        'right medial rearfoot posting',
        'right lateral rearfoot posting',
        'left medial forefoot posting',
        'left lateral forefoot posting',
        'right medial forefoot posting',
        'right lateral forefoot posting'
    ]

    for key in posting_keys:
        if content_dict.get(key, '') == 'selected':
            code = 'A45' if insole_type == 'cradle' else 'B56'
            passed_codes[code] += 2

    # Sole Stiffeners
    stiffener_keys = {
        'sole stiffeners left carbon fibre': 'A20',
        'sole stiffeners right carbon fibre': 'A20',
        'sole stiffeners left steel': 'A22',
        'sole stiffeners right steel': 'A22'
    }

    for key, code in stiffener_keys.items():
        if content_dict.get(key, '') == 'selected':
            passed_codes[code] += 2

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
    for side in ['left', 'right']:
        ankle_height_key = f'{side} ankle height'
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

    if content_dict.get('fastening', '') == 'boa':
        passed_codes['TWIST FASTEN'] += 2

    if content_dict.get('lining material', '') == 'white sheepskin':
        passed_codes['A18A'] += 2

    # A6 handling: 1.0 for pairs, 0.5 for singles
    if content_dict.get('sole material', '') == 'commando':
        passed_codes['A6'] += 1.0

    stiffeners_materials = {
        'stiffeners left materials': 'A15',
        'stiffeners right materials': 'A15'
    }

    for key, code in stiffeners_materials.items():
        if content_dict.get(key, '') in ('grey poron', 'pink poron', 'foam'):
            passed_codes[code] += 2

    # Stiffeners Checks
    # Left side
    left_a16_count = 0
    if content_dict.get('stiffeners left medial', '') == 'selected':
        left_a16_count += 1
    if content_dict.get('stiffeners left lateral', '') == 'selected':
        left_a16_count += 1

    if content_dict.get('stiffeners left type', '') in ('elongated', 'high'):
        if left_a16_count > 1:
            left_a16_count = 1
    if left_a16_count > 0:
        passed_codes['A16'] += left_a16_count * 2

    # Right side
    right_a16_count = 0
    if content_dict.get('stiffeners right medial', '') == 'selected':
        right_a16_count += 1
    if content_dict.get('stiffeners right lateral', '') == 'selected':
        right_a16_count += 1

    if content_dict.get('stiffeners right type', '') in ('elongated', 'high'):
        if right_a16_count > 1:
            right_a16_count = 1
    if right_a16_count > 0:
        passed_codes['A16'] += right_a16_count * 2

    sockets_type_a = {
        'left socket type': 'A37A',
        'right socket type': 'A37A'
    }

    for key, code in sockets_type_a.items():
        if content_dict.get(key, '') in (
            '5/16 round socket', '1/4inc round socket', 'small rectangular', 'large rectangular', 'rizzoli'
        ):
            passed_codes[code] += 2

    sockets_type_b = {
        'left socket type': 'A37B',
        'right socket type': 'A37B'
    }

    for key, code in sockets_type_b.items():
        if content_dict.get(key, '') in ('5/16 with backstop', '1/4 with backstop'):
            passed_codes[code] += 2

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

    # Raises - to do the 25mm+ codes 
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
    elongations_keys = ['left elongations type', 'right elongations type']
    for key in elongations_keys:
        if content_dict.get(key, '') in ('full', 'half'):
            passed_codes['A31'] += 2

    # Rocker
    rocker_keys = ['left rocker type', 'right rocker type']
    for key in rocker_keys:
        if content_dict.get(key, '') in ('plr', 'standard', 'two point'):
            passed_codes['A19'] += 2

    # Straps
    for side in ['left', 'right']:
        strap_type_key = f'{side} strap type'
        strap_type = content_dict.get(strap_type_key, '')
        if strap_type in ('t strap', 'y strap'):
            if content_dict.get(f'{side} double decker', '') == 'selected':
                passed_codes['A39'] += 2
            else:
                passed_codes['A38'] += 2
        elif strap_type in ('spur retaining strap', 'heel retaining strap'):
            passed_codes['A40'] += 2

    # Insole coding section - MATHS!
    x = 1
    if insole_type == 'simple':
        x -= 1
    if content_dict.get('insole top cover length', '') == 'not required':
        x -= 1
    if content_dict.get('lining to shell', '') == 'selected':
        x += 1
    if content_dict.get('lining to sulcus', '') == 'selected':
        x += 1
    if content_dict.get('lining full', '') == 'selected':
        x += 1
    if content_dict.get('insole top cover material', '') == 'spenco (green)':
        x += 1
    if content_dict.get('base', '') in ('35/20/80 sh', '45/30/80 sh'):
        x += 1

    if x >= 3:
        code = 'A44C' if insole_type == 'cradle' else 'B55C'
        passed_codes[code] += 2
    elif x == 2:
        code = 'A44B' if insole_type == 'cradle' else 'B55B'
        passed_codes[code] += 2
    elif x == 1:
        code = 'A44A' if insole_type == 'cradle' else 'B55A'
        passed_codes[code] += 2

    normalized_base = base.replace(' ', '').lower()
    shore_bases = {'40shore', '50shore', '65shore', '35/20/80sh', '45/30/80sh'}

    if insole_type == 'cradle':
        if normalized_base in shore_bases:
            passed_codes['A10'] += 2
        elif normalized_base == 'polypropylene':
            passed_codes['A10'] += 2
    elif insole_type in ('tci', 'simple', 'handmould'):
        if normalized_base == 'polypropylene':
            passed_codes['B54B'] += 2
        else:
            passed_codes['B54C'] += 2

    if content_dict.get('base poron', '') == 'selected':
        passed_codes['B40B'] += 2
    if content_dict.get('base carbon fibre', '') == 'selected':
        passed_codes['B54A'] += 2

    foot_modifications = [
        'cut out and additions', '1st met head', '1st met ray', '5th met ray',
        'navicular sweet spot', 'fascial accommodation', 'heel flange'
    ]
    for side in ['left', 'right']:
        for mod in foot_modifications:
            key = f"{side} {mod}"
            if content_dict.get(key, '') == 'selected':
                passed_codes['BNS45'] += 2

    posting_keys = [
        'left medial rearfoot posting', 'left lateral rearfoot posting',
        'right medial rearfoot posting', 'right lateral rearfoot posting',
        'left medial forefoot posting', 'left lateral forefoot posting',
        'right medial forefoot posting', 'right lateral forefoot posting'
    ]
    for key in posting_keys:
        if content_dict.get(key, '') == 'selected':
            code = 'A45' if insole_type == 'cradle' else 'B56'
            passed_codes[code] += 2

    # Insole coding section - MATHS!
    x = 1
    print(f"Initial value: x = {x}")

    if insole_type == 'simple':
        x -= 1
        print(f"After insole_type 'simple' check: x = {x}")
    if content_dict.get('insole top cover length', '') == 'not required':
        x -= 1
    if content_dict.get('lining to shell', '') == 'selected':
        x += 1
    if content_dict.get('lining to sulcus', '') == 'selected':
        x += 1
    if content_dict.get('lining full', '') == 'selected':
        x += 1
    if content_dict.get('insole top cover material', '') == 'spenco (green)':
        x += 1
        print(f"After spenco check: x = {x}")

    if content_dict.get('base', '') in ('35/20/80 sh', '45/30/80 sh'):
        x += 1
        print(f"After base check: x = {x}")

    if x >= 3:
        passed_codes['B55C'] += 2
        print(f"x >= 3, incrementing B55C: {passed_codes['B55C']}")
    elif x == 2:
        passed_codes['B55B'] += 2
        print(f"x == 2, incrementing B55B: {passed_codes['B55B']}")
    elif x == 1:
        passed_codes['B55A'] += 2
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
        passed_codes[chosen_tariff] += 2
        # Remove all non-tariff codes (all except chosen_tariff)
        for code in list(passed_codes.keys()):
            if code != chosen_tariff:
                del passed_codes[code]
    else:
        # Normal pair handling if not CLCH simple
        codes_to_double_insole = ['B54C', 'B40B', 'B54A', 'B55A', 'B55B', 'B55C', 'B54B']
        for code in codes_to_double_insole:
            if code in passed_codes:
                passed_codes[code] *= 2

    # --- Final Filtering Step ---
    insole_filter_codes = {
        'A10', 'B54C', 'B40B', 'B54A', 'A44A', 'A44B', 'A44C',
        'B55A', 'B55B', 'B55C', 'B56', 'A45', 'BNS45', 'A47',
        'B51', 'B50', 'A46', 'A20', 'B20', 'D8A', 'B43', 'B41'
    }
    # Define Wales-specific insole filter (same as insole_filter_codes but without 'B20')
    wales_insole_filter_codes = insole_filter_codes.copy()
    wales_insole_filter_codes.discard('B20')

    bespoke_filter_codes = {
        'A1B', 'A1A', 'A1K', 'A22', 'A23', 'A24', 'A25',
        'TWIST FASTEN', 'A18A', 'A6', 'A15', 'A16', 'A37A',
        'A37B', 'A31', 'A19', 'A26', 'A8', 'A13A', 'A12A',
        'A39', 'A38', 'A40', 'B54B'
    }
    # If insole tariff selected, remove insole_filter_codes
    if insole_tariff_added:
        # Use Wales-specific filter if applicable, else standard
        filter_set = wales_insole_filter_codes if customer_no in tariff_wales_customer_nos else insole_filter_codes
        for c in filter_set:
            if c in passed_codes:
                del passed_codes[c]
    # If bespoke tariff selected, remove bespoke_filter_codes
    if bespoke_tariff_added:
        for c in bespoke_filter_codes:
            if c in passed_codes:
                del passed_codes[c]

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
    
def generate_insole_codes(self, content):
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

    # --- Medway Tariff Logic ---
    if customer_no in tariff_medway_customer_nos:
        if insole_type == 'simple':
            passed_codes['MEDBNS71'] += 1
            if is_pair:
                passed_codes['MEDBNS71'] *= 2
            return 'MEDBNS71' if passed_codes['MEDBNS71'] == 1 else f'MEDBNS71 x{passed_codes["MEDBNS71"]}'
        else:
            passed_codes['MEDBNS72'] += 1
            if is_pair:
                passed_codes['MEDBNS72'] *= 2
            return 'MEDBNS72' if passed_codes['MEDBNS72'] == 1 else f'MEDBNS72 x{passed_codes["MEDBNS72"]}'

    # Wales Tariff Logic for Insoles
    if customer_no in tariff_wales_customer_nos:
        if selected_base == 'poly':
            passed_codes['WALES-POLYPROP'] += 1
            if is_pair:
                passed_codes['WALES-POLYPROP'] *= 2
            return 'WALES-POLYPROP' if passed_codes['WALES-POLYPROP'] == 1 else f'WALES-POLYPROP x{passed_codes["WALES-POLYPROP"]}'
        elif insole_type == 'simple':
            passed_codes['WALES-SIMPLE'] += 1
            if is_pair:
                passed_codes['WALES-SIMPLE'] *= 2
            return 'WALES-SIMPLE' if passed_codes['WALES-SIMPLE'] == 1 else f'WALES-SIMPLE x{passed_codes["WALES-SIMPLE"]}'
        elif insole_type in ('tci', 'cradle'):
            passed_codes['WALES-TCI'] += 1
            if is_pair:
                passed_codes['WALES-TCI'] *= 2
            return 'WALES-TCI' if passed_codes['WALES-TCI'] == 1 else f'WALES-TCI x{passed_codes["WALES-TCI"]}'

    # Now unify the three tariff checks in a single block:

    # 1) If the customer_no allows polyprop & selected_base == 'poly'
    if customer_no in tariff_polyprop_customer_nos and selected_base == 'poly':
        passed_codes['TARIFF POLYPROPS'] += 1
        if is_pair:
            passed_codes['TARIFF POLYPROPS'] *= 2
        return (
            'TARIFF POLYPROPS'
            if passed_codes['TARIFF POLYPROPS'] == 1
            else f"TARIFF POLYPROPS x{passed_codes['TARIFF POLYPROPS']}"
        )

    # 2) Else if the customer_no allows "simple" & insole_type == 'simple'
    elif customer_no in tariff_simple_customer_nos and insole_type == 'simple':
        passed_codes['TARIFF SIMPLE INSOLE'] += 1
        if is_pair:
            passed_codes['TARIFF SIMPLE INSOLE'] *= 2
        return (
            'TARIFF SIMPLE INSOLE'
            if passed_codes['TARIFF SIMPLE INSOLE'] == 1
            else f"TARIFF SIMPLE INSOLE x{passed_codes['TARIFF SIMPLE INSOLE']}"
        )

    # 3) Else if the customer_no is in the TCI list
    elif customer_no in tariff_tci_customer_nos:
        passed_codes['TARIFF TCI\'S'] += 1
        if is_pair:
            passed_codes['TARIFF TCI\'S'] *= 2
        return (
            'TARIFF TCI\'S'
            if passed_codes['TARIFF TCI\'S'] == 1
            else f"TARIFF TCI\'S x{passed_codes['TARIFF TCI\'S']}"
        )

    # If we get here, then the clinic isn't in any of those lists, or no conditions matched:
    # Continue with your normal "base logic" here.

    # Normal logic if no immediate tariff matched
    passed_codes = defaultdict(int)

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

    # Format output
    formatted_passed_codes = []
    for code, count in passed_codes.items():
        if count > 1:
            formatted_passed_codes.append(f"{code} x{count}")
        else:
            formatted_passed_codes.append(code)

    if formatted_passed_codes:
        return ', '.join(f"{code} x{count}" if count > 1 else code for code, count in passed_codes.items())
    else:
        return None
            
def generate_afo_codes(self, content):
    """Generates codes based on the content for the AFO model, counting duplicates."""
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

    # --- New Medway Tariff ---
    if customer_no in tariff_medway_customer_nos:
        passed_codes['MEDDNS2'] += 1
        if is_pair:
            passed_codes['MEDDNS2'] *= 2
        return 'MEDDNS2' if passed_codes['MEDDNS2'] == 1 else f'MEDDNS2 x{passed_codes["MEDDNS2"]}'

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
        return None  # Return None if no codes were added
    
def generate_modular_codes(self, content):
    """Generates codes based on the content for the Modular model, with tariff logic."""
    passed_codes = defaultdict(int)  # Use defaultdict to count occurrences

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
    # Check if it's a pair
    is_pair = (content_dict.get('pair', '') == 'selected' or 
               content_dict.get('insole pair', '') == 'selected')

    # Determine insole type for modular logic
    insole_type = None
    if content_dict.get('insole type tci', '') == 'selected':
        insole_type = 'tci'
    elif content_dict.get('insole type cradle', '') == 'selected':
        insole_type = 'cradle'
    elif content_dict.get('insole type simple', '') == 'selected':
        insole_type = 'simple'
    elif content_dict.get('insole type handmould', '') == 'selected':
        insole_type = 'handmould'

    # Get the base value for polyprop check
    base = content_dict.get('base', '').strip().lower()
    normalized_base = base.replace(' ', '').lower()

    # Variables to track tariffs
    modular_tariff_added = False
    insole_tariff_added = False

    # --- Medway Tariffs for Modular ---
    if customer_no in tariff_medway_customer_nos:
        if insole_type == 'simple':
            passed_codes['MEDBNS71'] += 1
        else:
            passed_codes['MEDBNS72'] += 1
        passed_codes['MEDFOOTWEAR'] += 1
        modular_tariff_added = True
        insole_tariff_added = True

    # Wales Tariff Check for Modular
    if customer_no in tariff_wales_customer_nos:
        passed_codes['WALES-MODULAR'] += 1
        modular_tariff_added = True

    # Wales Insole Tariff Checks
    if customer_no in tariff_wales_customer_nos:
        if insole_type in ('tci', 'cradle'):
            passed_codes['WALES-TCI'] += 1
            if is_pair:
                passed_codes['WALES-TCI'] *= 2
            insole_tariff_added = True
        elif insole_type == 'simple':
            passed_codes['WALES-SIMPLE'] += 1
            if is_pair:
                passed_codes['WALES-SIMPLE'] *= 2
            insole_tariff_added = True
        elif insole_type == 'handmould':
            passed_codes['WALES-POLYPROP'] += 1
            if is_pair:
                passed_codes['WALES-POLYPROP'] *= 2
            insole_tariff_added = True

    # Modular Tariff Check (other clinics)
    if customer_no in tariff_modular_customer_nos:
        passed_codes['TARIFF MODULAR'] += 1
        modular_tariff_added = True

    # Insole Tariff Checks
    if customer_no in tariff_tci_customer_nos:
        passed_codes['TARIFF TCI\'S'] += 1
        insole_tariff_added = True
    elif customer_no in tariff_simple_customer_nos:
        passed_codes['TARIFF SIMPLE INSOLE'] += 1
        insole_tariff_added = True
    elif customer_no in tariff_polyprop_customer_nos:
        passed_codes['TARIFF POLYPROPS'] += 1
        insole_tariff_added = True

    # Last Type Checks
    if content_dict.get('last type', '').strip().lower() == 'wide extra deep':
        count = 1
        if is_pair:
            count = 2
        passed_codes['6MM'] += count

    # Insole Allowance Checks - Updated logic to use the maximum code for pairs
    allowance_codes = {'3MM', '6MM', '9MM', '12MM'}
    pattern_allowances = {'9MM', '12MM'}
    allowance_order = ['3MM', '6MM', '9MM', '12MM']

    left_code = None
    right_code = None

    for side in ['left', 'right']:
        allowance_key = f'{side} insole allowance'
        addition_length_key = f'{side} addition option 1 length'
        value = content_dict.get(allowance_key, '') or content_dict.get(addition_length_key, '')
        if value:
            code = value.upper().replace('MM', 'MM')
            if code in allowance_codes:
                if side == 'left':
                    left_code = code
                else:
                    right_code = code

    if is_pair and left_code and right_code:
        max_code = max(left_code, right_code, key=allowance_order.index)
        passed_codes[max_code] += 2
        if max_code in pattern_allowances:
            passed_codes['PATTERN'] += 2
    elif left_code:
        passed_codes[left_code] += 1
        if left_code in pattern_allowances:
            passed_codes['PATTERN'] += 1
    elif right_code:
        passed_codes[right_code] += 1
        if right_code in pattern_allowances:
            passed_codes['PATTERN'] += 1

    # Sole and Style Checks
    sole_value = content_dict.get('sole', '')
    style_value = content_dict.get('styles', '')

    if sole_value in ('(lcr) lightweight commando sole', 'resin commando sole'):
        if style_value not in ('highland', 'rockingham', 'rockcliffe'):
            passed_codes['BNS62'] += 1

    style = content_dict.get('styles', '').lower()

    sport_styles = {'sneaker', 'greenock', 'greeock', 'colwyn', 'lineham', 'hove', 'plymouth', 
                    'drayton', 'olympic', 'melton', 'kelso', 'dover', 'shelwyck', 'mowbray'} 
    shoe_styles = {'trent', 'selby', 'hallam', 'totnes', 'tenby', 'chelsea', 'galway', 'vienna',
                   'truro', 'hendon', 'stirling', 'exeter', 'chester', 'shelby'}
    boot_styles = {'bumper', 'whitby', 'tralee', 'rockingham', 'perth', 'rockliffe',
                   'dundee', 'brigg', 'elgin', 'highland'}

    if style in sport_styles:
        passed_codes['MODULAR SPORTS'] += 1
    elif style in shoe_styles:
        passed_codes['MODULAR SHOES'] += 1
    elif style in boot_styles:
        passed_codes['MODULAR BOOTS'] += 1
    else:
        fallback_styles_used = []
        if content_dict.get('shoes', '') == 'selected':
            passed_codes['MODULAR SHOES'] += 1
            fallback_styles_used.append('shoes')
        if content_dict.get('boots', '') == 'selected':
            passed_codes['MODULAR BOOTS'] += 1
            fallback_styles_used.append('boots')
        if content_dict.get('trainers', '') == 'selected':
            passed_codes['MODULAR SPORTS'] += 1
            fallback_styles_used.append('trainers')

        if fallback_styles_used:
            warning_message = (
                f"Footwear style not detected!\n"
                f"• Entered style: '{style}' may be spelled incorrectly.\n"
                f"• Falling back to tick-box selections: {', '.join(fallback_styles_used)}"
            )
            self.root.after(0, self.append_and_show_info, "Warning", warning_message)
        else:
            warning_message = (
                f"Footwear style '{style}' not recognized, and no tick boxes selected. "
                f"Please verify the footwear style."
            )
            self.root.after(0, self.append_and_show_info, "Warning", warning_message)

    # Check boa/velcro 
    if content_dict.get('boa', '') == 'selected':
        passed_codes['TWIST FASTEN'] += 1
    if content_dict.get('VELCRO', '') == 'selected':
        passed_codes['VELCRO'] += 1

    # Straps Checks
    for side in ['left', 'right']:
        strap_position_key = f'{side} strap position'
        strap_position = content_dict.get(strap_position_key, '')
        if strap_position == 'double decker':
            passed_codes['B34'] += 1

    # Sockets Type Checks
    socket_keys = ['left socket type', 'right socket type']
    for key in socket_keys:
        value = content_dict.get(key, '')
        if value in ('5/16 round', '1/4 round', 'small rectangular', 'large rectangular', 'rizzoli'):
            passed_codes['B30'] += 1
        elif value in ("5/16 with b'stop", "1/4 with b'stop"):
            passed_codes['B31'] += 1

    # Elongation Type (B25)
    elongation_keys = ['left elongation type', 'right elongation type']
    for key in elongation_keys:
        if content_dict.get(key, '') in ('full', 'half'):
            passed_codes['B25'] += 1

    # Rocker
    rocker_keys = ['left rocker type', 'right rocker type']
    for key in rocker_keys:
        if content_dict.get(key, '') in ('plr', 'standard', 'two point'):
            passed_codes['B17'] += 1

    # Wedges
    wedges_keys = [
        'left wedges heel lateral', 'left wedges heel medial', 'right wedges heel medial',
        'right wedges heel lateral', 'left wedges sole lateral', 'left wedges sole medial',
        'right wedges sole medial', 'right wedges sole lateral'
    ]
    for key in wedges_keys:
        if content_dict.get(key, '') == 'selected':
            if 'heel' in key:
                passed_codes['B25'] += 1
            elif 'sole' in key:
                passed_codes['B17'] += 1

    # Floated
    floated_keys = [
        'right floated heel lateral', 'right floated heel medial', 'left floated heel medial',
        'left floated heel lateral', 'left floated sole lateral', 'left floated sole medial',
        'right floated sole lateral', 'right floated sole medial'
    ]
    for key in floated_keys:
        if content_dict.get(key, '') == 'selected':
            if 'heel' in key:
                passed_codes['B25'] += 1
            elif 'sole' in key:
                passed_codes['B26'] += 1

    # Insole logic
    shore_bases = {'40shore', '50shore', '65shore', '35/20/80sh', '45/30/80sh'}
    if insole_type == 'cradle':
        if normalized_base in shore_bases:
            passed_codes['A10'] += 1
        elif normalized_base == 'polypropylene':
            passed_codes['A10'] += 1
    elif insole_type in ('tci', 'simple', 'handmould'):
        if normalized_base == 'polypropylene':
            passed_codes['B54B'] += 1
        else:
            passed_codes['B54C'] += 1

    if content_dict.get('base poron', '') == 'selected':
        passed_codes['B40B'] += 1
    if content_dict.get('base carbon fibre', '') == 'selected':
        passed_codes['B54A'] += 1

    foot_modifications = [
        'cut out and additions', '1st met head', '1st met ray', '5th met ray',
        'navicular sweet spot', 'fascial accommodation', 'heel flange'
    ]
    for side in ['left', 'right']:
        for mod in foot_modifications:
            key = f"{side} {mod}"
            if content_dict.get(key, '') == 'selected':
                passed_codes['BNS45'] += 1

    addition_positions = [
        'left 1st addition', 'left 2nd addition', 'left 3rd addition', 'left 4th addition',
        'right 1st addition', 'right 2nd addition', 'right 3rd addition', 'right 4th addition'
    ]
    addition_code_mapping = {
        'A45_B41': {'valgus pad', 'metatarsal pad', 'metatarsal bar', 'balance pad',
                    'heel pad', 'cuboid pad', 'cobra pad', 'neuroma pad', 'sulcus crest', 'arch fill'},
        'A45_B56': {"morton's extension", "reverse morton's extension", 'poron forefoot'},
        'A45_B43': {'kinetic wedge', 'heel raise'},
        'D8A': {'neurological footplate'},
        'BNS45': {'recess', 'hole & plug'},
        'A20_B20': {'rigid 1st extension'},
        'A46_B50': {'partial toe block'},
        'A47_B51': {'full toe block'}
    }
    for key in addition_positions:
        addition_value = content_dict.get(key, '')
        if addition_value:
            if addition_value in addition_code_mapping['A45_B41']:
                code = 'A45' if insole_type == 'cradle' else 'B41'
                passed_codes[code] += 1
            elif addition_value in addition_code_mapping['A45_B56']:
                code = 'A45' if insole_type == 'cradle' else 'B56'
                passed_codes[code] += 1
            elif addition_value in addition_code_mapping['A45_B43']:
                code = 'A45' if insole_type == 'cradle' else 'B43'
                passed_codes[code] += 1
            elif addition_value in addition_code_mapping['D8A']:
                passed_codes['D8A'] += 1
            elif addition_value in addition_code_mapping['BNS45']:
                passed_codes['BNS45'] += 1
            elif addition_value in addition_code_mapping['A20_B20']:
                code = 'A20' if insole_type == 'cradle' else 'B20'
                passed_codes[code] += 1
            elif addition_value in addition_code_mapping['A46_B50']:
                code = 'A46' if insole_type == 'cradle' else 'B50'
                passed_codes[code] += 1
            elif addition_value in addition_code_mapping['A47_B51']:
                code = 'A47' if insole_type == 'cradle' else 'B51'
                passed_codes[code] += 1

    posting_keys = [
        'left medial rearfoot posting', 'left lateral rearfoot posting',
        'right medial rearfoot posting', 'right lateral rearfoot posting',
        'left medial forefoot posting', 'left lateral forefoot posting',
        'right medial forefoot posting', 'right lateral forefoot posting'
    ]
    for key in posting_keys:
        if content_dict.get(key, '') == 'selected':
            code = 'A45' if insole_type == 'cradle' else 'B56'
            passed_codes[code] += 1

    # Insole coding section - MATHS!
    x = 1
    print(f"Initial value: x = {x}")

    if insole_type == 'simple':
        x -= 1
        print(f"After insole_type 'simple' check: x = {x}")
    if content_dict.get('insole top cover length', '') == 'not required':
        x -= 1
    if content_dict.get('lining to shell', '') == 'selected':
        x += 1
    if content_dict.get('lining to sulcus', '') == 'selected':
        x += 1
    if content_dict.get('lining full', '') == 'selected':
        x += 1

    if content_dict.get('insole top cover material', '') == 'spenco (green)':
        x += 1
        print(f"After spenco check: x = {x}")

    if content_dict.get('base', '') in ('35/20/80 sh', '45/30/80 sh'):
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

    # --- Final Filtering Step ---
    insole_filter_codes = {
        'A10', 'B54C', 'B40B', 'B54A', 'A44A', 'A44B', 'A44C',
        'B55A', 'B55B', 'B55C', 'B56', 'A45', 'BNS45', 'A47',
        'B51', 'B50', 'A46', 'A20', 'B20', 'D8A', 'B43', 'B41', 'B54B'
    }
    # Define Wales-specific insole filter (same as insole_filter_codes but without 'B20')
    wales_insole_filter_codes = insole_filter_codes.copy()
    wales_insole_filter_codes.discard('B20')

    modular_filter_codes = {
        '6MM', 'PATTERN', 'BNS62', 'MODULAR SHOES', 'MODULAR BOOTS',
        'MODULAR SPORTS', 'TWIST FASTEN', 'VELCRO', 'B34', 'B33', 'B8',
        'B30', 'B31', 'B25', 'B17', 'B18', 'B19'
    }
    if insole_tariff_added:
        # Use Wales-specific filter if applicable, else standard
        filter_set = wales_insole_filter_codes if customer_no in tariff_wales_customer_nos else insole_filter_codes
        for c in filter_set:
            if c in passed_codes:
                del passed_codes[c]
          
    if modular_tariff_added:
        for c in modular_filter_codes:
            if c in passed_codes:
                del passed_codes[c]

    # Format output
    formatted_passed_codes = []
    for code, count in passed_codes.items():
        if count > 1:
            formatted_passed_codes.append(f"{code} x{count}")
        else:
            formatted_passed_codes.append(code)

    if formatted_passed_codes:
        return ', '.join(f"{code} x{count}" if count > 1 else code for code, count in passed_codes.items())
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