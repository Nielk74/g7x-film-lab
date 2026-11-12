"""Strict .cube I/O and vectorized tetrahedral interpolation in encoded sRGB."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shlex

import numpy as np


@dataclass(frozen=True)
class LUT:
    title: str
    table: np.ndarray  # [R, G, B, output channel], values 0..1

    def __post_init__(self):
        t = np.asarray(self.table, dtype=np.float64)
        if (t.ndim != 4 or t.shape[-1] != 3 or len(set(t.shape[:3])) != 1
                or not 2 <= t.shape[0] <= 129 or not np.isfinite(t).all()
                or t.min() < 0 or t.max() > 1):
            raise ValueError("LUT requires finite NxNxNx3 values in 0..1, 2<=N<=129")
        t = t.copy()
        t.flags.writeable = False
        object.__setattr__(self, "table", t)

    @property
    def size(self):
        return self.table.shape[0]

    def apply(self, rgb, *, chunk_size=262_144):
        """Apply to [...,3] sRGB code values, preserving shape; no gamma change."""
        values = np.asarray(rgb, dtype=np.float64)
        if values.ndim < 1 or values.shape[-1] != 3 or not np.isfinite(values).all():
            raise ValueError("Input must be finite RGB code values")
        if values.size and (values.min() < 0 or values.max() > 1):
            raise ValueError("Input must be in 0..1; convert log/HDR to SDR sRGB first")
        if type(chunk_size) is not int or chunk_size < 1:
            raise ValueError("chunk_size must be positive")
        flat = values.reshape(-1, 3)
        result = np.empty_like(flat)
        for start in range(0, len(flat), chunk_size):
            p = flat[start:start + chunk_size] * (self.size - 1)
            lo = np.minimum(np.floor(p).astype(np.intp), self.size - 2)
            frac = p - lo
            order = np.argsort(-frac, axis=1, kind="stable")
            sorted_frac = np.take_along_axis(frac, order, axis=1)
            first = np.zeros_like(lo)
            first[np.arange(len(lo)), order[:, 0]] = 1
            second = first.copy()
            second[np.arange(len(lo)), order[:, 1]] = 1
            def fetch(index):
                return self.table[index[:, 0], index[:, 1], index[:, 2]]
            a, b, c, d = fetch(lo), fetch(lo + first), fetch(lo + second), fetch(lo + 1)
            result[start:start + len(lo)] = (
                a + sorted_frac[:, 0, None] * (b - a)
                + sorted_frac[:, 1, None] * (c - b)
                + sorted_frac[:, 2, None] * (d - c)
            )
        return np.clip(result.reshape(values.shape), 0, 1)


def identity(size=33):
    axis = np.linspace(0, 1, size)
    return np.stack(np.meshgrid(axis, axis, axis, indexing="ij"), axis=-1)


def write_cube(path, lut: LUT, *, comments=()):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    title = lut.title.replace('"', "'").replace("\n", " ").replace("\r", " ")
    with path.open("w", encoding="ascii", newline="\n") as out:
        for text in comments:
            for line in str(text).splitlines():
                out.write("# " + line.encode("ascii", "replace").decode() + "\n")
        out.write(f'TITLE "{title}"\nLUT_3D_SIZE {lut.size}\nDOMAIN_MIN 0 0 0\nDOMAIN_MAX 1 1 1\n')
        # .cube has R fastest; the internal/PF3 array has B fastest.
        np.savetxt(out, lut.table.transpose(2, 1, 0, 3).reshape(-1, 3), fmt="%.9f")


def read_cube(path) -> LUT:
    title, size, rows = Path(path).stem, None, []
    seen = set()
    for number, raw in enumerate(Path(path).read_text(encoding="ascii").splitlines(), 1):
        line = raw.strip()
        tokens = line.partition("#")[0].split() if line and line[0] in "+-.0123456789" else shlex.split(line, comments=True)
        if not tokens:
            continue
        key = tokens[0]
        if key in {"TITLE", "LUT_3D_SIZE", "DOMAIN_MIN", "DOMAIN_MAX"}:
            if key in seen:
                raise ValueError(f"Duplicate {key} at line {number}")
            seen.add(key)
            if key == "TITLE":
                if len(tokens) != 2:
                    raise ValueError("TITLE requires one string")
                title = tokens[1]
            elif key == "LUT_3D_SIZE":
                if len(tokens) != 2:
                    raise ValueError("LUT_3D_SIZE requires one integer")
                size = int(tokens[1])
                if not 2 <= size <= 129:
                    raise ValueError("Unsupported LUT size")
            else:
                expected = [0.0] * 3 if key == "DOMAIN_MIN" else [1.0] * 3
                if list(map(float, tokens[1:])) != expected:
                    raise ValueError("Only the explicit 0..1 sRGB domain is supported")
        else:
            if len(tokens) != 3:
                raise ValueError(f"Expected three numeric samples at line {number}")
            rows.append(tuple(map(float, tokens)))
    if size is None or len(rows) != size ** 3:
        raise ValueError("Cube sample count does not match LUT_3D_SIZE")
    table = np.asarray(rows).reshape(size, size, size, 3).transpose(2, 1, 0, 3)
    return LUT(title, table)
