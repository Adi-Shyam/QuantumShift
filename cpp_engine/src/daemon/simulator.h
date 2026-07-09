#ifndef SIMULATOR_H
#define SIMULATOR_H

#include <vector>
#include <string>

struct SimProcess {
    std::string name;
    int arrival_time;
    int burst_time;
    int priority;
    
    // Output stats
    int start_time;
    int completion_time;
    int waiting_time;
    int turnaround_time;
};

struct GanttBlock {
    std::string name;
    int start;
    int duration;
};

class Simulator {
public:
    static void run_fcfs(std::vector<SimProcess>& processes, std::vector<GanttBlock>& gantt);
    static void run_sjf(std::vector<SimProcess>& processes, std::vector<GanttBlock>& gantt);
    static void run_rr(std::vector<SimProcess>& processes, int quantum, std::vector<GanttBlock>& gantt);
    static void run_eqs(std::vector<SimProcess>& processes, int initial_quantum, std::vector<GanttBlock>& gantt);
    
    static void print_gantt_chart(const std::vector<GanttBlock>& gantt, int max_width);
};

#endif
