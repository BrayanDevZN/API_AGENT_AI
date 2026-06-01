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

        df = self._normalize_dataframe_columns(df)

        chart_type = interpretation.get("chart_type", "none")
        operation = interpretation.get("operation")
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
            chart["title"] = (
                chart_spec.get("title")
                or chart.get("title")
                or f"Gráfico {index + 1}"
            )
            chart["reason"] = chart_spec.get("reason", "")

            results.append(chart)

        return results

    def _normalize_dataframe_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df.columns = [str(column).strip() for column in df.columns]
        return df

    def _normalize_name(self, value: str | None) -> str | None:
        if value is None:
            return None

        return str(value).strip().lower()

    def _find_column(self, df: pd.DataFrame, column: str | None) -> str | None:
        if not column:
            return None

        target = self._normalize_name(column)

        for real_column in df.columns:
            if self._normalize_name(real_column) == target:
                return real_column

        return None

    def _resolve_column(self, df: pd.DataFrame, value) -> str | None:
        column = self._get_first_column(value)
        return self._find_column(df, column)

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

    def _sort_result(self, result: pd.DataFrame, y: str | None) -> pd.DataFrame:
        if y and y in result.columns:
            return result.sort_values(by=y, ascending=False).head(20)

        return result.head(20)

    def _get_first_numeric_column(self, df: pd.DataFrame) -> str | None:
        numeric_columns = df.select_dtypes(include="number").columns.tolist()

        if numeric_columns:
            return numeric_columns[0]

        for column in df.columns:
            converted = pd.to_numeric(df[column], errors="coerce")

            if converted.notna().sum() > 0:
                return column

        return None

    def _get_first_categorical_column(self, df: pd.DataFrame) -> str | None:
        if df.empty or len(df.columns) == 0:
            return None

        numeric_columns = set(df.select_dtypes(include="number").columns.tolist())

        preferred_names = [
            "campanha",
            "produto",
            "categoria",
            "canal",
            "região",
            "regiao",
            "cidade",
            "cliente",
            "vendedor",
            "forma_pagamento",
            "status",
        ]

        for preferred in preferred_names:
            for column in df.columns:
                if self._normalize_name(column) == preferred:
                    return column

        for column in df.columns:
            if column not in numeric_columns:
                return column

        return df.columns[0]

    def _resolve_x_column(self, df: pd.DataFrame, interpretation: dict) -> str | None:
        x = self._resolve_column(df, interpretation.get("x"))

        if not x:
            x = self._resolve_column(df, interpretation.get("group_by", []))

        if not x:
            x = self._resolve_column(df, interpretation.get("dimension", []))

        if not x:
            x = self._get_first_categorical_column(df)

        return x

    def _resolve_y_column(self, df: pd.DataFrame, interpretation: dict) -> str | None:
        y = self._resolve_column(df, interpretation.get("y"))

        if not y:
            y = self._resolve_column(df, interpretation.get("metric", []))

        if not y:
            y = self._resolve_column(df, interpretation.get("value", []))

        if not y:
            y = self._get_first_numeric_column(df)

        return y

    def _count(
        self,
        df: pd.DataFrame,
        chart_type: str,
        interpretation: dict,
    ) -> dict:
        x = self._resolve_x_column(df, interpretation)

        if not x:
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
        x = self._resolve_x_column(df, interpretation)
        y = self._resolve_y_column(df, interpretation)

        if not x or not y:
            return self._empty_chart(interpretation)

        if aggregation == "none":
            aggregation = "sum"

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
        elif aggregation == "count":
            result = (
                df.groupby(x, dropna=False)
                .size()
                .reset_index(name="count")
            )
            y = "count"
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
        time_column = self._resolve_column(df, interpretation.get("time_column"))

        if not time_column:
            time_column = self._resolve_column(df, interpretation.get("date_column"))

        if not time_column:
            time_column = self._resolve_column(df, interpretation.get("x"))

        y = self._resolve_y_column(df, interpretation)

        time_freq = interpretation.get("time_freq", "M")
        aggregation = self._get_first_value(
            interpretation.get("aggregation", "sum")
        )

        if not time_column:
            return self._empty_chart(interpretation)

        if aggregation == "count":
            y = "count"

        if aggregation != "count" and not y:
            y = self._get_first_numeric_column(df)

        if aggregation != "count" and not y:
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
