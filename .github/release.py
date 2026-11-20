"""Publish each new mainline commit as a tag, a changelog entry and a GitHub release."""

import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path


METADATA = "refs/remotes/origin/releases"
FIRST_VERSION = "0.1.0"


def git(*args, input=None):
    return subprocess.check_output(["git", *args], input=input, text=True).rstrip("\n")


def succeeds(*args):
    return subprocess.run(args, stdout=subprocess.DEVNULL).returncode == 0


def changes_for(commit):
    # Include the feature commits brought in by a merge in its release notes.
    parents = git("show", "-s", "--format=%P", commit).split()
    revision = f"{parents[0]}..{commit}" if parents else commit
    changes = git("rev-list", "--reverse", "--no-merges", revision).splitlines() or [commit]
    return [(git("show", "-s", "--format=%s", sha), git("show", "-s", "--format=%b", sha))
            for sha in changes]


def next_version(previous, changes):
    if previous is None:
        return FIRST_VERSION
    major, minor, patch = map(int, previous.split("."))
    for subject, body in changes:
        if re.match(r"^[\w-]+(?:\([^)]*\))?!:", subject) or re.search(r"^BREAKING[ -]CHANGE:", body, re.M):
            return f"{major + 1}.0.0"
    if any(re.match(r"^feat(?:\([^)]*\))?:", subject) for subject, _ in changes):
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def render_notes(changes):
    lines = []
    for subject, body in changes:
        lines.append(f"- {subject}")
        for line in body.splitlines():
            if line.startswith("- "):
                lines.append(f"  {line}")
            elif re.match(r"^BREAKING[ -]CHANGE:", line):
                lines.append(f"  - {line}")
    return "\n".join(lines)


def publish_notes(tag, notes):
    if succeeds("gh", "release", "view", tag, "--json", "tagName"):
        return
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "notes.md"
        path.write_text(notes + "\n", encoding="utf-8")
        subprocess.run(["gh", "release", "create", tag, "--verify-tag",
                        "--title", tag, "--notes-file", str(path)], check=True)


def metadata_commit(parent, version, changelog):
    # Build the two-file releases branch without changing the source checkout.
    entries = []
    for name, content in (("CHANGELOG.md", changelog), ("VERSION", version)):
        blob = git("hash-object", "-w", "--stdin", input=content + "\n")
        entries.append(f"100644 blob {blob}\t{name}\n")
    tree = git("mktree", input="".join(entries))
    parents = ["-p", parent] if parent else []
    return git("commit-tree", tree, *parents, "-m", f"Release v{version}")


def main():
    target = git("rev-parse", "HEAD")
    parent = previous = None
    history = ""
    if succeeds("git", "show-ref", "--verify", "--quiet", METADATA):
        parent = git("rev-parse", METADATA)
        previous = git("show", f"{parent}:VERSION")
        previous_tag = f"v{previous}"
        last = git("rev-parse", f"refs/tags/{previous_tag}^{{commit}}")
        history = git("show", f"{parent}:CHANGELOG.md").removeprefix("# Changelog\n\n")
        # Repair a release if the GitHub API failed after the atomic Git push.
        publish_notes(previous_tag, render_notes(changes_for(last)))
        if succeeds("git", "merge-base", "--is-ancestor", target, last):
            return
        if not succeeds("git", "merge-base", "--is-ancestor", last, target):
            raise SystemExit("Main has diverged from the published version.")
        commits = git("rev-list", "--first-parent", "--reverse", f"{last}..{target}").splitlines()
    else:
        # Versioning starts when the publisher first lands on main.
        first = git("log", "--first-parent", "--reverse", "--diff-filter=A",
                    "--format=%H", target, "--", ".github/release.py").splitlines()[0]
        commits = [first, *git("rev-list", "--first-parent", "--reverse", f"{first}..{target}").splitlines()]

    for commit in commits:
        changes = changes_for(commit)
        version = next_version(previous, changes)
        tag = f"v{version}"
        notes = render_notes(changes)
        date = datetime.now(timezone.utc).date()
        history = f"## {tag} ({date})\n\n{notes}\n\n{history}".rstrip()
        parent = metadata_commit(parent, version, f"# Changelog\n\n{history}")
        git("push", "--atomic", "origin", f"{commit}:refs/tags/{tag}", f"{parent}:refs/heads/releases")
        publish_notes(tag, notes)
        previous = version


if __name__ == "__main__":
    main()
