#!/usr/bin/env bash
# Genera el changelog (Markdown) de una versión, agrupando los commits por tipo
# de Conventional Commits.
#
# Uso:  changelog.sh <tag-anterior|ninguno> <commit> <imagen-backend> <imagen-frontend> <version>
set -euo pipefail

previous="$1"
target="$2"
backend_image="${3:-}"
frontend_image="${4:-}"
version="${5:-}"

if [ "$previous" = "ninguno" ]; then
  range="$target"
else
  range="$previous..$target"
fi

section() {
  local title="$1" pattern="$2" lines
  lines="$(git log --format='%s (%h)' "$range" | grep -E "$pattern" || true)"
  if [ -n "$lines" ]; then
    printf '### %s\n\n' "$title"
    printf '%s\n' "$lines" | sed 's/^/- /'
    printf '\n'
  fi
}

section "Cambios incompatibles" '^[a-z]+(\([^)]*\))?!:'
section "Nuevas funcionalidades" '^feat(\([^)]*\))?:'
section "Correcciones" '^fix(\([^)]*\))?:'
section "Pipeline e infraestructura" '^(ci|build|infra)(\([^)]*\))?:'
section "Pruebas" '^test(\([^)]*\))?:'
section "Documentación" '^docs(\([^)]*\))?:'
section "Otros cambios" '^(chore|refactor|perf|style)(\([^)]*\))?:'

others="$(git log --format='%s (%h)' "$range" \
  | grep -Ev '^[a-z]+(\([^)]*\))?!?:' || true)"
if [ -n "$others" ]; then
  printf '### Commits sin prefijo convencional\n\n'
  printf '%s\n' "$others" | sed 's/^/- /'
  printf '\n'
fi

if [ -n "$backend_image" ] && [ -n "$version" ]; then
  printf '### Imágenes Docker de esta versión\n\n'
  printf -- '- `%s:%s`\n' "$backend_image" "${version#v}"
  printf -- '- `%s:%s`\n' "$frontend_image" "${version#v}"
  printf '\nSon las mismas imágenes (mismo digest) que el CI probó y publicó con la etiqueta `%s`.\n' "$(git rev-parse "$target")"
fi
