from pathlib import Path
import tempfile
import unittest

from citation_agent.config import CitationAgentConfig
from citation_agent.parse.tex_extract import extract_claims
from citation_agent.pipeline import run_pipeline
from citation_agent.report.text_report import (
    render_invalid_citations_report,
    render_manual_review_report,
    render_missing_citations_report,
    render_review_text_report,
)


class TestReportingAndSafety(unittest.TestCase):
    def test_structural_latex_is_not_treated_as_citation_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            tex = tmp_path / "main.tex"
            tex.write_text(
                r"""
\chapter{Main Part}
\section{Structure}
\label{sec:structure}
\printtumcsbibliography
This paragraph explains anaerobic digestion as a renewable energy process.
""".strip(),
                encoding="utf-8",
            )

            claims = extract_claims(tex, tmp_path)
            claim_texts = [claim.text for claim in claims if claim.needs_citation]

            self.assertEqual(len(claim_texts), 0)

    def test_review_report_contains_file_line_and_paragraph_information(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            (tmp_path / "refs.bib").write_text(
                """
@article{imagenet2009,
  title = {ImageNet: A large-scale hierarchical image database},
  author = {Deng, Jia and others},
  year = {2009}
}
""".strip(),
                encoding="utf-8",
            )
            (tmp_path / "main.tex").write_text(
                r"""
\documentclass{article}
\begin{document}
ImageNet was introduced in 2009 and is a widely used benchmark.
\bibliography{refs}
\end{document}
""".strip(),
                encoding="utf-8",
            )

            artifacts = run_pipeline(tmp_path, None, [str((tmp_path / "refs.bib").resolve())], CitationAgentConfig())
            report = render_review_text_report(artifacts)

            self.assertIn("Missing citations that can be added", report)
            self.assertIn("Line:", report)
            self.assertIn("Paragraph:", report)
            self.assertIn(str((tmp_path / "main.tex").resolve()), report)

    def test_focused_reports_render_expected_sections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            (tmp_path / "refs.bib").write_text(
                """
@article{imagenet2009,
  title = {ImageNet: A large-scale hierarchical image database},
  author = {Deng, Jia and others},
  year = {2009}
}
""".strip(),
                encoding="utf-8",
            )
            (tmp_path / "main.tex").write_text(
                r"""
\documentclass{article}
\begin{document}
ImageNet was introduced in 2009 and is a widely used benchmark \cite{missingkey}.
Transformers are universally optimal for every task.
\bibliography{refs}
\end{document}
""".strip(),
                encoding="utf-8",
            )

            artifacts = run_pipeline(tmp_path, None, [str((tmp_path / "refs.bib").resolve())], CitationAgentConfig())
            invalid_report = render_invalid_citations_report(artifacts)
            missing_report = render_missing_citations_report(artifacts)
            manual_report = render_manual_review_report(artifacts)

            self.assertIn("Invalid or Incorrect Citations Report", invalid_report)
            self.assertIn("Missing Citations Report", missing_report)
            self.assertIn("Manual Review Citations Report", manual_report)
