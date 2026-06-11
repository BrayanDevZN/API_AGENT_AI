import polars as pl


class DataProfiler:
    def profile(self, df: pl.DataFrame) -> dict:
        numeric_columns = []
        categorical_columns = []
        date_columns = []

        columns_info = []

        for col in df.columns:
            dtype = df.schema[col]
            dtype_name = str(dtype)

            if dtype.is_numeric():
                numeric_columns.append(col)

            elif dtype.is_temporal():
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

            null_percent = 0

            if df.height:
                null_percent = round(
                    float(df[col].null_count() / df.height) * 100,
                    2,
                )

            sample = (
                df
                .select(
                    pl.col(col)
                    .drop_nulls()
                    .head(5)
                    .cast(pl.Utf8, strict=False)
                    .alias(col)
                )
                .to_series()
                .to_list()
            )

            columns_info.append({
                "name": col,
                "dtype": dtype_name,
                "null_percent": null_percent,
                "sample": sample,
            })

        return {
            "rows": df.height,
            "column_count": len(df.columns),
            "numeric_columns": numeric_columns,
            "categorical_columns": categorical_columns,
            "date_columns": date_columns,
            "columns": columns_info,
        }
