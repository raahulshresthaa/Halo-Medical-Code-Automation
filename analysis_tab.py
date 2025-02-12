# analysis_tab.py
import os
import re  # For filename matching 
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import ttkbootstrap as ttk
def create_analysis_tab(notebook, style):
    """
    Creates a new tab in the provided ttk.Notebook that reads
    the 'result_logs' folder, and displays EITHER:
      - Single-line total logs/day (default),
      - OR 4 separate lines (insole, bespoke, afo, modular).
    """

    style.configure("Analysis.TFrame", background=style.colors.bg)

    analysis_tab = ttk.Frame(notebook, style="Analysis.TFrame")
    notebook.add(analysis_tab, text="Results Analysis")

    # ----------------------------------------------------------------------
    # NEW: Store a flag for whether we're in multi-line mode or not.
    # If you prefer toggling with a button, store this in an IntVar/BooleanVar
    # that you can flip from the main GUI. For demonstration, we do a plain bool:
    # ----------------------------------------------------------------------
    multi_mode = False

    # This will let us change it from outside if we keep a reference:
    def set_multi_mode(value: bool):
        nonlocal multi_mode
        multi_mode = value

    # Helper function that returns the current state:
    def is_multi_mode():
        return multi_mode
    # ----------------------------------------------------------------------

    # --- Helper function to gather logs by day ---
    def get_log_data_single():
        """
        For single-line mode: just count total .txt logs per day (as before).
        Returns a dict of { 'YYYY-MM-DD': count_of_files_that_day }.
        """
        data = {}
        result_logs_folder = os.path.join(os.getcwd(), 'result_logs')
        if os.path.exists(result_logs_folder):
            for folder in sorted(os.listdir(result_logs_folder)):
                folder_path = os.path.join(result_logs_folder, folder)
                if os.path.isdir(folder_path):
                    # Count how many .txt in that folder
                    count = len([
                        f for f in os.listdir(folder_path)
                        if os.path.isfile(os.path.join(folder_path, f))
                    ])
                    data[folder] = count
        return data

    # ----------------------------------------------------------------------
    # NEW: For multi-line mode, we parse each day’s logs and see
    # how many are insole vs. bespoke vs. afo vs. modular.
    # ----------------------------------------------------------------------
    def get_log_data_multi():
        """
        Returns a dict of { 'YYYY-MM-DD': {'insole': x, 'bespoke': y, 'afo': z, 'modular': w} }.
        The day keys might appear in sorted order in your final chart code.
        """
        data = {}
        categories = ('insole', 'bespoke', 'afo', 'modular')

        result_logs_folder = os.path.join(os.getcwd(), 'result_logs')
        if os.path.exists(result_logs_folder):
            for folder in sorted(os.listdir(result_logs_folder)):
                folder_path = os.path.join(result_logs_folder, folder)
                if os.path.isdir(folder_path):
                    # Initialize counters for each category
                    cat_counts = {'insole': 0, 'bespoke': 0, 'afo': 0, 'modular': 0}

                    # For each file, check if "insole", "bespoke", etc. is in the filename
                    for fname in os.listdir(folder_path):
                        if os.path.isfile(os.path.join(folder_path, fname)):
                            # A simple approach: check substring in filename
                            f_lower = fname.lower()
                            if 'insole' in f_lower:
                                cat_counts['insole'] += 1
                            elif 'bespoke' in f_lower:
                                cat_counts['bespoke'] += 1
                            elif 'afo' in f_lower:
                                cat_counts['afo'] += 1
                            elif 'modular' in f_lower:
                                cat_counts['modular'] += 1

                    data[folder] = cat_counts

        return data

    # Create the figure
    fig, ax = plt.subplots(figsize=(8, 6))
    fig.patch.set_facecolor(style.colors.bg)
    ax.set_facecolor(style.colors.bg)

    # 6) Embed the matplotlib figure in the analysis_tab
    canvas = FigureCanvasTkAgg(fig, master=analysis_tab)
    canvas.draw()
    canvas.get_tk_widget().pack(side='top', fill='both', expand=True)

    # ----------------------------------------------------------------------
    # The main "plotting" function that checks multi_mode and draws either
    # a single total line or multiple lines
    # ----------------------------------------------------------------------
    def refresh_chart():
        ax.clear()  # Clear old plot

        # Re-apply background colors
        fig.patch.set_facecolor(style.colors.bg)
        ax.set_facecolor(style.colors.bg)

        if not is_multi_mode():
            # SINGLE-LINE mode
            data_dict = get_log_data_single()
            dates = list(data_dict.keys())
            counts = list(data_dict.values())

            # Plot single line
            ax.plot(dates, counts, marker='o', linestyle='-', color=style.colors.primary, label='All Logs')
            ax.set_title("Total Logs by Day", color=style.colors.fg)

        else:
            # MULTI-LINE mode
            data_dict = get_log_data_multi()
            # We expect data_dict like: { 'YYYY-MM-DD': {'insole': #, 'bespoke': #, 'afo': #, 'modular': #} }

            dates = list(data_dict.keys())

            # Build separate lists for each category
            insole_counts  = []
            bespoke_counts = []
            afo_counts     = []
            modular_counts = []

            for d in dates:
                cat_counts = data_dict[d]
                insole_counts.append( cat_counts['insole'] )
                bespoke_counts.append(cat_counts['bespoke'])
                afo_counts.append(    cat_counts['afo'] )
                modular_counts.append(cat_counts['modular'])

            # We'll pick different line colors from the style or you can hardcode them
            # e.g. style.colors.info, style.colors.warning, etc.
            ax.plot(dates, insole_counts,  marker='o', linestyle='-', color=style.colors.primary,   label='Insole')
            ax.plot(dates, bespoke_counts, marker='o', linestyle='-', color=style.colors.info,      label='Bespoke')
            ax.plot(dates, afo_counts,     marker='o', linestyle='-', color=style.colors.warning,   label='AFO')
            ax.plot(dates, modular_counts, marker='o', linestyle='-', color=style.colors.success,   label='Modular')

            ax.set_title("Logs by Day (Multi-Line)", color=style.colors.fg)
            ax.legend(facecolor=style.colors.bg, edgecolor=style.colors.fg)

        # Common axis labels + theme styling
        ax.set_xlabel("Date", color=style.colors.fg)
        ax.set_ylabel("Number of Log Files", color=style.colors.fg)
        ax.tick_params(axis='x', rotation=45, colors=style.colors.fg)
        ax.tick_params(axis='y', colors=style.colors.fg)

        for spine in ax.spines.values():
            spine.set_edgecolor(style.colors.fg)

        canvas.draw()

    # Do an initial draw in single-line mode
    refresh_chart()

    # Return the analysis_tab plus a dictionary of new things you might need:
    return analysis_tab, {
        'refresh_chart': refresh_chart,
        'set_multi_mode': set_multi_mode,
        'is_multi_mode': is_multi_mode  

    }
