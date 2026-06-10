import pandas as pd

from app.dataframe_io import dataset_to_pandas


class DataCleaner:
    def clean(self, dataset: list[dict]) -> pd.DataFrame:
        df = dataset_to_pandas(dataset, drop_sparse_columns=True)

        if df.empty:
            raise ValueError("Dataset invalido apos limpeza.")

        return df
