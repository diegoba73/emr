#!/usr/bin/env python3
"""
Build consolidated GPT Knowledge package from docs_synesis sources.

Idempotent: overwrites only files inside docs_synesis_gpt_knowledge/.
Does not modify, move, or delete source documents.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_ROOT = REPO_ROOT / "docs_synesis"
OUTPUT_DIR = REPO_ROOT / "docs_synesis_gpt_knowledge"

DERIVED_WARNING = (
    "ADVERTENCIA: Los archivos SYNESIS_*.md en este directorio son derivados "
    "generados automáticamente. NO son fuente de verdad primaria. "
    "La SoT canónica permanece en docs_synesis/ (y el código del repositorio)."
)

# Rutas relativas al repo excluidas del escaneo de cobertura (unassigned_sources).
# Usar solo con justificación documentada; vacío = incluir todo .md bajo docs_synesis/.
EXPLICIT_EXCLUDE_FROM_COVERAGE: frozenset[str] = frozenset(
    {
        # Ejemplo futuro: "docs_synesis/README.md" — índice interno, no SoT de dominio
    }
)

SOURCE_BLOCK_TEMPLATE = """---

# Fuente: {source_path}

**Archivo fuente:** `{source_path}`
**Generado automáticamente:** sí

---

"""


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_text(path.read_text(encoding="utf-8"))


def relative_posix(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def read_source(source_rel: str) -> tuple[str | None, dict[str, Any]]:
    """Return (content, metadata). content is None if missing."""
    path = REPO_ROOT / source_rel
    meta: dict[str, Any] = {
        "path": source_rel,
        "status": "missing",
        "size_bytes": 0,
        "char_count": 0,
        "sha256": None,
    }
    if not path.is_file():
        return None, meta

    text = path.read_text(encoding="utf-8")
    meta.update(
        {
            "status": "included",
            "size_bytes": path.stat().st_size,
            "char_count": len(text),
            "sha256": sha256_text(text),
        }
    )
    return text, meta


def build_consolidated(
    output_name: str,
    source_paths: list[str],
) -> tuple[str, dict[str, Any]]:
    parts: list[str] = []
    included: list[dict[str, Any]] = []
    missing: list[str] = []

    for source_rel in source_paths:
        content, meta = read_source(source_rel)
        if content is None:
            missing.append(source_rel)
            continue
        included.append(meta)
        parts.append(SOURCE_BLOCK_TEMPLATE.format(source_path=source_rel))
        parts.append(content.rstrip())
        parts.append("\n\n")

    body = "\n".join(parts).rstrip() + "\n"
    consolidated_meta = {
        "file": output_name,
        "size_bytes": len(body.encode("utf-8")),
        "char_count": len(body),
        "sha256": sha256_text(body),
        "sources_included": included,
        "sources_missing": missing,
        "source_count_included": len(included),
        "source_count_missing": len(missing),
    }
    return body, consolidated_meta


def prod_operational_sources() -> list[str]:
    """PROD_*, checklists and related operational docs for SYNESIS_06."""
    patterns = [
        SOURCE_ROOT / "checklists" / "*.md",
        SOURCE_ROOT / "PROD_*.md",
    ]
    found: set[Path] = set()
    for pattern in patterns:
        found.update(pattern.parent.glob(pattern.name))
    rel_paths = sorted(relative_posix(p) for p in found)
    return rel_paths


def reglas_ordered_sources() -> list[str]:
    """Order: pacientes, usuarios, auditoria, documentos, ia, then alpha."""
    reglas_dir = SOURCE_ROOT / "reglas"
    if not reglas_dir.is_dir():
        return []

    all_files = sorted(reglas_dir.glob("*.md"))
    priority = [
        "pacientes.md",
        "usuarios-y-permisos.md",
        "auditoria.md",
        "documentos-e-imagenes.md",
        "ia.md",
    ]
    by_name = {p.name: p for p in all_files}
    ordered: list[str] = []
    seen: set[str] = set()

    for name in priority:
        if name in by_name:
            ordered.append(relative_posix(by_name[name]))
            seen.add(name)

    for path in all_files:
        if path.name not in seen:
            ordered.append(relative_posix(path))

    return ordered


def package_definitions() -> list[tuple[str, list[str]]]:
    """Return (output_filename, source_paths) for each consolidated file."""
    reglas = reglas_ordered_sources()

    packages: list[tuple[str, list[str]]] = [
        (
            "SYNESIS_00_MAPA_Y_PRIORIDADES.md",
            [
                "docs_synesis/DOC_MAPA_SISTEMA.md",
                "docs_synesis/DOC_ESTADO_ACTUAL_VERIFICADO.md",
            ],
        ),
        (
            "SYNESIS_01_REGLAS_CRITICAS.md",
            ["docs_synesis/DOC_REGLAS_NEGOCIO.md", *reglas],
        ),
        (
            "SYNESIS_02_DOMINIO_ESTADOS_INVARIANTES.md",
            [
                "docs_synesis/DOC_MODELO_FUNDAMENTAL_EMR_LIMS.md",
                "docs_synesis/DOC_ENTIDADES_PRINCIPALES.md",
                "docs_synesis/DOC_INVARIANTES.md",
                "docs_synesis/DOC_ESTADOS_TRANSICIONES.md",
            ],
        ),
        (
            "SYNESIS_03_BACKEND_API_DB.md",
            [
                "docs_synesis/DOC_BACKEND.md",
                "docs_synesis/DOC_API_ENDPOINTS.md",
                "docs_synesis/DOC_MODELOS_DB.md",
            ],
        ),
        (
            "SYNESIS_04_FLUJOS_EMR_LIMS.md",
            [
                "docs_synesis/DOC_FLUJOS_EMR.md",
                "docs_synesis/DOC_FLUJOS_LIMS.md",
            ],
        ),
        (
            "SYNESIS_05_FRONTEND_PERMISOS_AUDITORIA.md",
            [
                "docs_synesis/DOC_FRONTEND.md",
                "docs_synesis/DOC_PERMISOS_AUDITORIA.md",
            ],
        ),
        (
            "SYNESIS_06_TESTS_RIESGOS_OPERACION.md",
            [
                "docs_synesis/DOC_TESTS.md",
                "docs_synesis/DOC_RIESGOS_DEUDA_TECNICA.md",
                # Roadmap LIMS / deuda / próximas fases (no obsoletos)
                "docs_synesis/DOC_BLUEPRINT_LIMS_FASE_B.md",
                "docs_synesis/INFORME_PROXIMAS_FASES_LIMS.md",
                *prod_operational_sources(),
            ],
        ),
        (
            "SYNESIS_07_PROTOCOLO_ASISTENTE.md",
            [
                "docs_synesis/DOC_PROTOCOLO_TRABAJO_ASISTENTE.md",
                "docs_synesis/DOC_TRABAJO_SYNESIS_CURSOR_CODEX.md",
                "docs_synesis/prompts/prompt-maestro-cursor.md",
                "docs_synesis/B3_VALIDACION_A_CODEX_AUDIT.md",
            ],
        ),
    ]
    return packages


def discover_docs_synesis_markdown() -> list[str]:
    """All .md files under docs_synesis/, sorted."""
    if not SOURCE_ROOT.is_dir():
        return []
    return sorted(relative_posix(p) for p in SOURCE_ROOT.rglob("*.md"))


def assigned_sources_from_packages(
    packages: list[tuple[str, list[str]]],
) -> set[str]:
    assigned: set[str] = set()
    for _, source_paths in packages:
        assigned.update(source_paths)
    return assigned


def compute_unassigned_sources(
    packages: list[tuple[str, list[str]]],
) -> list[str]:
    """
    Existing .md under docs_synesis/ not included in any consolidated file.

    Excludes paths in EXPLICIT_EXCLUDE_FROM_COVERAGE (documented opt-out).
    Does not scan docs_synesis_gpt_knowledge/ (lives outside docs_synesis/).
    """
    all_md = set(discover_docs_synesis_markdown())
    assigned = assigned_sources_from_packages(packages)
    excluded = EXPLICIT_EXCLUDE_FROM_COVERAGE
    return sorted(all_md - assigned - excluded)


def build_readme(manifest: dict[str, Any]) -> str:
    missing = manifest.get("all_missing_sources", [])
    unassigned = manifest.get("unassigned_sources", [])
    warnings = manifest.get("warnings", [])
    consolidated = manifest.get("consolidated_files", [])

    lines = [
        "# SYNESIS GPT Knowledge — Paquete consolidado",
        "",
        f"**Generado:** {manifest['generated_at']}",
        "",
        DERIVED_WARNING,
        "",
        "## Propósito",
        "",
        "Este directorio contiene una **vista consolidada** de la documentación ",
        "SYNESIS para cargar en un GPT con límite de archivos (~20). ",
        "Los documentos fuente en `docs_synesis/` permanecen intactos y son la ",
        "**fuente de verdad primaria**.",
        "",
        "## Uso",
        "",
        "### 1. Regenerar el paquete",
        "",
        "Desde la raíz del repositorio:",
        "",
        "```bash",
        "python3 scripts/build_synesis_gpt_knowledge.py",
        "```",
        "",
        "### 2. Revisar el manifest",
        "",
        "- `MANIFEST.json` — auditoría machine-readable (hashes, fuentes, cobertura).",
        "- `MANIFEST.md` — resumen legible.",
        "",
        "### 2.1 Campos de trazabilidad en el manifest",
        "",
        "| Campo | Significado |",
        "|-------|-------------|",
        "| `all_missing_sources` | Rutas **esperadas** por el mapeo del script pero **no encontradas** en disco (`missing`). |",
        "| `unassigned_sources` | Archivos `.md` **existentes** bajo `docs_synesis/` que **no** fueron incluidos en ningún `SYNESIS_*.md`. |",
        "",
        "Un archivo puede existir y no estar en `missing` si nunca fue listado en el mapeo; ",
        "eso aparece en `unassigned_sources`. Objetivo: lista vacía = cobertura completa.",
        "",
        "### 3. Subir al GPT",
        "",
        "Subir **solo** los archivos consolidados:",
        "",
    ]

    for entry in consolidated:
        lines.append(f"- `{entry['file']}` ({entry['source_count_included']} fuentes incluidas)")

    lines.extend(
        [
            "",
            "Opcional: incluir este `README.md` como contexto operativo.",
            "",
            "**No subir** `MANIFEST.json` salvo que el GPT deba auditar procedencia.",
            "",
            "### 4. Mantener SoT real",
            "",
            "- Editar siempre `docs_synesis/` (documentos fuente).",
            "- Regenerar este paquete después de cambios relevantes.",
            "- Ante conflicto doc ↔ código, prevalece el **código**; reportar conflicto.",
            "",
            "## Archivos generados",
            "",
            f"| Archivo | Fuentes incluidas | Faltantes | Bytes |",
            f"|---------|-------------------|-----------|-------|",
        ]
    )

    for entry in consolidated:
        lines.append(
            f"| `{entry['file']}` | {entry['source_count_included']} | "
            f"{entry['source_count_missing']} | {entry['size_bytes']:,} |"
        )

    lines.extend(
        [
            "",
            "## Trazabilidad de fuentes",
            "",
            "### Fuentes faltantes (`all_missing_sources`)",
            "",
            "Esperadas por el script pero no encontradas en disco.",
            "",
        ]
    )
    if missing:
        for path in missing:
            lines.append(f"- `{path}`")
    else:
        lines.append("- _(ninguna)_")

    lines.extend(
        [
            "",
            "### Fuentes sin asignar (`unassigned_sources`)",
            "",
            "Existen en `docs_synesis/` pero no están en ningún consolidado.",
            "",
        ]
    )
    if unassigned:
        for path in unassigned:
            lines.append(f"- `{path}`")
    else:
        lines.append("- _(ninguna — cobertura completa)_")

    if warnings:
        lines.extend(["", "## Advertencias", ""])
        for warning in warnings:
            lines.append(f"- {warning}")

    lines.append("")
    return "\n".join(lines)


def build_manifest_md(manifest: dict[str, Any]) -> str:
    lines = [
        "# MANIFEST — SYNESIS GPT Knowledge",
        "",
        f"**Generado:** {manifest['generated_at']}",
        "",
        DERIVED_WARNING,
        "",
    ]

    for entry in manifest["consolidated_files"]:
        lines.extend(
            [
                f"## `{entry['file']}`",
                "",
                f"- **SHA256 consolidado:** `{entry['sha256']}`",
                f"- **Tamaño:** {entry['size_bytes']:,} bytes",
                f"- **Caracteres:** {entry['char_count']:,}",
                "",
                "### Fuentes incluidas",
                "",
            ]
        )
        if entry["sources_included"]:
            for src in entry["sources_included"]:
                lines.append(
                    f"- `{src['path']}` — {src['size_bytes']:,} bytes, "
                    f"sha256 `{src['sha256']}`"
                )
        else:
            lines.append("- _(ninguna)_")

        if entry["sources_missing"]:
            lines.extend(["", "### Fuentes faltantes", ""])
            for path in entry["sources_missing"]:
                lines.append(f"- `{path}` — **missing**")

        lines.append("")

    lines.extend(
        [
            "## Trazabilidad global",
            "",
            "### `all_missing_sources` — esperadas pero no encontradas",
            "",
        ]
    )
    if manifest.get("all_missing_sources"):
        for path in manifest["all_missing_sources"]:
            lines.append(f"- `{path}` — **missing**")
    else:
        lines.append("- _(ninguna)_")

    lines.extend(
        [
            "",
            "### `unassigned_sources` — existentes pero no consolidadas",
            "",
        ]
    )
    if manifest.get("unassigned_sources"):
        for path in manifest["unassigned_sources"]:
            lines.append(f"- `{path}` — **unassigned**")
    else:
        lines.append("- _(ninguna — cobertura completa)_")

    excluded = manifest.get("explicit_exclude_from_coverage", [])
    if excluded:
        lines.extend(["", "### Excluidos del escaneo (patrón documentado)", ""])
        for item in excluded:
            lines.append(f"- `{item['path']}` — {item['reason']}")

    if manifest.get("warnings"):
        lines.extend(["## Advertencias", ""])
        for warning in manifest["warnings"]:
            lines.append(f"- {warning}")

    lines.append("")
    return "\n".join(lines)


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    packages = package_definitions()
    consolidated_files: list[dict[str, Any]] = []
    all_missing: set[str] = set()
    warnings: list[str] = []

    critical_sources = {
        "docs_synesis/DOC_MAPA_SISTEMA.md",
        "docs_synesis/DOC_REGLAS_NEGOCIO.md",
        "docs_synesis/DOC_MODELOS_DB.md",
        "docs_synesis/DOC_API_ENDPOINTS.md",
    }

    for output_name, source_paths in packages:
        body, meta = build_consolidated(output_name, source_paths)
        out_path = OUTPUT_DIR / output_name
        out_path.write_text(body, encoding="utf-8")
        consolidated_files.append(meta)
        all_missing.update(meta["sources_missing"])

        if meta["source_count_included"] == 0:
            warnings.append(
                f"{output_name}: ninguna fuente incluida; archivo generado vacío."
            )
        elif meta["sources_missing"]:
            warnings.append(
                f"{output_name}: faltan {meta['source_count_missing']} fuente(s): "
                + ", ".join(meta["sources_missing"])
            )

    missing_critical = sorted(all_missing & critical_sources)
    if missing_critical:
        warnings.insert(
            0,
            "CRÍTICO: faltan documentos fundamentales: "
            + ", ".join(missing_critical),
        )

    unassigned_sources = compute_unassigned_sources(packages)
    if unassigned_sources:
        warnings.append(
            "COBERTURA: "
            f"{len(unassigned_sources)} archivo(s) .md en docs_synesis/ sin asignar: "
            + ", ".join(unassigned_sources)
        )

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    manifest: dict[str, Any] = {
        "generated_at": generated_at,
        "generator": "scripts/build_synesis_gpt_knowledge.py",
        "output_directory": relative_posix(OUTPUT_DIR),
        "warning": DERIVED_WARNING,
        "consolidated_files": consolidated_files,
        "all_missing_sources": sorted(all_missing),
        "unassigned_sources": unassigned_sources,
        "explicit_exclude_from_coverage": [
            {"path": path, "reason": "documented opt-out in script"}
            for path in sorted(EXPLICIT_EXCLUDE_FROM_COVERAGE)
        ],
        "coverage": {
            "docs_synesis_markdown_total": len(discover_docs_synesis_markdown()),
            "assigned_unique": len(assigned_sources_from_packages(packages)),
            "missing_count": len(all_missing),
            "unassigned_count": len(unassigned_sources),
            "complete": len(unassigned_sources) == 0 and len(all_missing) == 0,
        },
        "warnings": warnings,
        "totals": {
            "consolidated_file_count": len(consolidated_files),
            "sources_included": sum(
                e["source_count_included"] for e in consolidated_files
            ),
            "sources_missing": len(all_missing),
            "sources_unassigned": len(unassigned_sources),
            "total_output_bytes": sum(e["size_bytes"] for e in consolidated_files),
        },
    }

    manifest_json_path = OUTPUT_DIR / "MANIFEST.json"
    manifest_json_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    readme_path = OUTPUT_DIR / "README.md"
    readme_path.write_text(build_readme(manifest), encoding="utf-8")

    manifest_md_path = OUTPUT_DIR / "MANIFEST.md"
    manifest_md_path.write_text(build_manifest_md(manifest), encoding="utf-8")

    print("=" * 72)
    print("SYNESIS GPT Knowledge — build completado")
    print("=" * 72)
    print(f"Generado: {generated_at}")
    print(f"Directorio: {OUTPUT_DIR}")
    print()
    print("Archivos creados/actualizados:")
    for entry in consolidated_files:
        status = "OK"
        if entry["sources_missing"]:
            status = f"PARCIAL ({entry['source_count_missing']} faltante(s))"
        print(
            f"  - {entry['file']}: {entry['source_count_included']} fuentes, "
            f"{entry['size_bytes']:,} bytes [{status}]"
        )
    print(f"  - README.md")
    print(f"  - MANIFEST.json")
    print(f"  - MANIFEST.md")
    print()
    print(
        f"Totales: {manifest['totals']['consolidated_file_count']} consolidados, "
        f"{manifest['totals']['sources_included']} fuentes incluidas, "
        f"{manifest['totals']['sources_missing']} rutas faltantes, "
        f"{manifest['totals']['sources_unassigned']} sin asignar, "
        f"{manifest['totals']['total_output_bytes']:,} bytes output"
    )
    print(
        f"Cobertura docs_synesis/: "
        f"{'COMPLETA' if manifest['coverage']['complete'] else 'INCOMPLETA'}"
    )

    if all_missing:
        print()
        print("Fuentes faltantes (all_missing_sources):")
        for path in sorted(all_missing):
            print(f"  - {path}")

    print()
    print("Fuentes sin asignar (unassigned_sources):")
    if unassigned_sources:
        for path in unassigned_sources:
            print(f"  - {path}")
    else:
        print("  (ninguna — cobertura completa)")

    if warnings:
        print()
        print("Advertencias:")
        for warning in warnings:
            print(f"  ! {warning}")

    print()
    print("Regenerar:")
    print("  python3 scripts/build_synesis_gpt_knowledge.py")
    print()
    print(DERIVED_WARNING)

    return 0


if __name__ == "__main__":
    sys.exit(main())
