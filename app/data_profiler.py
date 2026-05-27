class DataProfiler:
    def profile(self, df) -> dict:
        return {
            "rows": len(df),
            "columns": [
                {
                    "name": col,
                    "dtype": str(df[col].dtype),
                    "null_percent": round(float(df[col].isna().mean()) * 100, 2),
                    "sample": df[col].dropna().head(5).astype(str).tolist()
                }
                for col in df.columns
            ]
        }