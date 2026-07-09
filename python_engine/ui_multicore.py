import tkinter as tk
from tkinter import ttk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from process_data import core_stats
from ui_constants import *

class MulticoreTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._build_multicore()

    def _build_multicore(self):
        parent = self
        top = ttk.Frame(parent)
        top.pack(fill='both', expand=True, padx=8, pady=8)
        self.core_bars = []
        self.core_labels = []
        self.core_proc_labels = []
        for c in range(4):
            card = ttk.Frame(top, relief='flat')
            card.pack(fill='x', padx=4, pady=4)
            hdr = ttk.Frame(card)
            hdr.pack(fill='x')
            ttk.Label(hdr, text=f'CPU {c}', style='Header.TLabel', width=8).pack(side='left')
            lbl = ttk.Label(hdr, text='0.0%', style='Dim.TLabel')
            lbl.pack(side='right')
            self.core_labels.append(lbl)
            canvas = tk.Canvas(card, height=14, bg=BG, highlightthickness=0)
            canvas.pack(fill='x', padx=2, pady=2)
            self.core_bars.append(canvas)
            plbl = ttk.Label(card, text='', style='Dim.TLabel')
            plbl.pack(anchor='w', padx=4)
            self.core_proc_labels.append(plbl)
            
        self.imb_var = tk.StringVar(value='')
        ttk.Label(top, textvariable=self.imb_var, style='Dim.TLabel').pack(anchor='w', padx=4, pady=8)
        self.mc_fig = Figure(figsize=(10, 2.8), facecolor=BG)
        self.mc_ax = self.mc_fig.add_subplot(1, 1, 1)
        self.mc_ax.set_facecolor(SURFACE)
        self.mc_canvas = FigureCanvasTkAgg(self.mc_fig, master=top)
        self.mc_canvas.get_tk_widget().pack(fill='both', expand=True)

    def refresh(self):
        stats = core_stats(self.app.processes)
        utils = [min(stats[c]['util'], 100) for c in range(4)]
        
        for c in range(4):
            util = utils[c]
            color = RED if util > 70 else YELLOW if util > 40 else GREEN
            self.core_labels[c].config(text=f'{util:.1f}%', foreground=color)
            canvas = self.core_bars[c]
            canvas.delete('all')
            w = canvas.winfo_width() or 400
            fill_w = int(util / 100 * w)
            canvas.create_rectangle(0, 0, w, 14, fill=SURFACE, outline='')
            canvas.create_rectangle(0, 0, fill_w, 14, fill=color, outline='')
            top3 = ', '.join((p['name'] for p in sorted(stats[c]['procs'], key=lambda p: p['cpu'], reverse=True)[:4]))
            self.core_proc_labels[c].config(text=top3 or '—')
            
        mean = sum(utils) / 4
        std = (sum(((u - mean) ** 2 for u in utils)) / 4) ** 0.5
        self.imb_var.set(f'Load imbalance (std dev): {std:.2f}%  → ' + ('migration recommended' if std > 15 else 'load is balanced'))
        
        ax = self.mc_ax
        ax.clear()
        ax.set_facecolor(SURFACE)
        ax.bar([f'Core {c}' for c in range(4)], utils, color=[RED if u > 70 else YELLOW if u > 40 else ACCENT for u in utils])
        ax.set_ylim(0, 100)
        ax.set_ylabel('%', color=DIM, fontsize=8)
        ax.set_title('Per-core utilization', color=FG, fontsize=9)
        ax.tick_params(colors=DIM, labelsize=8)
        for spine in ax.spines.values():
            spine.set_edgecolor(DIM)
        self.mc_canvas.draw()
