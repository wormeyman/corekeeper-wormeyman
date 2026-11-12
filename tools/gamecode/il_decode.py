#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.14"
# dependencies = ["dnfile"]
# ///
"""Decode a .NET method body, with member names and constant values. Read only.

Covers every opcode in ECMA-335 Partition III. An unknown opcode stops the listing with `??`
rather than guessing its length.

Usage:
    uv run tools/gamecode/il_decode.py <dll> <TypeName> <MethodName> [overload number]
"""

import argparse
import struct
import sys
from enum import Enum, auto
from pathlib import Path
from typing import Any

import dnfile


class Operand(Enum):
    """What follows an opcode in the byte stream."""

    NONE = auto()
    INDEX8 = auto()  # unsigned 8-bit argument or local index
    INDEX16 = auto()
    INT8 = auto()
    INT32 = auto()
    INT64 = auto()
    FLOAT32 = auto()
    FLOAT64 = auto()
    BRANCH8 = auto()  # signed offset from the next instruction
    BRANCH32 = auto()
    TOKEN = auto()  # metadata token
    SWITCH = auto()


def _table() -> dict[int, tuple[str, Operand]]:
    o = Operand
    ops: dict[int, tuple[str, Operand]] = {
        0x00: ("nop", o.NONE), 0x01: ("break", o.NONE), 0x14: ("ldnull", o.NONE), 0x15: ("ldc.i4.m1", o.NONE),
        0x1F: ("ldc.i4.s", o.INT8), 0x20: ("ldc.i4", o.INT32), 0x21: ("ldc.i8", o.INT64),
        0x22: ("ldc.r4", o.FLOAT32), 0x23: ("ldc.r8", o.FLOAT64), 0x25: ("dup", o.NONE), 0x26: ("pop", o.NONE),
        0x2A: ("ret", o.NONE), 0x45: ("switch", o.SWITCH), 0x7A: ("throw", o.NONE), 0x8E: ("ldlen", o.NONE),
        0xDC: ("endfinally", o.NONE), 0xDD: ("leave", o.BRANCH32), 0xDE: ("leave.s", o.BRANCH8),
    }  # fmt: skip
    for i, name in enumerate(("ldarg.0", "ldarg.1", "ldarg.2", "ldarg.3", "ldloc.0", "ldloc.1", "ldloc.2", "ldloc.3",
                              "stloc.0", "stloc.1", "stloc.2", "stloc.3")):  # fmt: skip
        ops[0x02 + i] = (name, o.NONE)
    for i, name in enumerate(("ldarg.s", "ldarga.s", "starg.s", "ldloc.s", "ldloca.s", "stloc.s")):
        ops[0x0E + i] = (name, o.INDEX8)
    for i in range(9):
        ops[0x16 + i] = (f"ldc.i4.{i}", o.NONE)
    branches = (
        "br",
        "brfalse",
        "brtrue",
        "beq",
        "bge",
        "bgt",
        "ble",
        "blt",
        "bne.un",
        "bge.un",
        "bgt.un",
        "ble.un",
        "blt.un",
    )
    for i, name in enumerate(branches):
        ops[0x2B + i] = (f"{name}.s", o.BRANCH8)
        ops[0x38 + i] = (name, o.BRANCH32)
    simple = {
        0x46: "ldind.i1", 0x47: "ldind.u1", 0x48: "ldind.i2", 0x49: "ldind.u2", 0x4A: "ldind.i4", 0x4B: "ldind.u4",
        0x4C: "ldind.i8", 0x4D: "ldind.i", 0x4E: "ldind.r4", 0x4F: "ldind.r8", 0x50: "ldind.ref", 0x51: "stind.ref",
        0x52: "stind.i1", 0x53: "stind.i2", 0x54: "stind.i4", 0x55: "stind.i8", 0x56: "stind.r4", 0x57: "stind.r8",
        0x58: "add", 0x59: "sub", 0x5A: "mul", 0x5B: "div", 0x5C: "div.un", 0x5D: "rem", 0x5E: "rem.un", 0x5F: "and",
        0x60: "or", 0x61: "xor", 0x62: "shl", 0x63: "shr", 0x64: "shr.un", 0x65: "neg", 0x66: "not",
        0x67: "conv.i1", 0x68: "conv.i2", 0x69: "conv.i4", 0x6A: "conv.i8", 0x6B: "conv.r4", 0x6C: "conv.r8",
        0x6D: "conv.u4", 0x6E: "conv.u8", 0x76: "conv.r.un",
        0x82: "conv.ovf.i1.un", 0x83: "conv.ovf.i2.un", 0x84: "conv.ovf.i4.un", 0x85: "conv.ovf.i8.un",
        0x86: "conv.ovf.u1.un", 0x87: "conv.ovf.u2.un", 0x88: "conv.ovf.u4.un", 0x89: "conv.ovf.u8.un",
        0x8A: "conv.ovf.i.un", 0x8B: "conv.ovf.u.un",
        0x90: "ldelem.i1", 0x91: "ldelem.u1", 0x92: "ldelem.i2", 0x93: "ldelem.u2", 0x94: "ldelem.i4",
        0x95: "ldelem.u4", 0x96: "ldelem.i8", 0x97: "ldelem.i", 0x98: "ldelem.r4", 0x99: "ldelem.r8",
        0x9A: "ldelem.ref", 0x9B: "stelem.i", 0x9C: "stelem.i1", 0x9D: "stelem.i2", 0x9E: "stelem.i4",
        0x9F: "stelem.i8", 0xA0: "stelem.r4", 0xA1: "stelem.r8", 0xA2: "stelem.ref",
        0xB3: "conv.ovf.i1", 0xB4: "conv.ovf.u1", 0xB5: "conv.ovf.i2", 0xB6: "conv.ovf.u2", 0xB7: "conv.ovf.i4",
        0xB8: "conv.ovf.u4", 0xB9: "conv.ovf.i8", 0xBA: "conv.ovf.u8", 0xC3: "ckfinite",
        0xD1: "conv.u2", 0xD2: "conv.u1", 0xD3: "conv.i", 0xD4: "conv.ovf.i", 0xD5: "conv.ovf.u",
        0xD6: "add.ovf", 0xD7: "add.ovf.un", 0xD8: "mul.ovf", 0xD9: "mul.ovf.un", 0xDA: "sub.ovf",
        0xDB: "sub.ovf.un", 0xDF: "stind.i", 0xE0: "conv.u",
    }  # fmt: skip
    ops.update({code: (name, o.NONE) for code, name in simple.items()})
    tokens = {
        0x27: "jmp", 0x28: "call", 0x29: "calli", 0x6F: "callvirt", 0x70: "cpobj", 0x71: "ldobj", 0x72: "ldstr",
        0x73: "newobj", 0x74: "castclass", 0x75: "isinst", 0x79: "unbox", 0x7B: "ldfld", 0x7C: "ldflda",
        0x7D: "stfld", 0x7E: "ldsfld", 0x7F: "ldsflda", 0x80: "stsfld", 0x81: "stobj", 0x8C: "box",
        0x8D: "newarr", 0x8F: "ldelema", 0xA3: "ldelem", 0xA4: "stelem", 0xA5: "unbox.any", 0xC2: "refanyval",
        0xC6: "mkrefany", 0xD0: "ldtoken",
    }  # fmt: skip
    ops.update({code: (name, o.TOKEN) for code, name in tokens.items()})
    return ops


ONE_BYTE = _table()
TWO_BYTE_PREFIX = 0xFE
TWO_BYTE: dict[int, tuple[str, Operand]] = {
    0x01: ("ceq", Operand.NONE), 0x02: ("cgt", Operand.NONE), 0x03: ("cgt.un", Operand.NONE),
    0x04: ("clt", Operand.NONE), 0x05: ("clt.un", Operand.NONE), 0x06: ("ldftn", Operand.TOKEN),
    0x09: ("ldarg", Operand.INDEX16), 0x0A: ("ldarga", Operand.INDEX16), 0x0B: ("starg", Operand.INDEX16),
    0x0C: ("ldloc", Operand.INDEX16), 0x0D: ("ldloca", Operand.INDEX16), 0x0E: ("stloc", Operand.INDEX16),
    0x15: ("initobj", Operand.TOKEN), 0x16: ("constrained.", Operand.TOKEN), 0x1C: ("sizeof", Operand.TOKEN),
    0x1E: ("readonly.", Operand.NONE), 0x00: ("arglist", Operand.NONE), 0x07: ("ldvirtftn", Operand.TOKEN),
    0x0F: ("localloc", Operand.NONE), 0x11: ("endfilter", Operand.NONE), 0x12: ("unaligned.", Operand.INDEX8),
    0x13: ("volatile.", Operand.NONE), 0x14: ("tail.", Operand.NONE), 0x17: ("cpblk", Operand.NONE),
    0x18: ("initblk", Operand.NONE), 0x19: ("no.", Operand.INDEX8), 0x1A: ("rethrow", Operand.NONE),
    0x1D: ("refanytype", Operand.NONE),
}  # fmt: skip

# struct format and size for fixed-size operands
FIXED: dict[Operand, tuple[str, int]] = {
    Operand.INDEX8: ("<B", 1), Operand.INDEX16: ("<H", 2), Operand.INT8: ("<b", 1), Operand.INT32: ("<i", 4),
    Operand.INT64: ("<q", 8), Operand.FLOAT32: ("<f", 4), Operand.FLOAT64: ("<d", 8),
    Operand.BRANCH8: ("<b", 1), Operand.BRANCH32: ("<i", 4), Operand.TOKEN: ("<I", 4),
}  # fmt: skip

TINY_HEADER = 0b10  # low two bits of a method body's first byte
TOKEN_TABLE_SHIFT = 24
TOKEN_ROW_MASK = 0xFFFFFF


class TokenNames:
    """Turns metadata tokens into readable names."""

    METHOD_DEF, MEMBER_REF, FIELD, METHOD_SPEC, TYPE_REF, TYPE_DEF, STRING = 0x06, 0x0A, 0x04, 0x2B, 0x01, 0x02, 0x70

    def __init__(self, md: Any) -> None:  # noqa: ANN401 - dnfile's metadata tables are untyped
        self.md = md

    def name(self, token: int) -> str:
        table, row = token >> TOKEN_TABLE_SHIFT, token & TOKEN_ROW_MASK
        try:
            return self._lookup(table, row) or f"tok {token:#x}"
        except (IndexError, AttributeError) as e:
            return f"tok {token:#x} ({e})"

    def _lookup(self, table: int, row: int) -> str | None:
        md = self.md
        result: str | None = None
        if table == self.METHOD_DEF:
            result = str(md.MethodDef[row - 1].Name)
        elif table == self.MEMBER_REF:
            ref = md.MemberRef[row - 1]
            owner = ref.Class.row
            result = f"{getattr(owner, 'TypeName', None) or getattr(owner, 'Name', '?')}::{ref.Name}"
        elif table == self.FIELD:
            result = f"field {md.Field[row - 1].Name}"
        elif table == self.METHOD_SPEC:
            target = md.MethodSpec[row - 1].Method
            kind = self.METHOD_DEF if target.table.name == "MethodDef" else self.MEMBER_REF
            result = "spec->" + self.name(kind << TOKEN_TABLE_SHIFT | target.row_index)
        elif table in {self.TYPE_REF, self.TYPE_DEF}:
            result = f"type {(md.TypeRef if table == self.TYPE_REF else md.TypeDef)[row - 1].TypeName}"
        elif table == self.STRING:
            result = "string"
        return result


def decode(body: bytes, names: TokenNames) -> list[str]:
    lines: list[str] = []
    i = 0
    while i < len(body):
        at, code = i, body[i]
        i += 1
        if code == TWO_BYTE_PREFIX:
            code = body[i]
            i += 1
            entry = TWO_BYTE.get(code)
        else:
            entry = ONE_BYTE.get(code)
        if entry is None:
            lines.append(f"  {at:#06x} ?? {code:#04x} (unknown opcode, stopping)")
            break
        name, operand = entry
        text = name
        if operand is Operand.SWITCH:
            (count,) = struct.unpack_from("<I", body, i)
            i += 4 + 4 * count
            text = f"{name} ({count} targets)"
        elif operand is not Operand.NONE:
            fmt, size = FIXED[operand]
            (value,) = struct.unpack_from(fmt, body, i)
            i += size
            if operand in {Operand.BRANCH8, Operand.BRANCH32}:
                text = f"{name} -> {i + value:#06x}"
            elif operand is Operand.TOKEN:
                text = f"{name} {names.name(value)}"
            else:
                text = f"{name} {value}"
        lines.append(f"  {at:#06x} {text}")
    return lines


def method_body(data: bytes, offset: int) -> bytes:
    header = data[offset]
    if header & 0b11 == TINY_HEADER:
        return data[offset + 1 : offset + 1 + (header >> 2)]
    (flags,) = struct.unpack_from("<H", data, offset)
    (size,) = struct.unpack_from("<I", data, offset + 4)
    start = offset + (flags >> 12) * 4
    return data[start : start + size]


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("dll", type=Path)
    parser.add_argument("type_name", help="type name without namespace, e.g. InventoryUtility")
    parser.add_argument("method_name")
    parser.add_argument("overload", nargs="?", type=int, help="only the Nth method with that name")
    args = parser.parse_args()
    dll: Path = args.dll
    type_name: str = args.type_name
    method_name: str = args.method_name
    which: int | None = args.overload

    pe = dnfile.dnPE(str(dll))
    md = pe.net.mdtables if pe.net else None
    type_defs = md.TypeDef if md else None
    if md is None or type_defs is None:
        sys.exit(f"{dll} is not a .NET assembly")
    data = dll.read_bytes()
    names = TokenNames(md)
    count = 0
    for t in type_defs:
        if str(t.TypeName) != type_name:
            continue
        for m in t.MethodList:
            row = m.row
            if row is None or str(row.Name) != method_name:
                continue
            count += 1
            if which is not None and count != which:
                continue
            body = method_body(data, pe.get_offset_from_rva(row.Rva))
            print(f"== {type_name}::{method_name} #{count} ({len(body)} bytes)")
            print("\n".join(decode(body, names)))
    if count == 0:
        sys.exit(f"no method {type_name}::{method_name} in {dll}")


if __name__ == "__main__":
    main()
