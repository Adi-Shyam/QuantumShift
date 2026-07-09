#include <iostream>
#include <map>
#include <string>
#include <csignal>
#include <chrono>
#include <unistd.h>
#include <bpf/libbpf.h>
#include "eqs.skel.h"
#include "eqs_types.h"

volatile bool exiting = false;

void sig_handler(int sig) {
    exiting = true;
}

struct TaskInfo {
    std::string comm;
    unsigned int cpu;
    unsigned int numa;
    unsigned long long vruntime;
    unsigned int migrations;
    unsigned long mem_kb;
};

unsigned long get_mem_kb(int pid) {
    char path[256];
    snprintf(path, sizeof(path), "/proc/%d/statm", pid);
    FILE *f = fopen(path, "r");
    if (!f) return 0;
    unsigned long size, resident, share, text, lib, data, dt;
    if (fscanf(f, "%lu %lu %lu %lu %lu %lu %lu", &size, &resident, &share, &text, &lib, &data, &dt) != 7) {
        fclose(f);
        return 0;
    }
    fclose(f);
    return resident * (sysconf(_SC_PAGESIZE) / 1024);
}

std::map<unsigned int, TaskInfo> task_stats;

int handle_event(void *ctx, void *data, size_t data_sz) {
    const struct sched_event *e = static_cast<const struct sched_event *>(data);
    
    auto& info = task_stats[e->pid];
    info.comm = e->comm;
    info.cpu = e->cpu_id;
    info.numa = e->numa_node;
    info.vruntime = e->vruntime;
    if (e->is_migration) {
        info.migrations++;
    }
    return 0;
}

void render_json() {
    std::cout << "[";
    bool first = true;
    for (auto it = task_stats.rbegin(); it != task_stats.rend(); ++it) {
        if (it->second.comm.empty()) continue;
        
        // Fetch accurate memory just before rendering
        it->second.mem_kb = get_mem_kb(it->first);
        
        if (!first) std::cout << ",";
        first = false;
        
        std::cout << "{"
                  << "\"pid\":" << it->first << ","
                  << "\"comm\":\"" << it->second.comm << "\","
                  << "\"cpu\":" << it->second.cpu << ","
                  << "\"numa\":" << it->second.numa << ","
                  << "\"vruntime\":" << it->second.vruntime << ","
                  << "\"migrations\":" << it->second.migrations << ","
                  << "\"mem_kb\":" << it->second.mem_kb
                  << "}";
    }
    std::cout << "]\n";
    std::cout.flush();
}

int main(int argc, char **argv) {
    struct eqs_bpf *skel;
    struct ring_buffer *rb = NULL;
    int err;

    signal(SIGINT, sig_handler);
    signal(SIGTERM, sig_handler);

    skel = eqs_bpf__open_and_load();
    if (!skel) {
        std::cerr << "{\"error\": \"Failed to open and load BPF skeleton\"}\n";
        return 1;
    }

    err = eqs_bpf__attach(skel);
    if (err) {
        std::cerr << "{\"error\": \"Failed to attach BPF skeleton\"}\n";
        eqs_bpf__destroy(skel);
        return 1;
    }

    struct bpf_link *ops_link = bpf_map__attach_struct_ops(skel->maps.eqs_ops);
    if (!ops_link) {
        std::cerr << "{\"error\": \"Failed to attach sched_ext ops\"}\n";
        eqs_bpf__destroy(skel);
        return 1;
    }

    rb = ring_buffer__new(bpf_map__fd(skel->maps.rb), handle_event, NULL, NULL);
    if (!rb) {
        std::cerr << "{\"error\": \"Failed to create ring buffer\"}\n";
        bpf_link__destroy(ops_link);
        eqs_bpf__destroy(skel);
        return 1;
    }
    
    auto last_render = std::chrono::steady_clock::now();

    // Clear stats periodically to remove dead processes
    auto last_clear = std::chrono::steady_clock::now();

    while (!exiting) {
        err = ring_buffer__poll(rb, 100 /* timeout, ms */);
        if (err == -EINTR) {
            err = 0;
            break;
        }
        
        auto now = std::chrono::steady_clock::now();
        if (std::chrono::duration_cast<std::chrono::milliseconds>(now - last_render).count() > 1000) {
            render_json();
            last_render = now;
        }
        
        if (std::chrono::duration_cast<std::chrono::milliseconds>(now - last_clear).count() > 5000) {
            // Keep map size bounded
            if (task_stats.size() > 500) {
                task_stats.clear();
            }
            last_clear = now;
        }
    }

    ring_buffer__free(rb);
    if (ops_link) bpf_link__destroy(ops_link);
    eqs_bpf__destroy(skel);
    return 0;
}
