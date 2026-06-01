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

    PREFERRED_CATEGORICAL_COLUMNS = [
        "campanha",
        "produto",
        "categoria",
        "canal",
        "região",
        "regiao",
        "cidade",
        "cliente",
        "vendedor",
        "status",
        "forma pagamento",
        "forma_pagamento",
    ]

    PREFERRED_NUMERIC_COLUMNS = [
        "receita",
        "valor",
        "valor total",
        "valor_total",
        "roi",
        "conversões",
        "conversoes",
        "vendas",
        "quantidade",
        "investimento",
        "custo",
        "lucro",
    ]

    def execute(self, df, plan: dict) -> list[dict]:
        if df is None or df.empty:
            return []

        df = self._normalize_dataframe_columns(df)

        rename_columns = plan.get("rename_columns", {})

        df = self.rename_columns_df(
            df=df,
            rename_map=rename_columns,
        )

        operation = plan.get("operation") or "groupby"

        group_by = self._normalize_list(
            plan.get("group_by")
        )

        metric = self._normalize_list(
            plan.get("metric")
        )

        aggregation = self._normalize_list(
            plan.get("aggregation", ["count"])
        )

        aggregation = self._sanitize_aggregations(aggregation)

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

        return self._groupby(
            df=df,
            group_by=group_by,
            metric=metric,
            aggregation=aggregation,
        )

    def _normalize_dataframe_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df.columns = [str(column).strip() for column in df.columns]
        return df

    def _normalize_name(self, value) -> str:
        return str(value).strip().lower().replace("_", " ")

    def _normalize_list(self, value) -> list:
        if value is None:
            return []

        if isinstance(value, list):
            return [
                item for item in value
                if item is not None and str(item).strip()
            ]

        return [value] if str(value).strip() else []

    def _sanitize_aggregations(self, aggregation: list[str]) -> list[str]:
        valid = []

        for item in aggregation:
            item = str(item).strip().lower()

            if item == "avg":
                item = "mean"

            if item in self.AGGREGATION_LABELS:
                valid.append(item)

        return valid or ["count"]

    def _find_column(self, df: pd.DataFrame, column: str | None) -> str | None:
        if not column:
            return None

        target = self._normalize_name(column)

        for real_column in df.columns:
            if self._normalize_name(real_column) == target:
                return real_column

        return None

    def _resolve_columns(
        self,
        df: pd.DataFrame,
        columns: list[str],
    ) -> list[str]:
        resolved = []

        for column in columns:
            real_column = self._find_column(df, column)

            if real_column and real_column not in resolved:
                resolved.append(real_column)

        return resolved

    def _get_numeric_columns(self, df: pd.DataFrame) -> list[str]:
        numeric_columns = df.select_dtypes(include="number").columns.tolist()

        if numeric_columns:
            return numeric_columns

        resolved = []

        for column in df.columns:
            converted = pd.to_numeric(df[column], errors="coerce")

            if converted.notna().sum() > 0:
                resolved.append(column)

        return resolved

    def _get_first_numeric_column(self, df: pd.DataFrame) -> str | None:
        numeric_columns = self._get_numeric_columns(df)

        for preferred in self.PREFERRED_NUMERIC_COLUMNS:
            for column in numeric_columns:
                if preferred == self._normalize_name(column):
                    return column

        for preferred in self.PREFERRED_NUMERIC_COLUMNS:
            for column in numeric_columns:
                if preferred in self._normalize_name(column):
                    return column

        return numeric_columns[0] if numeric_columns else None

    def _get_first_categorical_column(self, df: pd.DataFrame) -> str | None:
        if df.empty or len(df.columns) == 0:
            return None

        numeric_columns = set(self._get_numeric_columns(df))

        categorical_columns = [
            column for column in df.columns
            if column not in numeric_columns
        ]

        if not categorical_columns:
            return df.columns[0]

        for preferred in self.PREFERRED_CATEGORICAL_COLUMNS:
            for column in categorical_columns:
                if preferred == self._normalize_name(column):
                    return column

        for preferred in self.PREFERRED_CATEGORICAL_COLUMNS:
            for column in categorical_columns:
                if preferred in self._normalize_name(column):
                    return column

        return categorical_columns[0]

    def _resolve_group_by(
        self,
        df: pd.DataFrame,
        group_by: list[str],
    ) -> list[str]:
        resolved = self._resolve_columns(df, group_by)

        if resolved:
            return resolved

        fallback = self._get_first_categorical_column(df)

        return [fallback] if fallback else []

    def _resolve_metric(
        self,
        df: pd.DataFrame,
        metric: list[str],
    ) -> list[str]:
        resolved = self._resolve_columns(df, metric)

        if resolved:
            return resolved

        fallback = self._get_first_numeric_column(df)

        return [fallback] if fallback else []

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
        df: pd.DataFrame,
        group_by: list[str],
    ) -> list[dict]:
        group_by = self._resolve_group_by(
            df=df,
            group_by=group_by,
        )

        if not group_by:
            return []

        result = (
            df.groupby(group_by, dropna=False)
            .size()
            .reset_index(name="Quantidade")
            .sort_values("Quantidade", ascending=False)
            .head(20)
        )

        return result.to_dict(orient="records")

    def _groupby(
        self,
        df: pd.DataFrame,
        group_by: list[str],
        metric: list[str],
        aggregation: list[str],
    ) -> list[dict]:
        group_by = self._resolve_group_by(
            df=df,
            group_by=group_by,
        )

        if not group_by:
            return []

        metric = self._resolve_metric(
            df=df,
            metric=metric,
        )

        if not metric or aggregation == ["count"]:
            result = (
                df.groupby(group_by, dropna=False)
                .size()
                .reset_index(name="Quantidade")
                .sort_values("Quantidade", ascending=False)
                .head(20)
            )

            return result.to_dict(orient="records")

        temp_df = df.copy()

        for column in metric:
            temp_df[column] = pd.to_numeric(
                temp_df[column],
                errors="coerce",
            )

        temp_df = temp_df.dropna(subset=metric)

        if temp_df.empty:
            return []

        result = (
            temp_df.groupby(group_by, dropna=False)[metric]
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
        df: pd.DataFrame,
        time_column: str,
        metric: list[str],
        aggregation: list[str],
        time_freq: str,
        group_by: list[str] | None = None,
    ) -> list[dict]:
        real_time_column = self._find_column(df, time_column)

        if not real_time_column:
            real_time_column = self._find_best_date_column(df)

        if not real_time_column:
            return self._groupby(
                df=df,
                group_by=group_by or [],
                metric=metric,
                aggregation=aggregation,
            )

        if time_freq not in ["D", "M", "Y"]:
            time_freq = "M"

        temp_df = df.copy()

        temp_df[real_time_column] = pd.to_datetime(
            temp_df[real_time_column],
            errors="coerce",
        )

        temp_df = temp_df.dropna(
            subset=[real_time_column]
        )

        if temp_df.empty:
            return self._groupby(
                df=df,
                group_by=group_by or [],
                metric=metric,
                aggregation=aggregation,
            )

        temp_df["Período"] = (
            temp_df[real_time_column]
            .dt.to_period(time_freq)
            .astype(str)
        )

        group_columns = ["Período"]

        resolved_group_by = self._resolve_columns(
            temp_df,
            group_by or [],
        )

        group_columns.extend(resolved_group_by)

        metric = self._resolve_metric(
            df=temp_df,
            metric=metric,
        )

        if not metric or aggregation == ["count"]:
            result = (
                temp_df.groupby(group_columns, dropna=False)
                .size()
                .reset_index(name="Quantidade")
                .sort_values("Período")
                .head(20)
            )
        else:
            for column in metric:
                temp_df[column] = pd.to_numeric(
                    temp_df[column],
                    errors="coerce",
                )

            temp_df = temp_df.dropna(subset=metric)

            if temp_df.empty:
                return []

            result = (
                temp_df.groupby(group_columns, dropna=False)[metric]
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

    def _find_best_date_column(self, df: pd.DataFrame) -> str | None:
        for column in df.columns:
            normalized = self._normalize_name(column)

            if any(term in normalized for term in ["data", "date", "dia", "mes", "mês", "ano"]):
                return column

        return None

    @staticmethod
    def rename_columns_df(
        df: pd.DataFrame,
        rename_map: dict[str, str] | None,
    ) -> pd.DataFrame:
        if df.empty:
            return df

        if not rename_map:
            return df

        normalized_columns = {
            str(column).strip().lower(): column
            for column in df.columns
        }

        safe_rename_map = {}

        for old_name, new_name in rename_map.items():
            if not isinstance(new_name, str) or not new_name.strip():
                continue

            real_old_name = normalized_columns.get(
                str(old_name).strip().lower()
            )

            if real_old_name:
                safe_rename_map[real_old_name] = new_name.strip()

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

                if not metrics:
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
                        "reason": "Não foi possível gerar dados para este gráfico.",
                        "data": [],
                    })

                    continue

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
