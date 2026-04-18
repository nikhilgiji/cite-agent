from pathlib import Path
import tempfile
import unittest

from citation_agent.config import CitationAgentConfig
from citation_agent.edit.tex_rewriter import apply_citation_decisions
from citation_agent.pipeline import run_pipeline


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
            rewritten, inserted = apply_citation_decisions(tex, artifacts.claims, artifacts.decisions)

            self.assertGreaterEqual(inserted, 1)
            self.assertIn(r"\cite{imagenet2009}", rewritten)
