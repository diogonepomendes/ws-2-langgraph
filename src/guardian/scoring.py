"""Regras de qualidade — lógica pura (sem I/O, sem LLM), testável em isolamento.

O grafo chama isto no nó `score`.
"""

from .config import GREEN_AT, YELLOW_AT


def evaluate_row(row: dict) -> tuple[float, list[str]]:
    """Aplica as regras a um customer; retorna (health_score 0..1, violações)."""
    score = 1.0
    violations: list[str] = []

    email = row.get("email")
    if not email or "@" not in email:
        score -= 0.5
        violations.append("email inválido/ausente")

    if row.get("company") is None:
        score -= 0.15
        violations.append("company nula")

    n_orders = int(row.get("n_orders") or 0)
    failed = int(row.get("failed_orders") or 0)
    if n_orders > 0 and failed > 0:
        fail_ratio = failed / n_orders
        score -= min(0.4, fail_ratio)
        violations.append(f"{fail_ratio:.0%} dos pedidos falharam")

    return max(0.0, round(score, 3)), violations


def flag_for(score: float) -> str:
    """Converte um health score em flag: green / yellow / red."""
    if score >= GREEN_AT:
        return "green"
    if score >= YELLOW_AT:
        return "yellow"
    return "red"


def aggregate(rows: list[dict]) -> dict:
    """Pontua um conjunto de customers.

    Retorna `scored` [(id, score, flag)], `violations` (lista achatada),
    `dataset_health` (média, round 3), `dataset_flag`, `n_red` e `n_yellow`.
    """
    scored: list[tuple[int, float, str]] = []
    violations: list[str] = []
    for row in rows:
        score, row_violations = evaluate_row(row)
        scored.append((row["id"], score, flag_for(score)))
        violations.extend(row_violations)

    dataset_health = round(sum(s for _, s, _ in scored) / len(scored), 3) if scored else 0.0
    return {
        "scored": scored,
        "violations": violations,
        "dataset_health": dataset_health,
        "dataset_flag": flag_for(dataset_health),
        "n_red": sum(1 for *_, f in scored if f == "red"),
        "n_yellow": sum(1 for *_, f in scored if f == "yellow"),
    }
