# generate_code_logic.py
from collections import defaultdict
from tkinter import messagebox

def generate_bespoke_codes(self, content):
        """Generates codes based on the content for the Bespoke model, counting duplicates."""
        from collections import defaultdict
        passed_codes = defaultdict(int)  # Use defaultdict to count occurrences

        # Define lists of clinics for each insole tariff code (edit these lists as needed)
        tariff_tci_clinics = ['east surrey', 'bury cdc', 'ely', 'hinchingbrooke', 'pch', 'peterborough city hospital', 'sudbury', 'w.s.h', 'ws', 'wsh', 'stamford', 'pch diab', 'doddington', 'peterborough']
        tariff_simple_clinics = ['bury cdc', 'ely', 'harpenden', 'hinchingbrooke', 'pch', 'peterborough city hospital', 'sudbury', 'w.s.h', 'ws', 'wsh', 'stamford', 'pch diab', 'doddington', 'peterborough']
        tariff_polyprop_clinics = ['east surrey', 'bury cdc', 'ely', 'hinchingbrooke', 'pch', 'peterborough city hospital', 'sudbury', 'w.s.h', 'ws', 'wsh', 'stamford', 'pch diab', 'doddington', 'peterborough']

        # Define list of clinics for Tariff Bespoke
        tariff_bespoke_clinics = ['bury cdc', 'east surrey', 'sudbury', 'w.s.h', 'ws', 'wsh']

        # Split the content into lines for easier processing
        lines = content.split('\n')

        # Convert lines to a dictionary
        content_dict = {}
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                content_dict[key.strip().lower()] = value.strip().lower()

        clinic_name = content_dict.get('clinic', '').lower()

        # Check if it's a pair
        is_pair = content_dict.get('pair', '') == 'selected' or content_dict.get('insole pair', '') == 'selected'

        # Track if tariffs were added
        bespoke_tariff_added = False
        insole_tariff_added = False

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

        # --- Medway Tariffs for Bespoke ---
        # If medway:
        # - If simple: add MEDBNS71
        # - Otherwise: add MEDBNS72
        # In all cases: add MEDFOOTWEAR
        # Don't return immediately, continue logic and filter at the end
        if clinic_name == 'medway':
            if insole_type == 'simple':
                passed_codes['MEDBNS71'] += 1
            else:
                passed_codes['MEDBNS72'] += 1
            passed_codes['MEDFOOTWEAR'] += 1
            bespoke_tariff_added = True
            insole_tariff_added = True

        # Bespoke Tariff Check
        if clinic_name in tariff_bespoke_clinics:
            passed_codes['Tariff Bespoke'] += 1
            bespoke_tariff_added = True

        # Insole Tariff Checks
        if clinic_name in tariff_tci_clinics:
            passed_codes['Tariff TCI'] += 1
            if is_pair:
                passed_codes['Tariff TCI'] *= 2
            insole_tariff_added = True
        elif clinic_name in tariff_simple_clinics:
            passed_codes['Tariff Simple'] += 1
            if is_pair:
                passed_codes['Tariff Simple'] *= 2
            insole_tariff_added = True
        elif clinic_name in tariff_polyprop_clinics:
            passed_codes['Tariff Polyprop'] += 1
            if is_pair:
                passed_codes['Tariff Polyprop'] *= 2
            insole_tariff_added = True

        # Style-based logic
        style = content_dict.get('style', '').lower()

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

        if style in a1b_styles:
            passed_codes['A1B'] += 1
        elif style in a1a_styles:
            passed_codes['A1A'] += 1

        # Add logic for 'pop cast'
        if content_dict.get('pop cast', '') == 'selected':
            passed_codes['A1K'] += 1

        # Backup logic for 'A1A' and 'A1B'
        if 'A1A' not in passed_codes and 'A1B' not in passed_codes:
            type_code_mapping = {
                'type boots': 'A1A',
                'type bootee': 'A1A',
                'type shoes': 'A1B',
                'type sports': 'A1B',
            }
            for key, code in type_code_mapping.items():
                if content_dict.get(key, '') == 'selected':
                    passed_codes[code] += 1

        # Default to 'A1A' if neither 'A1A' nor 'A1B' is present
        if 'A1A' not in passed_codes and 'A1B' not in passed_codes:
            passed_codes['A1A'] += 1

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

        # Additions
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
                    passed_codes['BNS45'] += 1

        posting_keys = [
            'left medial rearfoot posting',
            'left lateral rearfoot posting',
            'right medial rearfoot posting',
            'right lateral rearfoot posting',
            'left medial forefoot posting',
            'left lateral forefoot posting',
            'right medial forefoot posting',
            'right lateral forefoot posting',
        ]

        for key in posting_keys:
            if content_dict.get(key, '') == 'selected':
                code = 'A45' if insole_type == 'cradle' else 'B56'
                passed_codes[code] += 1

        # Sole Stiffeners
        stiffener_keys = {
            'sole stiffeners left carbon fibre': 'A20',
            'sole stiffeners right carbon fibre': 'A20',
            'sole stiffeners left steel': 'A22',
            'sole stiffeners right steel': 'A22'
        }

        for key, code in stiffener_keys.items():
            if content_dict.get(key, '') == 'selected':
                passed_codes[code] += 1

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
                passed_codes[code] += 1

        if content_dict.get('fastening', '') == 'boa':
            passed_codes['Twist Fasten'] += 1

        if content_dict.get('lining material', '') == 'white sheepskin':
            passed_codes['A18A'] += 1

        if content_dict.get('sole material', '') == 'commando':
            passed_codes['A6'] += 1

        stiffeners_materials = {
            'stiffeners left materials': 'A15',
            'stiffeners right materials': 'A15'
        }

        for key, code in stiffeners_materials.items():
            if content_dict.get(key, '') in ('grey poron', 'pink poron', 'foam'):
                passed_codes[code] += 1

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
            passed_codes['A16'] += left_a16_count

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
            passed_codes['A16'] += right_a16_count

        sockets_type_a = {
            'left socket type': 'A37A',
            'right socket type': 'A37A'
        }

        for key, code in sockets_type_a.items():
            if content_dict.get(key, '') in (
                '5/16 round socket', '1/4inc round socket', 'small rectangular', 'large rectangular', 'rizzoli'
            ):
                passed_codes[code] += 1

        sockets_type_b = {
            'left socket type': 'A37B',
            'right socket type': 'A37B'
        }

        for key, code in sockets_type_b.items():
            if content_dict.get(key, '') in ('5/16 with backstop', '1/4 with backstop'):
                passed_codes[code] += 1

        # Wedges
        wedges_heel_keys = [
            'left wedges heel medial',
            'left wedges heel lateral',
            'right wedges heel medial',
            'right wedges heel lateral',
        ]

        for key in wedges_heel_keys:
            if content_dict.get(key, '') == 'selected':
                passed_codes['A31'] += 1

        wedges_sole_keys = [
            'left wedges sole medial',
            'left wedges sole lateral',
            'right wedges sole medial',
            'right wedges sole lateral',
        ]

        for key in wedges_sole_keys:
            if content_dict.get(key, '') == 'selected':
                passed_codes['A19'] += 1

        # Floated
        floated_heel_keys = [
            'left floated heel medial',
            'left floated heel lateral',
            'right floated heel medial',
            'right floated heel lateral',
        ]

        for key in floated_heel_keys:
            if content_dict.get(key, '') == 'selected':
                passed_codes['A31'] += 1

        floated_sole_keys = [
            'left floated sole medial',
            'left floated sole lateral',
            'right floated sole medial',
            'right floated sole lateral',
        ]

        for key in floated_sole_keys:
            if content_dict.get(key, '') == 'selected':
                passed_codes['A26'] += 1

        # Raises - to do the 25mm+ codes 
        for side in ['left', 'right']:
            raise_inside_key = f'raise {side} inside'
            raise_outside_key = f'raise {side} outside'
            raise_material_key = f'raise {side} material'

            raise_material = content_dict.get(raise_material_key, '')

            if content_dict.get(raise_inside_key, '') == 'selected':
                if raise_material in ('ld eva', 'lightweight p/zote (non-covered)', 'lightweight p/zote (covered)', 'cork'):
                    passed_codes['A8'] += 1

            if content_dict.get(raise_outside_key, '') == 'selected':
                if raise_material == 'ld eva':
                    passed_codes['A13A'] += 1
                elif raise_material in ('lightweight p/zote (non-covered)', 'lightweight p/zote (covered)'):
                    passed_codes['A12A'] += 1

        # Elongations
        elongations_keys = ['left elongations type', 'right elongations type']
        for key in elongations_keys:
            if content_dict.get(key, '') in ('full', 'half'):
                passed_codes['A31'] += 1

        # Rocker
        rocker_keys = ['left rocker type', 'right rocker type']
        for key in rocker_keys:
            if content_dict.get(key, '') in ('plr', 'standard', 'two point'):
                passed_codes['A19'] += 1

        # Straps
        for side in ['left', 'right']:
            strap_type_key = f'{side} strap type'
            strap_double_decker_key = f'{side} double decker'

            strap_type = content_dict.get(strap_type_key, '')
            strap_double_decker = content_dict.get(strap_double_decker_key, '')

            if strap_double_decker == 'selected':
                if strap_type in ('t strap', 'y strap'):
                    passed_codes['A39'] += 1
            else:
                if strap_type in ('t strap', 'y strap'):
                    passed_codes['A38'] += 1

            if strap_type in ('spur retaining strap', 'heel retaining strap'):
                passed_codes['A40'] += 1

        # Insole coding section - MATHS!
        x = 0
        if insole_type == 'simple':
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

        if x >= 2:
            code = 'A44C' if insole_type == 'cradle' else 'B55C'
            passed_codes[code] += 1
        elif x == 1:
            code = 'A44B' if insole_type == 'cradle' else 'B55B'
            passed_codes[code] += 1
        elif x == 0:
            code = 'A44A' if insole_type == 'cradle' else 'B55A'
            passed_codes[code] += 1

        normalized_base = base.replace(' ', '').lower()
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

        # Pair Handling for normal codes
        if content_dict.get('insole pair', '') == 'selected':
            codes_to_double_general = [
                'A1K', 'A18A', 'Twist Fasten', 'A6'
            ]
            for code in codes_to_double_general:
                if code in passed_codes:
                    passed_codes[code] *= 2

        if content_dict.get('insole pair', '') == 'selected':
            codes_to_double_insole = [
                'A10', 'B54C', 'B40B', 'B54A',
                'A44A', 'A44B', 'A44C', 'B55A', 'B55B', 'B55C', 'B54B'
            ]
            for code in codes_to_double_insole:
                if code in passed_codes:
                    passed_codes[code] *= 2

        # If it's a pair, double MEDBNS71 or MEDBNS72 if present, but not MEDFOOTWEAR
        if is_pair:
            if 'MEDBNS71' in passed_codes:
                passed_codes['MEDBNS71'] *= 2
            if 'MEDBNS72' in passed_codes:
                passed_codes['MEDBNS72'] *= 2
            # Do not double MEDFOOTWEAR

        # --- Final Filtering Step ---
        insole_filter_codes = {
            'A10', 'B54C', 'B40B', 'B54A', 'A44A', 'A44B', 'A44C',
            'B55A', 'B55B', 'B55C', 'B56', 'A45', 'BNS45', 'A47',
            'B51', 'B50', 'A46', 'A20', 'B20', 'D8A', 'B43', 'B41'
        }

        bespoke_filter_codes = {
            'A1B', 'A1A', 'A1K', 'A22', 'A23', 'A24', 'A25',
            'Twist Fasten', 'A18A', 'A6', 'A15', 'A16', 'A37A',
            'A37B', 'A31', 'A19', 'A26', 'A8', 'A13A', 'A12A',
            'A39', 'A38', 'A40', 'B54B'
        }

        # If insole tariff selected, remove insole_filter_codes
        if insole_tariff_added:
            for c in insole_filter_codes:
                if c in passed_codes:
                    del passed_codes[c]

        # If bespoke tariff selected, remove bespoke_filter_codes
        if bespoke_tariff_added:
            for c in bespoke_filter_codes:
                if c in passed_codes:
                    del passed_codes[c]

        # Format the passed codes with counts
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
def generate_insole_codes(self, content):
        """Generates insole codes based on the content."""

        from collections import defaultdict
        passed_codes = defaultdict(int)  # Use defaultdict to count occurrences

        # Define lists of clinics for each insole tariff code (edit these lists as needed)
        tariff_tci_clinics = ['east surrey', 'bury cdc', 'ely', 'hinchingbrooke', 'pch',
                            'peterborough city hospital', 'sudbury', 'w.s.h', 'ws', 'wsh', 'stamford', 'pch diab', 'doddington', 'peterborough']
        tariff_simple_clinics = ['bury cdc', 'ely', 'harpenden', 'hinchingbrooke', 'pch',
                                'peterborough city hospital', 'sudbury', 'w.s.h', 'ws', 'wsh', 'stamford', 'pch diab', 'doddington', 'peterborough']
        tariff_polyprop_clinics = ['east surrey', 'bury cdc', 'ely', 'hinchingbrooke', 'pch',
                                'peterborough city hospital', 'sudbury', 'w.s.h', 'ws', 'wsh', 'stamford', 'pch diab', 'doddington', 'peterborough']

        # Split the content into lines
        lines = content.split('\n')

        # Convert lines to a dictionary
        content_dict = {}
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                content_dict[key.strip().lower()] = value.strip().lower()

        clinic_name = content_dict.get('clinic', '').lower()

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
        if clinic_name == 'medway':
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

        # Now unify the three tariff checks in a single block:
        base = content_dict.get('base', '').strip().lower()

        # Create a combined set of all tariff clinics
        all_tariff_clinics = set(tariff_polyprop_clinics + tariff_simple_clinics + tariff_tci_clinics)

        if clinic_name in all_tariff_clinics:
            # 1) If the clinic allows polyprop & base == 'polypropylene'
            if clinic_name in tariff_polyprop_clinics and base == 'polypropylene':
                passed_codes['Tariff Polyprop'] += 1
                if is_pair:
                    passed_codes['Tariff Polyprop'] *= 2
                return (
                    'Tariff Polyprop'
                    if passed_codes['Tariff Polyprop'] == 1
                    else f"Tariff Polyprop x{passed_codes['Tariff Polyprop']}"
                )

            # 2) Else if the clinic allows "simple" & insole_type == 'simple'
            elif clinic_name in tariff_simple_clinics and insole_type == 'simple':
                passed_codes['Tariff Simple'] += 1
                if is_pair:
                    passed_codes['Tariff Simple'] *= 2
                return (
                    'Tariff Simple'
                    if passed_codes['Tariff Simple'] == 1
                    else f"Tariff Simple x{passed_codes['Tariff Simple']}"
                )

            # 3) Else if the clinic is in the TCI list
            elif clinic_name in tariff_tci_clinics:
                passed_codes['Tariff TCI'] += 1
                if is_pair:
                    passed_codes['Tariff TCI'] *= 2
                return (
                    'Tariff TCI'
                    if passed_codes['Tariff TCI'] == 1
                    else f"Tariff TCI x{passed_codes['Tariff TCI']}"
                )

        # If we get here, then the clinic isn't in any of those lists, or no conditions matched:
        # Continue with your normal "base logic" here.
        #
        # (the rest of your normal logic follows...)

        # Normal logic if no immediate tariff matched
        from collections import defaultdict
        passed_codes = defaultdict(int)

        base = content_dict.get('base', '').strip().lower()
        print(f"Base value: '{base}'")  # For debugging

        if content_dict.get('base poron', '').lower() == 'selected':
            passed_codes['B40B'] += 1

        # 2) Otherwise, use the base logic
        else:
            normalized_base = base.replace(' ', '').lower()
            shore_bases = {'40shore', '50shore', '65shore'}

            # Base codes
            if normalized_base == 'polypropylene':
                passed_codes['B54B'] += 1
            elif insole_type == 'simple' and normalized_base in shore_bases:
                passed_codes['B40B'] += 1
            elif normalized_base in ['carbonfibre', 'carbonfiber']:
                passed_codes['B54A'] += 1
            else:
                # If none match, default to B54C
                passed_codes['B54C'] += 1

        # Foot modifications -> BNS45
        foot_modifications = [
            'cut out and additions', '1st met head', '1st met ray', '5th met ray',
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
        addition_positions = [
            'left 1st addition', 'left 2nd addition', 'left 3rd addition', 'left 4th addition',
            'right 1st addition', 'right 2nd addition', 'right 3rd addition', 'right 4th addition'
        ]

        addition_code_mapping = {
            'B41': {'valgus pad', 'metatarsal pad', 'metatarsal bar', 'balance pad',
                    'heel pad', 'cuboid pad', 'cobra pad', 'neuroma pad',
                    'sulcus crest', 'arch fill'},
            'B56': {"morton's extension", "reverse morton's extension", 'poron forefoot'},
            'B43': {'kinetic wedge', 'heel raise'},
            'D8A': {'neurological footplate'},
            'BNS45': {'recess', 'hole & plug'},
            'B20': {'rigid 1st extension'},
            'B50': {'partial toe block'},
            'B51': {'full toe block'}
        }

        for key in addition_positions:
            addition_value = content_dict.get(key, '')
            if addition_value:
                for code, additions in addition_code_mapping.items():
                    if addition_value in additions:
                        passed_codes[code] += 1
                        break
                else:
                    print(f"Warning: Unrecognized addition value '{addition_value}' for '{key}'")

        # Insole coding - MATHS
        x = 0
        if insole_type == 'simple':
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

        if x >= 2:
            passed_codes['B55C'] += 1
        elif x == 1:
            passed_codes['B55B'] += 1
        elif x == 0:
            passed_codes['B55A'] += 1

        # CLCH Simple Logic
        if clinic_name == 'clch' and insole_type == 'simple':
            total_posts = (passed_codes['B41'] + passed_codes['B56'] +
                        passed_codes['B43'] + passed_codes['BNS45'])

            # Decide tariff
            if total_posts <= 4:
                chosen_tariff = 'Tariff insole >4 POST'
            else:
                chosen_tariff = 'Tariff insole <5 POST'

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

        # Define list of clinics for Tariff AFO (edit this list as needed)
        tariff_afo_clinics = ['bury cdc', 'east surrey', 'sudbury', 'w.s.h', 'ws', 'wsh']

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

        # Check if it's a pair for AFO
        is_pair = content_dict.get('pair', '') == 'selected' or content_dict.get('afo pair', '') == 'selected'

        # --- New Medway Tariff ---
        if clinic_name == 'medway':
            passed_codes['MEDDNS2'] += 1
            if is_pair:
                passed_codes['MEDDNS2'] *= 2
            return 'MEDDNS2' if passed_codes['MEDDNS2'] == 1 else f'MEDDNS2 x{passed_codes["MEDDNS2"]}'

        # --- Tariff AFO Check ---
        if clinic_name in tariff_afo_clinics:
            passed_codes['Tariff AFO'] += 1
            if is_pair:
                passed_codes['Tariff AFO'] *= 2
            return 'Tariff AFO' if passed_codes['Tariff AFO'] == 1 else f'Tariff AFO x{passed_codes["Tariff AFO"]}'

        # --- Start of AFO-specific logic (if not a Tariff AFO clinic) ---
        # Default codes
        default_codes = ['D1/C', 'D8/U']

        # Determine AFO Type codes with pair handling for 'D8/U'
        afo_type = content_dict.get('afo type', '').lower()
        if afo_type in ('normal', 'fixed', 'articulated'):
            passed_codes['D1/C'] += 1
            code_count = 1
            if content_dict.get('afo pair', '') == 'selected':
                code_count *= 2
            passed_codes['D8/U'] += code_count
        elif afo_type == 'crow boot':
            passed_codes['DNS 1'] += 1
        elif afo_type == 'afo/dafo':
            passed_codes['D1/C'] += 2
            code_count = 2
            if content_dict.get('afo pair', '') == 'selected':
                code_count *= 2
            passed_codes['D8/U'] += code_count
        elif afo_type == 'anterior shell':
            passed_codes['D12/M'] += 1
        else:
            # If 'AFO Type' does not exist, use default codes
            passed_codes['D1/C'] += 1
            code_count = 1
            if content_dict.get('afo pair', '') == 'selected':
                code_count *= 2
            passed_codes['D8/U'] += code_count

        # Check for 'Anterior Shell Height' even if 'AFO Type' is not 'anterior shell'
        if afo_type != 'anterior shell' and content_dict.get('anterior shell height', ''):
            passed_codes['D12/M'] += 1

        # Determine Hinge Type codes
        hinge_type = content_dict.get('hinge type', '').lower()
        hinge_code = None
        if hinge_type == 'gillette/tamrack':
            hinge_code = 'D2/A'
        elif hinge_type in ('double action', 'camber axis'):
            hinge_code = 'D2/D'
        elif hinge_type in ('appalachian/metal', 'appalachian', 'metal'):
            hinge_code = 'D2/B'

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
            passed_codes['D10/E'] += heel_posting_codes

        # PCRO Codes
        pcro_codes = defaultdict(int)
        pcro_right_as_left = content_dict.get('pcro right as left', '') == 'selected'

        # List of PCRO features and their codes
        pcro_features = {
            'varus resist': 'D8/D',
            'valgus resist': 'D8/D',
            'suctentaculum tali': 'D8/H',
            'peroneal notch': 'D8/I',
            'metatarsal button': 'B41',
            'neuro plate': 'D8/A',
            'toe lift': 'D8/U',
            'pcro values': 'D8/B'
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

        # M&T Codes
        m_and_t_codes = []
        if content_dict.get('carbon ankle reinforcements', '') == 'selected':
            m_and_t_codes.append('D10/B')
        if content_dict.get('ribbed ankle reinforcements', '') == 'selected':
            m_and_t_codes.append('D10/A')
        if content_dict.get('walking surface', '') == 'selected':
            m_and_t_codes.append('D10/G')
        if content_dict.get('transfer 1st choice', ''):
            m_and_t_codes.append('D10/I')

        # Add M&T codes
        for code in m_and_t_codes:
            passed_codes[code] += 1

        # AFO Lining
        afo_lining_codes = []

        # Process AFO Full
        afo_full_material_value = content_dict.get('afo full material', '').lower()

        if afo_full_material_value:
            if afo_full_material_value.startswith('yes'):
                afo_lining_codes.append('D14/E')  # Add D14/E code
                # Extract the material after 'yes'
                afo_full_material = afo_full_material_value[3:].strip()
            else:
                # If 'yes' is not present, assume the entire value is the material
                afo_full_material = afo_full_material_value.strip()
        else:
            afo_full_material = ''  # No material provided

        # Process AFO Calf
        afo_calf_material_value = content_dict.get('afo calf material', '').lower()

        if afo_calf_material_value:
            if afo_calf_material_value.startswith('yes'):
                afo_lining_codes.append('D14/D')  # Add D14/D code
                # Extract the material after 'yes'
                afo_calf_material = afo_calf_material_value[3:].strip()
            else:
                # If 'yes' is not present, assume the entire value is the material
                afo_calf_material = afo_calf_material_value.strip()
        else:
            afo_calf_material = ''  # No material provided

        # Materials for AFO Lining
        lining_materials = {
            'ld eva': 'D14/D',
            "p'zote": 'D14/D',
            'chamois': 'D14/F',
            'leather': 'D14/F',
            'sheepskin': 'D14/F'
        }

        # Check and add codes based on materials
        if afo_full_material in lining_materials:
            afo_lining_codes.append(lining_materials[afo_full_material])

        if afo_calf_material in lining_materials:
            afo_lining_codes.append(lining_materials[afo_calf_material])

        # Add AFO lining codes
        for code in afo_lining_codes:
            passed_codes[code] += 1

        # Pads
        pads_codes = []

        if content_dict.get('arch pads', ''):
            pads_codes.append('D14/C')
        if content_dict.get('navicular pad', ''):
            pads_codes.append('D14/C')

        slip_pads = ['slip pad calf', 'slip pad ankle', 'slip pad foot']
        for pad in slip_pads:
            if content_dict.get(pad, '') == 'yes':
                pads_codes.append('P15')

        # Add pads codes 
        for code in pads_codes:
            passed_codes[code] += 1

        # Ensure 'P15' is added as default if not already added
        if 'P15' not in passed_codes:
            passed_codes['P15'] += 1

        # Apply pair handling for 'P15' independently
        if content_dict.get('afo pair', '') == 'selected':
            passed_codes['P15'] *= 2

        # Slotted Heel Strap
        sides = ['left', 'right']
        for side in sides:
            strap_type_key = f'{side} strap type'
            strap_type = content_dict.get(strap_type_key, '').lower()

            if strap_type == 'y strap':
                passed_codes['D14/A'] += 1
                passed_codes['P15'] += 1
            elif strap_type == 'full as part of ankle lining':
                passed_codes['D14/A'] += 1
                passed_codes['P15'] += 1
            elif strap_type == 'single slotted fix':
                passed_codes['P1'] += 1
                passed_codes['P4'] += 1
                passed_codes['P15'] += 1

        # Additional Information
        additional_info_fields = [
            'additional information',
            'ca&t comments',
            'm&t comments',
            'pcro comments'
        ]
        additional_material_codes = 0
        for field in additional_info_fields:
            comments = content_dict.get(field, '').lower()
            if 'add 3mm' in comments or 'add poron' in comments or 'extend poron' in comments or 'add 3mm poron' in comments:
                additional_material_codes += 1

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

            # Check for any codes in the description not already added
            for word in comments.split():
                if word.upper() in passed_codes:
                    continue
                elif word.upper() in ['D14/C', 'D14C']:
                    passed_codes['D14/C'] += 1

        # Add D14/C code if additional material usage is found
        if additional_material_codes > 0:
            passed_codes['D14/C'] += additional_material_codes

        # --- Pair Handling ---
        # Apply Pair Handling after all codes have been added
        if content_dict.get('afo pair', '') == 'selected':
            # Codes to exclude from pair handling
            codes_to_exclude = ['D10/E', 'D14/A', 'D14/D', 'P1', 'P4', 'D8/D','D8/H','D8/A', 'B41','D8/I', 'D8/U', 'D8/B', 'P15', 'D2/D', 'D2/B', 'D2/A']
            for code in passed_codes:
                if code not in codes_to_exclude:
                    passed_codes[code] *= 2

        # Format the passed codes with counts
        formatted_passed_codes = []
        for code, count in passed_codes.items():
            if count > 1:
                formatted_passed_codes.append(f"{code} x{count}")
            else:
                formatted_passed_codes.append(code)

        # Return the passed codes as a string
        if formatted_passed_codes:
            return ', '.join(f"{code} x{count}" if count > 1 else code for code, count in passed_codes.items())
        else:
            return None  # Return None if no codes were added
        
def generate_modular_codes(self, content):
        """Generates codes based on the content for the Modular model, with tariff logic."""
        from collections import defaultdict
        passed_codes = defaultdict(int)  # Use defaultdict to count occurrences

        # Define lists of clinics for each insole tariff code (edit these lists as needed)
        tariff_tci_clinics = ['east surrey', 'bury cdc', 'ely', 'hinchingbrooke', 'pch',
                            'peterborough city hospital', 'sudbury', 'w.s.h', 'ws', 'wsh', 'stamford', 'pch diab', 'doddington', 'peterborough']
        tariff_simple_clinics = ['bury cdc', 'ely', 'harpenden', 'hinchingbrooke', 'pch',
                                'peterborough city hospital', 'sudbury', 'w.s.h', 'ws', 'wsh', 'stamford', 'pch diab', 'doddington', 'peterborough']
        tariff_polyprop_clinics = ['east surrey', 'bury cdc', 'ely', 'hinchingbrooke', 'pch',
                                'peterborough city hospital', 'sudbury', 'w.s.h', 'ws', 'wsh', 'stamford', 'pch diab', 'doddington', 'peterborough']

        # Define list of clinics for Tariff Modular
        tariff_modular_clinics = ['bury cdc', 'east surrey', 'sudbury', 'w.s.h', 'ws', 'wsh']

        # Split the content into lines
        lines = content.split('\n')

        # Convert lines to a dictionary
        content_dict = {}
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                content_dict[key.strip().lower()] = value.strip().lower()

        clinic_name = content_dict.get('clinic', '').lower()
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
        # If medway:
        # - If simple: add MEDBNS71
        # - Otherwise: add MEDBNS72
        # In all cases: add MEDFOOTWEAR
        if clinic_name == 'medway':
            if insole_type == 'simple':
                passed_codes['MEDBNS71'] += 1
            else:
                passed_codes['MEDBNS72'] += 1

            # Add MEDFOOTWEAR in all medway cases
            passed_codes['MEDFOOTWEAR'] += 1
            # Mark modular tariff as added so filters run later
            modular_tariff_added = True
            insole_tariff_added = True

        # Modular Tariff Check (other clinics)
        if clinic_name in tariff_modular_clinics:
            passed_codes['Tariff Modular'] += 1
            modular_tariff_added = True

        # Insole Tariff Checks
        if clinic_name in tariff_tci_clinics:
            passed_codes['Tariff TCI'] += 1
            insole_tariff_added = True
        elif clinic_name in tariff_simple_clinics:
            passed_codes['Tariff Simple'] += 1
            insole_tariff_added = True
        elif clinic_name in tariff_polyprop_clinics:
            passed_codes['Tariff Polyprop'] += 1
            insole_tariff_added = True

        # Note: Continue normal logic to allow code filtering at the end

        # Last Type Checks
        if content_dict.get('last type', '').strip().lower() == 'wide extra deep':
            count = 1
            if is_pair:
                count = 2
            passed_codes['6mm'] += count

        # Insole Allowance Checks
        allowance_codes = {'3mm', '6mm', '9mm', '12mm'}
        pattern_allowances = {'9mm', '12mm'}

        for key in ['left insole allowance', 'right insole allowance']:
            value = content_dict.get(key, '').strip().lower()
            if value in allowance_codes:
                passed_codes[value] += 1
                if value in pattern_allowances:
                    passed_codes['Pattern'] += 1

        # Sole and Style Checks
        sole_value = content_dict.get('sole', '')
        style_value = content_dict.get('styles', '')

        if sole_value in ('(lcr) lightweight commando sole', 'resin commando sole'):
            if style_value not in ('highland', 'rockingham', 'rockcliffe'):
                passed_codes['BNS62'] += 1

        style = content_dict.get('styles', '').lower()

        sport_styles = {
            'sneaker', 'greenock', 'greeock', 'colwyn', 'lineham', 'hove', 'plymouth', 
            'drayton', 'olympic', 'melton', 'kelso', 'dover', 'shelwyck', 'mowbray'
        } 

        shoe_styles = {
            'trent', 'selby', 'hallam', 'totnes', 'tenby', 'chelsea', 'galway', 'vienna',
            'truro', 'hendon', 'stirling', 'exeter', 'chester', 'shelby'
        }

        boot_styles = {
            'bumper', 'whitby', 'tralee', 'rockingham', 'perth', 'rockliffe',
            'dundee', 'brigg', 'elgin', 'highland'
        }

        # If style is recognized use style lists
        if style in sport_styles:
            passed_codes['Modular Sports'] += 1
        elif style in shoe_styles:
            passed_codes['Modular Shoes'] += 1
        elif style in boot_styles:
            passed_codes['Modular Boots'] += 1
        else:
            # --- ADDED WARNING LOGIC HERE ---
            # The style wasn't found in sport, shoe, or boot sets, so fallback to tick boxes.
            # We'll also build a warning message to show the user that we are “guessing.”
            fallback_styles_used = []

            if content_dict.get('shoes', '') == 'selected':
                passed_codes['Modular Shoes'] += 1
                fallback_styles_used.append('shoes')
            if content_dict.get('boots', '') == 'selected':
                passed_codes['Modular Boots'] += 1
                fallback_styles_used.append('boots')
            if content_dict.get('trainers', '') == 'selected':
                passed_codes['Modular Sports'] += 1
                fallback_styles_used.append('trainers')

            if fallback_styles_used:
                # Create a warning message letting the user know we didn't detect the style
                warning_message = (
                    f"Footwear style not detected!\n"
                    f"• Entered style: '{style}' may be spelled incorrectly.\n"
                    f"• Falling back to tick-box selections: {', '.join(fallback_styles_used)}"
                )
                # Show the pop-up in the same way you handle other warnings
                self.root.after(0, messagebox.showinfo, "Warning", warning_message)
            else:
                # If no tick boxes are also selected, you might want a different warning or default assumption.
                warning_message = (
                    f"Footwear style '{style}' not recognized, and no tick boxes selected. "
                    f"Please verify the footwear style."
                )
                self.root.after(0, messagebox.showinfo, "Warning", warning_message)

        # Check boa/velcro 
        if content_dict.get('boa', '') == 'selected':
            passed_codes['twist fasten'] += 1
        if content_dict.get('velcro', '') == 'selected':
            passed_codes['velcro'] += 1

        # Straps Checks
        for side in ['left', 'right']:
            strap_type_key = f'{side} strap type'
            double_decker_key = f'{side} double decker'

            strap_type = content_dict.get(strap_type_key, '')
            double_decker = content_dict.get(double_decker_key, '')

            if double_decker == 'yes':
                passed_codes['B34'] += 1
            else:
                if strap_type in ('t strap', 'y strap'):
                    passed_codes['B33'] += 1
                elif strap_type in ('spur retaining strap', 'heel retaining strap'):
                    passed_codes['B8'] += 1

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

        # Rocker Type (B17)
        rocker_keys = ['left rocker type', 'right rocker type']
        for key in rocker_keys:
            if content_dict.get(key, '') in ('plr', 'standard', 'two point'):
                passed_codes['B17'] += 1

        # Wedges
        wedges_keys = [
            'left wedges heel lateral',
            'left wedges heel medial',
            'right wedges heel medial',
            'right wedges heel lateral',
            'left wedges sole lateral',
            'left wedges sole medial',
            'right wedges sole medial',
            'right wedges sole lateral'
        ]

        for key in wedges_keys:
            if content_dict.get(key, '') == 'selected':
                if 'heel' in key:
                    passed_codes['B25'] += 1
                elif 'sole' in key:
                    passed_codes['B18'] += 1

        # Floated
        floated_keys = [
            'right floated heel lateral',
            'right floated heel medial',
            'left floated heel medial',
            'left floated heel lateral',
            'left floated sole lateral',
            'left floated sole medial',
            'right floated sole lateral',
            'right floated sole medial'
        ]

        for key in floated_keys:
            if content_dict.get(key, '') == 'selected':
                if 'heel' in key:
                    passed_codes['B25'] += 1
                elif 'sole' in key:
                    passed_codes['B19'] += 1

        # beyond this point is the insole logic
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
                    passed_codes['BNS45'] += 1

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
            'left medial rearfoot posting',
            'left lateral rearfoot posting',
            'right medial rearfoot posting',
            'right lateral rearfoot posting',
            'left medial forefoot posting',
            'left lateral forefoot posting',
            'right medial forefoot posting',
            'right lateral forefoot posting',
        ]

        for key in posting_keys:
            if content_dict.get(key, '') == 'selected':
                code = 'A45' if insole_type == 'cradle' else 'B56'
                passed_codes[code] += 1

        # Insole coding section - MATHS!
        x = 0
        if insole_type == 'simple':
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

        if x >= 2:
            code = 'A44C' if insole_type == 'cradle' else 'B55C'
            passed_codes[code] += 1
        elif x == 1:
            code = 'A44B' if insole_type == 'cradle' else 'B55B'
            passed_codes[code] += 1
        elif x == 0:
            code = 'A44A' if insole_type == 'cradle' else 'B55A'
            passed_codes[code] += 1

        if content_dict.get('pair', '') == 'selected':
            codes_to_double_general = [
                'twist fasten', 'BNS62', 'velcro'
            ]
            for code in codes_to_double_general:
                if code in passed_codes:
                    passed_codes[code] *= 2

        if content_dict.get('insole pair', '') == 'selected':
            codes_to_double_insole = [
                'A10', 'B54C', 'B40B', 'B54A',
                'A44A', 'A44B', 'A44C', 'B55A', 'B55B', 'B55C', 'B54B'
            ]
            for code in codes_to_double_insole:
                if code in passed_codes:
                    passed_codes[code] *= 2

        # Now we must double MEDBNS71 or MEDBNS72 if it's a pair, but NOT MEDFOOTWEAR
        if is_pair:
            if 'MEDBNS71' in passed_codes:
                passed_codes['MEDBNS71'] *= 2
            if 'MEDBNS72' in passed_codes:
                passed_codes['MEDBNS72'] *= 2
            # Do not double MEDFOOTWEAR

        # --- Filtering Step ---
        insole_filter_codes = {
            'A10', 'B54C', 'B40B', 'B54A', 'A44A', 'A44B', 'A44C',
            'B55A', 'B55B', 'B55C', 'B56', 'A45', 'BNS45', 'A47',
            'B51', 'B50', 'A46', 'A20', 'B20', 'D8A', 'B43', 'B41', 'B54B'
        }

        modular_filter_codes = {
            '6mm', 'Pattern', 'BNS62', 'Modular Shoes', 'Modular Boots',
            'Modular Sports', 'twist fasten', 'velcro', 'B34', 'B33', 'B8',
            'B30', 'B31', 'B25', 'B17', 'B18', 'B19'
        }

        if insole_tariff_added:
            for c in insole_filter_codes:
                if c in passed_codes:
                    del passed_codes[c]

        if modular_tariff_added:
            for c in modular_filter_codes:
                if c in passed_codes:
                    del passed_codes[c]

        # Format the passed codes with counts
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