from fastapi import UploadFile

from app.dataframe_io import read_file_to_records


class FileReader:
    async def read(self, file: UploadFile) -> list[dict]:
        try:
            return read_file_to_records(file)
        except Exception as error:
            raise ValueError(f"Erro ao ler arquivo: {str(error)}")
