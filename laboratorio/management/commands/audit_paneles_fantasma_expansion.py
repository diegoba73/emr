"""
Solo lectura: detecta expansión fantasma de paneles por componentes compartidos.

Uso (local):
  python manage.py audit_paneles_fantasma_expansion
  python manage.py audit_paneles_fantasma_expansion --numeros LAB-2026-00107 LAB-2026-00109

Uso (producción):
  ssh -p 2223 server@emr.sytes.net
  cd /srv/emr/app
  docker exec emr_backend_server python manage.py audit_paneles_fantasma_expansion
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

from laboratorio.audit_paneles_fantasma import NUMEROS_DEFAULT, auditar_por_numeros


class Command(BaseCommand):
    help = (
        "Audita (solo lectura) órdenes con paneles 24 hs / clearance "
        "probablemente agregados por componentes compartidos."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--numeros",
            nargs="+",
            default=None,
            help="Números de protocolo (default: las 7 órdenes reportadas).",
        )

    def handle(self, *args, **options):
        numeros = options["numeros"] or list(NUMEROS_DEFAULT)
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "Auditoría paneles fantasma por componentes compartidos (solo lectura)"
            )
        )
        self.stdout.write(f"Órdenes: {', '.join(numeros)}")
        self.stdout.write(
            "Claves: candidato_borrar = firma exclusiva vacía sin muestra/validación; "
            "compartido_revisar = DIUR/CREA_U/etc. arrastrado; "
            "revisar_manual = firma con valor/muestra/validado.\n"
        )

        informes = auditar_por_numeros(numeros)
        con_hallazgo = 0
        candidatos = 0
        revisar = 0

        for inf in informes:
            if inf.estado == "NO_ENCONTRADA":
                self.stdout.write(
                    self.style.ERROR(f"\n=== {inf.numero}: NO ENCONTRADA ===")
                )
                continue

            marca = "HALLAZGO" if inf.hallazgo else "sin firmas fantasma"
            style = self.style.WARNING if inf.hallazgo else self.style.SUCCESS
            self.stdout.write(
                style(
                    f"\n=== {inf.numero} (id={inf.id}) estado={inf.estado} [{marca}] ==="
                )
            )
            self.stdout.write(
                f"  Paneles M2M: {', '.join(inf.paneles) or '—'}"
            )
            self.stdout.write(
                f"  Justificados por paneles: {', '.join(inf.justificados) or '—'}"
            )

            if inf.sospechas:
                con_hallazgo += 1
                for s in inf.sospechas:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  Sospecha {s.panel}: firmas={', '.join(s.firmas_presentes)} | "
                            f"presentes={', '.join(s.componentes_presentes)} | "
                            f"no_justificados={', '.join(s.exclusivos_no_justificados)}"
                        )
                    )

            self.stdout.write("  Resultados:")
            for f in inf.filas:
                if f.clasificacion == "justificado" and not inf.hallazgo:
                    continue
                if f.clasificacion == "justificado":
                    # Con hallazgo, listar solo no justificados + firmas
                    continue
                flags = []
                if f.tiene_muestra:
                    flags.append(f"muestra={f.muestra_id}")
                else:
                    flags.append("sin_muestra")
                if f.validado:
                    flags.append("validado")
                if f.en_tipos_examen:
                    flags.append("en_tipos")
                valor_txt = repr(f.valor) if f.valor else "''"
                line = (
                    f"    [{f.clasificacion}] {f.codigo} id={f.id} "
                    f"valor={valor_txt} ({', '.join(flags)})"
                )
                if f.clasificacion == "candidato_borrar":
                    candidatos += 1
                    self.stdout.write(self.style.ERROR(line))
                elif f.clasificacion == "revisar_manual":
                    revisar += 1
                    self.stdout.write(self.style.WARNING(line))
                else:
                    revisar += 1
                    self.stdout.write(line)

            if inf.tubos:
                self.stdout.write("  Tubos/muestras:")
                for t in inf.tubos:
                    self.stdout.write(f"    {t}")
            else:
                self.stdout.write("  Tubos/muestras: (ninguno)")

        self.stdout.write(self.style.MIGRATE_HEADING("\nResumen"))
        self.stdout.write(f"  Órdenes con sospecha: {con_hallazgo}/{len(informes)}")
        self.stdout.write(f"  Filas candidato_borrar: {candidatos}")
        self.stdout.write(f"  Filas a revisar (manual/compartido): {revisar}")
        self.stdout.write(
            self.style.NOTICE(
                "\nNo modifica la base. Revisá el informe antes de cualquier reparación."
            )
        )
