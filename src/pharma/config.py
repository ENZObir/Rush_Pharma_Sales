"""Chargement de config/settings.yaml en un objet Settings."""

from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SETTINGS_FILE = ROOT / "config" / "settings.yaml"


@dataclass(frozen=True)
class Settings:
    raw_dir: Path
    external_dir: Path
    processed_dir: Path
    template: Path
    output: Path
    figures_dir: Path
    raw_files: dict[str, str]
    date_formats: dict[str, str]
    atc_groups: list[str]
    quality: dict
    forecast: dict
    external: dict


def load_settings(path: Path = SETTINGS_FILE) -> Settings:
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    paths = {k: ROOT / v for k, v in cfg["paths"].items()}
    return Settings(
        raw_dir=paths["raw"],
        external_dir=paths["external"],
        processed_dir=paths["processed"],
        template=paths["template"],
        output=paths["output"],
        figures_dir=paths["figures"],
        raw_files=cfg["raw_files"],
        date_formats=cfg["date_formats"],
        atc_groups=cfg["atc_groups"],
        quality=cfg["quality"],
        forecast=cfg["forecast"],
        external=cfg.get("external") or {},
    )
