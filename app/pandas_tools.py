class PandasTools:
    def execute(self, df, plan: dict) -> list[dict]:
        operation = plan.get("operation")
        group_by = plan.get("group_by")
        metric = plan.get("metric")
        aggregation = plan.get("aggregation", "sum")

        if operation == "groupby":
            if group_by not in df.columns:
                raise ValueError(f"Coluna group_by inválida: {group_by}")

            if metric not in df.columns:
                raise ValueError(f"Coluna metric inválida: {metric}")

            result = (
                df.groupby(group_by)[metric]
                .agg(aggregation)
                .reset_index()
                .sort_values(metric, ascending=False)
                .head(20)
            )

            return result.to_dict(orient="records")

        if operation == "count":
            if group_by not in df.columns:
                raise ValueError(f"Coluna group_by inválida: {group_by}")

            result = (
                df[group_by]
                .value_counts()
                .reset_index()
                .head(20)
            )

            result.columns = [group_by, "count"]

            return result.to_dict(orient="records")

        raise ValueError("Operação não suportada.")