#include "vmlinux.h"
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_tracing.h>
#include "eqs_types.h"

char LICENSE[] SEC("license") = "Dual BSD/GPL";

#define MIN_QUANTUM_NS (2 * 1000000ULL)
#define MAX_QUANTUM_NS (20 * 1000000ULL)
#define QUANTUM_STEP_NS (2 * 1000000ULL)
#define DEFAULT_QUANTUM_NS (4 * 1000000ULL)

#define SCX_DSQ_GLOBAL 0ULL

struct eqs_task_state {
    u64 current_quantum_ns;
};

/* Task local storage to hold the process's current quantum */
struct {
    __uint(type, BPF_MAP_TYPE_TASK_STORAGE);
    __uint(map_flags, BPF_F_NO_PREALLOC);
    __type(key, int);
    __type(value, struct eqs_task_state);
} eqs_state_map SEC(".maps");

/* Ringbuffer to send events to user-space */
struct {
    __uint(type, BPF_MAP_TYPE_RINGBUF);
    __uint(max_entries, 256 * 1024);
} rb SEC(".maps");

/* Map to keep track of a task's previous NUMA node to detect migrations */
struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 10240);
    __type(key, u32);   /* PID */
    __type(value, u32); /* NUMA Node */
} prev_numa_map SEC(".maps");

/* Declare sched_ext kfuncs */
extern void scx_bpf_dispatch(struct task_struct *p, u64 dsq_id, u64 slice, u64 enq_flags) __ksym;

/* 
 * EQS Enqueue: Assign the calculated timeslice to the task and dispatch it.
 */
SEC("struct_ops/eqs_enqueue")
void BPF_PROG(eqs_enqueue, struct task_struct *p, u64 enq_flags)
{
    struct eqs_task_state *state;
    u64 slice = DEFAULT_QUANTUM_NS;

    state = bpf_task_storage_get(&eqs_state_map, p, 0,
                                 BPF_LOCAL_STORAGE_GET_F_CREATE);
    if (state) {
        if (state->current_quantum_ns == 0) {
            state->current_quantum_ns = DEFAULT_QUANTUM_NS;
        }
        slice = state->current_quantum_ns;
    }

    scx_bpf_dispatch(p, SCX_DSQ_GLOBAL, slice, enq_flags);
}

/*
 * EQS Stopping: Adjust the timeslice dynamically based on the task's execution.
 * If slice == 0, it used its full quantum (CPU bound) -> Increase quantum
 * If slice > 0, it yielded early (I/O bound) -> Decrease quantum
 */
SEC("struct_ops/eqs_stopping")
void BPF_PROG(eqs_stopping, struct task_struct *p, bool runnable)
{
    struct eqs_task_state *state;
    state = bpf_task_storage_get(&eqs_state_map, p, 0, 0);
    if (state) {
        if (p->scx.slice == 0) {
            /* Task exhausted its slice (CPU bound) */
            if (state->current_quantum_ns < MAX_QUANTUM_NS) {
                state->current_quantum_ns += QUANTUM_STEP_NS;
                if (state->current_quantum_ns > MAX_QUANTUM_NS)
                    state->current_quantum_ns = MAX_QUANTUM_NS;
            }
        } else {
            /* Task yielded before exhausting slice (I/O bound) */
            if (state->current_quantum_ns > MIN_QUANTUM_NS) {
                if (state->current_quantum_ns > QUANTUM_STEP_NS)
                    state->current_quantum_ns -= QUANTUM_STEP_NS;
                if (state->current_quantum_ns < MIN_QUANTUM_NS)
                    state->current_quantum_ns = MIN_QUANTUM_NS;
            }
        }
    }
}

/* Keep existing tracepoint for telemetry pipeline */
SEC("tp_btf/sched_switch")
int BPF_PROG(handle_sched_switch, bool preempt, struct task_struct *prev, struct task_struct *next)
{
    struct sched_event *e;
    u32 pid = next->tgid;
    u32 cpu = bpf_get_smp_processor_id();
    u32 numa_node = bpf_get_numa_node_id();
    u32 is_migration = 0;
    
    u32 *prev_node = bpf_map_lookup_elem(&prev_numa_map, &pid);
    if (prev_node) {
        if (*prev_node != numa_node) {
            is_migration = 1;
        }
    }
    bpf_map_update_elem(&prev_numa_map, &pid, &numa_node, BPF_ANY);

    e = bpf_ringbuf_reserve(&rb, sizeof(*e), 0);
    if (!e)
        return 0;

    e->timestamp = bpf_ktime_get_ns();
    e->pid = pid;
    e->cpu_id = cpu;
    e->numa_node = numa_node;
    e->is_migration = is_migration;
    e->vruntime = next->se.vruntime;
    bpf_probe_read_kernel_str(&e->comm, sizeof(e->comm), next->comm);

    bpf_ringbuf_submit(e, 0);
    return 0;
}

/* Bind hooks to the sched_ext ops struct */
SEC(".struct_ops")
struct sched_ext_ops eqs_ops = {
    .enqueue = (void *)eqs_enqueue,
    .stopping = (void *)eqs_stopping,
    .flags = SCX_OPS_SWITCH_PARTIAL | SCX_OPS_ENQ_LAST,
    .name = "eqs",
};
