"""Volumes, parts et tendance pluriannuelle par groupe ATC."""

import pandas as pd


def volumes_and_shares(monthly: pd.DataFrame) -> pd.DataFrame:
    raise NotImplementedError


def yearly_trend(monthly: pd.DataFrame) -> pd.DataFrame:
    raise NotImplementedError
