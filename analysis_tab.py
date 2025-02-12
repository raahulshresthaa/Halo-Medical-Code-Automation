# analysis_tab.py
import os
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import ttkbootstrap as ttk

def create_analysis_tab(notebook, style):
    """
    Creates a new tab in the provided ttk.Notebook that reads
    the 'result_logs' folder, aggregates the number of log files
    per day, and displays a line chart. The chart’s background
    (and the tab’s background) follow the current ttkbootstrap theme.
    """

    # 1) Create a special style for our analysis frame
    style.configure("Analysis.TFrame", background=style.colors.bg)

    # 2) Build a ttk.Frame using that custom style
    analysis_tab = ttk.Frame(notebook, style="Analysis.TFrame")
    notebook.add(analysis_tab, text="Results Analysis")

    # 3) Define a helper function to gather your log data
    def get_log_data():
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

    # 4) Retrieve initial data
    data = get_log_data()
    dates = list(data.keys())
    counts = list(data.values())

    # 5) Create the matplotlib figure
    fig, ax = plt.subplots(figsize=(8, 6))

    # Set the face colors (figure + axes) from the theme
    fig.patch.set_facecolor(style.colors.bg)
    ax.set_facecolor(style.colors.bg)

    # Plot your line chart using the theme's primary color
    ax.plot(dates, counts, marker='o', linestyle='-', color=style.colors.primary)
    ax.set_title("Log Files by Day (Line Chart)", color=style.colors.fg)
    ax.set_xlabel("Date", color=style.colors.fg)
    ax.set_ylabel("Number of Log Files", color=style.colors.fg)

    # Tweak tick label colors
    ax.tick_params(axis='x', rotation=45, colors=style.colors.fg)
    ax.tick_params(axis='y', colors=style.colors.fg)

    # Tweak border/spine colors
    for spine in ax.spines.values():
        spine.set_edgecolor(style.colors.fg)

    # 6) Embed the matplotlib figure in the analysis_tab
    canvas = FigureCanvasTkAgg(fig, master=analysis_tab)
    canvas.draw()
    canvas.get_tk_widget().pack(side='top', fill='both', expand=True)

    # 7) Define a refresh function so you can update the chart later
    def refresh_chart():
        # Re-fetch data (in case logs changed)
        new_data = get_log_data()
        new_dates = list(new_data.keys())
        new_counts = list(new_data.values())

        # Clear old plot
        ax.clear()

        # Re-apply backgrounds
        fig.patch.set_facecolor(style.colors.bg)
        ax.set_facecolor(style.colors.bg)

        # Re-plot
        ax.plot(new_dates, new_counts, marker='o', linestyle='-', color=style.colors.primary)
        ax.set_title("Log Files by Day (Line Chart)", color=style.colors.fg)
        ax.set_xlabel("Date", color=style.colors.fg)
        ax.set_ylabel("Number of Log Files", color=style.colors.fg)
        ax.tick_params(axis='x', rotation=45, colors=style.colors.fg)
        ax.tick_params(axis='y', colors=style.colors.fg)

        # Re-color spines
        for spine in ax.spines.values():
            spine.set_edgecolor(style.colors.fg)

        # Redraw
        canvas.draw()

    # 8) Return both the tab frame and the refresh function
    return analysis_tab, refresh_chart
