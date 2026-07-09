import os
import ctypes
import random
import subprocess
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
SCHED_OTHER = 0
SCHED_FIFO = 1
SCHED_RR = 2
SCHED_BATCH = 3
SCHED_IDLE = 5
SCHED_EXT = 7
POLICY_INT = {'CFS': SCHED_OTHER, 'FIFO': SCHED_FIFO, 'RR': SCHED_RR, 'BATCH': SCHED_BATCH, 'IDLE': SCHED_IDLE, 'EXT': SCHED_EXT}
POLICY_STR = {v: k for (k, v) in POLICY_INT.items()}

class SchedParam(ctypes.Structure):
    _fields_ = [('sched_priority', ctypes.c_int)]
try:
    _libc = ctypes.CDLL('libc.so.6', use_errno=True)
    LIBC_AVAILABLE = True
except OSError:
    LIBC_AVAILABLE = False

def set_scheduler(pid, policy_str, priority=0):
    if not LIBC_AVAILABLE:
        raise OSError('libc.so.6 not available (Linux only)')
    policy_int = POLICY_INT.get(policy_str, SCHED_OTHER)
    param = SchedParam(priority)
    ret = _libc.sched_setscheduler(pid, policy_int, ctypes.byref(param))
    if ret != 0:
        errno = ctypes.get_errno()
        if errno == 1:
            if policy_str == 'EXT':
                script = f"import ctypes; ctypes.CDLL('libc.so.6').sched_setscheduler({pid}, 7, ctypes.byref(type('SchedParam', (ctypes.Structure,), {{'_fields_': [('sched_priority', ctypes.c_int)]}})(0)))"
                try:
                    subprocess.run(['pkexec', 'python3', '-c', script], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                except subprocess.CalledProcessError:
                    raise PermissionError('Permission denied — pkexec failed or was cancelled.')
                except FileNotFoundError:
                    raise PermissionError('Permission denied — run as root (pkexec not found).')
            else:
                chrt_policy = {'FIFO': '-f', 'RR': '-r', 'BATCH': '-b', 'IDLE': '-i', 'CFS': '-o'}.get(policy_str, '-o')
                try:
                    subprocess.run(['pkexec', 'chrt', '--pid', chrt_policy, str(priority), str(pid)], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                except subprocess.CalledProcessError:
                    raise PermissionError('Permission denied — pkexec failed or was cancelled.')
                except FileNotFoundError:
                    raise PermissionError('Permission denied — run as root (pkexec not found).')
        else:
            raise OSError(f'sched_setscheduler failed: errno={errno}')

def get_scheduler(pid):
    if not LIBC_AVAILABLE:
        return 'CFS'
    ret = _libc.sched_getscheduler(pid)
    return POLICY_STR.get(ret, 'CFS')
_PROC_SCHED_AVAILABLE = None

def _check_proc_sched_available():
    global _PROC_SCHED_AVAILABLE
    if _PROC_SCHED_AVAILABLE is not None:
        return _PROC_SCHED_AVAILABLE
    try:
        pid = os.getpid()
        path = f'/proc/{pid}/sched'
        with open(path, 'r') as f:
            content = f.read()
        _PROC_SCHED_AVAILABLE = 'se.vruntime' in content
    except (FileNotFoundError, PermissionError, OSError):
        _PROC_SCHED_AVAILABLE = False
    return _PROC_SCHED_AVAILABLE

def parse_proc_sched(pid):
    try:
        path = f'/proc/{pid}/sched'
        with open(path, 'r') as f:
            lines = f.readlines()
    except (FileNotFoundError, PermissionError, OSError):
        return None
    result = {}
    for line in lines:
        if ':' in line:
            (key, _, val) = line.partition(':')
            key = key.strip()
            val = val.strip()
            try:
                result[key] = float(val)
            except ValueError:
                result[key] = val
    return result if result else None

def get_real_vruntime(pid, fallback_cpu=0.0):
    if _check_proc_sched_available():
        data = parse_proc_sched(pid)
        if data and 'se.vruntime' in data:
            vrt = int(data['se.vruntime'] * 1000)
            return (vrt, 'proc')
    return (int(fallback_cpu * 1000000), 'estimated')

def get_proc_sched_extras(pid):
    if not _check_proc_sched_available():
        return None
    data = parse_proc_sched(pid)
    if not data:
        return None
    return {'vruntime_ns': int(data.get('se.vruntime', 0) * 1000), 'sum_exec_runtime_ns': int(data.get('se.sum_exec_runtime', 0) * 1000), 'voluntary_switches': int(data.get('nr_voluntary_switches', 0)), 'involuntary_switches': int(data.get('nr_involuntary_switches', 0))}
PROC_SCHED_SOURCE = property(lambda self: 'live /proc' if _check_proc_sched_available() else 'estimated')
_LINUX_STATE_MAP = {'running': 'R', 'sleeping': 'S', 'disk-sleep': 'D', 'zombie': 'Z', 'stopped': 'T', 'tracing-stop': 'T', 'dead': 'X', 'idle': 'S'}

import json
import threading
import time

EBPF_PROCS = []
_DAEMON_PROC = None
_DAEMON_STARTED = False

_psutil_procs = {}

def _read_ebpf_daemon():
    global EBPF_PROCS, _DAEMON_PROC, _psutil_procs
    # Determine absolute path to the daemon to avoid working directory issues
    daemon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'cpp_engine', 'sched_daemon'))
    
    if os.geteuid() == 0:
        cmd = [daemon_path]
    else:
        cmd = ['pkexec', daemon_path]
        
    try:
        _DAEMON_PROC = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True)
        for line in _DAEMON_PROC.stdout:
            try:
                data = json.loads(line.strip())
                procs = []
                
                # Remove dead processes from cache to prevent memory leaks
                current_pids = {d['pid'] for d in data}
                for pid in list(_psutil_procs.keys()):
                    if pid not in current_pids:
                        del _psutil_procs[pid]
                        
                for d in data:
                    pid = d['pid']
                    cpu_percent = 0.0
                    username = 'root'
                    nice = 0
                    vcs = 0
                    nvcs = 0
                    
                    if PSUTIL_AVAILABLE:
                        try:
                            if pid not in _psutil_procs:
                                p = psutil.Process(pid)
                                _psutil_procs[pid] = {'p': p, 'cpu': 0.0, 'time': time.time()}
                                p.cpu_percent(interval=None) # Initialize CPU counter
                            else:
                                cache = _psutil_procs[pid]
                                now = time.time()
                                if now - cache['time'] >= 0.5:
                                    cache['cpu'] = cache['p'].cpu_percent(interval=None)
                                    cache['time'] = now
                                cpu_percent = cache['cpu']
                                username = cache['p'].username()
                                nice = cache['p'].nice()
                                try:
                                    ctx = cache['p'].num_ctx_switches()
                                    vcs = ctx.voluntary
                                    nvcs = ctx.involuntary
                                except:
                                    vcs = 0
                                    nvcs = 0
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            if pid in _psutil_procs:
                                del _psutil_procs[pid]

                    procs.append({
                        'pid': pid,
                        'name': d['comm'],
                        'user': username[:10],
                        'state': 'R',
                        'ni': nice,
                        'pri': 20 + nice,
                        'cpu': round(cpu_percent / (psutil.cpu_count() or 1), 1), 
                        'mem': round((d.get('mem_kb', 0) * 1024.0) / psutil.virtual_memory().total * 100.0 if PSUTIL_AVAILABLE else 0.0, 1),
                        'policy': get_scheduler(pid),
                        'vrt': d['vruntime'],
                        'vcs': vcs,
                        'nvcs': nvcs,
                        'core': d['cpu']
                    })
                EBPF_PROCS = procs
            except Exception as e:
                pass
    except Exception:
        pass

def start_ebpf_daemon():
    global _DAEMON_STARTED
    if not _DAEMON_STARTED:
        t = threading.Thread(target=_read_ebpf_daemon, daemon=True)
        t.start()
        _DAEMON_STARTED = True

def get_real_processes():
    start_ebpf_daemon()
    if not EBPF_PROCS:
        return _generate_simulated_processes()
    return EBPF_PROCS

def update_real_processes(existing):
    start_ebpf_daemon()
    if not EBPF_PROCS:
        return _generate_simulated_processes()
    return EBPF_PROCS

def _generate_simulated_processes():
    names = ['systemd', 'bash', 'python3', 'chrome', 'code', 'nginx', 'postgres', 'node', 'java', 'gcc', 'vim', 'htop', 'curl', 'ssh', 'git', 'kworker', 'Xorg', 'pulseaudio', 'NetworkMgr', 'cups', 'dbus', 'avahi', 'cron', 'rsyslog', 'udev', 'snapd', 'containerd', 'dockerd', 'redis', 'mysql']
    users = ['root', 'user', 'daemon', 'www-data', 'postgres']
    states = ['R', 'S', 'S', 'S', 'D', 'Z']
    pols = ['CFS', 'CFS', 'CFS', 'CFS', 'FIFO', 'RR', 'BATCH']
    procs = []
    for i in range(28):
        pol = random.choice(pols)
        procs.append({'pid': 1000 + i * 17, 'name': names[i % len(names)], 'user': random.choice(users), 'state': random.choice(states), 'ni': random.choice([0, 0, 0, -5, 5, 10, 19]), 'pri': random.randint(1, 39), 'cpu': round(random.uniform(0, 45), 1), 'mem': round(random.uniform(0.1, 8), 1), 'policy': pol, 'vrt': random.randint(100000, 9000000) if pol == 'CFS' else 0, 'vcs': random.randint(0, 5000), 'nvcs': random.randint(0, 2000), 'core': random.randint(0, 3)})
    return procs

def _update_simulated_processes(procs):
    for p in procs:
        p['cpu'] = max(0.0, min(99.0, p['cpu'] + random.uniform(-3, 3)))
        p['mem'] = max(0.1, min(15.0, p['mem'] + random.uniform(-0.2, 0.2)))
        p['vcs'] += random.randint(0, 20)
        p['nvcs'] += random.randint(0, 5)
        if p['policy'] == 'CFS':
            p['vrt'] += random.randint(10000, 300000)
        if random.random() < 0.05:
            p['state'] = random.choice(['R', 'S', 'S', 'D'])
    return procs

def jains_fairness(vals):
    if not vals:
        return 1.0
    n = len(vals)
    s = sum(vals)
    sq = sum((v * v for v in vals))
    return round(s * s / (n * sq), 3) if sq else 1.0

def cpu_variance(vals):
    if not vals:
        return 0.0
    mean = sum(vals) / len(vals)
    return round(sum(((v - mean) ** 2 for v in vals)) / len(vals), 2)

def core_stats(processes):
    stats = {c: {'util': 0.0, 'procs': []} for c in range(4)}
    for p in processes:
        c = p['core'] % 4
        stats[c]['util'] += p['cpu']
        stats[c]['procs'].append(p)
    return stats