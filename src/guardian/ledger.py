"""Acesso ao Ledger do W01 (Postgres `dataops`) — ler dados e gravar health scores.

LER via SQL direto (determinístico, sem LLM). ESCREVER via ALTER/UPDATE: o W01 não
tem API de escrita, então esta é a parte aditiva do W02.
"""

from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row

from . import config

QUALITY_COLUMNS_DDL = """
ALTER TABLE customers
    ADD COLUMN IF NOT EXISTS health_score NUMERIC(4,3),
    ADD COLUMN IF NOT EXISTS quality_flag VARCHAR(10),
    ADD COLUMN IF NOT EXISTS checked_at   TIMESTAMP
"""

EXPECTED_COLUMNS = {"id", "name", "email", "plan", "company", "created_at"}


@contextmanager
def connect() -> Iterator[psycopg.Connection]:
    """Abre uma conexão autocommit com o Ledger (linhas como dict)."""
    with psycopg.connect(config.PG_CONNINFO, row_factory=dict_row, autocommit=True) as conn:
        yield conn


def ensure_quality_columns() -> None:
    """Garante as colunas health_score/quality_flag/checked_at em customers (idempotente)."""
    with connect() as conn:
        conn.execute(QUALITY_COLUMNS_DDL)


def get_columns(table: str) -> set[str]:
    """Retorna o conjunto de colunas de `table` (via information_schema)."""
    with connect() as conn:
        rows = conn.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = %s",
            (table,),
        ).fetchall()
    return {r["column_name"] for r in rows}


def read_customers(limit: int | None = None) -> list[dict]:
    """Lê os `limit` customers mais recentes (janela, default config.WINDOW) com agregados de orders.

    Cada linha traz os campos do customer + `n_orders`, `total_amount` e `failed_orders`.
    """
    sql = """
        SELECT c.id, c.name, c.email, c.plan, c.company, c.created_at,
               COUNT(o.id)                                     AS n_orders,
               COALESCE(SUM(o.amount), 0)                      AS total_amount,
               COALESCE(SUM((o.status = 'failed')::int), 0)    AS failed_orders
        FROM customers c
        LEFT JOIN orders o ON o.customer_id = c.id
        GROUP BY c.id
        ORDER BY c.id DESC
        LIMIT %s
    """
    with connect() as conn:
        return conn.execute(sql, (limit or config.WINDOW,)).fetchall()


def write_scores(scored: list[tuple[int, float, str]]) -> int:
    """Grava (id, health_score, quality_flag) em customers; retorna o nº de linhas atualizadas."""
    if not scored:
        return 0
    with connect() as conn, conn.cursor() as cur:
        cur.executemany(
            "UPDATE customers SET health_score = %s, quality_flag = %s, checked_at = NOW() "
            "WHERE id = %s",
            [(score, flag, cid) for cid, score, flag in scored],
        )
        return cur.rowcount


def count_by_flag() -> dict[str, int]:
    """Distribuição de quality_flag em customers (None = ainda não validado)."""
    with connect() as conn:
        rows = conn.execute(
            "SELECT quality_flag, COUNT(*) AS n FROM customers GROUP BY quality_flag"
        ).fetchall()
    return {r["quality_flag"] or "unchecked": r["n"] for r in rows}
