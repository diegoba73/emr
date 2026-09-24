"""
Importa filas LabWin de DNIs en SKIP_DNI hacia el Paciente ya existente.

Solo filas cuyo apellido CSV coincide con el apellido del paciente cargado
(evita mezclar Jofre en la ficha Ingaramo, etc.). No crea pacientes nuevos.
"""
from __future__ import annotations

import re
import unicodedata
import uuid
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from laboratorio.labwin_csv import (
    SKIP_DNI,
    LabwinOrder,
    LabwinPatient,
    extraer_eab_layout_b,
    format_protocolo_labwin,
    iter_labwin_rows,
    normalize_dni,
    parse_fecha,
    split_nombre,
    _pick_resultados,
)
from laboratorio.management.commands.import_labwin_csv import (
    Command as LabwinCmd,
    _audit_labwin_batch,
    _hmac_token,
    _set_digest,
    _sha256_file,
)
from laboratorio.models import SolicitudExamen, TipoExamen
from pacientes.models import Paciente


def _fold(text: str) -> str:
    text = (text or "").strip().upper()
    text = "".join(
        c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"[^A-Z0-9]+", " ", text).strip()


def _apellido_coincide(csv_apellido: str, csv_nombre: str, paciente: Paciente) -> bool:
    """True si el apellido del paciente aparece como apellido CSV (no el colisionante)."""
    pac_ap = _fold(paciente.apellido or "")
    if not pac_ap or len(pac_ap) < 3:
        return False
    csv_ap = _fold(csv_apellido or "")
    csv_full = _fold(f"{csv_apellido} {csv_nombre}")
    if csv_ap == pac_ap:
        return True
    if (csv_ap.startswith(pac_ap) or pac_ap.startswith(csv_ap)) and min(
        len(csv_ap), len(pac_ap)
    ) >= 4:
        return True
    if csv_full.startswith(pac_ap + " "):
        return True
    return False


class Command(BaseCommand):
    help = (
        "Importa historial LabWin bloqueado (SKIP_DNI) solo a pacientes ya cargados, "
        "filtrando por coincidencia de apellido. Dry-run por defecto."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_file",
            nargs="?",
            default="data/icpl/todo_labwin.csv",
        )
        parser.add_argument("--encoding", default="utf-8-sig")
        parser.add_argument("--apply", action="store_true")
        parser.add_argument(
            "--dni",
            action="append",
            default=[],
            help="Limitar a estos DNI (default: todos los SKIP_DNI). Repetible.",
        )
        parser.add_argument("--batch-size", type=int, default=200)

    def handle(self, *args, **options):
        csv_path = Path(options["csv_file"]).expanduser().resolve()
        if not csv_path.exists():
            raise CommandError(f"No existe: {csv_path}")

        target = set(options["dni"]) or set(SKIP_DNI)
        unknown = target - set(SKIP_DNI)
        if unknown:
            raise CommandError(f"DNI no estan en SKIP_DNI: {sorted(unknown)}")

        existing = {
            p.dni: p for p in Paciente.objects.filter(dni__in=list(target))
        }

        named_orders = []
        for _line_no, row in iter_labwin_rows(csv_path, encoding=options["encoding"]):
            dni = normalize_dni(row.get("Nº doc."))
            if dni not in target:
                continue
            fecha = parse_fecha(row.get("Fecha"))
            if not fecha:
                continue
            numero = (row.get("Número") or "").strip()
            proto = format_protocolo_labwin(fecha, numero)
            if not proto:
                continue
            ap, no = split_nombre(row.get("Apellido y nombre"))
            resultados = _pick_resultados(row)
            paneles: list[str] = []
            eab = extraer_eab_layout_b(row)
            if eab:
                eab_res, panel = eab
                resultados.update(eab_res)
                paneles.append(panel)
            if not resultados:
                continue
            named_orders.append((dni, ap, no, proto, fecha, numero, resultados, paneles))

        existing_numeros = set(
            SolicitudExamen.objects.filter(
                numero__in=[t[3] for t in named_orders]
            ).values_list("numero", flat=True)
        )

        write_patients: dict[str, LabwinPatient] = {}
        write_orders: list[LabwinOrder] = []
        skipped_no_patient = 0
        skipped_name = 0
        skipped_already = 0
        by_dni_ok: dict[str, int] = {}

        for dni, ap, no, proto, fecha, numero, resultados, paneles in named_orders:
            pac = existing.get(dni)
            if pac is None:
                skipped_no_patient += 1
                continue
            if not _apellido_coincide(ap, no, pac):
                skipped_name += 1
                self.stdout.write(
                    f"  omitido nombre distinto: dni=***{dni[-3:]} csv_ap={ap[:24]!r}"
                )
                continue
            if proto in existing_numeros:
                skipped_already += 1
                continue
            write_patients[dni] = LabwinPatient(
                dni=dni,
                apellido=(pac.apellido or ap)[:100],
                nombre=(pac.nombre or no)[:100],
                telefono="",
                direccion="",
                fecha=fecha,
            )
            write_orders.append(
                LabwinOrder(
                    dni=dni,
                    fecha=fecha,
                    numero_labwin=numero,
                    protocolo=proto,
                    resultados=resultados,
                    paneles=paneles,
                )
            )
            by_dni_ok[dni] = by_dni_ok.get(dni, 0) + 1

        self.stdout.write("== import_labwin_skipped_existing ==")
        self.stdout.write(f"  modo: {'APPLY' if options['apply'] else 'DRY-RUN'}")
        self.stdout.write(f"  DNI objetivo: {sorted('***'+d[-3:] for d in target)}")
        self.stdout.write(f"  pacientes existentes: {len(existing)}")
        self.stdout.write(f"  filas CSV con resultado: {len(named_orders)}")
        self.stdout.write(f"  ordenes a crear: {len(write_orders)}")
        self.stdout.write(f"  omitidas sin paciente: {skipped_no_patient}")
        self.stdout.write(f"  omitidas nombre distinto: {skipped_name}")
        self.stdout.write(f"  omitidas ya en BD: {skipped_already}")
        for dni, n in sorted(by_dni_ok.items()):
            pac = existing[dni]
            self.stdout.write(
                f"  ***{dni[-3:]} -> {n} ordenes "
                f"(paciente id={pac.id} ap={_fold(pac.apellido)[:20]})"
            )

        if not options["apply"]:
            self.stdout.write(
                self.style.WARNING("Dry-run: no se modifico la base. Usar --apply.")
            )
            return

        if not write_orders:
            self.stdout.write(self.style.SUCCESS("Nada para importar."))
            return

        tipos = {
            te.codigo: te
            for te in TipoExamen.objects.filter(
                codigo__in={c for o in write_orders for c in o.resultados},
                activo=True,
            )
        }
        batch_id = str(uuid.uuid4())
        file_sha = _sha256_file(csv_path)
        progress = {
            "created_p": 0,
            "filled_p": 0,
            "created_o": 0,
            "created_r": 0,
            "created_protos": [],
            "created_dnis": [],
            "added_eab": 0,
        }
        _audit_labwin_batch(
            batch_id=batch_id,
            file_sha256=file_sha,
            success=True,
            metadata={
                "status": "started",
                "source": "import_labwin_skipped_existing",
                "orders_planned": len(write_orders),
                "dnis_count": len(by_dni_ok),
            },
        )
        writer = LabwinCmd()
        writer._write(
            patients=write_patients,
            orders=write_orders,
            tipos=tipos,
            batch=max(1, options["batch_size"]),
            batch_id=batch_id,
            file_sha256=file_sha,
            progress=progress,
        )
        _audit_labwin_batch(
            batch_id=batch_id,
            file_sha256=file_sha,
            success=True,
            metadata={
                "status": "applied",
                "source": "import_labwin_skipped_existing",
                "orders_created": progress["created_o"],
                "results_created": progress["created_r"],
                "patients_created": progress["created_p"],
                "orders_created_set_sha256": _set_digest(progress["created_protos"]),
                "patients_hmac_set_sha256": _set_digest(
                    [_hmac_token("dni", d) for d in progress["created_dnis"]]
                ),
            },
        )
        self.stdout.write(self.style.SUCCESS("Import SKIP existentes completado."))
        self.stdout.write(f"  Lote: {batch_id}")
        self.stdout.write(f"  Ordenes: {progress['created_o']}")
        self.stdout.write(f"  Resultados: {progress['created_r']}")
        self.stdout.write(f"  Pacientes creados (debe ser 0): {progress['created_p']}")
