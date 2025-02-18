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
    """

    style.configure("Analysis.TFrame", background=style.colors.bg)
    analysis_tab = ttk.Frame(notebook, style="Analysis.TFrame")
    notebook.add(analysis_tab, text="Results Analysis")

    multi_mode = False

    def set_multi_mode(value: bool):
        nonlocal multi_mode
        multi_mode = value

    def is_multi_mode():
        return multi_mode

    # Single-line data gatherer
    def get_log_data_single():
        """
        Returns { 'YYYY-MM-DD': count_of_files_that_day }
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

    # Multi-line data gatherer
    def get_log_data_multi():
        """
        Returns { 'YYYY-MM-DD': {'insole': x, 'bespoke': y, 'afo': z, 'modular': w} }
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

    # Create figure + axes
    fig, ax = plt.subplots(figsize=(8, 6))
    fig.patch.set_facecolor(style.colors.bg)
    ax.set_facecolor(style.colors.bg)

    canvas = FigureCanvasTkAgg(fig, master=analysis_tab)
    canvas.draw()
    canvas.get_tk_widget().pack(side='top', fill='both', expand=True)

    # We'll store metadata for each plotted line in a dict: {line_object: (dates_list, counts_list)}
    lines_metadata = {}

    def refresh_chart():
        ax.clear()

        # Re-apply background
        fig.patch.set_facecolor(style.colors.bg)
        ax.set_facecolor(style.colors.bg)

        lines_metadata.clear()  # so we don’t accumulate from previous calls
        plotted_lines = []

        if not is_multi_mode():
            # Single-line mode
            data_dict = get_log_data_single()
            # Sort by date string, or keep as-is
            dates_str = list(data_dict.keys())
            counts = [data_dict[d] for d in dates_str]

            # We'll plot integer x-values: 0..N-1
            xvals = range(len(dates_str))

            (line,) = ax.plot(xvals, counts, marker='o', linestyle='-',
                              color=style.colors.primary, label='All Logs')
            plotted_lines.append(line)

            # Save metadata so we can lookup date_str in the hover
            lines_metadata[line] = (dates_str, counts)

            ax.set_title("Total Logs by Day", color=style.colors.fg)

        else:
            # Multi-line mode
            data_dict = get_log_data_multi()
            dates_str = list(data_dict.keys())
            # e.g. ['2023-06-01', '2023-06-02', ...]

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

            # xvals is 0..N-1
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

            # Save for hover
            lines_metadata[line1] = (dates_str, insole_counts)
            lines_metadata[line2] = (dates_str, bespoke_counts)
            lines_metadata[line3] = (dates_str, afo_counts)
            lines_metadata[line4] = (dates_str, modular_counts)

            ax.set_title("Logs by Day (Multi-Line)", color=style.colors.fg)
            ax.legend(facecolor=style.colors.bg, edgecolor=style.colors.fg)

        # Hide x-axis ticks so it appears blank
        ax.set_xticks([])

        # Y-axis style
        ax.set_ylabel("Number of Log Files", color=style.colors.fg)
        ax.tick_params(axis='y', colors=style.colors.fg)
        for spine in ax.spines.values():
            spine.set_edgecolor(style.colors.fg)

        # Use mplcursors with snap=True to ensure picking exact data points
        cursor = mplcursors.cursor(plotted_lines, hover=True)

        @cursor.connect("add")
        def on_add(sel):
            # The line object that was hovered
            line = sel.artist
            # Our stored (dates_str, counts) for that line
            dates_str, counts = lines_metadata[line]

            # This is the "index" along that line, usually a float
            i = sel.index

            # We'll round/clamp it to an integer in [0, len-1]
            i_rounded = int(round(i))
            i_rounded = max(0, min(i_rounded, len(dates_str) - 1))

            # Build the annotation text
            date_label  = dates_str[i_rounded]
            count_label = counts[i_rounded]
            sel.annotation.set_text(f"{date_label}\nCount: {count_label}")

        canvas.draw()

    refresh_chart()

    return analysis_tab, {
        'refresh_chart': refresh_chart,
        'set_multi_mode': set_multi_mode,
        'is_multi_mode': is_multi_mode
    }
