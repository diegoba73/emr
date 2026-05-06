"""
Request-scoped context for audit logging.

We use contextvars so that audit logging can be called from anywhere in the
request execution path without wiring request objects through every layer.
"""

from __future__ import annotations

from contextvars import ContextVar

request_id_var: ContextVar[str | None] = ContextVar("auditoria_request_id", default=None)
ip_address_var: ContextVar[str | None] = ContextVar("auditoria_ip_address", default=None)
user_agent_var: ContextVar[str | None] = ContextVar("auditoria_user_agent", default=None)


def get_request_id() -> str | None:
    return request_id_var.get()


def get_ip_address() -> str | None:
    return ip_address_var.get()


def get_user_agent() -> str | None:
    return user_agent_var.get()

