import pandas as pd


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
        "none",
    }

    VALID_OPERATIONS = {
        "groupby",
        "count",
        "time_groupby",
    }

    VALID_AGGREGATIONS = {
        "sum",
        "mean",
        "count",
        "max",
        "min",
        "none",
    }

    def run(self, dataset: list[dict], interpretation: dict | None) -> dict:
        interpretation = interpretation or {}

        if not dataset:
            return self._empty_chart(interpretation)

        df = pd.DataFrame(dataset)

        if df.empty:
            return self._empty_chart(interpretation)

        chart_type = interpretation.get("chart_type", "none")
        operation = interpretation.get("operation")
        x = interpretation.get("x")
        y = interpretation.get("y")
        aggregation = self._get_first_value(
            interpretation.get("aggregation", "none")
        )

        if chart_type not in self.VALID_CHART_TYPES:
            chart_type = "none"

        if aggregation not in self.VALID_AGGREGATIONS:
            aggregation = "none"

        if chart_type == "none":
            return self._empty_chart(interpretation)

        if operation not in self.VALID_OPERATIONS:
            operation = self._infer_operation(aggregation)

        if operation == "time_groupby":
            return self._time_groupby(
                df=df,
                chart_type=chart_type,
                interpretation=interpretation,
            )

        if operation == "count" or aggregation == "count":
            return self._count(
                df=df,
                chart_type=chart_type,
                interpretation=interpretation,
            )

        return self._groupby(
            df=df,
            chart_type=chart_type,
            interpretation=interpretation,
            aggregation=aggregation,
        )

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

    def _empty_chart(self, interpretation: dict | None = None) -> dict:
        interpretation = interpretation or {}

        return {
            "id": interpretation.get("id"),
            "title": interpretation.get("title", "Gráfico"),
            "type": "none",
            "x": None,
            "y": None,
            "data": [],
            "reason": interpretation.get("reason", ""),
        }

    def _infer_operation(self, aggregation: str) -> str:
        if aggregation == "count":
            return "count"

        return "groupby"

    def _get_first_value(self, value):
        if isinstance(value, list):
            return value[0] if value else "none"

        return value

    def _get_first_column(self, value):
        if isinstance(value, list):
            return value[0] if value else None

        return value

    def _column_exists(self, df: pd.DataFrame, column: str | None) -> bool:
        return bool(column) and column in df.columns

    def _sort_result(self, result: pd.DataFrame, y: str | None) -> pd.DataFrame:
        if y and y in result.columns:
            return result.sort_values(by=y, ascending=False).head(20)

        return result.head(20)

    def _count(
        self,
        df: pd.DataFrame,
        chart_type: str,
        interpretation: dict,
    ) -> dict:
        x = interpretation.get("x")

        if not self._column_exists(df, x):
            group_by = interpretation.get("group_by", [])
            x = self._get_first_column(group_by)

        if not self._column_exists(df, x):
            return self._empty_chart(interpretation)

        result = (
            df.groupby(x, dropna=False)
            .size()
            .reset_index(name="count")
        )

        result = self._sort_result(result, "count")

        return {
            "id": interpretation.get("id"),
            "title": interpretation.get("title", "Contagem por categoria"),
            "type": chart_type,
            "x": x,
            "y": "count",
            "data": result.to_dict(orient="records"),
            "operation": "count",
            "aggregation": "count",
            "reason": interpretation.get("reason", ""),
        }

    def _groupby(
        self,
        df: pd.DataFrame,
        chart_type: str,
        interpretation: dict,
        aggregation: str,
    ) -> dict:
        x = interpretation.get("x")
        y = interpretation.get("y")

        if not self._column_exists(df, x):
            group_by = interpretation.get("group_by", [])
            x = self._get_first_column(group_by)

        if not self._column_exists(df, y):
            metric = interpretation.get("metric", [])
            y = self._get_first_column(metric)

        if not self._column_exists(df, x) or not self._column_exists(df, y):
            return self._empty_chart(interpretation)

        df = df.copy()
        df[y] = pd.to_numeric(df[y], errors="coerce")
        df = df.dropna(subset=[y])

        if df.empty:
            return self._empty_chart(interpretation)

        if aggregation == "sum":
            result = df.groupby(x, dropna=False)[y].sum().reset_index()
        elif aggregation == "mean":
            result = df.groupby(x, dropna=False)[y].mean().reset_index()
        elif aggregation == "max":
            result = df.groupby(x, dropna=False)[y].max().reset_index()
        elif aggregation == "min":
            result = df.groupby(x, dropna=False)[y].min().reset_index()
        else:
            result = df[[x, y]].copy()

        result = self._sort_result(result, y)

        return {
            "id": interpretation.get("id"),
            "title": interpretation.get("title", "Gráfico gerado"),
            "type": chart_type,
            "x": x,
            "y": y,
            "data": result.to_dict(orient="records"),
            "operation": "groupby",
            "aggregation": aggregation,
            "reason": interpretation.get("reason", ""),
        }

    def _time_groupby(
        self,
        df: pd.DataFrame,
        chart_type: str,
        interpretation: dict,
    ) -> dict:
        time_column = interpretation.get("time_column")
        y = interpretation.get("y")
        time_freq = interpretation.get("time_freq", "M")
        aggregation = self._get_first_value(
            interpretation.get("aggregation", "sum")
        )

        if not self._column_exists(df, time_column):
            return self._empty_chart(interpretation)

        if not self._column_exists(df, y):
            metric = interpretation.get("metric", [])
            y = self._get_first_column(metric)

        if aggregation == "count":
            y = "count"

        if aggregation != "count" and not self._column_exists(df, y):
            return self._empty_chart(interpretation)

        if time_freq not in ["D", "M", "Y"]:
            time_freq = "M"

        df = df.copy()
        df[time_column] = pd.to_datetime(df[time_column], errors="coerce")
        df = df.dropna(subset=[time_column])

        if df.empty:
            return self._empty_chart(interpretation)

        df["periodo"] = df[time_column].dt.to_period(time_freq).astype(str)

        if aggregation == "count":
            result = (
                df.groupby("periodo", dropna=False)
                .size()
                .reset_index(name="count")
            )

            final_y = "count"
        else:
            df[y] = pd.to_numeric(df[y], errors="coerce")
            df = df.dropna(subset=[y])

            if df.empty:
                return self._empty_chart(interpretation)

            if aggregation == "mean":
                result = df.groupby("periodo", dropna=False)[y].mean().reset_index()
            elif aggregation == "max":
                result = df.groupby("periodo", dropna=False)[y].max().reset_index()
            elif aggregation == "min":
                result = df.groupby("periodo", dropna=False)[y].min().reset_index()
            else:
                result = df.groupby("periodo", dropna=False)[y].sum().reset_index()

            final_y = y

        result = result.sort_values(by="periodo").head(50)

        return {
            "id": interpretation.get("id"),
            "title": interpretation.get("title", "Evolução temporal"),
            "type": chart_type if chart_type in ["line", "area"] else "line",
            "x": "periodo",
            "y": final_y,
            "data": result.to_dict(orient="records"),
            "operation": "time_groupby",
            "aggregation": aggregation,
            "reason": interpretation.get("reason", ""),
        }