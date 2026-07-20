# analysis_tab.py
import os
import tkinter as tk

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.ticker import MaxNLocator
import ttkbootstrap as ttk
import mplcursors  # for hover tooltips

# Multi-line chart categories. These mirror the form types in main.py MODEL_IDS
# (log files are named results_log_<ref>_<form_type>.txt, where <form_type> is
# the lowercased MODEL_IDS key). Keep this list in sync with MODEL_IDS.
#   (chart label, filename suffix, theme color attribute or hex)
MULTI_CATEGORIES = [
    ('Insole',  'insoles', 'primary'),
    ('AFO',     'afos',    'warning'),
    ('Bespoke', 'bespoke', 'info'),
    ('Modular', 'modular', 'success'),
    ('KAFO',    'kafo',    'secondary'),
    ('Repairs', 'repairs', 'danger'),
    ('A&M',     'a&m',     '#9b59b6'),  # no distinct theme slot left
]


def create_analysis_tab(notebook, style):
    """
    Adds a "Results Analysis" tab that charts how many prescription logs were
    processed per day, read live from the 'result_logs' folder.

    Two views (toggle button):
      - Total logs per day (single line).
      - One line per form type (see MULTI_CATEGORIES, mirrors MODEL_IDS).

    Layout uses matplotlib constrained_layout so the chart always fits and
    resizes with the window; a navigation toolbar allows zoom / pan / save.
    """

    def _color(name):
        """Resolve a MULTI_CATEGORIES color: a theme attr name or a hex string."""
        if isinstance(name, str) and name.startswith('#'):
            return name
        return getattr(style.colors, name, style.colors.primary)

    def _matches(fname, suffix):
        """True if a log filename belongs to `suffix`'s form type.

        The form type is the token after the last '_'; compared whole and
        ignoring a trailing 's', so both current plural names (afos, insoles)
        and older singular ones (afo, insole) count, while 'kafo' and 'afos'
        can't collide. Legacy names with no current form type (old '_a&r' /
        'adapts and repairs' logs) match nothing here.
        """
        name = fname.lower()
        if name.endswith('.txt'):
            name = name[:-4]
        token = name.rsplit('_', 1)[-1]
        norm = lambda s: s[:-1] if s.endswith('s') else s
        return norm(token) == norm(suffix)

    # ------------------------------------------------------------------ tab
    style.configure("Analysis.TFrame", background=style.colors.bg)
    tab = ttk.Frame(notebook, style="Analysis.TFrame")
    notebook.add(tab, text="Results Analysis")

    multi_mode = True  # per-type breakdown is the more useful default

    def is_multi_mode():
        return multi_mode

    def set_multi_mode(value: bool):
        nonlocal multi_mode
        multi_mode = bool(value)

    # ------------------------------------------------------------- data read
    def _iter_day_folders():
        root = os.path.join(os.getcwd(), 'result_logs')
        if not os.path.exists(root):
            return
        for folder in sorted(os.listdir(root)):
            fp = os.path.join(root, folder)
            if os.path.isdir(fp):
                files = [f for f in os.listdir(fp)
                         if os.path.isfile(os.path.join(fp, f))]
                yield folder, files

    def get_log_data_single():
        """{'YYYY-MM-DD': total_file_count}."""
        return {folder: len(files) for folder, files in _iter_day_folders()}

    def get_log_data_multi():
        """{'YYYY-MM-DD': {suffix: count, ...}} — one entry per MULTI_CATEGORIES type."""
        data = {}
        for folder, files in _iter_day_folders():
            counts = {suffix: 0 for _, suffix, _ in MULTI_CATEGORIES}
            for fname in files:
                for _, suffix, _ in MULTI_CATEGORIES:
                    if _matches(fname, suffix):
                        counts[suffix] += 1
                        break
            data[folder] = counts
        return data

    # ------------------------------------------------------------- controls
    controls = ttk.Frame(tab, style="Analysis.TFrame")
    controls.pack(side='top', fill='x', padx=6, pady=4)

    mode_btn = ttk.Button(controls, text="Show Total", bootstyle="secondary")
    mode_btn.pack(side='left', padx=(0, 4))
    refresh_btn = ttk.Button(controls, text="Refresh", bootstyle="secondary-outline")
    refresh_btn.pack(side='left', padx=4)

    style.configure("Analysis.TLabel", background=style.colors.bg, foreground=style.colors.fg)
    summary_var = tk.StringVar(value="")
    summary_lbl = ttk.Label(controls, textvariable=summary_var, style="Analysis.TLabel")
    summary_lbl.pack(side='right', padx=6)

    # --------------------------------------------------------------- figure
    fig, ax = plt.subplots(figsize=(8, 5), constrained_layout=True)
    fig.patch.set_facecolor(style.colors.bg)

    chart_frame = ttk.Frame(tab, style="Analysis.TFrame")
    chart_frame.pack(side='top', fill='both', expand=True)

    canvas = FigureCanvasTkAgg(fig, master=chart_frame)
    canvas.get_tk_widget().pack(side='top', fill='both', expand=True)

    toolbar_frame = ttk.Frame(tab, style="Analysis.TFrame")
    toolbar_frame.pack(side='bottom', fill='x')
    toolbar = NavigationToolbar2Tk(canvas, toolbar_frame)  # auto-packs into toolbar_frame
    toolbar.update()
    # Best-effort: match the toolbar strip to the theme background (safe if unsupported).
    try:
        toolbar.config(background=style.colors.bg)
        for child in toolbar.winfo_children():
            child.config(background=style.colors.bg)
    except Exception:
        pass

    lines_metadata = {}  # {line: (dates, counts)}

    def _style_axes():
        fg = style.colors.fg
        ax.set_facecolor(style.colors.bg)
        ax.set_ylabel("Logs processed", color=fg)
        ax.tick_params(axis='y', colors=fg)
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        ax.grid(True, axis='y', alpha=0.25, color=fg)
        for spine in ax.spines.values():
            spine.set_edgecolor(fg)

    def refresh_chart():
        ax.clear()
        fig.patch.set_facecolor(style.colors.bg)
        lines_metadata.clear()
        plotted_lines = []
        fg = style.colors.fg

        # Which dataset?
        if is_multi_mode():
            data_dict = get_log_data_multi()
        else:
            data_dict = get_log_data_single()
        dates = list(data_dict.keys())

        # Empty state
        if not dates:
            ax.text(0.5, 0.5, "No logs found in result_logs/",
                    ha='center', va='center', transform=ax.transAxes, color=fg)
            ax.set_xticks([])
            ax.set_yticks([])
            for spine in ax.spines.values():
                spine.set_edgecolor(fg)
            summary_var.set("No logs yet")
            canvas.draw()
            return

        xvals = range(len(dates))
        marker_sz = 5 if len(dates) <= 40 else 3

        if is_multi_mode():
            grand = 0
            for label, suffix, color in MULTI_CATEGORIES:
                counts = [data_dict[d][suffix] for d in dates]
                total = sum(counts)
                grand += total
                (line,) = ax.plot(xvals, counts, marker='o', markersize=marker_sz,
                                  linestyle='-', color=_color(color),
                                  label=f"{label} ({total})")
                plotted_lines.append(line)
                lines_metadata[line] = (dates, counts)
            ax.set_title("Logs per day by form type", color=fg)
        else:
            counts = [data_dict[d] for d in dates]
            grand = sum(counts)
            (line,) = ax.plot(xvals, counts, marker='o', markersize=marker_sz,
                              linestyle='-', color=style.colors.primary,
                              label=f"All logs ({grand})")
            plotted_lines.append(line)
            lines_metadata[line] = (dates, counts)
            ax.set_title("Total logs per day", color=fg)

        # Date x-axis, thinned to ~12 labels so it stays readable
        n = len(dates)
        step = max(1, (n + 11) // 12)
        ticks = list(range(0, n, step))
        ax.set_xticks(ticks)
        ax.set_xticklabels([dates[i] for i in ticks], rotation=45,
                           ha='right', fontsize=8, color=fg)

        _style_axes()

        legend = ax.legend(facecolor=style.colors.bg, edgecolor=fg, fontsize=8)
        if legend:
            for text in legend.get_texts():
                text.set_color(fg)

        # Summary line
        busiest = max(dates, key=lambda d: (sum(data_dict[d].values())
                                            if is_multi_mode() else data_dict[d]))
        summary_var.set(
            f"{grand} logs · {n} days · {dates[0]} → {dates[-1]} · busiest {busiest}"
        )

        cursor = mplcursors.cursor(plotted_lines, hover=True)

        @cursor.connect("add")
        def on_add(sel):
            d, c = lines_metadata[sel.artist]
            i = max(0, min(int(round(sel.index)), len(d) - 1))
            lbl = sel.artist.get_label().split(' (')[0]
            sel.annotation.set_text(f"{lbl}\n{d[i]}: {c[i]}")

        canvas.draw()

    def toggle_multi_mode():
        set_multi_mode(not is_multi_mode())
        mode_btn.config(text="Show Total" if is_multi_mode() else "Show Breakdown")
        refresh_chart()

    mode_btn.config(command=toggle_multi_mode)
    refresh_btn.config(command=refresh_chart)

    refresh_chart()

    return tab, {
        'refresh_chart': refresh_chart,
        'set_multi_mode': set_multi_mode,
        'is_multi_mode': is_multi_mode,
    }
