# analysis_tab.py
import os
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import ttkbootstrap as ttk
import mplcursors  # for hover tooltips

def create_analysis_tab(notebook, style):
    """
    Creates a new tab in the provided ttk.Notebook that reads
    the 'result_logs' folder, and displays EITHER:
      - Single-line total logs/day,
      - OR 4 separate lines (insole, bespoke, afo, modular).

    It offers a "Toggle Multi-Line Mode" button that switches between
    the two modes. The background and colors follow the current ttkbootstrap theme.
    """

    # 1) Create the main tab frame
    style.configure("Analysis.TFrame", background=style.colors.bg)
    analysis_tab = ttk.Frame(notebook, style="Analysis.TFrame")
    notebook.add(analysis_tab, text="Results Analysis")

    # 2) Internal state: single-line vs multi-line
    multi_mode = False

    def set_multi_mode(value: bool):
        nonlocal multi_mode
        multi_mode = value

    def is_multi_mode():
        return multi_mode

    # 3) Data gatherers

    def get_log_data_single():
        """
        Returns a dict:
            {
                'YYYY-MM-DD': total_file_count_that_day,
                ...
            }
        """
        data = {}
        result_logs_folder = os.path.join(os.getcwd(), 'result_logs')
        if os.path.exists(result_logs_folder):
            for folder in sorted(os.listdir(result_logs_folder)):
                folder_path = os.path.join(result_logs_folder, folder)
                if os.path.isdir(folder_path):
                    count = len([
                        f for f in os.listdir(folder_path)
                        if os.path.isfile(os.path.join(folder_path, f))
                    ])
                    data[folder] = count
        return data

    def get_log_data_multi():
        """
        Returns a dict:
            {
                'YYYY-MM-DD': {
                    'insole': x,
                    'bespoke': y,
                    'afo': z,
                    'modular': w
                },
                ...
            }
        """
        data = {}
        result_logs_folder = os.path.join(os.getcwd(), 'result_logs')
        if os.path.exists(result_logs_folder):
            for folder in sorted(os.listdir(result_logs_folder)):
                folder_path = os.path.join(result_logs_folder, folder)
                if os.path.isdir(folder_path):
                    cat_counts = {'insole': 0, 'bespoke': 0, 'afo': 0, 'modular': 0}
                    for fname in os.listdir(folder_path):
                        if os.path.isfile(os.path.join(folder_path, fname)):
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

    # 4) Create the Matplotlib figure/axes
    fig, ax = plt.subplots(figsize=(8, 6))
    fig.patch.set_facecolor(style.colors.bg)
    ax.set_facecolor(style.colors.bg)

    # 5) Create two frames: controls (top), chart (bottom)
    controls_frame = ttk.Frame(analysis_tab)
    controls_frame.pack(side='top', fill='x')

    chart_frame = ttk.Frame(analysis_tab)
    chart_frame.pack(side='top', fill='both', expand=True)

    # 6) Place the figure canvas inside the chart frame
    canvas = FigureCanvasTkAgg(fig, master=chart_frame)
    canvas.draw()
    canvas.get_tk_widget().pack(side='top', fill='both', expand=True)

    # 7) We keep a dictionary for line hover info: {line: (dates_str, counts_list)}
    lines_metadata = {}

    def refresh_chart():
        """
        Clears and redraws the chart in either single-line or multi-line mode.
        Also sets up hover annotations via mplcursors.
        """
        ax.clear()

        # Re-apply the theme background
        fig.patch.set_facecolor(style.colors.bg)
        ax.set_facecolor(style.colors.bg)

        lines_metadata.clear()
        plotted_lines = []

        # Single-line mode or multi-line mode?
        if not is_multi_mode():
            # --- Single-Line Mode ---
            data_dict = get_log_data_single()
            dates_str = list(data_dict.keys())
            counts = [data_dict[d] for d in dates_str]

            xvals = range(len(dates_str))
            (line,) = ax.plot(xvals, counts, marker='o', linestyle='-',
                              color=style.colors.primary, label='All Logs')
            plotted_lines.append(line)

            # Store metadata for hover
            lines_metadata[line] = (dates_str, counts)

            ax.set_title("Total Logs by Day", color=style.colors.fg)

        else:
            # --- Multi-Line Mode ---
            data_dict = get_log_data_multi()
            dates_str = list(data_dict.keys())

            # Build arrays for each category
            insole_counts  = []
            bespoke_counts = []
            afo_counts     = []
            modular_counts = []

            for d in dates_str:
                cat_counts = data_dict[d]
                insole_counts.append(cat_counts['insole'])
                bespoke_counts.append(cat_counts['bespoke'])
                afo_counts.append(cat_counts['afo'])
                modular_counts.append(cat_counts['modular'])

            xvals = range(len(dates_str))

            line1, = ax.plot(xvals, insole_counts,  marker='o', linestyle='-',
                             color=style.colors.primary, label='Insole')
            line2, = ax.plot(xvals, bespoke_counts, marker='o', linestyle='-',
                             color=style.colors.info,    label='Bespoke')
            line3, = ax.plot(xvals, afo_counts,     marker='o', linestyle='-',
                             color=style.colors.warning, label='AFO')
            line4, = ax.plot(xvals, modular_counts, marker='o', linestyle='-',
                             color=style.colors.success, label='Modular')

            plotted_lines.extend([line1, line2, line3, line4])

            # Save hover info
            lines_metadata[line1] = (dates_str, insole_counts)
            lines_metadata[line2] = (dates_str, bespoke_counts)
            lines_metadata[line3] = (dates_str, afo_counts)
            lines_metadata[line4] = (dates_str, modular_counts)

            ax.set_title("Logs by Day (Multi-Line)", color=style.colors.fg)
            ax.legend(facecolor=style.colors.bg, edgecolor=style.colors.fg)

        # Customize x/y axes
        ax.set_xticks([])  # Hide x-axis ticks for a clean look
        ax.set_ylabel("Number of Log Files", color=style.colors.fg)
        ax.tick_params(axis='y', colors=style.colors.fg)
        for spine in ax.spines.values():
            spine.set_edgecolor(style.colors.fg)

        # Enable hover annotations
        cursor = mplcursors.cursor(plotted_lines, hover=True)

        @cursor.connect("add")
        def on_add(sel):
            line = sel.artist
            dates, counts = lines_metadata[line]
            i = int(round(sel.index))
            i = max(0, min(i, len(dates) - 1))

            sel.annotation.set_text(f"{dates[i]}\nCount: {counts[i]}")

        canvas.draw()

    # 8) Define the toggle function for the button
    def toggle_multi_mode():
        new_state = not is_multi_mode()
        set_multi_mode(new_state)
        refresh_chart()

    # 9) Create the toggle button in the controls frame
    toggle_button = ttk.Button(
        controls_frame,
        text="Toggle Multi-Line Mode",
        command=toggle_multi_mode
    )
    toggle_button.pack(side='left', padx=5, pady=5)

    # 10) Initial draw
    refresh_chart()

    # Return the tab widget and a dictionary of useful callbacks
    return analysis_tab, {
        'refresh_chart': refresh_chart,
        'set_multi_mode': set_multi_mode,
        'is_multi_mode': is_multi_mode
    }
