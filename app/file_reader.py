import polars as pl
from fastapi import UploadFile


class FileReader:
    async def read(self, file: UploadFile) -> list[dict]:
        filename = file.filename.lower()

        try:
            if filename.endswith(".csv"):
                df = pl.read_csv(file.file)

            elif filename.endswith(".xlsx") or filename.endswith(".xls"):
                df = pl.read_excel(file.file)

            elif filename.endswith(".json"):
                df = pl.read_json(file.file)

            else:
                raise ValueError("Tipo de arquivo nao suportado. Use CSV, Excel ou JSON.")

            df = self._clean(df)

            return df.to_dicts()

        except Exception as error:
            raise ValueError(f"Erro ao ler arquivo: {str(error)}")

    def _clean(self, df: pl.DataFrame) -> pl.DataFrame:
        if df.width:
            df = df.filter(~pl.all_horizontal(pl.all().is_null()))

        df = df.select([
            column for column in df.columns
            if df[column].null_count() < df.height
        ])

        df.columns = [
            str(col).strip()
            for col in df.columns
        ]

        float_columns = [
            column for column, dtype in df.schema.items()
            if dtype in (pl.Float32, pl.Float64)
        ]

        if float_columns:
            df = df.with_columns(pl.col(float_columns).fill_nan(None))

        return df
