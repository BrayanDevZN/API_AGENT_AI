import pandas as pd
from fastapi import UploadFile


class FileReader:
    async def read(self, file: UploadFile) -> list[dict]:
        filename = file.filename.lower()

        try:
            if filename.endswith(".csv"):
                df = pd.read_csv(file.file)

            elif filename.endswith(".xlsx") or filename.endswith(".xls"):
                df = pd.read_excel(file.file)

            elif filename.endswith(".json"):
                df = pd.read_json(file.file)

            else:
                raise ValueError("Tipo de arquivo não suportado. Use CSV, Excel ou JSON.")

            df = self._clean(df)

            return df.to_dict(orient="records")

        except Exception as error:
            raise ValueError(f"Erro ao ler arquivo: {str(error)}")

    def _clean(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.dropna(how="all")
        df = df.dropna(axis=1, how="all")

        df.columns = [
            str(col).strip()
            for col in df.columns
        ]

        df = df.where(pd.notnull(df), None)

        return df