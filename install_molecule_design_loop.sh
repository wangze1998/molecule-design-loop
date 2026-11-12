#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CODEX_HOME_DIR="${CODEX_HOME:-$HOME/.codex}"
SKILLS_DIR="$CODEX_HOME_DIR/skills"
INSTALL_RESEARCH_LIT=0
READ_ONLY=0

usage() {
  cat <<'USAGE'
Usage: install_molecule_design_loop.sh [--install-research-lit] [--read-only]

  --install-research-lit  also install the optional research-lit skill
  --read-only             remove write permission from the installed skill files,
                          so a design run cannot edit the rules it is judged by
                          (see references/run-integrity-protocol.md)
USAGE
}

for arg in "$@"; do
  case "$arg" in
    --install-research-lit) INSTALL_RESEARCH_LIT=1 ;;
    --read-only) READ_ONLY=1 ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'Unknown option: %s\n\n' "$arg" >&2; usage >&2; exit 2 ;;
  esac
done

mkdir -p "$SKILLS_DIR"

backup_if_exists() {
  local target="$1"
  if [[ -e "$target" && ! -L "$target" ]]; then
    local backup="${target}.backup.$(date +%Y%m%d-%H%M%S)"
    mv "$target" "$backup"
    printf 'Backed up %s -> %s\n' "$target" "$backup"
  elif [[ -L "$target" ]]; then
    rm "$target"
  fi
}

copy_skill() {
  local src="$1"
  local dest="$2"
  backup_if_exists "$dest"
  mkdir -p "$dest"
  rsync -a --delete --exclude '__pycache__/' "$src/" "$dest/"
  if [[ "$READ_ONLY" -eq 1 ]]; then
    chmod -R a-w "$dest"
    printf 'Installed %s (read-only)\n' "$dest"
  else
    printf 'Installed %s\n' "$dest"
  fi
}

copy_skill "$SCRIPT_DIR/molecule-design-loop" "$SKILLS_DIR/molecule-design-loop"

if [[ "$INSTALL_RESEARCH_LIT" -eq 1 ]]; then
  copy_skill "$SCRIPT_DIR/optional-skills/research-lit" "$SKILLS_DIR/research-lit"
fi

cat <<EOF

Done.
Main skill: $SKILLS_DIR/molecule-design-loop
EOF

if [[ "$INSTALL_RESEARCH_LIT" -eq 1 ]]; then
  cat <<EOF
Optional skill: $SKILLS_DIR/research-lit
EOF
fi

if [[ "$READ_ONLY" -eq 1 ]]; then
  cat <<'EOF'

The installed skill is read-only. Re-running this script replaces it and keeps the old
copy as a backup. To edit the installed copy in place: chmod -R u+w <installed folder>
EOF
fi

cat <<'EOF'

Restart Codex or open a new session to pick up the installed skill.
EOF
