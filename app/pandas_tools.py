import re

import pandas as pd


class PandasTools:
    VALID_OPERATIONS = {
        "groupby",
        "count",
        "time_groupby",
        "scatter",
        "kpi",
        "table",
    }

    VALID_AGGREGATIONS = {
        "sum",
        "mean",
        "avg",
        "count",
        "max",
        "min",
        "median",
        "none",
    }

    VALID_FILTER_OPERATORS = {
        "equals",
        "not_equals",
        "contains",
        "in",
    }

    def unique_values(self, df, columns=None, limit: int = 30) -> dict:
        if df is None or df.empty:
            return {}

        temp_df = self._normalize_dataframe_columns(df)
        resolved_columns = self._resolve_columns(temp_df, columns)

        if not resolved_columns:
            resolved_columns = [
                column for column in temp_df.columns
                if not pd.api.types.is_numeric_dtype(temp_df[column])
            ]

        result = {}

        for column in resolved_columns:
            values = (
                temp_df[column]
                .dropna()
                .astype(str)
                .map(str.strip)
            )
            values = values[values != ""].drop_duplicates().head(limit).tolist()

            result[column] = values

        return result

    def filter_dataframe(self, df, filters: list[dict]) -> pd.DataFrame:
        if df is None or df.empty or not filters:
            return df

        filtered_df = self._normalize_dataframe_columns(df)

        for filter_spec in filters:
            if not isinstance(filter_spec, dict):
                continue

            column = self._find_column(filtered_df, filter_spec.get("column"))

            if not column:
                continue

            operator = str(filter_spec.get("operator") or "equals").strip().lower()

            if operator not in self.VALID_FILTER_OPERATORS:
                operator = "equals"

            raw_value = filter_spec.get("value")
            values = self._as_list(raw_value)

            if not values:
                continue

            series = filtered_df[column].astype(str).str.strip()
            clean_values = [str(value).strip() for value in values]

            if operator == "equals":
                filtered_df = filtered_df[series.isin(clean_values)]
            elif operator == "not_equals":
                filtered_df = filtered_df[~series.isin(clean_values)]
            elif operator == "contains":
                pattern = "|".join(re.escape(value) for value in clean_values)
                filtered_df = filtered_df[series.str.contains(pattern, case=False, na=False)]
            elif operator == "in":
                filtered_df = filtered_df[series.isin(clean_values)]

        return filtered_df

    def execute(self, df, plan: dict) -> list[dict]:
        if df is None or df.empty:
            return []

        if not isinstance(plan, dict):
            return []

        df = self._normalize_dataframe_columns(df)
        df = self.filter_dataframe(df, plan.get("filters") or [])

        if df.empty:
            return []

        operation = plan.get("operation") or "groupby"

        if operation not in self.VALID_OPERATIONS:
            operation = "groupby"

        aggregation = self._first_value(plan.get("aggregation", ["sum"]))

        if aggregation == "avg":
            aggregation = "mean"

        if aggregation not in self.VALID_AGGREGATIONS:
            aggregation = "sum"

        if operation == "count" or aggregation == "count":
            return self._count(df, plan)

        if operation == "time_groupby":
            return self._time_groupby(df, plan, aggregation)

        if operation == "scatter":
            return self._scatter(df, plan)

        if operation == "kpi":
            return self._kpi(df, plan, aggregation)

        if operation == "table":
            return self._table(df, plan)

        return self._groupby(df, plan, aggregation)

    def execute_many(self, df, plans: list[dict]) -> list[dict]:
        results = []

        for index, plan in enumerate(plans or []):
            try:
                metrics = self.execute(df=df, plan=plan)

                results.append({
                    "id": f"chart_{index + 1}",
                    "title": plan.get("title", f"Gráfico {index + 1}"),
                    "chart_type": plan.get("chart_type", "bar") if metrics else "none",
                    "operation": plan.get("operation"),
                    "x": plan.get("x"),
                    "y": plan.get("y"),
                    "metric": plan.get("metric"),
                    "group_by": plan.get("group_by"),
                    "aggregation": plan.get("aggregation"),
                    "reason": plan.get("reason", "") if metrics else "Não foi possível gerar dados para este gráfico.",
                    "data": metrics,
                })

            except Exception as error:
                results.append({
                    "id": f"chart_{index + 1}",
                    "title": plan.get("title", f"Gráfico {index + 1}"),
                    "chart_type": "none",
                    "operation": plan.get("operation"),
                    "x": plan.get("x"),
                    "y": plan.get("y"),
                    "metric": plan.get("metric"),
                    "group_by": plan.get("group_by"),
                    "aggregation": plan.get("aggregation"),
                    "reason": str(error),
                    "data": [],
                })

        return results

    def _normalize_dataframe_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df.columns = [str(column).strip() for column in df.columns]
        return df

    def _normalize_name(self, value) -> str:
        return str(value).strip().lower().replace("_", " ")

    def _as_list(self, value) -> list:
        if value is None:
            return []

        if isinstance(value, list):
            return [
                item for item in value
                if item is not None and str(item).strip()
            ]

        return [value] if str(value).strip() else []

    def _first_value(self, value):
        values = self._as_list(value)
        return str(values[0]).strip().lower() if values else "none"

    def _find_column(self, df: pd.DataFrame, column) -> str | None:
        if not column:
            return None

        target = self._normalize_name(column)

        for real_column in df.columns:
            if self._normalize_name(real_column) == target:
                return real_column

        return None

    def _resolve_columns(self, df: pd.DataFrame, columns) -> list[str]:
        resolved = []

        for column in self._as_list(columns):
            real_column = self._find_column(df, column)

            if real_column and real_column not in resolved:
                resolved.append(real_column)

        return resolved

    def _resolve_group_by(self, df: pd.DataFrame, plan: dict) -> list[str]:
        group_by = self._resolve_columns(df, plan.get("group_by"))

        if group_by:
            return group_by

        x = self._find_column(df, plan.get("x"))

        if x:
            return [x]

        return []

    def _resolve_metric(self, df: pd.DataFrame, plan: dict) -> list[str]:
        metric = self._resolve_columns(df, plan.get("metric"))

        if metric:
            return metric

        y = self._find_column(df, plan.get("y"))

        if y:
            return [y]

        return []

    def _to_numeric(self, df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
        df = df.copy()

        for column in columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

        return df.dropna(subset=columns)

    def _clean_column_name(self, column: str) -> str:
        name = str(column).strip()

        suffixes = {
            "_sum": "",
            "_mean": " Médio",
            "_count": " Quantidade",
            "_max": " Máximo",
            "_min": " Mínimo",
            "_median": " Mediana",
        }

        for suffix, label in suffixes.items():
            if name.endswith(suffix):
                name = name[: -len(suffix)].strip()

                if label and not name.lower().endswith(label.strip().lower()):
                    name = f"{name}{label}"

                break

        name = name.replace("_", " ")
        name = " ".join(name.split())

        return name

    def _flatten_columns(self, result: pd.DataFrame) -> pd.DataFrame:
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

                    labels = {
                        "sum": "",
                        "mean": " Médio",
                        "count": " Quantidade",
                        "max": " Máximo",
                        "min": " Mínimo",
                        "median": " Mediana",
                    }

                    label = labels.get(aggregation, "")
                    new_name = f"{metric}{label}" if label else metric

                elif parts:
                    new_name = parts[0]
                else:
                    new_name = ""
            else:
                new_name = str(column)

            new_columns.append(self._clean_column_name(new_name))

        result.columns = new_columns

        return result

    def _sort_and_limit(self, result: pd.DataFrame, y_column: str | None, plan: dict, default_limit: int = 20) -> pd.DataFrame:
        limit = plan.get("limit", default_limit)

        try:
            limit = int(limit)
        except Exception:
            limit = default_limit

        limit = max(1, min(limit, 100))

        sort = plan.get("sort", "desc")

        if y_column and y_column in result.columns and sort in ["asc", "desc"]:
            result = result.sort_values(
                by=y_column,
                ascending=sort == "asc",
            )

        return result.head(limit)

    def _aggregate(self, df: pd.DataFrame, group_by: list[str], metric: list[str], aggregation: str) -> pd.DataFrame:
        if aggregation == "mean":
            result = df.groupby(group_by, dropna=False)[metric].mean().reset_index()
        elif aggregation == "max":
            result = df.groupby(group_by, dropna=False)[metric].max().reset_index()
        elif aggregation == "min":
            result = df.groupby(group_by, dropna=False)[metric].min().reset_index()
        elif aggregation == "median":
            result = df.groupby(group_by, dropna=False)[metric].median().reset_index()
        else:
            result = df.groupby(group_by, dropna=False)[metric].sum().reset_index()

        return self._flatten_columns(result)

    def _count(self, df: pd.DataFrame, plan: dict) -> list[dict]:
        group_by = self._resolve_group_by(df, plan)

        if not group_by:
            raise ValueError("group_by não encontrado para contagem.")

        result = (
            df.groupby(group_by, dropna=False)
            .size()
            .reset_index(name="Quantidade")
        )

        result = self._sort_and_limit(
            result=result,
            y_column="Quantidade",
            plan=plan,
            default_limit=20,
        )

        return result.to_dict(orient="records")

    def _groupby(self, df: pd.DataFrame, plan: dict, aggregation: str) -> list[dict]:
        group_by = self._resolve_group_by(df, plan)

        if not group_by:
            raise ValueError("group_by não encontrado para groupby.")

        metric = self._resolve_metric(df, plan)

        if not metric:
            raise ValueError("metric não encontrada para groupby.")

        if aggregation in ["none", "count"]:
            aggregation = "sum"

        temp_df = self._to_numeric(df, metric)

        if temp_df.empty:
            return []

        result = self._aggregate(
            df=temp_df,
            group_by=group_by,
            metric=metric,
            aggregation=aggregation,
        )

        numeric_columns = [
            column for column in result.columns
            if column not in group_by
        ]

        sort_column = numeric_columns[0] if numeric_columns else None

        result = self._sort_and_limit(
            result=result,
            y_column=sort_column,
            plan=plan,
            default_limit=20,
        )

        return result.to_dict(orient="records")

    def _time_groupby(self, df: pd.DataFrame, plan: dict, aggregation: str) -> list[dict]:
        time_column = (
            self._find_column(df, plan.get("time_column"))
            or self._find_column(df, plan.get("x"))
        )

        if not time_column:
            raise ValueError("time_column não encontrada para time_groupby.")

        time_freq = plan.get("time_freq", "M")

        if time_freq not in ["D", "W", "M", "Q", "Y"]:
            time_freq = "M"

        temp_df = df.copy()

        temp_df[time_column] = pd.to_datetime(
            temp_df[time_column],
            errors="coerce",
        )

        temp_df = temp_df.dropna(subset=[time_column])

        if temp_df.empty:
            return []

        temp_df["Período"] = (
            temp_df[time_column]
            .dt.to_period(time_freq)
            .astype(str)
        )

        group_columns = ["Período"]

        extra_group_by = self._resolve_columns(
            temp_df,
            plan.get("group_by"),
        )

        extra_group_by = [
            column for column in extra_group_by
            if column != time_column and column != "Período"
        ]

        group_columns.extend(extra_group_by)

        if aggregation == "count":
            result = (
                temp_df.groupby(group_columns, dropna=False)
                .size()
                .reset_index(name="Quantidade")
            )

            result = result.sort_values("Período").head(100)

        else:
            metric = self._resolve_metric(temp_df, plan)

            if not metric:
                raise ValueError("metric não encontrada para time_groupby.")

            if aggregation == "none":
                aggregation = "sum"

            temp_df = self._to_numeric(temp_df, metric)

            if temp_df.empty:
                return []

            result = self._aggregate(
                df=temp_df,
                group_by=group_columns,
                metric=metric,
                aggregation=aggregation,
            )

            result = result.sort_values("Período").head(100)

        if len(group_columns) > 1:
            result["label"] = (
                result[group_columns]
                .astype(str)
                .agg(" | ".join, axis=1)
            )
        else:
            result["label"] = result["Período"].astype(str)

        return result.to_dict(orient="records")

    def _scatter(self, df: pd.DataFrame, plan: dict) -> list[dict]:
        x = self._find_column(df, plan.get("x"))
        y = self._find_column(df, plan.get("y"))

        if not x or not y:
            raise ValueError("x ou y não encontrado para scatter.")

        temp_df = self._to_numeric(df, [x, y])

        if temp_df.empty:
            return []

        limit = plan.get("limit", 100)

        try:
            limit = int(limit)
        except Exception:
            limit = 100

        limit = max(1, min(limit, 500))

        return temp_df[[x, y]].head(limit).to_dict(orient="records")

    def _kpi(self, df: pd.DataFrame, plan: dict, aggregation: str) -> list[dict]:
        metric = self._resolve_metric(df, plan)

        if not metric:
            raise ValueError("metric não encontrada para kpi.")

        column = metric[0]

        temp_df = self._to_numeric(df, [column])

        if temp_df.empty:
            return []

        if aggregation == "mean":
            value = temp_df[column].mean()
        elif aggregation == "max":
            value = temp_df[column].max()
        elif aggregation == "min":
            value = temp_df[column].min()
        elif aggregation == "median":
            value = temp_df[column].median()
        elif aggregation == "count":
            value = temp_df[column].count()
        else:
            aggregation = "sum"
            value = temp_df[column].sum()

        return [
            {
                "label": plan.get("title", column),
                column: value,
            }
        ]

    def _table(self, df: pd.DataFrame, plan: dict) -> list[dict]:
        limit = plan.get("limit", 50)

        try:
            limit = int(limit)
        except Exception:
            limit = 50

        limit = max(1, min(limit, 200))

        return df.head(limit).to_dict(orient="records")
