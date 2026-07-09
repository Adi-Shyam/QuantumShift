import tkinter as tk
from tkinter import ttk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from process_data import _check_proc_sched_available
from ui_constants import *

class AnalysisTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._build_scheduler()

    def _build_scheduler(self):
        parent = self
        badge_row = ttk.Frame(parent)
        badge_row.pack(fill='x', padx=10, pady=(6, 0))
        self.vrt_source_var = tk.StringVar(value='')
        self.vrt_source_lbl = ttk.Label(badge_row, textvariable=self.vrt_source_var, font=('Courier New', 8), background=BG)
        self.vrt_source_lbl.pack(side='left')
        self.show_rbtree = tk.BooleanVar(value=True)
        ttk.Checkbutton(badge_row, text='Show RB-Tree Order', variable=self.show_rbtree).pack(side='right', padx=4)
        
        fig = Figure(figsize=(11, 7.5), facecolor=BG)
        fig.subplots_adjust(hspace=0.55, wspace=0.35)
        self.sched_axes = [fig.add_subplot(3, 2, i + 1) for i in range(6)]
        
        for ax in self.sched_axes:
            ax.set_facecolor(SURFACE)
            ax.tick_params(colors=DIM, labelsize=8)
            for spine in ax.spines.values():
                spine.set_edgecolor(DIM)
                
        self.sched_canvas = FigureCanvasTkAgg(fig, master=parent)
        self.sched_canvas.get_tk_widget().pack(fill='both', expand=True, padx=8, pady=8)
        self.sched_fig = fig

    def refresh(self):
        axes = self.sched_axes
        proc_sched_live = _check_proc_sched_available()
        
        if proc_sched_live:
            self.vrt_source_var.set('⬤  vruntime source: live /proc/<pid>/sched')
            self.vrt_source_lbl.config(foreground=GREEN)
        else:
            self.vrt_source_var.set('⬤  vruntime source: estimated (cpu% × 1M ns)  —  /proc/<pid>/sched unavailable on this kernel')
            self.vrt_source_lbl.config(foreground=YELLOW)
            
        top8 = sorted(self.app.processes, key=lambda p: p['cpu'], reverse=True)[:8]
        ax = axes[0]
        ax.clear()
        ax.set_facecolor(SURFACE)
        colors = [RED if p['cpu'] > 50 else YELLOW if p['cpu'] > 20 else ACCENT for p in top8]
        ax.barh([p['name'][:9] for p in top8], [p['cpu'] for p in top8], color=colors)
        ax.set_title('Top 8 by CPU%', color=FG, fontsize=9)
        ax.tick_params(colors=DIM, labelsize=8)
        ax.set_xlabel('%', color=DIM, fontsize=8)
        for spine in ax.spines.values():
            spine.set_edgecolor(DIM)
            
        cfs_procs_vrt = sorted([p for p in self.app.processes if p['policy'] == 'CFS' and p['vrt'] > 0], key=lambda p: p['vrt'], reverse=True)[:8]
        ax = axes[1]
        ax.clear()
        ax.set_facecolor(SURFACE)
        if cfs_procs_vrt:
            vrts_k = [p['vrt'] // 1000 for p in cfs_procs_vrt]
            names = [p['name'][:9] for p in cfs_procs_vrt]
            colors = [RED if v > 5000000 else YELLOW if v > 1000000 else ACCENT for v in vrts_k]
            ax.barh(names, vrts_k, color=colors)
            ax.set_xlabel('×10³ ns', color=DIM, fontsize=8)
            vrt_label = 'live /proc' if proc_sched_live else 'est.'
            ax.set_title(f'Top 8 by vruntime  [{vrt_label}]', color=FG, fontsize=9)
        else:
            ax.text(0.5, 0.5, 'No CFS processes', ha='center', va='center', color=DIM, fontsize=9, transform=ax.transAxes)
            ax.set_title('Top 8 by vruntime', color=FG, fontsize=9)
        ax.tick_params(colors=DIM, labelsize=8)
        for spine in ax.spines.values():
            spine.set_edgecolor(DIM)
            
        ax = axes[2]
        ax.clear()
        ax.set_facecolor(SURFACE)
        ax.plot(self.app.cpu_history, color=ACCENT, linewidth=1.2)
        ax.fill_between(range(len(self.app.cpu_history)), self.app.cpu_history, alpha=0.15, color=ACCENT)
        ax.set_title('CPU % over time', color=FG, fontsize=9)
        ax.set_ylim(0, max(max(self.app.cpu_history, default=0) * 1.2, 10))
        ax.tick_params(colors=DIM, labelsize=8)
        for spine in ax.spines.values():
            spine.set_edgecolor(DIM)
            
        policies = {}
        for p in self.app.processes:
            policies[p['policy']] = policies.get(p['policy'], 0) + 1
        ax = axes[3]
        ax.clear()
        ax.set_facecolor(SURFACE)
        colors_pie = [POLICY_COLOR.get(k, DIM) for k in policies]
        ax.pie(list(policies.values()), labels=list(policies.keys()), colors=colors_pie, textprops={'color': FG, 'fontsize': 8}, autopct='%1.0f%%', pctdistance=0.8, wedgeprops={'edgecolor': BG, 'linewidth': 1})
        ax.set_title('Policy distribution', color=FG, fontsize=9)
        
        top8_cs = sorted(self.app.processes, key=lambda p: p['vcs'] + p['nvcs'], reverse=True)[:8]
        ax = axes[4]
        ax.clear()
        ax.set_facecolor(SURFACE)
        cs_vals = [p['vcs'] + p['nvcs'] for p in top8_cs]
        ax.barh([p['name'][:9] for p in top8_cs], cs_vals, color=MAUVE)
        ax.set_title('Top 8 by Context Switches', color=FG, fontsize=9)
        ax.tick_params(colors=DIM, labelsize=8)
        for spine in ax.spines.values():
            spine.set_edgecolor(DIM)
            
        ax = axes[5]
        ax.clear()
        ax.set_facecolor(SURFACE)
        ax.plot(self.app.ctx_history, color=YELLOW, linewidth=1.2)
        ax.fill_between(range(len(self.app.ctx_history)), self.app.ctx_history, alpha=0.15, color=YELLOW)
        ax.set_title('Total Context Switches over time', color=FG, fontsize=9)
        ax.set_ylim(0, max(max(self.app.ctx_history, default=0) * 1.2, 10))
        ax.tick_params(colors=DIM, labelsize=8)
        for spine in ax.spines.values():
            spine.set_edgecolor(DIM)
            
        self.sched_canvas.draw()
