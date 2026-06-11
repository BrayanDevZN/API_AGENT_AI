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

    def test_deduplicates_repeated_dimension_and_friendly_titles(self):
        interpreter = self.make_interpreter()
        schema = {
            "columns": [
                {"name": "Status", "dtype": "String"},
                {"name": "Nota_Entrevista", "dtype": "Float64"},
                {"name": "Pretensao_Salarial", "dtype": "Float64"},
            ],
            "numeric_columns": ["Nota_Entrevista", "Pretensao_Salarial"],
            "categorical_columns": ["Status"],
            "date_columns": [],
        }
        output = {
            "tool": "dashboard_plan",
            "dataset_type": "rh",
            "analysis_type": "general",
            "business_context": "RH",
            "priority_metrics": ["Nota_Entrevista", "Pretensao_Salarial"],
            "rename_columns": {},
            "charts": [
                {
                    "title": "Quantidade por Status",
                    "operation": "count",
                    "chart_type": "bar",
                    "group_by": ["Status"],
                    "metric": [],
                    "aggregation": ["count"],
                    "x": "Status",
                    "y": "Quantidade",
                    "time_column": None,
                    "time_freq": "M",
                    "drill_down_hierarchy": [],
                    "filters": [],
                    "limit": 10,
                    "sort": "desc",
                    "reason": "Contagem por status",
                },
                {
                    "title": "Total de Nota_Entrevista por Status",
                    "operation": "groupby",
                    "chart_type": "horizontal_bar",
                    "group_by": ["Status"],
                    "metric": ["Nota_Entrevista"],
                    "aggregation": ["mean"],
                    "x": "Status",
                    "y": "Nota_Entrevista",
                    "time_column": None,
                    "time_freq": "M",
                    "drill_down_hierarchy": [],
                    "filters": [],
                    "limit": 10,
                    "sort": "desc",
                    "reason": "Nota por status",
                },
                {
                    "title": "Total de Pretensao_Salarial por Status",
                    "operation": "groupby",
                    "chart_type": "bar",
                    "group_by": ["Status"],
                    "metric": ["Pretensao_Salarial"],
                    "aggregation": ["sum"],
                    "x": "Status",
                    "y": "Pretensao_Salarial",
                    "time_column": None,
                    "time_freq": "M",
                    "drill_down_hierarchy": [],
                    "filters": [],
                    "limit": 10,
                    "sort": "desc",
                    "reason": "Pretensao por status",
                },
            ],
        }

        plan = interpreter._safe_dashboard_plan(json.dumps(output), schema)

        self.assertEqual(len(plan["charts"]), 1)
        self.assertEqual(plan["charts"][0]["metric"], ["Nota_Entrevista"])
        self.assertEqual(plan["charts"][0]["title"], "Media de Nota Entrevista por Status")
        self.assertEqual(plan["rename_columns"]["Nota_Entrevista"], "Nota Entrevista")
        self.assertEqual(plan["rename_columns"]["Pretensao_Salarial"], "Pretensao Salarial")


if __name__ == "__main__":
    unittest.main()
