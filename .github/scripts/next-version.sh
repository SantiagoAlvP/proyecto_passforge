#!/usr/bin/env bash
# Calcula la siguiente versión semántica (vMAYOR.MENOR.PARCHE) a partir de los
# mensajes de commit desde el último tag, siguiendo Conventional Commits:
#
#   feat!: ... / fix!: ... / "BREAKING CHANGE:" en el cuerpo  -> MAYOR
#   feat: ...  o  feat(alcance): ...                          -> MENOR
#   cualquier otro commit (fix, docs, ci, chore, sin prefijo) -> PARCHE
#
# Uso:  next-version.sh [commit]      (por defecto HEAD)
# Escribe en stdout:  previous=<tag|ninguno>  next=<vX.Y.Z>  bump=<major|minor|patch|none>
# "bump=none" significa que el commit ya tiene versión: no hay nada que publicar.
set -euo pipefail

target="${1:-HEAD}"

# Último tag de versión alcanzable desde el commit (ignora tags que no sean vX.Y.Z).
previous="$(git describe --tags --abbrev=0 --match 'v[0-9]*.[0-9]*.[0-9]*' "$target" 2>/dev/null || true)"

if [ -n "$previous" ] && [ "$(git rev-list -n 1 "$previous")" = "$(git rev-parse "$target")" ]; then
  echo "previous=$previous"
  echo "next=$previous"
  echo "bump=none"
  exit 0
fi

if [ -z "$previous" ]; then
  # Primera versión del proyecto.
  echo "previous=ninguno"
  echo "next=v1.0.0"
  echo "bump=initial"
  exit 0
fi

range="$previous..$target"
subjects="$(git log --format='%s' "$range")"
bodies="$(git log --format='%b' "$range")"

if printf '%s\n' "$subjects" | grep -Eq '^[a-z]+(\([^)]*\))?!:' \
  || printf '%s\n' "$bodies" | grep -q '^BREAKING CHANGE:'; then
  bump=major
elif printf '%s\n' "$subjects" | grep -Eq '^feat(\([^)]*\))?:'; then
  bump=minor
else
  bump=patch
fi

IFS=. read -r major minor patch <<<"${previous#v}"
case "$bump" in
  major) major=$((major + 1)); minor=0; patch=0 ;;
  minor) minor=$((minor + 1)); patch=0 ;;
  patch) patch=$((patch + 1)) ;;
esac

echo "previous=$previous"
echo "next=v$major.$minor.$patch"
echo "bump=$bump"
