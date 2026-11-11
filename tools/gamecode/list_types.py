#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.14"
# dependencies = ["dnfile"]
# ///
"""List types whose name matches a regex in .NET DLLs, with their first field names. Read only.

Usage:
    uv run tools/gamecode/list_types.py <regex> <dll> [dll ...]
"""

import argparse
import re
import sys
from pathlib import Path

import dnfile

MAX_FIELDS = 12


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("pattern", help="case-insensitive regex for the type name")
    parser.add_argument("dlls", nargs="+", type=Path)
    args = parser.parse_args()
    pattern = re.compile(args.pattern, re.IGNORECASE)
    dlls: list[Path] = args.dlls
    for dll in dlls:
        net = dnfile.dnPE(str(dll)).net
        type_defs = net.mdtables.TypeDef if net and net.mdtables else None
        if type_defs is None:
            print(f"{dll.name}: not a .NET assembly", file=sys.stderr)
            continue
        for t in type_defs:
            name = str(t.TypeName)
            if pattern.search(name):
                fields = [str(f.row.Name) for f in t.FieldList if f.row is not None][:MAX_FIELDS]
                print(f"{dll.name}: {t.TypeNamespace}.{name}  {fields}")


if __name__ == "__main__":
    main()
