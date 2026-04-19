from pathlib import Path
import tempfile
import unittest

from citation_agent.config import CitationAgentConfig
from citation_agent.edit.tex_rewriter import apply_citation_decisions
from citation_agent.pipeline import run_pipeline, summarize_scan


class TestApplyPipeline(unittest.TestCase):
    def test_pipeline_inserts_supported_existing_bib_citation(self) -> None:
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
            tex = tmp_path / "main.tex"
            tex.write_text(
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

            self.assertTrue(any(decision.action == "inserted" for decision in artifacts.decisions))
            rewritten, inserted, removed = apply_citation_decisions(
                tex,
                artifacts.claims,
                artifacts.decisions,
                artifacts.existing_citation_results,
            )

            self.assertGreaterEqual(inserted, 1)
            self.assertEqual(removed, 0)
            self.assertIn(r"\cite{imagenet2009}", rewritten)

    def test_apply_replaces_missing_existing_citation_with_supported_one(self) -> None:
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
            tex = tmp_path / "main.tex"
            tex.write_text(
                r"""
\documentclass{article}
\begin{document}
ImageNet was introduced in 2009 and is a widely used benchmark \cite{missingkey}.
\bibliography{refs}
\end{document}
""".strip(),
                encoding="utf-8",
            )

            artifacts = run_pipeline(tmp_path, None, [str((tmp_path / "refs.bib").resolve())], CitationAgentConfig())
            rewritten, inserted, removed = apply_citation_decisions(
                tex,
                artifacts.claims,
                artifacts.decisions,
                artifacts.existing_citation_results,
            )

            self.assertGreaterEqual(removed, 1)
            self.assertGreaterEqual(inserted, 1)
            self.assertNotIn(r"\cite{missingkey}", rewritten)
            self.assertIn(r"\cite{imagenet2009}", rewritten)

    def test_scan_summary_counts_explicit_bib_argument(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            bib_path = tmp_path / "references.bib"
            bib_path.write_text(
                """
@article{ref1,
  title = {A Paper},
  author = {Doe, Jane},
  year = {2020}
}
""".strip(),
                encoding="utf-8",
            )
            (tmp_path / "main.tex").write_text(
                r"""
\documentclass{article}
\begin{document}
This sentence discusses a benchmark introduced in 2020.
\end{document}
""".strip(),
                encoding="utf-8",
            )

            artifacts = run_pipeline(tmp_path, None, [str(bib_path.resolve())], CitationAgentConfig())
            summary = summarize_scan(artifacts)

            self.assertEqual(summary["bib_files"], 1)
