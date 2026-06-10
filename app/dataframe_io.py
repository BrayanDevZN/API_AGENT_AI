from io import BytesIO

import pandas as pd
import polars as pl


def _drop_empty_rows(df: pl.DataFrame) -> pl.DataFrame:
    if df.is_empty() or not df.columns:
        return df

    return df.filter(pl.any_horizontal(pl.all().is_not_null()))


def _drop_sparse_columns(df: pl.DataFrame, minimum_ratio: float = 0.7) -> pl.DataFrame:
    if df.is_empty() or not df.columns:
        return df

    threshold = int(df.height * minimum_ratio)
    keep_columns = [
        column
        for column in df.columns
        if df[column].is_not_null().sum() >= threshold
    ]
    return df.select(keep_columns) if keep_columns else pl.DataFrame()


def normalize_polars(df: pl.DataFrame, drop_sparse_columns: bool = False) -> pl.DataFrame:
    df = df.rename({column: str(column).strip() for column in df.columns})
    df = _drop_empty_rows(df)

    if drop_sparse_columns:
        df = _drop_sparse_columns(df)

    return df


def dataset_to_pandas(dataset: list[dict], drop_sparse_columns: bool = False) -> pd.DataFrame:
    if not dataset:
        return pd.DataFrame()

    df = pl.from_dicts(dataset, infer_schema_length=None)
    return normalize_polars(df, drop_sparse_columns=drop_sparse_columns).to_pandas()


def read_file_to_records(file) -> list[dict]:
    filename = file.filename.lower()

    if filename.endswith(".csv"):
        df = pl.read_csv(file.file, infer_schema_length=1000)
    elif filename.endswith(".json"):
        content = file.file.read()
        df = pl.read_json(BytesIO(content))
    elif filename.endswith(".xlsx") or filename.endswith(".xls"):
        df = pl.from_pandas(pd.read_excel(file.file))
    else:
        raise ValueError("Tipo de arquivo nao suportado. Use CSV, Excel ou JSON.")

    return normalize_polars(df).to_dicts()
