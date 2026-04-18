from __future__ import annotations

import json
from pathlib import Path

from citation_agent.models.schemas import PipelineArtifacts


def write_audit_json(path: str | Path, artifacts: PipelineArtifacts) -> None:
    output_path = Path(path)
    output_path.write_text(json.dumps(artifacts.to_json_dict(), indent=2), encoding="utf-8")
