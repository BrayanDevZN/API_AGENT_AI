import json
from openai import OpenAI
from core.config import Settings


class Generator:
    def __init__(self):
        self.client = OpenAI(api_key=Settings.OPENAI_API_KEY)
        self.model = Settings.OPENAI_MODEL

    def chat(self, question: str, messages: list[dict] | None = None) -> str:
        messages = messages or []

        prompt = self._chat_prompt(
            question=question,
            messages=messages
        )

        response = self.client.responses.create(
            model=self.model,
            input=prompt
        )

        return response.output_text

    def run(
        self,
        question: str,
        chart: dict | None = None,
        charts: list[dict] | None = None,
        messages: list[dict] | None = None,
        interpretation: dict | None = None
    ) -> str:
        if charts:
            return self.analysis_multi(
                question=question,
                charts=charts,
                messages=messages,
                interpretation=interpretation
            )

        return self.analysis(
            question=question,
            chart=chart,
            messages=messages,
            interpretation=interpretation
        )

    def analysis(
        self,
        question: str,
        chart: dict | None,
        messages: list[dict] | None = None,
        interpretation: dict | None = None
    ) -> str:
        messages = messages or []

        prompt = self._analysis_prompt(
            question=question,
            chart=chart,
            messages=messages,
            interpretation=interpretation
        )

        response = self.client.responses.create(
            model=self.model,
            input=prompt
        )

        return response.output_text

    def analysis_multi(
        self,
        question: str,
        charts: list[dict],
        messages: list[dict] | None = None,
        interpretation: dict | None = None
    ) -> str:
        messages = messages or []

        prompt = self._analysis_multi_prompt(
            question=question,
            charts=charts,
            messages=messages,
            interpretation=interpretation
        )

        response = self.client.responses.create(
            model=self.model,
            input=prompt
        )

        return response.output_text

    def dashboard_analysis(
        self,
        prompt: str,
        plan: dict,
        metrics: list[dict],
        schema: dict
    ) -> str:
        final_prompt = f"""
Você é o DataPilot AI, uma IA especialista em análise de dados, dashboards e Business Intelligence.

Você receberá UM OU MAIS gráficos já processados pelo pandas.

Sua função é analisar todos os gráficos em conjunto.

REGRAS OBRIGATÓRIAS:
- Responda em português.
- Use apenas os dados fornecidos.
- Não invente dados.
- Não invente colunas.
- Não recalcule métricas.
- Não trate hipóteses como certeza.
- Se os dados forem insuficientes, diga claramente.
- Não use JSON.
- Não use markdown pesado.
- Foque em insights, padrões e recomendações.

O QUE ANALISAR:
- maiores valores
- menores valores
- concentração
- ranking
- tendência
- distribuição
- possíveis anomalias
- relação entre gráficos
- riscos
- oportunidades

ESTRUTURA DA RESPOSTA:
Resumo executivo

Principais descobertas

Padrões encontrados

Riscos e oportunidades

Recomendações

Próximos passos

Pedido do usuário:
{prompt}

Plano usado:
{json.dumps(plan, ensure_ascii=False)}

Schema do dataset:
{json.dumps(schema, ensure_ascii=False)}

Gráficos e métricas calculadas:
{json.dumps(metrics, ensure_ascii=False)}

Resposta:
"""

        response = self.client.responses.create(
            model=self.model,
            input=final_prompt
        )

        return response.output_text

    def dashboard_analysis_multi(
        self,
        prompt: str,
        charts: list[dict],
        schema: dict,
        plan: dict | None = None
    ) -> str:
        plan = plan or {}

        final_prompt = f"""
Você é o DataPilot AI, uma IA especialista em análise de dados, dashboards e Business Intelligence.

Você recebeu vários gráficos já processados.
Cada gráfico contém título, tipo, operação, configuração e dados calculados.

Sua função é gerar UMA análise geral sobre todos os gráficos.

REGRAS OBRIGATÓRIAS:
- Responda em português.
- Use apenas os dados fornecidos.
- Não invente dados.
- Não invente colunas.
- Não recalcule métricas.
- Não afirme causas como certeza.
- Quando falar de causa, use linguagem de hipótese.
- Se os dados forem insuficientes, diga isso claramente.
- Não use JSON.
- Não use markdown pesado.
- Não analise cada gráfico isoladamente sem conectar os pontos.
- Faça conexões entre os gráficos quando fizer sentido.

FOQUE EM:
- resumo geral do cenário
- principais padrões
- comparações entre gráficos
- concentração de resultados
- tendência temporal, se existir gráfico de tempo
- oportunidades
- riscos
- recomendações práticas

ESTRUTURA DA RESPOSTA:
Resumo executivo

Principais descobertas

Relação entre os gráficos

Riscos e oportunidades

Recomendações práticas

Próximos passos

Pedido do usuário:
{prompt}

Plano utilizado:
{json.dumps(plan, ensure_ascii=False)}

Schema:
{json.dumps(schema, ensure_ascii=False)}

Gráficos:
{json.dumps(charts, ensure_ascii=False)}

Resposta:
"""

        response = self.client.responses.create(
            model=self.model,
            input=final_prompt
        )

        return response.output_text

    def _format_history(self, messages: list[dict], limit: int = 12) -> str:
        if not messages:
            return "Sem histórico anterior."

        formatted = []

        for message in messages[-limit:]:
            role = message.get("role", "")
            content = message.get("content", "")

            if not content:
                continue

            if role == "user":
                role_name = "Usuário"
            elif role == "assistant":
                role_name = "Assistente"
            else:
                role_name = role or "Mensagem"

            formatted.append(f"{role_name}: {content}")

        return "\n".join(formatted) if formatted else "Sem histórico anterior."

    def _chat_prompt(
        self,
        question: str,
        messages: list[dict]
    ) -> str:
        history = self._format_history(messages)

        return f"""
Você é o DataPilot AI, um assistente inteligente dentro de uma plataforma de análise de dados.

Neste endpoint, você está em modo CHAT NORMAL.
O usuário NÃO enviou arquivo e você NÃO deve tentar gerar gráfico.

Sua função aqui é conversar, explicar conceitos, ajudar com dúvidas e usar o histórico da conversa quando ele for relevante.

REGRAS:
- Responda em português.
- Seja claro, útil e direto.
- Use o histórico apenas quando ele ajudar na resposta.
- Não invente dados.
- Não diga que analisou arquivo, dataset ou dashboard.
- Não gere JSON.
- Não use markdown pesado.
- Se o usuário pedir gráfico, dashboard ou análise de arquivo, explique que ele deve usar a área de dashboards/análise.
- Se o usuário perguntar algo sobre mensagens anteriores, use o histórico abaixo.
- Se o histórico não tiver a informação, diga que não encontrou essa informação na conversa.

HISTÓRICO DA CONVERSA:
{history}

PERGUNTA ATUAL:
{question}

Resposta:
"""

    def _analysis_prompt(
        self,
        question: str,
        chart: dict | None,
        messages: list[dict],
        interpretation: dict | None
    ) -> str:
        history = self._format_history(messages)

        return f"""
Você é o DataPilot AI, uma IA especialista em análise de dados, geração de insights e recomendação estratégica.

Neste endpoint, você está em modo ANÁLISE/DASHBOARD.
Você deve analisar apenas os dados fornecidos pela aplicação.

REGRAS OBRIGATÓRIAS:
- Responda em português.
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
- Não use JSON.
- Não use markdown pesado.

ESTRUTURA:
1. Resumo geral
2. Principais descobertas
3. Possíveis causas
4. Soluções recomendadas
5. Próximos passos

HISTÓRICO DA CONVERSA:
{history}

PERGUNTA DO USUÁRIO:
{question}

INTERPRETAÇÃO USADA:
{json.dumps(interpretation, ensure_ascii=False)}

DADOS/GRÁFICO ANALISADO:
{json.dumps(chart, ensure_ascii=False)}

Resposta:
"""

    def _analysis_multi_prompt(
        self,
        question: str,
        charts: list[dict],
        messages: list[dict],
        interpretation: dict | None
    ) -> str:
        history = self._format_history(messages)

        return f"""
Você é o DataPilot AI, uma IA especialista em análise de dados, dashboards, BI e geração de insights.

Neste endpoint, você está em modo ANÁLISE COM MÚLTIPLOS GRÁFICOS.
Você deve analisar todos os gráficos fornecidos pela aplicação.

REGRAS OBRIGATÓRIAS:
- Responda em português.
- Use apenas os dados fornecidos.
- Não invente dados.
- Não invente colunas.
- Não recalcule métricas.
- Não invente causas como certeza.
- Quando falar de causa, trate como hipótese.
- Se os dados forem insuficientes, diga isso claramente.
- Não use JSON.
- Não use markdown pesado.
- Faça conexões entre os gráficos quando fizer sentido.
- Não repita todos os números sem necessidade.
- Foque em padrões e decisões.

ESTRUTURA:
1. Resumo geral
2. Principais descobertas
3. Relação entre os gráficos
4. Riscos e oportunidades
5. Recomendações práticas
6. Próximos passos

HISTÓRICO DA CONVERSA:
{history}

PERGUNTA DO USUÁRIO:
{question}

INTERPRETAÇÃO USADA:
{json.dumps(interpretation, ensure_ascii=False)}

GRÁFICOS ANALISADOS:
{json.dumps(charts, ensure_ascii=False)}

Resposta:
"""