from pathlib import Path
import tempfile
import unittest

from citation_agent.ingest.tex_project import analyze_project


class TestTexProject(unittest.TestCase):
    def test_analyze_project_detects_main_graph_and_bib(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            (tmp_path / "sections").mkdir()
            (tmp_path / "sections" / "intro.tex").write_text("Intro text.\n", encoding="utf-8")
            (tmp_path / "refs.bib").write_text(
                "@article{smith2020,\n  title={A Paper},\n  author={Smith, Jane},\n  year={2020}\n}\n",
                encoding="utf-8",
            )
            (tmp_path / "main.tex").write_text(
                r"""
\documentclass{IEEEtran}
\begin{document}
\input{sections/intro}
\bibliography{refs}
\end{document}
""".strip(),
                encoding="utf-8",
            )

            analysis = analyze_project(tmp_path)

            self.assertEqual(analysis.main_tex, str((tmp_path / "main.tex").resolve()))
            self.assertIn(str((tmp_path / "refs.bib").resolve()), analysis.bibliography_files)
            self.assertTrue(analysis.ieee_like)
            self.assertIn(
                str((tmp_path / "sections" / "intro.tex").resolve()),
                analysis.dependency_graph[str((tmp_path / "main.tex").resolve())],
            )
