#!/usr/bin/env python3
"""PDK-free CI guard: re-derive design/row5-error-budget.md from the committed records.

Every numeric table cell of sections 3, 4, 5, 6, 7 (extrapolation table) and 8
of design/row5-error-budget.md is mechanically derivable from the three records
the note's own section 1 provenance table names. This guard reads those record
paths from section 1 (never hardcoded), re-derives each cell, and compares on
the half-digit rule: a cell passes iff |derived - cell| < 0.5*10^-decimals + 1e-9,
where decimals is the cell's own display precision. The note rounds half-up;
Python's round() is half-even, so no rounding function is used -- the tolerance
rule discriminates a correctly rounded cell from a wrong last digit.

Fails closed (`.loom/docs/ci-principles.md`): a record path section 1 names that
does not exist, a record field whose name changed, a section heading, table,
row or prose anchor the parser cannot locate -- each exits non-zero naming the
reason. Never "0 cells checked, OK".

sim/ is append-only; this guard only reads it.
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
NOTE_REL = "design/row5-error-budget.md"
LEVELS = [0, 1, 2, 3]
CORNERS = ["tt", "ss", "ff", "sf", "fs", "mc"]  # table keys: tt_mm..fs_mm, mc
BAND = 27.0  # spec row 5, +/-27 mV at 3 sigma, untrimmed
SUP_LO = 3.3  # nominal detector supply, V
SUP_DROOP = 2.97  # drooped detector supply, V
SUP_HI = 3.63  # extrapolated supply corner, V

failures = []
checks = 0


def die(msg):
    sys.exit("check_row5_budget: FAIL-CLOSED: " + msg)


def fail(where, msg):
    failures.append("%s: %s" % (where, msg))


def read_file(rel):
    p = ROOT / rel
    if not p.is_file():
        die("file not found: %s" % rel)
    return p.read_text()


def norm(s):
    # the note typesets minus as U+2212; normalize so number parsing is ASCII
    return s.replace("\u2212", "-").replace("\u00a0", " ")


NUM = re.compile(r"[-+]?\d[\d,]*(?:\.\d+)?")


def first_number(cell):
    m = NUM.search(norm(cell))
    if not m:
        return None
    tok = m.group(0).replace(",", "")
    dec = len(tok.split(".")[1]) if "." in tok else 0
    return float(tok), dec


def check(where, cell, derived):
    global checks
    got = first_number(cell)
    if got is None:
        fail(where, "no number found in cell %r" % cell)
        return
    checks += 1
    value, dec = got
    tol = 0.5 * 10 ** -dec + 1e-9
    if abs(derived - value) >= tol:
        fail(where, "cell reads %.*f, derived %.6f (delta %+.6f, tolerance %g)"
             % (dec, value, derived, derived - value, tol))


def check_anchor(where, text, pattern, derived_list):
    """Regex-anchored prose figures: every capture group of every match maps,
    in order, to one expected derived value; fail closed if absent."""
    global checks
    text = " ".join(text.split())  # markdown reflows; anchors must not care
    ms = re.findall(pattern, text)
    if not ms:
        die("prose anchor not found in %s (note wording changed?): %r" % (where, pattern))
    groups = []
    for m in ms:
        groups.extend(m if isinstance(m, tuple) else [m])
    if len(groups) != len(derived_list):
        die("expected %d figure(s) from %r in %s, found %d"
            % (len(derived_list), pattern, where, len(groups)))
    for tok, derived in zip(groups, derived_list):
        value = float(tok)
        dec = len(tok.split(".")[1]) if "." in tok else 0
        checks += 1
        tol = 0.5 * 10 ** -dec + 1e-9
        if abs(derived - value) >= tol:
            fail(where, "prose figure %.*f, derived %.6f (delta %+.6f, tolerance %g)"
                 % (dec, value, derived, derived - value, tol))


# ---------------------------------------------------------------- note parsing

def load_note():
    return norm(read_file(NOTE_REL))


def provenance_paths(note):
    """Record paths from the section 1 provenance table, keyed by bench."""
    paths = re.findall(r"^\|\s*`?(sim/[^|`\s]+)`?\s*\|", note, re.M)
    keyed = {}
    for p in paths:
        bench = ("tb_ref_droop" if "tb_ref_droop" in p
                 else "tb_threshold_mc" if "tb_threshold_mc" in p
                 else "tb_threshold_accuracy" if "tb_threshold_accuracy" in p
                 else None)
        if bench is None:
            continue
        if bench in keyed:
            die("section 1 provenance table lists two %s records (%s, %s); ambiguous"
                % (bench, keyed[bench], p))
        keyed[bench] = p
    for bench in ("tb_ref_droop", "tb_threshold_mc", "tb_threshold_accuracy"):
        if bench not in keyed:
            die("section 1 provenance table: no %s record found (found: %s)"
                % (bench, paths))
    return keyed


def section(note, num):
    m = re.search(r"^## %d\. (.+)$" % num, note, re.M)
    if not m:
        die("note heading '## %d.' not found" % num)
    start = m.end()
    nxt = re.search(r"^## \d+\.", note[start:], re.M)
    return note[start:start + nxt.start()] if nxt else note[start:]


def md_tables(sec_text):
    out, cur = [], None
    for line in sec_text.splitlines():
        s = line.strip()
        if s.startswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if set("".join(cells)) <= set("-: "):
                continue  # separator row
            cur = [] if cur is None else cur
            cur.append(cells)
        elif cur is not None:
            out.append(cur)
            cur = None
    if cur is not None:
        out.append(cur)
    return out


def find_table(num, sec_text, header_sub):
    for t in md_tables(sec_text):
        if header_sub in norm(t[0][0]) or any(header_sub in norm(h) for h in t[0]):
            return t
    die("section %d: no table with header containing %r" % (num, header_sub))


def col(table, header_sub):
    for i, h in enumerate(table[0]):
        if header_sub in norm(h):
            return i
    die("table header %r has no column containing %r" % (table[0], header_sub))


def row(table, key):
    for r in table[1:]:
        if norm(r[0]).replace("`", "").replace("**", "").strip().startswith(key):
            return r
    die("table %r has no row starting with %r" % (table[0], key))


# ------------------------------------------------------------- record parsing

def parse_ref(text):
    """tb_ref_droop: nominal and 2.97 V level blocks -> level -> (vtrip, nominal, delta)."""
    sections, cur = {}, None
    for line in text.splitlines():
        m = re.match(r"\s*levels (.+?):\s*$", line)
        if m:
            cur = m.group(1)
            continue
        m = re.match(r"\s*vtrip_l(\d) = ([0-9.]+) V; nominal ([0-9.]+) V;"
                     r" delta ([+-][0-9.]+) mV", line)
        if m and cur is not None:
            sections.setdefault(cur, {})[int(m.group(1))] = (
                float(m.group(2)), float(m.group(3)), float(m.group(4)))
    nom = sup = None
    for name, lv in sections.items():
        if name.startswith("at nominal"):
            nom = lv
        elif "2.97" in name:
            sup = lv
    if nom is None or sup is None:
        die("tb_ref_droop record: 'levels at nominal' / 'levels with detector"
            " supply at 2.97 V' blocks not found (field rename?)")
    for lv in (nom, sup):
        if sorted(lv) != LEVELS:
            die("tb_ref_droop record: expected levels l0..l3, got %s" % sorted(lv))
    return nom, sup


def parse_mc(text):
    """tb_threshold_mc: monte_carlo JSON header + per-section mean/sd lines."""
    m = re.search(r"^monte_carlo: (\{.*\})\s*$", text, re.M)
    if not m:
        die("tb_threshold_mc record: 'monte_carlo:' JSON line not found (field rename?)")
    meta = json.loads(m.group(1))
    nominals = meta.get("levels")
    if not isinstance(nominals, list) or len(nominals) != 4:
        die("tb_threshold_mc record: monte_carlo.levels must list 4 level nominals")
    secs = {}
    for m in re.finditer(r"^\s+vtrip_l(\d)_([A-Za-z]+(?:_mm)?): n=\d+ mean=([-\d.eE+]+)"
                         r" sd=([-\d.eE+]+)", text, re.M):
        corner = m.group(2)
        corner = corner[:-3] if corner.endswith("_mm") else corner
        secs[(int(m.group(1)), corner)] = (float(m.group(3)), float(m.group(4)))
    for l in LEVELS:
        for c in CORNERS:
            if (l, c) not in secs:
                die("tb_threshold_mc record: section vtrip_l%d_%s missing"
                    " (mean=/sd= field rename?)" % (l, c))
    return nominals, secs


def parse_acc(text):
    """tb_threshold_accuracy: results block -> level -> delta mV."""
    deltas = {}
    for m in re.finditer(r"^\s+vtrip_l(\d) = ([0-9.]+) V; nominal ([0-9.]+) V;"
                         r" delta ([+-][0-9.]+) mV", text, re.M):
        deltas[int(m.group(1))] = float(m.group(4))
    if sorted(deltas) != LEVELS:
        die("tb_threshold_accuracy record: expected vtrip_l0..l3 delta lines"
            " (field rename?)")
    return deltas


# ------------------------------------------------------------------ derivation

def derive(nominals, mc, ref_nom, ref_sup, acc):
    """All derived figures in mV, keyed the way the note quotes them."""
    dv = {}
    dv["nominal"] = nominals
    for i in LEVELS:
        if abs(ref_nom[i][1] - nominals[i]) > 1e-9:
            die("level l%d nominal disagrees between records: %r vs %r"
                % (i, ref_nom[i][1], nominals[i]))
    dv["a"] = {i: (ref_sup[i][0] - ref_nom[i][0]) * 1000 for i in LEVELS}
    dv["a_pct"] = {i: dv["a"][i] / 1800.0 * 100 for i in LEVELS}
    dv["slope"] = {i: dv["a"][i] / (SUP_DROOP - SUP_LO) for i in LEVELS}
    dv["d"] = {i: (mc[(i, "tt")][0] - nominals[i]) * 1000 for i in LEVELS}
    dv["b"] = {(i, c): (mc[(i, c)][0] - mc[(i, "tt")][0]) * 1000
               for i in LEVELS for c in CORNERS}
    dv["c3"] = {(i, c): 3.0 * mc[(i, c)][1] * 1000
                for i in LEVELS for c in CORNERS}
    dv["acc_delta"] = acc
    dv["ref_delta"] = {i: (ref_nom[i][0] - ref_nom[i][1]) * 1000 for i in LEVELS}
    dv["share"] = {i: dv["acc_delta"][i] - dv["ref_delta"][i] for i in LEVELS}
    dv["share_pct"] = {i: dv["share"][i] / dv["acc_delta"][i] * 100 for i in LEVELS}
    dv["a363"] = {i: dv["slope"][i] * (SUP_HI - SUP_LO) for i in LEVELS}
    dv["edges"] = {}
    for i in LEVELS:
        for c in CORNERS:
            lo33 = dv["d"][i] + dv["b"][(i, c)] - dv["c3"][(i, c)]
            hi33 = dv["d"][i] + dv["b"][(i, c)] + dv["c3"][(i, c)]
            dv["edges"][(i, c)] = {"lo33": lo33, "hi33": hi33,
                                   "lo297": lo33 + dv["a"][i],
                                   "hi297": hi33 + dv["a"][i]}
    dv["binding"] = {}
    for i in LEVELS:
        best = None
        for c in CORNERS:
            for edge, val in dv["edges"][(i, c)].items():
                if best is None or abs(val) > abs(best[3]):
                    sup = "3.3" if edge.endswith("33") else "2.97"
                    name = "lower" if edge.startswith("lo") else "upper"
                    best = (c, sup, name, val)
        dv["binding"][i] = best
    dv["fs_hi363"] = {i: dv["d"][i] + dv["b"][(i, "fs")] + dv["a363"][i]
                      + dv["c3"][(i, "fs")] for i in LEVELS}
    return dv


def ckey(corner):
    return corner if corner == "mc" else corner + "_mm"


# -------------------------------------------------------------------- checking

def check_s3(sec, dv):
    t = find_table(3, sec, "implied slope")
    c_lab, c_a, c_pct, c_s = 0, col(t, "vtrip, 3.3"), col(t, "% of 1.8"), col(t, "implied slope")
    for i in LEVELS:
        r = row(t, "l%d" % i)
        m = re.search(r"\(([0-9.]+) V\)", norm(r[c_lab]))
        if not m:
            die("section 3 table: level label for l%d does not state a nominal"
                " tap voltage: %r" % (i, r[c_lab]))
        check("S3 l%d label" % i, m.group(1) + " V", dv["nominal"][i])
        check("S3 l%d delta_vtrip" % i, r[c_a], dv["a"][i])
        check("S3 l%d pct_of_1v8" % i, r[c_pct], dv["a_pct"][i])
        check("S3 l%d slope" % i, r[c_s], dv["slope"][i])
    check_anchor("S3 prose delta-field quote", sec,
                 r"its `delta` field reads ([+-][0-9.]+) / ([+-][0-9.]+) /"
                 r" ([+-][0-9.]+) / ([+-][0-9.]+) mV",
                 [dv["_ref_sup"][i][2] for i in LEVELS])


def check_s4(sec, dv):
    t1 = find_table(4, sec, "systematic @ tt")
    t2 = find_table(4, sec, "(c) `tt`")
    for i in LEVELS:
        r = row(t1, "l%d" % i)
        check("S4(d) l%d" % i, r[col(t1, "(d)")], dv["d"][i])
        for c in CORNERS[1:]:
            check("S4(b) l%d %s" % (i, c), r[col(t1, "`%s`" % c)], dv["b"][(i, c)])
        r = row(t2, "l%d" % i)
        for c in CORNERS:
            check("S4(c) l%d %s" % (i, c), r[col(t2, "`%s`" % c)], dv["c3"][(i, c)])
    check_anchor("S4 prose accuracy-bench quote", sec,
                 r"It reads \*\*([+-][0-9.]+) / ([+-][0-9.]+) / ([+-][0-9.]+) /"
                 r" ([+-][0-9.]+) mV\*\* at l0",
                 [dv["acc_delta"][i] for i in LEVELS])


def check_s5(sec, dv):
    t1 = find_table(5, sec, "edge lo @3.3")
    c_d, c_b, c_c = col(t1, "(d)"), col(t1, "(b)"), col(t1, "(c)")
    c_l3, c_h3 = col(t1, "edge lo @3.3"), col(t1, "edge hi @3.3")
    c_l2, c_h2 = col(t1, "edge lo @2.97"), col(t1, "edge hi @2.97")
    c_w = col(t1, "worst")
    for c in CORNERS:
        r = row(t1, ckey(c))
        e = dv["edges"][(0, c)]
        b = 0.0 if c == "tt" else dv["b"][(0, c)]
        check("S5 l0 %s (d)" % c, r[c_d], dv["d"][0])
        check("S5 l0 %s (b)" % c, r[c_b], b)
        check("S5 l0 %s (c)" % c, r[c_c], dv["c3"][(0, c)])
        check("S5 l0 %s lo33" % c, r[c_l3], e["lo33"])
        check("S5 l0 %s hi33" % c, r[c_h3], e["hi33"])
        check("S5 l0 %s lo297" % c, r[c_l2], e["lo297"])
        check("S5 l0 %s hi297" % c, r[c_h2], e["hi297"])
        worst = max(abs(v) for v in e.values())
        check("S5 l0 %s worst_ratio" % c, r[c_w], worst / BAND)
    t2 = find_table(5, sec, "binding case")
    c_case, c_edge, c_ratio = col(t2, "binding case"), col(t2, "worst edge"), col(t2, "vs ±27")
    for i in LEVELS:
        r = row(t2, "l%d" % i)
        bc, bsup, bname, bval = dv["binding"][i]
        m = re.match(r"`?([\w]+)`?, ([0-9.]+) V, (upper|lower) edge", norm(r[c_case]))
        if not m:
            die("section 5 binding-case cell unparseable for l%d: %r"
                % (i, r[c_case]))
        checks_done = (m.group(1) == ckey(bc) and float(m.group(2)) == float(bsup)
                       and m.group(3) == bname)
        if not checks_done:
            fail("S5 l%d binding case" % i,
                 "cell names %s %s V %s edge, derived binding case is %s %s V %s edge"
                 % (m.group(1), m.group(2), m.group(3), ckey(bc), bsup, bname))
        check("S5 l%d binding edge" % i, r[c_edge], bval)
        check("S5 l%d binding ratio" % i, r[c_ratio], abs(bval) / BAND)


def check_s6(sec, dv):
    t = find_table(6, sec, "share")
    c_ref, c_full, c_share = col(t, "reference + ladder"), col(t, "full detector"), col(t, "share")
    for i in LEVELS:
        r = row(t, "l%d" % i)
        check("S6 l%d ref_ladder" % i, r[c_ref], dv["ref_delta"][i])
        check("S6 l%d full_detector" % i, r[c_full], dv["acc_delta"][i])
        cell = norm(r[c_share])
        m = re.search(r"\(([0-9.]+) %", cell)
        if not m:
            die("section 6 share cell for l%d lacks '(N %% ...)': %r"
                % (i, r[c_share]))
        check("S6 l%d share" % i, cell, dv["share"][i])
        check("S6 l%d share_pct" % i, m.group(1) + " %", dv["share_pct"][i])


def check_s7(sec, dv):
    t = find_table(7, sec, "(a) @ 3.63")
    c_a, c_edge, c_ratio = col(t, "(a) @ 3.63"), col(t, "upper edge"), col(t, "vs ±27")
    for i in LEVELS:
        r = row(t, "l%d" % i)
        check("S7 l%d a363" % i, r[c_a], dv["a363"][i])
        check("S7 l%d fs_hi363" % i, r[c_edge], dv["fs_hi363"][i])
        check("S7 l%d ratio363" % i, r[c_ratio], dv["fs_hi363"][i] / BAND)


def check_s8(sec, dv):
    tables = [t for t in md_tables(sec) if "remove entirely" in norm(t[0][0])]
    if len(tables) != 2:
        die("section 8: expected 2 'remove entirely' tables, found %d" % len(tables))
    t_low, t_high = None, None
    for t in tables:
        if any(norm(r[0]).startswith("(a)") for r in t[1:]):
            t_low = t
        else:
            t_high = t
    if t_low is None or t_high is None:
        die("section 8: cannot tell the low-edge table (has an '(a)' row) from"
            " the upper-edge table")

    bc, bsup, bname, E = dv["binding"][0]
    if not (bc == "sf" and bsup == "2.97" and bname == "lower"):
        fail("S8 premise", "derived binding case for l0 is %s %s V %s edge, note"
             " assumes sf_mm 2.97 V lower edge" % (ckey(bc), bsup, bname))
    check_anchor("S8 binding-edge prose", sec,
                 r"detector supply 2\.97 V, lower edge ([+-][0-9.]+) mV", [E])
    check_anchor("S8 must-come-out prose", sec,
                 r"bound, \*\*([0-9.]+) mV must come out", [abs(E) - BAND])

    ta, tb, tc, td = dv["a"][0], dv["b"][(0, "sf")], dv["c3"][(0, "sf")], dv["d"][0]
    display = {"(a)": ta, "(b)": tb, "(c)": tc, "(d)": td}  # as the note displays them
    removed = {"(a)": ta, "(b)": tb, "(c)": -tc, "(d)": td}  # signed effect on the edge
    c_rem, c_edge, c_fit = col(t_low, "remove entirely"), col(t_low, "remaining edge"), col(t_low, "fits")
    for key in ("(a)", "(b)", "(c)", "(d)"):
        r = row(t_low, key)
        remaining = E - removed[key]
        check("S8 low %s removed" % key, r[c_rem], display[key])
        check("S8 low %s remaining" % key, r[c_edge], remaining)
        if "worse by" in norm(r[c_fit]):
            check("S8 low %s worse_by" % key, r[c_fit], abs(remaining) - abs(E))
        else:
            check("S8 low %s over_by" % key, r[c_fit], abs(remaining) - BAND)

    U = dv["edges"][(0, "fs")]["hi33"]
    check_anchor("S8 upper-edge prose", sec,
                 r"3\.3 V, \*\*([+-][0-9.]+) mV\*\*, ([0-9.]+) mV to remove",
                 [U, U - BAND])
    removed_hi = {"(b)": dv["b"][(0, "fs")], "(c)": dv["c3"][(0, "fs")], "(d)": dv["d"][0]}
    c_rem2, c_edge2, c_fit2 = col(t_high, "remove entirely"), col(t_high, "remaining edge"), col(t_high, "fits")
    for key in ("(b)", "(c)", "(d)"):
        r = row(t_high, key)
        remaining = U - removed_hi[key]
        check("S8 high %s removed" % key, r[c_rem2], abs(removed_hi[key]))
        check("S8 high %s remaining" % key, r[c_edge2], remaining)
        check("S8 high %s over_by" % key, r[c_fit2], remaining - BAND)

    prose = " ".join(sec.split())  # markdown reflows; anchors must not care
    ks = re.findall(r"k = 27 / ([0-9.]+) = ([0-9.]+)", prose)
    if len(ks) != 2:
        die("section 8: expected two 'k = 27 / …' prose formulas, found %d" % len(ks))
    for (den_cell, k_cell), den in zip(ks, (abs(E), U)):
        check("S8 k denominator", den_cell + " mV", den)
        check("S8 k", k_cell, BAND / den)
    check_anchor("S8 low cut", sec, r"cut by (\d+) %", [100.0 * (1.0 - BAND / abs(E))])
    check_anchor("S8 high cut", sec, r"an (\d+) % cut", [100.0 * (1.0 - BAND / U)])

    c_tt = dv["c3"][(0, "tt")]
    check_anchor("S8 floor band formula", sec,
                 r"\(d\) \+ \(c\) = \+([0-9.]+) ± ([0-9.]+) mV", [dv["d"][0], c_tt])
    check_anchor("S8 floor band edges", sec,
                 r"i\.e\. a ([+-][0-9.]+) … \+([0-9.]+) mV band",
                 [dv["d"][0] - c_tt, dv["d"][0] + c_tt])
    check_anchor("S8 floor ratio", sec, r"still \*\*([0-9.]+)×\*\*",
                 [(dv["d"][0] + c_tt) / BAND])
    check_anchor("S8 mismatch-alone ratio", sec,
                 r"bound — \*\*([0-9.]+)× over", [c_tt / BAND])
    check_anchor("S8 mismatch cut", sec, r"by at least (\d+) %",
                 [100.0 * (1.0 - BAND / c_tt)])


def main():
    note = load_note()
    paths = provenance_paths(note)
    ref_nom, ref_sup = parse_ref(read_file(paths["tb_ref_droop"]))
    nominals, mc = parse_mc(read_file(paths["tb_threshold_mc"]))
    acc = parse_acc(read_file(paths["tb_threshold_accuracy"]))

    dv = derive(nominals, mc, ref_nom, ref_sup, acc)
    dv["_ref_sup"] = ref_sup  # raw 2.97 V block, incl. the record's own delta fields

    check_s3(section(note, 3), dv)
    check_s4(section(note, 4), dv)
    check_s5(section(note, 5), dv)
    check_s6(section(note, 6), dv)
    check_s7(section(note, 7), dv)
    check_s8(section(note, 8), dv)

    if checks < 150:
        die("only %d cells checked; expected on the order of 200 -- the note's"
            " table shape must have changed; refusing to pass" % checks)
    if failures:
        sys.exit("check_row5_budget: %d of %d checked cells DO NOT match the"
                 " committed records:\n  - %s"
                 % (len(failures), checks, "\n  - ".join(failures)))
    print("check_row5_budget: %d cells re-derived from %s and all match"
          % (checks, ", ".join(sorted(paths.values()))))


if __name__ == "__main__":
    main()
