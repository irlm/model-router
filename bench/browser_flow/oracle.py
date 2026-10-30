"""Scripted user for the browser-flow checklist. Drives the app over HTTP the
way a user would through its pages and returns pass/fail per checklist item.
It computes each task's truth vector (make_tasks.py) and doubles as the app's
test. Agents never see it; they only get CHECKLIST.
"""
import http.cookiejar
import re
import urllib.parse
import urllib.request
from decimal import Decimal, InvalidOperation

CHECKLIST = [
    'Sign in with username `tester` and password `wrong`: the page shows the message "Invalid username or password" and you are still on the sign-in page.',
    'Sign in with username `tester` and password `letmein`: you land on the Items page and it shows "Signed in as tester".',
    'Add an item with name `Pen`, quantity `3`, unit price `2.50`: a row `Pen` appears with line total 7.50.',
    'Add an item with name `Notebook`, quantity `1`, unit price `3.25`: a row `Notebook` appears with line total 3.25.',
    'The grand total shown is 10.75.',
    'Open the Edit link of `Pen`, change the quantity to `4`, keep the rest, and Save: the `Pen` row shows line total 10.00 and the grand total is 13.25.',
    'Press the Delete button of `Notebook`: the `Notebook` row is gone, the `Pen` row remains, and the grand total is 10.00.',
    'Submit the Add item form with an empty name (quantity `1`, unit price `1.00`): the page shows "Name is required" and the table still has exactly one row.',
    'Press Log out: you are on the sign-in page, and opening the Items page URL (/items) shows the sign-in page, not the items.',
]
ROW = re.compile(r'<tr data-id="(\d+)"><td class="name">(.*?)</td><td class="qty">(\d+)</td>'
                 r'<td class="price">(.*?)</td><td class="line">(.*?)</td>')


def same(text, expected):
    try:
        return Decimal(text.strip()) == Decimal(expected)
    except (InvalidOperation, AttributeError):
        return False


class User:
    def __init__(self, base):
        self.base = base.rstrip('/')
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def get(self, path):
        with self.opener.open(self.base + path, timeout=10) as r:
            return r.geturl(), r.read().decode()

    def post(self, path, **data):
        body = urllib.parse.urlencode(data).encode()
        with self.opener.open(urllib.request.Request(self.base + path, data=body), timeout=10) as r:
            return r.geturl(), r.read().decode()


def rows(html):
    return [{'id': int(i), 'name': n, 'qty': int(q), 'price': p, 'line': l} for i, n, q, p, l in ROW.findall(html)]


def grand(html):
    m = re.search(r'<span id="grand-value">(.*?)</span>', html)
    return m.group(1) if m else ''


def is_login(html):
    return 'id="login"' in html and 'Signed in as' not in html


def run_checklist(base):
    u, ok = User(base), {}
    _, h = u.post('/login', username='tester', password='wrong')
    ok[1] = 'Invalid username or password' in h and is_login(h)
    url, h = u.post('/login', username='tester', password='letmein')
    ok[2] = url.endswith('/items') and 'Signed in as tester' in h
    _, h = u.post('/items', name='Pen', qty='3', price='2.50')
    pen = [r for r in rows(h) if r['name'] == 'Pen']
    ok[3] = bool(pen) and same(pen[0]['line'], '7.50')
    _, h = u.post('/items', name='Notebook', qty='1', price='3.25')
    nb = [r for r in rows(h) if r['name'] == 'Notebook']
    ok[4] = bool(nb) and same(nb[0]['line'], '3.25')
    ok[5] = same(grand(h), '10.75')
    pen = [r for r in rows(h) if r['name'] == 'Pen']
    if pen:
        _, h = u.post(f"/items/{pen[0]['id']}", name='Pen', qty='4', price='2.50')
    pen = [r for r in rows(h) if r['name'] == 'Pen']
    ok[6] = bool(pen) and same(pen[0]['line'], '10.00') and same(grand(h), '13.25')
    nb = [r for r in rows(h) if r['name'] == 'Notebook']
    if nb:
        _, h = u.post(f"/items/{nb[0]['id']}/delete")
    names = [r['name'] for r in rows(h)]
    ok[7] = 'Notebook' not in names and 'Pen' in names and same(grand(h), '10.00')
    before = len(rows(h))
    _, h = u.post('/items', name='', qty='1', price='1.00')
    ok[8] = 'Name is required' in h and len(rows(h)) == before == 1
    _, h = u.post('/logout')
    _, h2 = u.get('/items')
    ok[9] = is_login(h) and is_login(h2)
    return {str(k): ('pass' if v else 'fail') for k, v in sorted(ok.items())}
