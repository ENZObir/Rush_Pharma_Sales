"""DataQualityReport : findings typés, sérialisés tels quels dans la feuille « État des données »."""

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class Finding:
    source: str
    type: str
    detail: str
    decision: str
    reason: str


@dataclass
class DataQualityReport:
    findings: list[Finding] = field(default_factory=list)

    def add(self, source: str, type: str, detail: str, decision: str, reason: str) -> None:
        self.findings.append(Finding(source, type, detail, decision, reason))

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame([vars(f) for f in self.findings],
                            columns=["source", "type", "detail", "decision", "reason"])
