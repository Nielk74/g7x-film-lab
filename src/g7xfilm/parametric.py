# SPDX-License-Identifier: MIT
"""Fit an authored RGB LUT to the parametric stages read by Canon software.

This is an approximation, not an alternative encoding of an arbitrary 3D LUT.
The observed stages are RGB curves (1018), a 3x19 cubic polynomial (1021 or
1029), RGB curves (1065), then a luminance curve (1019). We leave luminance
unchanged. Native-camera execution is a separate validation boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping, Iterator
import struct

import numpy as np
from scipy.interpolate import BSpline

from .pf3 import Field


# Observed mathematical order; the twentieth word in each stored row is unused.
POWERS = (
    (1, 0, 0), (0, 1, 0), (0, 0, 1),
    (2, 0, 0), (1, 1, 0), (1, 0, 1), (0, 2, 0), (0, 1, 1), (0, 0, 2),
    (3, 0, 0), (2, 1, 0), (2, 0, 1), (1, 2, 0), (1, 1, 1),
    (1, 0, 2), (0, 3, 0), (0, 2, 1), (0, 1, 2), (0, 0, 3),
)


def polynomial_basis(rgb):
    values = np.asarray(rgb, dtype=np.float64)
    if values.shape[-1:] != (3,) or not np.isfinite(values).all():
        raise ValueError("Require finite RGB samples with a final three-channel axis")
    r, g, b = np.moveaxis(values, -1, 0)
    # Products spell out the monomial order independently of a renderer or DLL.
    return np.stack((r, g, b, r*r, r*g, r*b, g*g, g*b, b*b,
                     r*r*r, r*r*g, r*r*b, r*g*g, r*g*b, r*b*b,
                     g*g*g, g*g*b, g*b*b, b*b*b), axis=-1)


def _sample_lut(lut, rgb):
    table = np.asarray(lut, dtype=np.float64)
    points = np.clip(np.asarray(rgb, dtype=np.float64), 0, 1)
    n = table.shape[0]
    position = points * (n - 1)
    lower = np.minimum(position.astype(np.int64), n - 2)
    fraction = position - lower
    result = np.zeros_like(points)
    for red in (0, 1):
        for green in (0, 1):
            for blue in (0, 1):
                corner = (red, green, blue)
                weight = np.prod(np.where(corner, fraction, 1 - fraction), axis=-1)
                index = lower + corner
                result += table[index[..., 0], index[..., 1], index[..., 2]] * weight[..., None]
    return result


def _check_lut(lut):
    table = np.asarray(lut, dtype=np.float64)
    if (table.ndim != 4 or table.shape[-1] != 3 or table.shape[0] < 5
            or table.shape[:3] != (table.shape[0],) * 3
            or not np.isfinite(table).all() or np.min(table) < 0 or np.max(table) > 1):
        raise ValueError("Require a finite cubic RGB grid with values in [0,1]")
    return table


def curve_cache(points):
    """Evaluate the observed integer-point quadratic curve into 256 samples.

    This uses the standard B-spline basis with the observed clamped quadratic
    knots. Final monotonic/upper-point clipping models the measured cache
    preparation, not a generic unconstrained editor spline.
    """
    coordinates = np.asarray(points, dtype=np.float64)
    if (coordinates.ndim != 2 or coordinates.shape[1] != 2
            or not 2 <= len(coordinates) <= 12 or not np.isfinite(coordinates).all()
            or np.min(coordinates) < 0 or np.max(coordinates) > 255
            or coordinates[0, 0] != 0 or coordinates[-1, 0] != 255
            or np.any(np.diff(coordinates[:, 0]) <= 0)
            or np.any(np.diff(coordinates[:, 1]) < 0)):
        raise ValueError("Require 2..12 ordered monotonic integer-domain points")
    x, y = coordinates.T / 255
    domain = np.linspace(0, 1, 256)
    if len(x) == 2:
        sampled = y[0] + domain * (y[-1] - y[0])
    else:
        knots = np.concatenate((np.zeros(3), (x[:-3] + x[3:]) / 2, np.ones(3)))
        interpolation = BSpline.design_matrix(x, knots, 2).toarray()
        weights = np.linalg.solve(interpolation, y)
        sampled = BSpline(knots, weights, 2)(domain)
    upper_points = y[np.minimum(np.searchsorted(x, domain, side="left"), len(y) - 1)]
    sampled = np.maximum.accumulate(np.minimum(np.minimum(sampled, 1), upper_points))
    return np.clip(sampled, 0, 1)


def _curve_points(samples, max_points):
    wanted = np.asarray(samples, dtype=np.float64)
    if wanted.shape != (256,) or not np.isfinite(wanted).all():
        raise ValueError("Need 256 finite curve samples")
    wanted = np.maximum.accumulate(np.clip(wanted, 0, 1))
    indices = [0, 255]
    for _ in range(max_points - 2):
        points = np.stack((indices, np.rint(wanted[indices] * 255)), axis=1).astype(int)
        predicted = curve_cache(points)
        error = np.abs(predicted - wanted)
        # Adjacent integer abscissas can be legal but provide an unstable
        # interpolation system; retain a two-code minimum spacing.
        for index in indices:
            error[max(0, index - 1):min(256, index + 2)] = -1
        chosen = int(np.argmax(error))
        if error[chosen] <= 0.6 / 255:
            break
        indices.append(chosen)
        indices.sort()
    return np.stack((indices, np.rint(wanted[indices] * 255)), axis=1).astype(int)


def _curve_record(channels):
    data = bytearray()
    for points in channels:
        points = np.asarray(points, dtype=np.int64)
        # Re-evaluation validates all bounds before bytes reach the file writer.
        curve_cache(points)
        words = [len(points), *points.ravel().tolist()]
        data.extend(struct.pack("<25I", *(words + [0] * (25 - len(words)))))
    return Field(4, bytes(data))


def _apply_curves(rgb, curves):
    values = np.asarray(rgb, dtype=np.float64)
    x = np.linspace(0, 1, 256)
    return np.stack([np.interp(values[..., channel], x, curves[channel])
                     for channel in range(3)], axis=-1)


def _inverse_curves(rgb, curves):
    values = np.asarray(rgb, dtype=np.float64)
    x = np.linspace(0, 1, 256)
    result = []
    for channel in range(3):
        ordinate, first = np.unique(curves[channel], return_index=True)
        last = np.maximum.reduceat(np.arange(256), first)
        abscissa = (x[first] + x[last]) / 2
        abscissa[0], abscissa[-1] = 0, 1
        result.append(np.interp(values[..., channel], ordinate, abscissa))
    return np.stack(result, axis=-1)


def _lab(rgb):
    values = np.clip(np.asarray(rgb, dtype=np.float64), 0, 1)
    linear = np.where(values <= .04045, values / 12.92, ((values + .055) / 1.055) ** 2.4)
    xyz = linear @ np.array([[.4124564, .3575761, .1804375],
                             [.2126729, .7151522, .0721750],
                             [.0193339, .1191920, .9503041]]).T
    normalized = xyz / np.array([.95047, 1., 1.08883])
    delta = 6 / 29
    f = np.where(normalized > delta ** 3, np.cbrt(normalized),
                 normalized / (3 * delta ** 2) + 4 / 29)
    return np.stack((116*f[..., 1] - 16, 500*(f[..., 0] - f[..., 1]),
                     200*(f[..., 1] - f[..., 2])), axis=-1)


def _metrics(reference, predicted):
    error = np.abs(np.asarray(reference) - predicted)
    de = np.linalg.norm(_lab(reference) - _lab(predicted), axis=-1)
    return {
        "rgb_rmse": float(np.sqrt(np.mean(error ** 2))),
        "rgb_max_error": float(np.max(error)),
        "delta_e76_mean": float(np.mean(de)),
        "delta_e76_p95": float(np.percentile(de, 95)),
        "delta_e76_max": float(np.max(de)),
    }


def _evaluate(rgb, coefficients, pre, post):
    shaped = _apply_curves(rgb, pre)
    transformed = np.clip(polynomial_basis(shaped) @ coefficients.T, 0, 1)
    return np.clip(_apply_curves(transformed, post), 0, 1)


@dataclass(frozen=True)
class ParametricFit(Mapping):
    """Typed-field overrides plus the independently evaluated fitted model."""

    fields: Mapping[int, Field]
    coefficients: np.ndarray
    pre_cache: np.ndarray
    post_cache: np.ndarray
    report: dict

    def __getitem__(self, key):
        return self.fields[key]

    def __iter__(self) -> Iterator:
        return iter(self.fields)

    def __len__(self):
        return len(self.fields)

    def evaluate(self, rgb):
        return _evaluate(rgb, self.coefficients, self.pre_cache, self.post_cache)


def fit_lut(lut, *, max_points=12, training_grid=17, validation_samples=8192):
    """Project a full LUT onto the supported curve/polynomial curve chain.

    Candidate shapers and regularization are chosen using a deterministic
    held-out RGB sample set. Independent gray and skin-region samples are
    reported separately. These numerical errors measure projection quality,
    not film fidelity or agreement with the camera's complete JPEG pipeline.
    """
    target = _check_lut(lut)
    if not 2 <= max_points <= 12 or not 5 <= training_grid <= 33 or validation_samples < 128:
        raise ValueError("Unsupported fitting bounds")
    axis = np.linspace(0, 1, training_grid)
    lattice = np.stack(np.meshgrid(axis, axis, axis, indexing="ij"), axis=-1).reshape(-1, 3)
    rng = np.random.default_rng(400200100)
    gray_axis = np.linspace(0, 1, 257)
    gray = np.repeat(gray_axis[:, None], 3, axis=1)
    skin = rng.uniform([.25, .13, .07], [.95, .78, .62], (1536, 3))
    skin.sort(axis=1)
    skin = skin[:, ::-1].copy()
    train = np.concatenate((lattice, gray, skin[:1024]))
    expected = _sample_lut(target, train)
    validation = rng.uniform(0, 1, (validation_samples, 3))
    expected_validation = _sample_lut(target, validation)
    neutral_expected = _sample_lut(target, gray)
    skin_validation = skin[1024:]
    skin_expected = _sample_lut(target, skin_validation)
    weights = np.concatenate((np.ones(len(lattice)), np.full(len(gray), 8.), np.full(1024, 2.)))
    root_weight = np.sqrt(weights[:, None])
    samples = np.linspace(0, 1, 256)
    diagonal = _sample_lut(target, np.repeat(samples[:, None], 3, axis=1))
    identity_points = np.array([[0, 0], [255, 255]])
    identity = np.repeat(samples[None, :], 3, axis=0)
    identity_channels = [identity_points] * 3

    candidates = []
    # A directly fitted cubic is retained as a simple candidate; tone-shaped
    # alternatives reduce the burden on its 19 basis functions.
    definitions = [("cubic", identity_channels, identity_channels)]
    film_points = [_curve_points(diagonal[:, channel], max_points) for channel in range(3)]
    definitions.append(("pre-film-tone", film_points, identity_channels))
    definitions.append(("post-film-tone", identity_channels, film_points))
    for gamma in (.65, 1.4, 1.8, 2.2):
        pre_points = _curve_points(samples ** gamma, max_points)
        pre = curve_cache(pre_points)
        inverse = np.interp(samples, pre, samples)
        post_target = _sample_lut(target, np.repeat(inverse[:, None], 3, axis=1))
        post_points = [_curve_points(post_target[:, channel], max_points) for channel in range(3)]
        definitions.append((f"gamma-{gamma:g}-film-tone", [pre_points] * 3, post_points))

    best = None
    penalties = np.array([1.] * 3 + [3.] * 6 + [8.] * 10)
    identity_coefficients = np.zeros((19, 3))
    identity_coefficients[:3] = np.eye(3)
    monochrome = bool(np.max(np.ptp(target, axis=-1)) < 1e-10)
    for name, pre_points, post_points in definitions:
        pre = np.stack([curve_cache(points) for points in pre_points])
        post = np.stack([curve_cache(points) for points in post_points])
        design = polynomial_basis(_apply_curves(train, pre))
        desired = _inverse_curves(expected, post)
        for regularization in (1e-5, 1e-3, 1e-1):
            ridge = np.sqrt(regularization) * np.diag(penalties)
            design_augmented = np.vstack((design * root_weight, ridge))
            target_augmented = np.vstack((desired * root_weight, ridge @ identity_coefficients))
            coefficients = np.linalg.lstsq(design_augmented, target_augmented, rcond=None)[0].T
            if monochrome:
                coefficients[:] = np.mean(coefficients, axis=0)
            # All scoring uses the Q16.16 values that will actually be stored.
            coefficients = np.rint(coefficients * 65536) / 65536
            predicted = _evaluate(validation, coefficients, pre, post)
            report = _metrics(expected_validation, predicted)
            neutral_report = _metrics(neutral_expected, _evaluate(gray, coefficients, pre, post))
            skin_report = _metrics(skin_expected, _evaluate(skin_validation, coefficients, pre, post))
            score = (report["delta_e76_mean"] + .15*report["delta_e76_p95"]
                     + .35*skin_report["delta_e76_mean"] + .25*neutral_report["delta_e76_mean"])
            candidate = {
                "model": name, "regularization": regularization, "score": score,
                "holdout": report, "neutral": neutral_report, "skin_region": skin_report,
                "pre_points": [points.tolist() for points in pre_points],
                "post_points": [points.tolist() for points in post_points],
            }
            candidates.append(candidate)
            if best is None or score < best[0]:
                best = (score, coefficients, pre, post, pre_points, post_points, candidate)
    _, coefficients, pre, post, pre_points, post_points, chosen = best
    packed_coefficients = np.zeros((3, 20), dtype="<i4")
    codes = np.rint(coefficients * 65536)
    if np.max(np.abs(codes)) > np.iinfo(np.int32).max:
        raise ValueError("Fitted coefficient exceeds signed Q16.16 storage")
    packed_coefficients[:, :19] = codes.astype("<i4")
    matrix_field = Field(4, packed_coefficients.tobytes())
    fields = {
        0x1021: matrix_field, 0x1029: matrix_field,
        0x1018: _curve_record(pre_points),
        0x1065: _curve_record(post_points),
        0x1019: _curve_record(identity_channels),
    }
    report = {
        "model": chosen["model"], "regularization": chosen["regularization"],
        "training_samples": len(train), "holdout_samples": len(validation),
        "monochrome": monochrome, "selected": chosen, "candidates": candidates,
        "coefficient_layout": "three rows, 19 cubic monomials plus one unused zero word; signed Q16.16",
        "curve_layout": "1018 pre RGB, 1065 post RGB, 1019 unchanged luminance",
        "native_camera_validated": False,
        "limitations": [
            "Projection metrics compare the independent parametric model with the target LUT, not physical film.",
            "The native pipeline can differ through color management, gamut policy and quantization.",
            "Native Canon rendering and actual camera registration/output require separate checks.",
        ],
    }
    return ParametricFit(fields, coefficients, pre, post, report)
