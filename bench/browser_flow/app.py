"""Tiny "items" web app with one planted defect, for the browser-flow family.

Login, a list of items with quantity, unit price, line total and grand total,
add / edit / delete, logout. Pure standard library, in-memory state, one
process per task. The defect is chosen on the command line and is invisible in
the HTML except through behaviour.

Usage: python3 app.py --port 8765 --defect none|wrong-password-accepted|...
Grading endpoints: GET /__state (items, action log), POST /__reset.
"""
import argparse
import html
import json
import re
import secrets
import threading
from decimal import Decimal, InvalidOperation
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

USER, PASSWORD = 'tester', 'letmein'
DEFECTS = ['none', 'wrong-password-accepted', 'wrong-user-shown', 'line-total-adds',
           'grand-total-skips-last', 'grand-total-rounds', 'empty-name-accepted',
           'edit-not-saved', 'edit-loses-name', 'delete-wrong-row', 'logout-keeps-session']
DEFECT = 'none'
LOCK = threading.Lock()
STATE = {'items': [], 'next_id': 1, 'sessions': set(), 'log': []}

PAGE = """<!doctype html><html><head><meta charset="utf-8"><title>{title}</title>
<style>body{{font-family:sans-serif;max-width:720px;margin:2em auto}} .error{{color:#b00020;font-weight:bold}}
table{{border-collapse:collapse}} td,th{{border:1px solid #999;padding:4px 10px}} form.inline{{display:inline}}</style>
</head><body>{body}</body></html>"""


def money(v):
    return f'{v.quantize(Decimal("0.01")):.2f}'


def line_total(item):
    if DEFECT == 'line-total-adds':
        return item['qty'] + item['price']
    return item['qty'] * item['price']


def grand_total(items):
    rows = items[:-1] if DEFECT == 'grand-total-skips-last' else items
    total = sum((line_total(i) for i in rows), Decimal('0'))
    return str(int(total)) if DEFECT == 'grand-total-rounds' else money(total)


def login_page(error=''):
    err = f'<p class="error" id="error">{html.escape(error)}</p>' if error else ''
    return PAGE.format(title='Sign in', body=f"""<h1>Sign in</h1>{err}
<form method="post" action="/login" id="login">
<label>Username <input name="username" id="username"></label><br>
<label>Password <input name="password" id="password" type="password"></label><br>
<button type="submit">Sign in</button></form>""")


def items_page(items, error='', who=USER):
    shown = 'admin' if DEFECT == 'wrong-user-shown' else who
    rows = ''.join(
        f'<tr data-id="{i["id"]}"><td class="name">{html.escape(i["name"])}</td><td class="qty">{i["qty"]}</td>'
        f'<td class="price">{money(i["price"])}</td><td class="line">{money(line_total(i))}</td>'
        f'<td><a href="/items/{i["id"]}">Edit</a> <form class="inline" method="post" action="/items/{i["id"]}/delete">'
        f'<button type="submit">Delete</button></form></td></tr>' for i in items)
    err = f'<p class="error" id="error">{html.escape(error)}</p>' if error else ''
    return PAGE.format(title='Items', body=f"""<p id="who">Signed in as {html.escape(shown)}</p>
<form class="inline" method="post" action="/logout" id="logout"><button type="submit">Log out</button></form>
<h1>Items</h1>
<table id="items"><thead><tr><th>Name</th><th>Quantity</th><th>Unit price</th><th>Line total</th><th></th></tr></thead>
<tbody>{rows}</tbody></table>
<p id="grand">Grand total: <span id="grand-value">{grand_total(items)}</span></p>
<h2>Add item</h2>{err}
<form method="post" action="/items" id="add">
<label>Name <input name="name" id="name"></label>
<label>Quantity <input name="qty" id="qty" value="1" size="4"></label>
<label>Unit price <input name="price" id="price" value="1.00" size="8"></label>
<button type="submit">Add item</button></form>""")


def edit_page(item, error=''):
    err = f'<p class="error" id="error">{html.escape(error)}</p>' if error else ''
    return PAGE.format(title='Edit item', body=f"""<h1>Edit item</h1>{err}
<form method="post" action="/items/{item['id']}" id="edit">
<label>Name <input name="name" id="name" value="{html.escape(item['name'])}"></label>
<label>Quantity <input name="qty" id="qty" value="{item['qty']}" size="4"></label>
<label>Unit price <input name="price" id="price" value="{money(item['price'])}" size="8"></label>
<button type="submit">Save</button> <a href="/items">Cancel</a></form>""")


def validate(form):
    name = (form.get('name') or [''])[0].strip()
    if not name and DEFECT != 'empty-name-accepted':
        return None, 'Name is required'
    try:
        qty = int((form.get('qty') or [''])[0].strip())
        if qty < 1:
            raise ValueError
    except ValueError:
        return None, 'Quantity must be a whole number of at least 1'
    try:
        price = Decimal((form.get('price') or [''])[0].strip())
        if price < 0 or price != price.quantize(Decimal('0.01')):
            raise InvalidOperation
    except InvalidOperation:
        return None, 'Price must be a number like 2.50'
    return {'name': name, 'qty': qty, 'price': price}, ''


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def sid(self):
        c = cookies.SimpleCookie(self.headers.get('Cookie', ''))
        return c['sid'].value if 'sid' in c else None

    def signed_in(self):
        s = self.sid()
        return bool(s and s in STATE['sessions'])

    def send(self, body, status=200, set_cookie=None):
        data = body.encode()
        self.send_response(status)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        if set_cookie:
            self.send_header('Set-Cookie', set_cookie)
        self.end_headers()
        self.wfile.write(data)

    def redirect(self, where, set_cookie=None):
        self.send_response(303)
        self.send_header('Location', where)
        self.send_header('Content-Length', '0')
        if set_cookie:
            self.send_header('Set-Cookie', set_cookie)
        self.end_headers()

    def form(self):
        n = int(self.headers.get('Content-Length') or 0)
        return parse_qs(self.rfile.read(n).decode(), keep_blank_values=True)

    def note(self, action, **detail):
        STATE['log'].append({'action': action, **detail})

    def do_GET(self):
        if self.path == '/__state':
            with LOCK:
                body = json.dumps({'defect': DEFECT, 'items': [{**i, 'price': money(i['price'])} for i in STATE['items']],
                                   'sessions': len(STATE['sessions']), 'log': STATE['log']})
            data = body.encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if self.path == '/':
            return self.send(login_page())
        if not self.signed_in():
            self.note('denied', path=self.path)
            return self.redirect('/')
        if self.path == '/items':
            with LOCK:
                self.note('list')
                return self.send(items_page(STATE['items']))
        m = re.fullmatch(r'/items/(\d+)', self.path)
        if m:
            with LOCK:
                item = next((i for i in STATE['items'] if i['id'] == int(m.group(1))), None)
            if item:
                return self.send(edit_page(item))
        self.send(PAGE.format(title='Not found', body='<h1>Not found</h1>'), 404)

    def do_POST(self):
        if self.path == '/__reset':
            with LOCK:
                STATE.update({'items': [], 'next_id': 1, 'sessions': set(), 'log': []})
            return self.redirect('/')
        if self.path == '/login':
            f = self.form()
            user = (f.get('username') or [''])[0]
            pw = (f.get('password') or [''])[0]
            ok = user == USER and (pw == PASSWORD or DEFECT == 'wrong-password-accepted')
            with LOCK:
                self.note('login', user=user, ok=ok)
                if not ok:
                    return self.send(login_page('Invalid username or password'))
                sid = secrets.token_hex(8)
                STATE['sessions'].add(sid)
            return self.redirect('/items', set_cookie=f'sid={sid}; Path=/; HttpOnly')
        if not self.signed_in():
            self.note('denied', path=self.path)
            return self.redirect('/')
        if self.path == '/logout':
            with LOCK:
                self.note('logout')
                if DEFECT != 'logout-keeps-session':
                    STATE['sessions'].discard(self.sid())
            return self.redirect('/', set_cookie=None if DEFECT == 'logout-keeps-session'
                                 else 'sid=; Path=/; Max-Age=0')
        if self.path == '/items':
            f = self.form()
            item, error = validate(f)
            with LOCK:
                self.note('add', name=(f.get('name') or [''])[0], ok=not error)
                if error:
                    return self.send(items_page(STATE['items'], error))
                item['id'] = STATE['next_id']
                STATE['next_id'] += 1
                STATE['items'].append(item)
            return self.redirect('/items')
        m = re.fullmatch(r'/items/(\d+)(/delete)?', self.path)
        if not m:
            return self.send(PAGE.format(title='Not found', body='<h1>Not found</h1>'), 404)
        target = int(m.group(1))
        with LOCK:
            item = next((i for i in STATE['items'] if i['id'] == target), None)
            if item is None:
                return self.send(PAGE.format(title='Not found', body='<h1>Not found</h1>'), 404)
            if m.group(2):
                victim = STATE['items'][0] if DEFECT == 'delete-wrong-row' else item
                self.note('delete', id=target, removed=victim['id'])
                STATE['items'].remove(victim)
                return self.redirect('/items')
            f = self.form()
            new, error = validate(f)
            self.note('edit', id=target, ok=not error)
            if error:
                return self.send(edit_page(item, error))
            if DEFECT != 'edit-not-saved':
                item.update(new)
                if DEFECT == 'edit-loses-name':
                    item['name'] = ''
            return self.redirect('/items')


def main():
    global DEFECT
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', type=int, default=8765)
    ap.add_argument('--defect', default='none', choices=DEFECTS)
    args = ap.parse_args()
    DEFECT = args.defect
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    print(f'ready http://127.0.0.1:{args.port}/ defect={DEFECT}', flush=True)
    server.serve_forever()


if __name__ == '__main__':
    main()
