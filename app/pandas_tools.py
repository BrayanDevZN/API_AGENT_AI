import pandas as pd


class PandasTools:
    def execute(self, df, plan: dict) -> list[dict]:
        operation = plan.get("operation")
        group_by = plan.get("group_by")
        metric = plan.get("metric")
        aggregation = plan.get("aggregation", "count")
        time_column = plan.get("time_column")
        time_freq = plan.get("time_freq", "M")

        if operation == "count":
            return self._count(df=df, group_by=group_by)

        if operation == "groupby":
            return self._groupby(
                df=df,
                group_by=group_by,
                metric=metric,
                aggregation=aggregation
            )

        if operation == "time_groupby":
            return self._time_groupby(
                df=df,
                time_column=time_column,
                metric=metric,
                aggregation=aggregation,
                time_freq=time_freq
            )

        raise ValueError("Operação não suportada.")

    def _count(self, df, group_by: str) -> list[dict]:
        if group_by not in df.columns:
            raise ValueError(f"Coluna group_by inválida: {group_by}")

        result = (
            df[group_by]
            .astype(str)
            .value_counts()
            .reset_index()
            .head(20)
        )

        result.columns = [group_by, "count"]

        return result.to_dict(orient="records")

    def _groupby(
        self,
        df,
        group_by: str,
        metric: str | None,
        aggregation: str
    ) -> list[dict]:
        if group_by not in df.columns:
            raise ValueError(f"Coluna group_by inválida: {group_by}")

        if aggregation == "count":
            return self._count(df=df, group_by=group_by)

        if not metric or metric not in df.columns:
            raise ValueError(f"Coluna metric inválida: {metric}")

        result = (
            df.groupby(group_by)[metric]
            .agg(aggregation)
            .reset_index()
            .sort_values(metric, ascending=False)
            .head(20)
        )

        return result.to_dict(orient="records")

    def _time_groupby(
        self,
        df,
        time_column: str,
        metric: str | None,
        aggregation: str,
        time_freq: str
    ) -> list[dict]:
        if time_column not in df.columns:
            raise ValueError(f"Coluna de tempo inválida: {time_column}")

        temp_df = df.copy()
        temp_df[time_column] = pd.to_datetime(
            temp_df[time_column],
            errors="coerce"
        )

        temp_df = temp_df.dropna(subset=[time_column])

        if temp_df.empty:
            raise ValueError("Nenhuma data válida encontrada.")

        temp_df["periodo"] = temp_df[time_column].dt.to_period(time_freq).astype(str)

        if aggregation == "count":
            result = (
                temp_df.groupby("periodo")
                .size()
                .reset_index(name="count")
                .sort_values("periodo")
            )

            return result.to_dict(orient="records")

        if not metric or metric not in temp_df.columns:
            raise ValueError(f"Coluna metric inválida: {metric}")

        result = (
            temp_df.groupby("periodo")[metric]
            .agg(aggregation)
            .reset_index()
            .sort_values("periodo")
        )

        return result.to_dict(orient="records")