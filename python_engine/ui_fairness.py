import tkinter as tk
from tkinter import ttk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from process_data import jains_fairness, cpu_variance
from ui_constants import *

class FairnessTab(ttk.Frame):
    _FP_PALETTE = ['#89b4fa', '#a6e3a1', '#f9e2af', '#f38ba8', '#cba6f7', '#94e2d5', '#fab387', '#89dceb']

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._build_fairness()

    def _build_fairness(self):
        parent = self
        top_row = ttk.Frame(parent)
        top_row.pack(fill='x', padx=10, pady=10)
        self.fair_cards = {}
        for (key, title) in [('ji', "Jain's Fairness Index"), ('var', 'CPU Variance'), ('starve', 'Starving Processes'), ('max', 'Max CPU%')]:
            card = ttk.Frame(top_row)
            card.pack(side='left', padx=6)
            ttk.Label(card, text=title, style='Dim.TLabel').pack(anchor='w')
            val_lbl = ttk.Label(card, text='—', font=('Courier New', 20, 'bold'), background=BG, foreground=FG)
            val_lbl.pack(anchor='w')
            self.fair_cards[key] = val_lbl
            
        pol_frame = ttk.Frame(parent)
        pol_frame.pack(fill='x', padx=10, pady=4)
        ttk.Label(pol_frame, text='Fairness by policy', style='Header.TLabel').pack(anchor='w')
        self.pol_canvas = tk.Canvas(pol_frame, height=80, bg=BG, highlightthickness=0)
        self.pol_canvas.pack(fill='x', padx=2, pady=4)
        
        fp_ctrl = ttk.Frame(parent)
        fp_ctrl.pack(fill='x', padx=10, pady=(2, 0))
        ttk.Label(fp_ctrl, text='Scheduling Fingerprinting', style='Header.TLabel').pack(side='left')
        ttk.Label(fp_ctrl, text=' | k-means clusters:', style='Dim.TLabel').pack(side='left')
        self.fp_k = tk.IntVar(value=4)
        ttk.Spinbox(fp_ctrl, from_=2, to=8, textvariable=self.fp_k, width=3, font=('Courier New', 9)).pack(side='left', padx=4)
        self.fp_algo = ttk.Combobox(fp_ctrl, values=['k-means', 'DBSCAN'], state='readonly', width=8, font=('Courier New', 9))
        self.fp_algo.set('k-means')
        self.fp_algo.pack(side='left', padx=4)
        self.fp_label_var = tk.StringVar(value='')
        ttk.Label(fp_ctrl, textvariable=self.fp_label_var, foreground=DIM, background=BG, font=('Courier New', 8)).pack(side='left', padx=8)
        
        fp_row = ttk.Frame(parent)
        fp_row.pack(fill='both', expand=True, padx=8, pady=4)
        self.fair_fig = Figure(figsize=(10, 3.8), facecolor=BG)
        self.fair_fig.subplots_adjust(wspace=0.38, left=0.06, right=0.97, top=0.88, bottom=0.18)
        self.fair_ax1 = self.fair_fig.add_subplot(1, 3, 1)
        self.fair_ax2 = self.fair_fig.add_subplot(1, 3, 2)
        self.fp_ax = self.fair_fig.add_subplot(1, 3, 3)
        for ax in [self.fair_ax1, self.fair_ax2, self.fp_ax]:
            ax.set_facecolor(SURFACE)
        self.fair_canvas = FigureCanvasTkAgg(self.fair_fig, master=fp_row)
        self.fair_canvas.get_tk_widget().pack(fill='both', expand=True)
        
        self.starve_var = tk.StringVar(value='')
        ttk.Label(parent, textvariable=self.starve_var, foreground=RED, background=BG, font=('Courier New', 9)).pack(anchor='w', padx=10, pady=2)

    def refresh(self):
        cpu_vals = [p['cpu'] for p in self.app.processes]
        ji = jains_fairness(cpu_vals)
        var = cpu_variance(cpu_vals)
        starving = [p for p in self.app.processes if p['cpu'] < 0.8 and p['state'] == 'S']
        max_cpu = max(cpu_vals) if cpu_vals else 0
        max_name = next((p['name'] for p in self.app.processes if p['cpu'] == max_cpu), '')
        
        self.fair_cards['ji'].config(text=str(ji), foreground=GREEN if ji > 0.85 else YELLOW if ji > 0.7 else RED)
        self.fair_cards['var'].config(text=str(var), foreground=GREEN if var < 40 else YELLOW if var < 80 else RED)
        self.fair_cards['starve'].config(text=str(len(starving)), foreground=RED if starving else GREEN)
        self.fair_cards['max'].config(text=f'{max_cpu:.1f}%\n{max_name}', foreground=FG)
        
        pol_groups = {}
        for p in self.app.processes:
            pol_groups.setdefault(p['policy'], []).append(p['cpu'])
            
        self.pol_canvas.delete('all')
        w = self.pol_canvas.winfo_width() or 500
        for (row, (pol, cpus)) in enumerate(pol_groups.items()):
            pji = jains_fairness(cpus)
            color = POLICY_COLOR.get(pol, DIM)
            y = 10 + row * 22
            self.pol_canvas.create_text(5, y + 7, text=f'{pol:<6}', anchor='w', fill=color, font=('Courier New', 9))
            self.pol_canvas.create_rectangle(60, y, 60 + w - 140, y + 14, fill=SURFACE, outline='')
            self.pol_canvas.create_rectangle(60, y, 60 + int(pji * (w - 140)), y + 14, fill=color, outline='')
            self.pol_canvas.create_text(w - 75, y + 7, text=f'{pji:.3f}', anchor='w', fill=DIM, font=('Courier New', 9))
            
        ax1 = self.fair_ax1
        ax1.clear()
        ax1.set_facecolor(SURFACE)
        buckets = list(range(0, 105, 10))
        counts = [sum((1 for v in cpu_vals if b <= v < b + 10)) for b in buckets]
        ax1.bar([f'{b}' for b in buckets], counts, color=MAUVE)
        ax1.set_title('CPU % distribution', color=FG, fontsize=9)
        ax1.tick_params(colors=DIM, labelsize=7, rotation=35)
        for spine in ax1.spines.values():
            spine.set_edgecolor(DIM)
            
        ax2 = self.fair_ax2
        ax2.clear()
        ax2.set_facecolor(SURFACE)
        pol_names = list(pol_groups.keys())
        ax2.barh(pol_names, [jains_fairness(pol_groups[p]) for p in pol_names], color=[POLICY_COLOR.get(p, DIM) for p in pol_names])
        ax2.set_xlim(0, 1)
        ax2.axvline(1.0, color=DIM, linewidth=0.8, linestyle='--')
        ax2.set_title("Jain's index by policy", color=FG, fontsize=9)
        ax2.tick_params(colors=DIM, labelsize=8)
        for spine in ax2.spines.values():
            spine.set_edgecolor(DIM)
            
        self._refresh_fingerprint()
        self.fair_canvas.draw()
        self.starve_var.set('Starvation: ' + '  '.join((f"PID {p['pid']} [{p['name']}] cpu={p['cpu']:.1f}%" for p in starving[:4])) if starving else '')

    def _fingerprint_label(self, centroid):
        (cpu, vcs, nvcs, vrt) = centroid
        if cpu > 0.55:
            return 'CPU-bound'
        if vcs > 0.55:
            return 'I/O-bound' if cpu < 0.25 else 'Interactive'
        if cpu < 0.15 and vcs < 0.2:
            return 'Idle/BG'
        if nvcs > 0.5:
            return 'Preempted'
        return 'Mixed'

    def _refresh_fingerprint(self):
        import numpy as np
        ax = self.fp_ax
        ax.clear()
        ax.set_facecolor(SURFACE)
        ax.set_title('Scheduling Fingerprint  (PCA)', color=FG, fontsize=9)
        procs = self.app.processes
        if len(procs) < 4:
            ax.text(0.5, 0.5, 'Need ≥4 processes', ha='center', va='center', color=DIM, fontsize=9, transform=ax.transAxes)
            self.fp_label_var.set('')
            return
            
        X_raw = np.array([[p['cpu'], p['vcs'], p['nvcs'], p['vrt'] / 1000000] for p in procs], dtype=float)
        col_max = X_raw.max(axis=0)
        col_max[col_max == 0] = 1.0
        X = X_raw / col_max
        algo = self.fp_algo.get()
        labels = None
        n_clusters = 0
        if algo == 'k-means':
            from sklearn.cluster import KMeans
            k = max(2, min(self.fp_k.get(), len(procs) - 1))
            try:
                km = KMeans(n_clusters=k, n_init=10, random_state=42)
                labels = km.fit_predict(X)
                centroids_norm = km.cluster_centers_
                n_clusters = k
                cluster_names = [self._fingerprint_label(c) for c in centroids_norm]
            except Exception as e:
                ax.text(0.5, 0.5, f'k-means failed:\n{e}', ha='center', va='center', color=RED, fontsize=8, transform=ax.transAxes)
                return
        else:
            from sklearn.cluster import DBSCAN
            try:
                db = DBSCAN(eps=0.35, min_samples=2)
                labels = db.fit_predict(X)
                unique = sorted(set(labels))
                n_clusters = sum((1 for l in unique if l >= 0))
                cluster_names = []
                for cl in unique:
                    if cl < 0:
                        cluster_names.append('Noise')
                    else:
                        mask = labels == cl
                        c = X[mask].mean(axis=0)
                        cluster_names.append(self._fingerprint_label(c))
            except Exception as e:
                ax.text(0.5, 0.5, f'DBSCAN failed:\n{e}', ha='center', va='center', color=RED, fontsize=8, transform=ax.transAxes)
                return
                
        from sklearn.decomposition import PCA
        pca = PCA(n_components=2)
        try:
            X2 = pca.fit_transform(X)
        except Exception:
            ax.text(0.5, 0.5, 'PCA failed', ha='center', va='center', color=RED, fontsize=8, transform=ax.transAxes)
            return
            
        unique_labels = sorted(set(labels))
        if algo == 'k-means':
            cl_name_map = {cl: cluster_names[i] for (i, cl) in enumerate(unique_labels)}
        else:
            dbscan_unique = sorted(set(labels))
            cl_name_map = {cl: cluster_names[i] for (i, cl) in enumerate(dbscan_unique)}
            
        for (i, cl) in enumerate(unique_labels):
            mask = labels == cl
            color = self._FP_PALETTE[i % len(self._FP_PALETTE)] if cl >= 0 else DIM
            beh = cl_name_map.get(cl, f'C{cl}')
            label_txt = beh if cl >= 0 else 'Noise'
            ax.scatter(X2[mask, 0], X2[mask, 1], c=color, s=32, alpha=0.85, edgecolors='none', label=label_txt)
            
        for cl in unique_labels:
            if cl < 0:
                continue
            cl_procs = [procs[j] for j in range(len(procs)) if labels[j] == cl]
            if not cl_procs:
                continue
            top = max(cl_procs, key=lambda p: p['cpu'])
            idx = procs.index(top)
            ax.annotate(top['name'][:7], (X2[idx, 0], X2[idx, 1]), fontsize=6, color=FG, alpha=0.75, xytext=(3, 3), textcoords='offset points')
            
        var_exp = pca.explained_variance_ratio_
        ax.set_xlabel(f'PC1 ({var_exp[0] * 100:.0f}%)', color=DIM, fontsize=7)
        ax.set_ylabel(f'PC2 ({var_exp[1] * 100:.0f}%)', color=DIM, fontsize=7)
        ax.tick_params(colors=DIM, labelsize=7)
        for spine in ax.spines.values():
            spine.set_edgecolor(DIM)
        leg = ax.legend(fontsize=6, labelcolor=FG, facecolor=SURFACE, edgecolor=DIM, loc='upper right', markerscale=0.8, framealpha=0.7)
        cluster_word = 'cluster' if n_clusters == 1 else 'clusters'
        self.fp_label_var.set(f'{algo}  →  {n_clusters} {cluster_word}  |  PC1+PC2 explain {sum(var_exp) * 100:.0f}% of variance')
