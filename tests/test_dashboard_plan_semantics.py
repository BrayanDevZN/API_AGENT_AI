import json
import unittest

from app.interpreter import Interpreter


class DashboardPlanSemanticsTest(unittest.TestCase):
    def make_interpreter(self) -> Interpreter:
        return Interpreter.__new__(Interpreter)

    def test_replaces_technical_columns_with_business_columns(self):
        interpreter = self.make_interpreter()
        schema = {
            "columns": [
                {"name": "ID", "dtype": "Int64"},
                {"name": "Categoria", "dtype": "String"},
                {"name": "Valor", "dtype": "Float64"},
                {"name": "Email", "dtype": "String"},
            ],
            "numeric_columns": ["ID", "Valor"],
            "categorical_columns": ["Categoria", "Email"],
            "date_columns": [],
        }
        output = {
            "tool": "dashboard_plan",
            "dataset_type": "vendas",
            "analysis_type": "general",
            "business_context": "Vendas por categoria",
            "priority_metrics": ["ID"],
            "rename_columns": {},
            "charts": [
                {
                    "title": "Total de ID por Email",
                    "operation": "groupby",
                    "chart_type": "bar",
                    "group_by": ["Email"],
                    "metric": ["ID"],
                    "aggregation": ["sum"],
                    "x": "Email",
                    "y": "ID",
                    "time_column": None,
                    "time_freq": "M",
                    "drill_down_hierarchy": [],
                    "filters": [],
                    "limit": 10,
                    "sort": "desc",
                    "reason": "Plano ruim vindo da IA",
                }
            ],
        }

        plan = interpreter._safe_dashboard_plan(json.dumps(output), schema)
        chart = plan["charts"][0]

        self.assertEqual(chart["operation"], "groupby")
        self.assertEqual(chart["group_by"], ["Categoria"])
        self.assertEqual(chart["metric"], ["Valor"])
        self.assertEqual(chart["x"], "Categoria")
        self.assertEqual(chart["y"], "Valor")
        self.assertIn("Valor", chart["title"])
        self.assertIn("Categoria", chart["title"])


if __name__ == "__main__":
    unittest.main()
