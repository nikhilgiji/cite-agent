from __future__ import annotations

from pathlib import Path
import re


INCLUDE_PATTERN = re.compile(
    r"\\(?:input|include|subfile)\{(?P<target>[^}]+)\}",
    re.IGNORECASE,
)


def resolve_include(base_file: Path, target: str) -> Path:
    candidate = (base_file.parent / target).resolve()
    if candidate.suffix:
        return candidate
    return candidate.with_suffix(".tex")


def build_dependency_graph(tex_files: list[Path]) -> dict[str, list[str]]:
    graph: dict[str, list[str]] = {}
    tex_set = {path.resolve() for path in tex_files}

    for tex_file in tex_files:
        content = tex_file.read_text(encoding="utf-8", errors="ignore")
        dependencies: list[str] = []
        for match in INCLUDE_PATTERN.finditer(content):
            include_path = resolve_include(tex_file, match.group("target"))
            if include_path in tex_set:
                dependencies.append(str(include_path))
        graph[str(tex_file.resolve())] = dependencies
    return graph
