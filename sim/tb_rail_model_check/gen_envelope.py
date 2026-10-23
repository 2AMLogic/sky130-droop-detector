#!/usr/bin/env python3
"""Generate the behavioural-envelope rail bench: envelope.spice + envelope.request.json.

The envelope is an ASSUMPTION (spec/target-spec.md, "Rail model", form 2), not a
measurement. One transient plays every case back to back from a parameterised
PWL (plus gated tones for W2/W3); each case has its own measurement window and
its own bound, so a single `klt sim` unit asserts all of them.

usage: gen_envelope.py OUTDIR [NEGCTL_MV]
  NEGCTL_MV  push the W5 downward spike NEGCTL_MV below the 1.764 V window edge
             (negative control: the bound check must then fail).
"""
import json
import math
import sys

NOM = 1.8
WIN_LO, WIN_HI = 1.764, 1.836          # LDO +-2 % window
BAND = 0.018                            # +-1 % of nominal
LEVELS = {"l4": 1.728, "l6": 1.692, "l9": 1.638, "l12": 1.584}   # row 4 trips
STARTS = {"lo": 1.764, "nom": 1.8, "hi": 1.836}                  # row 6 start points
WIDTHS_NS = (2, 10, 50)                                          # row 7: stretch/target/fallback
SLACK = 1e-6                            # V; below the 6-digit print resolution
GAP = 200e-9


def fmt(x):
    return f"{x:.12g}"


class Pwl:
    def __init__(self):
        self.pts = [(0.0, NOM)]
        self.t = 0.0

    def to(self, t, v):
        assert t >= self.t - 1e-18, (t, self.t)
        self.pts.append((t, v))
        self.t = t

    def ramp(self, dur, v):
        self.to(self.t + dur, v)

    def hold(self, dur):
        self.to(self.t + dur, self.pts[-1][1])

    def level(self):
        return self.pts[-1][1]


def main(outdir, negctl_mv):
    p = Pwl()
    tones = []          # B-source terms
    meas = []           # request measurement entries
    notes = []

    def window(label, t0, t1):
        notes.append(f"* {label}: {fmt(t0)} .. {fmt(t1)} s")

    def m_min(name, a, b, lo=None, hi=None):
        e = {"name": name, "spice": f".meas tran {name} min v(rail) from={fmt(a)} to={fmt(b)}"}
        if lo is not None:
            e["min"] = lo
        if hi is not None:
            e["max"] = hi
        meas.append(e)

    def m_max(name, a, b, lo=None, hi=None):
        e = {"name": name, "spice": f".meas tran {name} max v(rail) from={fmt(a)} to={fmt(b)}"}
        if lo is not None:
            e["min"] = lo
        if hi is not None:
            e["max"] = hi
        meas.append(e)

    def m_pp(name, a, b, lo):
        meas.append({"name": name, "spice": f".meas tran {name} pp v(rail) from={fmt(a)} to={fmt(b)}", "min": lo})

    def rest(dur=GAP):
        p.hold(dur)

    def recovery_expr(a, b):
        def s(x):
            return f"(({x})/(abs({x})+1e-15)+1)/2"
        return (f"vecmax({s('abs(v(rail)-1.8)-0.018')}*{s('time-' + fmt(a))}"
                f"*{s(fmt(b) + '-time')}*(time-{fmt(a)}))*1e6")

    # ---- W1: static levels across the window -------------------------------
    for tag, v in (("lo", WIN_LO), ("nom", NOM), ("hi", WIN_HI)):
        p.ramp(1e-6, v)
        t0 = p.t
        p.hold(1e-6)
        window(f"W1 {tag}", t0, p.t)
        m_min(f"w1_{tag}_vmin", t0, p.t, lo=WIN_LO - SLACK, hi=WIN_HI + SLACK)
        m_max(f"w1_{tag}_vmax", t0, p.t, lo=WIN_LO - SLACK, hi=WIN_HI + SLACK)
    p.ramp(1e-6, NOM)
    rest()

    # ---- W2: +-1 % sinusoid, 1 kHz .. 10 MHz --------------------------------
    for tag, f, cycles in (("1k", 1e3, 1), ("100k", 1e5, 5), ("10m", 1e7, 20)):
        t0 = p.t
        dur = cycles / f
        p.hold(dur)
        tones.append(f"(u(time-{fmt(t0)})-u(time-{fmt(t0 + dur)}))*{BAND}*sin(2*pi*{fmt(f)}*(time-{fmt(t0)}))")
        window(f"W2 {tag}", t0, t0 + dur)
        m_min(f"w2_{tag}_vmin", t0, t0 + dur, lo=WIN_LO - SLACK, hi=WIN_HI + SLACK)
        m_max(f"w2_{tag}_vmax", t0, t0 + dur, lo=WIN_LO - SLACK, hi=WIN_HI + SLACK)
        m_pp(f"w2_{tag}_pp", t0, t0 + dur, 0.034)      # stimulus fidelity: really +-1 %
        rest()

    # ---- W3: bounded pseudo-noise, 16 incommensurate tones -------------------
    t0 = p.t
    dur = 20e-6
    p.hold(dur)
    terms = []
    for k in range(16):
        fk = 2e5 * (100e6 / 2e5) ** (k / 15) * (1 + 0.013 * k)
        ph = (k * 2.399963) % (2 * math.pi)
        terms.append(f"0.0015*sin(2*pi*{fmt(fk)}*(time-{fmt(t0)})+{fmt(ph)})")
    taper = f"sin(pi*(time-{fmt(t0)})/{fmt(dur)})"
    tones.append(f"(u(time-{fmt(t0)})-u(time-{fmt(t0 + dur)}))*{taper}*({'+'.join(terms)})")
    window("W3", t0, t0 + dur)
    m_min("w3_vmin", t0, t0 + dur, lo=WIN_LO - SLACK, hi=WIN_HI + SLACK)
    m_max("w3_vmax", t0, t0 + dur, lo=WIN_LO - SLACK, hi=WIN_HI + SLACK)
    m_pp("w3_pp", t0, t0 + dur, 0.01)                  # stimulus fidelity: noise is present
    rest()

    # ---- W4: slow excursion to the window edge, 1 us edges --------------------
    t0 = p.t
    p.ramp(1e-6, WIN_LO)
    p.hold(5e-6)
    p.ramp(1e-6, NOM)
    t1 = t0 + 60e-6
    p.to(t1, NOM)
    window("W4", t0, t1)
    m_min("w4_vmin", t0, t1, lo=WIN_LO - SLACK, hi=WIN_LO + SLACK)   # reaches the edge, not past it
    m_max("w4_vmax", t0, t1, lo=WIN_LO - SLACK, hi=WIN_HI + SLACK)
    meas.append({"name": "w4_recovery_us", "expr": recovery_expr(t0, t1), "max": 20})
    rest()

    # ---- W5: fast spikes to the window edge, 1 ns edges, 5 ns wide ------------
    for tag, edge_v, extra in (("dn", WIN_LO, negctl_mv * 1e-3), ("up", WIN_HI, 0.0)):
        sign = -1.0 if tag == "dn" else 1.0
        v = edge_v + sign * extra
        half = (NOM + v) / 2
        t0 = p.t
        p.ramp(1e-9, v)
        p.hold(4e-9)                                   # FWHM = 4 ns hold + 1 ns edge = 5 ns
        p.ramp(1e-9, NOM)
        t1 = p.t + 20e-9
        p.to(t1, NOM)
        window(f"W5 {tag}", t0 - 10e-9, t1)
        a, b = t0 - 10e-9, t1
        if tag == "dn":
            m_min("w5_dn_vmin", a, b, lo=WIN_LO - SLACK, hi=WIN_LO + 1e-3)
            m_max("w5_dn_vmax", a, b, lo=WIN_LO - SLACK, hi=WIN_HI + SLACK)
            tr, tt = "fall=1", "rise=1"
        else:
            m_min("w5_up_vmin", a, b, lo=WIN_LO - SLACK, hi=WIN_HI + SLACK)
            m_max("w5_up_vmax", a, b, lo=WIN_HI - 1e-3, hi=WIN_HI + SLACK)
            tr, tt = "rise=1", "fall=1"
        meas.append({"name": f"w5_{tag}_fwhm_s",
                     "spice": (f".meas tran w5_{tag}_fwhm_s trig v(rail) val={fmt(half)} {tr} "
                               f"targ v(rail) val={fmt(half)} {tt} from={fmt(a)} to={fmt(b)}"),
                     "min": 4.9e-9, "max": 5.1e-9})
        rest()

    # ---- LDO-compliant worst-case transient: -150 mV, 1 us edges, <= 20 us ----
    t0 = p.t
    p.ramp(1e-6, NOM - 0.15)
    p.hold(2e-6)
    tau = 4e-6
    tr0 = p.t
    for k in range(1, 81):
        x = 0.5e-6 * k
        p.to(tr0 + x, NOM - 0.15 * math.exp(-x / tau))
    p.to(t0 + 60e-6, NOM)
    t1 = p.t
    window("compliant transient", t0, t1)
    m_min("ct_vmin", t0, t1, lo=NOM - 0.15 - SLACK, hi=NOM - 0.15 + SLACK)   # peak excursion <= 150 mV
    meas.append({"name": "ct_recovery_us", "expr": recovery_expr(t0, t1), "max": 20})
    rest()

    # ---- rows 6 / 7: fast-edge droops to threshold - 100 mV -------------------
    def droop(case, S, L, hold, edge, width_ns=None, ideal=False):
        D = L - 0.1
        p.ramp(1e-6, S)
        p.hold(100e-9)
        t_start = p.t
        p.ramp(edge, D)
        p.hold(hold)
        p.ramp(edge, S)
        t_end = p.t
        p.hold(100e-9)
        a, b = t_start - 5e-9, t_end + 5e-9
        window(case, a, b)
        m_min(f"{case}_vmin", a, b, lo=D - 5e-4, hi=D + 5e-4)     # reaches full overdrive
        if width_ns is None and not ideal:
            dv = S - D
            meas.append({"name": f"{case}_edge_s",
                         "spice": (f".meas tran {case}_edge_s trig v(rail) val={fmt(S - 0.1 * dv)} fall=1 "
                                   f"targ v(rail) val={fmt(S - 0.9 * dv)} fall=1 from={fmt(a)} to={fmt(b)}"),
                         "min": 0.76e-9, "max": 0.84e-9})        # 1 ns linear edge, 10-90 % = 0.8 ns
        if width_ns is not None:
            w = width_ns * 1e-9
            meas.append({"name": f"{case}_width_s",
                         "spice": (f".meas tran {case}_width_s trig v(rail) val={fmt(L)} fall=1 "
                                   f"targ v(rail) val={fmt(L)} rise=1 from={fmt(a)} to={fmt(b)}"),
                         "min": 0.98 * w, "max": 1.02 * w})
        p.ramp(1e-6, NOM)
        rest()

    for lv, L in LEVELS.items():                       # row 6: three starting points per level
        for sv, S in STARTS.items():
            droop(f"r6_{lv}_{sv}", S, L, 60e-9, 1e-9)
    for lv, L in LEVELS.items():                       # row 7: down-and-back at the trip level
        S = NOM
        for w in WIDTHS_NS:
            hold = w * 1e-9 - 2e-9 * 0.1 / (S - (L - 0.1))
            droop(f"r7_{lv}_w{w}", S, L, hold, 1e-9, width_ns=w)
    droop("ideal_l4", NOM, LEVELS["l4"], 60e-9, 1e-12, ideal=True)   # additional case only

    tstop = p.t + 1e-6
    pwl = " ".join(f"{fmt(t)} {fmt(v)}" for t, v in p.pts)
    tone_expr = "+".join(tones)
    spice = (
        "* Behavioural-envelope rail (ASSUMPTION, not a measurement). Generated by gen_envelope.py;\n"
        "* do not edit. Parameterised PWL (W1, W4, W5, compliant transient, rows 6/7) plus gated\n"
        "* tones (W2 sinusoid, W3 bounded pseudo-noise). Circuit body for `klt sim`.\n"
        f"* NEGCTL_MV={negctl_mv}\n"
        + "\n".join(notes) + "\n"
        f"Vbase base 0 PWL({pwl})\n"
        f"Btone tone 0 V='{tone_expr}'\n"
        "Erail rail 0 vol='v(base)+v(tone)'\n"
        "Rload rail 0 1k\n"
    )
    open(f"{outdir}/envelope.spice", "w").write(spice)
    req = {
        "netlist": "envelope.spice",
        "models": {"pdk": "sky130A", "lib": "libs.tech/combined/sky130.lib.spice"},
        "corners": {"process": ["tt"], "temperature_c": [27]},
        "analysis": {"kind": "tran", "args": f"5n {fmt(tstop)}"},
        "options": {"timeout_s": 900},
        "measurements": meas,
    }
    for e in meas:                                      # klt wants bounds under "limits"
        lim = {k: e.pop(k) for k in ("min", "max") if k in e}
        if lim:
            e["limits"] = lim
    with open(f"{outdir}/envelope.request.json", "w") as fh:
        json.dump(req, fh, indent=1)
        fh.write("\n")


if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 0.0)
