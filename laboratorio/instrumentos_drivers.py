"""Drivers ASTM por analizador (mapeo de mensajes, no de códigos de catálogo)."""
from __future__ import annotations

from laboratorio.instrumentos_astm import (
    ResultadoAstm,
    build_worklist_message,
    parse_resultados,
    sample_id_from_query,
    split_records,
)
from laboratorio.instrumentos_service import IngestaItem, WorklistResult


def parse_query_sample_id(message: str) -> str:
    return sample_id_from_query(split_records(message))


def parse_ingesta_message(message: str) -> tuple[str, list[IngestaItem]]:
    sample_id, rows = parse_resultados(split_records(message))
    items = [IngestaItem(codigo_instrumento=r.codigo, valor=r.valor, unidad=r.unidad) for r in rows]
    return sample_id, items


def worklist_to_astm(wl: WorklistResult, *, sender: str = "SYNESIS") -> str:
    sid = ""
    if wl.muestra is not None:
        sid = (wl.muestra.codigo_instrumento or wl.muestra.codigo_barra or wl.sample_id)
    else:
        sid = wl.sample_id
    codes = [a.codigo_instrumento for a in wl.analitos]
    return build_worklist_message(
        sample_id=sid,
        apellido=wl.paciente_apellido,
        nombre=wl.paciente_nombre,
        dni=wl.paciente_dni,
        test_codes=codes,
        sender=sender,
    )


def is_query_message(message: str) -> bool:
    return any(rec and rec[0][:1].upper() == "Q" for rec in split_records(message))


def is_result_message(message: str) -> bool:
    return any(rec and rec[0][:1].upper() == "R" for rec in split_records(message))


# Compat: los drivers no cambian el codec; el mapeo de analito vive en BD.
CM260_SENDER = "CM260"
SYSMEX_SENDER = "XP300"


def sender_for_driver(driver: str) -> str:
    if driver == "SYSMEX_XP300":
        return SYSMEX_SENDER
    if driver == "CM260":
        return CM260_SENDER
    return "SYNESIS"


__all__ = [
    "ResultadoAstm",
    "parse_query_sample_id",
    "parse_ingesta_message",
    "worklist_to_astm",
    "is_query_message",
    "is_result_message",
    "sender_for_driver",
]
