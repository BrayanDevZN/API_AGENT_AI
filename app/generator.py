import json
from openai import OpenAI
from core.config import Settings


class Generator:
    def __init__(self):
        self.client = OpenAI(api_key=Settings.OPENAI_API_KEY)
        self.model = Settings.OPENAI_MODEL

    def run(
        self,
        question: str,
        chart: dict | None,
        messages: list,
        interpretation: dict | None
    ) -> str:

        has_data = (
            chart is not None
            and interpretation is not None
            and chart.get("type") != "none"
            and bool(chart.get("data"))
            and interpretation.get("mode") == "analysis"
        )

        if has_data:
            prompt = self._analysis_prompt(
                question=question,
                chart=chart,
                messages=messages,
                interpretation=interpretation
            )
        else:
            prompt = self._chat_prompt(
                question=question,
                messages=messages
            )

        response = self.client.responses.create(
            model=self.model,
            input=prompt
        )

        return response.output_text

    def _chat_prompt(
        self,
        question: str,
        messages: list
    ) -> str:
        return f"""
Você é um assistente útil, direto e inteligente.

Neste momento não existem dados enviados para análise.
Responda como conversa normal, sem tentar criar gráfico ou inventar informações.

REGRAS:
- Responda em português.
- Seja claro e objetivo.
- Não invente dados.
- Não invente colunas.
- Não finja que analisou um dataset.
- Se o usuário pediu análise, explique que precisa de um arquivo/dataset para analisar.
- Se a pergunta for comum, responda naturalmente.
- Não use JSON.
- Não use markdown pesado.

Pergunta:
{question}

Histórico:
{json.dumps(messages, ensure_ascii=False)}
"""

    def _analysis_prompt(
        self,
        question: str,
        chart: dict,
        messages: list,
        interpretation: dict
    ) -> str:
        return f"""
Você é uma IA especialista em análise de dados, diagnóstico de problemas e recomendação estratégica.

Sua função é analisar os dados fornecidos, explicar o que eles indicam e sugerir soluções práticas.

REGRAS OBRIGATÓRIAS:
- Use apenas os dados fornecidos.
- Não invente dados.
- Não invente colunas.
- Não invente causas como certeza.
- Quando falar de causa, trate como hipótese.
- Se os dados forem insuficientes, diga isso claramente.
- Explique os principais padrões encontrados.
- Aponte riscos, gargalos, quedas, concentrações ou oportunidades.
- Dê recomendações práticas e acionáveis.
- Se não houver base suficiente para uma solução definitiva, diga quais dados extras seriam necessários.
- Não diga que você gerou gráfico.
- Não diga que existe gráfico se os dados forem insuficientes.
- Não use JSON.
- Não use markdown pesado.
- Responda em português.

ESTRUTURA OBRIGATÓRIA:
1. Resumo geral
2. Principais descobertas
3. Possíveis causas
4. Soluções recomendadas
5. Próximos passos

COMO ANALISAR:
- Se houver concentração muito alta em uma categoria, destaque o risco.
- Se houver queda ou valor baixo, sugira investigação.
- Se houver ranking, compare os maiores e menores valores.
- Se houver evolução temporal, destaque tendência de crescimento, queda ou estabilidade.
- Se houver proporção, destaque concentração e distribuição.
- Se os dados forem poucos, avise que a conclusão é limitada.
- Se uma recomendação depender de contexto externo, apresente como hipótese.

Pergunta do usuário:
{question}

Histórico:
{json.dumps(messages, ensure_ascii=False)}

Interpretação usada:
{json.dumps(interpretation, ensure_ascii=False)}

Dados analisados:
{json.dumps(chart, ensure_ascii=False)}
"""