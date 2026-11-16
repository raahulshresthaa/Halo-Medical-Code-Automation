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

import requests

# Our name for each value -> the SharePoint internal column name.
COLUMNS = {
    'prod_no': 'Title',
    'sales_order': 'SONo',
    'auto_doc': 'PADNo',
    'clinic': 'ClinicName',
    'quantity': 'Quantity',
    'orthosis_type': 'OrthosisType',
    'orthosis_category': 'OrthosisCategory',
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
}

# Values that never change for a new insole order (matches the Pre-Production row on the list).
# Every column on this list is text, so numbers go as strings. The creation date is the list's
# own Created field, which SharePoint fills in at upload.
FIXED_VALUES = {
    'classification': 'New',
    'quality_checked': 'No',
    'location': 'Pre-Production',
    'current_process': 'Pre-Production',
    'current_stage_no': '1',
    'site_location': 'Wellingborough (Halo)',
    'prod_dates_added': 'No',
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


def _split(prod_no):
    """'PO-00123' -> ('PO-', 123, 5). None if there is no trailing number."""
    m = re.match(r'^(.*?)(\d+)$', str(prod_no or '').strip())
    return (m.group(1), int(m.group(2)), len(m.group(2))) if m else None


def _next_prod_no(s, headers):
    """Highest production number on the list plus one, keeping its prefix and zero padding."""
    col = COLUMNS['prod_no']
    best = None
    for item in _all_fields(s, headers, [col]):
        parts = _split(item.get('fields', {}).get(col))
        if parts and (best is None or parts[1] > best[1]):
            best = parts
    if best is None:
        raise ValueError("No existing production number on the list to count on from. "
                         "Create the first one by hand so the format is known.")
    prefix, number, width = best
    return f"{prefix}{number + 1:0{width}d}"


def quantity_and_extremity(content):
    """Read quantity and side from the form text ('key: value' lines).

    A pair is quantity 2 and 'Bilateral' (as on the list); a single is 1 and 'Right' or 'Left'.
    'order quantity' on the form multiplies it. If the form doesn't say which side, extremity
    comes back '' and is left blank on the list rather than guessed.
    """
    d = {}
    for line in (content or '').split(chr(10)):
        if ':' in line:
            k, v = line.split(':', 1)
            d[k.strip().lower()] = v.strip().lower()
    on = lambda *keys: any(d.get(k) == 'selected' for k in keys)
    if on('insole pair', 'pair'):
        count, side = 2, 'Bilateral'
    elif on('insole type uni lat r', 'insole rt', 'rt', 'right'):
        count, side = 1, 'Right'
    elif on('insole type uni lat l', 'insole lt', 'lt', 'left'):
        count, side = 1, 'Left'
    else:
        count, side = 1, ''
    try:
        multiple = max(1, int(float(d.get('order quantity', '1').replace('x', '').strip() or 1)))
    except ValueError:
        multiple = 1
    return count * multiple, side


def create_production_order(sales_order_no, auto_doc_ref, clinic, order_category_code,
                            request_delivery_date, quantity=1, extremity=''):
    """Add the production order. Returns (ok, message). Never raises."""
    try:
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

        simple = (order_category_code or '').upper() == 'SIMPLE INSOLE'
        delivery = f"{request_delivery_date}T00:00:00Z"
        values = {
            'sales_order': sales_order_no,
            'auto_doc': auto_doc_ref,
            'clinic': clinic,
            'quantity': str(quantity),
            'orthosis_type': 'Insole Simple' if simple else 'CAD',
            'extremity': extremity,
            'delivery_date': delivery,
            'delivery_date_original': delivery,
            **FIXED_VALUES,
        }
        if not simple:
            values['orthosis_category'] = 'CAD Insoles'
        values = {k: v for k, v in values.items() if v not in (None, '')}

        for attempt in range(3):
            prod_no = _next_prod_no(s, headers)
            body = {'fields': {COLUMNS[k]: v for k, v in values.items()}}
            body['fields'][COLUMNS['prod_no']] = prod_no
            r = requests.post(_items_url(s), headers=headers, json=body, timeout=TIMEOUT)
            if r.status_code not in (200, 201):
                return False, (f"SharePoint production order not created for {sales_order_no}: "
                               f"{r.status_code} {r.text[:300]}")
            my_id = int(r.json()['id'])
            # Two people uploading at the same moment can be handed the same number. If anyone
            # got it before this item, take ours off and try the next number.
            pc = COLUMNS['prod_no']
            clash = [int(i['id']) for i in _all_fields(s, headers, [pc])
                     if str(i.get('fields', {}).get(pc, '')).strip() == prod_no]
            if len(clash) > 1 and my_id != min(clash):
                requests.delete(f"{_items_url(s)}/{my_id}", headers=headers, timeout=TIMEOUT)
                continue
            return True, f"Created SharePoint production order {prod_no} for {sales_order_no}."
        return False, f"SharePoint production order not created for {sales_order_no}: production number kept clashing."
    except Exception as e:
        return False, f"SharePoint production order not created for {sales_order_no}: {type(e).__name__}: {e}"
