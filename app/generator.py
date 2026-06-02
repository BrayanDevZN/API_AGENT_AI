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
        question: str | None,
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
        question: str | None,
        chart: dict | None,
        messages: list[dict] | None = None,
        interpretation: dict | None = None
    ) -> str:
        messages = messages or []
        question = self._normalize_user_prompt(question)

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
        question: str | None,
        charts: list[dict],
        messages: list[dict] | None = None,
        interpretation: dict | None = None
    ) -> str:
        messages = messages or []
        question = self._normalize_user_prompt(question)

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
        prompt: str | None,
        plan: dict,
        metrics: list[dict],
        schema: dict
    ) -> str:
        user_prompt = self._normalize_user_prompt(prompt)

        if user_prompt:
            final_prompt = self._dashboard_specific_prompt(
                user_prompt=user_prompt,
                plan=plan,
                metrics=metrics,
                schema=schema
            )
        else:
            final_prompt = self._dashboard_general_prompt(
                plan=plan,
                metrics=metrics,
                schema=schema
            )

        response = self.client.responses.create(
            model=self.model,
            input=final_prompt
        )

        return response.output_text

    def dashboard_analysis_multi(
        self,
        prompt: str | None,
        charts: list[dict],
        schema: dict,
        plan: dict | None = None
    ) -> str:
        plan = plan or {}
        user_prompt = self._normalize_user_prompt(prompt)

        if user_prompt:
            final_prompt = self._dashboard_multi_specific_prompt(
                user_prompt=user_prompt,
                charts=charts,
                schema=schema,
                plan=plan
            )
        else:
            final_prompt = self._dashboard_multi_general_prompt(
                charts=charts,
                schema=schema,
                plan=plan
            )

        response = self.client.responses.create(
            model=self.model,
            input=final_prompt
        )

        return response.output_text

    def _normalize_user_prompt(self, prompt: str | None) -> str | None:
        if not prompt:
            return None

        clean_prompt = str(prompt).strip()

        if not clean_prompt:
            return None

        empty_like_prompts = {
            "analise",
            "análise",
            "analise geral",
            "análise geral",
            "dashboard",
            "gerar dashboard",
            "crie um dashboard",
            "criar dashboard",
        }

        if clean_prompt.lower() in empty_like_prompts:
            return None

        return clean_prompt

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

    def _base_rules(self) -> str:
        return """
REGRAS OBRIGATÓRIAS:
- Responda em português.
- Use apenas os dados fornecidos.
- Não invente dados, colunas, métricas, percentuais ou causas.
- Não recalcule métricas além do que já foi fornecido.
- Não afirme causalidade como certeza. Quando falar de causa, use linguagem de hipótese.
- Se os dados forem insuficientes, diga claramente o que falta.
- Não use JSON.
- Não use markdown pesado.
- Use títulos simples com markdown leve.
- Seja analítico, não apenas descritivo.
- Sempre conecte números com impacto de negócio.
- Evite repetir todos os valores sem necessidade.
- Priorize o que ajuda alguém a tomar decisão.
"""

    def _report_quality_rules(self) -> str:
        return """
COMO UMA BOA ANÁLISE DEVE FUNCIONAR:
- Comece pelo que mais importa.
- Destaque os maiores valores, menores valores e concentrações.
- Compare categorias, períodos ou métricas quando os dados permitirem.
- Identifique padrões, tendências, outliers, gargalos e oportunidades.
- Explique a evidência usada para cada conclusão.
- Transforme achados em recomendações práticas.
- Se houver gráfico temporal, comente evolução, queda, pico ou estabilidade.
- Se houver gráfico de ranking, comente liderança, cauda longa e concentração.
- Se houver KPI, explique o que o número indica no contexto.
- Se houver dispersão, comente relação entre variáveis apenas como associação, não causa.
"""

    def _general_report_structure(self) -> str:
        return """
ESTRUTURA OBRIGATÓRIA DA RESPOSTA:

## Resumo executivo
Explique em 3 a 6 linhas o cenário geral encontrado nos dados.

## Indicadores principais
Liste os KPIs e métricas mais importantes encontrados nos gráficos.
Explique rapidamente o que cada indicador representa.

## Principais descobertas
Mostre os padrões mais relevantes, rankings, concentrações, diferenças entre categorias e pontos fortes.

## Tendências e comportamento
Analise evolução temporal se houver dados de tempo.
Se não houver dados temporais, diga que não foi possível avaliar tendência.

## Alertas e oportunidades
Aponte riscos, gargalos, quedas, concentração excessiva, baixo desempenho ou oportunidades de melhoria.

## Recomendações estratégicas
Dê ações práticas com base nos dados.
Cada recomendação precisa estar conectada a uma evidência.

## Próximos passos
Diga quais análises complementares ou dados extras ajudariam a melhorar a decisão.
"""

    def _specific_report_structure(self) -> str:
        return """
ESTRUTURA OBRIGATÓRIA DA RESPOSTA:

## Resposta direta ao pedido
Responda primeiro exatamente o que o usuário pediu.

## Evidências encontradas
Mostre quais gráficos, métricas ou valores sustentam a resposta.

## Principais descobertas
Liste os achados mais relevantes relacionados ao pedido.

## Alertas e limitações
Explique riscos, pontos de atenção e limites dos dados.

## Recomendações práticas
Dê ações objetivas com base no pedido do usuário.

## Próximos passos
Indique o que analisar depois para aprofundar a decisão.
"""

    def _dashboard_general_prompt(
        self,
        plan: dict,
        metrics: list[dict],
        schema: dict
    ) -> str:
        return f"""
Você é o DataPilot AI, uma IA especialista em análise de dados, dashboards e Business Intelligence.

O usuário NÃO informou um pedido específico.
Portanto, faça uma ANÁLISE GERAL COMPLETA do dataset com base nos gráficos e métricas já processados.

{self._base_rules()}

{self._report_quality_rules()}

{self._general_report_structure()}

Plano usado:
{json.dumps(plan, ensure_ascii=False)}

Schema do dataset:
{json.dumps(schema, ensure_ascii=False)}

Gráficos e métricas calculadas:
{json.dumps(metrics, ensure_ascii=False)}

Resposta:
"""

    def _dashboard_specific_prompt(
        self,
        user_prompt: str,
        plan: dict,
        metrics: list[dict],
        schema: dict
    ) -> str:
        return f"""
Você é o DataPilot AI, uma IA especialista em análise de dados, dashboards e Business Intelligence.

O usuário informou um pedido específico.
Sua prioridade é responder esse pedido, usando somente os gráficos e métricas fornecidos.

{self._base_rules()}

{self._report_quality_rules()}

{self._specific_report_structure()}

PEDIDO ESPECÍFICO DO USUÁRIO:
{user_prompt}

Plano usado:
{json.dumps(plan, ensure_ascii=False)}

Schema do dataset:
{json.dumps(schema, ensure_ascii=False)}

Gráficos e métricas calculadas:
{json.dumps(metrics, ensure_ascii=False)}

Resposta:
"""

    def _dashboard_multi_general_prompt(
        self,
        charts: list[dict],
        schema: dict,
        plan: dict
    ) -> str:
        return f"""
Você é o DataPilot AI, uma IA especialista em análise de dados, dashboards, BI e geração de insights.

O usuário NÃO informou um pedido específico.
Você recebeu vários gráficos já processados.
Sua função é gerar uma ANÁLISE GERAL ROBUSTA conectando todos os gráficos.

{self._base_rules()}

{self._report_quality_rules()}

REGRAS PARA MÚLTIPLOS GRÁFICOS:
- Não analise cada gráfico como uma ilha.
- Conecte os achados entre os gráficos.
- Identifique se uma métrica reforça ou contradiz outra.
- Priorize os achados mais relevantes para decisão.
- Não transforme a resposta em uma lista mecânica de gráficos.

{self._general_report_structure()}

Plano utilizado:
{json.dumps(plan, ensure_ascii=False)}

Schema:
{json.dumps(schema, ensure_ascii=False)}

Gráficos:
{json.dumps(charts, ensure_ascii=False)}

Resposta:
"""

    def _dashboard_multi_specific_prompt(
        self,
        user_prompt: str,
        charts: list[dict],
        schema: dict,
        plan: dict
    ) -> str:
        return f"""
Você é o DataPilot AI, uma IA especialista em análise de dados, dashboards, BI e geração de insights.

O usuário informou um pedido específico.
Você recebeu vários gráficos já processados.
Sua função é responder o pedido do usuário conectando os gráficos disponíveis.

{self._base_rules()}

{self._report_quality_rules()}

REGRAS PARA MÚLTIPLOS GRÁFICOS:
- Responda primeiro ao objetivo do usuário.
- Use os gráficos como evidência.
- Conecte os achados entre gráficos quando fizer sentido.
- Não analise cada gráfico isoladamente sem explicar o impacto.
- Se os gráficos não responderem completamente ao pedido, diga o que falta.

{self._specific_report_structure()}

PEDIDO ESPECÍFICO DO USUÁRIO:
{user_prompt}

Plano utilizado:
{json.dumps(plan, ensure_ascii=False)}

Schema:
{json.dumps(schema, ensure_ascii=False)}

Gráficos:
{json.dumps(charts, ensure_ascii=False)}

Resposta:
"""

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
        question: str | None,
        chart: dict | None,
        messages: list[dict],
        interpretation: dict | None
    ) -> str:
        history = self._format_history(messages)

        if question:
            structure = self._specific_report_structure()
            objective = f"PERGUNTA DO USUÁRIO:\n{question}"
            mode_instruction = "O usuário fez um pedido específico. Responda esse pedido antes de qualquer análise geral."
        else:
            structure = self._general_report_structure()
            objective = "PERGUNTA DO USUÁRIO:\nNenhum pedido específico informado. Faça uma análise geral."
            mode_instruction = "O usuário não fez pedido específico. Faça uma análise geral executiva."

        return f"""
Você é o DataPilot AI, uma IA especialista em análise de dados, geração de insights e recomendação estratégica.

Neste endpoint, você está em modo ANÁLISE/DASHBOARD.
Você deve analisar apenas os dados fornecidos pela aplicação.

{mode_instruction}

{self._base_rules()}

{self._report_quality_rules()}

{structure}

HISTÓRICO DA CONVERSA:
{history}

{objective}

INTERPRETAÇÃO USADA:
{json.dumps(interpretation, ensure_ascii=False)}

DADOS/GRÁFICO ANALISADO:
{json.dumps(chart, ensure_ascii=False)}

Resposta:
"""

    def _analysis_multi_prompt(
        self,
        question: str | None,
        charts: list[dict],
        messages: list[dict],
        interpretation: dict | None
    ) -> str:
        history = self._format_history(messages)

        if question:
            structure = self._specific_report_structure()
            objective = f"PERGUNTA DO USUÁRIO:\n{question}"
            mode_instruction = "O usuário fez um pedido específico. Responda esse pedido primeiro."
        else:
            structure = self._general_report_structure()
            objective = "PERGUNTA DO USUÁRIO:\nNenhum pedido específico informado. Faça uma análise geral."
            mode_instruction = "O usuário não fez pedido específico. Faça uma análise geral robusta conectando os gráficos."

        return f"""
Você é o DataPilot AI, uma IA especialista em análise de dados, dashboards, BI e geração de insights.

Neste endpoint, você está em modo ANÁLISE COM MÚLTIPLOS GRÁFICOS.
Você deve analisar todos os gráficos fornecidos pela aplicação.

{mode_instruction}

{self._base_rules()}

{self._report_quality_rules()}

REGRAS PARA MÚLTIPLOS GRÁFICOS:
- Não analise cada gráfico como uma ilha.
- Faça conexões entre os gráficos quando fizer sentido.
- Priorize padrões que ajudem a tomar decisão.
- Se os gráficos não forem suficientes para responder algo, diga claramente.

{structure}

HISTÓRICO DA CONVERSA:
{history}

{objective}

INTERPRETAÇÃO USADA:
{json.dumps(interpretation, ensure_ascii=False)}

GRÁFICOS ANALISADOS:
{json.dumps(charts, ensure_ascii=False)}

Resposta:
"""
