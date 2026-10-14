#!/usr/bin/env python3
"""Render one file's unified diff as an escaped, aligned red/green HTML fragment."""
import argparse
import html
import re
from itertools import zip_longest
from pathlib import Path

HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)$")


def parse(patch):
    lines = patch.split("\n")
    result = []
    i = 0
    files = sum(line.startswith("diff --git ") for line in lines)
    if files > 1:
        raise ValueError("Render one file at a time, not a multi-file patch")
    while i < len(lines):
        match = HUNK.match(lines[i])
        if not match:
            i += 1
            continue
        old, new = int(match[1]), int(match[3])
        old_left, new_left = int(match[2] or 1), int(match[4] or 1)
        rows, deleted, added = [], [], []
        last = []

        def flush():
            rows.extend(zip_longest(deleted, added))
            deleted.clear()
            added.clear()

        heading = lines[i]
        i += 1
        while i < len(lines):
            line = lines[i]
            if line.startswith("\\ No newline at end of file"):
                for cell in last:
                    cell["no_newline"] = True
                i += 1
                continue
            if old_left == 0 and new_left == 0:
                if line.startswith((" ", "+", "-")):
                    raise ValueError("Hunk contains more lines than its header declares")
                break
            if not line or line[0] not in " +-":
                raise ValueError(f"Incomplete or invalid hunk near line {i + 1}")
            sign, content = line[0], line[1:]
            if sign == " ":
                flush()
                left = {"number": old, "text": content, "kind": "context"}
                right = {"number": new, "text": content, "kind": "context"}
                rows.append((left, right))
                old += 1
                new += 1
                old_left -= 1
                new_left -= 1
                last = [left, right]
            elif sign == "-":
                cell = {"number": old, "text": content, "kind": "del"}
                deleted.append(cell)
                old += 1
                old_left -= 1
                last = [cell]
            else:
                cell = {"number": new, "text": content, "kind": "add"}
                added.append(cell)
                new += 1
                new_left -= 1
                last = [cell]
            if old_left < 0 or new_left < 0:
                raise ValueError("Hunk contains more lines than its header declares")
            i += 1
        if old_left or new_left:
            raise ValueError("Hunk is truncated; do not fabricate missing code")
        flush()
        result.append({"header": heading, "rows": rows})
    return result


def cells(cell, right=False):
    border = " right-start" if right else ""
    if cell is None:
        return f'<td class="ln gap{border}"></td><td class="sign gap"></td><td class="code gap"></td>'
    kind = cell["kind"]
    sign = {"del": "−", "add": "+", "context": ""}[kind]
    note = '<span class="no-newline">文件末尾无换行</span>' if cell.get("no_newline") else ""
    return (f'<td class="ln {kind}{border}">{cell["number"]}</td>'
            f'<td class="sign {kind}">{sign}</td>'
            f'<td class="code {kind}"><code>{html.escape(cell["text"])}</code>{note}</td>')


def render(patch, old_label="旧代码 / base", new_label="新代码 / head", hunk_ids=None):
    hunks = parse(patch)
    if hunk_ids is not None:
        if len(hunk_ids) != len(hunks):
            raise ValueError("Each rendered hunk must have exactly one supplied ID")
        if len(set(hunk_ids)) != len(hunk_ids) or any(
            not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]*", value) for value in hunk_ids
        ):
            raise ValueError("Hunk IDs must be unique safe HTML identifiers")
    if not hunks:
        return '<div class="diff-view"><div class="diff-empty">没有文本改动块；请单独说明文件级变化及审查限制。</div></div>'
    output = ['<div class="diff-view" role="region" aria-label="左右代码对比" tabindex="0">',
              '<table class="diff-table"><colgroup><col class="line-col"><col class="sign-col"><col><col class="line-col"><col class="sign-col"><col></colgroup>',
              '<thead><tr>', f'<th colspan="3" scope="colgroup">{html.escape(old_label)}</th>',
              f'<th colspan="3" scope="colgroup" class="right-start">{html.escape(new_label)}</th>',
              '</tr></thead><tbody>']
    for index, hunk in enumerate(hunks):
        identifier = hunk_ids[index] if hunk_ids is not None else None
        anchor = f' id="diff-{identifier}"' if identifier else ""
        link = f' · <a href="#note-{identifier}">{identifier}：查看说明</a>' if identifier else ""
        output.append(f'<tr class="hunk"{anchor}><td colspan="6">{html.escape(hunk["header"])}{link}</td></tr>')
        for left, right in hunk["rows"]:
            output.append('<tr>' + cells(left) + cells(right, right=True) + '</tr>')
    output.append('</tbody></table></div>')
    return "\n".join(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--old-label", default="旧代码 / base")
    parser.add_argument("--new-label", default="新代码 / head")
    parser.add_argument("--hunk-ids", nargs="+", help="One stable review ID per hunk, in order")
    args = parser.parse_args()
    try:
        # Preserve source carriage returns rather than silently normalizing code.
        with open(args.input, encoding="utf-8", newline="") as source:
            patch = source.read()
        fragment = render(patch, args.old_label, args.new_label, args.hunk_ids)
        target = Path(args.out)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(fragment + "\n", encoding="utf-8")
        print(f"Rendered split diff: {target}")
    except (OSError, ValueError) as error:
        parser.exit(1, f"Cannot render diff: {error}\n")


if __name__ == "__main__":
    main()
