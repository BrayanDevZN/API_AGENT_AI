import pandas as pd


class PandasTools:
    def execute(self, df, plan: dict) -> list[dict]:
        rename_columns = plan.get("rename_columns", {})

        df = self.rename_columns_df(
            df=df,
            rename_map=rename_columns
        )

        operation = plan.get("operation")

        group_by = self._normalize_list(
            plan.get("group_by")
        )

        metric = self._normalize_list(
            plan.get("metric")
        )

        aggregation = self._normalize_list(
            plan.get("aggregation", ["count"])
        )

        time_column = plan.get("time_column")
        time_freq = plan.get("time_freq", "M")

        if operation == "count":
            return self._count(
                df=df,
                group_by=group_by
            )

        if operation == "groupby":
            return self._groupby(
                df=df,
                group_by=group_by,
                metric=metric,
                aggregation=aggregation
            )

        if operation == "time_groupby":
            return self._time_groupby(
                df=df,
                time_column=time_column,
                metric=metric,
                aggregation=aggregation,
                time_freq=time_freq,
                group_by=group_by
            )

        raise ValueError("Operação não suportada.")

    def _normalize_list(self, value) -> list:
        if value is None:
            return []

        if isinstance(value, list):
            return value

        return [value]

    def _validate_columns(
        self,
        df,
        columns: list[str],
        label: str
    ) -> None:
        for column in columns:
            if column not in df.columns:
                raise ValueError(
                    f"Coluna {label} inválida: {column}"
                )

    def _flatten_columns(
        self,
        result: pd.DataFrame
    ) -> pd.DataFrame:
        result.columns = [
            "_".join(
                [str(part) for part in col if part]
            )
            if isinstance(col, tuple)
            else str(col)
            for col in result.columns
        ]

        return result

    def _count(
        self,
        df,
        group_by: list[str]
    ) -> list[dict]:

        if not group_by:
            raise ValueError(
                "Nenhuma coluna group_by informada."
            )

        self._validate_columns(
            df=df,
            columns=group_by,
            label="group_by"
        )

        result = (
            df.groupby(group_by)
            .size()
            .reset_index(name="count")
            .sort_values("count", ascending=False)
            .head(20)
        )

        return result.to_dict(orient="records")

    def _groupby(
        self,
        df,
        group_by: list[str],
        metric: list[str],
        aggregation: list[str]
    ) -> list[dict]:

        if not group_by:
            raise ValueError(
                "Nenhuma coluna group_by informada."
            )

        self._validate_columns(
            df=df,
            columns=group_by,
            label="group_by"
        )

        if not metric:
            result = (
                df.groupby(group_by)
                .size()
                .reset_index(name="count")
                .sort_values("count", ascending=False)
                .head(20)
            )

            return result.to_dict(orient="records")

        self._validate_columns(
            df=df,
            columns=metric,
            label="metric"
        )

        result = (
            df.groupby(group_by)[metric]
            .agg(aggregation)
            .reset_index()
        )

        result = self._flatten_columns(result)

        numeric_columns = [
            col for col in result.columns
            if col not in group_by
        ]

        if numeric_columns:
            result = result.sort_values(
                numeric_columns[0],
                ascending=False
            )

        result = result.head(20)

        return result.to_dict(orient="records")

    def _time_groupby(
        self,
        df,
        time_column: str,
        metric: list[str],
        aggregation: list[str],
        time_freq: str,
        group_by: list[str] | None = None
    ) -> list[dict]:

        if not time_column:
            raise ValueError(
                "time_column não informado."
            )

        if time_column not in df.columns:
            raise ValueError(
                f"Coluna de tempo inválida: {time_column}"
            )

        temp_df = df.copy()

        temp_df[time_column] = pd.to_datetime(
            temp_df[time_column],
            errors="coerce"
        )

        temp_df = temp_df.dropna(
            subset=[time_column]
        )

        if temp_df.empty:
            raise ValueError(
                "Nenhuma data válida encontrada."
            )

        temp_df["periodo"] = (
            temp_df[time_column]
            .dt.to_period(time_freq)
            .astype(str)
        )

        group_columns = ["periodo"]

        if group_by:
            self._validate_columns(
                df=temp_df,
                columns=group_by,
                label="group_by"
            )

            group_columns.extend(group_by)

        if not metric:
            result = (
                temp_df.groupby(group_columns)
                .size()
                .reset_index(name="count")
                .sort_values("periodo")
                .head(20)
            )

        else:
            self._validate_columns(
                df=temp_df,
                columns=metric,
                label="metric"
            )

            result = (
                temp_df.groupby(group_columns)[metric]
                .agg(aggregation)
                .reset_index()
            )

            result = self._flatten_columns(result)

            result = result.sort_values(
                "periodo"
            ).head(20)

        if len(group_columns) > 1:
            result["label"] = (
                result[group_columns]
                .astype(str)
                .agg(" - ".join, axis=1)
            )
        else:
            result["label"] = (
                result["periodo"]
                .astype(str)
            )

        return result.to_dict(orient="records")

    @staticmethod
    def rename_columns_df(
        df: pd.DataFrame,
        rename_map: dict[str, str] | None
    ) -> pd.DataFrame:

        if df.empty:
            return df

        if not rename_map:
            return df

        safe_rename_map = {
            old_name: new_name.strip()
            for old_name, new_name in rename_map.items()
            if old_name in df.columns
            and isinstance(new_name, str)
            and new_name.strip()
        }

        if not safe_rename_map:
            return df

        return df.rename(
            columns=safe_rename_map
        )