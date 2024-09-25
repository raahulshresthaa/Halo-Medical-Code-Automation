# gui.py

import os
import tkinter as tk
from tkinter import messagebox, Toplevel
import ttkbootstrap as ttk
from PIL import Image, ImageTk

current_dir = os.path.dirname(os.path.abspath(__file__))


def load_theme_setting(theme_list):
    settings_file = os.path.join(current_dir, 'settings.txt')
    if os.path.exists(settings_file):
        try:
            with open(settings_file, 'r') as f:
                theme = f.read().strip()
                if theme in theme_list:
                    return theme
                else:
                    return 'darkly'
        except:
            return 'darkly'
    else:
        return 'darkly'


def save_theme_setting(theme):
    settings_file = os.path.join(current_dir, 'settings.txt')
    with open(settings_file, 'w') as f:
        f.write(theme)


def change_theme(event, root, theme_var):
    selected = theme_var.get()
    root.style.theme_use(selected)
    save_theme_setting(selected)


def ensure_result_logs_folder_exists():
    result_logs_folder = os.path.join(current_dir, 'result_logs')
    if not os.path.exists(result_logs_folder):
        os.makedirs(result_logs_folder)
        print(f"Created 'result_logs' folder at {result_logs_folder}")
    else:
        print(f"'result_logs' folder already exists at {result_logs_folder}")


def show_loading_popup(root, icon_path):
    global loading_popup, loading_label, dot_index
    loading_popup = Toplevel(root)
    loading_popup.title("Loading...")

    icon_image_loading = None
    try:
        icon_image_loading = ImageTk.PhotoImage(
            Image.open(icon_path).resize((32, 32), Image.LANCZOS))
        loading_popup.iconphoto(False, icon_image_loading)
    except Exception as e:
        messagebox.showerror("Error", f"Error loading icon: {str(e)}")

    loading_popup.resizable(False, False)
    loading_popup.protocol("WM_DELETE_WINDOW", lambda: None)

    root.update_idletasks()
    x = root.winfo_x() + (root.winfo_width() // 2) - (300 // 2)
    y = root.winfo_y() + (root.winfo_height() // 2) - (100 // 2)
    loading_popup.geometry(f"300x100+{x}+{y}")

    loading_popup.transient(root)
    loading_popup.grab_set()

    loading_label = ttk.Label(
        loading_popup, text="Please wait, processing\n", font=("Calibri", 12, "bold"))
    loading_label.pack(expand=True, pady=20)

    dot_index = 0
    animate_dots()

    root.attributes('-disabled', True)


def animate_dots():
    global dot_index
    dots = ['.', '..', '...', '']
    loading_label.config(text=f"Please wait, processing\n{dots[dot_index]}")
    dot_index = (dot_index + 1) % len(dots)
    loading_popup.after(500, animate_dots)


def close_loading_popup(root):
    loading_popup.destroy()
    root.attributes('-disabled', False)
    root.focus_force()


def display_results(formatted_datetime, AutoDocRef, clinic, tariff_codes, auto_doc_ref_entry, datetime_entry, clinic_entry, result_text):
    auto_doc_ref_entry.config(state=tk.NORMAL)
    auto_doc_ref_entry.delete(0, tk.END)
    auto_doc_ref_entry.insert(0, AutoDocRef)
    auto_doc_ref_entry.config(state='readonly')

    datetime_entry.config(state=tk.NORMAL)
    datetime_entry.delete(0, tk.END)
    datetime_entry.insert(0, formatted_datetime)
    datetime_entry.config(state='readonly')

    clinic_entry.config(state=tk.NORMAL)
    clinic_entry.delete(0, tk.END)
    if clinic:
        clinic_entry.insert(0, clinic)
    else:
        clinic_entry.insert(0, "N/A")
    clinic_entry.config(state='readonly')

    result_text.config(state=tk.NORMAL)
    result_text.delete('1.0', tk.END)
    result_text.tag_configure('center', justify='center')
    result_text.insert(tk.END, '\n'.join(tariff_codes), 'center')
    result_text.config(state=tk.DISABLED)
