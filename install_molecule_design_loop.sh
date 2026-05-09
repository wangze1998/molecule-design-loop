#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CODEX_HOME_DIR="${CODEX_HOME:-$HOME/.codex}"
SKILLS_DIR="$CODEX_HOME_DIR/skills"
INSTALL_RESEARCH_LIT=0

if [[ "${1:-}" == "--install-research-lit" ]]; then
  INSTALL_RESEARCH_LIT=1
fi

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
  printf 'Installed %s\n' "$dest"
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

cat <<'EOF'

Restart Codex or open a new session to pick up the installed skill.
EOF
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CODEX_HOME_DIR="${CODEX_HOME:-$HOME/.codex}"
SKILLS_DIR="$CODEX_HOME_DIR/skills"
INSTALL_RESEARCH_LIT=0

if [[ "${1:-}" == "--install-research-lit" ]]; then
  INSTALL_RESEARCH_LIT=1
fi

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
  printf 'Installed %s\n' "$dest"
}

copy_skill "$SCRIPT_DIR/molecule-design-loop" "$SKILLS_DIR/molecule-design-loop"

if [[ "$INSTALL_RESEARCH_LIT" -eq 1 ]]; then
  backup_if_exists "$SKILLS_DIR/research-lit"
  mkdir -p "$SKILLS_DIR/research-lit"
  cp "$SCRIPT_DIR/optional-skills/research-lit.SKILL.md" "$SKILLS_DIR/research-lit/SKILL.md"
  printf 'Installed %s\n' "$SKILLS_DIR/research-lit"
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

cat <<'EOF'

Restart Codex or open a new session to pick up the installed skill.
EOF
