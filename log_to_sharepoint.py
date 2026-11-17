# log_to_sharepoint.py
"""A small window: drag results logs from the app onto it and it makes the SharePoint production
order for each - no NAV needed. Same job as simulate_order.py, with drag and drop.

Start it with:   python log_to_sharepoint.py
The box is ticked "DRY RUN" to begin with: it shows the row and writes nothing. Untick it to really
create the rows on the SharePoint list.
"""
import argparse
import contextlib
import io
import os
import sys
import tkinter as tk
from tkinter import filedialog, scrolledtext

from tkinterdnd2 import DND_FILES, TkinterDnD

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
sys.path.insert(0, HERE)
import simulate_order  # noqa: E402  (reads main.py's mapping functions without starting the app)


def process(paths, live, nav_clinic='', nav_patient_no=''):
    """Run each log through the same step the app uses. Returns the text to show."""
    args = argparse.Namespace(live=live, nav_clinic=nav_clinic, nav_patient_no=nav_patient_no,
                              so='TEST-SO-0001')
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        for path in paths:
            try:
                text = open(path, encoding='utf-8', errors='replace').read()
                simulate_order.run(os.path.basename(path), text, args)
            except Exception as e:
                print(f"  FAILED  {os.path.basename(path)}: {type(e).__name__}: {e}")
    return out.getvalue()


def main():
    root = TkinterDnD.Tk()
    root.title('Log to SharePoint')
    root.geometry('820x640')

    dry = tk.BooleanVar(value=True)
    top = tk.Frame(root)
    top.pack(fill='x', padx=10, pady=8)
    tk.Checkbutton(top, text='DRY RUN (show the row, write nothing) - untick to really create',
                   variable=dry).pack(side='left')

    drop = tk.Label(root, text='Drag results log(s) here\n(or click to choose)', relief='groove',
                    bd=3, height=5, bg='#eef3f8', font=('Segoe UI', 12))
    drop.pack(fill='x', padx=10, pady=4)
    box = scrolledtext.ScrolledText(root, font=('Consolas', 9), wrap='none')
    box.pack(fill='both', expand=True, padx=10, pady=8)

    def go(paths):
        live = not dry.get()
        box.insert('end', f"\n{'LIVE - creating on SharePoint' if live else 'DRY RUN - nothing written'}"
                          f" ({len(paths)} file(s))...\n")
        box.see('end')
        root.update_idletasks()
        box.insert('end', process(paths, live))
        box.see('end')

    def on_drop(event):
        go([p for p in root.tk.splitlist(event.data) if os.path.isfile(p)])

    def on_click(_event):
        paths = filedialog.askopenfilenames(
            title='Choose the results log(s)', filetypes=[('Results logs', '*.txt'), ('All', '*.*')])
        if paths:
            go(list(paths))

    drop.drop_target_register(DND_FILES)
    drop.dnd_bind('<<Drop>>', on_drop)
    drop.bind('<Button-1>', on_click)
    root.mainloop()


if __name__ == '__main__':
    main()
