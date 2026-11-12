# SPDX-License-Identifier: MIT
"""Independent, bounded codec for the observed Canon PF3 0x3000 envelope.

The file-format implementation, neutral coefficients and identity tables in
this module are authored for this project. No Canon binary, third-party PF3
file or fixed cipher tables are included. A caller supplies an independently
obtained calibration. Successful decoding is not camera validation.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from hashlib import sha256
import math
import struct
from types import MappingProxyType
from typing import Mapping


MAGIC = bytes.fromhex("0000300050535000")
GRID_SIZE = 33
CODE_MAX = 4095
MAX_PROFILE_BYTES = 16 * 1024 * 1024


class PF3Error(ValueError):
    """An input lies outside the strictly observed PF3 format."""


@dataclass(frozen=True)
class Calibration:
    """Caller-owned stream factors; these are intentionally absent from repr.

    For a byte at absolute file position p, the mask is
    first[p % 512] XOR second[p % 513]. Different factor pairs can represent
    the same mask. References and factors are build inputs, not bundled data.
    """

    first: bytes = field(repr=False)
    second: bytes = field(repr=False)
    reference_sha256: str = ""

    def __post_init__(self):
        if type(self.first) is not bytes or len(self.first) != 512:
            raise PF3Error("Calibration needs a 512-byte first factor")
        if type(self.second) is not bytes or len(self.second) != 513:
            raise PF3Error("Calibration needs a 513-byte second factor")

    def transform(self, data: bytes, *, offset: int = 12) -> bytes:
        if type(data) is not bytes or offset < 0:
            raise PF3Error("Transform requires immutable bytes and a nonnegative offset")
        a, b = self.first, self.second
        return bytes(value ^ a[(offset + i) % 512] ^ b[(offset + i) % 513]
                     for i, value in enumerate(data))


@dataclass(frozen=True)
class Field:
    """A typed PF3 field with numeric words represented as little-endian bytes."""

    kind: int
    data: bytes


@dataclass(frozen=True)
class Profile:
    fields: Mapping[int, Field]
    sha256: str
    byte_length: int

    @property
    def title(self) -> str:
        item = self.fields.get(0x1002)
        return "" if item is None else item.data.split(b"\0", 1)[0].decode("ascii")

    @property
    def base_style(self) -> int | None:
        item = self.fields.get(0x1009)
        return None if item is None else struct.unpack("<H", item.data)[0]

    @property
    def controls(self) -> dict[str, int]:
        names = {
            "sharpness": 0x1030, "contrast": 0x1031,
            "saturation": 0x1032, "color_tone": 0x1033,
            "fineness": 0x1034, "threshold": 0x1035,
        }
        return {name: struct.unpack("<i", self.fields[identifier].data)[0]
                for name, identifier in names.items() if identifier in self.fields}

    def lut_array(self, identifier: int = 0x1070):
        """Return float64 [R,G,B,channel] samples, including 12-bit quantization."""
        import numpy as np
        item = self.fields[identifier]
        _check_table(item)
        return np.frombuffer(item.data, dtype="<u2", offset=6).reshape(
            GRID_SIZE, GRID_SIZE, GRID_SIZE, 3).astype(np.float64) / CODE_MAX


def _swap_words(data: bytes, width: int) -> bytes:
    if len(data) % width:
        raise PF3Error("A typed field has a partial numeric word")
    if width == 1:
        return data
    swapped = bytearray(len(data))
    for lane in range(width):
        swapped[lane::width] = data[width - lane - 1::width]
    return bytes(swapped)


def _field_width(kind: int) -> int:
    if kind in (2, 0xFFFF):
        return 1
    if kind == 3:
        return 2
    if kind == 4:
        return 4
    raise PF3Error(f"Unsupported PF3 field type {kind:#x}")


def _header(raw: bytes) -> bytes:
    if type(raw) is not bytes or not 32 <= len(raw) <= MAX_PROFILE_BYTES:
        raise PF3Error("Require bounded immutable PF3 file bytes")
    if raw[:8] != MAGIC:
        raise PF3Error("Only the observed PF3 version 0x3000 is supported")
    if struct.unpack_from(">I", raw, 8)[0] != len(raw) - 12:
        raise PF3Error("PF3 envelope length does not match the actual file")
    return raw[12:]


def parse_profile(raw: bytes, calibration: Calibration) -> Profile:
    """Decode the complete envelope and verify its checksum and terminator."""
    plain = calibration.transform(_header(raw))
    fields: dict[int, Field] = {}
    cursor = 0
    checksum_seen = False
    while cursor + 8 <= len(plain):
        record_start = cursor
        identifier, kind, size = struct.unpack_from(">HHI", plain, cursor)
        cursor += 8
        if size > len(plain) - cursor:
            raise PF3Error("A PF3 field extends beyond the body")
        data = plain[cursor:cursor + size]
        cursor += size
        if identifier == 0xFFFF:
            if (kind, size) != (0xFFFF, 0) or cursor != len(plain) or not checksum_seen:
                raise PF3Error("Invalid PF3 terminator, checksum order or trailing data")
            return Profile(MappingProxyType(fields), sha256(raw).hexdigest(), len(raw))
        if checksum_seen:
            raise PF3Error("A field follows the final PF3 checksum")
        if identifier == 0xFFFE:
            if kind != 4 or size != 4:
                raise PF3Error("Invalid PF3 checksum field")
            expected = sum(plain[:record_start]) & 0xFFFFFFFF
            if struct.unpack(">I", data)[0] != expected:
                raise PF3Error("PF3 body checksum mismatch")
            checksum_seen = True
            continue
        if not (0x1000 <= identifier <= 0x10FF or 0x9000 <= identifier <= 0x90FF):
            raise PF3Error(f"Unsupported PF3 field identifier {identifier:#x}")
        if identifier in fields or len(fields) >= 256:
            raise PF3Error("Duplicate or excessive PF3 fields")
        fields[identifier] = Field(kind, _swap_words(data, _field_width(kind)))
    raise PF3Error("Missing complete PF3 terminator")


def encode_fields(fields: Mapping[int, Field], calibration: Calibration) -> bytes:
    """Serialize caller-authored fields; checksums are always recomputed."""
    if not isinstance(fields, Mapping) or not 1 <= len(fields) <= 256:
        raise PF3Error("Require between one and 256 ordered fields")
    body = bytearray()
    for identifier, item in fields.items():
        if (type(identifier) is not int or not
                (0x1000 <= identifier <= 0x10FF or 0x9000 <= identifier <= 0x90FF)):
            raise PF3Error("Unsupported PF3 field identifier")
        if not isinstance(item, Field) or type(item.data) is not bytes:
            raise PF3Error("Each field needs a type and immutable bytes")
        value = _swap_words(item.data, _field_width(item.kind))
        body.extend(struct.pack(">HHI", identifier, item.kind, len(value)))
        body.extend(value)
        if len(body) + 32 > MAX_PROFILE_BYTES:
            raise PF3Error("PF3 body exceeds the size limit")
    checksum = sum(body) & 0xFFFFFFFF
    body.extend(struct.pack(">HHII", 0xFFFE, 4, 4, checksum))
    body.extend(struct.pack(">HHI", 0xFFFF, 0xFFFF, 0))
    immutable = bytes(body)
    return MAGIC + struct.pack(">I", len(immutable)) + calibration.transform(immutable)


def _identity_wire_table() -> bytes:
    levels = [(i * CODE_MAX + 16) // 32 for i in range(GRID_SIZE)]
    result = bytearray(struct.pack(">HHH", 12, 3, GRID_SIZE))
    for red in levels:
        for green in levels:
            for blue in levels:
                result.extend(struct.pack(">HHH", red, green, blue))
    return bytes(result)


def _rectangle_fingerprint(data: bytes, count: int | None = None) -> bytes:
    """Cancel both periodic stream factors without knowing either factor."""
    stop = len(data) - 1025
    if count is not None:
        stop = min(stop, count)
    if stop < 0:
        return b""
    return bytes(data[i] ^ data[i + 512] ^ data[i + 513] ^ data[i + 1025]
                 for i in range(stop))


def _solve_calibration(plain: bytes, cipher: bytes, offset: int, digest: str) -> Calibration:
    # Each known byte constrains one edge of a bipartite XOR graph. The two
    # periods are coprime; a short continuous span connects all 1025 vertices.
    edges: list[list[tuple[int, int]]] = [[] for _ in range(1025)]
    for index, (clear, encoded) in enumerate(zip(plain[:4096], cipher[:4096])):
        p = offset + index
        left, right = p % 512, 512 + p % 513
        mask = clear ^ encoded
        edges[left].append((right, mask))
        edges[right].append((left, mask))
    values: list[int | None] = [None] * 1025
    values[0] = 0  # Fix the irrelevant common-XOR gauge.
    work = deque([0])
    while work:
        node = work.popleft()
        for neighbor, mask in edges[node]:
            answer = values[node] ^ mask
            if values[neighbor] is None:
                values[neighbor] = answer
                work.append(neighbor)
            elif values[neighbor] != answer:
                raise PF3Error("Known-identity constraints are inconsistent")
    if any(value is None for value in values):
        raise PF3Error("Known-identity span did not determine the full stream")
    calibration = Calibration(bytes(values[:512]), bytes(values[512:]), digest)
    if calibration.transform(cipher, offset=offset) != plain:
        raise PF3Error("Known-identity table does not match the recovered stream")
    return calibration


def calibrate_identity(raw: bytes) -> Calibration:
    """Learn a stream from a caller-supplied PF3 containing an identity table.

    This never reads adjacent files, downloads references, stores factor data,
    or assumes an arbitrary creative LUT is an identity. Both the complete
    known table and the complete decoded file checksum must validate.
    """
    _header(raw)
    known = _identity_wire_table()
    expected = _rectangle_fingerprint(known, 64)
    searchable = _rectangle_fingerprint(raw)
    candidates = 0
    offset = 12
    found: Calibration | None = None
    while True:
        offset = searchable.find(expected, offset)
        if offset < 0:
            break
        candidate_offset = offset
        offset += 1
        candidates += 1
        if candidates > 32:
            raise PF3Error("Ambiguous identity calibration candidates")
        if candidate_offset + len(known) > len(raw):
            continue
        try:
            current = _solve_calibration(
                known, raw[candidate_offset:candidate_offset + len(known)],
                candidate_offset, sha256(raw).hexdigest())
            profile = parse_profile(raw, current)
            host_identity = _swap_words(known, 2)
            if not any(profile.fields.get(identifier) == Field(3, host_identity)
                       for identifier in (0x1070, 0x1071)):
                continue
        except PF3Error:
            continue
        if found is not None and (found.first, found.second) != (current.first, current.second):
            raise PF3Error("Multiple incompatible stream calibrations")
        found = current
    if found is None:
        raise PF3Error("The supplied PF3 has no fully verified identity calibration")
    return found


def _check_table(item: Field) -> None:
    if (item.kind != 3 or len(item.data) != 6 + GRID_SIZE ** 3 * 6 or
            struct.unpack_from("<HHH", item.data) != (12, 3, GRID_SIZE)):
        raise PF3Error("Require an observed 33-cubed, three-channel, 12-bit table")
    if any(value[0] > CODE_MAX for value in struct.iter_unpack("<H", item.data[6:])):
        raise PF3Error("A color-table entry exceeds its declared 12-bit range")


def _lut_field(lut_rgb) -> Field:
    shape = getattr(lut_rgb, "shape", None)
    if shape is not None and tuple(shape) != (33, 33, 33, 3):
        raise PF3Error("LUT shape must be [33,33,33,3] in R,G,B,channel order")
    if shape is None:
        try:
            if (len(lut_rgb) != 33 or any(len(g) != 33 for g in lut_rgb)
                    or any(len(b) != 33 for g in lut_rgb for b in g)
                    or any(len(rgb) != 3 for g in lut_rgb for b in g for rgb in b)):
                raise PF3Error("LUT shape must be [33,33,33,3]")
        except TypeError as error:
            raise PF3Error("LUT must be a complete three-dimensional RGB grid") from error
    result = bytearray(struct.pack("<HHH", 12, 3, GRID_SIZE))
    for red in range(GRID_SIZE):
        for green in range(GRID_SIZE):
            for blue in range(GRID_SIZE):
                rgb = lut_rgb[red][green][blue]
                codes = []
                for component in rgb:
                    value = float(component)
                    if not math.isfinite(value) or not 0 <= value <= 1:
                        raise PF3Error("Every LUT value must be finite and within [0,1]")
                    codes.append(math.floor(value * CODE_MAX + 0.5))
                result.extend(struct.pack("<HHH", *codes))
    return Field(3, bytes(result))


def build_profile(
    lut_rgb,
    title: str,
    calibration: Calibration,
    *,
    base_style: int = 0x84,
    contrast: int = 0,
    saturation: int = 0,
    color_tone: int = 0,
    sharpness: int = 0,
    fineness: int = 2,
    threshold: int = 4,
) -> bytes:
    """Construct an original neutral-base PF3 carrying the supplied RGB LUT.

    All auxiliary color matrices and curves are mathematical identities, so
    the film tone/color transform belongs in the supplied LUT exactly once.
    The two observed user-table records receive the same LUT. Their distinct
    native-camera roles have not been independently established by this codec.
    """
    if type(title) is not str or not 1 <= len(title) <= 31:
        raise PF3Error("Title must contain one to 31 printable ASCII characters")
    try:
        encoded_title = title.encode("ascii")
    except UnicodeEncodeError as error:
        raise PF3Error("Title must use printable ASCII") from error
    if any(value < 32 or value > 126 for value in encoded_title):
        raise PF3Error("Title must use printable ASCII")
    if base_style != 0x84:
        raise PF3Error("This pack is authored for the Canon Neutral base (0x84)")
    controls = {
        0x1030: (sharpness, 0, 7), 0x1031: (contrast, -4, 4),
        0x1032: (saturation, -4, 4), 0x1033: (color_tone, -4, 4),
        0x1034: (fineness, 1, 5), 0x1035: (threshold, 1, 5),
    }
    fields = {0x1009: Field(3, struct.pack("<H", base_style))}
    for identifier, (value, low, high) in controls.items():
        if type(value) is not int or not low <= value <= high:
            raise PF3Error(f"Control {identifier:#x} must be an integer in [{low},{high}]")
        fields[identifier] = Field(4, struct.pack("<i", value))
    fields[0x1002] = Field(2, encoded_title.ljust(32, b"\0"))
    fields[0x100A] = Field(2, bytes(64))
    # Sixty 16.16 coefficients: identity entries in the three channel rows.
    coefficients = [0] * 60
    for index in (0, 21, 42):
        coefficients[index] = 1 << 16
    matrix = Field(4, struct.pack("<60i", *coefficients))
    fields[0x1021] = fields[0x1029] = matrix
    # Three channels, each with a count and two endpoint pairs in 25 words.
    points = [2, 0, 0, 255, 255] + [0] * 20
    curve = Field(4, struct.pack("<75I", *(points * 3)))
    for identifier in (0x1019, 0x1018, 0x1065):
        fields[identifier] = curve
    for identifier in (0x1061, 0x1062):
        fields[identifier] = Field(4, struct.pack("<I", 2) + bytes(508))
    for identifier in (0x1023, 0x102B):
        fields[identifier] = Field(4, struct.pack("<II", 1, 0))
    fields[0x1008] = Field(0xFFFF, bytes(456))
    fields[0x1012] = Field(4, bytes(4))
    fields[0x1070] = fields[0x1071] = _lut_field(lut_rgb)
    fields[0x100D] = Field(2, b"UD ")
    fields[0x100C] = Field(3, struct.pack("<H", 1))
    fields[0x1011] = Field(4, bytes(4))
    fields[0x1080] = Field(4, bytes(4))
    result = encode_fields(fields, calibration)
    reopened = parse_profile(result, calibration)
    if reopened.fields != fields or len(result) != 434511:
        raise PF3Error("Generated PF3 failed complete structural readback")
    return result
