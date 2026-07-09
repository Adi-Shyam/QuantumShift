def custom_scheduler(jobs, quantum=2):
    jobs = sorted(jobs, key=lambda j: j['arrival'])
    n = len(jobs)
    if n == 0:
        return ([], [], [])
    global_q_max = 10
    global_q_min = 2
    processes = []
    for j in jobs:
        processes.append({'name': j['name'], 'id': j['id'], 'arrival': j['arrival'], 'burst': j['burst'], 'remaining_bt': j['burst'], 'current_q': quantum, 'start_time': -1, 'original_job': j})
    ready_queue = []
    current_time = 0
    done = []
    events = []
    quantum_log = []
    arrived = [False] * n
    completed = 0

    def enqueue_arrived(time_limit):
        for i in range(n):
            if not arrived[i] and processes[i]['arrival'] <= time_limit:
                ready_queue.append(processes[i])
                arrived[i] = True
    enqueue_arrived(current_time)
    while completed < n:
        if not ready_queue:
            next_arrival = min((processes[i]['arrival'] for i in range(n) if not arrived[i]))
            current_time = next_arrival
            enqueue_arrived(current_time)
            continue
        p = ready_queue.pop(0)
        if p['start_time'] == -1:
            p['start_time'] = current_time
        q_before = p['current_q']
        time_run = min(p['current_q'], p['remaining_bt'])
        events.append({'name': p['name'], 'id': p['id'], 'start': current_time, 'end': current_time + time_run})
        current_time += time_run
        p['remaining_bt'] -= time_run
        enqueue_arrived(current_time)
        if p['remaining_bt'] > 0:
            used_full = time_run == q_before
            if used_full:
                p['current_q'] = min(global_q_max, p['current_q'] + 2)
            else:
                p['current_q'] = max(global_q_min, p['current_q'] - 2)
            quantum_log.append({'name': p['name'], 'id': p['id'], 'time': current_time, 'q_before': q_before, 'q_after': p['current_q'], 'used_full': used_full})
            ready_queue.append(p)
        else:
            completed += 1
            if time_run < q_before:
                final_q = max(global_q_min, q_before - 2)
            else:
                final_q = q_before
            quantum_log.append({'name': p['name'], 'id': p['id'], 'time': current_time, 'q_before': q_before, 'q_after': final_q, 'used_full': time_run == q_before, 'completed': True})
            j = p['original_job']
            done.append({**j, 'start': p['start_time'], 'end': current_time, 'wait': current_time - j['arrival'] - j['burst'], 'tat': current_time - j['arrival']})
    compact_events = []
    for e in events:
        if compact_events and compact_events[-1]['name'] == e['name'] and (compact_events[-1]['id'] == e['id']) and (compact_events[-1]['end'] == e['start']):
            compact_events[-1]['end'] = e['end']
        else:
            compact_events.append(e)
    return (done, compact_events, quantum_log)