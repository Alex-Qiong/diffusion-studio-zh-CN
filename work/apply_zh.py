#!/usr/bin/env python3
"""Apply Simplified Chinese translations to Diffusion Studio Windows build bundles.

Safety rules per string-literal occurrence (renderer):
- skip TS-enum reverse maps:   [x.Member=0]="Member"
- skip property assignment:     x.Member="Member"   (prop name == string)
- skip object literal:          {Member:"Member"}   (key == string)
- skip switch case:             case"Member"
- skip KeyboardEvent.key compare: .key==="Member"
- skip hostElement registrations: hr("Member")
- getNextName (minified ad) call args use OVERRIDES (noun forms)
"""
import re, json, sys, os, argparse

WORK = os.path.dirname(os.path.abspath(__file__))
_ap = argparse.ArgumentParser()
_ap.add_argument('--app', default=os.path.join(WORK, '..', 'stage_app'),
                 help='path to the extracted app dir (resources/app)')
APP = os.path.abspath(_ap.parse_args().app)

DICT = {k: v for k, v in json.load(open(os.path.join(WORK, 'dict_zh.json'), encoding='utf-8')).items()
        if v != '__KEEP__'}

# noun forms for getNextName() default layer names (minified name: ad)
OVERRIDES = {('ad', 'Group'): '组', ('ad', 'Rect'): '矩形'}

# main.js: targeted raw-text replacements (dialog strings; template literals kept intact)
MAIN_REPLACEMENTS = [
    ('title: "Choose projects folder"', 'title: "选择项目文件夹"'),
    ('title: "Choose project folder"', 'title: "选择项目文件夹"'),
    ('"Choose another folder"', '"选择其他文件夹"'),
    ('title: "This folder is synced"', 'title: "此文件夹已同步"'),
    ('`${kind} syncs this folder.`', '`${kind} 会同步此文件夹。`'),
    ('`Projects here are not supported. Expect glitches: edits reappearing after you change them, '
     'work lost to a conflicting copy, or the project failing to build.\n\n'
     'Somewhere on local disk avoids all of this.`',
     '`此处不支持存放项目。可能会出现异常：修改的内容被还原、工作因冲突副本丢失，或项目无法构建。\n\n'
     '建议改用本地磁盘上的其他位置。`'),
    ('"Use anyway"', '"仍要使用"'),
]
# updater call site -> no-op (must not self-update back to official English build)
UPDATER_RE = re.compile(r'\(0,\s*import_update_electron_app\.updateElectronApp\)\(\{\s*repo:\s*"diffusionstudio/editor"\s*\}\);?')

# --- JS literal scanner (handles nested ${} in template literals) ---
_REGEX_PRECEDERS = set('(,=:[!&|?{};+-*%<>^~')

def _prev_sig(text, p):
    j = p - 1
    while j >= 0 and text[j] in ' \t\r\n':
        j -= 1
    return text[j] if j >= 0 else ''

def _looks_like_regex(text, p):
    """Heuristic: is the '/' at p the start of a regex literal?"""
    c = _prev_sig(text, p)
    if not c:
        return True
    if c in _REGEX_PRECEDERS:
        return True
    # keyword preceders: return, typeof, instanceof, in, of, new, delete, void
    m = re.search(r'(return|typeof|instanceof|in|of|new|delete|void|yield|await)$', text[:p])
    return bool(m)

def _scan_regex(text, i):
    n = len(text)
    j = i + 1
    in_class = False
    while j < n:
        ch = text[j]
        if ch == '\\':
            j += 2
            continue
        if ch == '\n':
            return j
        if ch == '[':
            in_class = True
        elif ch == ']':
            in_class = False
        elif ch == '/' and not in_class:
            j += 1
            while j < n and text[j] in 'dgimsuvy':
                j += 1
            return j
        j += 1
    return n
def _scan_quoted(text, i, q):
    n = len(text)
    j = i + 1
    while j < n:
        ch = text[j]
        if ch == '\\':
            j += 2
            continue
        if ch == q:
            return j + 1
        if ch == '\n':
            return None
        j += 1
    return None

def _scan_template(text, i):
    n = len(text)
    j = i + 1
    while j < n:
        ch = text[j]
        if ch == '\\':
            j += 2
            continue
        if ch == '`':
            return j + 1
        if ch == '$' and j + 1 < n and text[j + 1] == '{':
            j = _scan_expr(text, j + 2)
            if j is None:
                return None
            continue
        j += 1
    return None

def _scan_expr(text, j):
    # just past '${'; return index just past matching '}'
    n = len(text)
    depth = 1
    while j < n:
        ch = text[j]
        if ch == '\\':
            j += 2
            continue
        if ch == '"' or ch == "'":
            e = _scan_quoted(text, j, ch)
            j = e if e else j + 1
            continue
        if ch == '`':
            e = _scan_template(text, j)
            j = e if e else j + 1
            continue
        if ch == '/' and j + 1 < n and text[j + 1] == '/':
            k = text.find('\n', j)
            j = n if k < 0 else k + 1
            continue
        if ch == '/' and j + 1 < n and text[j + 1] == '*':
            k = text.find('*/', j + 2)
            j = n if k < 0 else k + 2
            continue
        if ch == '/' and _looks_like_regex(text, j):
            # regex literal inside ${...}, e.g. ${x.replace(/"/g, '')}
            e = _scan_regex(text, j)
            j = e if e else j + 1
            continue
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return j + 1
        j += 1
    return None

def iter_literals(text):
    """Yield (start, end, raw) for each string/template literal, skipping comments."""
    n = len(text)
    i = 0
    while i < n:
        a = text.find('"', i)
        b = text.find("'", i)
        c = text.find('`', i)
        d1 = text.find('//', i)
        d2 = text.find('/*', i)
        f = text.find('/', i)
        cand = []
        if a >= 0: cand.append((a, 'q', '"'))
        if b >= 0: cand.append((b, 'q', "'"))
        if c >= 0: cand.append((c, 'q', '`'))
        if d1 >= 0: cand.append((d1, 's', '//'))
        if d2 >= 0: cand.append((d2, 's', '/*'))
        if f >= 0: cand.append((f, 's', '/'))
        if not cand:
            return
        cand.sort()
        p, kind, val = cand[0]
        if kind == 's':
            if val == '//' or val == '/*':
                # '//' and '/*' always start a comment in JS (a regex can
                # never start with '//' or '/*')
                if val == '//':
                    k = text.find('\n', p)
                    i = n if k < 0 else k + 1
                else:
                    k = text.find('*/', p + 2)
                    i = n if k < 0 else k + 2
                continue
            else:
                # single '/': skip regex literals so their closing '/' isn't
                # re-examined and quotes inside them (e.g. /["']/) aren't
                # mistaken for string starts
                if _looks_like_regex(text, p):
                    i = _scan_regex(text, p)
                    continue
                i = p + 1
                continue
        # check escaped quote
        bs = 0
        k = p - 1
        while k >= 0 and text[k] == '\\':
            bs += 1
            k -= 1
        if bs % 2 == 1:
            i = p + 1
            continue
        if val == '`':
            e = _scan_template(text, p)
        else:
            e = _scan_quoted(text, p, val)
        if e is None:
            i = p + 1
            continue
        yield (p, e, text[p:e])
        i = e

ESC = {'n': '\n', 't': '\t', 'r': '\r', 'b': '\b', 'f': '\f', 'v': '\v', '0': '\0'}

def js_unescape(s):
    out, i = [], 0
    while i < len(s):
        c = s[i]
        if c == '\\' and i + 1 < len(s):
            n = s[i + 1]
            if n in ESC:
                out.append(ESC[n]); i += 2; continue
            if n == 'u':
                h = s[i+2:i+6]
                if len(h) == 4 and all(x in '0123456789abcdefABCDEF' for x in h):
                    out.append(chr(int(h, 16))); i += 6; continue
            if n == 'x':
                h = s[i+2:i+4]
                if len(h) == 2 and all(x in '0123456789abcdefABCDEF' for x in h):
                    out.append(chr(int(h, 16))); i += 4; continue
            out.append(n); i += 2; continue
        out.append(c); i += 1
    return ''.join(out)

def js_escape(s, q):
    # escape for embedding inside quote char q
    s = s.replace('\\', '\\\\')
    if q == '"': s = s.replace('"', '\\"')
    elif q == "'": s = s.replace("'", "\\'")
    elif q == '`': s = s.replace('`', '\\`').replace('$', '\\$')
    return s.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')

def dangerous(text, start, end, s):
    before = text[max(0, start - 60):start]
    after = text[end:end + 10]
    esc = re.escape(s)
    # [x.Member=0]="Member"  (TS enum reverse map)
    if re.search(r'\[\s*[\w$]+\.' + esc + r'\s*=', before): return 'enum-rev'
    # x.Member="Member"  (prop assignment, name == value)
    if re.search(r'\.\s*' + esc + r'\s*=\s*$', before): return 'prop-assign'
    # {Member:"Member"}  (object literal, key == value)
    if re.search(r'[{,]\s*' + esc + r'\s*:\s*$', before): return 'obj-key'
    # case"Member"
    if re.search(r'\bcase\s*$', before): return 'case'
    # .key==="Member"
    if re.search(r'\.key\s*(===|!==|==|!=)\s*$', before): return 'key-cmp'
    # hr("Member")  (hostElement registration)
    if re.search(r'\bhr\($', before) and after.startswith(')'): return 'host-element'
    return None

def patch_file(path, mapping, stats, allow_getnextname=True):
    text = open(path, encoding='utf-8', errors='replace').read()
    out = []
    pos = 0
    replaced = skipped = 0
    for s, e, raw in iter_literals(text):
        q = raw[0]
        # template literals with placeholders: consume as opaque, never translate
        if q == '`' and '${' in raw:
            continue
        logical = js_unescape(raw[1:-1])
        if logical not in mapping:
            continue
        reason = dangerous(text, s, e, logical)
        if reason:
            skipped += 1
            stats['skipped_reasons'][reason] = stats['skipped_reasons'].get(reason, 0) + 1
            continue
        # getNextName override: ad("Group") etc. (ad may have earlier args)
        before = text[max(0, s - 24):s]
        after = text[e:e + 2]
        zh = mapping[logical]
        if allow_getnextname and re.search(r'\bad\([^()]*$', before) and after.startswith(')'):
            key = ('ad', logical)
            if key in OVERRIDES:
                zh = OVERRIDES[key]
                stats['overrides'] += 1
        new_raw = q + js_escape(zh, q) + q
        out.append(text[pos:s])
        out.append(new_raw)
        pos = e
        replaced += 1
        stats['replaced_keys'].add(logical)
    out.append(text[pos:])
    open(path, 'w', encoding='utf-8').write(''.join(out))
    return replaced, skipped

def main():
    stats = {'skipped_reasons': {}, 'replaced_keys': set(), 'overrides': 0}
    renderer_files = [
        os.path.join(APP, 'web/assets/index-aZSYMEsA.js'),
        os.path.join(APP, 'web/assets/index-DXSZDER1.js'),
        os.path.join(APP, 'web/assets/index-CK89WP--.js'),
    ]
    total_r = total_s = 0
    for f in renderer_files:
        r, sk = patch_file(f, DICT, stats)
        total_r += r; total_s += sk
        print(f'{os.path.basename(f)}: replaced={r} skipped={sk}')
    main_js = os.path.join(APP, 'dist/main.js')
    t = open(main_js, encoding='utf-8').read()
    mr = 0
    for old, new in MAIN_REPLACEMENTS:
        c = t.count(old)
        if c:
            t = t.replace(old, new)
            mr += c
        else:
            print(f'main.js: WARNING not found: {old[:50]!r}')
    open(main_js, 'w', encoding='utf-8').write(t)
    print(f'main.js (targeted): replaced={mr}')
    # disable auto-updater
    t = open(main_js, encoding='utf-8').read()
    t2, n = UPDATER_RE.subn('void 0;', t)
    if n:
        open(main_js, 'w', encoding='utf-8').write(t2)
        print(f'main.js: updater disabled ({n} call site)')
    else:
        print('main.js: WARNING updater call site not found!')
    # index.html lang
    idx = os.path.join(APP, 'web/index.html')
    h = open(idx, encoding='utf-8').read()
    h = h.replace('<html lang="en">', '<html lang="zh-CN">')
    open(idx, 'w', encoding='utf-8').write(h)
    print('index.html: lang -> zh-CN')
    print('skip reasons:', stats['skipped_reasons'])
    print('getNextName overrides:', stats['overrides'])
    print('unique keys replaced:', len(stats['replaced_keys']), '/', len(DICT))
    missing = [k for k in DICT if k not in stats['replaced_keys']]
    print('keys not found in bundles:', len(missing))
    json.dump(sorted(missing), open(os.path.join(WORK, 'unmatched.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)

if __name__ == '__main__':
    main()
