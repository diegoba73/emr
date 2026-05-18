#!/usr/bin/env bash
# Checkpoints: commit + tag incremental (checkpoint-1, checkpoint-2, ...).
# Uso: scripts/checkpoint.sh <checkpoint|volver|last|listar>

set -euo pipefail
cd "$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "No es un repositorio git." >&2; exit 1; }

prefix="checkpoint-"

list_checkpoints() {
  git tag -l "${prefix}*" 2>/dev/null | sort -V
}

last_tag() {
  list_checkpoints | tail -1
}

cmd="${1:-}"

case "$cmd" in
  listar|list)
    list_checkpoints
    ;;
  last|ultimo|último)
    t="$(last_tag)"
    if [ -z "$t" ]; then
      echo "No hay tags ${prefix}*." >&2
      exit 1
    fi
    echo "$t"
    ;;
  checkpoint|save|crear)
    git add -A
    if git diff --cached --quiet; then
      echo "Nada que commitear (índice vacío tras git add -A)."
      exit 0
    fi
    last="$(last_tag)"
    if [ -z "$last" ]; then
      n=1
    else
      n="${last#$prefix}"
      n=$((n + 1))
    fi
    tag="${prefix}${n}"
    if git tag -l "$tag" | grep -q .; then
      echo "El tag $tag ya existe. Aborto." >&2
      exit 1
    fi
    git commit -m "checkpoint: ${tag}"
    git tag -a "$tag" -m "Checkpoint ${n}"
    echo "Creado: $tag (commit $(git rev-parse --short HEAD))"
    ;;
  volver|restore|reset)
    t="$(last_tag)"
    if [ -z "$t" ]; then
      echo "No hay ningún tag ${prefix}* para volver." >&2
      exit 1
    fi
    if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
      echo "ADVERTENCIA: Hay cambios sin commitear; reset --hard los descarta." >&2
    fi
    git reset --hard "$t"
    echo "HEAD en $t ($(git rev-parse --short HEAD))"
    ;;
  *)
    echo "Uso: $0 {checkpoint|volver|last|listar}" >&2
    exit 1
    ;;
esac
