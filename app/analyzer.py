import polars as pl

from app.polars_tools import PolarsTools


class Analyzer:
    VALID_CHART_TYPES = {
        "bar",
        "horizontal_bar",
        "line",
        "area",
        "pie",
        "donut",
        "scatter",
        "table",
        "kpi",
        "none",
    }

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
        "count",
        "max",
        "min",
        "median",
        "none",
    }

    VALID_TIME_FREQS = {"D", "W", "M", "Q", "Y"}

    def __init__(self):
        self.polars_tools = PolarsTools()

    def run(self, dataset: list[dict], interpretation: dict | None) -> dict:
        interpretation = interpretation or {}

        if not dataset:
            return self._empty_chart(interpretation)

        df = pl.from_dicts(dataset, infer_schema_length=None)

        if df.is_empty():
            return self._empty_chart(interpretation)

        df = self._normalize_dataframe_columns(df)
        df = self.polars_tools.filter_dataframe(df, interpretation.get("filters") or [])

        if df.is_empty():
            return self._empty_chart(interpretation)

        chart_type = interpretation.get("chart_type", "none")
        operation = interpretation.get("operation")
        aggregation = self._get_first_value(interpretation.get("aggregation", "none"))

        if chart_type not in self.VALID_CHART_TYPES:
            chart_type = "none"

        if operation not in self.VALID_OPERATIONS:
            operation = self._infer_operation(chart_type, aggregation)

        if aggregation not in self.VALID_AGGREGATIONS:
            aggregation = "none"

        if chart_type == "none":
            return self._empty_chart(interpretation)

        if operation == "kpi":
            return self._kpi(df, chart_type, interpretation, aggregation)

        if operation == "scatter":
            return self._scatter(df, chart_type, interpretation)

        if operation == "table":
            return self._table(df, chart_type, interpretation)

        if operation == "time_groupby":
            return self._time_groupby(df, chart_type, interpretation)

        if operation == "count" or aggregation == "count":
            return self._count(df, chart_type, interpretation)

        return self._groupby(df, chart_type, interpretation, aggregation)

    def run_many(self, dataset: list[dict], charts: list[dict] | None) -> list[dict]:
        if not charts:
            return []

        results = []

        for index, chart_spec in enumerate(charts):
            if not isinstance(chart_spec, dict):
                continue

            chart = self.run(dataset=dataset, interpretation=chart_spec)

            if chart.get("type") == "none":
                continue

            chart["id"] = chart_spec.get("id") or f"chart_{index + 1}"
            chart["title"] = chart_spec.get("title") or chart.get("title") or f"Grafico {index + 1}"
            chart["reason"] = chart_spec.get("reason", "")

            results.append(chart)

        return results

    def _normalize_dataframe_columns(self, df: pl.DataFrame) -> pl.DataFrame:
        df = df.clone()
        df.columns = [str(column).strip() for column in df.columns]
        return df

    def _normalize_name(self, value) -> str:
        return str(value).strip().lower()

    def _find_column(self, df: pl.DataFrame, column) -> str | None:
        if not column:
            return None

        target = self._normalize_name(column)

        for real_column in df.columns:
            if self._normalize_name(real_column) == target:
                return real_column

        return None

    def _as_list(self, value) -> list:
        if value is None:
            return []

        if isinstance(value, list):
            return [item for item in value if item not in [None, ""]]

        return [value]

    def _get_first_value(self, value):
        values = self._as_list(value)
        return values[0] if values else "none"

    def _resolve_first_column(self, df: pl.DataFrame, value) -> str | None:
        for item in self._as_list(value):
            column = self._find_column(df, item)

            if column:
                return column

        return None

    def _empty_chart(self, interpretation: dict | None = None) -> dict:
        interpretation = interpretation or {}

        return {
            "id": interpretation.get("id"),
            "title": interpretation.get("title", "Grafico"),
            "type": "none",
            "x": None,
            "y": None,
            "data": [],
            "operation": interpretation.get("operation"),
            "aggregation": interpretation.get("aggregation"),
            "reason": interpretation.get("reason", ""),
        }

    def _infer_operation(self, chart_type: str, aggregation: str) -> str:
        if chart_type == "kpi":
            return "kpi"

        if chart_type == "scatter":
            return "scatter"

        if chart_type == "table":
            return "table"

        if aggregation == "count":
            return "count"

        return "groupby"

    def _numeric_columns(self, df: pl.DataFrame) -> list[str]:
        result = []

        for column in df.columns:
            converted = df.select(
                pl.col(column)
                .cast(pl.Float64, strict=False)
                .drop_nulls()
                .alias(column)
            )

            if converted.height > 0:
                result.append(column)

        return result

    def _categorical_columns(self, df: pl.DataFrame) -> list[str]:
        numeric = set(self._numeric_columns(df))
        return [column for column in df.columns if column not in numeric]

    def _resolve_x_column(self, df: pl.DataFrame, interpretation: dict) -> str | None:
        return (
            self._resolve_first_column(df, interpretation.get("x"))
            or self._resolve_first_column(df, interpretation.get("group_by"))
            or self._resolve_first_column(df, interpretation.get("dimension"))
            or self._first_categorical_column(df)
        )

    def _resolve_y_column(self, df: pl.DataFrame, interpretation: dict, allow_fallback: bool = False) -> str | None:
        y = (
            self._resolve_first_column(df, interpretation.get("metric"))
            or self._resolve_first_column(df, interpretation.get("y"))
            or self._resolve_first_column(df, interpretation.get("value"))
        )

        if y:
            return y

        if allow_fallback:
            return self._first_numeric_column(df)

        return None

    def _first_numeric_column(self, df: pl.DataFrame) -> str | None:
        numeric_columns = self._numeric_columns(df)
        return numeric_columns[0] if numeric_columns else None

    def _first_categorical_column(self, df: pl.DataFrame) -> str | None:
        preferred = [
            "campanha",
            "canal",
            "categoria",
            "produto",
            "cliente",
            "regiao",
            "regiao",
            "cidade",
            "status",
            "tipo",
        ]

        categorical = self._categorical_columns(df)

        for name in preferred:
            for column in categorical:
                if self._normalize_name(column) == name:
                    return column

        return categorical[0] if categorical else None

    def _apply_limit_and_sort(
        self,
        result: pl.DataFrame,
        y: str | None,
        interpretation: dict,
        default_limit: int = 20,
    ) -> pl.DataFrame:
        limit = interpretation.get("limit", default_limit)

        try:
            limit = int(limit)
        except Exception:
            limit = default_limit

        limit = max(1, min(limit, 100))

        sort = interpretation.get("sort", "desc")

        if y and y in result.columns and sort in ["desc", "asc"]:
            result = result.sort(
                y,
                descending=sort == "desc",
                nulls_last=True,
            )

        return result.head(limit)

    def _to_numeric_df(self, df: pl.DataFrame, column: str) -> pl.DataFrame:
        return (
            df.with_columns(pl.col(column).cast(pl.Float64, strict=False).alias(column))
            .drop_nulls(subset=[column])
        )

    def _aggregate(self, df: pl.DataFrame, x: str, y: str, aggregation: str) -> pl.DataFrame:
        if aggregation == "mean":
            expression = pl.col(y).mean().alias(y)
        elif aggregation == "max":
            expression = pl.col(y).max().alias(y)
        elif aggregation == "min":
            expression = pl.col(y).min().alias(y)
        elif aggregation == "median":
            expression = pl.col(y).median().alias(y)
        else:
            expression = pl.col(y).sum().alias(y)

        return df.group_by(x, maintain_order=True).agg(expression)

    def _count(self, df: pl.DataFrame, chart_type: str, interpretation: dict) -> dict:
        x = self._resolve_x_column(df, interpretation)

        if not x:
            return self._empty_chart(interpretation)

        result = df.group_by(x, maintain_order=True).len(name="count")
        result = self._apply_limit_and_sort(result, "count", interpretation)

        return {
            "id": interpretation.get("id"),
            "title": interpretation.get("title", f"Quantidade por {x}"),
            "type": chart_type,
            "x": x,
            "y": "count",
            "data": result.to_dicts(),
            "operation": "count",
            "aggregation": "count",
            "reason": interpretation.get("reason", ""),
        }

    def _groupby(self, df: pl.DataFrame, chart_type: str, interpretation: dict, aggregation: str) -> dict:
        x = self._resolve_x_column(df, interpretation)
        y = self._resolve_y_column(df, interpretation, allow_fallback=False)

        if not x or not y:
            return self._empty_chart(interpretation)

        if aggregation in ["none", "count"]:
            aggregation = "sum"

        df = self._to_numeric_df(df, y)

        if df.is_empty():
            return self._empty_chart(interpretation)

        result = self._aggregate(df, x, y, aggregation)
        result = self._apply_limit_and_sort(result, y, interpretation)

        return {
            "id": interpretation.get("id"),
            "title": interpretation.get("title", f"{y} por {x}"),
            "type": chart_type,
            "x": x,
            "y": y,
            "data": result.to_dicts(),
            "operation": "groupby",
            "aggregation": aggregation,
            "reason": interpretation.get("reason", ""),
        }

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

    def _time_groupby(self, df: pl.DataFrame, chart_type: str, interpretation: dict) -> dict:
        time_column = (
            self._resolve_first_column(df, interpretation.get("time_column"))
            or self._resolve_first_column(df, interpretation.get("date_column"))
            or self._resolve_first_column(df, interpretation.get("x"))
        )

        if not time_column:
            return self._empty_chart(interpretation)

        aggregation = self._get_first_value(interpretation.get("aggregation", "sum"))
        time_freq = interpretation.get("time_freq", "M")

        if time_freq not in self.VALID_TIME_FREQS:
            time_freq = "M"

        df = (
            df.with_columns(self._datetime_expr(time_column).alias("__period_source"))
            .drop_nulls(subset=["__period_source"])
        )

        if df.is_empty():
            return self._empty_chart(interpretation)

        df = df.with_columns(
            self._period_expr("__period_source", time_freq).alias("periodo")
        )

        if aggregation == "count":
            result = df.group_by("periodo", maintain_order=True).len(name="count")
            final_y = "count"
        else:
            y = self._resolve_y_column(df, interpretation, allow_fallback=False)

            if not y:
                return self._empty_chart(interpretation)

            if aggregation == "none":
                aggregation = "sum"

            df = self._to_numeric_df(df, y)

            if df.is_empty():
                return self._empty_chart(interpretation)

            result = self._aggregate(df, "periodo", y, aggregation)
            final_y = y

        result = result.sort("periodo").head(100)

        return {
            "id": interpretation.get("id"),
            "title": interpretation.get("title", "Evolucao temporal"),
            "type": chart_type if chart_type in ["line", "area", "bar"] else "line",
            "x": "periodo",
            "y": final_y,
            "data": result.to_dicts(),
            "operation": "time_groupby",
            "aggregation": aggregation,
            "reason": interpretation.get("reason", ""),
        }

    def _scatter(self, df: pl.DataFrame, chart_type: str, interpretation: dict) -> dict:
        x = self._resolve_first_column(df, interpretation.get("x"))
        y = self._resolve_first_column(df, interpretation.get("y"))

        numeric_columns = self._numeric_columns(df)

        if x not in numeric_columns:
            x = numeric_columns[0] if len(numeric_columns) >= 1 else None

        if y not in numeric_columns or y == x:
            y = numeric_columns[1] if len(numeric_columns) >= 2 else None

        if not x or not y:
            return self._empty_chart(interpretation)

        df = (
            df.with_columns([
                pl.col(x).cast(pl.Float64, strict=False).alias(x),
                pl.col(y).cast(pl.Float64, strict=False).alias(y),
            ])
            .drop_nulls(subset=[x, y])
        )

        if df.is_empty():
            return self._empty_chart(interpretation)

        limit = interpretation.get("limit", 100)

        try:
            limit = int(limit)
        except Exception:
            limit = 100

        result = df.select([x, y]).head(max(1, min(limit, 500)))

        return {
            "id": interpretation.get("id"),
            "title": interpretation.get("title", f"Relacao entre {x} e {y}"),
            "type": "scatter",
            "x": x,
            "y": y,
            "data": result.to_dicts(),
            "operation": "scatter",
            "aggregation": "none",
            "reason": interpretation.get("reason", ""),
        }

    def _kpi(self, df: pl.DataFrame, chart_type: str, interpretation: dict, aggregation: str) -> dict:
        y = self._resolve_y_column(df, interpretation, allow_fallback=False)

        if not y:
            return self._empty_chart(interpretation)

        df = self._to_numeric_df(df, y)

        if df.is_empty():
            return self._empty_chart(interpretation)

        if aggregation == "mean":
            value = df.select(pl.col(y).mean()).item()
        elif aggregation == "max":
            value = df.select(pl.col(y).max()).item()
        elif aggregation == "min":
            value = df.select(pl.col(y).min()).item()
        elif aggregation == "median":
            value = df.select(pl.col(y).median()).item()
        elif aggregation == "count":
            value = df.select(pl.col(y).count()).item()
        else:
            aggregation = "sum"
            value = df.select(pl.col(y).sum()).item()

        data = [{"label": interpretation.get("title", y), y: float(value)}]

        return {
            "id": interpretation.get("id"),
            "title": interpretation.get("title", f"Total de {y}"),
            "type": "kpi",
            "x": "label",
            "y": y,
            "data": data,
            "operation": "kpi",
            "aggregation": aggregation,
            "reason": interpretation.get("reason", ""),
        }

    def _table(self, df: pl.DataFrame, chart_type: str, interpretation: dict) -> dict:
        limit = interpretation.get("limit", 50)

        try:
            limit = int(limit)
        except Exception:
            limit = 50

        limit = max(1, min(limit, 200))

        return {
            "id": interpretation.get("id"),
            "title": interpretation.get("title", "Tabela de dados"),
            "type": "table",
            "x": None,
            "y": None,
            "data": df.head(limit).to_dicts(),
            "operation": "table",
            "aggregation": "none",
            "reason": interpretation.get("reason", ""),
        }
