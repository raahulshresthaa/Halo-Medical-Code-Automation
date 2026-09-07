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
    'GB-CUST02295', 'GB-CUST02554', 'GB-CUST02583', 'GB-CUST02836'
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

# Shared socket type lists (bespoke A37A/A37B and modular B30/B31)
TYPE_A_SOCKETS = ['5/16 round', '1/4 round', '3/16x9/16', 'rizzoli']
TYPE_B_SOCKETS = ['5/16 backstop', '1/4 backstop']

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

def parse_content_dict(content):
    """Parse key:value content lines into a lowercase dict.

    Lines without ':' are dropped; keys and values are stripped and lowercased;
    if a key appears more than once, the last value wins.
    """
    content_dict = {}
    for line in content.split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            content_dict[key.strip().lower()] = value.strip().lower()
    return content_dict


def parse_order_quantity(content_dict):
    """Return how many of this device to make. Missing or junk values count as 1.

    A pair is still quantity 1 (one pair). Quantity 2 means two copies of the
    whole prescription, not 'it is a pair'.
    """
    raw = content_dict.get('order quantity', '').strip().lower()
    if not raw:
        return 1
    raw = raw.replace('x', '').strip()
    try:
        qty = int(float(raw))
    except ValueError:
        print(f"Could not parse order quantity '{content_dict.get('order quantity', '')}'; treating as 1")
        return 1
    if qty < 1:
        return 1
    return qty


def apply_order_quantity(passed_codes, content_dict):
    """Multiply every code by order quantity when it is greater than 1.

    Mutates passed_codes in place and returns it. Quantity 1, missing, or
    unparseable is a no-op. Call this once on the finished code dict of the
    outermost generator (after pair/tariff logic, after any nested insole
    merge) so nested generate_insole_codes(..., return_dict=True) does not
    apply it as well.
    """
    order_qty = parse_order_quantity(content_dict)
    print(f"Order quantity: {order_qty}")
    if order_qty > 1:
        print(f"Order quantity {order_qty}: multiplying all codes")
        for code in list(passed_codes.keys()):
            passed_codes[code] *= order_qty
    return passed_codes


# Matches a code as <optional letters><number><optional letters>, e.g.
# D1C -> ('D', '1', 'C'), DNS6 -> ('DNS', '6', ''), B43 -> ('B', '43', ''), P15 -> ('P', '15', '').
_CODE_PARTS_RE = re.compile(r'^[A-Za-z]*?(\d+)([A-Za-z]*)$')


def code_sort_key(code):
    """Sort key ordering codes by NUMBER first, then the letter(s) after the number.

    The leading letter is deliberately ignored, so the order is e.g.
    D1C, D2A, D2B, DNS6, D8U, D10E, D10I, D12M, D14A, D14C, P15, B43.
    Note this is a numeric sort - a plain string sort would wrongly put D10E
    before D1C and D8U.

    Codes with no number in them (e.g. 'WALES-AFO', 'TARIFF AFO') can't be
    ordered this way, so they are grouped at the end in alphabetical order
    rather than raising. The trailing `code` element keeps the sort stable and
    deterministic if two codes share a number and suffix.
    """
    match = _CODE_PARTS_RE.match(str(code).strip())
    if not match:
        return (1, 0, '', str(code))
    return (0, int(match.group(1)), match.group(2).upper(), str(code))


# A field belonging to one side is written either side-first ("right arch pads") or
# side-last ("nc pf right"). Both shapes have to be handled or the count comes out low.
def _side_fields(content_dict, side):
    """The set of field names filled in for one side, with the side word stripped off."""
    names = set()
    for key, value in content_dict.items():
        if not str(value).strip():
            continue
        if key.startswith(side + ' '):
            names.add(key[len(side) + 1:])
        elif key.endswith(' ' + side):
            names.add(key[:-(len(side) + 1)])
    return names


# 3 or more matched fields means a pair. On the 40 AFO forms on file, genuine single-leg
# forms score 0 or 1 and the one misread pair scores 13, so the line sits in a wide gap.
MIRRORED_FIELD_PAIR_THRESHOLD = 3


def detect_missed_pair(content_dict, content=''):
    """Spot a pair whose Pair tick box was not read correctly.

    The form has three boxes - Pair, Rt and Lt. The reader can put the tick on the wrong
    one (F1460463 was read as 'afo rt' when the work ticket said "HARD PR GRAFO'S"), and
    because is_pair doubles nearly every AFO code, that halves the whole order.

    Two independent checks, either of which is enough:
      1. the same field is filled in for BOTH sides several times over - a brace made for
         one leg only ever has that leg's measurements filled in;
      2. "PR CASTS" (PR = pair) appears in the text - rarer, but it catches a pair that
         has barely any measurements on it, which check 1 would miss. It has to be read
         from the raw text: the reader writes "Article Number ::" and puts the value on
         the NEXT line, so parse_content_dict drops it.

    Returns a short reason for the code checker, or None if nothing looks wrong. This
    only ever reports a MISSED pair; it can't tell that a ticked Pair box is wrong.
    """
    # Nothing to spot if the form already says it's a pair. Checked here rather than at
    # each call site so a caller can't forget it and warn on every genuine pair.
    if (content_dict.get('pair', '') == 'selected'
            or content_dict.get('afo pair', '') == 'selected'):
        return None

    matched = _side_fields(content_dict, 'left') & _side_fields(content_dict, 'right')
    if len(matched) >= MIRRORED_FIELD_PAIR_THRESHOLD:
        return (f"{len(matched)} measurements are filled in for both legs "
                f"({', '.join(sorted(matched)[:4])}...), but the form is not marked as a pair")

    if re.search(r'\bPR\s+CASTS\b', content or '', re.IGNORECASE):
        return "the form says 'PR CASTS' (PR = pair), but it is not marked as a pair"

    return None


def merge_code_strings(code_strings):
    """Add up several "CODE xN, CODE xM" strings into one, in the standard order.

    Used when a single PDF holds more than one prescription form and the results are
    combined into one order. The forms' extractions cannot simply be merged - both use
    the same field names, so they would overwrite each other - so each form's codes are
    generated separately and the quantities are summed here.
    """
    totals = defaultdict(int)
    for code_string in code_strings:
        for part in (code_string or '').split(','):
            part = part.strip()
            if not part:
                continue
            match = re.match(r'^(.*?)\s*[xX]\s*(\d+)$', part)
            if match:
                totals[match.group(1).strip()] += int(match.group(2))
            else:
                totals[part] += 1
    merged = []
    for code in sorted(totals, key=code_sort_key):
        count = totals[code]
        merged.append(f"{code} x{count}" if count > 1 else code)
    return ', '.join(merged)

def generate_bespoke_codes(self, content):
    """Generates codes based on the content for the Bespoke model, counting duplicates."""
    passed_codes = defaultdict(float)  # Use float to allow fractional counts

    content_dict = parse_content_dict(content)

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
        passed_codes['A1A'] += 1
    elif style in a1b_styles:
        passed_codes['A1B'] += 1
    else:
        passed_codes['A1A'] += 1  # Default to A1A if no style matches

    # Add logic for 'pop cast'
    if content_dict.get('pop cast', '') == 'selected':
        passed_codes['A1K'] += 2

    # Stiffeners Checks
    for side in ['left', 'right']:
        print(f"Checking stiffeners for side: {side}")
        a20_count = 0
        for typ in ['high', 'elongated']:
            for pos in ['medial', 'lateral']:
                key = f'stiffener {typ} {side} {pos}'
                value = content_dict.get(key, '')
                print(f"Checking key '{key}': value = '{value}'")
                if value == 'selected':
                    a20_count += 1
                    print(f"Incrementing a20_count for {key}")
        print(f"Pre-cap a20_count for {side}: {a20_count}")
        if a20_count > 1:
            a20_count = 1
            print(f"Capped a20_count to 1 for {side}")
        if a20_count > 0:
            passed_codes['A20'] += a20_count
            print(f"Added to A20: {a20_count} (total now: {passed_codes['A20']})")

        padded_key = f'stiffener padded {side}'
        padded_value = content_dict.get(padded_key, '')
        print(f"Checking padded key '{padded_key}': value = '{padded_value}'")
        if padded_value == 'selected':
            passed_codes['A15'] += 1
            print(f"Added A15 for {padded_key}")

        elongated_lateral_key = f'stiffener elongated {side} lateral'
        elongated_lateral_value = content_dict.get(elongated_lateral_key, '')
        if elongated_lateral_value == 'selected':
            passed_codes['A16'] += 1

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
        has_type_a = any(content_dict.get(f'{side} {socket}', '') == 'selected' for socket in TYPE_A_SOCKETS)
        has_type_b = any(content_dict.get(f'{side} {socket}', '') == 'selected' for socket in TYPE_B_SOCKETS)

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

    apply_order_quantity(passed_codes, content_dict)

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

    content_dict = parse_content_dict(content)

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
    if content_dict.get('insole type tci', '') == 'selected' or content_dict.get('insole type cradle', '') == 'selected':
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
            left_keys = [f"left {mod}", f"left {mod} cut outs"]
            right_keys = [f"right {mod}", f"right {mod} cut outs"]
            if any(content_dict.get(k, '') == 'selected' for k in left_keys):
                left_modifications_count += 1
                passed_codes['BNS45'] += 1
            if any(content_dict.get(k, '') == 'selected' for k in right_keys):
                right_modifications_count += 1
                passed_codes['BNS45'] += 1

        # Postings -> B56. Two Azure/form schemas exist:
        #   A) "left medial rearfoot posting: selected" + separate "... height: 4"
        #   B) "left medial rearfoot: selected" + "... posting: 4" (height on posting key)
        # Count each side/position once if either the bare key or the "... posting" key is selected.
        posting_positions = [
            'medial rearfoot', 'lateral rearfoot',
            'medial forefoot', 'lateral forefoot',
        ]
        # Kirby skive: logs often omit "posting"; main.py groups may include it.
        kirby_positions = ['medial kirby skive', 'lateral kirby skive']

        def _posting_selected(side, position):
            bare = content_dict.get(f'{side} {position}', '').strip().lower()
            with_suffix = content_dict.get(f'{side} {position} posting', '').strip().lower()
            return bare == 'selected' or with_suffix == 'selected'

        left_postings_count = 0
        right_postings_count = 0

        for position in posting_positions:
            if _posting_selected('left', position):
                left_postings_count += 1
                passed_codes['B56'] += 1
            if _posting_selected('right', position):
                right_postings_count += 1
                passed_codes['B56'] += 1

        for position in kirby_positions:
            if _posting_selected('left', position):
                left_postings_count += 1
                passed_codes['B56'] += 1
            if _posting_selected('right', position):
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
            'left valgus pad 3mm', 'left valgus pad 6mm', 'right valgus pad 3mm', 'right valgus pad 6mm',
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

        # Check if any poron lining is selected
        linings = [
            'soft poron 1.6mm',
            'soft poron 3mm',
            'soft poron 6mm',
            'medium poron 1.6mm',
            'medium poron 3mm',
            'medium poron 6mm',
            'firm memory foam poron 1.6mm',
            'firm memory foam poron 3mm',
            'firm memory foam poron 6mm'
        ]
        has_lining = any(content_dict.get(lining, '') == 'selected' for lining in linings)
        if has_lining:
            x += 1
            print(f"After poron lining check: x = {x}")

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

    # Nested calls (bespoke/modular) apply quantity once on the merged order.
    if not return_dict:
        apply_order_quantity(passed_codes, content_dict)

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
    from collections import defaultdict
    passed_codes = defaultdict(int)  # Use defaultdict to count occurrences

    content_dict = parse_content_dict(content)

    # Extract the clinic name if it exists in the content
    clinic_name = content_dict.get('clinic', '').lower()
    customer_no = get_customer_no(clinic_name)

    # Check if it's a pair for AFO
    is_pair = content_dict.get('pair', '') == 'selected' or content_dict.get('afo pair', '') == 'selected'

    # The Pair tick box is not always read correctly, and is_pair doubles nearly every
    # code below, so a wrong reading halves the whole order. Fall back to the rest of the
    # form. main.py runs the same check to warn the code checker.
    if not is_pair and detect_missed_pair(content_dict, content):
        is_pair = True

    # Wales Tariff for AFO
    if customer_no in tariff_wales_customer_nos:
        passed_codes['WALES-AFO'] += 1
        if is_pair:
            passed_codes['WALES-AFO'] *= 2
        apply_order_quantity(passed_codes, content_dict)
        return 'WALES-AFO' if passed_codes['WALES-AFO'] == 1 else f'WALES-AFO x{passed_codes["WALES-AFO"]}'

    # --- Tariff AFO Check ---
    if customer_no in tariff_afo_customer_nos:
        passed_codes['TARIFF AFO'] += 1
        if is_pair:
            passed_codes['TARIFF AFO'] *= 2
        apply_order_quantity(passed_codes, content_dict)
        return 'TARIFF AFO' if passed_codes['TARIFF AFO'] == 1 else f'TARIFF AFO x{passed_codes["TARIFF AFO"]}'

    # Non-tariff AFO type logic
    # P15 - every AFO gets it, 2 per device (single -> x2, pair -> x4 via pair doubling
    # below). A GRAFO gets half that, 1 per device.
    # This is not conditional on anything on the form. Across the 56 reviewed forms in the
    # corrections sheets, P15 has never once been crossed out. The five forms with no P15
    # come from the July round, when the app produced no P15 at all and the reviewer had to
    # write it on by hand 42 times; the August round, where the app supplied it, wanted it
    # on 14 of 14. An earlier attempt to drive P15 off the full-part-lining boxes instead
    # scored 11 of 37 against the reviewers, where this scores 32.
    passed_codes['P15'] += 1 if content_dict.get('grafo', '') == 'selected' else 2
    # D8U - applied by default at 1 per device (single -> x1, pair -> x2 via pair doubling below)
    passed_codes['D8U'] += 1

    if content_dict.get('dafo', '') == 'selected':
        passed_codes['D1K'] += 1

    if (content_dict.get('afo fixed', '') == 'selected' or content_dict.get('afo smafo', '') == 'selected' or
        content_dict.get('grafo', '') == 'selected' or content_dict.get('afo hinged', '') == 'selected' or
        content_dict.get('afo/dafo', '') == 'selected'):
        passed_codes['D1C'] += 1

    # DNS6 - CROW boot, or a Nora Lunairmed (A18) lining.
    # The original 'crow' trigger is KEPT. No form in the sample has a CROW boot, so we
    # cannot say it is wrong - only that it has never had the chance to fire. Nora
    # Lunairmed is added alongside as a second, independent trigger.
    # It is recorded two different ways, so both are checked: HC566422 ticked the box
    # 'ptm nora lunairmed a18', while RR157819 typed it into 'additional info ptm'.
    # The full phrase is matched rather than just "nora", so other Nora products do not
    # trigger it (HC566422 also says "Internal 6 mm Nora DAFO", which is not this).
    # Fires ONCE even if more than one of these is present. Device level, so the pair
    # loop doubles it - both sample forms are pairs and want DNS6 x2.
    nora_lunairmed = (
        content_dict.get('ptm nora lunairmed a18', '') == 'selected'
        or any(re.search(r'nora\s*lunairmed', value, re.IGNORECASE)
               for key, value in content_dict.items() if key.startswith('additional info'))
    )
    if content_dict.get('crow', '') == 'selected' or nora_lunairmed:
        passed_codes['DNS6'] += 1

    # A GRAFO or clam shell is built as TWO shells - a back shell and a front shell -
    # where an ordinary AFO is one. That drives both D12M and D10I below.
    two_shell_device = (content_dict.get('grafo', '') == 'selected'
                        or content_dict.get('clam shell', '') == 'selected')

    if content_dict.get('clam shell', '') == 'selected':
        passed_codes['D1C'] += 1     # base code (was missing - clam shell is a solid AFO)

    # D12M - the anterior / front shell, charged once per device (on top of any D1C base
    # set above). Three things point at the same shell: the GRAFO box, the clam shell box
    # and the 'nc ant shell' height measurement, so they must not be added up - PP629803
    # has the GRAFO box AND the measurement and is billed D12M x2, not x4.
    # D12M is in per_side_codes below, so the blanket pair doubling skips it and the
    # doubling is done here. ('nc ant shell' is always filled in for both sides or
    # neither, so charging per device rather than per side changes nothing else.)
    has_anterior_shell = two_shell_device or any(
        content_dict.get(f'nc ant shell {side}', '') != '' for side in ('left', 'right'))
    if has_anterior_shell:
        passed_codes['D12M'] += 2 if is_pair else 1

    # D10I - the transfer (decorative pattern) applied to the plastic. One per shell, so
    # a two-shell device gets two. D10I is NOT in per_side_codes, so a pair doubles this
    # again: ordinary AFO pair x2, GRAFO pair x4.
    if content_dict.get('transfer', '') != '':
        passed_codes['D10I'] += 2 if two_shell_device else 1

    # Additions logic
    if content_dict.get('additions tamarac', '') == 'selected':
        passed_codes['D2A'] += 1

    if content_dict.get('additions other', '') == 'metal':
        passed_codes['D2B'] += 1

    if content_dict.get('additions carbon', '') == 'selected':
        passed_codes['D10A'] += 1

    if content_dict.get('additions ribbed', '') == 'selected':
        passed_codes['D10B'] += 1

    # PTM
    if content_dict.get('ptm fully lined', '') == 'selected':
        passed_codes['D14E'] += 1

    if content_dict.get('ptm pad top of calf', '') == 'selected':
        passed_codes['D14D'] += 1

    if content_dict.get('ptm footplate lining', '') == 'selected':
        passed_codes['D14H'] += 1

    # finishing
    if content_dict.get('finishing perforated', '') == 'selected':
        passed_codes['D10U'] += 1

    # A non-slip sole is D10G, one per device (the pair loop doubles it). This used to
    # give D10C: across the 56 reviewed forms no reviewer has ever asked for D10C, and the
    # one time the app produced it (DC499735) it was crossed out and D10G written in.
    # DC499735 also wanted D10F, which AD044733 - the other sole form, which asks for a
    # "walking sole" in its notes - did not. D10F is deliberately NOT added here: the site
    # visit report describes it as a raise code, neither form mentions a raise, and it is
    # worth about GBP110 a time. Needs a code checker's answer before anyone guesses.
    if content_dict.get('finishing non slip sole', '') == 'selected':
        passed_codes['D10G'] += 1

    # B43 - REMOVED from AFO coding. B43 is a heel RAISE (see the insole logic, where
    # 'heel raise' -> B43), not heel wedging. The old trigger below fired on
    # 'finishing heel wedging', which is a mis-extraction: the reader picks up text from
    # the form's "Shank to Vertical Alignment Angle (SVA)" area, so the field only ever
    # holds "Vert" or "Sv". All 4 forms where it fired should NOT have been billed B43,
    # and the one form that genuinely needed B43 x2 had the field empty - it asked for it
    # in free text ("Please include 2 x 6mm internal heel raises"). Do not reinstate this
    # without a real heel-raise source.
    # if content_dict.get('finishing heel wedging', '') != '':
    #     passed_codes['B43'] += 1

    # D10E - heel post. There is no "heel post" box on the AFO form: the post is HOW an
    # angle is built, so the trigger is the prescription asking for one - either a bench
    # alignment instruction or a plantarflexion angle. Either alone is enough; having both
    # (or angles on both sides) does NOT add more - it is one post per device.
    # A bench alignment reading "No posts" is an explicit refusal, so it is excluded.
    # Checked against 24 corrected forms (17 needing D10E, 7 not): 100% correct.
    # NOTE: the previous rule used '{side} heel raise posting', which is an Insole Room
    # field and never appears on an AFO form, so D10E could never fire.
    bench_alignment = content_dict.get('additional info bench alignment', '').strip()
    wants_heel_post = bool(bench_alignment) and not re.search(r'\bno\s+post', bench_alignment, re.I)
    if not wants_heel_post:
        wants_heel_post = any(content_dict.get(f'nc pf {side}', '').strip()
                              for side in ('left', 'right'))
    if wants_heel_post:
        # Doubled here for a pair; D10E is in per_side_codes so the pair loop skips it.
        passed_codes['D10E'] += 2 if is_pair else 1

    # Straps
    sides = ['left', 'right']
    positions = ['medial', 'lateral']

    for side in sides:
        for position in positions:
            # D10H - COMMENTED OUT. The cause of D10H is unknown.
            # This slotted-strap trigger was added in commit 2011fb3 (11 Oct 2025), which
            # mapped the form's Straps boxes onto codes by eye rather than against real
            # billing corrections. The data does not support it:
            #   - Only ST728904 has slotted straps, and its corrected codes contain NO D10H
            #     (it wants D8H x2, which comes from sust tali - see below).
            #   - The only form that DOES want D10H (M1422592, x1) has no slotted strap at all.
            # So the rule fires only where it is wrong and misses the one case that wants it.
            # It also double-counted: gathered per side but absent from per_side_codes, so a
            # pair doubled it again (ST728904 was billed D10H x4).
            # Across all 56 corrected rows D10H is wanted exactly once, with no derivable
            # trigger. Do not reinstate without knowing what actually drives it.
            # if content_dict.get(f'{side} {position} straps slotted', '') == 'selected':
            #     passed_codes['D10H'] += 1
            # NOTE: D14B comes from the same untested 2011fb3 batch and is likewise counted
            # per side while missing from per_side_codes. It fires on none of the 41 logs, so
            # it is dormant rather than proven wrong - worth checking before it ever does.
            if content_dict.get(f'{side} {position} straps df assist', '') == 'selected':
                passed_codes['D14B'] += 1
            # Y-strap full-part lining box, per side/position (up to 4): each = D14A.
            # These are per-side (already bilateral for a pair) so D14A is in
            # per_side_codes below and is NOT doubled again by the pair loop.
            # These boxes used to add P15 as well. They do not: P15 is a flat per-device
            # default (see the top of this function), and adding the boxes on top
            # over-bills - M1100442 has two boxes ticked and is billed P15 x4, which the
            # default already gives.
            if content_dict.get(f'{side} {position} full part lining', '') == 'selected':
                passed_codes['D14A'] += 1

    # D14A - toe strap. Just D14A here (P15 comes only from the full-part lining boxes above).
    # `straps toe` is a single device-level field, so for a pair we double it manually here;
    # D14A is in per_side_codes below (for the per-side lining boxes) and so is skipped by the
    # blanket pair-doubling loop.
    # NOTE: the date/number values seen in `straps toe` in the logs come from a stamp applied
    # AFTER the app has processed a form, so the live app never sees them - the field is clean
    # at processing time, hence a plain non-empty check is safe here.
    # (The old straps-calf/straps-heel rule was the wrong trigger and was removed.)
    if content_dict.get('straps toe', '') != '':
        passed_codes['D14A'] += 2 if is_pair else 1

    # (The `straps heel` "lateral" fallback that used to sit here raised P15 to x4. It went
    # with the lining-box P15 rule - the flat default already gives x4 for a pair.)

    # D14C - padding. Two per device as standard, three when the clinician has asked for an
    # extra pad on top: either by typing a material into the lateral/medial pad box (e.g.
    # "3 Ld PZ") or by asking for foot wall padding in the pads notes.
    #
    # This replaces a per-side count of the pad tick boxes. Counting the boxes scored 18 of
    # 37 against the code checkers; this scores 25. The checkers never ask for more than 3
    # per device however many boxes are ticked, and 12 forms with IDENTICAL boxes are billed
    # anywhere from 2 to 3 per device - so the box count was never what drove the number.
    #
    # It breaks 4 forms (H1586477, PF132900, PP629803, R1808722) which want 3 per device with
    # no extra pad asked for. All four come from the July review round, the same round that
    # omitted P15 on five forms. Every form from the August round agrees with this rule.
    # 9 forms have identical pad data and different answers, so 28 of 37 is the ceiling for
    # any rule built on these fields - this gets 25 of that 28.
    #
    # D14C is NOT in per_side_codes any more: it is now a per-device figure, so the pair loop
    # below has to double it.
    pad_tick_boxes = ['lat mall pads', 'med mall pads', 'elongated pads',
                      'arch pads', 'navicular pads']
    any_pad = any(content_dict.get(f'{side} {pad}', '') == 'selected'
                  for side in sides for pad in pad_tick_boxes)
    if any_pad:
        extra_pad_asked_for = any(
            content_dict.get(f'{side} {pad}', '').strip()
            for side in sides for pad in ('lateral pads', 'medial pads'))
        if not extra_pad_asked_for:
            extra_pad_asked_for = bool(
                re.search(r'foot\s*wall', content_dict.get('additional info pads', ''), re.I))
        passed_codes['D14C'] += 3 if extra_pad_asked_for else 2

    # D8H - sustentaculum tali (Sust Tali) option, once per side selected.
    # Counted from the left/right fields so a pair is already correct; D8H is
    # in per_side_codes so the pair-doubling loop skips it (otherwise x4).
    for side in sides:
        if content_dict.get(f'{side} sust tali', '') == 'selected':
            passed_codes['D8H'] += 1

    # Handle pairs by doubling codes if applicable.
    # Per-side codes are counted from both the left and right fields, so they are already
    # bilateral for a pair and must NOT be doubled again (that would double-count them).
    # D14A comes from the per-side full-part-lining boxes; the device-level toe-strap D14A
    # is doubled manually above, so it is treated as per-side here.
    # D8H is counted from the left/right sust tali fields and is already bilateral.
    # P15 and D14C are NOT here: both are flat per-device figures, so a pair must double them.
    per_side_codes = {'D12M', 'D10E', 'D14A', 'D8H'}
    if is_pair:
        for code in list(passed_codes.keys()):
            if code not in per_side_codes:
                passed_codes[code] *= 2

    apply_order_quantity(passed_codes, content_dict)

    # Format the passed codes with counts.
    # Sorted by code number then the letter after it (see code_sort_key). The sort is applied
    # to the code keys BEFORE the " x{count}" text is attached, so quantities can never affect
    # the ordering. Codes with a count of 0 or less are skipped so a quantity-less code can
    # never reach NAV. This step is presentation only - it changes neither which codes are
    # emitted nor their quantities.
    formatted_passed_codes = []
    for code in sorted(passed_codes, key=code_sort_key):
        count = passed_codes[code]
        if count <= 0:
            continue
        if count > 1:
            formatted_passed_codes.append(f"{code} x{count}")
        else:
            formatted_passed_codes.append(code)

    if formatted_passed_codes:
        return ', '.join(formatted_passed_codes)
    else:
        return None

def generate_modular_codes(self, content):
    """Generates codes based on the content for the Modular model, with tariff logic."""
    passed_codes = defaultdict(int) # Use defaultdict to count occurrences
    content_dict = parse_content_dict(content)
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
        has_type_a = any(content_dict.get(f'{side} {socket}', '') == 'selected' for socket in TYPE_A_SOCKETS)
        has_type_b = any(content_dict.get(f'{side} {socket}', '') == 'selected' for socket in TYPE_B_SOCKETS)
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
    apply_order_quantity(passed_codes, content_dict)
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

def generate_repairs_codes(self, content):
    return None

def generate_adapts_and_modifications_codes(self, content):
    return None