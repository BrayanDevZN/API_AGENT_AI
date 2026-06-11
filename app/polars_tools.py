import re

import polars as pl


class PolarsTools:
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
        if self._is_empty(df):
            return {}

        temp_df = self._normalize_dataframe_columns(self._to_dataframe(df))
        resolved_columns = self._resolve_columns(temp_df, columns)

        if not resolved_columns:
            resolved_columns = [
                column for column in temp_df.columns
                if not temp_df.schema[column].is_numeric()
            ]

        result = {}

        for column in resolved_columns:
            values = (
                temp_df
                .select(
                    pl.col(column)
                    .drop_nulls()
                    .cast(pl.Utf8, strict=False)
                    .str.strip_chars()
                    .alias(column)
                )
                .filter(pl.col(column) != "")
                .unique(maintain_order=True)
                .head(limit)
                .to_series()
                .to_list()
            )

            result[column] = values

        return result

    def filter_dataframe(self, df, filters: list[dict]) -> pl.DataFrame:
        if self._is_empty(df) or not filters:
            return self._to_dataframe(df)

        filtered_df = self._normalize_dataframe_columns(self._to_dataframe(df))

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

            clean_values = [str(value).strip() for value in values]
            series = (
                pl.col(column)
                .cast(pl.Utf8, strict=False)
                .str.strip_chars()
                .fill_null("")
            )

            if operator == "equals":
                filtered_df = filtered_df.filter(series.is_in(clean_values))
            elif operator == "not_equals":
                filtered_df = filtered_df.filter(~series.is_in(clean_values))
            elif operator == "contains":
                pattern = "|".join(re.escape(value) for value in clean_values)
                filtered_df = filtered_df.filter(series.str.contains(f"(?i){pattern}"))
            elif operator == "in":
                filtered_df = filtered_df.filter(series.is_in(clean_values))

        return filtered_df

    def execute(self, df, plan: dict) -> list[dict]:
        if self._is_empty(df):
            return []

        if not isinstance(plan, dict):
            return []

        df = self._normalize_dataframe_columns(self._to_dataframe(df))
        df = self.filter_dataframe(df, plan.get("filters") or [])

        if df.is_empty():
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
                    "title": plan.get("title", f"Grafico {index + 1}"),
                    "chart_type": plan.get("chart_type", "bar") if metrics else "none",
                    "operation": plan.get("operation"),
                    "x": plan.get("x"),
                    "y": plan.get("y"),
                    "metric": plan.get("metric"),
                    "group_by": plan.get("group_by"),
                    "aggregation": plan.get("aggregation"),
                    "reason": plan.get("reason", "") if metrics else "Nao foi possivel gerar dados para este grafico.",
                    "data": metrics,
                })

            except Exception as error:
                results.append({
                    "id": f"chart_{index + 1}",
                    "title": plan.get("title", f"Grafico {index + 1}"),
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

    def _to_dataframe(self, df) -> pl.DataFrame:
        if isinstance(df, pl.DataFrame):
            return df

        if df is None:
            return pl.DataFrame()

        if isinstance(df, list):
            return pl.from_dicts(df, infer_schema_length=None)

        if hasattr(df, "to_dict"):
            try:
                records = df.to_dict(orient="records")
                return pl.from_dicts(records, infer_schema_length=None)
            except TypeError:
                pass

        return pl.DataFrame(df)

    def _is_empty(self, df) -> bool:
        if df is None:
            return True

        if isinstance(df, pl.DataFrame):
            return df.is_empty()

        empty = getattr(df, "empty", None)

        if isinstance(empty, bool):
            return empty

        if isinstance(df, list):
            return not df

        return False

    def _normalize_dataframe_columns(self, df: pl.DataFrame) -> pl.DataFrame:
        df = df.clone()
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

    def _find_column(self, df: pl.DataFrame, column) -> str | None:
        if not column:
            return None

        target = self._normalize_name(column)

        for real_column in df.columns:
            if self._normalize_name(real_column) == target:
                return real_column

        return None

    def _resolve_columns(self, df: pl.DataFrame, columns) -> list[str]:
        resolved = []

        for column in self._as_list(columns):
            real_column = self._find_column(df, column)

            if real_column and real_column not in resolved:
                resolved.append(real_column)

        return resolved

    def _resolve_group_by(self, df: pl.DataFrame, plan: dict) -> list[str]:
        group_by = self._resolve_columns(df, plan.get("group_by"))

        if group_by:
            return group_by

        x = self._find_column(df, plan.get("x"))

        if x:
            return [x]

        return []

    def _resolve_metric(self, df: pl.DataFrame, plan: dict) -> list[str]:
        metric = self._resolve_columns(df, plan.get("metric"))

        if metric:
            return metric

        y = self._find_column(df, plan.get("y"))

        if y:
            return [y]

        return []

    def _to_numeric(self, df: pl.DataFrame, columns: list[str]) -> pl.DataFrame:
        return (
            df.with_columns([
                pl.col(column).cast(pl.Float64, strict=False).alias(column)
                for column in columns
            ])
            .drop_nulls(subset=columns)
        )

    def _clean_column_name(self, column: str) -> str:
        name = str(column).strip()

        suffixes = {
            "_sum": "",
            "_mean": " Medio",
            "_count": " Quantidade",
            "_max": " Maximo",
            "_min": " Minimo",
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

    def _sort_and_limit(
        self,
        result: pl.DataFrame,
        y_column: str | None,
        plan: dict,
        default_limit: int = 20,
    ) -> pl.DataFrame:
        limit = plan.get("limit", default_limit)

        try:
            limit = int(limit)
        except Exception:
            limit = default_limit

        limit = max(1, min(limit, 100))

        sort = plan.get("sort", "desc")

        if y_column and y_column in result.columns and sort in ["asc", "desc"]:
            result = result.sort(
                y_column,
                descending=sort == "desc",
                nulls_last=True,
            )

        return result.head(limit)

    def _aggregate(
        self,
        df: pl.DataFrame,
        group_by: list[str],
        metric: list[str],
        aggregation: str,
    ) -> pl.DataFrame:
        if aggregation == "mean":
            expressions = [pl.col(column).mean().alias(column) for column in metric]
        elif aggregation == "max":
            expressions = [pl.col(column).max().alias(column) for column in metric]
        elif aggregation == "min":
            expressions = [pl.col(column).min().alias(column) for column in metric]
        elif aggregation == "median":
            expressions = [pl.col(column).median().alias(column) for column in metric]
        else:
            expressions = [pl.col(column).sum().alias(column) for column in metric]

        result = df.group_by(group_by, maintain_order=True).agg(expressions)
        result.columns = [self._clean_column_name(column) for column in result.columns]

        return result

    def _count(self, df: pl.DataFrame, plan: dict) -> list[dict]:
        group_by = self._resolve_group_by(df, plan)

        if not group_by:
            raise ValueError("group_by nao encontrado para contagem.")

        result = df.group_by(group_by, maintain_order=True).len(name="Quantidade")

        result = self._sort_and_limit(
            result=result,
            y_column="Quantidade",
            plan=plan,
            default_limit=20,
        )

        return result.to_dicts()

    def _groupby(self, df: pl.DataFrame, plan: dict, aggregation: str) -> list[dict]:
        group_by = self._resolve_group_by(df, plan)

        if not group_by:
            raise ValueError("group_by nao encontrado para groupby.")

        metric = self._resolve_metric(df, plan)

        if not metric:
            raise ValueError("metric nao encontrada para groupby.")

        if aggregation in ["none", "count"]:
            aggregation = "sum"

        temp_df = self._to_numeric(df, metric)

        if temp_df.is_empty():
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

        return result.to_dicts()

    def _datetime_expr(self, column: str) -> pl.Expr:
        text = pl.col(column).cast(pl.Utf8, strict=False)

        return pl.coalesce([
            pl.col(column).cast(pl.Datetime, strict=False),
            text.str.to_datetime(strict=False),
            text.str.to_date(strict=False).cast(pl.Datetime),
        ])

    def _period_expr(self, column: str, time_freq: str) -> pl.Expr:
        value = pl.col(column)

        if time_freq == "D":
            return value.dt.strftime("%Y-%m-%d")

        if time_freq == "W":
            return value.dt.truncate("1w").dt.strftime("%Y-%m-%d")

        if time_freq == "Q":
            return pl.concat_str([
                value.dt.year().cast(pl.Utf8),
                pl.lit("-Q"),
                value.dt.quarter().cast(pl.Utf8),
            ])

        if time_freq == "Y":
            return value.dt.strftime("%Y")

        return value.dt.strftime("%Y-%m")

    def _time_groupby(self, df: pl.DataFrame, plan: dict, aggregation: str) -> list[dict]:
        time_column = (
            self._find_column(df, plan.get("time_column"))
            or self._find_column(df, plan.get("x"))
        )

        if not time_column:
            raise ValueError("time_column nao encontrada para time_groupby.")

        time_freq = plan.get("time_freq", "M")

        if time_freq not in ["D", "W", "M", "Q", "Y"]:
            time_freq = "M"

        temp_df = (
            df.with_columns(self._datetime_expr(time_column).alias("__time_column"))
            .drop_nulls(subset=["__time_column"])
        )

        if temp_df.is_empty():
            return []

        temp_df = temp_df.with_columns(
            self._period_expr("__time_column", time_freq).alias("Periodo")
        )

        group_columns = ["Periodo"]

        extra_group_by = self._resolve_columns(
            temp_df,
            plan.get("group_by"),
        )

        extra_group_by = [
            column for column in extra_group_by
            if column != time_column and column != "Periodo"
        ]

        group_columns.extend(extra_group_by)

        if aggregation == "count":
            result = (
                temp_df
                .group_by(group_columns, maintain_order=True)
                .len(name="Quantidade")
                .sort("Periodo")
                .head(100)
            )
        else:
            metric = self._resolve_metric(temp_df, plan)

            if not metric:
                raise ValueError("metric nao encontrada para time_groupby.")

            if aggregation == "none":
                aggregation = "sum"

            temp_df = self._to_numeric(temp_df, metric)

            if temp_df.is_empty():
                return []

            result = self._aggregate(
                df=temp_df,
                group_by=group_columns,
                metric=metric,
                aggregation=aggregation,
            )

            result = result.sort("Periodo").head(100)

        if len(group_columns) > 1:
            result = result.with_columns(
                pl.concat_str(
                    [
                        pl.col(column).cast(pl.Utf8, strict=False).fill_null("")
                        for column in group_columns
                    ],
                    separator=" | ",
                ).alias("label")
            )
        else:
            result = result.with_columns(pl.col("Periodo").cast(pl.Utf8).alias("label"))

        return result.to_dicts()

    def _scatter(self, df: pl.DataFrame, plan: dict) -> list[dict]:
        x = self._find_column(df, plan.get("x"))
        y = self._find_column(df, plan.get("y"))

        if not x or not y:
            raise ValueError("x ou y nao encontrado para scatter.")

        temp_df = self._to_numeric(df, [x, y])

        if temp_df.is_empty():
            return []

        limit = plan.get("limit", 100)

        try:
            limit = int(limit)
        except Exception:
            limit = 100

        limit = max(1, min(limit, 500))

        return temp_df.select([x, y]).head(limit).to_dicts()

    def _kpi(self, df: pl.DataFrame, plan: dict, aggregation: str) -> list[dict]:
        metric = self._resolve_metric(df, plan)

        if not metric:
            raise ValueError("metric nao encontrada para kpi.")

        column = metric[0]

        temp_df = self._to_numeric(df, [column])

        if temp_df.is_empty():
            return []

        if aggregation == "mean":
            value = temp_df.select(pl.col(column).mean()).item()
        elif aggregation == "max":
            value = temp_df.select(pl.col(column).max()).item()
        elif aggregation == "min":
            value = temp_df.select(pl.col(column).min()).item()
        elif aggregation == "median":
            value = temp_df.select(pl.col(column).median()).item()
        elif aggregation == "count":
            value = temp_df.select(pl.col(column).count()).item()
        else:
            aggregation = "sum"
            value = temp_df.select(pl.col(column).sum()).item()

        return [
            {
                "label": plan.get("title", column),
                column: value,
            }
        ]

    def _table(self, df: pl.DataFrame, plan: dict) -> list[dict]:
        limit = plan.get("limit", 50)

        try:
            limit = int(limit)
        except Exception:
            limit = 50

        limit = max(1, min(limit, 200))

        return df.head(limit).to_dicts()
