from pathlib import Path
import tempfile
import unittest

from citation_agent.config import CitationAgentConfig
from citation_agent.pipeline import run_pipeline
from citation_agent.report.text_report import render_existing_citation_text_report


class TestVerifyExisting(unittest.TestCase):
    def test_existing_citation_report_flags_supported_and_missing_keys(self) -> None:
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
ImageNet was introduced in 2009 and is a widely used benchmark \cite{imagenet2009}.
Transformers are universally optimal for every task \cite{missingkey}.
\bibliography{refs}
\end{document}
""".strip(),
                encoding="utf-8",
            )

            artifacts = run_pipeline(tmp_path, None, [str((tmp_path / "refs.bib").resolve())], CitationAgentConfig())
            results = artifacts.existing_citation_results
            report = render_existing_citation_text_report(results)

            self.assertEqual(len(results), 2)
            self.assertTrue(any(result.status == "supported" for result in results))
            self.assertTrue(any(result.status == "missing_key" for result in results))
            self.assertTrue(all(result.line_number >= 1 for result in results))
            self.assertIn("SUPPORTED", report)
            self.assertIn("MISSING_KEY", report)
            self.assertIn("Line:", report)
