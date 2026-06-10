import pandas as pd


class DataCleaner:
    def clean(self, dataset: list[dict]) -> pd.DataFrame:
        df = pd.DataFrame(dataset)

        if df.empty:
            raise ValueError("Dataset vazio.")

        df.columns = [str(col).strip() for col in df.columns]

        min_non_null = int(len(df) * 0.7)
        df = df.dropna(axis=1, thresh=min_non_null)
        df = df.dropna(how="all")

        if df.empty:
            raise ValueError("Dataset inválido após limpeza.")

        return df