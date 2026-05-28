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

    def _normalize_group_by(self, group_by) -> list[str]:
        if isinstance(group_by, str):
            return [group_by]

        if isinstance(group_by, list):
            return group_by

        raise ValueError(f"group_by inválido: {group_by}")


    def _groupby(
            self,
            df,
            group_by,
            metric: str | None,
            aggregation: str
        ) -> list[dict]:
            group_columns = self._normalize_group_by(group_by)

            for column in group_columns:
                if column not in df.columns:
                    raise ValueError(f"Coluna group_by inválida: {column}")

            if aggregation == "count":
                result = (
                    df.groupby(group_columns)
                    .size()
                    .reset_index(name="value")
                    .sort_values("value", ascending=False)
                    .head(20)
                )

                return result.to_dict(orient="records")

            if not metric or metric not in df.columns:
                raise ValueError(f"Coluna metric inválida: {metric}")

            result = (
                df.groupby(group_columns)[metric]
                .agg(aggregation)
                .reset_index(name="value")
                .sort_values("value", ascending=False)
                .head(20)
            )

            return result.to_dict(orient="records")


    def _time_groupby(
        self,
        df,
        time_column: str,
        metric: str | None,
        aggregation: str,
        time_freq: str,
        group_by=None
    ) -> list[dict]:
        if not time_column or time_column not in df.columns:
            raise ValueError(f"Coluna de tempo inválida: {time_column}")

        temp_df = df.copy()

        temp_df[time_column] = pd.to_datetime(
            temp_df[time_column],
            errors="coerce"
        )

        temp_df = temp_df.dropna(subset=[time_column])

        if temp_df.empty:
            raise ValueError("Nenhuma data válida encontrada.")

        temp_df["periodo"] = (
            temp_df[time_column]
            .dt.to_period(time_freq)
            .astype(str)
        )

        group_columns = ["periodo"]

        if group_by:
            extra_groups = self._normalize_group_by(group_by)

            for column in extra_groups:
                if column not in temp_df.columns:
                    raise ValueError(f"Coluna group_by inválida: {column}")

            group_columns.extend(extra_groups)

        if aggregation == "count":
            result = (
                temp_df.groupby(group_columns)
                .size()
                .reset_index(name="value")
                .sort_values("periodo")
                .head(20)
            )
        else:
            if not metric or metric not in temp_df.columns:
                raise ValueError(f"Coluna metric inválida: {metric}")

            result = (
                temp_df.groupby(group_columns)[metric]
                .agg(aggregation)
                .reset_index(name="value")
                .sort_values("periodo")
                .head(20)
            )

        if len(group_columns) > 1:
            result["label"] = result[group_columns].astype(str).agg(" - ".join, axis=1)
        else:
            result["label"] = result["periodo"].astype(str)

        return result.to_dict(orient="records")
    
    
    @staticmethod
    def rename_columns_df(
        df: pd.DataFrame,
        rename_map: dict[str, str] | None
    ) -> pd.DataFrame:
        if df.empty:
            return df

        if not rename_map:
            return df

        safe_rename_map = {
            old_name: new_name.strip()
            for old_name, new_name in rename_map.items()
            if old_name in df.columns
            and isinstance(new_name, str)
            and new_name.strip()
        }

        if not safe_rename_map:
            return df

        return df.rename(columns=safe_rename_map)