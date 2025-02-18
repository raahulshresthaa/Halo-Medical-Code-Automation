import os
import tkinter.ttk as ttk
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

def create_analysis_tab(notebook, theme):
    # Create a custom style for the analysis tab.
    style = ttk.Style()
    style.configure("Analysis.TFrame", background=theme["frame_bg"])
    
    # Create the analysis tab using the custom style.
    analysis_tab = ttk.Frame(notebook, style="Analysis.TFrame")
    
    # Helper function: gather log file data.
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

    data = get_log_data()
    dates = list(data.keys())
    counts = list(data.values())
    
    # Create a matplotlib figure.
    fig, ax = plt.subplots(figsize=(8,6))
    fig.patch.set_facecolor(theme["frame_bg"])
    ax.set_facecolor(theme["frame_bg"])
    ax.plot(dates, counts, marker='o', linestyle='-', color=theme["primary"])
    ax.set_title("Log Files by Day", color=theme["fg"])
    ax.set_xlabel("Date", color=theme["fg"])
    ax.set_ylabel("Number of Log Files", color=theme["fg"])
    ax.tick_params(axis='x', rotation=45, colors=theme["fg"])
    ax.tick_params(axis='y', colors=theme["fg"])
    for spine in ax.spines.values():
        spine.set_edgecolor(theme["fg"])
    
    # Embed the matplotlib figure into the tab.
    canvas = FigureCanvasTkAgg(fig, master=analysis_tab)
    canvas.draw()
    canvas.get_tk_widget().pack(side="top", fill="both", expand=True)
    
    # Provide a refresh function so the chart can be updated.
    def refresh_chart():
        new_data = get_log_data()
        new_dates = list(new_data.keys())
        new_counts = list(new_data.values())
        ax.clear()
        fig.patch.set_facecolor(theme["frame_bg"])
        ax.set_facecolor(theme["frame_bg"])
        ax.plot(new_dates, new_counts, marker='o', linestyle='-', color=theme["primary"])
        ax.set_title("Log Files by Day", color=theme["fg"])
        ax.set_xlabel("Date", color=theme["fg"])
        ax.set_ylabel("Number of Log Files", color=theme["fg"])
        ax.tick_params(axis='x', rotation=45, colors=theme["fg"])
        ax.tick_params(axis='y', colors=theme["fg"])
        for spine in ax.spines.values():
            spine.set_edgecolor(theme["fg"])
        canvas.draw()
    
    # For demonstration purposes, we include dummy multi-line mode functions.
    analysis_handles = {
        "refresh_chart": refresh_chart,
        "is_multi_mode": lambda: False,
        "set_multi_mode": lambda mode: None
    }
    
    return analysis_tab, analysis_handles
