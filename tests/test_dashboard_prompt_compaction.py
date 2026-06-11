import unittest

from app.data_cleaner import DataCleaner
from app.data_profiler import DataProfiler
from app.polars_tools import PolarsTools
from app.service import Service, AI_UNIQUE_VALUES_LIMIT


class FakeAccounts:
    def valid_token(self, token: str) -> bool:
        return True


class FakeInterpreter:
    def __init__(self):
        self.schema = None

    def dashboard_plan(self, prompt: str, schema: dict) -> dict:
        self.schema = schema
        return {
            "tool": "dashboard_plan",
            "dataset_type": "ecommerce",
            "analysis_type": "general",
            "business_context": "Vendas de ecommerce",
            "priority_metrics": ["Valor"],
            "rename_columns": {},
            "charts": [
                {
                    "title": "Valor por categoria",
                    "operation": "groupby",
                    "chart_type": "bar",
                    "group_by": ["Categoria"],
                    "metric": ["Valor"],
                    "aggregation": ["sum"],
                    "x": "Categoria",
                    "y": "Valor",
                    "time_column": None,
                    "time_freq": "M",
                    "drill_down_hierarchy": ["Categoria", "Produto"],
                    "filters": [],
                    "limit": 10,
                    "sort": "desc",
                    "reason": "Ranking de categorias",
                }
            ],
        }


class FakeGenerator:
    def __init__(self):
        self.charts = None
        self.schema = None
        self.plan = None

    def dashboard_analysis_multi(self, prompt, charts, schema, plan):
        self.charts = charts
        self.schema = schema
        self.plan = plan
        return "Resumo gerado"


class DashboardPromptCompactionTest(unittest.TestCase):
    def make_service(self) -> Service:
        service = Service.__new__(Service)
        service.accounts = FakeAccounts()
        service.interpreter = FakeInterpreter()
        service.generator = FakeGenerator()
        service.cleaner = DataCleaner()
        service.profiler = DataProfiler()
        service.polars_tools = PolarsTools()
        return service

    def test_large_dashboard_payload_is_compacted_only_for_ai(self):
        service = self.make_service()
        dataset = [
            {
                "Categoria": f"Categoria {index % 20}",
                "Produto": f"Produto {index}",
                "Valor": index + 1,
            }
            for index in range(6000)
        ]

        result = service._build_dashboard_analysis({
            "token": "token",
            "prompt": None,
            "dataset": dataset,
        })

        storage_drill_down = result["charts"][0]["drill_down"]
        ai_drill_down = service.generator.charts[0]["drill_down"]

        self.assertTrue(storage_drill_down["enabled"])
        self.assertIn("rows", storage_drill_down)
        self.assertGreater(len(storage_drill_down["rows"]), 1000)
        self.assertNotIn("rows", ai_drill_down)

        ai_unique_values = service.generator.schema["unique_values"]
        plan_unique_values = service.interpreter.schema["unique_values"]

        self.assertLessEqual(
            len(ai_unique_values["Categoria"]),
            AI_UNIQUE_VALUES_LIMIT,
        )
        self.assertLessEqual(
            len(plan_unique_values["Categoria"]),
            AI_UNIQUE_VALUES_LIMIT,
        )


if __name__ == "__main__":
    unittest.main()
