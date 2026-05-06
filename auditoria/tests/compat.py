"""Compatibilidad de tests: ubicación del helper ``on_commit`` según versión de Django."""

from __future__ import annotations

try:
    from django.test.utils import capture_on_commit_callbacks
except ImportError:
    # Django 5.2+: el context manager vive en ``TestCase`` (no en ``TransactionTestCase`` / ``utils``).
    from django.test.testcases import TestCase

    capture_on_commit_callbacks = TestCase.captureOnCommitCallbacks
