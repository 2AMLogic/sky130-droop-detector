"""Shared behavioural-envelope rail waveform pieces (spec "Rail model", form 2: an
ASSUMPTION, not a measurement).

Imported by sim/tb_rail_model_check/gen_envelope.py (checks the envelope against its
bounds) and sim/tb_false_flag/gen_envelope_ff.py (applies it to the detector), so the
two benches cannot drift apart. Changing anything here changes both benches' rail.

The generators run as `python3 -I`, which does not put the script directory on
sys.path; they add this directory explicitly before importing.
"""
import math

NOM = 1.8
WIN_LO, WIN_HI = 1.764, 1.836          # LDO +-2 % window
BAND = 0.018                            # +-1 % of nominal
GAP = 200e-9


def fmt(x):
    return f"{x:.12g}"


class Pwl:
    """Piecewise-linear base waveform builder, starting at NOM at t = 0."""

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

    def pwl_text(self):
        return " ".join(f"{fmt(t)} {fmt(v)}" for t, v in self.pts)


def w2_tone(t0, dur, f):
    """Gated +-BAND sinusoid B-source term over [t0, t0 + dur]."""
    return f"(u(time-{fmt(t0)})-u(time-{fmt(t0 + dur)}))*{BAND}*sin(2*pi*{fmt(f)}*(time-{fmt(t0)}))"


def w3_noise(t0, dur):
    """Gated, tapered 16-tone bounded pseudo-noise B-source term over [t0, t0 + dur]."""
    terms = []
    for k in range(16):
        fk = 2e5 * (100e6 / 2e5) ** (k / 15) * (1 + 0.013 * k)
        ph = (k * 2.399963) % (2 * math.pi)
        terms.append(f"0.0015*sin(2*pi*{fmt(fk)}*(time-{fmt(t0)})+{fmt(ph)})")
    taper = f"sin(pi*(time-{fmt(t0)})/{fmt(dur)})"
    return f"(u(time-{fmt(t0)})-u(time-{fmt(t0 + dur)}))*{taper}*({'+'.join(terms)})"
