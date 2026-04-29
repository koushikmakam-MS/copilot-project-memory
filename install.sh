#!/usr/bin/env bash
#
# One-time installer for Copilot Project Memory skill.
# Run once on any machine — works forever after.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/koushikmakam-MS/copilot-project-memory/main/install.sh | bash
#
set -euo pipefail

FORCE="${FORCE:-false}"
COPILOT_DIR="$HOME/.copilot"
MEMORY_DIR="$COPILOT_DIR/project-memory"
GLOBAL_DIR="$MEMORY_DIR/_global"
TEMPLATE_DIR="$MEMORY_DIR/_template"
INSTRUCTIONS_FILE="$COPILOT_DIR/copilot-instructions.md"

echo ""
echo "  📂 Copilot Project Memory — Installer"
echo "  ======================================="
echo ""

# --- Step 1: Create directory structure ---
echo "  [1/4] Creating directory structure..."

for dir in "$MEMORY_DIR" "$GLOBAL_DIR" "$GLOBAL_DIR/sessions" "$GLOBAL_DIR/snippets" "$TEMPLATE_DIR"; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        echo "    ✅ Created: $dir"
    else
        echo "    ⏭️  Exists:  $dir"
    fi
done

# --- Step 2: Create global memory template files ---
echo "  [2/4] Setting up global memory files..."

if [ ! -f "$GLOBAL_DIR/preferences.yml" ] || [ "$FORCE" = "true" ]; then
cat > "$GLOBAL_DIR/preferences.yml" << 'PREFS'
# Global Preferences (apply to all projects unless overridden)
# These are YOUR personal defaults.

# language: typescript
# tone: concise
# style:
#   indent: 2
#   quotes: single
PREFS
    echo "    ✅ Created: preferences.yml"
fi

if [ ! -f "$GLOBAL_DIR/rules.yml" ] || [ "$FORCE" = "true" ]; then
cat > "$GLOBAL_DIR/rules.yml" << 'RULES'
# Global Rules (apply to all projects unless overridden)
# Format:
#   - type: do|dont
#     description: "What to always/never do"
#     learned_from: "how this was learned"

rules: []
RULES
    echo "    ✅ Created: rules.yml"
fi

if [ ! -f "$GLOBAL_DIR/snippets/README.md" ] || [ "$FORCE" = "true" ]; then
cat > "$GLOBAL_DIR/snippets/README.md" << 'SNIP'
# Snippets
Save reusable code patterns here as `.md` files.
Each file should contain a code block and a short description.
SNIP
fi

# --- Step 3: Create project template ---
echo "  [3/4] Setting up project template..."

cat > "$TEMPLATE_DIR/preferences.yml" << 'EOF'
# Project preferences (override global preferences)
# language: python
# framework: django
# package_manager: pip
# test_runner: pytest
EOF

cat > "$TEMPLATE_DIR/rules.yml" << 'EOF'
# Project rules (in addition to global rules)
# Project rules win over global rules when they conflict.
rules: []
EOF

cat > "$TEMPLATE_DIR/context.yml" << 'EOF'
# Project context — auto-detected on first open, editable anytime.
name: ""
description: ""
stack: []
key_files: []
notes: ""
EOF

cat > "$TEMPLATE_DIR/extensions.yml" << 'EOF'
# IDE Extensions for this project
extensions: []
EOF

echo "    ✅ Created project template"

# --- Step 4: Install master instructions ---
echo "  [4/4] Installing master instructions..."

# Try to read from co-located file first
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MASTER_PROMPT_FILE="$SCRIPT_DIR/copilot-instructions.md"

if [ -f "$MASTER_PROMPT_FILE" ]; then
    MASTER_PROMPT=$(cat "$MASTER_PROMPT_FILE")
else
    # Inline the prompt (same content as the .md file)
    MASTER_PROMPT=$(cat << 'PROMPT'

<!-- PROJECT MEMORY SKILL — Do not edit this section manually -->
<!-- Installed by copilot-project-memory. See: ~/.copilot/project-memory/ -->

## Project Memory System

You have access to a persistent project memory system stored at ~/.copilot/project-memory/.

### On Every Session Start
1. Determine the current working directory.
2. Check if a project memory folder exists for this directory in ~/.copilot/project-memory/.
3. If memory exists, load all YAML files and offer to resume last session.
4. If no memory exists, auto-detect stack and create from template.

### Auto-Save on Exit
Before ending ANY session, silently save a session summary with: what was discussed, files changed, decisions made, learnings.

### Commands
- /memory status|prefs|rules|context|extensions|sessions|snippets|export|export-team|backup|restore|reset|stats
- /remember <instruction> — Quick-add a rule
- /forget <rule-id> — Remove a rule

See full command reference at: https://github.com/koushikmakam-MS/copilot-project-memory

<!-- END PROJECT MEMORY SKILL -->
PROMPT
)
fi

if [ -f "$INSTRUCTIONS_FILE" ]; then
    if grep -q "PROJECT MEMORY SKILL" "$INSTRUCTIONS_FILE"; then
        if [ "$FORCE" = "true" ]; then
            # Use perl for multiline replace
            perl -i -0pe "s/<!-- PROJECT MEMORY SKILL.*?<!-- END PROJECT MEMORY SKILL -->/$(echo "$MASTER_PROMPT" | sed 's/[&/\]/\\&/g')/s" "$INSTRUCTIONS_FILE"
            echo "    ✅ Updated master instructions (FORCE=true)"
        else
            echo "    ⏭️  Already installed. Use FORCE=true to overwrite."
        fi
    else
        echo "" >> "$INSTRUCTIONS_FILE"
        echo "$MASTER_PROMPT" >> "$INSTRUCTIONS_FILE"
        echo "    ✅ Appended to existing copilot-instructions.md"
    fi
else
    echo "$MASTER_PROMPT" > "$INSTRUCTIONS_FILE"
    echo "    ✅ Created copilot-instructions.md"
fi

echo ""
echo "  🎉 Installation complete!"
echo ""
echo "  Memory location:  $MEMORY_DIR"
echo "  Instructions:     $INSTRUCTIONS_FILE"
echo ""
echo "  Just open Copilot in any project folder — it will auto-detect"
echo "  and start building memory. No further setup needed."
echo ""
