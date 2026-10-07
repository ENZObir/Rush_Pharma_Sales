"""Une fonction par feuille, signature (writer, data) -> None."""

import pandas as pd

from pharma.excel.writer import TemplateWriter


def write_data_quality(writer: TemplateWriter, report: pd.DataFrame) -> None:
    raise NotImplementedError


def write_sales_long(writer: TemplateWriter, long_df: pd.DataFrame) -> None:
    raise NotImplementedError


def write_descriptive(writer: TemplateWriter, stats: pd.DataFrame) -> None:
    raise NotImplementedError


def write_seasonality(writer: TemplateWriter, profile: pd.DataFrame) -> None:
    raise NotImplementedError


def write_forecast(writer: TemplateWriter, backtest: pd.DataFrame, forecast_next: pd.DataFrame) -> None:
    raise NotImplementedError


def write_summary(writer: TemplateWriter, data: dict[str, pd.DataFrame]) -> None:
    raise NotImplementedError
