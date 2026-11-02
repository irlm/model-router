"""Generate K4 semantic tasks (results/kernel-semantic/tasks.json).

Ground truth here is HAND-CLASSIFIED (call vs prototype vs definition
vs comment; dispatch handler wiring), reviewed site by site on
2026-10-09 against the pinned v6.12 tree. Everything mechanical is
re-checked at generation time and again by tests/test_semantic_tasks:
each classified site's line text must match the tree exactly, clean
candidates must have zero mentions, dispatch handlers must be defined,
and sysfs-paste handlers must occur exactly once tree-wide (the
wiring-invisibility property the family exists to test).
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE / 'bench/common'))
import local  # noqa: E402
OUT = HERE / 'results/kernel-semantic/tasks.json'
TREE = local.resolve('$KERNEL_TREE')   # local/config.json: kernel_tree

# family callers: per function, {candidate: [(line, class), ...]};
# class 'call' marks an actual runtime invocation. A file is in truth
# iff it has >= 1 'call' site. Files with no entry list are verified
# zero-mention clean files.
CALLERS = {
    'memparse': {
        'include/linux/string.h': [(318, 'prototype')],
        'lib/cmdline.c': [(150, 'definition')],
        'mm/hugetlb.c': [(4164, 'call'), (4652, 'call'), (4705, 'call'),
                         (7561, 'call'), (7574, 'call')],
        'fs/proc/loadavg.c': [],
    },
    'match_string': {
        'include/linux/string.h': [(323, 'prototype')],
        'lib/string_helpers.c': [(920, 'definition'), (943, 'comment')],
        'mm/vmpressure.c': [(391, 'call'), (399, 'call')],
        'lib/glob.c': [],
    },
    'sysfs_streq': {
        'include/linux/string.h': [(322, 'prototype')],
        'lib/string_helpers.c': [(886, 'definition'), (963, 'call')],
        'kernel/cpu.c': [(2926, 'call'), (2929, 'call'), (2932, 'call')],
        'lib/net_utils.c': [],
    },
    'kbasename': {
        'include/linux/string.h': [(383, 'inline-definition')],
        'kernel/gcov/fs.c': [(494, 'call')],
        'fs/exec.c': [(1350, 'call')],
        'lib/glob.c': [],
    },
    'strreplace': {
        'include/linux/string.h': [(284, 'prototype')],
        'lib/string_helpers.c': [(743, 'call'), (981, 'definition')],
        'kernel/irq/irqdomain.c': [(163, 'call')],
        'fs/proc/uptime.c': [],
    },
    'hex2bin': {
        'include/linux/hex.h': [(30, 'prototype')],
        'lib/hexdump.c': [(63, 'definition')],
        'fs/overlayfs/namei.c': [(627, 'call')],
        'lib/glob.c': [],
    },
    'kstrdup_const': {
        'include/linux/string.h': [(301, 'prototype')],
        'include/kunit/test.h': [(528, 'comment')],
        'mm/util.c': [(82, 'definition')],
        'lib/kobject.c': [(504, 'call')],
    },
    'memchr_inv': {
        'include/linux/string.h': [(283, 'prototype'), (295, 'call')],
        'lib/string.c': [(820, 'definition')],
        'mm/vmstat.c': [(2030, 'call'), (2037, 'call')],
        'io_uring/register.c': [(54, 'call'), (345, 'call')],
    },
    'skip_spaces': {
        'include/linux/string.h': [(184, 'prototype')],
        'lib/string_helpers.c': [(842, 'definition'), (872, 'call')],
        'lib/vsprintf.c': [(3438, 'call'), (3439, 'call'),
                           (3528, 'call'), (3618, 'call')],
        'drivers/gpio/gpio-sim.c': [(726, 'call')],
    },
    'string_get_size': {
        'include/linux/string_helpers.h': [(31, 'prototype')],
        'lib/string_helpers.c': [(39, 'definition')],
        'mm/hugetlb.c': [(3324, 'call'), (3351, 'call'),
                         (3515, 'call'), (4457, 'call')],
        'fs/proc/meminfo.c': [],
    },
    'mac_pton': {
        'include/linux/hex.h': [(33, 'prototype')],
        'lib/net_utils.c': [(8, 'definition')],
        'net/core/netpoll.c': [(602, 'call')],
        'lib/hexdump.c': [],
    },
    'glob_match': {
        'include/linux/glob.h': [(8, 'prototype')],
        'lib/glob.c': [(28, 'comment'), (40, 'definition')],
        'lib/kunit/executor.c': [(63, 'comment'), (105, 'call'),
                                 (124, 'call'), (193, 'call')],
        'lib/globtest.c': [(21, 'call')],
    },
}

# family dispatch: (path, mechanism, handler, registration path:line,
# definition path:line, m_visibility). m_visibility preregisters what
# the M packet's two fixed-string searches can surface (verified
# 2026-10-09): 'direct' = handler on the registration line matched by
# the final component; 'substring' = the handler's own name contains
# the component, so its lines surface; 'convention' = only the
# handler's definition line surfaces (wiring is paste-invisible), so
# answering needs a naming-convention inference; 'invisible' = no
# shown line can contain the handler name at all.
DISPATCH = [
    ('/proc/uptime', 'proc', 'uptime_proc_show',
     ('fs/proc/uptime.c', 45), ('fs/proc/uptime.c', 12), 'direct'),
    ('/proc/meminfo', 'proc', 'meminfo_proc_show',
     ('fs/proc/meminfo.c', 177), ('fs/proc/meminfo.c', 34), 'direct'),
    ('/proc/softirqs', 'proc', 'show_softirqs',
     ('fs/proc/softirqs.c', 33), ('fs/proc/softirqs.c', 11), 'direct'),
    ('/proc/cmdline', 'proc', 'cmdline_proc_show',
     ('fs/proc/cmdline.c', 19), ('fs/proc/cmdline.c', 8), 'direct'),
    ('/proc/sys/kernel/hostname', 'sysctl', 'proc_do_uts_string',
     ('kernel/utsname_sysctl.c', 112), ('kernel/utsname_sysctl.c', 33),
     'invisible'),
    ('/proc/sys/vm/overcommit_memory', 'sysctl', 'overcommit_policy_handler',
     ('kernel/sysctl.c', 2040), ('mm/util.c', 927), 'invisible'),
    ('/proc/sys/vm/drop_caches', 'sysctl', 'drop_caches_sysctl_handler',
     ('kernel/sysctl.c', 2100), ('fs/drop_caches.c', 51), 'substring'),
    ('/proc/sys/vm/dirty_ratio', 'sysctl', 'dirty_ratio_handler',
     ('mm/page-writeback.c', 2320), ('mm/page-writeback.c', 538),
     'substring'),
    ('/sys/kernel/uevent_seqnum', 'sysfs-paste', 'uevent_seqnum_show',
     ('kernel/ksysfs.c', 44), ('kernel/ksysfs.c', 39), 'convention'),
    ('/sys/kernel/cpu_byteorder', 'sysfs-paste', 'cpu_byteorder_show',
     ('kernel/ksysfs.c', 52), ('kernel/ksysfs.c', 47), 'convention'),
    ('/sys/kernel/vmcoreinfo', 'sysfs-paste', 'vmcoreinfo_show',
     ('kernel/ksysfs.c', 175), ('kernel/ksysfs.c', 168), 'convention'),
    ('/sys/kernel/fscaps', 'sysfs-paste', 'fscaps_show',
     ('kernel/ksysfs.c', 197), ('kernel/ksysfs.c', 192), 'convention'),
]

SUBJECTS = {
    'proc': 'is the seq_file show handler that generates the contents of {p}',
    'sysctl': 'is the sysctl proc_handler invoked when a process writes to {p}',
    'sysfs-paste': 'implements the read (show) operation of the sysfs file {p}',
}


def file_line(path, lineno):
    return (Path(TREE) / path).read_text(errors='replace').splitlines()[lineno - 1]


def rg_count(pattern, path='.'):
    proc = subprocess.run(['rg', '-c', pattern, '--', path], cwd=TREE,
                          text=True, capture_output=True,
                          stdin=subprocess.DEVNULL)
    if proc.returncode > 1:
        raise RuntimeError(proc.stderr[:200])
    return sum(int(l.rsplit(':', 1)[-1]) for l in proc.stdout.splitlines() if l)


def main():
    tasks = []
    for i, (name, cands) in enumerate(CALLERS.items(), 1):
        sites, calling = {}, []
        for path, classified in cands.items():
            if not classified:
                assert rg_count(r'\b' + name + r'\b', path) == 0, \
                    f'{path} is not clean for {name}'
                sites[path] = []
                continue
            shaped = rg_count(r'\b' + name + r'\s*\(', path)
            assert shaped == len(classified), \
                f'{name} {path}: {shaped} call-shaped sites, {len(classified)} classified'
            sites[path] = [{'line': ln, 'class': cls,
                            'text': file_line(path, ln).strip()}
                           for ln, cls in classified]
            if any(cls == 'call' for _, cls in classified):
                calling.append(path)
        tasks.append({'id': f'callers-{i:02d}', 'family': 'callers',
                      'name': name, 'candidates': sorted(cands),
                      'truth': {'calling': sorted(calling)},
                      'evidence': {'sites': sites}})
    for i, (path, mech, handler, reg, dfn, vis) in enumerate(DISPATCH, 1):
        reg_text = file_line(*reg).strip()
        def_text = file_line(*dfn).strip()
        assert handler in def_text, f'{handler} not at {dfn}'
        if mech == 'sysfs-paste':
            assert handler not in reg_text, \
                f'{handler} visible at wiring {reg} — not paste-invisible'
            assert rg_count(r'\b' + handler + r'\b') == 1, \
                f'{handler} occurs more than once tree-wide'
        else:
            assert handler in reg_text, f'{handler} not on registration line {reg}'
        component = path.rsplit('/', 1)[-1]
        if vis in ('direct', 'substring', 'convention'):
            assert component in (def_text if vis == 'convention' else
                                 handler if vis == 'substring' else reg_text)
        else:
            # invisible: no line in the tree may contain component AND handler
            proc = subprocess.run(
                ['rg', '--no-heading', component, '.'], cwd=TREE, text=True,
                capture_output=True, stdin=subprocess.DEVNULL)
            assert not any(handler in l for l in proc.stdout.splitlines()), \
                f'{handler} co-occurs with {component} — not invisible'
        tasks.append({'id': f'dispatch-{i:02d}', 'family': 'dispatch',
                      'name': path, 'mechanism': mech, 'm_visibility': vis,
                      'subject': SUBJECTS[mech].format(p=path),
                      'truth': {'function': handler},
                      'evidence': {
                          'registration': {'path': reg[0], 'line': reg[1],
                                           'text': reg_text},
                          'definition': {'path': dfn[0], 'line': dfn[1],
                                         'text': def_text}}})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({'tree': TREE, 'tasks': tasks}, indent=1))
    print(f'wrote {OUT}: {len(tasks)} tasks '
          f'({sum(t["family"] == "callers" for t in tasks)} callers, '
          f'{sum(t["family"] == "dispatch" for t in tasks)} dispatch)')


if __name__ == '__main__':
    sys.exit(main())
