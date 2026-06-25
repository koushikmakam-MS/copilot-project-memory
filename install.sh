#!/usr/bin/env bash
#
# One-time installer for Copilot Project Memory skill.
# Run once on any machine — works forever after.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/KoushikMakam/copilot-project-memory/main/install.sh | bash
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

if [ ! -f "$GLOBAL_DIR/preferences.yml" ]; then
cat > "$GLOBAL_DIR/preferences.yml" << 'PREFS'
schema_version: 1

# Global Preferences (apply to all projects unless overridden)
# These are YOUR personal defaults.

# language: typescript
# tone: concise
# style:
#   indent: 2
#   quotes: single
PREFS
    echo "    ✅ Created: preferences.yml"
elif [ "$FORCE" = "true" ]; then
    cp "$GLOBAL_DIR/preferences.yml" "$GLOBAL_DIR/preferences.yml.bak"
    echo "    ⏭️  Backed up existing preferences.yml → preferences.yml.bak"
fi

if [ ! -f "$GLOBAL_DIR/rules.yml" ]; then
cat > "$GLOBAL_DIR/rules.yml" << 'RULES'
schema_version: 1

# Global Rules (apply to all projects unless overridden)
# Format:
#   - type: do|dont
#     description: "What to always/never do"
#     learned_from: "how this was learned"

rules: []
RULES
    echo "    ✅ Created: rules.yml"
elif [ "$FORCE" = "true" ]; then
    cp "$GLOBAL_DIR/rules.yml" "$GLOBAL_DIR/rules.yml.bak"
    echo "    ⏭️  Backed up existing rules.yml → rules.yml.bak"
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
schema_version: 1

# Project preferences (override global preferences)
# language: python
# framework: django
# package_manager: pip
# test_runner: pytest
EOF

cat > "$TEMPLATE_DIR/rules.yml" << 'EOF'
schema_version: 1

# Project rules (in addition to global rules)
# Project rules win over global rules when they conflict.
rules: []
EOF

cat > "$TEMPLATE_DIR/context.yml" << 'EOF'
schema_version: 1

# Project context — auto-detected on first open, editable anytime.
name: ""
description: ""
stack: []
key_files: []
notes: ""
EOF

cat > "$TEMPLATE_DIR/extensions.yml" << 'EOF'
schema_version: 1

# IDE Extensions for this project
extensions: []
EOF

echo "    ✅ Created project template"

# --- Step 4: Install master instructions ---
echo "  [4/5] Installing master instructions..."

# Try to read from co-located file first (prefer slim prompt)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MASTER_PROMPT_FILE="$SCRIPT_DIR/prompts/copilot-instructions-slim.md"
if [ ! -f "$MASTER_PROMPT_FILE" ]; then
    MASTER_PROMPT_FILE="$SCRIPT_DIR/copilot-instructions.md"
fi

if [ -f "$MASTER_PROMPT_FILE" ]; then
    MASTER_PROMPT=$(cat "$MASTER_PROMPT_FILE")
    echo "    Using: $(basename "$MASTER_PROMPT_FILE")"
else
    echo "    !! No instructions file found in $SCRIPT_DIR" >&2
    echo "       Run installer from the copilot-project-memory repo directory." >&2
    exit 1
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

# --- Step 5: Install bundled tools ---
echo "  [5/5] Installing bundled tools..."

TOOLS_DIR="$SCRIPT_DIR/tools"
if [ -d "$TOOLS_DIR" ]; then
    FOUND_TOOLS=0
    for tool_dir in "$TOOLS_DIR"/*/; do
        if [ -f "${tool_dir}pyproject.toml" ]; then
            FOUND_TOOLS=1
            tool_name=$(basename "$tool_dir")
            printf "    Installing %s..." "$tool_name"

            if command -v python3 &>/dev/null; then
                PIP_CMD="python3 -m pip"
            elif command -v python &>/dev/null; then
                PIP_CMD="python -m pip"
            else
                PIP_CMD=""
            fi

            if [ -n "$PIP_CMD" ]; then
                if $PIP_CMD install --quiet "$tool_dir" 2>/dev/null; then
                    echo " OK"
                else
                    echo " WARN (check: pip install $tool_dir)"
                fi
            else
                echo " SKIP (pip not found)"
            fi
        fi
    done
    if [ "$FOUND_TOOLS" -eq 0 ]; then
        echo "    -- No tools with pyproject.toml found"
    fi
else
    echo "    -- No tools/ directory found"
fi

# --- Step 6: Set up auto-permissions ---
echo ""
echo "  [Bonus] Setting up auto-permissions..."

# Approach 1: Add shell alias wrapping 'gh copilot' with --add-dir
ALIAS_BLOCK='
# --- Copilot Project Memory: auto-grant memory path access ---
ghc() { gh copilot -- --add-dir "$HOME/.copilot/project-memory" "$@"; }
# --- End Copilot Project Memory ---'

add_shell_alias() {
    local rcfile="$1"
    if [ -f "$rcfile" ]; then
        if grep -q "Copilot Project Memory" "$rcfile" 2>/dev/null; then
            echo "    ⏭️  Shell alias already in $(basename "$rcfile")"
        else
            echo "$ALIAS_BLOCK" >> "$rcfile"
            echo "    ✅ Added 'ghc' alias to $(basename "$rcfile")"
        fi
    fi
}

# Detect shell and add alias
ALIAS_ADDED=false
if [ -f "$HOME/.zshrc" ]; then
    add_shell_alias "$HOME/.zshrc"
    ALIAS_ADDED=true
fi
if [ -f "$HOME/.bashrc" ]; then
    add_shell_alias "$HOME/.bashrc"
    ALIAS_ADDED=true
fi
if [ -f "$HOME/.bash_profile" ] && [ ! -f "$HOME/.bashrc" ]; then
    add_shell_alias "$HOME/.bash_profile"
    ALIAS_ADDED=true
fi
if [ "$ALIAS_ADDED" = "false" ]; then
    # Create .bashrc if nothing exists
    echo "$ALIAS_BLOCK" >> "$HOME/.bashrc"
    echo "    ✅ Created ~/.bashrc with 'ghc' alias"
fi
echo "       Use 'ghc' instead of 'gh copilot' for auto-permissions"

# Approach 2: Seed permissions-config.json for the current project
PERM_FILE="$COPILOT_DIR/permissions-config.json"
CWD="$(pwd)"
if [ "$CWD" != "$HOME" ] && [ "$CWD" != "/" ]; then
    # Find git root for locationKey
    GIT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "")"
    if [ -n "$GIT_ROOT" ]; then
        LOCATION_KEY="$(cd "$GIT_ROOT" && pwd)"
    else
        LOCATION_KEY="$CWD"
    fi
    
    if command -v python3 &>/dev/null; then
        python3 -c "
import json, os
pf = '$PERM_FILE'
perms = {'locations': {}}
if os.path.exists(pf):
    with open(pf) as f:
        perms = json.load(f)
if 'locations' not in perms:
    perms['locations'] = {}
lk = '$LOCATION_KEY'
mp = '$MEMORY_DIR'
if lk not in perms['locations']:
    perms['locations'][lk] = {}
loc = perms['locations'][lk]
dirs = loc.get('allowed_directories', [])
if mp not in dirs:
    dirs.append(mp)
    loc['allowed_directories'] = dirs
    if 'tool_approvals' not in loc:
        loc['tool_approvals'] = [{'kind': 'read'}, {'kind': 'write'}]
    with open(pf, 'w') as f:
        json.dump(perms, f, indent=2)
    print('    ✅ Granted memory access for: ' + lk)
else:
    print('    ⏭️  Permissions already set')
" 2>/dev/null || echo "    ⚠️  Could not update permissions"
    elif command -v node &>/dev/null; then
        node -e "
const fs = require('fs');
const pf = '$PERM_FILE';
let perms = {locations: {}};
try { perms = JSON.parse(fs.readFileSync(pf, 'utf8')); } catch {}
if (!perms.locations) perms.locations = {};
const lk = '$LOCATION_KEY';
const mp = '$MEMORY_DIR';
if (!perms.locations[lk]) perms.locations[lk] = {};
const loc = perms.locations[lk];
const dirs = loc.allowed_directories || [];
if (!dirs.includes(mp)) {
    dirs.push(mp);
    loc.allowed_directories = dirs;
    if (!loc.tool_approvals) loc.tool_approvals = [{kind:'read'},{kind:'write'}];
    fs.writeFileSync(pf, JSON.stringify(perms, null, 2));
    console.log('    ✅ Granted memory access for: ' + lk);
} else {
    console.log('    ⏭️  Permissions already set');
}
" 2>/dev/null || echo "    ⚠️  Could not update permissions"
    fi
fi

echo ""
echo "  🎉 Installation complete!"
echo ""

# --- Post-install verification ---
echo "  Verifying installation..."

VERIFY_PASSED=true

# Check directory structure
if [ -d "$MEMORY_DIR" ]; then
    echo "    ✅ Memory directory exists"
else
    echo "    ❌ Memory directory missing: $MEMORY_DIR"
    VERIFY_PASSED=false
fi

# Check instructions file
if [ -f "$INSTRUCTIONS_FILE" ] && grep -q "PROJECT MEMORY SKILL" "$INSTRUCTIONS_FILE"; then
    echo "    ✅ Instructions file installed"
else
    echo "    ❌ Instructions file missing or incomplete"
    VERIFY_PASSED=false
fi

# Check CLI tools
if command -v copilot-memory &>/dev/null; then
    echo "    ✅ copilot-memory CLI available"
else
    echo "    ⚠️  copilot-memory CLI not found (Python tools optional)"
fi

if command -v pipeline &>/dev/null; then
    echo "    ✅ pipeline CLI available"
else
    echo "    ⚠️  pipeline CLI not found (Python tools optional)"
fi

if [ "$VERIFY_PASSED" = "true" ]; then
    echo ""
    echo "  ✅ All checks passed!"
else
    echo ""
    echo "  ⚠️  Some checks failed — review the output above"
fi

echo ""
echo "  Two ways to use Copilot with project memory:"
echo "    1. Use 'ghc' (auto-grants memory access for any project)"
echo "    2. Use 'gh copilot' (memory access pre-granted for current project)"
echo ""
echo "  💡 Re-run this installer from any project folder to grant access."
echo ""
