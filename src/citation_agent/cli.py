from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Sequence

from citation_agent.config import CitationAgentConfig
from citation_agent.edit.bib_writer import append_bib_entries
from citation_agent.edit.diff_writer import unified_diff
from citation_agent.edit.tex_rewriter import apply_citation_decisions
from citation_agent.pipeline import run_pipeline, summarize_scan
from citation_agent.report.audit_json import write_audit_json
from citation_agent.report.text_report import write_existing_citation_text_report


LOGGER = logging.getLogger("citation_agent")


def _parse_bib_args(values: list[str] | None) -> list[str]:
    return [str(Path(value).resolve()) for value in values or []]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="citation-agent")
    parser.add_argument("--config", help="Path to TOML or JSON config", default=None)
    parser.add_argument("--log-level", default="INFO")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for name in ("scan", "audit", "apply", "verify-existing"):
        subparser = subparsers.add_parser(name)
        subparser.add_argument("--project", required=True)
        subparser.add_argument("--pdfs", default=None)
        subparser.add_argument("--bib", action="append", default=[])

    audit_parser = subparsers.choices["audit"]
    audit_parser.add_argument("--out", required=True)

    apply_parser = subparsers.choices["apply"]
    mode_group = apply_parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("--dry-run", action="store_true")
    mode_group.add_argument("--write", action="store_true")

    repair_parser = subparsers.add_parser("repair-bib")
    repair_parser.add_argument("--bib", action="append", required=True)
    repair_parser.add_argument("--pdfs", required=True)

    verify_parser = subparsers.choices["verify-existing"]
    verify_parser.add_argument("--out", required=True, help="Path to a plain text verification report")

    return parser


def _configure_logging(level: str) -> None:
    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO), format="%(levelname)s %(name)s: %(message)s")


def _run_scan(args: argparse.Namespace, config: CitationAgentConfig) -> int:
    artifacts = run_pipeline(args.project, args.pdfs, _parse_bib_args(args.bib), config)
    print(json.dumps(summarize_scan(artifacts), indent=2))
    return 0


def _run_audit(args: argparse.Namespace, config: CitationAgentConfig) -> int:
    artifacts = run_pipeline(args.project, args.pdfs, _parse_bib_args(args.bib), config)
    write_audit_json(args.out, artifacts)
    print(artifacts.markdown_report)
    return 0


def _run_apply(args: argparse.Namespace, config: CitationAgentConfig) -> int:
    artifacts = run_pipeline(args.project, args.pdfs, _parse_bib_args(args.bib), config)
    project_root = Path(args.project).resolve()
    changed_files: dict[str, str] = {}

    for tex_file in artifacts.analysis.tex_files:
        path = Path(tex_file)
        before = path.read_text(encoding="utf-8", errors="ignore")
        after, inserted = apply_citation_decisions(path, artifacts.claims, artifacts.decisions)
        if inserted <= 0 or before == after:
            continue
        changed_files[str(path)] = after
        if args.write:
            backup_path = path.with_suffix(path.suffix + config.editing.backup_suffix)
            backup_path.write_text(before, encoding="utf-8")
            path.write_text(after, encoding="utf-8")
        else:
            print(unified_diff(path.relative_to(project_root), before, after))

    if artifacts.added_bib_entries and _parse_bib_args(args.bib):
        bib_path = _parse_bib_args(args.bib)[0]
        if args.write:
            append_bib_entries(bib_path, artifacts.added_bib_entries)
        else:
            print(f"# Would append {len(artifacts.added_bib_entries)} bibliography entr(y/ies) to {bib_path}")

    if args.write:
        print(artifacts.markdown_report)
    return 0


def _run_repair_bib(args: argparse.Namespace, config: CitationAgentConfig) -> int:
    artifacts = run_pipeline(Path(args.bib[0]).parent, args.pdfs, _parse_bib_args(args.bib), config)
    if not artifacts.added_bib_entries:
        print("No safe bibliography repairs found.")
        return 0
    append_bib_entries(_parse_bib_args(args.bib)[0], artifacts.added_bib_entries)
    print(f"Appended {len(artifacts.added_bib_entries)} bibliography entr(y/ies).")
    return 0


def _run_verify_existing(args: argparse.Namespace, config: CitationAgentConfig) -> int:
    artifacts = run_pipeline(args.project, args.pdfs, _parse_bib_args(args.bib), config)
    write_existing_citation_text_report(args.out, artifacts.existing_citation_results)
    print(f"Wrote existing citation verification report to {args.out}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _configure_logging(args.log_level)
    config = CitationAgentConfig.load(args.config)

    if args.command == "scan":
        return _run_scan(args, config)
    if args.command == "audit":
        return _run_audit(args, config)
    if args.command == "apply":
        return _run_apply(args, config)
    if args.command == "repair-bib":
        return _run_repair_bib(args, config)
    if args.command == "verify-existing":
        return _run_verify_existing(args, config)
    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
