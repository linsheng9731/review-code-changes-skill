#!/usr/bin/env python3
"""Collect a read-only Git review scope and stable hunk IDs using only Python/Git."""
import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def git(repo, *args):
    return subprocess.check_output(["git", "--literal-pathspecs", "-C", str(repo), *args], stderr=subprocess.PIPE)


def decode(data):
    return data.decode("utf-8", errors="replace")


def collect(repo, scope, base=None, head="HEAD"):
    repo = Path(decode(git(repo, "rev-parse", "--show-toplevel")).strip()).resolve()
    head_sha = decode(git(repo, "rev-parse", "--verify", head + "^{commit}")).strip()
    if scope == "branch":
        if not base:
            raise ValueError("branch scope requires --base")
        base_sha = decode(git(repo, "rev-parse", "--verify", base + "^{commit}")).strip()
        comparison_base = decode(git(repo, "merge-base", base_sha, head_sha)).strip()
        comparison = [comparison_base, head_sha]
    else:
        if base or head != "HEAD":
            raise ValueError("--base/--head only apply to branch scope")
        base_sha = comparison_base = head_sha
        comparison = {"all": [head_sha], "staged": ["--cached", head_sha], "worktree": []}[scope]
    options = ["diff", "--no-ext-diff", "--no-textconv", "--no-renames"]
    before = git(repo, *options, "--unified=0", *comparison, "--")
    names = git(repo, *options, "--name-only", "-z", *comparison, "--").split(b"\0")
    files, count = [], 0
    pattern = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)$", re.M)
    for name in filter(None, names):
        path = name.decode("utf-8", errors="surrogateescape")
        patch = git(repo, *options, "--unified=0", *comparison, "--", path)
        hunks = []
        for match in pattern.finditer(decode(patch)):
            count += 1
            hunks.append({"id": f"C{count:03d}",
                          "old_start": int(match[1]), "old_count": int(match[2] or 1),
                          "new_start": int(match[3]), "new_count": int(match[4] or 1),
                          "context": match[5].strip()})
        files.append({"path": path, "hunks": hunks,
                      "requires_file_annotation": not bool(hunks), "diff": decode(patch)})
    untracked = []
    if scope in ("all", "worktree"):
        untracked = [decode(p) for p in git(repo, "ls-files", "--others", "--exclude-standard", "-z").split(b"\0") if p]
    after = git(repo, *options, "--unified=0", *comparison, "--")
    if before != after:
        raise RuntimeError("Scope changed during collection; collect again")
    return {"repo": str(repo), "scope": scope, "base_sha": base_sha,
            "comparison_base_sha": comparison_base, "head_sha": head_sha,
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "tracked_diff_sha256": hashlib.sha256(before).hexdigest(),
            "hunk_count": count, "tracked_file_count": len(files),
            "files": files, "untracked_paths": untracked,
            "notes": ["Untracked contents require manual review and U IDs.",
                      "Renames are deletion/addition; reconcile old/new paths.",
                      "Files without text hunks need F IDs and explicit review limits.",
                      "Fingerprint excludes untracked content; recheck content before delivery."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--scope", choices=("branch", "all", "staged", "worktree"), default="all")
    parser.add_argument("--base")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    try:
        data = collect(args.repo, args.scope, args.base, args.head)
        output = Path(args.out).resolve()
        if output == Path(data["repo"]) or Path(data["repo"]) in output.parents:
            parser.error("Save inventory outside the reviewed repo to keep scope unchanged")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(data, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
        print(f"Collected {data['tracked_file_count']} tracked files / {data['hunk_count']} hunks / {len(data['untracked_paths'])} untracked paths")
    except (ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"Collection failed: {exc}\n")


if __name__ == "__main__":
    main()
