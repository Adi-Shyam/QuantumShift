#include "simulator.h"
#include <iostream>
#include <algorithm>
#include <queue>
#include <iomanip>

void Simulator::run_fcfs(std::vector<SimProcess>& processes, std::vector<GanttBlock>& gantt) {
    gantt.clear();
    int current_time = 0;
    
    // Sort by arrival time
    std::sort(processes.begin(), processes.end(), [](const SimProcess& a, const SimProcess& b) {
        return a.arrival_time < b.arrival_time;
    });

    for (auto& p : processes) {
        if (current_time < p.arrival_time) {
            current_time = p.arrival_time;
        }
        p.start_time = current_time;
        gantt.push_back({p.name, current_time, p.burst_time});
        current_time += p.burst_time;
        p.completion_time = current_time;
        p.turnaround_time = p.completion_time - p.arrival_time;
        p.waiting_time = p.turnaround_time - p.burst_time;
    }
}

void Simulator::run_sjf(std::vector<SimProcess>& processes, std::vector<GanttBlock>& gantt) {
    gantt.clear();
    // Simplified non-preemptive SJF
    std::vector<SimProcess*> remaining;
    for (auto& p : processes) remaining.push_back(&p);
    
    int current_time = 0;
    while (!remaining.empty()) {
        auto it = std::min_element(remaining.begin(), remaining.end(), 
            [current_time](SimProcess* a, SimProcess* b) {
                if (a->arrival_time <= current_time && b->arrival_time > current_time) return true;
                if (b->arrival_time <= current_time && a->arrival_time > current_time) return false;
                return a->burst_time < b->burst_time;
            });
            
        SimProcess* p = *it;
        if (current_time < p->arrival_time) current_time = p->arrival_time;
        
        p->start_time = current_time;
        gantt.push_back({p->name, current_time, p->burst_time});
        current_time += p->burst_time;
        p->completion_time = current_time;
        p->turnaround_time = p->completion_time - p->arrival_time;
        p->waiting_time = p->turnaround_time - p->burst_time;
        remaining.erase(it);
    }
}

void Simulator::run_rr(std::vector<SimProcess>& processes, int quantum, std::vector<GanttBlock>& gantt) {
    gantt.clear();
    int current_time = 0;
    std::queue<SimProcess*> q;
    std::vector<int> rem_burst(processes.size());
    
    for (size_t i = 0; i < processes.size(); i++) {
        rem_burst[i] = processes[i].burst_time;
        q.push(&processes[i]);
    }
    
    while (!q.empty()) {
        SimProcess* p = q.front();
        q.pop();
        
        size_t idx = p - &processes[0];
        int exec = std::min(quantum, rem_burst[idx]);
        
        gantt.push_back({p->name, current_time, exec});
        current_time += exec;
        rem_burst[idx] -= exec;
        
        if (rem_burst[idx] > 0) {
            q.push(p);
        } else {
            p->completion_time = current_time;
            p->turnaround_time = p->completion_time - p->arrival_time;
            p->waiting_time = p->turnaround_time - p->burst_time;
        }
    }
}

struct EqsProcess {
    SimProcess* proc;
    int remaining;
    int current_q;
};

void Simulator::run_eqs(std::vector<SimProcess>& processes, int initial_quantum, std::vector<GanttBlock>& gantt) {
    gantt.clear();
    int current_time = 0;
    std::queue<EqsProcess> q;
    
    int q_max = 10;
    int q_min = 2;
    
    for (auto& p : processes) {
        q.push({&p, p.burst_time, initial_quantum});
    }
    
    while (!q.empty()) {
        EqsProcess p = q.front();
        q.pop();
        
        int time_run = std::min(p.current_q, p.remaining);
        
        // Compact Gantt
        if (!gantt.empty() && gantt.back().name == p.proc->name && 
            (gantt.back().start + gantt.back().duration) == current_time) {
            gantt.back().duration += time_run;
        } else {
            gantt.push_back({p.proc->name, current_time, time_run});
        }
        
        current_time += time_run;
        p.remaining -= time_run;
        
        if (p.remaining > 0) {
            bool used_full = (time_run == p.current_q);
            if (used_full) {
                p.current_q = std::min(q_max, p.current_q + 2);
            } else {
                p.current_q = std::max(q_min, p.current_q - 2);
            }
            q.push(p);
        } else {
            p.proc->completion_time = current_time;
            p.proc->turnaround_time = current_time - p.proc->arrival_time;
            p.proc->waiting_time = p.proc->turnaround_time - p.proc->burst_time;
        }
    }
}

void Simulator::print_gantt_chart(const std::vector<GanttBlock>& gantt, int max_width) {
    if (gantt.empty()) return;
    int total_time = gantt.back().start + gantt.back().duration;
    if (total_time == 0) return;
    
    std::string colors[] = {"\033[44m", "\033[42m", "\033[43m", "\033[41m", "\033[45m", "\033[46m"};
    int c_idx = 0;
    
    std::cout << "\n  Gantt Chart (Total Time: " << total_time << "):\n  ";
    for (const auto& b : gantt) {
        int width = (b.duration * max_width) / total_time;
        if (width < 3) width = 3; // min width
        std::cout << colors[c_idx % 6];
        std::cout << "[" << b.name;
        for (int i = 0; i < width - 2 - (int)b.name.length(); i++) std::cout << " ";
        std::cout << "]\033[0m";
        c_idx++;
    }
    std::cout << "\n\n";
}
