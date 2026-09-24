"""
Importa catálogos microbiológicos LabWin (ANTIB, BACTE, NEMOTEC, NEMOESPE).

Idempotente: clave = tipo de catálogo + código (preserva mayúsculas/espacios).
No pisa ediciones manuales. No importa datos clínicos de pacientes.

Uso:
  python manage.py import_labwin_micro_catalogos /ruta/exportacion --dry-run
  python manage.py import_labwin_micro_catalogos /ruta/exportacion
  python manage.py import_labwin_micro_catalogos --fixtures --dry-run
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from laboratorio.labwin_micro_catalog_corrections import (
    corregir_antibiotico,
    corregir_frase,
    corregir_microorganismo,
    filas_reporte_revision_conocidas,
)
from laboratorio.labwin_micro_csv import cell_str, iter_labwin_csv_rows
from laboratorio.models_microbiologia import (
    Antibiotico,
    FraseRapidaAsociacionAnalisis,
    FraseRapidaMicrobiologia,
    LabwinMicroCatalogImportBatch,
    Microorganismo,
)

FIXTURES_DIR = (
    Path(__file__).resolve().parents[2] / "fixtures" / "labwin_micro_catalog_minimo"
)


def _counter() -> dict:
    return {
        "insertados": 0,
        "actualizados": 0,
        "omitidos": 0,
        "omitidos_manual": 0,
        "duplicados_archivo": 0,
        "errores": 0,
    }


class Command(BaseCommand):
    help = "Importa catálogos micro LabWin (ANTIB/BACTE/NEMOTEC/NEMOESPE) de forma idempotente."

    def add_arguments(self, parser):
        parser.add_argument(
            "export_dir",
            nargs="?",
            default="",
            help="Directorio de exportación LabWin (contiene ANTIB.csv, etc.).",
        )
        parser.add_argument("--dry-run", action="store_true", help="Simula sin persistir.")
        parser.add_argument(
            "--fixtures",
            action="store_true",
            help="Usa fixtures mínimos en laboratorio/fixtures/labwin_micro_catalog_minimo/.",
        )
        parser.add_argument("--encoding", default="utf-8-sig")

    def handle(self, *args, **options):
        dry = bool(options["dry_run"])
        if options["fixtures"]:
            export_dir = FIXTURES_DIR
        else:
            if not options["export_dir"]:
                raise CommandError("Indique export_dir o use --fixtures.")
            export_dir = Path(options["export_dir"]).expanduser()
        export_dir = export_dir.resolve()
        if not export_dir.is_dir():
            raise CommandError(f"Directorio inexistente: {export_dir}")

        required = ["ANTIB.csv", "BACTE.csv", "NEMOTEC.csv", "NEMOESPE.csv"]
        missing = [f for f in required if not (export_dir / f).is_file()]
        if missing:
            raise CommandError(f"Faltan archivos en {export_dir}: {', '.join(missing)}")

        self.stdout.write(f"Fuente: {export_dir}")
        self.stdout.write(f"Modo: {'DRY-RUN' if dry else 'IMPORTACIÓN'}")

        counts = {k: _counter() for k in ("ANTIB", "BACTE", "NEMOTEC", "NEMOESPE")}
        errores: list[dict] = []
        revision: list[dict] = []
        now = timezone.now()
        enc = options["encoding"]

        def run():
            self._import_antib(export_dir / "ANTIB.csv", counts["ANTIB"], errores, revision, now, enc)
            self._import_bacte(export_dir / "BACTE.csv", counts["BACTE"], errores, revision, now, enc)
            self._import_nemotec(export_dir / "NEMOTEC.csv", counts["NEMOTEC"], errores, revision, now, enc)
            self._import_nemoespe(export_dir / "NEMOESPE.csv", counts["NEMOESPE"], errores, revision, now, enc)

        with transaction.atomic():
            run()
            batch = LabwinMicroCatalogImportBatch(
                fuente_dir=str(export_dir),
                dry_run=dry,
                counts=counts,
                errores=errores[:200],
                revision_pendiente=revision[:500],
            )
            batch.save()
            batch.finished_at = timezone.now()
            batch.save(update_fields=["finished_at"])
            if dry:
                transaction.set_rollback(True)

        for cat, c in counts.items():
            self.stdout.write(
                f"  {cat}: insertados={c['insertados']} actualizados={c['actualizados']} "
                f"omitidos={c['omitidos']} omitidos_manual={c['omitidos_manual']} "
                f"duplicados_archivo={c['duplicados_archivo']} errores={c['errores']}"
            )
        self.stdout.write(f"Errores de fila: {len(errores)}")
        for e in errores[:10]:
            self.stdout.write(f"  ! {e}")
        self.stdout.write(f"Pendientes de revisión (esta corrida): {len(revision)}")
        self.stdout.write("Reglas documentadas conocidas:")
        for row in filas_reporte_revision_conocidas():
            self.stdout.write(
                f"  [{row['origen']}] {row['codigo']}: {row['original']!r} → "
                f"{row['propuesta']!r} ({row['motivo']})"
            )

    def _import_antib(self, path, counts, errores, revision, now, encoding):
        seen: Counter[str] = Counter()
        for i, row in enumerate(iter_labwin_csv_rows(path, encoding=encoding), start=2):
            try:
                codigo = cell_str(row.get("ABREV_FLD"))
                if not codigo:
                    counts["omitidos"] += 1
                    continue
                seen[codigo] += 1
                if seen[codigo] > 1:
                    counts["duplicados_archivo"] += 1
                    errores.append(
                        {"archivo": "ANTIB", "fila": i, "codigo": codigo, "error": "duplicado en archivo"}
                    )
                    continue
                nombre_orig = cell_str(row.get("NOMBRE_FLD"))
                corr = corregir_antibiotico(codigo, nombre_orig)
                d1 = cell_str(row.get("D1_FLD"))
                d2 = cell_str(row.get("D2_FLD"))
                if corr.requiere_revision:
                    revision.append(
                        {
                            "catalogo": "ANTIB",
                            "codigo": codigo,
                            "original": nombre_orig,
                            "propuesta": corr.nombre_mostrar,
                            "motivo": corr.motivo_revision,
                        }
                    )
                existing = Antibiotico.objects.filter(codigo=codigo).first()
                if existing is None:
                    Antibiotico.objects.create(
                        codigo=codigo,
                        nombre=corr.nombre_mostrar or nombre_orig,
                        nombre_original=nombre_orig,
                        origen="LABWIN_ANTIB",
                        correccion_estado=corr.correccion_estado,
                        requiere_revision=corr.requiere_revision,
                        motivo_revision=corr.motivo_revision,
                        archivo_origen=path.name,
                        importado_at=now,
                        labwin_d1=d1,
                        labwin_d2=d2,
                        activo=corr.activo,
                    )
                    counts["insertados"] += 1
                    continue
                if existing.editado_manualmente:
                    counts["omitidos_manual"] += 1
                    continue
                if existing.origen not in ("LABWIN_ANTIB", "MANUAL") and existing.nombre and existing.nombre != (
                    corr.nombre_mostrar or nombre_orig
                ):
                    existing.nombre_original = existing.nombre_original or nombre_orig
                    existing.labwin_d1 = d1 or existing.labwin_d1
                    existing.labwin_d2 = d2 or existing.labwin_d2
                    existing.archivo_origen = path.name
                    existing.importado_at = now
                    existing.save()
                    counts["omitidos"] += 1
                    continue
                existing.nombre_original = nombre_orig
                existing.origen = "LABWIN_ANTIB"
                existing.labwin_d1 = d1
                existing.labwin_d2 = d2
                existing.archivo_origen = path.name
                existing.importado_at = now
                existing.correccion_estado = corr.correccion_estado
                existing.requiere_revision = corr.requiere_revision
                existing.motivo_revision = corr.motivo_revision
                existing.nombre = corr.nombre_mostrar or nombre_orig
                existing.activo = corr.activo
                existing.save()
                counts["actualizados"] += 1
            except Exception as exc:  # noqa: BLE001
                counts["errores"] += 1
                errores.append({"archivo": "ANTIB", "fila": i, "error": str(exc)})

    def _import_bacte(self, path, counts, errores, revision, now, encoding):
        seen: Counter[str] = Counter()
        for i, row in enumerate(iter_labwin_csv_rows(path, encoding=encoding), start=2):
            try:
                codigo = cell_str(row.get("ABREV_FLD"))
                if not codigo:
                    counts["omitidos"] += 1
                    continue
                seen[codigo] += 1
                if seen[codigo] > 1:
                    counts["duplicados_archivo"] += 1
                    errores.append(
                        {"archivo": "BACTE", "fila": i, "codigo": codigo, "error": "duplicado en archivo"}
                    )
                    continue
                nombre_orig = cell_str(row.get("NOMBRE_FLD"))
                corr = corregir_microorganismo(codigo, nombre_orig)
                if corr.requiere_revision:
                    revision.append(
                        {
                            "catalogo": "BACTE",
                            "codigo": codigo,
                            "original": nombre_orig,
                            "propuesta": corr.nombre_mostrar,
                            "motivo": corr.motivo_revision,
                        }
                    )
                existing = Microorganismo.objects.filter(codigo=codigo).first()
                if existing is None:
                    Microorganismo.objects.create(
                        codigo=codigo,
                        nombre=corr.nombre_mostrar or nombre_orig,
                        nombre_original=nombre_orig,
                        origen="LABWIN_BACTE",
                        tipo_registro=corr.tipo_registro or "MICROORGANISMO",
                        correccion_estado=corr.correccion_estado,
                        requiere_revision=corr.requiere_revision,
                        motivo_revision=corr.motivo_revision,
                        archivo_origen=path.name,
                        importado_at=now,
                        activo=corr.activo,
                    )
                    counts["insertados"] += 1
                    continue
                if existing.editado_manualmente:
                    counts["omitidos_manual"] += 1
                    continue
                if existing.origen not in ("LABWIN_BACTE", "MANUAL") and existing.nombre:
                    existing.nombre_original = existing.nombre_original or nombre_orig
                    existing.archivo_origen = path.name
                    existing.importado_at = now
                    existing.save()
                    counts["omitidos"] += 1
                    continue
                existing.nombre_original = nombre_orig
                existing.origen = "LABWIN_BACTE"
                existing.tipo_registro = corr.tipo_registro or existing.tipo_registro
                existing.correccion_estado = corr.correccion_estado
                existing.requiere_revision = corr.requiere_revision
                existing.motivo_revision = corr.motivo_revision
                existing.nombre = corr.nombre_mostrar or nombre_orig
                existing.archivo_origen = path.name
                existing.importado_at = now
                existing.activo = corr.activo
                existing.save()
                counts["actualizados"] += 1
            except Exception as exc:  # noqa: BLE001
                counts["errores"] += 1
                errores.append({"archivo": "BACTE", "fila": i, "error": str(exc)})

    def _import_nemotec(self, path, counts, errores, revision, now, encoding):
        seen: Counter[str] = Counter()
        for i, row in enumerate(iter_labwin_csv_rows(path, encoding=encoding), start=2):
            try:
                abrev = cell_str(row.get("ABREV_FLD"))
                if not abrev:
                    counts["omitidos"] += 1
                    continue
                seen[abrev] += 1
                if seen[abrev] > 1:
                    counts["duplicados_archivo"] += 1
                    errores.append(
                        {"archivo": "NEMOTEC", "fila": i, "codigo": abrev, "error": "duplicado en archivo"}
                    )
                    continue
                texto_orig = cell_str(row.get("TEXTO_FLD"))
                corr = corregir_frase(abrev, texto_orig)
                if corr.requiere_revision:
                    revision.append(
                        {
                            "catalogo": "NEMOTEC",
                            "codigo": abrev,
                            "original": texto_orig[:200],
                            "propuesta": (corr.nombre_mostrar or "")[:200],
                            "motivo": corr.motivo_revision,
                        }
                    )
                existing = FraseRapidaMicrobiologia.objects.filter(abreviatura=abrev).first()
                if existing is None:
                    FraseRapidaMicrobiologia.objects.create(
                        abreviatura=abrev,
                        texto=corr.nombre_mostrar or texto_orig,
                        texto_original=texto_orig,
                        categoria=corr.categoria or "GENERAL",
                        origen="LABWIN_NEMOTEC",
                        correccion_estado=corr.correccion_estado,
                        requiere_revision=corr.requiere_revision,
                        motivo_revision=corr.motivo_revision,
                        archivo_origen=path.name,
                        importado_at=now,
                        activo=corr.activo,
                    )
                    counts["insertados"] += 1
                    continue
                if existing.editado_manualmente:
                    counts["omitidos_manual"] += 1
                    continue
                existing.texto_original = texto_orig
                existing.texto = corr.nombre_mostrar or texto_orig
                existing.categoria = corr.categoria or existing.categoria
                existing.origen = "LABWIN_NEMOTEC"
                existing.correccion_estado = corr.correccion_estado
                existing.requiere_revision = corr.requiere_revision
                existing.motivo_revision = corr.motivo_revision
                existing.archivo_origen = path.name
                existing.importado_at = now
                existing.activo = corr.activo
                existing.save()
                counts["actualizados"] += 1
            except Exception as exc:  # noqa: BLE001
                counts["errores"] += 1
                errores.append({"archivo": "NEMOTEC", "fila": i, "error": str(exc)})

    def _import_nemoespe(self, path, counts, errores, revision, now, encoding):
        seen: Counter[tuple] = Counter()
        for i, row in enumerate(iter_labwin_csv_rows(path, encoding=encoding), start=2):
            try:
                analisis = cell_str(row.get("ABREV_FLD"))
                pos_raw = row.get("POSICION_FLD")
                nemo = cell_str(row.get("NEMOTEC_FLD"))
                numrec = cell_str(row.get("NUMREC_FLD"))
                if not analisis or pos_raw is None or pos_raw == "" or not nemo:
                    counts["omitidos"] += 1
                    continue
                try:
                    posicion = int(str(pos_raw).strip())
                except ValueError:
                    counts["errores"] += 1
                    errores.append(
                        {
                            "archivo": "NEMOESPE",
                            "fila": i,
                            "error": f"POSICION_FLD no numérica: {pos_raw!r}",
                        }
                    )
                    continue
                key = (analisis, posicion, nemo)
                seen[key] += 1
                if seen[key] > 1:
                    counts["duplicados_archivo"] += 1
                    continue
                frase = FraseRapidaMicrobiologia.objects.filter(abreviatura=nemo).first()
                existing = FraseRapidaAsociacionAnalisis.objects.filter(
                    analisis_abrev_labwin=analisis,
                    posicion=posicion,
                    nemotec_abrev=nemo,
                ).first()
                if existing is None:
                    FraseRapidaAsociacionAnalisis.objects.create(
                        analisis_abrev_labwin=analisis,
                        posicion=posicion,
                        nemotec_abrev=nemo,
                        frase=frase,
                        numrec_labwin=numrec,
                        archivo_origen=path.name,
                        importado_at=now,
                    )
                    counts["insertados"] += 1
                else:
                    existing.frase = frase
                    existing.numrec_labwin = numrec
                    existing.archivo_origen = path.name
                    existing.importado_at = now
                    existing.save()
                    counts["actualizados"] += 1
                if frase is None:
                    revision.append(
                        {
                            "catalogo": "NEMOESPE",
                            "codigo": f"{analisis}@{posicion}:{nemo}",
                            "original": nemo,
                            "propuesta": "frase pendiente de resolución",
                            "motivo": "NEMOTEC_FLD sin fila correspondiente en NEMOTEC",
                        }
                    )
            except Exception as exc:  # noqa: BLE001
                counts["errores"] += 1
                errores.append({"archivo": "NEMOESPE", "fila": i, "error": str(exc)})
