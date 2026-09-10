"""Sesión ASTM E1381 sobre TCP (un cliente por conexión)."""
from __future__ import annotations

import logging
import socket

from laboratorio.instrumentos_astm import (
    ACK,
    ENQ,
    EOT,
    ETB,
    ETX,
    NAK,
    STX,
    decode_frame,
    frames_from_message,
)
from laboratorio.instrumentos_drivers import (
    is_query_message,
    is_result_message,
    parse_ingesta_message,
    parse_query_sample_id,
    sender_for_driver,
    worklist_to_astm,
)
from laboratorio.instrumentos_service import consulta_trabajo, ingestar_resultados
from laboratorio.models_instrumentos import InterfazInstrumento, MensajeInstrumento

logger = logging.getLogger(__name__)

RECV_TIMEOUT = 30


def _assemble_frames(chunks: list[str]) -> str:
    return "".join(chunks)


def handle_astm_connection(conn: socket.socket, interfaz: InterfazInstrumento, actor=None) -> None:
    conn.settimeout(RECV_TIMEOUT)
    buf = b""
    frame_texts: list[str] = []
    try:
        while True:
            try:
                data = conn.recv(4096)
            except socket.timeout:
                break
            if not data:
                break
            buf += data
            if ENQ in buf:
                conn.sendall(ACK)
                buf = buf.replace(ENQ, b"", 1)
            while True:
                start = buf.find(STX)
                if start < 0:
                    break
                end_etx = buf.find(ETX, start)
                end_etb = buf.find(ETB, start)
                ends = [i for i in (end_etx, end_etb) if i >= 0]
                if not ends:
                    break
                end = min(ends)
                # checksum 2 + CR LF
                frame_end = end + 5
                if len(buf) < frame_end:
                    break
                raw = buf[start:frame_end]
                buf = buf[frame_end:]
                try:
                    text = decode_frame(raw)
                    frame_texts.append(text)
                    conn.sendall(ACK)
                except ValueError:
                    logger.warning("ASTM frame inválido interfaz=%s", interfaz.pk)
                    conn.sendall(NAK)
                    frame_texts.clear()
            if EOT in buf:
                buf = buf.replace(EOT, b"", 1)
                message = _assemble_frames(frame_texts)
                frame_texts = []
                if not message.strip():
                    continue
                _dispatch_message(conn, interfaz, message, actor=actor)
    except Exception:
        logger.exception("Error sesión ASTM interfaz=%s", interfaz.pk)


def _dispatch_message(conn: socket.socket, interfaz: InterfazInstrumento, message: str, actor=None) -> None:
    sender = sender_for_driver(interfaz.driver)
    if is_query_message(message):
        sample_id = parse_query_sample_id(message)
        wl = consulta_trabajo(
            sample_id=sample_id,
            interfaz=interfaz,
            actor=actor,
            crudo=message,
        )
        if wl.estado != MensajeInstrumento.Estado.OK or not wl.analitos:
            reply = worklist_to_astm(wl, sender=sender) if wl.muestra else ""
            if not wl.analitos:
                from laboratorio.instrumentos_astm import build_header, build_terminator, join_records

                reply = join_records([build_header(sender), ["P", "1"], ["L", "1", "F"]])
            _send_message(conn, reply)
            return
        _send_message(conn, worklist_to_astm(wl, sender=sender))
        return
    if is_result_message(message):
        sample_id, items = parse_ingesta_message(message)
        ingestar_resultados(
            sample_id=sample_id,
            interfaz=interfaz,
            items=items,
            actor=actor,
            crudo=message,
        )
        return
    logger.info("ASTM mensaje ignorado interfaz=%s", interfaz.pk)


def _send_message(conn: socket.socket, message: str) -> None:
    conn.sendall(ENQ)
    try:
        ack = conn.recv(8)
        if ACK not in ack:
            return
    except socket.timeout:
        return
    for frame in frames_from_message(message):
        conn.sendall(frame)
        try:
            ack = conn.recv(8)
            if NAK in ack:
                conn.sendall(frame)
        except socket.timeout:
            break
    conn.sendall(EOT)


def serve_tcp(interfaz: InterfazInstrumento, host: str, port: int) -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, port))
    sock.listen(5)
    logger.info("Gateway ASTM %s escuchando %s:%s", interfaz.driver, host, port)
    try:
        while True:
            conn, addr = sock.accept()
            logger.info("ASTM conexión %s", addr)
            try:
                handle_astm_connection(conn, interfaz)
            finally:
                conn.close()
    finally:
        sock.close()
