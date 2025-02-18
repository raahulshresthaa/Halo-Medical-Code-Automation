########################################
# main.py
########################################
import os
import sys
import time
import base64
import datetime
import threading

import customtkinter as ctk
from tkinter import filedialog, messagebox, simpledialog
from PIL import Image
import openai

from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Import your code–generation functions from generate_code_logic.py
# (Ensure generate_insole_codes, generate_afo_codes, generate_bespoke_codes, generate_modular_codes are standalone.)
from generate_code_logic import (
    generate_insole_codes,
    generate_afo_codes,
    generate_bespoke_codes,
    generate_modular_codes
)

VERSION = "5.1.0-dev"


def get_form_type_from_model_id(model_id):
    mapping = {
        "InsoleReaderFullV3": "insole",
        "AfoReaderV7": "afo",
        "BespokeReaderFullV4": "bespoke",
        "ModularReaderFullV3": "modular",
    }
    return mapping.get(model_id, "unknown")


class PdfButtonHandler:
    """
    Handles uploading a PDF and calling Azure Form Recognizer,
    then passing the extracted content plus logic to OpenAI.
    """
    def __init__(
        self,
        app,
        result_text,
        auto_doc_ref_entry,
        datetime_entry,
        clinic_entry,
        show_loading_popup,
        close_loading_popup,
        display_results,
        get_model_id_callback
    ):
        self.app = app
        self.result_text = result_text
        self.auto_doc_ref_entry = auto_doc_ref_entry
        self.datetime_entry = datetime_entry
        self.clinic_entry = clinic_entry
        self.show_loading_popup = show_loading_popup
        self.close_loading_popup = close_loading_popup
        self.display_results = display_results
        self.get_model_id = get_model_id_callback

        self.upload_pdf_button = None

        # Read Azure credentials
        self.endpoint = self.read_azure_credential_file("azure_endpoint.txt", "Azure Endpoint")
        self.key = self.read_azure_credential_file("azure_key.txt", "Azure Key")

        # Validate them
        if not self.endpoint or not isinstance(self.endpoint, str):
            raise ValueError("Azure endpoint is not set or is not a valid string.")
        if not self.key or not isinstance(self.key, str):
            raise ValueError("Azure key is not set or is not a valid string.")

        # Create a DocumentAnalysisClient
        self.document_analysis_client = DocumentAnalysisClient(
            endpoint=self.endpoint,
            credential=AzureKeyCredential(self.key)
        )

    def set_upload_pdf_button(self, button):
        """Keep a reference to the 'Upload PDF' button so we can re-enable it after processing."""
        self.upload_pdf_button = button

    def read_azure_credential_file(self, filename, credential_name):
        file_path = os.path.join(os.getcwd(), filename)
        if os.path.exists(file_path):
            try:
                with open(file_path, "rb") as f:
                    encoded_data = f.read()
                    decoded_data = base64.b64decode(encoded_data).decode("utf-8").strip()
                if not decoded_data:
                    raise ValueError(f"{credential_name} file is empty.")
                return decoded_data
            except Exception as e:
                messagebox.showerror("Error", f"Error reading {credential_name}: {str(e)}")
                sys.exit()
        else:
            # If the file doesn't exist, ask user for the credential
            credential = simpledialog.askstring(f"{credential_name} Required", f"Please enter your {credential_name}:")
            if not credential:
                messagebox.showerror("Error", f"No {credential_name} entered. The application will exit.")
                sys.exit()
            self.write_azure_credential_file(filename, credential.strip())
            return credential.strip()

    def write_azure_credential_file(self, filename, credential):
        file_path = os.path.join(os.getcwd(), filename)
        encoded_data = base64.b64encode(credential.encode("utf-8"))
        with open(file_path, "wb") as f:
            f.write(encoded_data)
        print(f"{filename} saved to {file_path}")

    def upload_pdf_file(self):
        """Called when 'Upload PDF' button is pressed. Allows user to select a PDF to process."""
        pdf_file_path = filedialog.askopenfilename(
            title="Select a PDF File",
            filetypes=[("PDF Files", "*.pdf")]
        )
        if pdf_file_path:
            # Disable the button, show loading popup, then process in a separate thread
            self.upload_pdf_button.configure(state="disabled")
            self.show_loading_popup()
            threading.Thread(target=self.process_pdf_and_call_api, args=(pdf_file_path,)).start()
        else:
            messagebox.showinfo("No PDF File Selected", "Please select a PDF file to process.")

    def process_pdf_and_call_api(self, pdf_file_path):
        """Called in a background thread after user selects a PDF."""
        try:
            model_id = self.get_model_id()
            print(f"Using model ID: {model_id}")
            with open(pdf_file_path, "rb") as pdf_file:
                poller = self.document_analysis_client.begin_analyze_document(model_id, document=pdf_file)
                result = poller.result()

            # Update the loading popup text
            self.app.update_loading_message("Please wait, extracting data from Azure")

            fields_data = self.extract_fields_from_result(result)
            if not fields_data:
                raise ValueError("No data extracted from the PDF.")

            # Convert extracted fields into a single string
            content = "\n".join(f"{k}: {v}" for k, v in fields_data.items())
            print(f"Extracted content: {content}")

            AutoDocRef = fields_data.get("AutoDocRef", "N/A")
            clinic = fields_data.get("Clinic", "N/A")

            # Based on model_id, generate any "passed codes" (short-circuit logic)
            content_with_passed = self.apply_passed_codes_logic(model_id, content)

            # Now read the relevant logic file from your logic_folder
            logic_file_name = self.get_logic_filename_for_model_id(model_id, content_with_passed)
            logic_file_path = os.path.join(os.getcwd(), "logic_folder", logic_file_name)
            logic_content = self.read_logic_file(logic_file_path)
            if "Error" in logic_content:
                raise ValueError(logic_content)

            # Finally, call the API
            self.process_api_call(content_with_passed, logic_content, AutoDocRef, clinic)

        except Exception as e:
            messagebox.showerror("Error", f"Error processing the PDF file: {str(e)}")
            self.upload_pdf_button.configure(state="normal")
            self.close_loading_popup()

    def process_api_call(self, content, logic_content, AutoDocRef, clinic):
        """Sends the content to OpenAI with the given logic_content, then updates the GUI."""
        try:
            # Format the request to OpenAI
            response = openai.ChatCompletion.create(
                model="gpt-4o-2024-08-06",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            f"Use the following logic to generate price codes:\n\n{logic_content}\n\n"
                            "The 'Passed code' section contains codes that have already been generated "
                            "and should be included in the final output.\n\n"
                            "Write your full working out and then write **Final Codes:** and output the final codes "
                            "each on a new line, including the passed codes."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Here is the content to process:\n{content}"
                    }
                ],
                max_tokens=1000,
                temperature=0.1
            )
            price_codes = response["choices"][0]["message"]["content"]
            print("Price codes received:", price_codes)

            # Possibly create a timestamp
            current_datetime = datetime.datetime.now()
            formatted_datetime = current_datetime.strftime("%Y-%m-%d %H:%M:%S")

            # Check for "no base" warnings if relevant
            query_msg = None
            model_id = self.get_model_id()
            if model_id == "InsoleReaderFullV3":
                query_msg = self.check_for_base(content)

            combined_msg = query_msg if query_msg else None

            # Finally, update the GUI
            self.app.display_results(
                formatted_datetime, AutoDocRef, clinic, price_codes, combined_msg
            )

        except Exception as e:
            messagebox.showerror("Error", f"Error: {str(e)}")
        finally:
            self.upload_pdf_button.configure(state="normal")
            self.close_loading_popup()

    def extract_fields_from_result(self, result):
        fields_data = {}
        for document in result.documents:
            for name, field in document.fields.items():
                field_value = field.value if field.value else field.content
                if field_value and str(field_value).lower() not in ["none", "unselected"]:
                    fields_data[name.strip()] = field_value.strip()
        return fields_data

    def check_for_base(self, data):
        """If there's no 'base', 'carbon fibre', or 'poron' mention, return a 'raise a query' msg."""
        data_lower = data.lower()
        if not any(keyword in data_lower for keyword in ["base:", "carbon fibre:", "poron:"]):
            query = "No base, Carbon Fibre, or Poron found in the form. Please raise a query."
            messagebox.showinfo("Query", query)
            return query
        return None

    def apply_passed_codes_logic(self, model_id, content):
        """
        For each model, generate 'passed_codes' from the generate_code_logic.py functions
        and then append them to the content under 'Passed code:'.
        """
        # Just a skeleton example
        passed_codes = None
        if model_id == "InsoleReaderFullV3":
            passed_codes = generate_insole_codes(content)
        elif model_id == "AfoReaderV7":
            passed_codes = generate_afo_codes(content)
        elif model_id == "BespokeReaderFullV4":
            passed_codes = generate_bespoke_codes(content)
        elif model_id == "ModularReaderFullV3":
            passed_codes = generate_modular_codes(content)

        if passed_codes:
            return content + f"\n\nPassed code:\n{passed_codes}"
        return content

    def get_logic_filename_for_model_id(self, model_id, content_with_passed):
        """
        Decide which logic file to read from logic_folder based on model_id or form_type, etc.
        This is just an example that picks a single file name for each model.
        """
        if model_id == "InsoleReaderFullV3":
            return "tci_logic.txt"
        elif model_id == "AfoReaderV7":
            return "afo_logic.txt"
        elif model_id == "BespokeReaderFullV4":
            return "bespoke_logic.txt"
        elif model_id == "ModularReaderFullV3":
            return "modular_logic.txt"
        else:
            return "unknown_logic.txt"


class Application(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Set the default theme, size, etc....
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.title("Halo Medical Code Automation - PDF Processing")
        self.geometry("900x700")
        
        # (A) CREATE THE AUTO-WATCH VARIABLE HERE:
        self.auto_watch_var = ctk.BooleanVar(value=False)
        
        # Then create the tabview and build the tabs
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=20, pady=20)
        self.tabview.add("Main Processing")
        self.tabview.add("Analysis")

        self.build_main_tab(self.tabview.tab("Main Processing"))
        self.build_analysis_tab(self.tabview.tab("Analysis"))
        
        # Then start watching for new PDFs in downloads
        self.known_downloads = set()  # some set to keep track of known files
        self.after(1500, self.watch_downloads_folder)

        # Watch for new PDFs in Downloads
        self.auto_watch_var = ctk.BooleanVar(value=False)
        self.known_downloads = set()
        self.after(1500, self.watch_downloads_folder)

    def build_main_tab(self, parent):
        # 1) Top section with a logo and title
        top_frame = ctk.CTkFrame(parent)
        top_frame.pack(fill="x", padx=10, pady=10)

        # Attempt to load a custom image (optional)
        logo_path = os.path.join(os.getcwd(), "images", "HALO(TM)_Logo.png")
        self.logo_image = None
        try:
            pil_logo = Image.open(logo_path).resize((200, 100))
            self.logo_image = ctk.CTkImage(light_image=pil_logo, dark_image=pil_logo, size=(200, 100))
        except Exception as e:
            print(f"Warning: could not load logo image. {e}")

        if self.logo_image:
            logo_label = ctk.CTkLabel(top_frame, image=self.logo_image, text="")
            logo_label.pack(side="left", padx=10)

        title_label = ctk.CTkLabel(
            top_frame,
            text="Code Automation Program",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(side="left", padx=10)

        # 2) Info frame for AutoDocRef, Clinic, Date
        info_frame = ctk.CTkFrame(parent)
        info_frame.pack(fill="x", padx=10, pady=10)

        # AutoDocRef
        self.autodoc_label = ctk.CTkLabel(info_frame, text="AutoDocRef:")
        self.autodoc_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.autodoc_entry = ctk.CTkEntry(info_frame, width=200)
        self.autodoc_entry.grid(row=1, column=0, padx=5, pady=5)

        # Clinic
        self.clinic_label = ctk.CTkLabel(info_frame, text="Clinic:")
        self.clinic_label.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        self.clinic_entry = ctk.CTkEntry(info_frame, width=200)
        self.clinic_entry.grid(row=1, column=1, padx=5, pady=5)

        # Date and Time
        self.datetime_label = ctk.CTkLabel(info_frame, text="Date and Time:")
        self.datetime_label.grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.datetime_entry = ctk.CTkEntry(info_frame, width=200)
        self.datetime_entry.grid(row=1, column=2, padx=5, pady=5)

        # 3) A large text box for results
        self.result_text = ctk.CTkTextbox(parent, wrap="word", height=280)
        self.result_text.pack(fill="both", expand=True, padx=10, pady=10)
        self.result_text.configure(state="disabled")

        # 4) Model selection, plus buttons
        bottom_frame = ctk.CTkFrame(parent)
        bottom_frame.pack(fill="x", padx=10, pady=(0, 10))

        # Model selection
        self.model_choices = {
            "Insoles": "InsoleReaderFullV3",
            "AFOs": "AfoReaderV7",
            "Bespoke": "BespokeReaderFullV4",
            "Modular": "ModularReaderFullV3"
        }
        self.model_label = ctk.CTkLabel(bottom_frame, text="Select Form Type:")
        self.model_label.grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.model_var = ctk.StringVar(value="Insoles")
        self.model_optionmenu = ctk.CTkOptionMenu(
            bottom_frame,
            variable=self.model_var,
            values=list(self.model_choices.keys())
        )
        self.model_optionmenu.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        # Check box for auto watch
        self.auto_watch_checkbox = ctk.CTkCheckBox(
            bottom_frame,
            text="Auto-detect new PDF in Downloads (beta)",
            variable=self.auto_watch_var  # This now exists
        )
        self.auto_watch_checkbox.grid(row=0, column=2, padx=5, pady=5)

        # Buttons
        self.upload_button = ctk.CTkButton(bottom_frame, text="Upload PDF")
        self.upload_button.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        self.copy_button = ctk.CTkButton(
            bottom_frame, text="Copy to Clipboard", command=self.copy_final_codes
        )
        self.copy_button.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.exit_button = ctk.CTkButton(
            bottom_frame, text="Exit", command=self.on_close
        )
        self.exit_button.grid(row=1, column=2, padx=5, pady=5, sticky="ew")

        # Create PdfButtonHandler instance
        self.pdf_handler = PdfButtonHandler(
            app=self,
            result_text=self.result_text,
            auto_doc_ref_entry=self.autodoc_entry,
            datetime_entry=self.datetime_entry,
            clinic_entry=self.clinic_entry,
            show_loading_popup=self.show_loading_popup,
            close_loading_popup=self.close_loading_popup,
            display_results=self.display_results,
            get_model_id_callback=self.get_model_id
        )
        self.pdf_handler.set_upload_pdf_button(self.upload_button)

        # The "Upload PDF" button calls pdf_handler.upload_pdf_file
        self.upload_button.configure(command=self.pdf_handler.upload_pdf_file)

    def build_analysis_tab(self, parent):
        # A placeholder analysis tab with a simple chart
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.fig, self.ax = plt.subplots(figsize=(6, 4))
        # Example data
        x_data = ["2023-07-01", "2023-07-02", "2023-07-03"]
        y_data = [5, 8, 3]
        self.ax.plot(x_data, y_data, marker="o", color="cyan")
        self.ax.set_title("Log Files by Day", color="white")
        self.ax.set_facecolor("#333333")
        self.fig.patch.set_facecolor("#2e2e2e")
        self.ax.tick_params(axis="x", rotation=45, colors="white")
        self.ax.tick_params(axis="y", colors="white")

        self.canvas = FigureCanvasTkAgg(self.fig, master=frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def on_close(self):
        self.destroy()

    def get_model_id(self):
        selected = self.model_var.get()
        return self.model_choices.get(selected, "InsoleReaderFullV3")

    def copy_final_codes(self):
        """Copy text from result_text to clipboard."""
        full_text = self.result_text.get("1.0", "end")
        self.clipboard_clear()
        self.clipboard_append(full_text)
        messagebox.showinfo("Copied", "Final codes copied to clipboard.")

    def display_results(self, formatted_datetime, AutoDocRef, clinic, price_codes, messages=None):
        """Called by pdf_handler after GPT logic is done."""
        self.autodoc_entry.configure(state="normal")
        self.autodoc_entry.delete(0, "end")
        self.autodoc_entry.insert(0, AutoDocRef)
        self.autodoc_entry.configure(state="readonly")

        self.datetime_entry.configure(state="normal")
        self.datetime_entry.delete(0, "end")
        self.datetime_entry.insert(0, formatted_datetime)
        self.datetime_entry.configure(state="readonly")

        self.clinic_entry.configure(state="normal")
        self.clinic_entry.delete(0, "end")
        self.clinic_entry.insert(0, clinic if clinic else "N/A")
        self.clinic_entry.configure(state="readonly")

        self.result_text.configure(state="normal")
        self.result_text.delete("1.0", "end")
        # Insert the returned price codes
        self.result_text.insert("end", price_codes)
        if messages:
            self.result_text.insert("end", "\n\n" + messages)
        self.result_text.configure(state="disabled")

    ########################################
    # LOADING POPUP
    ########################################
    def show_loading_popup(self):
        self.loading_popup = ctk.CTkToplevel(self)
        self.loading_popup.title("Loading...")
        self.loading_popup.geometry("300x100")
        self.loading_popup.resizable(False, False)
        self.loading_popup.grab_set()

        self.loading_label = ctk.CTkLabel(
            self.loading_popup,
            text="Please wait, reading the file\n",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.loading_label.pack(expand=True, pady=20)
        self.dot_index = 0
        self.animate_dots()

    def animate_dots(self):
        dots = [".", "..", "...", ""]
        text = f"Please wait, reading the file\n{dots[self.dot_index]}"
        self.loading_label.configure(text=text)
        self.dot_index = (self.dot_index + 1) % len(dots)
        if hasattr(self, "loading_popup"):
            self.loading_popup.after(500, self.animate_dots)

    def update_loading_message(self, new_message):
        if hasattr(self, "loading_label"):
            self.loading_label.configure(text=new_message)

    def close_loading_popup(self):
        if hasattr(self, "loading_popup"):
            self.loading_popup.destroy()

    ########################################
    # AUTO-WATCH FOR NEW PDFS
    ########################################
    def watch_downloads_folder(self):
        """Checks if a new PDF is in Downloads, and if so, processes it automatically."""
        if self.auto_watch_var.get():
            downloads_folder = os.path.join(os.path.expanduser("~"), "Downloads")
            if os.path.isdir(downloads_folder):
                pdf_files = [f for f in os.listdir(downloads_folder) if f.lower().endswith(".pdf")]
                if pdf_files:
                    pdf_files.sort(key=lambda f: os.path.getmtime(os.path.join(downloads_folder, f)))
                    newest_pdf = pdf_files[-1]
                    pdf_path = os.path.join(downloads_folder, newest_pdf)
                    if newest_pdf not in self.known_downloads:
                        self.known_downloads.add(newest_pdf)
                        self.upload_button.configure(state="disabled")
                        self.show_loading_popup()
                        threading.Thread(
                            target=self.pdf_handler.process_pdf_and_call_api,
                            args=(pdf_path,)
                        ).start()
        self.after(1000, self.watch_downloads_folder)


if __name__ == "__main__":
    app = Application()
    app.mainloop()
