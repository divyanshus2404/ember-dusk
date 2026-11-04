"""Color vision deficiency simulation (Machado et al. 2009, severity 1.0)
and CIELAB distance, used by build.py to keep paired colors distinguishable."""

MATRICES = {
    "protanopia": ((0.152286, 1.052583, -0.204868), (0.114503, 0.786281, 0.099216), (-0.003882, -0.048116, 1.051998)),
    "deuteranopia": ((0.367322, 0.860646, -0.227968), (0.280085, 0.672501, 0.047413), (-0.011820, 0.042940, 0.968881)),
    "tritanopia": ((1.255528, -0.076749, -0.178779), (-0.078411, 0.930809, 0.147602), (0.004733, 0.691367, 0.303900)),
}


def _lin(v):
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


def _rgb(h):
    h = h.lstrip("#")[:6]
    return [_lin(int(h[i:i + 2], 16) / 255) for i in (0, 2, 4)]


def simulate(h, kind):
    r = _rgb(h)
    return [max(0.0, min(1.0, sum(m * c for m, c in zip(row, r)))) for row in MATRICES[kind]]


def _lab(lin):
    x = (0.4124 * lin[0] + 0.3576 * lin[1] + 0.1805 * lin[2]) / 0.95047
    y = 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]
    z = (0.0193 * lin[0] + 0.1192 * lin[1] + 0.9505 * lin[2]) / 1.08883
    f = [t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116 for t in (x, y, z)]
    return 116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])


def distance(a, b, kind=None):
    la = _lab(simulate(a, kind) if kind else _rgb(a))
    lb = _lab(simulate(b, kind) if kind else _rgb(b))
    return sum((p - q) ** 2 for p, q in zip(la, lb)) ** 0.5


def worst(a, b):
    """Smallest distance across normal vision and all three deficiencies."""
    return min((distance(a, b, k), k) for k in (None, *MATRICES))
