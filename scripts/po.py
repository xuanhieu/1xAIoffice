"""Minimal reader and writer for the gettext PO files used by upstream translations (no external packages).

An entry keeps its original lines. Only a field that is changed is re-rendered, in the layout gettext and
upstream's own l10ntools use (multi-line values as `msgstr ""` followed by one quoted line per "\\n"), because
upstream's cfgex silently drops a file whose multi-line msgctxt is written on a single line. An unchanged file is
written back byte for byte.
"""
import re

_STR = re.compile(r'^(msgctxt|msgid|msgid_plural|msgstr(?:\[\d+\])?)\s+"(.*)"\s*$')
_CONT = re.compile(r'^"(.*)"\s*$')


def _unquote(s):
    return (s.replace('\\\\', '\x00').replace('\\n', '\n').replace('\\t', '\t').replace('\\"', '"')
            .replace('\x00', '\\'))


def _quote(s):
    return s.replace('\\', '\\\\').replace('"', '\\"').replace('\t', '\\t').replace('\n', '\\n')


def _render_field(name, value):
    if '\n' not in value or value.endswith('\n') and value.count('\n') == 1 and len(value) < 70:
        return [f'{name} "{_quote(value)}"']
    parts = value.split('\n')
    pieces = [p + '\n' for p in parts[:-1]] + ([parts[-1]] if parts[-1] else [])
    return [f'{name} ""'] + [f'"{_quote(p)}"' for p in pieces]


class Entry:
    def __init__(self):
        self.comments = []          # raw lines starting with '#'
        self.fields = {}            # field name -> unquoted value
        self.order = []             # field order as read
        self.raw = {}               # field name -> original lines (absent for new or changed fields)

    @property
    def key(self):
        return (self.fields.get('msgctxt', ''), self.fields.get('msgid', ''))

    @property
    def fuzzy(self):
        return any(c.startswith('#,') and 'fuzzy' in c for c in self.comments)

    def set_field(self, name, value):
        self.fields[name] = value
        self.raw.pop(name, None)
        if name not in self.order:
            self.order.append(name)

    def set_translation(self, text):
        # Plural entries (msgid_plural) keep their translation in msgstr[0]; Vietnamese has a single plural form.
        self.set_field('msgstr[0]' if 'msgid_plural' in self.fields else 'msgstr', text)
        cleaned = []
        for c in self.comments:
            if c.startswith('#,') and 'fuzzy' in c:
                flags = [f.strip() for f in c[2:].split(',') if f.strip() and f.strip() != 'fuzzy']
                if flags:
                    cleaned.append('#, ' + ', '.join(flags))
            else:
                cleaned.append(c)
        self.comments = cleaned

    def references(self):
        return [r for c in self.comments if c.startswith('#:') for r in c[2:].split()]

    def render(self):
        lines = list(self.comments)
        for name in self.order:
            lines.extend(self.raw.get(name) or _render_field(name, self.fields[name]))
        return '\n'.join(lines)


def parse(text):
    entries, cur, last = [], Entry(), None
    for line in text.split('\n'):
        if not line.strip():
            if cur.fields or cur.comments:
                entries.append(cur)
            cur, last = Entry(), None
            continue
        if line.startswith('#'):
            if cur.fields:
                entries.append(cur)
                cur, last = Entry(), None
            cur.comments.append(line)
            continue
        m = _STR.match(line)
        if m:
            last = m.group(1)
            cur.fields[last] = _unquote(m.group(2))
            cur.order.append(last)
            cur.raw[last] = [line]
            continue
        m = _CONT.match(line)
        if m and last:
            cur.fields[last] += _unquote(m.group(1))
            cur.raw[last].append(line)
            continue
        raise ValueError(f'cannot parse PO line: {line!r}')
    if cur.fields or cur.comments:
        entries.append(cur)
    return entries


def render(entries):
    return '\n\n'.join(e.render() for e in entries) + '\n'


def load(path):
    with open(path, encoding='utf-8') as f:
        return parse(f.read())


def save(path, entries):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(render(entries))


def is_translated(entry):
    text = entry.fields.get('msgstr[0]' if 'msgid_plural' in entry.fields else 'msgstr')
    return bool(text) and not entry.fuzzy


def translation(entry):
    return entry.fields.get('msgstr[0]' if 'msgid_plural' in entry.fields else 'msgstr', '')
