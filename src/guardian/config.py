"""Configuração do Quality Guardian — tudo via env var, com defaults do setup local.

Carrega o `.env` no import: como este módulo é importado por todos os entrypoints
(CLI, Chainlit, MCP, testes), a `ANTHROPIC_API_KEY` do `.env` chega a todos eles.
"""

import os

try:
    from dotenv import load_dotenv

    load_dotenv()
except ModuleNotFoundError:  # python-dotenv ausente: segue só com o ambiente do processo
    pass

# --- Ledger do W01 (Postgres no host :5442) ---
PG_HOST = os.getenv("GUARDIAN_PG_HOST", "localhost")
PG_PORT = int(os.getenv("GUARDIAN_PG_PORT", "5442"))
PG_DB = os.getenv("GUARDIAN_PG_DB", "dataops")
PG_USER = os.getenv("GUARDIAN_PG_USER", "dataops")
PG_PASSWORD = os.getenv("GUARDIAN_PG_PASSWORD", "dataops123")
PG_CONNINFO = (
    f"postgresql://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DB}?sslmode=disable"
)

# --- Modelos (nunca hardcodar no código: sempre via env) ---
LLM_MODEL = os.getenv("GUARDIAN_LLM_MODEL", "anthropic:claude-sonnet-4-6")
# Evaluator-optimizer (prompt 05): gerador fraco propõe, avaliador forte julga.
GENERATOR_MODEL = os.getenv("GUARDIAN_GENERATOR_MODEL", "anthropic:claude-haiku-4-5")
EVALUATOR_MODEL = os.getenv("GUARDIAN_EVALUATOR_MODEL", "anthropic:claude-sonnet-4-6")

# --- Janela: valida só os N registros mais recentes (id DESC) ---
WINDOW = int(os.getenv("GUARDIAN_WINDOW", "50"))

# --- Controle do grafo ---
MAX_RETRIES = 2
RECURSION_LIMIT = 25

# --- Limiares de health score ---
GREEN_AT = 0.8
YELLOW_AT = 0.5
