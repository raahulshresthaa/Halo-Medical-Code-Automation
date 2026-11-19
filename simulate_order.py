# simulate_order.py
"""Create the SharePoint production order for an order the app has already run - no NAV needed.

Give it a results log from the app. It reads the real sales order number, auto doc ref, order
category, delivery date and patient from the log (the "Uploaded Order Data" block the app
writes), then makes the same row the app would make.

    python simulate_order.py --pick                a file box opens to choose the log, DRY RUN
    python simulate_order.py --pick --live         ... and really creates the row
    python simulate_order.py <log> [<log> ...]     the same, naming the log(s) here
    python simulate_order.py                       built-in sample forms with made-up SOs (DRY RUN)

DRY RUN is the default: it shows the row and writes nothing. --live writes it. If the sales order
is already on the list it says so and does not make a second row.

NAV isn't asked, so what only NAV knows is filled in from the log if there (logs from this branch
keep NAV's reply on a [NAV ORDER] line), else:
          --nav-clinic "Name as NAV shows it"   (otherwise the form's clinic name is used)
          --nav-patient-no 1234567              (otherwise PatientNumber is left blank)
          --so TEST-SO-0001                     made-up SO, only for forms with none in the log
"""
import argparse
import ast
import collections
import datetime
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)  # the sp_*.txt settings are read from the current folder
sys.path.insert(0, HERE)

from sharepoint_production import (create_production_order,  # noqa: E402
                                    nav_clinic_name, nav_patient_number, quantity_and_extremity)


def _from_main(*names):
    """Pull plain functions out of main.py without running it (it opens the GUI on import)."""
    src = open(os.path.join(HERE, 'main.py'), encoding='utf-8').read()
    wanted = [n for n in ast.parse(src).body
              if isinstance(n, ast.FunctionDef) and n.name in names]
    scope = {'MODEL_IDS': collections.defaultdict(lambda: 'x', {'Insoles': 'Insoles'}),
             'os': os, 're': re}
    exec(compile(ast.Module(body=wanted, type_ignores=[]), 'main.py', 'exec'), scope)
    return [scope[n] for n in names]


determine_order_category_code, move_number_after_name = _from_main(
    'determine_order_category_code', 'move_number_after_name')

SAMPLES = {
    'Simple, pair (patient number after name)': """AutoDocRef: TEST0001
Clinic: Lister
clinician: Nicola Hood - Lister
patient: Jane Smith 1234567
insole type simple: selected
insole pair: selected
order quantity: 1""",
    'TCI, left only, x2 (number between names)': """AutoDocRef: TEST0002
Clinic: Lister
patient: Jane 1234567 Smith
insole type tci: selected
insole type uni lat l: selected
order quantity: 2""",
    'Cradle, right only (initials + number)': """AutoDocRef: TEST0003
Clinic: Lister
patient: SG RWH228885
insole type cradle: selected
insole type uni lat r: selected
order quantity: 1""",
    'Hand mould, pair': """AutoDocRef: TEST0004
Clinic: Lister
patient: HH 4933544
insole type hand mould: selected
insole pair: selected
order quantity: 1""",
    'Simple with poly base (becomes hand mould)': """AutoDocRef: TEST0005
Clinic: Lister
patient: No number here
insole type simple: selected
base poly: selected
insole pair: selected
order quantity: 1""",
}


def fields_of(text):
    d = {}
    for line in text.splitlines():
        if ':' in line:
            k, v = line.split(':', 1)
            d[k.strip().lower()] = v.strip()
    return d


def from_log(text):
    """What the app wrote to a results log after it uploaded the order (all optional)."""
    out = {}
    m = re.search(r'Created Sales Order:\s*(\S+)', text)
    if m:
        out['so'] = m.group(1)
    for key, name in (('Requested_Delivery_Date', 'delivery'), ('Order_Category_Code', 'category'),
                      ('Pad_No', 'auto_doc'), ('Patient_Name', 'patient')):
        m = re.search(r'"%s":\s*"([^"]*)"' % key, text)
        if m:
            out[name] = m.group(1)
    m = re.search(r'^\[NAV ORDER\]\s*(\{.*\})\s*$', text, re.M)
    if m:
        try:
            out['nav_order'] = ast.literal_eval(m.group(1))
        except (ValueError, SyntaxError):
            pass
    return out


def run(label, text, args):
    f = fields_of(text)
    log = from_log(text)
    patient = log.get('patient') or f.get('patient', '')
    if patient.lower().startswith('name'):
        patient = patient[4:].lstrip(': ').strip()
    patient = move_number_after_name(patient or 'Unknown')
    category = log.get('category') or determine_order_category_code('Insoles', f)
    qty, side = quantity_and_extremity(text)
    # NAV's reply: the log's [NAV ORDER] line if it has one, else what was given on the command line.
    nav_order = log.get('nav_order') or {'Sell_to_Customer_Name': args.nav_clinic,
                                         'Patient_No': args.nav_patient_no}
    clinic = nav_clinic_name(nav_order) or f.get('clinic', '')
    so = log.get('so') or args.so
    delivery = log.get('delivery') or (datetime.date.today() + datetime.timedelta(days=7)).strftime('%Y-%m-%d')
    auto_doc = log.get('auto_doc') or f.get('autodocref', 'N/A')

    print('=' * 78)
    print(label)
    print(f"  from log  : SO {so} ({'real, from the log' if log.get('so') else 'made up'}), "
          f"delivery {delivery}, category {category}")
    print(f"  form says : patient='{patient}'  order quantity={f.get('order quantity', '-')}")
    ok, msg = create_production_order(
        so, auto_doc, clinic, category, delivery, qty, side, nav_patient_number(nav_order),
        dry_run=not args.live, form_content=text)
    print(('  OK  ' if ok else '  FAILED  ') + msg)
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument('logs', nargs='*', help='results_log files to replay (default: built-in samples)')
    ap.add_argument('--pick', action='store_true', help='choose the log file(s) in a file box')
    ap.add_argument('--live', action='store_true', help='really write to the SharePoint list')
    ap.add_argument('--nav-clinic', default='', help='clinic name as NAV shows it')
    ap.add_argument('--nav-patient-no', default='', help='patient number as NAV shows it')
    ap.add_argument('--so', default='TEST-SO-0001', help='made-up sales order number')
    args = ap.parse_args()
    if args.pick:
        from tkinter import Tk, filedialog
        Tk().withdraw()
        args.logs = list(filedialog.askopenfilenames(
            title='Choose the results log(s) to send to SharePoint',
            filetypes=[('Results logs', '*.txt'), ('All files', '*.*')])) or sys.exit('No file chosen.')

    jobs = ([(os.path.basename(p), open(p, encoding='utf-8', errors='replace').read())
             for p in args.logs] or list(SAMPLES.items()))
    if args.live:
        print("LIVE: this writes real rows to the SharePoint list. Delete them afterwards.")
    ok = all([run(label, text, args) for label, text in jobs])
    if not args.live:
        print('\nDry run only - nothing was written. Add --live to create the row(s).')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
