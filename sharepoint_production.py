# sharepoint_production.py
"""Creates a Production Order item on the SharePoint list when an Insole order goes to NAV.

Uses the Microsoft Graph API with an Azure app registration (client credentials). Settings are
kept in base64 .txt files next to the app, the same way NavApi.py keeps the NAV login, and are
git-ignored:

    sp_tenant_id.txt      Azure tenant (directory) ID
    sp_client_id.txt      Azure app (client) ID
    sp_client_secret.txt  Azure app client secret
    sp_site_id.txt        Graph site ID, e.g.  contoso.sharepoint.com,<siteGuid>,<webGuid>
    sp_list_id.txt        The Production Orders list ID (GUID) or its display name

If any file is missing, nothing is created and the NAV upload is NOT affected - the caller gets
a (False, message) back and shows it as a warning. This module never raises into the upload.

!! The column names below are the SharePoint INTERNAL names. The screenshot shows the display
   names; if any internal name differs (check List settings > click the column > the URL ends
   in Field=<InternalName>), change it in COLUMNS - nothing else needs editing.
"""
import base64
import datetime
import os
import re
import sqlite3
import sys

import requests

# Our name for each value -> the SharePoint internal column name.
COLUMNS = {
    'prod_no': 'Title',
    'sales_order': 'SONo',
    'auto_doc': 'PADNo',
    'patient_number': 'PatientNumber',
    'clinic': 'ClinicName',
    'quantity': 'Quantity',
    # Swapped on purpose: our "type" values (CAD Insoles...) belong in the list's OrthosisCategory
    # column and our "category" values (CAD Insoles - Additions...) in its OrthosisType column.
    'orthosis_type': 'OrthosisCategory',
    'orthosis_category': 'OrthosisType',
    'extremity': 'Extremity',
    'classification': 'ProductionClassification',
    'delivery_date': 'DeliveryDate',
    'delivery_date_original': 'DeliveryDateOriginal',
    'quality_checked': 'QualityChecked',
    'location': 'Location',
    'current_process': 'CurrentProcess',
    'current_stage_no': 'CurrentStageNo',
    'site_location': 'SiteLocation',
    'prod_dates_added': 'ProdDatesAdded',
    'data_version': 'DataVersion',
    'vers': 'Vers',
    'delivery_method': 'DeliveryMethod',
    'delivery_location': 'DeliveryLocation',
    'awaiting_go_ahead': 'AwaitingGoAhead',
    'priority': 'Priority',
    'gallery_filter': 'GalleryFilter',
    'path': 'ProductionPath',
    'cadcam': 'Cadcam',
    'cadcam_date': 'CadcamDate',
    'cadcam_date_original': 'CadcamDateOriginal',
    'insoles': 'Insoles',
    'insole_date': 'InsoleDate',
    'insole_date_original': 'InsoleDateOriginal',
    'plaster': 'Plaster',
    'metal': 'Metal',
    'footwear': 'Footwear',
    'cadcam_status': 'CadcamStatus',
    'insoles_status': 'InsoleStatus',
    'lined': 'Lined',
    'insole_si': 'InsoleSi',
    'cadcam_si': 'CadcamSi',
    'bluebox': 'BlueBox',
    'moulding': 'Moulding',
    'machining': 'Machining',
    'finishing': 'Finishing',
    'plaster_si': 'PlasterSi',
    'metal_si': 'MetalSi',
    'footwear_si': 'FootwearSi',
    'moulding_si': 'MouldingSi',
    'machining_si': 'MachiningSi',
    'finishing_si': 'FinishingSi',
}

# Values that never change for a new insole order (matches the Pre-Production row on the list).
# Every column on this list is text, so numbers go as strings. The creation date is the list's
# own Created field, which SharePoint fills in at upload.
FIXED_VALUES = {
    'classification': 'New',
    'quality_checked': 'No',
    'location': 'Pre-Production',
    'current_process': 'Not started',s
    'current_stage_no': '1',
    'site_location': 'Wellingborough (Halo)',
    'prod_dates_added': 'No',
    'data_version': 'Version 3',
    'vers': '3.0',
    'delivery_method': 'Post',
    'awaiting_go_ahead': 'No',
    'priority': '1',
    'gallery_filter': 'All',
}

GRAPH = 'https://graph.microsoft.com/v1.0'
TIMEOUT = 20


def _read(filename):
    path = os.path.join(os.getcwd(), filename)
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'rb') as f:
            return base64.b64decode(f.read()).decode('utf-8').strip() or None
    except Exception:
        return None


def _settings():
    names = ['sp_tenant_id', 'sp_client_id', 'sp_client_secret', 'sp_site_id', 'sp_list_id']
    values = {n: _read(n + '.txt') for n in names}
    missing = [n + '.txt' for n, v in values.items() if not v]
    return values, missing


def _token(s):
    r = requests.post(
        f"https://login.microsoftonline.com/{s['sp_tenant_id']}/oauth2/v2.0/token",
        data={'client_id': s['sp_client_id'], 'client_secret': s['sp_client_secret'],
              'scope': 'https://graph.microsoft.com/.default', 'grant_type': 'client_credentials'},
        timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()['access_token']


def _items_url(s):
    return f"{GRAPH}/sites/{s['sp_site_id']}/lists/{s['sp_list_id']}/items"


def _all_fields(s, headers, fields):
    """Every item's chosen fields, following Graph paging."""
    url = f"{_items_url(s)}?$expand=fields($select={','.join(fields)})&$top=999"
    while url:
        r = requests.get(url, headers=headers, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
        for item in data.get('value', []):
            yield item
        url = data.get('@odata.nextLink')


# Production number = 'PROD' + site letter + 2-digit year + '-' + the list item's own ID, 6 digits.
# e.g. the 10th line on the list, from Wellingborough, in 2026 -> PRODW26-000010
SITE_LETTERS = {'wellingborough': 'W', 'aldershot': 'A', 'lewes': 'F'}


def site_letter(site_location):
    """'Wellingborough (Halo)' -> 'W'. Raises if the site isn't one we know."""
    name = str(site_location or '').lower()
    for site, letter in SITE_LETTERS.items():
        if site in name:
            return letter
    raise ValueError(f"Unknown site '{site_location}' - add it to SITE_LETTERS.")


def prod_no_for(item_id, site_location=None, today=None):
    """PRODW26-000010 for item ID 10 at Wellingborough in 2026."""
    today = today or datetime.date.today()
    letter = site_letter(site_location or FIXED_VALUES['site_location'])
    return f"PROD{letter}{today.year % 100:02d}-{int(item_id):06d}"


def _form_fields(content):
    d = {}
    for line in (content or '').split(chr(10)):
        if ':' in line:
            k, v = line.split(':', 1)
            d[k.strip().lower()] = v.strip().lower()
    return d


def quantity_and_extremity(content):
    """Read quantity and side from the form text ('key: value' lines).

    Quantity is the form's 'order quantity' as written (a pair is NOT doubled - the side says
    Bilateral). Side is 'Bilateral' (insole pair), 'Right' (uni-lat R) or 'Left' (uni-lat L). If
    the form doesn't say which side, it comes back '' and is left blank on the list.
    """
    d = _form_fields(content)
    on = lambda *keys: any(d.get(k) == 'selected' for k in keys)
    if on('insole pair', 'pair'):
        side = 'Bilateral'
    elif on('insole type uni lat r', 'insole rt', 'rt', 'right'):
        side = 'Right'
    elif on('insole type uni lat l', 'insole lt', 'lt', 'left'):
        side = 'Left'
    else:
        side = ''
    try:
        quantity = max(1, int(float(d.get('order quantity', '1').replace('x', '').strip() or 1)))
    except ValueError:
        quantity = 1
    return quantity, side


def nav_patient_number(nav_order):
    """The patient number NAV gives the created order (its Patient_No field), '' if none."""
    return str((nav_order or {}).get('Patient_No') or '').strip()


# Our category key (also the PATHS key) -> the name on the OrthosisTypes list (OrthosisType column).
ORTHOSIS_TYPE_NAMES = {
    'CAD Insoles':                           'Insoles CAD - ALD',
    'CAD Insoles - Additions':               'Insoles CAD - Additions',
    'CAD Insoles - Covering':                'Insoles CAD - Covering',
    'CAD Insoles - Additions - Covering':    'Insoles CAD - Additions - Covering',
    'Simple Insoles':                        'Simple Insoles',
    'Simple Insoles - Additions':            'Simple Insoles - Additions',
    'Simple Insoles - Covering':             'Simple Insoles - Covering',
    'Simple Insoles - Additions - Covering': 'Simple Insoles - Additions - Covering',
}

# NAV order categories that don't go on the SharePoint list (not a category there yet).
IGNORED_CATEGORY_CODES = ('MOULDED INSOLE',)

# What the NAV order category means for the Orthosis Category column.
ORTHOSIS_TYPES = {
    'SIMPLE INSOLE': 'Simple Insoles',    # simple insole
    'MILLED INSOLES': 'CAD Insoles',     # cradle / TCI
}


# Parts of the form that count as "Additions" (cut outs + additions boxes) or "Covering"
# (lining + top cover). Matched against the form's lower-case field names.
_ADDITION_KEYS = ('met head', 'all mets', 'met ray', 'custom hole and plug', 'navicular sweet spot',
                  'additional info cut outs', 'valgus pad', 'heel pad', 'mortons extension',
                  'met bar', 'met dome', 'additional info additions')
_COVERING_KEYS = ('soft poron', 'medium poron', 'firm memory foam poron', 'vinyl black', 'on steam',
                  'microfibre brown', 'multi ld eva', 'black ld eva', 'spenco',
                  'additional info top cover')
_EMPTY_VALUES = ('', 'unselected', 'not selected', 'none', 'n/a', '0', 'false', 'no')


def form_orthosis(content):
    """(OrthosisType, OrthosisCategory) read from the form, or (None, None) if the form isn't
    a TCI or Simple insole (Hand Moulded and Cradle are not handled yet).

    TCI -> 'CAD Insoles'; Simple -> 'Simple Insoles' (the OrthosisCategory column). The second
    value returned is the full name with any suffix, e.g. 'CAD Insoles - Additions' (OrthosisType).
    Anything ticked or filled in under Cut Outs / Additions adds ' - Additions'; anything under
    Lining / Top Cover adds ' - Covering'; both gives ' - Additions - Covering'.
    """
    d = _form_fields(content)
    if d.get('insole type tci') == 'selected':
        orthosis_type, category = 'CAD Insoles', 'CAD Insoles'
    elif d.get('insole type simple') == 'selected':
        orthosis_type, category = 'Simple Insoles', 'Simple Insoles'
    else:
        return None, None

    def used(keys):
        return any(v not in _EMPTY_VALUES and any(k in name for k in keys)
                   for name, v in d.items())

    if used(_ADDITION_KEYS):
        category += ' - Additions'
    if used(_COVERING_KEYS):
        category += ' - Covering'
    return orthosis_type, category


# Category -> (path, first location, first process, CAD/CAM offset, Insoles offset), copied from
# the Production Paths list. Offsets are days from the required delivery date (negative = before).
# A CAD/CAM offset of None means the order doesn't go through CAD/CAM.
PATHS = {
    'CAD Insoles':                          ('PATHINS1', 'CAD/CAM', 'Digital input', -8, -3),
    'CAD Insoles - Additions':              ('PATHINS2', 'CAD/CAM', 'Digital input', -7, -2),
    'CAD Insoles - Covering':               ('PATHINS3', 'CAD/CAM', 'Digital input', -8, -3),
    'CAD Insoles - Additions - Covering':   ('PATHINS4', 'CAD/CAM', 'Digital input', -7, -2),
    'Simple Insoles':                       ('PATHINS5', 'Insoles', 'Insole Shaping', None, -3),
    'Simple Insoles - Additions':           ('PATHINS6', 'Insoles', 'Insole Shaping', None, -2),
    'Simple Insoles - Covering':            ('PATHINS7', 'Insoles', 'Insole Shaping', None, -3),
    'Simple Insoles - Additions - Covering': ('PATHINS8', 'Insoles', 'Insole Shaping', None, -2),
}


def _holidays_db_path():
    base = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) \
        else os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, 'databases', 'holidays.db')


def holiday_ranges():
    """The (start, end) holiday blackout ranges the app keeps in holidays.db, as dates.

    Same table the Holidays tab edits. Returns [] if the file or table isn't there, so a missing
    holiday list never stops a production order being created.
    """
    path = _holidays_db_path()
    if not os.path.exists(path):
        return []
    ranges = []
    try:
        conn = sqlite3.connect(path)
        try:
            for start_s, end_s in conn.execute("SELECT start_date, end_date FROM holidays"):
                try:
                    ranges.append((datetime.date.fromisoformat(start_s),
                                   datetime.date.fromisoformat(end_s)))
                except (TypeError, ValueError):
                    continue
        finally:
            conn.close()
    except sqlite3.Error:
        return []
    return ranges


def next_working_day(d, ranges=()):
    """`d` itself if it is a weekday outside every holiday range, else the next day that is."""
    for _ in range(3660):   # safety cap so a bad open-ended range can't loop forever
        if d.weekday() < 5 and not any(start <= d <= end for start, end in ranges):
            return d
        d += datetime.timedelta(days=1)
    return d


def _offset_date(delivery_date, days, ranges=()):
    """The delivery date (YYYY-MM-DD) moved by `days`, then rolled forward past weekends and
    holiday blackouts to the next working day, as the list's date text."""
    d = datetime.date.fromisoformat(str(delivery_date)[:10]) + datetime.timedelta(days=days)
    return f"{next_working_day(d, ranges).isoformat()}T00:00:00Z"


def build_values(sales_order_no, auto_doc_ref, clinic, order_category_code,
                 request_delivery_date, quantity=1, extremity='', patient_no='', form_content='',
                 holidays=None):
    """The columns to write for one new insole order (blank ones left out).

    The CAD/CAM and Insole dates skip weekends and the app's holiday blackouts (moved to the next
    working day). `holidays` is a list of (start, end) dates; None reads holidays.db.
    """
    if holidays is None:
        holidays = holiday_ranges()
    orthosis_type = ORTHOSIS_TYPES.get((order_category_code or '').upper(), 'CAD Insoles')
    form_type, form_category = form_orthosis(form_content)
    if form_type:
        orthosis_type = form_type
    delivery = f"{request_delivery_date}T00:00:00Z"
    # A bilateral order is a pair, so each one counts as 2 insoles: 1 pair = 2, 2 pairs = 4.
    if extremity == 'Bilateral':
        quantity = int(quantity) * 2
    values = {
        'sales_order': sales_order_no,
        'auto_doc': auto_doc_ref,
        'patient_number': patient_no,
        'clinic': clinic,
        'quantity': str(quantity),
        'orthosis_type': orthosis_type,
        'extremity': extremity,
        'delivery_date': delivery,
        'delivery_date_original': delivery,
        **FIXED_VALUES,
    }
    values['delivery_location'] = clinic   # same as ClinicName
    path_key = form_category or ('CAD Insoles' if orthosis_type == 'CAD Insoles' else None)
    if path_key:
        # The OrthosisType column holds the OrthosisTypes list's own names, not our path keys.
        values['orthosis_category'] = ORTHOSIS_TYPE_NAMES.get(path_key, path_key)
    route = PATHS.get(path_key)
    if route:
        path, location, process, cadcam_offset, insole_offset = route
        # CurrentProcess stays 'Not Started' (from FIXED_VALUES); `process` is the first step.
        values.update(path=path, location=location, insoles='Yes',
                      prod_dates_added='Yes', cadcam='No', plaster='No', metal='No',
                      footwear='No', insoles_status='Not Completed', lined='No',
                      insole_si='No', cadcam_si='No')
        # Departments this order doesn't use, and every department's "Si" flag, are all No.
        for name in ('bluebox', 'moulding', 'machining', 'finishing'):
            values[name] = 'No'
        for name in ('plaster', 'metal', 'footwear', 'moulding', 'machining', 'finishing'):
            values[name + '_si'] = 'No'
        values['insole_date'] = values['insole_date_original'] = _offset_date(
            request_delivery_date, insole_offset, holidays)
        if cadcam_offset is not None:
            values['cadcam'] = 'Yes'
            values['cadcam_status'] = 'Not Completed'
            values['cadcam_date'] = values['cadcam_date_original'] = _offset_date(
                request_delivery_date, cadcam_offset, holidays)
    return {k: v for k, v in values.items() if v not in (None, '')}


def create_production_order(sales_order_no, auto_doc_ref, clinic, order_category_code,
                            request_delivery_date, quantity=1, extremity='', patient_no='',
                            form_content=''):
    """Add the production order. Returns (ok, message). Never raises."""
    try:
        # Hand moulded (and poly / carbon base) insoles aren't a SharePoint category yet - ignore.
        if (order_category_code or '').upper() in IGNORED_CATEGORY_CODES:
            return True, (f"Hand moulded insole - no SharePoint production order is made for "
                          f"{sales_order_no} yet.")
        s, missing = _settings()
        if missing:
            return False, "SharePoint production order not created - missing " + ", ".join(missing)
        token = _token(s)
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

        so_col = COLUMNS['sales_order']
        # Already there for this SO (a re-run) - don't make a second one.
        for item in _all_fields(s, headers, [so_col, COLUMNS['prod_no']]):
            fields = item.get('fields', {})
            if str(fields.get(so_col, '')).strip() == sales_order_no:
                return True, (f"Production order {fields.get(COLUMNS['prod_no'])} already exists "
                              f"on SharePoint for {sales_order_no} - not created again.")

        values = build_values(sales_order_no, auto_doc_ref, clinic, order_category_code,
                              request_delivery_date, quantity, extremity, patient_no, form_content)

        # The production number is built from the item's own ID, which SharePoint hands out
        # when the item is created - so create it first, then put the number in the Title.
        # Two people at once can't clash: every item has its own ID.
        body = {'fields': {COLUMNS[k]: v for k, v in values.items()}}
        body['fields'][COLUMNS['prod_no']] = 'PENDING'
        r = requests.post(_items_url(s), headers=headers, json=body, timeout=TIMEOUT)
        if r.status_code not in (200, 201):
            return False, (f"SharePoint production order not created for {sales_order_no}: "
                           f"{r.status_code} {r.text[:300]}")
        item_id = int(r.json()['id'])
        prod_no = prod_no_for(item_id)
        r = requests.patch(f"{_items_url(s)}/{item_id}/fields", headers=headers,
                           json={COLUMNS['prod_no']: prod_no}, timeout=TIMEOUT)
        if r.status_code not in (200, 201):
            requests.delete(f"{_items_url(s)}/{item_id}", headers=headers, timeout=TIMEOUT)
            return False, (f"SharePoint production order not created for {sales_order_no}: "
                           f"could not set the production number ({r.status_code} {r.text[:200]}).")
        return True, f"Created SharePoint production order {prod_no} for {sales_order_no}."
    except Exception as e:
        return False, f"SharePoint production order not created for {sales_order_no}: {type(e).__name__}: {e}"
