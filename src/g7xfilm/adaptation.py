"""Fixed display-input calibration; its choices are authored, not film measurements."""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class DisplayShaper:
    axis: np.ndarray
    exposure: np.ndarray
    target_neutral: np.ndarray
    identity_share: float
    black: float
    white: float

    def apply(self, rgb):
        values = np.asarray(rgb, dtype=np.float64)
        if not np.isfinite(values).all() or values.min() < 0 or values.max() > 1:
            raise ValueError("The public input is encoded SDR sRGB in 0..1")
        return np.interp(values, self.axis, self.exposure)


def calibrate_display_shaper(model_axis, model_neutral, *, identity_share, black, white):
    """Invert an extended model gray ramp against an explicit display tone target.

    The nonlinear RGB pre-shaper fixes repeated tone rendering on processed
    images. It is neutral only on the gray axis; it can also change color ratios.
    The target retains a declared fraction of the stock's modeled tone response.
    No scene is metered, and no histogram or learned photo content is used.
    """
    x = np.asarray(model_axis, dtype=np.float64)
    y = np.asarray(model_neutral, dtype=np.float64)
    if y.shape != (len(x), 3) or x[0] != 0 or x[-1] <= 1 or not np.all(np.diff(x) > 0):
        raise ValueError("Need an increasing extended exposure domain and complete RGB gray ramp")
    if not np.isfinite(y).all() or not 0 < identity_share < 1 or not 0 <= black < white <= 1:
        raise ValueError("Invalid finite calibration or display settings")
    neutral = y.mean(axis=1)
    if np.min(np.diff(neutral)) < -2e-6:
        raise ValueError("The stock gray response is not monotonic enough to invert")
    neutral = np.maximum.accumulate(neutral)
    # Reject unreachable targets. Silent inverse clamping made an early trial
    # flatten the top of the ramp; final bakes must retain its highlight detail.
    if black <= neutral[0] or white >= neutral[-1] - 1e-5:
        raise ValueError("Display black/white lie outside the sampled model range; extend calibration")
    axis = np.linspace(0, 1, 4097)
    normal_white = np.interp(1, x, neutral)
    stock_curve = (np.interp(axis, x, neutral) - neutral[0]) / (normal_white - neutral[0])
    target = black + (white - black) * (identity_share * axis + (1 - identity_share) * stock_curve)
    levels, unique = np.unique(neutral, return_index=True)
    exposure = np.interp(target, levels, x[unique])
    if not np.all(np.diff(exposure) > 0) or not np.all(np.diff(target) > 0):
        raise ValueError("The display calibration introduced a flat or reversed interval")
    return DisplayShaper(axis, exposure, target, identity_share, black, white)


def neutral_print_timing(rgb, model_neutral):
    """Remove the modeled gray crossover, then softly contain its chroma.

    This is an authored, fixed print/scanner balancing decision. It is keyed
    only to the model's neutral axis, never to an individual photo's contents.
    Subtracting a zero-mean RGB cast keeps the mean gray tone target intact.
    """
    values = np.asarray(rgb, dtype=np.float64)
    gray = np.asarray(model_neutral, dtype=np.float64)
    if gray.ndim != 2 or gray.shape[1] != 3 or not np.isfinite(gray).all():
        raise ValueError("Need a complete finite model gray ramp")
    mean = gray.mean(axis=-1)
    levels, indices = np.unique(np.maximum.accumulate(mean), return_index=True)
    casts = gray[indices] - mean[indices, None]
    light = values.mean(axis=-1)
    correction = np.stack([np.interp(light, levels, casts[:, c]) for c in range(3)], axis=-1)
    corrected = values - correction
    # Contain any new out-of-gamut colors introduced by neutral balancing.
    chroma = corrected - light[..., None]
    room = np.where(chroma >= 0, 1 - light[..., None], light[..., None])
    distance = np.max(np.abs(chroma) / np.maximum(room, 1e-10), axis=-1)
    knee, ceiling = .90, .995
    mapped = np.where(distance <= knee, distance,
                      knee + (ceiling - knee) * -np.expm1(-np.maximum(distance-knee, 0)/(ceiling-knee)))
    scale = np.divide(mapped, distance, out=np.ones_like(distance), where=distance > 0)
    return np.clip(light[..., None] + chroma * scale[..., None], 0, 1)
