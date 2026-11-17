# simulate_order.py
"""Test the NAV -> SharePoint hand-off without NAV.

Feeds a form through the app's own mapping (the real functions, taken from main.py) with a
made-up Sales Order number, and shows what would go on the SharePoint Production Orders list.

    python simulate_order.py                       built-in sample forms, DRY RUN (writes nothing)
    python simulate_order.py path\\to\\results_log_XXXX_insoles.txt   a real day's log, DRY RUN
    python simulate_order.py <log> --live          really create the row on the list (a test row,
                                                   SO 'TEST-SO-...'; delete it by hand afterwards)

Options:  --nav-clinic "Name as NAV shows it"   (stands in for what NAV sends back on a real run)
          --nav-patient-no 1234567              the patient number NAV shows back (blank if NAV sends none)
          --so TEST-SO-0001                     the made-up sales order number
"""
import argparse
import ast
import collections
import datetime
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


def run(label, text, args):
    f = fields_of(text)
    patient = f.get('patient', '')
    if patient.lower().startswith('name'):
        patient = patient[4:].lstrip(': ').strip()
    patient = move_number_after_name(patient or 'Unknown')
    category = determine_order_category_code('Insoles', f)
    qty, side = quantity_and_extremity(text)
    # Stands in for NAV's reply to creating the order.
    nav_order = {'Sell_to_Customer_Name': args.nav_clinic, 'Patient_No': args.nav_patient_no}
    clinic = nav_clinic_name(nav_order) or f.get('clinic', '')
    delivery = (datetime.date.today() + datetime.timedelta(days=7)).strftime('%Y-%m-%d')
    auto_doc = f.get('autodocref', 'N/A')

    print('=' * 78)
    print(label)
    print(f"  form says : patient='{patient}'  order quantity={f.get('order quantity', '-')}  "
          f"-> NAV category {category}")
    ok, msg = create_production_order(
        args.so, auto_doc, clinic, category, delivery, qty, side, nav_patient_number(nav_order),
        dry_run=not args.live)
    print(('  OK  ' if ok else '  FAILED  ') + msg)
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument('logs', nargs='*', help='results_log files to replay (default: built-in samples)')
    ap.add_argument('--live', action='store_true', help='really write to the SharePoint list')
    ap.add_argument('--nav-clinic', default='', help='clinic name as NAV shows it')
    ap.add_argument('--nav-patient-no', default='', help='patient number as NAV shows it')
    ap.add_argument('--so', default='TEST-SO-0001', help='made-up sales order number')
    args = ap.parse_args()

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
