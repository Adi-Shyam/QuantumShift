# QuantumShift (EQS)

This project is a hybrid C++ eBPF and Python application that introduces the **Elastic Quantum Scheduler (EQS)** into the Linux Kernel via the `sched_ext` (SCX) framework. 

It provides both a real-time kernel-level scheduling agent and a Python-based Tkinter GUI for advanced telemetry, monitoring, algorithm simulation, and dynamic process control.

## Architecture

* **Backend (`cpp_engine/`)**: A high-performance C++ eBPF daemon. It hooks into the Linux `sched_ext` framework to implement EQS directly in the kernel. It tracks context switches, process migrations, and memory usage with zero-overhead using eBPF ring buffers, and dynamically adapts process quantums based on CPU/IO behavior.
* **Frontend (`python_engine/`)**: A Tkinter-based Python GUI that visualizes real-time metrics (Gantt charts, multi-core utilization, fairness metrics) and allows you to explicitly switch standard CFS processes into the custom EQS policy on the fly using `pkexec`.

## Requirements

* **OS:** Linux (Kernel 6.12+ with `CONFIG_SCHED_CLASS_EXT=y` enabled)
* **Dependencies (Backend):** `clang`, `g++`, `libbpf-dev`, `linux-tools-common` (for `bpftool`), `libelf-dev`, `zlib1g-dev`
* **Dependencies (Frontend):** Python 3.10+, `psutil`, `matplotlib`

## Build Instructions

1. **Build the Backend:**
   ```bash
   cd cpp_engine
   make
   ```
2. **Install Python Dependencies:**
   ```bash
   pip install psutil matplotlib
   ```

## Running the Application

To start the platform, run the Python UI. The UI will automatically attempt to launch the C++ backend daemon using `pkexec` (it will prompt for your root password).

```bash
cd python_engine
python3 main.py
```

## Features

* **Targeted Optimization**: Using the `SCX_OPS_SWITCH_PARTIAL` flag, EQS acts as a safe, targeted performance tuner. It only manages processes that you explicitly assign to it via the UI, leaving the rest of your OS safely on the default CFS scheduler.
* **Algorithm Simulator**: Includes a fully-featured visual simulator comparing standard algorithms (FCFS, SJF, RR, MLQ) against the custom EQS logic.

## Quantifiable Advantages of EQS

When compared to standard schedulers like CFS, the Elastic Quantum Scheduler is designed to provide measurable improvements in specific scenarios:

1. **Context Switch Reduction:** By dynamically scaling the timeslice up to 20ms for CPU-bound tasks, EQS heavily reduces the number of involuntary context switches. This drastically lowers kernel overhead and improves raw CPU throughput (Makespan) for heavy computational workloads (like rendering or compiling).
2. **I/O Bound Penalty:** Tasks that yield early (I/O bound) have their maximum quantum shrunk down to 2ms. This creates a quantifiable reduction in "rogue latency"—if an interactive process suddenly becomes CPU-intensive, it is strictly capped at 2ms slices, guaranteeing it cannot instantly starve the rest of the queue.
3. **Measurable Efficiency in Simulator:** You can use the built-in "Algorithm Simulator" tab to benchmark EQS against CFS, quantifying exact improvements in Average Wait Time (AWT), Turnaround Time (ATT), and overall CPU Utilization percentages across mock workloads.

## Additional Improvements

- Updated the repository for structural integrity tracking.
- Minor enhancements for documentation clarity.
