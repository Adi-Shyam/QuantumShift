import os
import signal
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

from process_data import set_scheduler, PSUTIL_AVAILABLE
from ui_constants import *

class MonitorTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._paused_pids = set()
        self._build_monitor()

    def _build_monitor(self):
        parent = self
        top = ttk.Frame(parent)
        top.pack(fill='x', padx=10, pady=(8, 2))
        self.mon_stats_var = tk.StringVar(value='Loading…')
        ttk.Label(top, textvariable=self.mon_stats_var, style='Dim.TLabel').pack(side='left')
        src_frame = ttk.Frame(top)
        src_frame.pack(side='right')
        ttk.Label(src_frame, text='Data:', style='Dim.TLabel').pack(side='left')
        
        src_cb = ttk.Checkbutton(src_frame, text='Live (psutil)', variable=self.app.use_real_data, onvalue=True, offvalue=False, style='TCheckbutton')
        if not PSUTIL_AVAILABLE:
            src_cb.config(state='disabled')
            ttk.Label(src_frame, text=' [pip install psutil]', foreground=YELLOW, background=BG, font=('Courier New', 8)).pack(side='left')
        src_cb.pack(side='left', padx=4)
        
        ctrl = ttk.Frame(parent)
        ctrl.pack(fill='x', padx=10, pady=2)
        ttk.Label(ctrl, text='Sort:', style='Dim.TLabel').pack(side='left')
        self.mon_sort = ttk.Combobox(ctrl, values=['cpu', 'mem', 'pid', 'vrt', 'cs'], state='readonly', width=6, font=('Courier New', 9))
        self.mon_sort.set('cpu')
        self.mon_sort.pack(side='left', padx=(2, 10))
        ttk.Label(ctrl, text='Policy:', style='Dim.TLabel').pack(side='left')
        self.mon_pol = ttk.Combobox(ctrl, values=['ALL', 'CFS', 'FIFO', 'RR', 'BATCH', 'IDLE', 'EXT'], state='readonly', width=7, font=('Courier New', 9))
        self.mon_pol.set('ALL')
        self.mon_pol.pack(side='left', padx=2)
        ttk.Label(ctrl, text='  Search:', style='Dim.TLabel').pack(side='left')
        self.mon_search = tk.StringVar()
        ttk.Entry(ctrl, textvariable=self.mon_search, width=14).pack(side='left', padx=2)
        
        act = ttk.Frame(parent)
        act.pack(fill='x', padx=10, pady=(2, 0))
        ttk.Label(act, text='Selected process:', style='Dim.TLabel').pack(side='left')
        ttk.Button(act, text='⏸ Pause', command=self._action_pause).pack(side='left', padx=2)
        ttk.Button(act, text='▶ Resume', command=self._action_resume).pack(side='left', padx=2)
        ttk.Button(act, text='⏹ Stop', command=self._action_stop).pack(side='left', padx=2)
        ttk.Button(act, text='✕ Kill', command=self._action_kill, style='Danger.TButton').pack(side='left', padx=2)
        ttk.Button(act, text='↑↓ Renice', command=self._action_renice).pack(side='left', padx=2)
        ttk.Button(act, text='⚙ Policy', command=self._action_policy).pack(side='left', padx=2)
        ttk.Button(act, text='🚀 EQS (Custom)', command=self._action_use_custom).pack(side='left', padx=2)
        ttk.Button(act, text='ℹ Info', command=self._action_info).pack(side='left', padx=2)
        
        cols = ('pid', 'name', 'user', 'state', 'ni', 'pri', 'cpu', 'mem', 'policy', 'vruntime', 'vcs', 'nvcs', 'core')
        frame = ttk.Frame(parent)
        frame.pack(fill='both', expand=True, padx=10, pady=6)
        vsb = ttk.Scrollbar(frame, orient='vertical')
        vsb.pack(side='right', fill='y')
        self.mon_tree = ttk.Treeview(frame, columns=cols, show='headings', yscrollcommand=vsb.set, selectmode='browse')
        vsb.config(command=self.mon_tree.yview)
        self.mon_tree.pack(fill='both', expand=True)
        
        widths = [55, 110, 80, 35, 35, 35, 75, 60, 65, 95, 60, 55, 45]
        headers = {'cpu': 'CPU %', 'mem': 'MEM %', 'vruntime': 'VRUNTIME', 'vcs': 'V.CS', 'nvcs': 'NV.CS'}
        for (col, w) in zip(cols, widths):
            self.mon_tree.heading(col, text=headers.get(col, col.upper()))
            self.mon_tree.column(col, width=w, anchor='w', stretch=False)
        self.mon_tree.tag_configure('R', foreground=GREEN)
        self.mon_tree.tag_configure('D', foreground=RED)
        self.mon_tree.tag_configure('Z', foreground=MAUVE)
        self.mon_tree.tag_configure('S', foreground=FG)
        self.mon_tree.tag_configure('T', foreground=YELLOW)
        
        self.mon_tree.bind('<Button-3>', self._on_tree_right_click)
        self.mon_tree.bind('<Double-1>', lambda e: self._action_info())

    def _get_selected_pid(self):
        sel = self.mon_tree.selection()
        if not sel:
            messagebox.showinfo('No selection', 'Please select a process first.')
            return None
        vals = self.mon_tree.item(sel[0])['values']
        return int(vals[0])

    def _get_selected_proc_info(self):
        sel = self.mon_tree.selection()
        if not sel:
            return None
        return self.mon_tree.item(sel[0])['values']

    def _on_tree_right_click(self, event):
        item = self.mon_tree.identify_row(event.y)
        if not item:
            return
        self.mon_tree.selection_set(item)
        vals = self.mon_tree.item(item)['values']
        pid = int(vals[0])
        name = vals[1]
        
        menu = tk.Menu(self, tearoff=0, bg=SURFACE, fg=FG, activebackground='#313244', activeforeground=ACCENT, font=('Courier New', 9))
        menu.add_command(label=f'  PID {pid} — {name}', state='disabled', foreground=DIM)
        menu.add_separator()
        menu.add_command(label='⏸  Pause  (SIGSTOP)', command=self._action_pause)
        menu.add_command(label='▶  Resume (SIGCONT)', command=self._action_resume)
        menu.add_separator()
        menu.add_command(label='⏹  Stop   (SIGTERM)', command=self._action_stop)
        menu.add_command(label='✕  Kill   (SIGKILL)', command=self._action_kill)
        menu.add_separator()
        menu.add_command(label='↑↓ Renice…', command=self._action_renice)
        menu.add_command(label='⚙  Change Policy…', command=self._action_policy)
        menu.add_command(label='🚀 Use Custom Scheduler (EQS)', command=self._action_use_custom)
        menu.add_separator()
        menu.add_command(label='ℹ  Process Info', command=self._action_info)
        menu.post(event.x_root, event.y_root)

    def _action_pause(self):
        pid = self._get_selected_pid()
        if pid is None:
            return
        try:
            os.kill(pid, signal.SIGSTOP)
            self._paused_pids.add(pid)
            messagebox.showinfo('Paused', f'PID {pid} paused (SIGSTOP)')
        except PermissionError:
            messagebox.showerror('Permission Denied', f'Cannot pause PID {pid}.\nTry running as root.')
        except ProcessLookupError:
            messagebox.showerror('Not Found', f'PID {pid} no longer exists.')
        except Exception as e:
            messagebox.showerror('Error', str(e))

    def _action_resume(self):
        pid = self._get_selected_pid()
        if pid is None:
            return
        try:
            os.kill(pid, signal.SIGCONT)
            self._paused_pids.discard(pid)
            messagebox.showinfo('Resumed', f'PID {pid} resumed (SIGCONT)')
        except PermissionError:
            messagebox.showerror('Permission Denied', f'Cannot resume PID {pid}.\nTry running as root.')
        except ProcessLookupError:
            messagebox.showerror('Not Found', f'PID {pid} no longer exists.')
        except Exception as e:
            messagebox.showerror('Error', str(e))

    def _action_stop(self):
        pid = self._get_selected_pid()
        if pid is None:
            return
        vals = self._get_selected_proc_info()
        name = vals[1] if vals else str(pid)
        if not messagebox.askyesno('Confirm Stop', f'Send SIGTERM to PID {pid} ({name})?'):
            return
        try:
            os.kill(pid, signal.SIGTERM)
        except Exception as e:
            messagebox.showerror('Error', str(e))

    def _action_kill(self):
        pid = self._get_selected_pid()
        if pid is None:
            return
        vals = self._get_selected_proc_info()
        name = vals[1] if vals else str(pid)
        if not messagebox.askyesno('Confirm KILL', f'⚠ Force-kill PID {pid} ({name}) with SIGKILL?', icon='warning'):
            return
        try:
            os.kill(pid, signal.SIGKILL)
        except Exception as e:
            messagebox.showerror('Error', str(e))

    def _action_renice(self):
        pid = self._get_selected_pid()
        if pid is None:
            return
        val = simpledialog.askinteger('Renice', f'Enter new nice value for PID {pid} (-20 to 19):', minvalue=-20, maxvalue=19, parent=self)
        if val is None:
            return
        try:
            if PSUTIL_AVAILABLE:
                import psutil
                psutil.Process(pid).nice(val)
            else:
                os.system(f'renice {val} -p {pid}')
            messagebox.showinfo('Reniced', f'PID {pid} nice value set to {val}')
        except Exception as e:
            messagebox.showerror('Error', str(e))

    def _action_policy(self):
        pid = self._get_selected_pid()
        if pid is None:
            return
        dlg = tk.Toplevel(self)
        dlg.title(f'Change Policy — PID {pid}')
        dlg.configure(bg=BG)
        dlg.grab_set()
        dlg.resizable(False, False)
        
        ttk.Label(dlg, text=f'PID: {pid}', style='Header.TLabel').pack(pady=(12, 2), padx=20, anchor='w')
        ttk.Label(dlg, text='Note: pkexec will prompt for password if root is required.', foreground=YELLOW, background=BG, font=('Courier New', 8)).pack(padx=20, anchor='w')
        
        pol_var = tk.StringVar(value='CFS')
        ttk.Combobox(dlg, textvariable=pol_var, values=['CFS', 'FIFO', 'RR', 'BATCH', 'IDLE', 'EXT'], state='readonly', width=12, font=('Courier New', 10)).pack(padx=20, anchor='w', pady=10)
        
        pri_frame = ttk.Frame(dlg)
        pri_frame.pack(padx=20, pady=6, anchor='w')
        ttk.Label(pri_frame, text='RT Priority (FIFO/RR, 1–99):', style='Dim.TLabel').pack(side='left')
        pri_var = tk.IntVar(value=1)
        ttk.Entry(pri_frame, textvariable=pri_var, width=5).pack(side='left', padx=4)

        def apply():
            policy = pol_var.get()
            pri = pri_var.get() if policy in ('FIFO', 'RR') else 0
            try:
                set_scheduler(pid, policy, pri)
                messagebox.showinfo('Done', f'PID {pid} policy set to {policy}')
                dlg.destroy()
            except Exception as e:
                messagebox.showerror('Error', str(e))
                
        ttk.Button(dlg, text='Apply', command=apply).pack(pady=10)

    def _action_use_custom(self):
        pid = self._get_selected_pid()
        if pid is None:
            return
        vals = self._get_selected_proc_info()
        name = vals[1] if vals else str(pid)
        try:
            set_scheduler(pid, 'EXT', 0)
            messagebox.showinfo('Done', f'PID {pid} ({name}) moved to Custom Algorithm (SCHED_EXT)')
        except Exception as e:
            messagebox.showerror('Error', str(e))

    def _action_info(self):
        vals = self._get_selected_proc_info()
        if vals is None:
            return
        pid = int(vals[0])
        lines = [f'{k}: {v}' for k, v in zip(('PID', 'Name', 'User', 'State', 'Nice', 'Priority', 'CPU%', 'MEM%', 'Policy', 'VRuntime', 'Vol.CS', 'Nvol.CS', 'Core'), vals)]
        
        dlg = tk.Toplevel(self)
        dlg.title(f'Process Info — PID {pid}')
        dlg.configure(bg=BG)
        
        text = tk.Text(dlg, bg=SURFACE, fg=FG, font=('Courier New', 10), width=40, height=len(lines) + 2, padx=10, pady=8)
        text.pack(padx=10, pady=10)
        text.insert('1.0', '\n'.join(lines))
        text.config(state='disabled')

    def refresh(self):
        sort_by = self.mon_sort.get()
        filt_pol = self.mon_pol.get()
        search = self.mon_search.get().lower()
        
        procs = [p for p in self.app.processes if (filt_pol == 'ALL' or p['policy'] == filt_pol) and (not search or search in p['name'].lower() or search in str(p['pid']))]
        key_map = {'cpu': lambda p: -p['cpu'], 'mem': lambda p: -p['mem'], 'pid': lambda p: p['pid'], 'vrt': lambda p: -p['vrt'], 'cs': lambda p: -(p['vcs'] + p['nvcs'])}
        procs = sorted(procs, key=key_map.get(sort_by, key_map['cpu']))
        
        total_cpu = sum((p['cpu'] for p in self.app.processes))
        running = sum((1 for p in self.app.processes if p['state'] == 'R'))
        policies = {}
        for p in self.app.processes:
            policies[p['policy']] = policies.get(p['policy'], 0) + 1
        pol_str = '  '.join((f'{k}:{v}' for (k, v) in sorted(policies.items())))
        
        self.mon_stats_var.set(f'Procs: {len(self.app.processes)}   Running: {running}   Total CPU: {total_cpu:.1f}%   {pol_str}')
        
        sel = self.mon_tree.selection()
        sel_pid = int(self.mon_tree.item(sel[0])['values'][0]) if sel else None
        self.mon_tree.delete(*self.mon_tree.get_children())
        
        for p in procs:
            bar_len = int(p['cpu'] / 5)
            bar = '█' * bar_len + '░' * (6 - min(bar_len, 6))
            vrt = str(p['vrt']) if p['policy'] == 'CFS' else '—'
            paused = ' ⏸' if p['pid'] in self._paused_pids else ''
            iid = self.mon_tree.insert('', 'end', tags=(p['state'],), values=(
                p['pid'], p['name'] + paused, p['user'], p['state'], p['ni'], p['pri'],
                f"{bar} {p['cpu']:.1f}", f"{p['mem']:.1f}", p['policy'], vrt, p['vcs'], p['nvcs'], p['core']
            ))
            if sel_pid == p['pid']:
                self.mon_tree.selection_set(iid)
