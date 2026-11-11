#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.14"
# dependencies = ["dnfile"]
# ///
"""Decode a .NET method body with resolved member names and constants. Read only.
Usage: il2.py <dll> <TypeName> <MethodName> [overload index]"""
import struct, sys
import dnfile

# operand sizes for one-byte opcodes (ECMA-335), name table abbreviated
NAMES = {0x00:"nop",0x01:"break",0x02:"ldarg.0",0x03:"ldarg.1",0x04:"ldarg.2",0x05:"ldarg.3",0x06:"ldloc.0",0x07:"ldloc.1",0x08:"ldloc.2",0x09:"ldloc.3",0x0A:"stloc.0",0x0B:"stloc.1",0x0C:"stloc.2",0x0D:"stloc.3",
0x0E:"ldarg.s",0x0F:"ldarga.s",0x10:"starg.s",0x11:"ldloc.s",0x12:"ldloca.s",0x13:"stloc.s",0x14:"ldnull",0x15:"ldc.i4.m1",0x1F:"ldc.i4.s",0x20:"ldc.i4",0x21:"ldc.i8",0x22:"ldc.r4",0x23:"ldc.r8",0x25:"dup",0x26:"pop",0x27:"jmp",0x28:"call",0x29:"calli",0x2A:"ret",
0x2B:"br.s",0x2C:"brfalse.s",0x2D:"brtrue.s",0x2E:"beq.s",0x2F:"bge.s",0x30:"bgt.s",0x31:"ble.s",0x32:"blt.s",0x33:"bne.un.s",0x34:"bge.un.s",0x35:"bgt.un.s",0x36:"ble.un.s",0x37:"blt.un.s",
0x38:"br",0x39:"brfalse",0x3A:"brtrue",0x3B:"beq",0x3C:"bge",0x3D:"bgt",0x3E:"ble",0x3F:"blt",0x40:"bne.un",0x41:"bge.un",0x42:"bgt.un",0x43:"ble.un",0x44:"blt.un",0x45:"switch",
0x46:"ldind.i1",0x47:"ldind.u1",0x48:"ldind.i2",0x49:"ldind.u2",0x4A:"ldind.i4",0x4B:"ldind.u4",0x4C:"ldind.i8",0x4D:"ldind.i",0x4E:"ldind.r4",0x4F:"ldind.r8",0x50:"ldind.ref",0x51:"stind.ref",0x52:"stind.i1",0x53:"stind.i2",0x54:"stind.i4",0x55:"stind.i8",0x56:"stind.r4",0x57:"stind.r8",
0x58:"add",0x59:"sub",0x5A:"mul",0x5B:"div",0x5C:"div.un",0x5D:"rem",0x5E:"rem.un",0x5F:"and",0x60:"or",0x61:"xor",0x62:"shl",0x63:"shr",0x64:"shr.un",0x65:"neg",0x66:"not",0x67:"conv.i1",0x68:"conv.i2",0x69:"conv.i4",0x6A:"conv.i8",0x6B:"conv.r4",0x6C:"conv.r8",0x6D:"conv.u4",0x6E:"conv.u8",
0x6F:"callvirt",0x70:"cpobj",0x71:"ldobj",0x72:"ldstr",0x73:"newobj",0x74:"castclass",0x75:"isinst",0x76:"conv.r.un",0x79:"unbox",0x7A:"throw",0x7B:"ldfld",0x7C:"ldflda",0x7D:"stfld",0x7E:"ldsfld",0x7F:"ldsflda",0x80:"stsfld",0x81:"stobj",
0x8C:"box",0x8D:"newarr",0x8E:"ldlen",0x8F:"ldelema",0x94:"ldelem.i4",0x9E:"stelem.i4",0xA3:"ldelem",0xA4:"stelem",0xA5:"unbox.any",0xD0:"ldtoken",0xD1:"conv.u2",0xD2:"conv.u1",0xD3:"conv.i",0xDC:"endfinally",0xDD:"leave",0xDE:"leave.s",0xE0:"conv.u"}
for i in range(9): NAMES[0x16+i] = f"ldc.i4.{i}"
TOKEN_OPS = {0x27,0x28,0x29,0x6F,0x70,0x71,0x72,0x73,0x74,0x75,0x79,0x7B,0x7C,0x7D,0x7E,0x7F,0x80,0x81,0x8C,0x8D,0x8F,0xA3,0xA4,0xA5,0xD0}
U8 = {0x0E,0x0F,0x10,0x11,0x12,0x13}
FE = {0x01:"ceq",0x02:"cgt",0x03:"cgt.un",0x04:"clt",0x05:"clt.un",0x06:("ldftn",4),0x09:("ldarg",2),0x0A:("ldarga",2),0x0B:("starg",2),0x0C:("ldloc",2),0x0D:("ldloca",2),0x0E:("stloc",2),0x15:("initobj",4),0x16:("constrained.",4),0x1C:("sizeof",4),0x1E:"readonly."}

dll, tname, mname = sys.argv[1:4]
which = int(sys.argv[4]) if len(sys.argv) > 4 else None
pe = dnfile.dnPE(dll); md = pe.net.mdtables
def tokname(tok):
    tbl, row = tok >> 24, tok & 0xFFFFFF
    try:
        if tbl == 0x06: m = md.MethodDef[row-1]; return f"{m.Name}"
        if tbl == 0x0A:
            r = md.MemberRef[row-1]; cls = r.Class.row
            cn = getattr(cls, "TypeName", None) or getattr(cls, "Name", "?")
            return f"{cn}::{r.Name}"
        if tbl == 0x04: return f"field {md.Field[row-1].Name}"
        if tbl == 0x2B: r = md.MethodSpec[row-1]; return f"spec->{tokname((0x06 if r.Method.table.name=='MethodDef' else 0x0A)<<24 | r.Method.row_index)}"
        if tbl in (0x01, 0x02): t = (md.TypeRef if tbl==1 else md.TypeDef)[row-1]; return f"type {t.TypeName}"
        if tbl == 0x70: return "string"
    except Exception as e: return f"tok {tok:#x} ({e})"
    return f"tok {tok:#x}"
n = 0
for t in md.TypeDef:
    if str(t.TypeName) != tname: continue
    for m in t.MethodList:
        if str(m.row.Name) != mname: continue
        n += 1
        if which is not None and n != which: continue
        off = pe.get_offset_from_rva(m.row.Rva); data = pe.__data__; h = data[off]
        if h & 3 == 2: size, code = h >> 2, off + 1
        else: size = struct.unpack_from("<I", data, off+4)[0]; code = off + ((struct.unpack_from("<H", data, off)[0] >> 12) * 4)
        b = data[code:code+size]; i = 0
        print(f"== {tname}::{mname} #{n} ({size} bytes)")
        while i < len(b):
            at = i; op = b[i]; i += 1
            if op == 0xFE:
                op2 = b[i]; i += 1; e = FE.get(op2, f"fe.{op2:#x}")
                if isinstance(e, tuple):
                    v = int.from_bytes(b[i:i+e[1]], "little"); i += e[1]
                    s = f"{e[0]} {tokname(v) if e[1]==4 else v}"
                else: s = e
            elif op in U8: s = f"{NAMES[op]} {b[i]}"; i += 1
            elif op == 0x1F: s = f"ldc.i4.s {struct.unpack_from('b', b, i)[0]}"; i += 1
            elif 0x2B <= op <= 0x37: v = struct.unpack_from('b', b, i)[0]; i += 1; s = f"{NAMES[op]} -> {i+v:#06x}"
            elif 0x38 <= op <= 0x44: v = struct.unpack_from('<i', b, i)[0]; i += 4; s = f"{NAMES[op]} -> {i+v:#06x}"
            elif op == 0x20: s = f"ldc.i4 {struct.unpack_from('<i', b, i)[0]}"; i += 4
            elif op == 0x21: s = f"ldc.i8 {struct.unpack_from('<q', b, i)[0]}"; i += 8
            elif op == 0x22: s = f"ldc.r4 {struct.unpack_from('<f', b, i)[0]}"; i += 4
            elif op == 0x23: s = f"ldc.r8 {struct.unpack_from('<d', b, i)[0]}"; i += 8
            elif op in TOKEN_OPS: s = f"{NAMES[op]} {tokname(struct.unpack_from('<I', b, i)[0])}"; i += 4
            elif op == 0xDD: v = struct.unpack_from('<i', b, i)[0]; i += 4; s = f"leave -> {i+v:#06x}"
            elif op == 0xDE: v = struct.unpack_from('b', b, i)[0]; i += 1; s = f"leave.s -> {i+v:#06x}"
            elif op == 0x45: cnt = struct.unpack_from('<I', b, i)[0]; i += 4 + 4*cnt; s = f"switch ({cnt})"
            elif op in NAMES: s = NAMES[op]
            else: s = f"?? {op:#04x}"; print(f"  {at:#06x} {s}"); break
            print(f"  {at:#06x} {s}")
