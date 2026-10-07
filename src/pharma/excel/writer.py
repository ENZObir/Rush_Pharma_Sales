"""Ouvre le template et remplace uniquement les feuilles de données (tables nommées)."""

from pathlib import Path

import pandas as pd


class TemplateWriter:
    def __init__(self, template: Path, output: Path):
        self.template = template
        self.output = output

    def write_table(self, sheet: str, table_name: str, df: pd.DataFrame) -> None:
        raise NotImplementedError

    def save(self) -> None:
        raise NotImplementedError
