"""Deterministic offline tool implementations.

These are the harness-side tools a stub agent can call. They operate on a
plain dict workspace {relpath: content} so runs are hermetic, offline and
reproducible. Tools cost real tokens: the harness accounts their output as
part of the next call's context (and as cache re-reads in later calls),
which is exactly the cost dimension the paper studies.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


class ToolError(Exception):
    pass


@dataclass
class ToolResult:
    name: str
    args: dict
    output: str

    def render(self) -> str:
        """Deterministic rendering of the tool result for the LLM context."""
        arg_str = ", ".join(f"{k}={v}" for k, v in sorted(self.args.items()))
        return f"[tool:{self.name}({arg_str})]\n{self.output}\n[/tool:{self.name}]"


# --- compaction (paper: "tool output compaction", near-lossless) -----------

_TEMPLATE_RUN_MIN = 3


def compact_lines(text: str) -> str:
    """Collapse runs of structurally identical lines into one summary line.

    Lines are templated by replacing digits with '#'; a run of >= 3 lines
    sharing a template becomes '[N similar lines: <template>]'. Signal lines
    (unique templates, e.g. 'secret=...' or 'where=...') survive verbatim,
    which is what makes this compaction near-lossless the way the paper's
    technique claims to be.
    """
    lines = text.splitlines()
    trailing_nl = text.endswith("\n")

    def template(line: str) -> str:
        return re.sub(r"\d+", "#", line)

    out: list[str] = []
    i = 0
    while i < len(lines):
        j = i
        while j < len(lines) and template(lines[j]) == template(lines[i]):
            j += 1
        run = lines[i:j]
        if len(run) >= _TEMPLATE_RUN_MIN:
            out.append(f"[{len(run)} similar lines: {template(run[0])}]")
        else:
            out.extend(run)
        i = j
    result = "\n".join(out)
    return result + "\n" if trailing_nl else result


# --- tools -----------------------------------------------------------------

def tool_list_dir(workspace: dict, path: str = "") -> str:
    path = path.strip("/")
    prefix = path + "/" if path else ""
    entries: set[str] = set()
    for rel in workspace:
        if not rel.startswith(prefix):
            continue
        rest = rel[len(prefix):]
        if "/" in rest:
            entries.add(rest.split("/", 1)[0] + "/")
        else:
            entries.add(rest)
    return "\n".join(sorted(entries)) if entries else "(empty)"


def tool_read_file(workspace: dict, path: str) -> str:
    return workspace[_resolve(workspace, path)]


def tool_grep(workspace: dict, pattern: str, path: str = "") -> str:
    """Search all files (or one file) for a substring. Returns 'path:line' hits."""
    path = path.strip("/")
    hits: list[str] = []
    if path:
        names = [_resolve(workspace, path)]
    else:
        names = sorted(workspace)
    for name in names:
        for i, line in enumerate(workspace[name].splitlines(), 1):
            if pattern in line:
                hits.append(f"{name}:{i}: {line}")
    return "\n".join(hits) if hits else "(no matches)"


def tool_write_file(workspace: dict, path: str, content: str) -> str:
    workspace[path.strip("/")] = content
    return f"ok: wrote {len(content)} chars to {path.strip('/')}"


def _resolve(workspace: dict, path: str) -> str:
    path = path.strip("/")
    if path not in workspace:
        raise ToolError(f"no such file: {path}")
    return path


TOOL_SPECS = {
    # name -> (schema description text the harness puts in context, callable)
    "list_dir": (
        "list_dir(path) -> names of files and subdirectories under path",
        tool_list_dir,
    ),
    "read_file": (
        "read_file(path) -> full file content",
        tool_read_file,
    ),
    "grep": (
        "grep(pattern, path='') -> 'path:line: text' for every line containing pattern",
        tool_grep,
    ),
    "write_file": (
        "write_file(path, content) -> creates/overwrites a file, returns ok message",
        tool_write_file,
    ),
}


class ToolBox:
    """Executes ToolCalls against a workspace, honoring harness settings:
    optional near-lossless output compaction and a hard character cap."""

    def __init__(
        self,
        workspace: dict,
        max_output_chars: int | None = None,
        compact: bool = False,
    ):
        self.workspace = workspace
        self.max_output_chars = max_output_chars
        self.compact = compact

    def execute(self, call) -> ToolResult:
        name, args = call.name, call.args
        if name not in TOOL_SPECS:
            raise ToolError(f"unknown tool: {name}")
        fn = TOOL_SPECS[name][1]
        output = fn(self.workspace, **args)
        if self.compact:
            output = compact_lines(output)
        if self.max_output_chars is not None and len(output) > self.max_output_chars:
            output = output[: self.max_output_chars] + f"\n...[truncated {len(output) - self.max_output_chars} chars]"
        return ToolResult(name=name, args=args, output=output)
