from __future__ import annotations

from pathlib import Path
import re

from citation_agent.models.schemas import ProjectAnalysis
from citation_agent.parse.tex_graph import build_dependency_graph


BIB_DECLARATION_PATTERN = re.compile(r"\\(?:bibliography|addbibresource)\{([^}]+)\}", re.IGNORECASE)
CITATION_COMMAND_PATTERN = re.compile(r"\\([A-Za-z]*cite[A-Za-z]*|cite)\{", re.IGNORECASE)


def find_tex_files(project_root: Path) -> list[Path]:
    return sorted(project_root.rglob("*.tex"))


def detect_main_tex(tex_files: list[Path]) -> Path | None:
    scored: list[tuple[int, Path]] = []
    for tex_file in tex_files:
        text = tex_file.read_text(encoding="utf-8", errors="ignore")
        score = 0
        if r"\documentclass" in text:
            score += 5
        if r"\begin{document}" in text:
            score += 5
        if r"\bibliography{" in text or r"\addbibresource{" in text:
            score += 2
        if score:
            scored.append((score, tex_file))
    if not scored:
        return tex_files[0] if tex_files else None
    scored.sort(key=lambda item: (-item[0], str(item[1])))
    return scored[0][1]


def detect_bibliography_declarations(tex_files: list[Path], project_root: Path) -> tuple[list[str], list[str]]:
    declarations: list[str] = []
    bib_files: set[str] = set()
    for tex_file in tex_files:
        text = tex_file.read_text(encoding="utf-8", errors="ignore")
        for match in BIB_DECLARATION_PATTERN.finditer(text):
            declarations.append(match.group(0))
            raw_targets = [part.strip() for part in match.group(1).split(",")]
            for target in raw_targets:
                bib_path = project_root / target
                if bib_path.suffix != ".bib":
                    bib_path = bib_path.with_suffix(".bib")
                bib_files.add(str(bib_path.resolve()))
    return sorted(bib_files), declarations


def detect_citation_commands(tex_files: list[Path]) -> list[str]:
    commands: set[str] = set()
    for tex_file in tex_files:
        text = tex_file.read_text(encoding="utf-8", errors="ignore")
        for match in CITATION_COMMAND_PATTERN.finditer(text):
            commands.add(match.group(1))
    return sorted(commands)


def detect_ieee_like(tex_files: list[Path], bib_files: list[str]) -> bool:
    for tex_file in tex_files:
        text = tex_file.read_text(encoding="utf-8", errors="ignore").lower()
        if "ieeetran" in text or "style=ieee" in text or "ieee" in text and "bibliographystyle" in text:
            return True
    return any("ieee" in Path(path).name.lower() for path in bib_files)


def analyze_project(project_root: str | Path) -> ProjectAnalysis:
    root = Path(project_root).resolve()
    tex_files = find_tex_files(root)
    main_tex = detect_main_tex(tex_files)
    bib_files, declarations = detect_bibliography_declarations(tex_files, root)
    citation_commands = detect_citation_commands(tex_files)
    return ProjectAnalysis(
        project_root=str(root),
        tex_files=[str(path.resolve()) for path in tex_files],
        main_tex=str(main_tex.resolve()) if main_tex else None,
        dependency_graph=build_dependency_graph(tex_files),
        bibliography_files=bib_files,
        bibliography_declarations=declarations,
        citation_commands=citation_commands,
        ieee_like=detect_ieee_like(tex_files, bib_files),
    )
