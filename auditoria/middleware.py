from __future__ import annotations

import uuid
from typing import Callable

from django.http import HttpRequest, HttpResponse

from .context import ip_address_var, request_id_var, user_agent_var


class RequestContextMiddleware:
    """
    Attaches request tracing data to a request-scoped context.

    - Generates request_id (UUID4) per request
    - Captures ip_address and user_agent
    - Adds X-Request-ID header to the response
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

    @staticmethod
    def _get_client_ip(request: HttpRequest) -> str | None:
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            # first IP is the original client
            return xff.split(",")[0].strip() or None
        return request.META.get("REMOTE_ADDR") or None

    def __call__(self, request: HttpRequest) -> HttpResponse:
        rid = str(uuid.uuid4())
        ip = self._get_client_ip(request)
        ua = request.META.get("HTTP_USER_AGENT") or None

        t1 = request_id_var.set(rid)
        t2 = ip_address_var.set(ip)
        t3 = user_agent_var.set(ua)

        try:
            request.request_id = rid  # convenience attribute
            response = self.get_response(request)
            try:
                response["X-Request-ID"] = rid
            except Exception:
                # Don't break response creation on header issues.
                pass
            return response
        finally:
            request_id_var.reset(t1)
            ip_address_var.reset(t2)
            user_agent_var.reset(t3)

