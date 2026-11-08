"""The text a session carries whatever the task, measured from the transcripts.

Claude Code puts four lists in front of every request: the agent descriptions, the skill descriptions,
the text hooks add at session start, and the instructions of the MCP servers. Each is written to the
server cache once and re-read on every request after it, and written again when the cache has expired.
A skill's body joins them from the moment the skill is loaded until the session is compacted or ends.
The transcript records each of these (the attachment rows `agent_listing_delta`, `skill_listing`,
`hook_additional_context`, `mcp_instructions_delta`, and the "Base directory for this skill" message),
so their size and what re-reading them cost can be counted per machine, with nothing run.

Tokens are characters / 4: an estimate, say "about" when quoting them. A transcript written by a
Claude Code version without these rows counts nothing, and nothing is suggested from it.
"""
import collections
import hashlib
import re

CHARS_PER_TOKEN = 4
PARTS = ('agents', 'skills', 'hooks', 'mcp')
BODY_START = 'Base directory for this skill'
# A fenced block of shell: the part of a skill body a script could run in one command.
COMMAND_FENCE = re.compile(r'```(?:bash|sh|shell|zsh|console|powershell|ps1|cmd)[^\n]*\n(.*?)```', re.S)


def tokens(chars):
    return round(chars / CHARS_PER_TOKEN)


def command_share(body):
    """The share of a skill body that is shell in fenced blocks (0..1): how much of it is a procedure."""
    return round(sum(len(m.group(1)) for m in COMMAND_FENCE.finditer(body)) / len(body), 2) if body else 0.0


def write_rate(usage, rates):
    """What a token written to the cache cost on this request: by its 5-minute/1-hour split when the
    receipt has one, else the CLI's default 1-hour cache (the same rule as catalog/price.py)."""
    cc = usage.get('cache_creation') or {}
    w5, w1 = cc.get('ephemeral_5m_input_tokens') or 0, cc.get('ephemeral_1h_input_tokens') or 0
    return (w5 * rates['write_5m'] + w1 * rates['write_1h']) / (w5 + w1) if w5 + w1 else rates['write_1h']


class Session:
    """One main transcript, read in order: what it carries now, and what carrying it cost in the window."""

    def __init__(self):
        self.chars = dict.fromkeys(PARTS, 0)            # what each list holds now
        self.cost = dict.fromkeys(PARTS, 0.0)
        self.entries = {'agents': {}, 'skills': {}}     # name -> characters of its line in the list
        self.builtin = set()                            # agent types Claude Code ships: no file to move
        self.unwritten = set()                          # lists that changed since the last request
        self.first_total = None                         # what the first request cached: a later read below it means a cold cache
        self.requests = 0
        self.last_ts = ''
        self.calls = {}                                 # Skill tool_use id -> skill name
        self.used = collections.Counter()               # skill -> loads in the window
        self.bodies = []                                # loaded skill bodies, in order

    def attachment(self, a):
        k = a.get('type')
        if k == 'agent_listing_delta':
            lines = a.get('addedLines') or []
            names = a.get('addedTypes') or []
            if a.get('isInitial'):
                self.entries['agents'] = {}
            for i, line in enumerate(lines):
                name = names[i] if len(names) == len(lines) else line[2:].split(':', 1)[0]
                self.entries['agents'][name] = len(line) + 1
            for name in a.get('removedTypes') or []:
                self.entries['agents'].pop(name, None)
            self.builtin |= set(a.get('builtInTypes') or []) | set(a.get('builtInPluginTypes') or [])
            self.chars['agents'] = sum(self.entries['agents'].values())
            self.unwritten.add('agents')
        elif k == 'skill_listing':
            if a.get('isInitial'):
                self.entries['skills'] = {}
            for entry in ('\n' + (a.get('content') or '')).split('\n- ')[1:]:
                self.entries['skills'][entry.split(': ', 1)[0].strip()] = len(entry) + 3
            self.chars['skills'] = sum(self.entries['skills'].values())
            self.unwritten.add('skills')
        elif k == 'hook_additional_context':
            c = a.get('content')
            self.chars['hooks'] += sum(len(x) for x in c) if isinstance(c, list) else len(str(c or ''))
            self.unwritten.add('hooks')
        elif k == 'mcp_instructions_delta':
            self.chars['mcp'] += sum(len(x) for x in a.get('addedBlocks') or [])
            self.unwritten.add('mcp')

    def skill_call(self, tool_use_id, name):
        if name:
            self.calls[tool_use_id] = name

    def body(self, text, tool_use_id=None, counted=True):
        """A skill body entered the session: named by the Skill call that asked for it, else by its folder
        (a /name typed by the person has no call)."""
        folder = re.split(r'[\\/]', text.split('\n', 1)[0].strip())[-1]
        name = self.calls.get(tool_use_id) or next((n for n in self.entries['skills'] if n == folder or n.endswith(':' + folder)), folder)
        self.bodies.append({'skill': name, 'chars': len(text), 'digest': hashlib.sha1(text.encode('utf-8')).hexdigest()[:8],
                            'commands': command_share(text), 'written': False, 'alive': True, 'requests': 0, 'cost': 0.0})
        if counted:
            self.used[name] += 1

    def compact(self):
        """A compaction: the loaded bodies are gone with the rest of the conversation (the lists come back)."""
        for b in self.bodies:
            b['alive'] = False

    def request(self, usage, rates, ts='', counted=True):
        """One API request: every list and every loaded body was read from the cache, or written to it when
        it was new or the cache was cold. `counted` is False outside the window (the state still moves)."""
        rd = usage.get('cache_read_input_tokens') or 0
        cold = self.first_total is None or rd < self.first_total
        if self.first_total is None:
            self.first_total = rd + (usage.get('cache_creation_input_tokens') or 0)   # what the first request left in the cache
        if counted and rates:
            wr = write_rate(usage, rates)
            for p in PARTS:
                self.cost[p] += tokens(self.chars[p]) * (wr if cold or p in self.unwritten else rates['cache_read'])
            for b in self.bodies:
                if b['alive']:
                    b['cost'] += tokens(b['chars']) * (wr if cold or not b['written'] else rates['cache_read'])
                    b['requests'] += 1
            self.requests += 1
            self.last_ts = max(self.last_ts, ts)
        for b in self.bodies:
            b['written'] = True
        self.unwritten.clear()


def summary(sessions, called_agents=()):
    """The window over every main transcript: per list its size now (the newest session's), what carrying it
    cost, and the entries nothing here used; per loaded skill its loads, the requests that carried it and
    what that cost. None when no transcript has the rows."""
    live = [s for s in sessions if s.requests and any(s.chars.values())]
    if not live:
        return None
    newest = max(live, key=lambda s: s.last_ts)
    listed = newest.entries['skills']

    def as_listed(name):   # a body named by its folder (the list came after it) under the name the list has
        match = [n for n in listed if n.endswith(':' + name)]
        return name if name in listed or len(match) != 1 else match[0]
    used = collections.Counter()
    for s in live:
        for name, n in s.used.items():
            used[as_listed(name)] += n
    called = set(called_agents)
    parts = {}
    for p in PARTS:
        part = {'tokens': tokens(newest.chars[p]), 'cost': round(sum(s.cost[p] for s in live), 2)}
        if p in newest.entries:
            entries = newest.entries[p]
            inuse = called if p == 'agents' else set(used)
            fixed = newest.builtin if p == 'agents' else set()
            idle = {n: c for n, c in entries.items() if n not in inuse and n not in fixed}
            part.update({'n': len(entries), 'unused_n': len(idle), 'unused_tokens': tokens(sum(idle.values())),
                         'largest_unused': [{'name': n, 'tokens': tokens(c)} for n, c in sorted(idle.items(), key=lambda kv: -kv[1])[:8]]})
            if p == 'skills':   # plugin:skill names say which plugin a skill goes with; '' is the person's own and the bundled ones
                src = collections.defaultdict(lambda: [0, 0])
                for n, c in idle.items():
                    k = n.split(':', 1)[0] if ':' in n else ''
                    src[k][0] += 1; src[k][1] += c
                part['unused_by_source'] = [{'source': k, 'n': v[0], 'tokens': tokens(v[1])} for k, v in sorted(src.items(), key=lambda kv: -kv[1][1])]
        parts[p] = part
    by_skill = {}
    for s in live:
        for b in s.bodies:
            if not b['requests']:
                continue
            name = as_listed(b['skill'])
            x = by_skill.setdefault(name, {'skill': name, 'loads': 0, 'requests': 0, 'cost': 0.0})
            x['loads'] += 1; x['requests'] += b['requests']; x['cost'] += b['cost']
            x.update({'tokens': tokens(b['chars']), 'digest': b['digest'], 'commands': b['commands']})   # the newest load's body
    bodies = sorted(({**x, 'cost': round(x['cost'], 2)} for x in by_skill.values()), key=lambda x: -x['cost'])
    return {'requests': sum(s.requests for s in live), 'sessions': len(live), 'parts': parts, 'bodies': bodies,
            'skills_used': dict(used)}
