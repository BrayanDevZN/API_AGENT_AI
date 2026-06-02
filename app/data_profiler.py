import pandas as pd


class DataProfiler:
    def profile(self, df) -> dict:
        numeric_columns = []
        categorical_columns = []
        date_columns = []

        columns_info = []

        for col in df.columns:
            dtype = str(df[col].dtype)

            if pd.api.types.is_numeric_dtype(df[col]):
                numeric_columns.append(col)

            elif pd.api.types.is_datetime64_any_dtype(df[col]):
                date_columns.append(col)

            else:
                lowered = col.lower()

                if any(
                    keyword in lowered
                    for keyword in [
                        "data",
                        "date",
                        "dia",
                        "mes",
                        "ano",
                        "timestamp",
                        "created",
                        "updated",
                    ]
                ):
                    date_columns.append(col)
                else:
                    categorical_columns.append(col)

            columns_info.append({
                "name": col,
                "dtype": dtype,
                "null_percent": round(
                    float(df[col].isna().mean()) * 100,
                    2
                ),
                "sample": (
                    df[col]
                    .dropna()
                    .head(5)
                    .astype(str)
                    .tolist()
                ),
            })

        return {
            "rows": len(df),
            "column_count": len(df.columns),

            "numeric_columns": numeric_columns,
            "categorical_columns": categorical_columns,
            "date_columns": date_columns,

            "columns": columns_info,
        }