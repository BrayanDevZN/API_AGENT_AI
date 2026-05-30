import pandas as pd


class PandasTools:
    AGGREGATION_LABELS = {
        "sum": "",
        "mean": " Médio",
        "avg": " Médio",
        "count": " Quantidade",
        "max": " Máximo",
        "min": " Mínimo",
    }

    def execute(self, df, plan: dict) -> list[dict]:
        rename_columns = plan.get("rename_columns", {})

        df = self.rename_columns_df(
            df=df,
            rename_map=rename_columns,
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
                group_by=group_by,
            )

        if operation == "groupby":
            return self._groupby(
                df=df,
                group_by=group_by,
                metric=metric,
                aggregation=aggregation,
            )

        if operation == "time_groupby":
            return self._time_groupby(
                df=df,
                time_column=time_column,
                metric=metric,
                aggregation=aggregation,
                time_freq=time_freq,
                group_by=group_by,
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
        label: str,
    ) -> None:
        for column in columns:
            if column not in df.columns:
                raise ValueError(
                    f"Coluna {label} inválida: {column}"
                )

    def _clean_column_name(self, column: str) -> str:
        name = str(column).strip()

        for aggregation, label in self.AGGREGATION_LABELS.items():
            suffix = f"_{aggregation}"

            if name.endswith(suffix):
                name = name[: -len(suffix)].strip()

                if label and not name.lower().endswith(label.strip().lower()):
                    name = f"{name}{label}"

                break

        name = name.replace("_", " ")
        name = " ".join(name.split())

        return name

    def _flatten_columns(
        self,
        result: pd.DataFrame,
    ) -> pd.DataFrame:
        new_columns = []

        for column in result.columns:
            if isinstance(column, tuple):
                parts = [
                    str(part).strip()
                    for part in column
                    if part is not None and str(part).strip()
                ]

                if len(parts) >= 2:
                    metric = " ".join(parts[:-1]).strip()
                    aggregation = parts[-1].strip()

                    label = self.AGGREGATION_LABELS.get(
                        aggregation,
                        "",
                    )

                    if label:
                        new_name = f"{metric}{label}"
                    else:
                        new_name = metric
                elif parts:
                    new_name = parts[0]
                else:
                    new_name = ""
            else:
                new_name = str(column)

            new_columns.append(
                self._clean_column_name(new_name)
            )

        result.columns = new_columns

        return result

    def _count(
        self,
        df,
        group_by: list[str],
    ) -> list[dict]:

        if not group_by:
            raise ValueError(
                "Nenhuma coluna group_by informada."
            )

        self._validate_columns(
            df=df,
            columns=group_by,
            label="group_by",
        )

        result = (
            df.groupby(group_by)
            .size()
            .reset_index(name="Quantidade")
            .sort_values("Quantidade", ascending=False)
            .head(20)
        )

        return result.to_dict(orient="records")

    def _groupby(
        self,
        df,
        group_by: list[str],
        metric: list[str],
        aggregation: list[str],
    ) -> list[dict]:

        if not group_by:
            raise ValueError(
                "Nenhuma coluna group_by informada."
            )

        self._validate_columns(
            df=df,
            columns=group_by,
            label="group_by",
        )

        if not metric:
            result = (
                df.groupby(group_by)
                .size()
                .reset_index(name="Quantidade")
                .sort_values("Quantidade", ascending=False)
                .head(20)
            )

            return result.to_dict(orient="records")

        self._validate_columns(
            df=df,
            columns=metric,
            label="metric",
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
                ascending=False,
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
        group_by: list[str] | None = None,
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
            errors="coerce",
        )

        temp_df = temp_df.dropna(
            subset=[time_column]
        )

        if temp_df.empty:
            raise ValueError(
                "Nenhuma data válida encontrada."
            )

        temp_df["Período"] = (
            temp_df[time_column]
            .dt.to_period(time_freq)
            .astype(str)
        )

        group_columns = ["Período"]

        if group_by:
            self._validate_columns(
                df=temp_df,
                columns=group_by,
                label="group_by",
            )

            group_columns.extend(group_by)

        if not metric:
            result = (
                temp_df.groupby(group_columns)
                .size()
                .reset_index(name="Quantidade")
                .sort_values("Período")
                .head(20)
            )

        else:
            self._validate_columns(
                df=temp_df,
                columns=metric,
                label="metric",
            )

            result = (
                temp_df.groupby(group_columns)[metric]
                .agg(aggregation)
                .reset_index()
            )

            result = self._flatten_columns(result)

            result = result.sort_values(
                "Período"
            ).head(20)

        if len(group_columns) > 1:
            result["label"] = (
                result[group_columns]
                .astype(str)
                .agg(" | ".join, axis=1)
            )
        else:
            result["label"] = (
                result["Período"]
                .astype(str)
            )

        return result.to_dict(orient="records")

    @staticmethod
    def rename_columns_df(
        df: pd.DataFrame,
        rename_map: dict[str, str] | None,
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

    def execute_many(
        self,
        df,
        plans: list[dict],
    ) -> list[dict]:

        results = []

        for index, plan in enumerate(plans):

            try:
                metrics = self.execute(
                    df=df,
                    plan=plan,
                )

                results.append({
                    "id": f"chart_{index + 1}",
                    "title": plan.get(
                        "title",
                        f"Gráfico {index + 1}",
                    ),
                    "chart_type": plan.get(
                        "chart_type",
                        "bar",
                    ),
                    "operation": plan.get(
                        "operation"
                    ),
                    "x": plan.get("x"),
                    "y": plan.get("y"),
                    "reason": plan.get(
                        "reason",
                        "",
                    ),
                    "data": metrics,
                })

            except Exception as error:

                results.append({
                    "id": f"chart_{index + 1}",
                    "title": plan.get(
                        "title",
                        f"Gráfico {index + 1}",
                    ),
                    "chart_type": "none",
                    "operation": None,
                    "x": None,
                    "y": None,
                    "reason": str(error),
                    "data": [],
                })

        return results