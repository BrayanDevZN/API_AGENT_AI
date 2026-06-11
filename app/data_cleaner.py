import polars as pl


class DataCleaner:
    def clean(self, dataset: list[dict]) -> pl.DataFrame:
        df = pl.from_dicts(dataset, infer_schema_length=None)

        if df.is_empty():
            raise ValueError("Dataset vazio.")

        df.columns = [str(col).strip() for col in df.columns]

        min_non_null = int(df.height * 0.7)
        kept_columns = [
            column for column in df.columns
            if df.height - df[column].null_count() >= min_non_null
        ]
        df = df.select(kept_columns)

        if df.width:
            df = df.filter(~pl.all_horizontal(pl.all().is_null()))

        if df.is_empty():
            raise ValueError("Dataset invalido apos limpeza.")

        return df
