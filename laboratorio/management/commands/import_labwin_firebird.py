"""
Importa delta LabWin desde CSV Firebird (post-corte), reutilizando escritura/auditoría R1.
"""
from __future__ import annotations

import uuid
from datetime import date
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from laboratorio.labwin_csv import load_labwin_csv
from laboratorio.labwin_firebird import load_firebird_delta
from laboratorio.management.commands.import_labwin_csv import (
    Command as LabwinCmd,
    _audit_labwin_batch,
    _hmac_token,
    _set_digest,
    _sha256_file,
)
from laboratorio.models import SolicitudExamen, TipoExamen
from pacientes.models import Paciente


class Command(BaseCommand):
    help = (
        "Importa órdenes LabWin nuevas desde extracción Firebird (DATOS/). "
        "No modifica órdenes FINALIZADO existentes."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "datos_dir",
            type=str,
            help="Carpeta DATOS/ con PACIENTES.csv, DETERS.csv, HCLINICA.csv",
        )
        parser.add_argument(
            "--wide-csv",
            default="data/icpl/todo_labwin.csv",
            help="Export ancho previo (excluye protocolos ya importados)",
        )
        parser.add_argument(
            "--since",
            default="2026-08-12",
            help="Solo protocolos con fecha estrictamente posterior (YYYY-MM-DD)",
        )
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument(
            "--allow-new-patients",
            action="store_true",
            help="Permite crear pacientes nuevos (DNI=HCLIN). Off por defecto.",
        )
        parser.add_argument("--batch-size", type=int, default=200)

    def handle(self, *args, **options):
        datos_dir = Path(options["datos_dir"]).expanduser().resolve()
        if not datos_dir.is_dir():
            raise CommandError(f"No existe directorio: {datos_dir}")
        for req in ("PACIENTES.csv", "DETERS.csv", "HCLINICA.csv", "RESULTS.csv"):
            if not (datos_dir / req).exists():
                raise CommandError(f"Falta {req} en {datos_dir}")

        since = date.fromisoformat(options["since"])
        wide_path = Path(options["wide_csv"]).expanduser().resolve()
        if not wide_path.exists():
            raise CommandError(f"No existe wide CSV: {wide_path}")

        _, wide_orders, _ = load_labwin_csv(wide_path)
        wide_protos = {o.protocolo for o in wide_orders}
        lims_codes = set(
            TipoExamen.objects.filter(activo=True).values_list("codigo", flat=True)
        )

        file_sha = _set_digest(
            [
                _sha256_file(datos_dir / "PACIENTES.csv"),
                _sha256_file(datos_dir / "DETERS.csv"),
                _sha256_file(datos_dir / "HCLINICA.csv"),
                _sha256_file(datos_dir / "RESULTS.csv"),
                options["since"],
            ]
        )

        patients, orders, stats = load_firebird_delta(
            datos_dir,
            wide_protocols=wide_protos,
            since=since,
            lims_codes=lims_codes,
        )

        self.stdout.write(f"Fuente Firebird: {datos_dir}")
        self.stdout.write(f"  Manifest digest: {file_sha}")
        self.stdout.write(f"  Since: {since.isoformat()}")
        self.stdout.write(f"  Protocolos leídos: {stats.protocols_read}")
        self.stdout.write(f"  Post-corte candidatos: {stats.protocols_post}")
        self.stdout.write(f"  Omitidos pre-corte: {stats.protocols_skipped_pre}")
        self.stdout.write(f"  Ya en wide CSV: {stats.protocols_skipped_in_wide}")
        self.stdout.write(f"  Sin HCLIN: {stats.protocols_no_hclin}")
        self.stdout.write(f"  HCLIN forma inválida: {stats.protocols_bad_hclin}")
        self.stdout.write(f"  Órdenes construidas: {stats.orders_built}")
        self.stdout.write(f"  Resultados mapeados: {stats.results_mapped}")
        self.stdout.write(f"  Resultados escalados: {stats.results_scaled}")
        self.stdout.write(f"  Resultados textuales/passthrough: {stats.results_textual}")
        self.stdout.write(f"  Resultados en cuarentena: {stats.results_quarantined}")
        self.stdout.write(f"  Determinaciones no mapeadas: {stats.results_unmapped_abrev}")
        self.stdout.write(f"  Pacientes en alcance: {stats.patients}")

        existing_pac = set(
            Paciente.objects.filter(dni__in=list(patients.keys())).values_list(
                "dni", flat=True
            )
        )
        to_create = [d for d in patients if d not in existing_pac]
        existing_numeros = set(
            SolicitudExamen.objects.filter(
                numero__in=[o.protocolo for o in orders]
            ).values_list("numero", flat=True)
        )
        new_orders = [o for o in orders if o.protocolo not in existing_numeros]
        self.stdout.write(f"  Pacientes nuevos: {len(to_create)}")
        self.stdout.write(f"  Órdenes nuevas vs BD: {len(new_orders)}")
        self.stdout.write(f"  Órdenes ya en BD (skip): {len(orders) - len(new_orders)}")

        identity_ok = len(to_create) == 0
        allow_new = bool(options["allow_new_patients"])
        if identity_ok:
            self.stdout.write(self.style.SUCCESS("  Identidad: OK — sin pacientes nuevos"))
        else:
            self.stdout.write(
                self.style.ERROR(
                    f"  Identidad: {len(to_create)} pacientes nuevos requieren "
                    "--allow-new-patients o precarga"
                )
            )

        if stats.warnings:
            self.stdout.write(self.style.WARNING("Advertencias (sin PHI):"))
            for w in stats.warnings[:20]:
                self.stdout.write(f"  - {w}")

        if options["dry_run"]:
            self.stdout.write(self.style.SUCCESS("Dry-run: no se modificó la base."))
            return

        if not identity_ok and not allow_new:
            raise CommandError("Apply bloqueado: pacientes nuevos sin autorización.")

        batch_id = str(uuid.uuid4())
        batch = max(1, options["batch_size"])
        progress = {
            "created_p": 0,
            "filled_p": 0,
            "created_o": 0,
            "created_r": 0,
            "created_protos": [],
            "created_dnis": [],
            "added_eab": 0,
        }
        tipos = {
            te.codigo: te
            for te in TipoExamen.objects.filter(
                codigo__in={c for o in new_orders for c in o.resultados},
                activo=True,
            )
        }

        write_patients = patients if allow_new else {
            d: patients[d] for d in patients if d in existing_pac
        }
        # Órdenes cuyo DNI no está en write_patients se omiten en _write
        if not allow_new:
            write_dnis = set(write_patients)
            new_orders = [o for o in new_orders if o.dni in write_dnis]

        _audit_labwin_batch(
            batch_id=batch_id,
            file_sha256=file_sha,
            success=True,
            metadata={
                "status": "started",
                "source": "firebird_r2",
                "since": since.isoformat(),
                "orders_planned": len(new_orders),
                "patients_in_scope": len(write_patients),
                "patients_new_planned": len(to_create) if allow_new else 0,
            },
        )

        writer = LabwinCmd()
        try:
            writer._write(
                patients=write_patients,
                orders=new_orders,
                tipos=tipos,
                batch=batch,
                batch_id=batch_id,
                file_sha256=file_sha,
                progress=progress,
            )
        except Exception as exc:
            _audit_labwin_batch(
                batch_id=batch_id,
                file_sha256=file_sha,
                success=False,
                error_message=type(exc).__name__,
                metadata={
                    "status": (
                        "failed_partial"
                        if (progress["created_o"] or progress["created_p"])
                        else "failed"
                    ),
                    "source": "firebird_r2",
                    "orders_created_confirmed": progress["created_o"],
                    "results_created_confirmed": progress["created_r"],
                    "orders_created_set_sha256": _set_digest(progress["created_protos"]),
                },
            )
            raise

        _audit_labwin_batch(
            batch_id=batch_id,
            file_sha256=file_sha,
            success=True,
            metadata={
                "status": "applied",
                "source": "firebird_r2",
                "patients_created": progress["created_p"],
                "orders_created": progress["created_o"],
                "results_created": progress["created_r"],
                "orders_created_set_sha256": _set_digest(progress["created_protos"]),
                "patients_created_hmac_set_sha256": _set_digest(
                    [_hmac_token("dni", d) for d in progress["created_dnis"]]
                ),
            },
        )
        self.stdout.write(self.style.SUCCESS("Importación Firebird R2 completada."))
        self.stdout.write(f"  Lote: {batch_id}")
        self.stdout.write(f"  Pacientes creados: {progress['created_p']}")
        self.stdout.write(f"  Órdenes creadas: {progress['created_o']}")
        self.stdout.write(f"  Resultados creados: {progress['created_r']}")
