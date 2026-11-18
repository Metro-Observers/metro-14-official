#!/usr/bin/env python3
"""Metro-14 RSI / prototype validator (stdlib only).

Usage: python Tools/_Metro14/validate_rsi.py [paths...]
Default: all *.rsi under Resources/Textures/_Metro14 and all *.yml under
Resources/Prototypes/_Metro14. Exit 1 if any ERROR.

Engine rules mirrored (RobustToolbox/Robust.Shared/Resources/RsiLoading.cs):
 - directions must be 1/4/8; len(delays) must equal directions (L68-95)
 - empty delay list counts as 1 frame; frames = sum(len(d) for d in delays) (L97-104, L144-155)
 - PNG size must be a multiple of size (L181-186)
 - source frames are read row-major with columns = w/size.x (L234-237);
   atlas uses ceil(sqrt(total)) columns (L216). Metro-14 convention: source
   PNG columns must equal ceil(sqrt(frames)) (so 4-dir = 2x2, not 4x1).
"""
import json
import math
import os
import re
import struct
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
TEX = os.path.join(REPO, "Resources", "Textures")
TEX_M14 = os.path.join(TEX, "_Metro14")
PROTO_M14 = os.path.join(REPO, "Resources", "Prototypes", "_Metro14")

errors = []
warns = []


def rel(p):
    try:
        return os.path.relpath(p, REPO).replace("\\", "/")
    except ValueError:
        return p


def err(p, msg):
    r = rel(p)
    errors.append(f"ERROR {msg}" if msg.startswith(r + ":") else f"ERROR {r}: {msg}")


def warn(p, msg):
    r = rel(p)
    warns.append(f"WARN {msg}" if msg.startswith(r + ":") else f"WARN {r}: {msg}")


def read_text(p):
    with open(p, "r", encoding="utf-8-sig") as f:
        return f.read()


def png_size(p):
    try:
        from PIL import Image  # optional
        with Image.open(p) as im:
            return im.size
    except ImportError:
        pass
    except Exception as e:
        raise ValueError(f"cannot open PNG: {e}")
    with open(p, "rb") as f:
        head = f.read(24)
    if len(head) < 24 or head[:8] != b"\x89PNG\r\n\x1a\n" or head[12:16] != b"IHDR":
        raise ValueError("not a valid PNG (bad signature/IHDR)")
    return struct.unpack(">II", head[16:24])


def png_pixels(p):
    """Decode 8-bit non-interlaced PNG -> (w, h, list of RGBA tuples). Stdlib only."""
    import zlib
    with open(p, "rb") as f:
        data = f.read()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG")
    pos, idat, plte, trns = 8, [], None, None
    w = h = bd = ct = il = None
    while pos < len(data):
        ln, typ = struct.unpack(">I4s", data[pos:pos + 8])
        chunk = data[pos + 8:pos + 8 + ln]
        pos += 12 + ln
        if typ == b"IHDR":
            w, h, bd, ct, _, _, il = struct.unpack(">IIBBBBB", chunk)
        elif typ == b"PLTE":
            plte = chunk
        elif typ == b"tRNS":
            trns = chunk
        elif typ == b"IDAT":
            idat.append(chunk)
        elif typ == b"IEND":
            break
    if bd != 8 or il != 0 or ct not in (0, 2, 3, 4, 6):
        raise NotImplementedError(f"unsupported PNG (bitdepth={bd}, colortype={ct}, interlace={il})")
    bpp = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[ct]
    raw = zlib.decompress(b"".join(idat))
    stride = w * bpp
    prev = bytearray(stride)
    out = []
    i = 0
    for _ in range(h):
        ft = raw[i]
        line = bytearray(raw[i + 1:i + 1 + stride])
        i += 1 + stride
        if ft == 1:
            for x in range(bpp, stride):
                line[x] = (line[x] + line[x - bpp]) & 255
        elif ft == 2:
            for x in range(stride):
                line[x] = (line[x] + prev[x]) & 255
        elif ft == 3:
            for x in range(stride):
                a = line[x - bpp] if x >= bpp else 0
                line[x] = (line[x] + ((a + prev[x]) >> 1)) & 255
        elif ft == 4:
            for x in range(stride):
                a = line[x - bpp] if x >= bpp else 0
                b = prev[x]
                c = prev[x - bpp] if x >= bpp else 0
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                pr = a if pa <= pb and pa <= pc else (b if pb <= pc else c)
                line[x] = (line[x] + pr) & 255
        elif ft != 0:
            raise ValueError(f"bad filter type {ft}")
        if ct == 6:
            out.extend(zip(line[0::4], line[1::4], line[2::4], line[3::4]))
        elif ct == 2:
            tk = struct.unpack(">HHH", trns) if trns and len(trns) == 6 else None
            for x in range(0, stride, 3):
                r, g, b = line[x], line[x + 1], line[x + 2]
                out.append((r, g, b, 0 if tk == (r, g, b) else 255))
        elif ct == 3:
            for v in line:
                a = trns[v] if trns and v < len(trns) else 255
                out.append((plte[3 * v], plte[3 * v + 1], plte[3 * v + 2], a))
        elif ct == 4:
            out.extend((g, g, g, a) for g, a in zip(line[0::2], line[1::2]))
        else:
            tk = struct.unpack(">H", trns)[0] if trns and len(trns) == 2 else None
            out.extend((g, g, g, 0 if g == tk else 255) for g in line)
        prev = line
    return w, h, out


def color_limit(sx, sy):
    """Per-state WARN threshold from Tools/_Metro14/style/STYLE_GUIDE.md section 1."""
    m = max(sx, sy)
    if m <= 32:
        return 16
    if m <= 64:
        return 30
    return 300


COLOR_ERROR = 2048  # gross photo/blur-level palette -> ERROR


SEMI_MAX_FRACTION = 0.02  # STYLE_GUIDE gives no number -> default 2% of visible pixels
SEMI_STATE_PATTERNS = ("glass", "window", "shadow", "light", "lit", "glow", "overlay", "unshaded", "emissive")
_whitelist = None


def load_whitelist():
    """Tools/_Metro14/rsi_whitelist.txt: one entry per line, '#' comments.
    Entry = RSI path relative to Resources/Textures (whole RSI) or '<rsi>/<state>'; fnmatch globs allowed."""
    global _whitelist
    if _whitelist is None:
        _whitelist = []
        wp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rsi_whitelist.txt")
        if os.path.isfile(wp):
            for line in read_text(wp).splitlines():
                line = line.split("#", 1)[0].strip().replace("\\", "/").strip("/")
                if line:
                    _whitelist.append(line)
    return _whitelist


def is_whitelisted(png, name):
    import fnmatch
    low = name.lower()
    if any(pat in low for pat in SEMI_STATE_PATTERNS):
        return True
    rsi = os.path.dirname(os.path.abspath(png))
    try:
        rp = os.path.relpath(rsi, TEX).replace("\\", "/")
    except ValueError:
        rp = rsi.replace("\\", "/")
    for e in load_whitelist():
        if fnmatch.fnmatch(rp, e) or fnmatch.fnmatch(f"{rp}/{name}", e):
            return True
    return False


def check_style(png, name, sx, sy):
    try:
        try:
            from PIL import Image
            with Image.open(png) as im:
                b = im.convert("RGBA").tobytes()
                px = list(zip(b[0::4], b[1::4], b[2::4], b[3::4]))
        except ImportError:
            px = png_pixels(png)[2]
    except NotImplementedError as e:
        warn(png, f"style check skipped: {e}")
        return
    except Exception as e:
        err(png, f"cannot decode pixels: {e}")
        return
    colors = len({p for p in px if p[3] != 0})
    semi = sum(1 for p in px if 0 < p[3] < 255)
    lim = color_limit(sx, sy)
    if semi:
        visible = sum(1 for p in px if p[3] != 0) or 1
        frac = semi / visible
        if frac > SEMI_MAX_FRACTION:
            msg = (f"state '{name}': {semi} semi-transparent pixels = {frac:.1%} of visible "
                   f"(limit {SEMI_MAX_FRACTION:.0%}; allowed only for glass/shadow/light/overlay)")
            if is_whitelisted(png, name):
                warn(png, msg + " [whitelisted]")
            else:
                err(png, msg)
    if colors > COLOR_ERROR:
        err(png, f"state '{name}': {colors} unique colors (> {COLOR_ERROR}; guide limit ~{lim} for {sx}x{sy})")
    elif colors > lim:
        warn(png, f"state '{name}': {colors} unique colors (STYLE_GUIDE limit ~{lim} for {sx}x{sy})")


# ---------------------------------------------------------------- RSI
_rsi_cache = {}


def load_meta(rsi):
    """Return dict state->directions, or None if meta unreadable (no reporting)."""
    if rsi in _rsi_cache:
        return _rsi_cache[rsi]
    res = None
    mp = os.path.join(rsi, "meta.json")
    try:
        meta = json.loads(read_text(mp))
        res = {}
        for s in meta.get("states") or []:
            if isinstance(s, dict) and "name" in s:
                res[s["name"]] = s.get("directions", 1)
    except Exception:
        res = None
    _rsi_cache[rsi] = res
    return res


def check_rsi(rsi):
    mp = os.path.join(rsi, "meta.json")
    if not os.path.isfile(mp):
        err(rsi, "missing meta.json")
        return
    try:
        meta = json.loads(read_text(mp))
    except Exception as e:
        err(mp, f"meta.json does not parse: {e}")
        return
    if not isinstance(meta, dict):
        err(mp, "meta.json root is not an object")
        return
    for k in ("version", "license", "copyright"):
        if k not in meta:
            err(mp, f"missing '{k}'")
    size = meta.get("size")
    sx = sy = None
    if isinstance(size, dict) and isinstance(size.get("x"), int) and isinstance(size.get("y"), int) \
            and size["x"] > 0 and size["y"] > 0:
        sx, sy = size["x"], size["y"]
    else:
        err(mp, "missing/invalid size.x/size.y")
    states = meta.get("states")
    if not isinstance(states, list):
        err(mp, "missing 'states' list")
        return
    names = set()
    for st in states:
        if not isinstance(st, dict) or not isinstance(st.get("name"), str):
            err(mp, f"state without name: {st!r}")
            continue
        name = st["name"]
        if name in names:
            err(mp, f"duplicate state '{name}'")
        names.add(name)
        dirs = st.get("directions", 1)
        if dirs not in (1, 4, 8):
            err(mp, f"state '{name}': directions={dirs}, must be 1, 4 or 8")
            continue
        delays = st.get("delays")
        if delays is not None:
            if not isinstance(delays, list) or len(delays) != dirs:
                err(mp, f"state '{name}': delays has {len(delays) if isinstance(delays, list) else '?'} lists, directions={dirs}")
                continue
            required = sum(max(1, len(d) if isinstance(d, list) else 1) for d in delays)
        else:
            required = dirs
        png = os.path.join(rsi, name + ".png")
        if not os.path.isfile(png):
            err(rsi, f"state '{name}' has no {name}.png")
            continue
        if sx is None:
            continue
        try:
            w, h = png_size(png)
        except Exception as e:
            err(png, str(e))
            continue
        if w % sx or h % sy:
            err(png, f"size {w}x{h} not a multiple of {sx}x{sy}")
            continue
        check_style(png, name, sx, sy)
        cols, rows = w // sx, h // sy
        frames = cols * rows
        if frames < required:
            err(png, f"has {frames} frames ({cols}x{rows}), state '{name}' needs {required} (dirs={dirs})")
            continue
        exp_cols = math.ceil(math.sqrt(required))
        if cols != exp_cols:
            animated = required > dirs
            (err if (dirs in (4, 8) and not animated) else warn)(png, f"layout {cols}x{rows} frames; expected {exp_cols} columns for {required} frames "
                     f"(row-major grid, cols=ceil(sqrt(n)), e.g. 4 frames = 2x2)")
    for f in os.listdir(rsi):
        if f.lower().endswith(".png") and f[:-4] not in names:
            warn(os.path.join(rsi, f), "PNG has no matching state in meta.json")


# ---------------------------------------------------------------- YAML
def strip_comment(s):
    out, q = [], None
    for i, c in enumerate(s):
        if q:
            if c == q:
                q = None
        elif c in "'\"":
            q = c
        elif c == "#" and (i == 0 or s[i - 1] in " \t"):
            break
        out.append(c)
    return "".join(out).rstrip()


def scalar(v):
    v = v.strip()
    if v.startswith("!"):
        parts = v.split(None, 1)
        v = parts[1] if len(parts) > 1 else ""
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"":
        v = v[1:-1]
    return v


def parse_flow_list(v):
    v = v.strip()
    if v.startswith("[") and v.endswith("]"):
        return [scalar(x) for x in v[1:-1].split(",") if x.strip()]
    return [scalar(v)] if v else []


def parse_entities(path):
    """Line-based tolerant parser. Returns list of entity dicts:
    {id, parents, line, comps: [{type, line, fields{}, layers:[{sprite,state,line}]}]}"""
    try:
        lines = read_text(path).splitlines()
    except Exception as e:
        err(path, f"cannot read: {e}")
        return []
    ents = []
    cur = None
    i = 0
    n = len(lines)
    while i < n:
        raw = strip_comment(lines[i])
        if not raw.strip():
            i += 1
            continue
        ind = len(raw) - len(raw.lstrip())
        txt = raw.strip()
        if ind == 0 and txt.startswith("- "):
            cur = None
            m = re.match(r"-\s+type:\s*(\S+)", txt)
            if m and scalar(m.group(1)) == "entity":
                cur = {"id": None, "parents": [], "line": i + 1, "comps": [], "file": path}
                ents.append(cur)
            i += 1
            continue
        if cur is None:
            i += 1
            continue
        m = re.match(r"(\w+):\s*(.*)$", txt)
        if m and ind <= 2:
            k, v = m.group(1), m.group(2)
            if k == "id":
                cur["id"] = scalar(v)
            elif k == "parent":
                if v.strip():
                    cur["parents"] = parse_flow_list(v)
                else:
                    j = i + 1
                    while j < n and strip_comment(lines[j]).strip().startswith("- "):
                        cur["parents"].append(scalar(strip_comment(lines[j]).strip()[2:]))
                        j += 1
            elif k == "components":
                i = parse_components(lines, i + 1, ind, cur)
                continue
        i += 1
    return ents


def parse_components(lines, i, base_ind, ent):
    n = len(lines)
    comp = None
    comp_ind = None
    in_layers = None  # indent of 'layers:' key
    layer = None
    while i < n:
        raw = strip_comment(lines[i])
        if not raw.strip():
            i += 1
            continue
        ind = len(raw) - len(raw.lstrip())
        txt = raw.strip()
        if ind < base_ind or (ind == base_ind and not txt.startswith("- ")) or (ind == 0):
            break
        m = re.match(r"-\s+type:\s*(\S+)", txt)
        if m and (comp_ind is None or ind <= comp_ind):
            comp_ind = ind
            comp = {"type": scalar(m.group(1)), "line": i + 1, "fields": {}, "layers": []}
            ent["comps"].append(comp)
            in_layers = None
            layer = None
            i += 1
            continue
        if comp is None:
            i += 1
            continue
        if in_layers is not None:
            if ind < in_layers or (ind == in_layers and not txt.startswith("- ")):
                in_layers = None
                layer = None
            else:
                body = txt
                if txt.startswith("- "):
                    layer = {"line": i + 1}
                    comp["layers"].append(layer)
                    body = txt[2:].strip()
                lm = re.match(r"(\w+):\s*(.*)$", body)
                if lm and layer is not None and lm.group(1) in ("sprite", "state", "rsi"):
                    key = "sprite" if lm.group(1) == "rsi" else lm.group(1)
                    if lm.group(2).strip():
                        layer[key] = scalar(lm.group(2))
                i += 1
                continue
        fm = re.match(r"(\w+):\s*(.*)$", txt)
        if fm and ind == comp_ind + 2:
            k, v = fm.group(1), fm.group(2)
            if k == "layers":
                in_layers = ind
            elif v.strip():
                comp["fields"][k] = (scalar(v), i + 1)
        i += 1
    return i


def resolve_rsi(sprite):
    p = os.path.join(TEX, sprite.replace("/", os.sep))
    return p if os.path.isdir(p) and os.path.isfile(os.path.join(p, "meta.json")) else None


def check_entities(ents, all_by_id):
    def inherited_sprite(ent, comp_type, seen):
        for pid in ent["parents"]:
            if pid in seen:
                continue
            seen.add(pid)
            p = all_by_id.get(pid)
            if not p:
                return None, True
            for c in p["comps"]:
                if c["type"] == comp_type and "sprite" in c["fields"]:
                    return c["fields"]["sprite"][0], False
            s, unknown = inherited_sprite(p, comp_type, seen)
            if s or unknown:
                return s, unknown
        return None, False

    for ent in ents:
        eid = ent["id"] or f"<entity@{ent['line']}>"
        loc = f"{ent['file']}"
        for c in ent["comps"]:
            if c["type"] not in ("Sprite", "Icon"):
                continue
            where = lambda ln: f"{rel(loc)}:{ln} [{eid}/{c['type']}]"
            sprite = c["fields"].get("sprite", (None,))[0]
            spline = c["fields"].get("sprite", (None, c["line"]))[1]
            inherited = False
            if sprite is None:
                sprite, _ = inherited_sprite(ent, c["type"], set())
                inherited = sprite is not None
            rsi = None
            if sprite:
                rsi = resolve_rsi(sprite)
                if not rsi:
                    (warn if inherited else err)(loc, f"{where(spline)}: sprite '{sprite}' -> no RSI at Resources/Textures/{sprite}")
            refs = []  # (rsi, state, line, label)
            if "state" in c["fields"]:
                st, ln = c["fields"]["state"]
                if not sprite:
                    warn(loc, f"{where(ln)}: state '{st}' but sprite unresolvable (not set, parent chain unknown)")
                elif rsi:
                    refs.append((rsi, sprite, st, ln))
            for L in c["layers"]:
                if "state" not in L:
                    if "sprite" in L and not resolve_rsi(L["sprite"]):
                        err(loc, f"{where(L['line'])}: layer sprite '{L['sprite']}' -> no RSI")
                    continue
                ls = L.get("sprite") or sprite
                if not ls:
                    warn(loc, f"{where(L['line'])}: layer state '{L['state']}' but sprite unresolvable")
                    continue
                lr = resolve_rsi(ls)
                if not lr:
                    if L.get("sprite"):
                        err(loc, f"{where(L['line'])}: layer sprite '{ls}' -> no RSI")
                    continue
                refs.append((lr, ls, L["state"], L["line"]))
            snap = c["fields"].get("snapCardinals", ("false",))[0].lower() == "true"
            for r, sp, st, ln in refs:
                meta = load_meta(r)
                if meta is None:
                    err(loc, f"{where(ln)}: RSI '{sp}' has unreadable meta.json")
                    continue
                if st not in meta:
                    err(loc, f"{where(ln)}: state '{st}' not found in '{sp}'")
                    continue
                d = meta[st]
                if c["type"] == "Sprite" and snap and d != 1:
                    err(loc, f"{where(ln)}: snapCardinals: true but state '{st}' in '{sp}' has directions={d} (must be 1; trips DebugAssert in SpriteSystem.Bounds)")
                if c["type"] == "Icon" and d != 1:
                    warn(loc, f"{where(ln)}: Icon state '{st}' has directions={d}; GetIcon uses Frame0 (south only)")


# ---------------------------------------------------------------- main
def find_rsis(root):
    out = []
    for dp, dns, _ in os.walk(root):
        for d in list(dns):
            if d.endswith(".rsi"):
                out.append(os.path.join(dp, d))
                dns.remove(d)
    return sorted(out)


def find_ymls(root):
    return sorted(os.path.join(dp, f) for dp, _, fs in os.walk(root) for f in fs if f.endswith((".yml", ".yaml")))


def main(argv):
    rsis, ymls = [], []
    if argv:
        for a in argv:
            p = os.path.abspath(a)
            if os.path.isdir(p) and p.rstrip("\\/").endswith(".rsi"):
                rsis.append(p)
            elif os.path.isdir(p):
                rsis += find_rsis(p)
                ymls += find_ymls(p)
            elif os.path.isfile(p) and p.endswith((".yml", ".yaml")):
                ymls.append(p)
            else:
                err(p, "not an .rsi folder, .yml file or directory")
    else:
        rsis = find_rsis(TEX_M14)
        ymls = find_ymls(PROTO_M14)

    for r in rsis:
        check_rsi(r)

    # parent lookup: always index all Metro14 prototypes + the targeted files
    index_files = set(find_ymls(PROTO_M14)) | set(ymls)
    by_id = {}
    parsed = {}
    for f in index_files:
        ents = parse_entities(f)
        parsed[f] = ents
        for e in ents:
            if e["id"]:
                by_id.setdefault(e["id"], e)
    for f in ymls:
        check_entities(parsed[f], by_id)

    for line in errors + warns:
        print(line)
    print(f"\nChecked {len(rsis)} RSI, {len(ymls)} YAML: {len(errors)} error(s), {len(warns)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    sys.exit(main(sys.argv[1:]))
