#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.14"
# dependencies = ["dnfile"]
# ///
"""List Type::Method names where the method name matches a regex, in .NET DLLs. Read only.

Usage:
    uv run tools/gamecode/list_methods.py <regex> <dll> [dll ...] [--type <regex>]
"""

import argparse
import re
import sys
from pathlib import Path

import dnfile


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("pattern", help="case-insensitive regex for the method name")
    parser.add_argument("dlls", nargs="+", type=Path)
    parser.add_argument("--type", dest="type_pattern", default="", help="only types whose name matches this regex")
    args = parser.parse_args()
    method_pattern = re.compile(args.pattern, re.IGNORECASE)
    type_pattern = re.compile(args.type_pattern, re.IGNORECASE)
    dlls: list[Path] = args.dlls
    for dll in dlls:
        net = dnfile.dnPE(str(dll)).net
        type_defs = net.mdtables.TypeDef if net and net.mdtables else None
        if type_defs is None:
            print(f"{dll.name}: not a .NET assembly", file=sys.stderr)
            continue
        for t in type_defs:
            if not type_pattern.search(str(t.TypeName)):
                continue
            for m in t.MethodList:
                if m.row is not None and method_pattern.search(str(m.row.Name)):
                    print(f"{dll.name}: {t.TypeNamespace}.{t.TypeName}::{m.row.Name}")


if __name__ == "__main__":
    main()
