#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.14"
# dependencies = ["dnfile"]
# ///
"""List Type::Method names matching a regex in .NET DLLs. Read only."""
import re, sys
import dnfile
pat = re.compile(sys.argv[1], re.I)
for dll in sys.argv[2:]:
    md = dnfile.dnPE(dll).net.mdtables
    for t in md.TypeDef:
        for m in t.MethodList:
            n = str(m.row.Name)
            if pat.search(n) or pat.search(str(t.TypeName)) and pat.search(n):
                print(f"{dll.split('/')[-1]}: {t.TypeNamespace}.{t.TypeName}::{n}")
