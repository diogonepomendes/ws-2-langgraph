"""GuardianState — a memória de trabalho do grafo.

Cada nó lê o state e devolve uma atualização PARCIAL. Campos com
`Annotated[tipo, reducer]` são fundidos pelo reducer (`add_messages` faz append
inteligente); campos sem reducer são simplesmente sobrescritos.
"""

from typing import Annotated, Literal, Optional, TypedDict

from langchain.messages import AnyMessage
from langgraph.graph.message import add_messages

Flag = Literal["green", "yellow", "red"]


class GuardianState(TypedDict):
    """Estado do Quality Guardian ao longo de uma validação."""

    # Canal de conversa (reducer: append)
    messages: Annotated[list[AnyMessage], add_messages]

    # Alvo
    dataset: str

    # Resultado da validação
    schema_ok: Optional[bool]
    rows_checked: Optional[int]
    rule_violations: Optional[list[str]]
    n_red: Optional[int]  # registros individuais RED — disparam o HITL
    n_yellow: Optional[int]
    health_score: Optional[float]
    quality_flag: Optional[Flag]
    recommendation: Optional[str]

    # Caronas internas
    _scored: Optional[list]  # [(id, score, flag)] p/ o write_ledger
    _rows: Optional[list]  # rows brutos p/ o optimize

    # Evaluator-optimizer (prompt 05)
    hardening: int  # nº de rejeições do evaluator
    proposed_fixes: Optional[list]  # [(id, patch)] do gerador
    eval_feedback: Optional[str]  # motivo da rejeição -> volta p/ o gerador
    eval_accepted: Optional[bool]
    corrected_rows: Optional[list]  # rows corrigidos in-state p/ re-pontuar

    # Controle de fluxo
    retries: int
    needs_human: bool
    human_decision: Optional[str]
    written: Optional[bool]


def initial_state(dataset: str = "customers") -> GuardianState:
    """Retorna um GuardianState zerado para validar `dataset`."""
    return GuardianState(
        messages=[],
        dataset=dataset,
        schema_ok=None,
        rows_checked=None,
        rule_violations=None,
        n_red=None,
        n_yellow=None,
        health_score=None,
        quality_flag=None,
        recommendation=None,
        _scored=None,
        _rows=None,
        hardening=0,
        proposed_fixes=None,
        eval_feedback=None,
        eval_accepted=None,
        corrected_rows=None,
        retries=0,
        needs_human=False,
        human_decision=None,
        written=None,
    )
