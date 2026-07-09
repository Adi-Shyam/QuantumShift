import sys
import os
import time
import signal
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import matplotlib
matplotlib.use('TkAgg')

from process_data import get_real_processes, _update_simulated_processes, PSUTIL_AVAILABLE, _generate_simulated_processes
from ui_constants import *
from ui_monitor import MonitorTab
from ui_analysis import AnalysisTab
from ui_simulator import SimulatorTab
from ui_multicore import MulticoreTab
from ui_fairness import FairnessTab

class SchedulerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Linux Scheduler Analysis Platform')
        self.geometry('1200x800')
        self.minsize(960, 680)
        self.configure(bg=BG)
        
        self.use_real_data = tk.BooleanVar(value=PSUTIL_AVAILABLE)
        self.processes = get_real_processes() if PSUTIL_AVAILABLE else _generate_simulated_processes()
        self.cpu_history = [0.0] * 20
        self.ctx_history = [0] * 20
        self.running = True
        
        self._setup_styles()
        self._build_notebook()
        self._start_updates()
        
        self.protocol('WM_DELETE_WINDOW', self._on_close)

    def _setup_styles(self):
        s = ttk.Style(self)
        s.theme_use('clam')
        s.configure('.', background=BG, foreground=FG)
        s.configure('TNotebook', background=BG, borderwidth=0)
        s.configure('TNotebook.Tab', background=SURFACE, foreground=DIM, padding=[12, 5], font=('Courier New', 10))
        s.map('TNotebook.Tab', background=[('selected', BG)], foreground=[('selected', ACCENT)])
        s.configure('TFrame', background=BG)
        s.configure('TLabel', background=BG, foreground=FG, font=('Courier New', 10))
        s.configure('Header.TLabel', background=BG, foreground=ACCENT, font=('Courier New', 11, 'bold'))
        s.configure('Dim.TLabel', background=BG, foreground=DIM, font=('Courier New', 9))
        s.configure('TButton', background=SURFACE, foreground=FG, font=('Courier New', 10), relief='flat', borderwidth=1)
        s.map('TButton', background=[('active', '#313244')], foreground=[('active', ACCENT)])
        s.configure('Danger.TButton', background='#3d1e2a', foreground=RED, font=('Courier New', 10), relief='flat')
        s.map('Danger.TButton', background=[('active', '#5c2a3a')], foreground=[('active', RED)])
        s.configure('Treeview', background=SURFACE, foreground=FG, fieldbackground=SURFACE, font=('Courier New', 9), rowheight=21, borderwidth=0)
        s.configure('Treeview.Heading', background=BG, foreground=ACCENT, font=('Courier New', 9, 'bold'), relief='flat')
        s.map('Treeview', background=[('selected', '#313244')])
        s.configure('TEntry', fieldbackground=SURFACE, foreground=FG, insertcolor=FG, font=('Courier New', 10))
        s.configure('TCombobox', fieldbackground=SURFACE, foreground=FG, font=('Courier New', 10))
        s.configure('TScrollbar', background=SURFACE, troughcolor=BG, arrowcolor=DIM)

    def _build_notebook(self):
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill='both', expand=True, padx=8, pady=8)
        
        self.tab_monitor = MonitorTab(self.nb, self)
        self.tab_analysis = AnalysisTab(self.nb, self)
        self.tab_simulator = SimulatorTab(self.nb, self)
        self.tab_multicore = MulticoreTab(self.nb, self)
        self.tab_fairness = FairnessTab(self.nb, self)
        
        self.nb.add(self.tab_monitor, text='Process Monitor')
        self.nb.add(self.tab_analysis, text='Scheduler Analysis')
        self.nb.add(self.tab_simulator, text='Algorithm Simulator')
        self.nb.add(self.tab_multicore, text='Multi-Core View')
        self.nb.add(self.tab_fairness, text='Fairness Metrics')

    def _start_updates(self):
        self._tick()

    def _tick(self):
        if not self.running:
            return
            
        if self.use_real_data.get() and PSUTIL_AVAILABLE:
            from process_data import update_real_processes
            self.processes = update_real_processes(self.processes)
        else:
            self.processes = _update_simulated_processes(self.processes)
            
        self.cpu_history = self.cpu_history[1:] + [sum((p['cpu'] for p in self.processes))]
        self.ctx_history = self.ctx_history[1:] + [sum((p['vcs'] + p['nvcs'] for p in self.processes))]
        
        try:
            tab = self.nb.index(self.nb.select())
            if tab == 0:
                self.tab_monitor.refresh()
            elif tab == 1:
                self.tab_analysis.refresh()
            elif tab == 3:
                self.tab_multicore.refresh()
            elif tab == 4:
                self.tab_fairness.refresh()
        except Exception as e:
            import traceback
            traceback.print_exc()
            
        self.after(1500, self._tick)

    def _on_close(self):
        self.running = False
        self.destroy()