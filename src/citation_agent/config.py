from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import json
import tomllib
from typing import Any


@dataclass(slots=True)
class RetrievalConfig:
    lexical_weight: float = 0.65
    semantic_weight: float = 0.35
    top_k: int = 5


@dataclass(slots=True)
class VerificationConfig:
    direct_support_threshold: float = 0.68
    partial_support_threshold: float = 0.5
    auto_insert_threshold: float = 0.65


@dataclass(slots=True)
class EditingConfig:
    replacement_mode: bool = False
    backup_suffix: str = ".bak"


@dataclass(slots=True)
class CitationAgentConfig:
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    verification: VerificationConfig = field(default_factory=VerificationConfig)
    editing: EditingConfig = field(default_factory=EditingConfig)

    @classmethod
    def load(cls, path: str | Path | None) -> "CitationAgentConfig":
        if path is None:
            return cls()

        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        if config_path.suffix in {".toml", ".tml"}:
            data = tomllib.loads(config_path.read_text(encoding="utf-8"))
        elif config_path.suffix == ".json":
            data = json.loads(config_path.read_text(encoding="utf-8"))
        else:
            raise ValueError("Config must be TOML or JSON for this build")

        return cls(
            retrieval=RetrievalConfig(**data.get("retrieval", {})),
            verification=VerificationConfig(**data.get("verification", {})),
            editing=EditingConfig(**data.get("editing", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "retrieval": self.retrieval.__dict__,
            "verification": self.verification.__dict__,
            "editing": self.editing.__dict__,
        }
