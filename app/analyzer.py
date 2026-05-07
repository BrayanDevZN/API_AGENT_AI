import pandas as pd


class Analyzer:
    def run(self, dataset: list[dict], interpretation: dict):
        if not dataset:
            return {
                "type": "none",
                "x": None,
                "y": None,
                "data": []
            }

        df = pd.DataFrame(dataset)

        chart_type = interpretation.get("chart_type", "none")
        x = interpretation.get("x")
        y = interpretation.get("y")
        aggregation = interpretation.get("aggregation", "none")

        if chart_type == "none" or not x or x not in df.columns:
            return {
                "type": "none",
                "x": None,
                "y": None,
                "data": []
            }

        if aggregation == "count":
            result = df.groupby(x).size().reset_index(name="count")

            return {
                "type": chart_type,
                "x": x,
                "y": "count",
                "data": result.to_dict(orient="records")
            }

        if not y or y not in df.columns:
            return {
                "type": "none",
                "x": None,
                "y": None,
                "data": []
            }

        df[y] = pd.to_numeric(df[y], errors="coerce")
        df = df.dropna(subset=[y])

        if aggregation == "sum":
            result = df.groupby(x)[y].sum().reset_index()
        elif aggregation == "mean":
            result = df.groupby(x)[y].mean().reset_index()
        elif aggregation == "max":
            result = df.groupby(x)[y].max().reset_index()
        elif aggregation == "min":
            result = df.groupby(x)[y].min().reset_index()
        else:
            result = df[[x, y]]

        return {
            "type": chart_type,
            "x": x,
            "y": y,
            "data": result.to_dict(orient="records")
        }