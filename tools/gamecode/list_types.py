#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.14"
# dependencies = ["dnfile"]
# ///
"""List type names (and their field names) matching a regex in .NET DLLs. Read only."""
import re, sys
import dnfile
pat = re.compile(sys.argv[1], re.I)
for dll in sys.argv[2:]:
    md = dnfile.dnPE(dll).net.mdtables
    for t in md.TypeDef:
        name = str(t.TypeName)
        if pat.search(name):
            fields = [str(f.row.Name) for f in t.FieldList][:12]
            print(f"{dll.split('/')[-1]}: {t.TypeNamespace}.{name}  {fields}")
