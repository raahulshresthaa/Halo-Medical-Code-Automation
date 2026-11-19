# simulate_gui.py
"""A small window to test the SharePoint production-order step without NAV or OpenAI.

Add one or more results logs, then:
    Dry run  - shows the row each log would create, writes nothing
    Post     - really creates the row(s) on the SharePoint list (asks you to confirm first)

Run:  python simulate_gui.py
"""
import contextlib
import io
import os
import threading
import tkinter as tk
from argparse import Namespace
from tkinter import filedialog, messagebox, scrolledtext, ttk

import simulate_order as sim   # also moves into the app folder so the sp_*.txt settings are found


class App:
    def __init__(self, root):
        self.root = root
        root.title("SharePoint production order - log tester")
        root.geometry("900x650")
        self.logs = []

        top = ttk.Frame(root, padding=8)
        top.pack(fill='x')
        ttk.Button(top, text="Add logs...", command=self.add_logs).pack(side='left')
        ttk.Button(top, text="Remove selected", command=self.remove_selected).pack(side='left', padx=4)
        ttk.Button(top, text="Clear", command=self.clear).pack(side='left')

        self.listbox = tk.Listbox(root, height=6, selectmode='extended')
        self.listbox.pack(fill='x', padx=8)

        opts = ttk.Frame(root, padding=8)
        opts.pack(fill='x')
        ttk.Label(opts, text="NAV clinic (optional):").grid(row=0, column=0, sticky='w')
        self.clinic = ttk.Entry(opts, width=28)
        self.clinic.grid(row=0, column=1, padx=4)
        ttk.Label(opts, text="Patient no (optional):").grid(row=0, column=2, sticky='w')
        self.patient = ttk.Entry(opts, width=16)
        self.patient.grid(row=0, column=3, padx=4)
        ttk.Label(opts, text="Made-up SO:").grid(row=0, column=4, sticky='w')
        self.so = ttk.Entry(opts, width=16)
        self.so.insert(0, 'TEST-SO-0001')
        self.so.grid(row=0, column=5, padx=4)

        btns = ttk.Frame(root, padding=8)
        btns.pack(fill='x')
        self.dry_btn = ttk.Button(btns, text="Dry run (writes nothing)", command=lambda: self.go(False))
        self.dry_btn.pack(side='left')
        self.post_btn = ttk.Button(btns, text="Post to SharePoint", command=lambda: self.go(True))
        self.post_btn.pack(side='left', padx=8)
        ttk.Button(btns, text="Clear output", command=self.clear_output).pack(side='right')

        self.out = scrolledtext.ScrolledText(root, font=('Consolas', 9), wrap='none')
        self.out.pack(fill='both', expand=True, padx=8, pady=(0, 8))

    def add_logs(self):
        paths = filedialog.askopenfilenames(
            title="Choose results log(s)", initialdir=os.path.join(sim.HERE, 'result_logs'),
            filetypes=[('Results logs', '*.txt'), ('All files', '*.*')])
        for p in paths:
            if p not in self.logs:
                self.logs.append(p)
                self.listbox.insert('end', p)

    def remove_selected(self):
        for i in reversed(self.listbox.curselection()):
            self.listbox.delete(i)
            del self.logs[i]

    def clear(self):
        self.listbox.delete(0, 'end')
        self.logs.clear()

    def clear_output(self):
        self.out.delete('1.0', 'end')

    def go(self, live):
        if not self.logs:
            messagebox.showinfo("No logs", "Add at least one results log first.")
            return
        if live and not messagebox.askyesno(
                "Post to SharePoint",
                f"This creates {len(self.logs)} REAL row(s) on the SharePoint list.\n\n"
                "Rows for a sales order already on the list are skipped. Continue?",
                icon='warning'):
            return
        self.dry_btn.state(['disabled'])
        self.post_btn.state(['disabled'])
        threading.Thread(target=self.work, args=(live, list(self.logs)), daemon=True).start()

    def work(self, live, logs):
        args = Namespace(live=live, nav_clinic=self.clinic.get().strip(),
                         nav_patient_no=self.patient.get().strip(), so=self.so.get().strip())
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            if live:
                print("LIVE: real rows are being written to the SharePoint list.")
            for p in logs:
                try:
                    text = open(p, encoding='utf-8', errors='replace').read()
                    sim.run(os.path.basename(p), text, args)
                except Exception as e:
                    print(f"{os.path.basename(p)}: FAILED - {type(e).__name__}: {e}")
            if not live:
                print("\nDry run only - nothing was written.")
        self.root.after(0, self.done, buf.getvalue())

    def done(self, text):
        self.out.insert('end', text + "\n")
        self.out.see('end')
        self.dry_btn.state(['!disabled'])
        self.post_btn.state(['!disabled'])


if __name__ == '__main__':
    root = tk.Tk()
    App(root)
    root.mainloop()
