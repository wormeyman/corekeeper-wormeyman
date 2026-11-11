#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.14"
# ///
"""Check each commit of a Core Keeper mod branch against its parent: compile, analyzers and formatting.

For every commit given, the mod's scripts are exported for the commit and for its parent, then built
with the .NET SDK in Docker against the game's DLLs (mounted read-only). A commit passes when it adds
no compiler errors, no .NET analyzer warnings (compared without line numbers) and no whitespace
problems in the files it changes. Problems already in the code are left alone, so this works on
other people's mods.

The work folder must be under your home folder: Docker Desktop on Linux shares only that.

Usage:
    uv run tools/modcheck/modcheck.py --repo <mod repo> --scripts <scripts folder in the repo>
        [--dep <scripts folder of a mod it needs>]... [--style <editorconfig>] <commit>...
"""

import argparse
import io
import re
import shutil
import subprocess
import sys
import tarfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

HERE = Path(__file__).resolve().parent
IMAGE = "mcr.microsoft.com/dotnet/sdk:10.0"
DEFAULT_MANAGED = Path.home() / ".local/share/Steam/steamapps/common/Core Keeper/CoreKeeper_Data/Managed"
DEFAULT_WORK = Path.home() / ".cache/corekeeper-modcheck"
DIAGNOSTIC = re.compile(r"^/work/[^/]+/(?P<file>[^(]+)\(\d+,\d+\): (?P<kind>error|warning) (?P<rest>.*?)(?: \[.*)?$")


@dataclass(frozen=True)
class Setup:
    repo: Path
    scripts: str
    work: Path
    managed: Path
    git: str
    docker: str


def find(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        sys.exit(f"{name} is not on PATH")
    return path


def run(command: list[str], data: bytes | None = None) -> bytes:
    # The executables are full paths from shutil.which; the arguments are this script's own or the user's.
    result = subprocess.run(command, input=data, capture_output=True, check=False)  # noqa: S603
    if result.returncode:
        sys.exit(f"{' '.join(command[:4])} ... failed:\n{result.stderr.decode(errors='replace')}")
    return result.stdout


def export(setup: Setup, rev: str, out: Path) -> None:
    """Write the mod's scripts folder as it was at `rev` into `out`."""
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    archive = run([setup.git, "-C", str(setup.repo), "archive", rev, setup.scripts])
    base = PurePosixPath(setup.scripts)
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        members: list[tarfile.TarInfo] = []
        for member in tar.getmembers():
            path = PurePosixPath(member.name)
            if not path.is_relative_to(base):  # the archive also lists the parent folders
                continue
            relative = path.relative_to(base)
            if relative != PurePosixPath("."):
                member.name = str(relative)
                members.append(member)
        tar.extractall(out, members=members, filter="data")


def in_container(setup: Setup, command: list[str]) -> str:
    """Run `command` in the .NET SDK container on a copy of the work folder; return its output.

    The command goes to bash as separate arguments ("$@"), never as shell text, because file names
    come from the mod's repository. The container gets no network.
    """
    copy_then_run = 'cp -r /src /work && cd /work && exec "$@"'
    result = subprocess.run(  # noqa: S603  (full path to docker; no shell parses the arguments)
        [setup.docker, "run", "--rm", "--network", "none",
         "--volume", f"{setup.work}:/src:ro", "--volume", f"{setup.managed}:/game:ro",
         IMAGE, "bash", "-c", copy_then_run, "bash", *command],
        capture_output=True, text=True, check=False,
    )  # fmt: skip
    return result.stdout + result.stderr


def diagnostics(log: str, kind: str) -> set[str]:
    found: set[str] = set()
    for line in log.splitlines():
        match = DIAGNOSTIC.match(line.strip())
        if match and match["kind"] == kind:
            found.add(f"{match['file']}: {match['rest']}")
    return found


def check(setup: Setup, rev: str) -> bool:
    export(setup, f"{rev}~1", setup.work / "before")
    export(setup, rev, setup.work / "after")
    build = ["dotnet", "build", "analyze.csproj", "-nologo", "-v:q", "-clp:NoSummary"]
    before, after = (in_container(setup, [*build, f"-p:ModSrc={side}"]) for side in ("before", "after"))
    changed = run([setup.git, "-C", str(setup.repo), "diff", "--name-only", "-z", f"{rev}~1", rev, "--", setup.scripts])
    files = [
        f"after/{PurePosixPath(name).relative_to(setup.scripts)}"
        for name in changed.decode().split("\0")
        if name.endswith(".cs")
    ]
    whitespace: list[str] = []
    if files:
        fmt = in_container(
            setup, ["dotnet", "format", "whitespace", ".", "--folder", "--verify-no-changes", "--include", *files]
        )
        whitespace = [line.strip() for line in fmt.splitlines() if "WHITESPACE" in line]
    new_errors = diagnostics(after, "error") - diagnostics(before, "error")
    new_warnings = diagnostics(after, "warning") - diagnostics(before, "warning")
    title = run([setup.git, "-C", str(setup.repo), "log", "-1", "--format=%h %s", rev]).decode().strip()
    passed = not (new_errors or new_warnings or whitespace)
    print(f"{'PASS' if passed else 'FAIL'}  {title}")
    for label, items in (("new error", new_errors), ("new warning", new_warnings), ("format", set(whitespace))):
        for item in sorted(items):
            print(f"      {label}: {item}")
    return passed


def prepare(work: Path, deps: list[Path], style: Path) -> None:
    work.mkdir(parents=True, exist_ok=True)
    shutil.copy(HERE / "analyze.csproj", work / "analyze.csproj")
    shutil.copy(style, work / ".editorconfig")
    shutil.rmtree(work / "deps", ignore_errors=True)
    for i, dep in enumerate(deps):
        shutil.copytree(dep, work / "deps" / str(i))


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("commits", nargs="+", help="commits to check, each against its parent")
    parser.add_argument("--repo", type=Path, required=True, help="the mod's git repository")
    parser.add_argument("--scripts", required=True, help="the mod's scripts folder, relative to the repo")
    parser.add_argument("--dep", type=Path, action="append", default=[], help="scripts of a mod it depends on")
    parser.add_argument("--style", type=Path, default=HERE / "reishyousose.editorconfig", help="house style")
    parser.add_argument("--managed", type=Path, default=DEFAULT_MANAGED, help="the game's CoreKeeper_Data/Managed")
    parser.add_argument("--work", type=Path, default=DEFAULT_WORK, help="work folder, under your home folder")
    args = parser.parse_args()
    deps: list[Path] = args.dep
    work: Path = args.work.resolve()
    prepare(work, deps, args.style)
    setup = Setup(
        args.repo.resolve(), args.scripts.strip("/"), work, args.managed.resolve(), find("git"), find("docker")
    )
    commits: list[str] = args.commits
    results = [check(setup, rev) for rev in commits]
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
