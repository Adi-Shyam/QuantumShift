#ifndef __EQS_TYPES_H
#define __EQS_TYPES_H

#define MAX_COMM_LEN 16

/* Event type emitted from BPF to User Space */
struct sched_event {
    unsigned long long timestamp;
    unsigned int pid;
    unsigned int cpu_id;
    unsigned int numa_node;
    unsigned int is_migration;
    unsigned long long vruntime;
    char comm[MAX_COMM_LEN];
};

#endif /* __EQS_TYPES_H */
