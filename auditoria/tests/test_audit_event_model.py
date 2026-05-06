import pytest
from django.core.exceptions import ValidationError

from auditoria.models import AuditEvent


@pytest.mark.django_db
def test_audit_event_is_append_only():
    ev = AuditEvent.objects.create(
        action="CREATE",
        entity_type="turnos.Turno",
        entity_id="1",
        entity_repr="Turno #1",
        request_id="req-1",
    )

    # UPDATE should fail
    ev.action = "UPDATE"
    with pytest.raises(ValidationError):
        ev.save()

    # DELETE should fail
    with pytest.raises(ValidationError):
        ev.delete()

