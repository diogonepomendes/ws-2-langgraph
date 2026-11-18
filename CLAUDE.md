# CLAUDE.md — Quality Guardian Agent (W02)

> Contrato entre desenvolvedor e Claude Code para este projeto. Plano completo em `sketch/plan.md`.

## 1. Project Overview

O **Quality Guardian** é um agente **stateful** em LangGraph que consome o catálogo do W01
(DataOps Knowledge Hub, já rodando), valida a qualidade de cada dataset percorrendo um grafo de
estados, e **grava `health_score` / `quality_flag` de volta no Ledger** (Postgres do W01). Um
`quality_flag = "red"` no Ledger é o trigger da Crew do W03.

**Conceito central:** uma **máquina de estados explícita** (LangGraph) — nós, arestas
condicionais, ciclos de auto-correção, checkpointing e human-in-the-loop — em vez de um agente
ReAct caixa-preta.

```
START → check_schema → validate_rules → score → decide
                            ▲                       ├── red    → human_gate (interrupt) → write_ledger → END
                            └── bump_retry ◄── yellow├── yellow → loop (auto-correção, até MAX_RETRIES)
                                                     └── green  → write_ledger → END
```

**Entrega final:** o agente exposto como **servidor MCP** (FastMCP) e **UI Chainlit**,
consumível em linguagem natural.

## 2. Tech Stack

Versões pinadas em `requirements.txt` (fonte da verdade).

| Componente | Tecnologia |
|---|---|
| Grafo / estado | LangGraph 1.2 |
| Modelo, tools, mensagens | LangChain 1.3 + langchain-anthropic (Claude) |
| Checkpointing | langgraph-checkpoint-sqlite / langgraph-checkpoint-postgres |
| Acesso ao Ledger | psycopg 3 |
| Consumir o MCP do W01 (opcional) | langchain-mcp-adapters |
| Expor o agente | mcp (FastMCP) |
| UI | Chainlit 2.11 |
| Runtime | Python 3.11–3.13 (chainlit 2.11.1 não instala em 3.14) — venv em `.venv/` |

## 3. Architecture Rules (não-negociáveis)

- **O grafo é uma máquina de estados explícita: construir o `StateGraph` à mão.**
  **NÃO usar `create_react_agent`** — o objetivo didático é VER os nós e as arestas.
- Todo nó é uma função `(state) -> dict` que retorna **atualização PARCIAL** do state
  (nunca o state inteiro, nunca mutar o state recebido).
- Loops **SEMPRE** têm contador de parada no state (ex.: `retries` vs `MAX_RETRIES`) para nunca
  cair em `GraphRecursionError`.
- Human-in-the-loop com **`interrupt()` + `Command(resume=...)`**. NÃO usar
  `interrupt_before`/`interrupt_after` no `compile()` (API antiga, hoje só para debug).
- HITL dispara se houver **qualquer** registro RED (não só pela média do dataset).
- **LER** dados factuais via SQL direto no Postgres do W01.
- **ESCREVER** `health_score` / `quality_flag` via SQL (`ALTER TABLE ... ADD COLUMN` + `UPDATE`) —
  o W01 não tem API de escrita.
- Grafos que usam `interrupt()` precisam de checkpointer no `compile()` e de `thread_id` no config.

## 4. Code Standards

- Type hints e docstrings em todas as funções públicas.
- Layout `src/`: o pacote é `src/guardian/`. Testes em `tests/` (pytest).
- Segredos e configuração em `.env` (carregado com `python-dotenv`); ver `.env.example`.
- Imports do namespace novo do LangChain 1.x — **não** `langchain_core.*`:
  ```python
  from langchain.chat_models import init_chat_model
  from langchain.tools import tool
  from langchain.messages import HumanMessage, AIMessage, SystemMessage
  ```

## 5. Connection to W01

- Ledger = Postgres `dataops` em **`localhost:5442`** (porta remapeada para não conflitar com
  outros Postgres locais).
- Conexão: `postgresql://dataops:dataops123@localhost:5442/dataops`
  (montada a partir de `GUARDIAN_PG_HOST/PORT/DB/USER/PASSWORD` no `.env`).
- Tabelas:
  - `customers(id, name, email, plan, company, created_at)`
  - `orders(..., status, amount)`
  - `products(...)`
- Colunas adicionadas pelo W02: `health_score`, `quality_flag` (e afins) — ficam visíveis ao
  text-to-SQL do W01.
- Subir/restaurar o W01: `scripts/bootstrap-w01.sh`, `scripts/restore.sh`.

## 6. Constraints (proibições)

- ❌ **NÃO** reconstruir o W01 (RAG/MCP do Luan) — ele já existe e roda em `w01-rag/`.
- ❌ **NÃO** usar `create_react_agent` no fluxo principal — queremos a máquina de estados explícita.
- ❌ **NÃO** hardcodar nomes de modelo — ler de env var (`GUARDIAN_LLM_MODEL`,
  `GUARDIAN_GENERATOR_MODEL`, `GUARDIAN_EVALUATOR_MODEL`).
- ❌ **NÃO** commitar segredos — `.env` é git-ignored; só `.env.example` vai para o repositório.
