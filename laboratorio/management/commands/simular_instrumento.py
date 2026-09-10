"""Simula query + resultados ASTM (TCP) o JSON contra servicios LIMS."""
from __future__ import annotations

import socket

from django.core.management.base import BaseCommand, CommandError

from laboratorio.instrumentos_astm import ACK, ENQ, EOT, encode_frame, join_records
from laboratorio.instrumentos_seed import asegurar_interfaz
from laboratorio.instrumentos_service import IngestaItem, consulta_trabajo, ingestar_resultados


def _mensaje_query(sample_id: str) -> str:
    return join_records(
        [
            ["H", r"\^&", "", "", "SIM"],
            ["Q", "1", f"^{sample_id}"],
            ["L", "1", "N"],
        ]
    )


def _mensaje_resultados(sample_id: str, pares: list[tuple[str, str]]) -> str:
    recs = [
        ["H", r"\^&", "", "", "SIM"],
        ["P", "1", sample_id],
        ["O", "1", sample_id],
    ]
    for i, (codigo, valor) in enumerate(pares, start=1):
        recs.append(["R", str(i), f"^^^{codigo}", valor, ""])
    recs.append(["L", "1", "N"])
    return join_records(recs)


class Command(BaseCommand):
    help = "Simula analizador: llama servicios LIMS (json) o envía ASTM por TCP."

    def add_arguments(self, parser):
        parser.add_argument("--driver", default="CM260")
        parser.add_argument("--sample-id", required=True)
        parser.add_argument("--mode", choices=("json", "astm"), default="json")
        parser.add_argument("--host", default="127.0.0.1")
        parser.add_argument("--port", type=int, default=5000)
        parser.add_argument(
            "--resultados",
            default="GLU:100,URE:30",
            help="codigo:valor,codigo:valor",
        )

    def handle(self, *args, **options):
        driver = options["driver"].strip().upper()
        sample_id = options["sample_id"].strip()
        pares: list[tuple[str, str]] = []
        for chunk in (options["resultados"] or "").split(","):
            if ":" not in chunk:
                continue
            k, v = chunk.split(":", 1)
            pares.append((k.strip().upper(), v.strip()))
        if options["mode"] == "json":
            interfaz = asegurar_interfaz(driver)
            wl = consulta_trabajo(sample_id=sample_id, interfaz=interfaz)
            self.stdout.write(f"worklist estado={wl.estado} analitos={len(wl.analitos)}")
            items = [IngestaItem(codigo_instrumento=c, valor=v) for c, v in pares]
            ing = ingestar_resultados(sample_id=sample_id, interfaz=interfaz, items=items)
            self.stdout.write(f"ingesta estado={ing.estado} cargados={ing.cargados} {ing.detalle}")
            return

        self._send_tcp(options["host"], int(options["port"]), _mensaje_query(sample_id))
        self._send_tcp(options["host"], int(options["port"]), _mensaje_resultados(sample_id, pares))
        self.stdout.write("ASTM query+resultados enviados.")

    def _send_tcp(self, host: str, port: int, message: str) -> None:
        try:
            sock = socket.create_connection((host, port), timeout=8)
        except OSError as exc:
            raise CommandError(f"No se pudo conectar a {host}:{port}: {exc}") from exc
        try:
            sock.sendall(ENQ)
            try:
                sock.recv(16)
            except OSError:
                pass
            sock.sendall(encode_frame(message, 1, last=True))
            try:
                sock.recv(16)
            except OSError:
                pass
            sock.sendall(EOT)
        finally:
            sock.close()
