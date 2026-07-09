import tkinter as tk
from tkinter import ttk, messagebox
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from algorithms import fcfs, sjf, srtf, round_robin, priority_np, multilevel_queue, cfs, compare_all
from custom_algorithm import custom_scheduler
from ui_constants import *

class SimulatorTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._build_simulator()

    def _build_simulator(self):
        parent = self
        left = ttk.Frame(parent)
        right = ttk.Frame(parent)
        left.pack(side='left', fill='y', padx=(10, 4), pady=8)
        right.pack(side='left', fill='both', expand=True, padx=(4, 10), pady=8)
        
        ttk.Label(left, text='Algorithm', style='Header.TLabel').pack(anchor='w')
        self.sim_algo = ttk.Combobox(left, values=['FCFS', 'SJF', 'SRTF', 'Round Robin', 'Priority (NP)', 'Multilevel Queue', 'CFS', 'Custom Algorithm', 'CFS vs Custom', 'Compare All'], state='readonly', width=18, font=('Courier New', 10))
        self.sim_algo.set('FCFS')
        self.sim_algo.pack(anchor='w', pady=(2, 4))
        self.sim_algo_desc = tk.StringVar(value='')
        ttk.Label(left, textvariable=self.sim_algo_desc, foreground=DIM, background=BG, font=('Courier New', 8), wraplength=180).pack(anchor='w', pady=(0, 6))
        _algo_descs = {'FCFS': 'First Come First Served. Non-preemptive.', 'SJF': 'Shortest Job First. Non-preemptive.', 'SRTF': 'Shortest Remaining Time First. Preemptive.', 'Round Robin': 'Round Robin with configurable quantum.', 'Priority (NP)': 'Non-preemptive Priority.', 'Multilevel Queue': 'Two queues: burst≤3 → RR, else → FCFS.', 'CFS': 'Completely Fair Scheduler (simulated vruntime).', 'Custom Algorithm': 'Your custom logic from custom_algorithm.py.', 'CFS vs Custom': 'Compare CFS and your custom algorithm.', 'Compare All': 'Run all algorithms and compare.'}

        def on_algo_change(*_):
            self.sim_algo_desc.set(_algo_descs.get(self.sim_algo.get(), ''))
        self.sim_algo.bind('<<ComboboxSelected>>', on_algo_change)
        on_algo_change()
        
        ttk.Label(left, text='Quantum (RR/MLQ)', style='Dim.TLabel').pack(anchor='w')
        self.sim_q = tk.IntVar(value=2)
        ttk.Entry(left, textvariable=self.sim_q, width=6).pack(anchor='w', pady=(2, 8))
        
        ttk.Label(left, text='Processes', style='Header.TLabel').pack(anchor='w')
        job_frame = ttk.Frame(left)
        job_frame.pack(fill='x')
        cols = ('name', 'arrival', 'burst', 'priority')
        self.sim_tree = ttk.Treeview(job_frame, columns=cols, show='headings', height=12, selectmode='browse')
        for (col, w) in zip(cols, [55, 60, 50, 60]):
            self.sim_tree.heading(col, text=col.upper())
            self.sim_tree.column(col, width=w, anchor='center', stretch=False)
        self.sim_tree.pack(fill='x')
        self.sim_jobs = [{'id': 1, 'name': 'P1', 'arrival': 0, 'burst': 5, 'priority': 3}, {'id': 2, 'name': 'P2', 'arrival': 0, 'burst': 5, 'priority': 1}, {'id': 3, 'name': 'P3', 'arrival': 0, 'burst': 7, 'priority': 4}, {'id': 4, 'name': 'P4', 'arrival': 0, 'burst': 5, 'priority': 2}, {'id': 5, 'name': 'P5', 'arrival': 0, 'burst': 5, 'priority': 3}, {'id': 6, 'name': 'P6', 'arrival': 0, 'burst': 5, 'priority': 2}]
        self._reload_sim_tree()
        
        btn_row = ttk.Frame(left)
        btn_row.pack(fill='x', pady=4)
        ttk.Button(btn_row, text='+ Add', command=self._add_job).pack(side='left', padx=2)
        ttk.Button(btn_row, text='✎ Edit', command=self._edit_job).pack(side='left', padx=2)
        ttk.Button(btn_row, text='– Rm', command=self._del_job).pack(side='left', padx=2)
        ttk.Button(btn_row, text='⟳', command=self._reset_jobs, width=3).pack(side='left', padx=2)
        ttk.Button(left, text='📷 Snap Live Procs', command=self._snap_live_procs).pack(fill='x', pady=(2, 8))
        ttk.Button(left, text='▶ Run Simulation', command=self._run_sim).pack(fill='x')
        
        ttk.Label(right, text='Results', style='Header.TLabel').pack(anchor='w')
        res_cols = ('process', 'arrival', 'burst', 'priority', 'start', 'end', 'wait', 'tat')
        res_frame = ttk.Frame(right)
        res_frame.pack(fill='x', pady=4)
        self.sim_res_tree = ttk.Treeview(res_frame, columns=res_cols, show='headings', height=4)
        for (col, w) in zip(res_cols, [65, 60, 50, 60, 50, 50, 60, 75]):
            self.sim_res_tree.heading(col, text=col.upper())
            self.sim_res_tree.column(col, width=w, anchor='center', stretch=False)
        self.sim_res_tree.pack(fill='x')
        self.sim_res_tree.tag_configure('low', foreground=GREEN)
        self.sim_res_tree.tag_configure('med', foreground=YELLOW)
        self.sim_res_tree.tag_configure('high', foreground=RED)
        
        self.sim_metrics_var = tk.StringVar(value='')
        ttk.Label(right, textvariable=self.sim_metrics_var, foreground=TEAL, background=BG, font=('Courier New', 9)).pack(anchor='w', pady=4)
        
        self.sim_fig = Figure(figsize=(8, 2.0), facecolor=BG)
        self.sim_ax = self.sim_fig.add_subplot(1, 1, 1)
        self.sim_ax.set_facecolor(SURFACE)
        self.sim_canvas = FigureCanvasTkAgg(self.sim_fig, master=right)
        self.sim_canvas.get_tk_widget().pack(fill='both', expand=True)
        
        ttk.Label(right, text='Quantum Dynamics  —  Custom Algorithm (EQS)', style='Header.TLabel').pack(anchor='w', pady=(6, 0))
        self.quantum_fig = Figure(figsize=(8, 2.4), facecolor=BG)
        self.quantum_fig.subplots_adjust(left=0.07, right=0.97, wspace=0.35, top=0.82, bottom=0.22)
        self.quantum_ax = self.quantum_fig.add_subplot(1, 2, 1)
        self.quantum_util_ax = self.quantum_fig.add_subplot(1, 2, 2)
        for ax in (self.quantum_ax, self.quantum_util_ax):
            ax.set_facecolor(SURFACE)
            ax.tick_params(colors=DIM, labelsize=8)
            for spine in ax.spines.values():
                spine.set_edgecolor(DIM)
        self.quantum_canvas = FigureCanvasTkAgg(self.quantum_fig, master=right)
        self.quantum_canvas.get_tk_widget().pack(fill='both', expand=True)
        self._clear_quantum_chart()

    def _reload_sim_tree(self):
        self.sim_tree.delete(*self.sim_tree.get_children())
        for j in self.sim_jobs:
            self.sim_tree.insert('', 'end', iid=str(j['id']), values=(j['name'], j['arrival'], j['burst'], j.get('priority', 0)))

    def _add_job(self):
        self._job_dialog(None)

    def _edit_job(self):
        sel = self.sim_tree.selection()
        if not sel:
            return
        job = next((j for j in self.sim_jobs if j['id'] == int(sel[0])), None)
        if job:
            self._job_dialog(job)

    def _job_dialog(self, job=None):
        is_edit = job is not None
        dlg = tk.Toplevel(self)
        dlg.title('Edit Process' if is_edit else 'Add Process')
        dlg.configure(bg=BG)
        dlg.grab_set()
        fields = {}
        defaults = {'Name': job['name'] if is_edit else f'P{len(self.sim_jobs) + 1}', 'Arrival': str(job['arrival']) if is_edit else str(len(self.sim_jobs)), 'Burst': str(job['burst']) if is_edit else '3', 'Priority': str(job.get('priority', 0)) if is_edit else '0'}
        for (label, default) in defaults.items():
            row = ttk.Frame(dlg)
            row.pack(fill='x', padx=14, pady=3)
            ttk.Label(row, text=label, width=9).pack(side='left')
            var = tk.StringVar(value=default)
            ttk.Entry(row, textvariable=var, width=10).pack(side='left')
            fields[label] = var

        def ok():
            try:
                new_data = {'id': job['id'] if is_edit else max((j['id'] for j in self.sim_jobs), default=0) + 1, 'name': fields['Name'].get(), 'arrival': int(fields['Arrival'].get()), 'burst': max(1, int(fields['Burst'].get())), 'priority': int(fields['Priority'].get())}
                if is_edit:
                    idx = next((i for (i, j) in enumerate(self.sim_jobs) if j['id'] == job['id']))
                    self.sim_jobs[idx] = new_data
                else:
                    self.sim_jobs.append(new_data)
                self._reload_sim_tree()
                dlg.destroy()
            except ValueError:
                messagebox.showerror('Invalid input', 'Numbers only.', parent=dlg)
        ttk.Button(dlg, text='Save' if is_edit else 'Add', command=ok).pack(pady=8)

    def _del_job(self):
        sel = self.sim_tree.selection()
        if sel:
            self.sim_jobs = [j for j in self.sim_jobs if j['id'] != int(sel[0])]
            self._reload_sim_tree()

    def _reset_jobs(self):
        self.sim_jobs = [{'id': 1, 'name': 'P1', 'arrival': 0, 'burst': 5, 'priority': 3}, {'id': 2, 'name': 'P2', 'arrival': 0, 'burst': 5, 'priority': 1}, {'id': 3, 'name': 'P3', 'arrival': 0, 'burst': 7, 'priority': 4}, {'id': 4, 'name': 'P4', 'arrival': 0, 'burst': 5, 'priority': 2}, {'id': 5, 'name': 'P5', 'arrival': 0, 'burst': 5, 'priority': 3}, {'id': 6, 'name': 'P6', 'arrival': 0, 'burst': 5, 'priority': 2}]
        self._reload_sim_tree()

    def _snap_live_procs(self):
        top = sorted(self.app.processes, key=lambda p: p['cpu'], reverse=True)[:8]
        new_jobs = []
        for (i, p) in enumerate(top):
            burst = max(1, int(p['cpu'] / 5))
            new_jobs.append({'id': i + 1, 'name': p['name'][:5], 'arrival': i, 'burst': burst, 'priority': p['pri']})
        self.sim_jobs = new_jobs
        self._reload_sim_tree()

    def _run_sim(self):
        algo = self.sim_algo.get()
        q = max(1, self.sim_q.get())
        self.sim_res_tree.delete(*self.sim_res_tree.get_children())
        self.sim_ax.clear()
        self.sim_ax.set_facecolor(SURFACE)
        if algo in ('Compare All', 'CFS vs Custom'):
            if algo == 'Compare All':
                results = compare_all(self.sim_jobs, q)
            else:
                results = {}
                try:
                    (cfs_done, _) = cfs(self.sim_jobs)
                except:
                    cfs_done = []
                try:
                    (cust_done, _, _ql) = custom_scheduler(self.sim_jobs, q)
                except:
                    cust_done = []
                for (n, done) in [('CFS', cfs_done), ('Custom', cust_done)]:
                    ln = len(done)
                    results[n] = {'awt': round(sum((j['wait'] for j in done)) / ln, 2) if ln else 0, 'att': round(sum((j['tat'] for j in done)) / ln, 2) if ln else 0}
            names = list(results.keys())
            x = range(len(names))
            self.sim_ax.bar([i - 0.2 for i in x], [results[n]['awt'] for n in names], 0.35, label='Avg wait', color=ACCENT)
            self.sim_ax.bar([i + 0.2 for i in x], [results[n]['att'] for n in names], 0.35, label='Avg turnaround', color=GREEN)
            self.sim_ax.set_xticks(list(x))
            self.sim_ax.set_xticklabels(names, color=DIM, fontsize=8)
            self.sim_ax.tick_params(colors=DIM, labelsize=8)
            self.sim_ax.set_title('Algorithm Comparison', color=FG, fontsize=9)
            self.sim_ax.legend(fontsize=8, labelcolor=FG, facecolor=SURFACE)
            for spine in self.sim_ax.spines.values():
                spine.set_edgecolor(DIM)
            self.sim_metrics_var.set('  '.join((f"{n}: awt={results[n]['awt']} att={results[n]['att']}" for n in names)))
            self.sim_canvas.draw()
            return
            
        fn_map = {'FCFS': fcfs, 'SJF': sjf, 'SRTF': srtf, 'Round Robin': round_robin, 'Priority (NP)': priority_np, 'Multilevel Queue': multilevel_queue, 'CFS': cfs, 'Custom Algorithm': custom_scheduler}
        fn = fn_map[algo]
        args = [self.sim_jobs, q] if algo in ('Round Robin', 'Multilevel Queue', 'Custom Algorithm') else [self.sim_jobs]
        try:
            result = fn(*args)
            if algo == 'Custom Algorithm':
                (done, events, quantum_log) = result
            else:
                (done, events) = result
                self._clear_quantum_chart()
        except Exception as e:
            messagebox.showerror('Simulation Error', str(e))
            return
            
        for j in sorted(done, key=lambda x: x['id']):
            tag = 'low' if j['wait'] <= 3 else 'med' if j['wait'] <= 6 else 'high'
            self.sim_res_tree.insert('', 'end', tags=(tag,), values=(j['name'], j['arrival'], j['burst'], j.get('priority', '—'), j['start'], j['end'], j['wait'], j['tat']))
            
        n = len(done)
        awt = round(sum((j['wait'] for j in done)) / n, 2) if n else 0
        att = round(sum((j['tat'] for j in done)) / n, 2) if n else 0
        mkspan = max((j['end'] for j in done)) if done else 0
        cpu_util = round(sum((j['burst'] for j in done)) / mkspan * 100, 1) if mkspan else 0
        self.sim_metrics_var.set(f'Avg wait: {awt}  Avg turnaround: {att}  Makespan: {mkspan}  CPU util: {cpu_util}%')
        if algo == 'Custom Algorithm':
            self._draw_quantum_chart(quantum_log, self.sim_jobs, q, cpu_util)
            
        seen_ids = []
        id_to_row = {}
        for e in events:
            eid = e.get('id', e['name'])
            if eid not in id_to_row:
                id_to_row[eid] = len(seen_ids)
                seen_ids.append(eid)
                
        name_counts = {}
        for e in events:
            name_counts[e['name']] = name_counts.get(e['name'], 0) + 1
        id_to_label = {}
        for e in events:
            eid = e.get('id', e['name'])
            if eid not in id_to_label:
                if name_counts[e['name']] > 1:
                    id_to_label[eid] = f"{e['name']}({eid})"
                else:
                    id_to_label[eid] = e['name']
                    
        for e in events:
            eid = e.get('id', e['name'])
            row = id_to_row[eid]
            self.sim_ax.barh(row, e['end'] - e['start'], left=e['start'], color=GANTT_COLORS[row % len(GANTT_COLORS)], edgecolor=BG, linewidth=0.8)
            mid = e['start'] + (e['end'] - e['start']) / 2
            if e['end'] - e['start'] >= 1:
                self.sim_ax.text(mid, row, str(e['start']), ha='center', va='center', fontsize=6, color=BG)
                
        labels_order = [id_to_label[eid] for eid in seen_ids]
        self.sim_ax.set_yticks(range(len(seen_ids)))
        self.sim_ax.set_yticklabels(labels_order, color=FG, fontsize=8)
        self.sim_ax.tick_params(colors=DIM, labelsize=8)
        self.sim_ax.set_title(f'Gantt Chart — {algo}', color=FG, fontsize=9)
        self.sim_ax.set_xlabel('Time units', color=DIM, fontsize=8)
        for spine in self.sim_ax.spines.values():
            spine.set_edgecolor(DIM)
        self.sim_canvas.draw()

    def _clear_quantum_chart(self):
        for ax in (self.quantum_ax, self.quantum_util_ax):
            ax.clear()
            ax.set_facecolor(SURFACE)
            ax.text(0.5, 0.5, 'Run  Custom Algorithm\nto see quantum dynamics', ha='center', va='center', color=DIM, fontsize=8, transform=ax.transAxes)
            for spine in ax.spines.values():
                spine.set_edgecolor(DIM)
        self.quantum_canvas.draw()

    def _draw_quantum_chart(self, quantum_log, jobs, initial_q, cpu_util):
        job_map = {j['id']: j for j in jobs}
        ax1 = self.quantum_ax
        ax1.clear()
        ax1.set_facecolor(SURFACE)
        proc_ids = list(dict.fromkeys((e['id'] for e in quantum_log)))
        name_counts = {}
        for e in quantum_log:
            name_counts[e['name']] = name_counts.get(e['name'], 0) + 1
            
        for (i, proc_id) in enumerate(proc_ids):
            color = GANTT_COLORS[i % len(GANTT_COLORS)]
            entries = [e for e in quantum_log if e['id'] == proc_id]
            proc_name = entries[0]['name']
            legend_label = f'{proc_name}({proc_id})' if name_counts[proc_name] > 1 else proc_name
            arrival = job_map[proc_id]['arrival'] if proc_id in job_map else 0
            times = [arrival]
            quanta = [initial_q]
            for e in entries:
                times.append(e['time'])
                quanta.append(e['q_after'])
            ax1.step(times, quanta, where='post', color=color, linewidth=1.8, label=legend_label, alpha=0.9)
            inc_t = [e['time'] for e in entries if not e.get('completed')]
            inc_q = [e['q_after'] for e in entries if not e.get('completed')]
            if inc_t:
                ax1.scatter(inc_t, inc_q, color=color, s=28, marker='o', zorder=5)
            for e in entries:
                if e.get('completed'):
                    marker = '^' if e['used_full'] else 'v'
                    ax1.scatter([e['time']], [e['q_after']], color=color, s=60, marker=marker, zorder=6, edgecolors=FG, linewidths=0.6)
                    
        ax1.axhline(y=2, color=GREEN, linewidth=0.8, linestyle='--', alpha=0.7, label='q_min = 2')
        ax1.axhline(y=10, color=RED, linewidth=0.8, linestyle='--', alpha=0.7, label='q_max = 10')
        ax1.set_ylim(0, 12)
        ax1.set_yticks([2, 4, 6, 8, 10])
        ax1.set_title('Dynamic Quantum  (● increase  ▼ finished early = penalised)', color=FG, fontsize=8)
        ax1.set_xlabel('Time', color=DIM, fontsize=8)
        ax1.set_ylabel('Quantum', color=DIM, fontsize=8)
        ax1.tick_params(colors=DIM, labelsize=8)
        for spine in ax1.spines.values():
            spine.set_edgecolor(DIM)
        ax1.legend(fontsize=7, labelcolor=FG, facecolor=SURFACE, edgecolor=DIM, loc='upper left', markerscale=0.8)
        
        ax2 = self.quantum_util_ax
        ax2.clear()
        ax2.set_facecolor(SURFACE)
        makespan = max((e['time'] for e in quantum_log)) if quantum_log else 1
        proc_names = [j['name'] for j in jobs]
        proc_bursts = [j['burst'] for j in jobs]
        shares = [round(b / makespan * 100, 1) for b in proc_bursts]
        colors = [GANTT_COLORS[i % len(GANTT_COLORS)] for i in range(len(jobs))]
        bars = ax2.barh(proc_names, shares, color=colors, height=0.55)
        for (bar, share) in zip(bars, shares):
            ax2.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2, f'{share}%', va='center', color=FG, fontsize=7)
        ax2.set_xlim(0, max(shares) * 1.25 if shares else 100)
        ax2.set_title('Per-Process CPU Share', color=FG, fontsize=9)
        ax2.set_xlabel(f'% of makespan ({makespan} units)  —  sum = {round(sum(shares), 1)}%', color=DIM, fontsize=7)
        ax2.tick_params(colors=DIM, labelsize=8)
        for spine in ax2.spines.values():
            spine.set_edgecolor(DIM)
            
        color_util = GREEN if cpu_util >= 80 else YELLOW if cpu_util >= 50 else RED
        ax2.text(0.98, 0.04, f'Sched. efficiency: {cpu_util}%\n(idle gaps = {round(100 - cpu_util, 1)}%)', transform=ax2.transAxes, ha='right', va='bottom', color=color_util, fontsize=6.5, bbox=dict(boxstyle='round,pad=0.3', facecolor=SURFACE, edgecolor=color_util, alpha=0.8))
        self.quantum_canvas.draw()
        
    def refresh(self):
        pass
