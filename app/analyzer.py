import pandas as pd

from app.pandas_tools import PandasTools


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
        self.pandas_tools = PandasTools()

    def run(self, dataset: list[dict], interpretation: dict | None) -> dict:
        interpretation = interpretation or {}

        if not dataset:
            return self._empty_chart(interpretation)

        df = pd.DataFrame(dataset)

        if df.empty:
            return self._empty_chart(interpretation)

        df = self._normalize_dataframe_columns(df)
        df = self.pandas_tools.filter_dataframe(df, interpretation.get("filters") or [])

        if df.empty:
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
            chart["title"] = chart_spec.get("title") or chart.get("title") or f"Gráfico {index + 1}"
            chart["reason"] = chart_spec.get("reason", "")

            results.append(chart)

        return results

    def _normalize_dataframe_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df.columns = [str(column).strip() for column in df.columns]
        return df

    def _normalize_name(self, value) -> str:
        return str(value).strip().lower()

    def _find_column(self, df: pd.DataFrame, column) -> str | None:
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

    def _resolve_first_column(self, df: pd.DataFrame, value) -> str | None:
        for item in self._as_list(value):
            column = self._find_column(df, item)

            if column:
                return column

        return None

    def _empty_chart(self, interpretation: dict | None = None) -> dict:
        interpretation = interpretation or {}

        return {
            "id": interpretation.get("id"),
            "title": interpretation.get("title", "Gráfico"),
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

    def _numeric_columns(self, df: pd.DataFrame) -> list[str]:
        result = []

        for column in df.columns:
            converted = pd.to_numeric(df[column], errors="coerce")

            if converted.notna().sum() > 0:
                result.append(column)

        return result

    def _categorical_columns(self, df: pd.DataFrame) -> list[str]:
        numeric = set(self._numeric_columns(df))
        return [column for column in df.columns if column not in numeric]

    def _resolve_x_column(self, df: pd.DataFrame, interpretation: dict) -> str | None:
        return (
            self._resolve_first_column(df, interpretation.get("x"))
            or self._resolve_first_column(df, interpretation.get("group_by"))
            or self._resolve_first_column(df, interpretation.get("dimension"))
            or self._first_categorical_column(df)
        )

    def _resolve_y_column(self, df: pd.DataFrame, interpretation: dict, allow_fallback: bool = False) -> str | None:
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

    def _first_numeric_column(self, df: pd.DataFrame) -> str | None:
        numeric_columns = self._numeric_columns(df)
        return numeric_columns[0] if numeric_columns else None

    def _first_categorical_column(self, df: pd.DataFrame) -> str | None:
        preferred = [
            "campanha",
            "canal",
            "categoria",
            "produto",
            "cliente",
            "regiao",
            "região",
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
        result: pd.DataFrame,
        y: str | None,
        interpretation: dict,
        default_limit: int = 20,
    ) -> pd.DataFrame:
        limit = interpretation.get("limit", default_limit)

        try:
            limit = int(limit)
        except Exception:
            limit = default_limit

        limit = max(1, min(limit, 100))

        sort = interpretation.get("sort", "desc")

        if y and y in result.columns and sort in ["desc", "asc"]:
            result = result.sort_values(by=y, ascending=sort == "asc")

        return result.head(limit)

    def _to_numeric_df(self, df: pd.DataFrame, column: str) -> pd.DataFrame:
        df = df.copy()
        df[column] = pd.to_numeric(df[column], errors="coerce")
        return df.dropna(subset=[column])

    def _aggregate(self, df: pd.DataFrame, x: str, y: str, aggregation: str) -> pd.DataFrame:
        if aggregation == "mean":
            return df.groupby(x, dropna=False)[y].mean().reset_index()

        if aggregation == "max":
            return df.groupby(x, dropna=False)[y].max().reset_index()

        if aggregation == "min":
            return df.groupby(x, dropna=False)[y].min().reset_index()

        if aggregation == "median":
            return df.groupby(x, dropna=False)[y].median().reset_index()

        return df.groupby(x, dropna=False)[y].sum().reset_index()

    def _count(self, df: pd.DataFrame, chart_type: str, interpretation: dict) -> dict:
        x = self._resolve_x_column(df, interpretation)

        if not x:
            return self._empty_chart(interpretation)

        result = df.groupby(x, dropna=False).size().reset_index(name="count")
        result = self._apply_limit_and_sort(result, "count", interpretation)

        return {
            "id": interpretation.get("id"),
            "title": interpretation.get("title", f"Quantidade por {x}"),
            "type": chart_type,
            "x": x,
            "y": "count",
            "data": result.to_dict(orient="records"),
            "operation": "count",
            "aggregation": "count",
            "reason": interpretation.get("reason", ""),
        }

    def _groupby(self, df: pd.DataFrame, chart_type: str, interpretation: dict, aggregation: str) -> dict:
        x = self._resolve_x_column(df, interpretation)
        y = self._resolve_y_column(df, interpretation, allow_fallback=False)

        if not x or not y:
            return self._empty_chart(interpretation)

        if aggregation in ["none", "count"]:
            aggregation = "sum"

        df = self._to_numeric_df(df, y)

        if df.empty:
            return self._empty_chart(interpretation)

        result = self._aggregate(df, x, y, aggregation)
        result = self._apply_limit_and_sort(result, y, interpretation)

        return {
            "id": interpretation.get("id"),
            "title": interpretation.get("title", f"{y} por {x}"),
            "type": chart_type,
            "x": x,
            "y": y,
            "data": result.to_dict(orient="records"),
            "operation": "groupby",
            "aggregation": aggregation,
            "reason": interpretation.get("reason", ""),
        }

    def _time_groupby(self, df: pd.DataFrame, chart_type: str, interpretation: dict) -> dict:
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

        df = df.copy()
        df[time_column] = pd.to_datetime(df[time_column], errors="coerce")
        df = df.dropna(subset=[time_column])

        if df.empty:
            return self._empty_chart(interpretation)

        df["periodo"] = df[time_column].dt.to_period(time_freq).astype(str)

        if aggregation == "count":
            result = df.groupby("periodo", dropna=False).size().reset_index(name="count")
            final_y = "count"
        else:
            y = self._resolve_y_column(df, interpretation, allow_fallback=False)

            if not y:
                return self._empty_chart(interpretation)

            if aggregation == "none":
                aggregation = "sum"

            df = self._to_numeric_df(df, y)

            if df.empty:
                return self._empty_chart(interpretation)

            result = self._aggregate(df, "periodo", y, aggregation)
            final_y = y

        result = result.sort_values(by="periodo").head(100)

        return {
            "id": interpretation.get("id"),
            "title": interpretation.get("title", "Evolução temporal"),
            "type": chart_type if chart_type in ["line", "area", "bar"] else "line",
            "x": "periodo",
            "y": final_y,
            "data": result.to_dict(orient="records"),
            "operation": "time_groupby",
            "aggregation": aggregation,
            "reason": interpretation.get("reason", ""),
        }

    def _scatter(self, df: pd.DataFrame, chart_type: str, interpretation: dict) -> dict:
        x = self._resolve_first_column(df, interpretation.get("x"))
        y = self._resolve_first_column(df, interpretation.get("y"))

        numeric_columns = self._numeric_columns(df)

        if x not in numeric_columns:
            x = numeric_columns[0] if len(numeric_columns) >= 1 else None

        if y not in numeric_columns or y == x:
            y = numeric_columns[1] if len(numeric_columns) >= 2 else None

        if not x or not y:
            return self._empty_chart(interpretation)

        df = df.copy()
        df[x] = pd.to_numeric(df[x], errors="coerce")
        df[y] = pd.to_numeric(df[y], errors="coerce")
        df = df.dropna(subset=[x, y])

        if df.empty:
            return self._empty_chart(interpretation)

        limit = interpretation.get("limit", 100)

        try:
            limit = int(limit)
        except Exception:
            limit = 100

        result = df[[x, y]].head(max(1, min(limit, 500)))

        return {
            "id": interpretation.get("id"),
            "title": interpretation.get("title", f"Relação entre {x} e {y}"),
            "type": "scatter",
            "x": x,
            "y": y,
            "data": result.to_dict(orient="records"),
            "operation": "scatter",
            "aggregation": "none",
            "reason": interpretation.get("reason", ""),
        }

    def _kpi(self, df: pd.DataFrame, chart_type: str, interpretation: dict, aggregation: str) -> dict:
        y = self._resolve_y_column(df, interpretation, allow_fallback=False)

        if not y:
            return self._empty_chart(interpretation)

        df = self._to_numeric_df(df, y)

        if df.empty:
            return self._empty_chart(interpretation)

        if aggregation == "mean":
            value = df[y].mean()
        elif aggregation == "max":
            value = df[y].max()
        elif aggregation == "min":
            value = df[y].min()
        elif aggregation == "median":
            value = df[y].median()
        elif aggregation == "count":
            value = df[y].count()
        else:
            aggregation = "sum"
            value = df[y].sum()

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

    def _table(self, df: pd.DataFrame, chart_type: str, interpretation: dict) -> dict:
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
            "data": df.head(limit).to_dict(orient="records"),
            "operation": "table",
            "aggregation": "none",
            "reason": interpretation.get("reason", ""),
        }
