def fcfs(jobs):
    jobs = sorted(jobs, key=lambda j: j['arrival'])
    (time_now, done, events) = (0, [], [])
    for j in jobs:
        start = max(time_now, j['arrival'])
        end = start + j['burst']
        done.append({**j, 'start': start, 'end': end, 'wait': start - j['arrival'], 'tat': end - j['arrival']})
        events.append({'name': j['name'], 'start': start, 'end': end})
        time_now = end
    return (done, events)

def sjf(jobs):
    jobs = sorted(jobs, key=lambda j: j['arrival'])
    (time_now, done, events, remaining) = (0, [], [], list(jobs))
    while remaining:
        available = [j for j in remaining if j['arrival'] <= time_now]
        if not available:
            time_now = remaining[0]['arrival']
            continue
        j = min(available, key=lambda x: x['burst'])
        remaining.remove(j)
        start = time_now
        end = start + j['burst']
        done.append({**j, 'start': start, 'end': end, 'wait': start - j['arrival'], 'tat': end - j['arrival']})
        events.append({'name': j['name'], 'start': start, 'end': end})
        time_now = end
    return (done, events)

def srtf(jobs):
    jobs = sorted(jobs, key=lambda j: j['arrival'])
    remaining = {j['id']: j['burst'] for j in jobs}
    start_t = {}
    time_now = 0
    done = []
    events = []
    finished = set()
    max_t = sum((j['burst'] for j in jobs)) + max((j['arrival'] for j in jobs)) + 1
    last_pid = None
    seg_start = 0
    for t in range(max_t):
        available = [j for j in jobs if j['arrival'] <= t and j['id'] not in finished]
        if not available:
            if len(finished) == len(jobs):
                break
            continue
        cur = min(available, key=lambda j: remaining[j['id']])
        if cur['id'] not in start_t:
            start_t[cur['id']] = t
        if last_pid is not None and last_pid != cur['id']:
            prev = next((j for j in jobs if j['id'] == last_pid))
            events.append({'name': prev['name'], 'start': seg_start, 'end': t})
            seg_start = t
        if last_pid != cur['id']:
            seg_start = t
        last_pid = cur['id']
        remaining[cur['id']] -= 1
        if remaining[cur['id']] == 0:
            events.append({'name': cur['name'], 'start': seg_start, 'end': t + 1})
            seg_start = t + 1
            last_pid = None
            finished.add(cur['id'])
            end = t + 1
            done.append({**cur, 'start': start_t[cur['id']], 'end': end, 'wait': end - cur['arrival'] - cur['burst'], 'tat': end - cur['arrival']})
    return (done, events)

def priority_np(jobs):
    jobs = sorted(jobs, key=lambda j: j['arrival'])
    (time_now, done, events, remaining) = (0, [], [], list(jobs))
    while remaining:
        available = [j for j in remaining if j['arrival'] <= time_now]
        if not available:
            time_now = remaining[0]['arrival']
            continue
        j = min(available, key=lambda x: x.get('priority', x['arrival']))
        remaining.remove(j)
        start = time_now
        end = start + j['burst']
        done.append({**j, 'start': start, 'end': end, 'wait': start - j['arrival'], 'tat': end - j['arrival']})
        events.append({'name': j['name'], 'start': start, 'end': end})
        time_now = end
    return (done, events)

def round_robin(jobs, quantum=2):
    jobs = sorted(jobs, key=lambda j: j['arrival'])
    queue = []
    time_now = 0
    remaining = {j['id']: j['burst'] for j in jobs}
    start_t = {}
    done = []
    events = []
    arrived = set()
    job_map = {j['id']: j for j in jobs}
    pending = list(jobs)
    while pending or queue:
        new = [j for j in pending if j['arrival'] <= time_now]
        for j in new:
            if j['id'] not in arrived:
                queue.append(j)
                arrived.add(j['id'])
        pending = [j for j in pending if j['id'] not in arrived]
        if not queue:
            if pending:
                time_now = pending[0]['arrival']
            continue
        j = queue.pop(0)
        if j['id'] not in start_t:
            start_t[j['id']] = time_now
        run = min(quantum, remaining[j['id']])
        events.append({'name': j['name'], 'start': time_now, 'end': time_now + run})
        time_now += run
        remaining[j['id']] -= run
        new = [p for p in pending if p['arrival'] <= time_now and p['id'] not in arrived]
        for p in new:
            queue.append(p)
            arrived.add(p['id'])
        pending = [p for p in pending if p['id'] not in arrived]
        if remaining[j['id']] == 0:
            end = time_now
            done.append({**j, 'start': start_t[j['id']], 'end': end, 'wait': end - j['arrival'] - j['burst'], 'tat': end - j['arrival']})
        else:
            queue.append(j)
    return (done, events)

def multilevel_queue(jobs, quantum=2):
    high = [j for j in jobs if j['burst'] <= 3]
    low = [j for j in jobs if j['burst'] > 3]
    (done_h, ev_h) = round_robin(high, quantum) if high else ([], [])
    offset = max((e['end'] for e in ev_h), default=0)
    low_shifted = [{**j, 'arrival': max(j['arrival'], offset)} for j in low]
    (done_l, ev_l) = fcfs(low_shifted) if low else ([], [])
    return (done_h + done_l, ev_h + ev_l)

def cfs(jobs):
    jobs = sorted(jobs, key=lambda j: j['arrival'])
    queue = []
    time_now = 0
    remaining = {j['id']: j['burst'] for j in jobs}
    vruntime = {j['id']: 0 for j in jobs}
    start_t = {}
    done = []
    events = []
    arrived = set()
    pending = list(jobs)
    while pending or queue:
        new = [j for j in pending if j['arrival'] <= time_now]
        for j in new:
            if j['id'] not in arrived:
                queue.append(j)
                arrived.add(j['id'])
        pending = [j for j in pending if j['id'] not in arrived]
        if not queue:
            if pending:
                time_now = pending[0]['arrival']
            continue
        queue.sort(key=lambda x: (vruntime[x['id']], x['arrival']))
        j = queue.pop(0)
        if j['id'] not in start_t:
            start_t[j['id']] = time_now
        run = 1
        events.append({'name': j['name'], 'start': time_now, 'end': time_now + run})
        time_now += run
        remaining[j['id']] -= run
        vruntime[j['id']] += run
        new = [p for p in pending if p['arrival'] <= time_now and p['id'] not in arrived]
        for p in new:
            queue.append(p)
            arrived.add(p['id'])
        pending = [p for p in pending if p['id'] not in arrived]
        if remaining[j['id']] == 0:
            end = time_now
            done.append({**j, 'start': start_t[j['id']], 'end': end, 'wait': end - j['arrival'] - j['burst'], 'tat': end - j['arrival']})
        else:
            queue.append(j)
    compact_events = []
    for e in events:
        if compact_events and compact_events[-1]['name'] == e['name'] and (compact_events[-1]['end'] == e['start']):
            compact_events[-1]['end'] = e['end']
        else:
            compact_events.append(e)
    return (done, compact_events)

def compare_all(jobs, quantum=2):
    results = {}
    for (name, fn, args) in [('FCFS', fcfs, [jobs]), ('SJF', sjf, [jobs]), ('SRTF', srtf, [jobs]), ('RR', round_robin, [jobs, quantum]), ('Priority', priority_np, [jobs]), ('MLQ', multilevel_queue, [jobs, quantum]), ('CFS', cfs, [jobs])]:
        try:
            (done, _) = fn(*args)
            n = len(done)
            awt = round(sum((j['wait'] for j in done)) / n, 2) if n else 0
            att = round(sum((j['tat'] for j in done)) / n, 2) if n else 0
            results[name] = {'awt': awt, 'att': att}
        except Exception:
            results[name] = {'awt': 0, 'att': 0}
    return results