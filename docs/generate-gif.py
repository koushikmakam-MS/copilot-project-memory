"""Generate pipeline demo GIF using Pillow — no browser, no VHS, just Python."""
import io
import sys
import time
from PIL import Image, ImageDraw, ImageFont

# Terminal colors (Dracula theme)
BG = (40, 42, 54)
FG = (248, 248, 242)
GREEN = (80, 250, 123)
RED = (255, 85, 85)
YELLOW = (241, 250, 140)
CYAN = (139, 233, 253)
PURPLE = (189, 147, 249)
ORANGE = (255, 184, 108)
COMMENT = (98, 114, 164)

WIDTH, HEIGHT = 900, 550
PADDING = 20
LINE_HEIGHT = 18
FONT_SIZE = 14

try:
    font = ImageFont.truetype("consola.ttf", FONT_SIZE)
except OSError:
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", FONT_SIZE)
    except OSError:
        font = ImageFont.load_default()


def make_frame(lines):
    """Create a single frame image from colored text lines."""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)
    y = PADDING
    for text, color in lines:
        if y + LINE_HEIGHT > HEIGHT - PADDING:
            break
        draw.text((PADDING, y), text, fill=color, font=font)
        y += LINE_HEIGHT
    return img


# Build frames as sequences of (lines_so_far, duration_ms)
frames_spec = []

def scene(lines, duration_ms=800):
    frames_spec.append((list(lines), duration_ms))

# --- Scene 1: Command typed ---
lines = []
lines.append(("$ copilot> :pipeline Create a calculator with add, subtract, multiply", CYAN))
scene(lines, 1500)

# --- Scene 2: Phase 0 ---
lines.append(("", FG))
lines.append(("=" * 60, PURPLE))
lines.append(("  PHASE 0: PIPELINE ACTIVATED", PURPLE))
lines.append(("=" * 60, PURPLE))
lines.append(("  Trigger: ':pipeline' keyword detected", COMMENT))
lines.append(("  Task: Create a calculator with add, subtract, multiply", FG))
scene(lines, 1200)

# --- Scene 3: Phase 1 ---
lines.append(("", FG))
lines.append(("=" * 60, CYAN))
lines.append(("  PHASE 1: DECOMPOSITION", CYAN))
lines.append(("=" * 60, CYAN))
lines.append(("", FG))
lines.append(("  Step 1: Create calculator.py with functions     [PLANNED]", FG))
lines.append(("  Step 2: Create test_calculator.py               [PLANNED]", FG))
lines.append(("  Step 3: Run tests and verify output              [PLANNED]", FG))
lines.append(("  Step 4: Add docstrings and type hints            [PLANNED]", FG))
scene(lines, 1500)

# --- Scene 4: Phase 1b approval ---
lines.append(("", FG))
lines.append(("  Phase 1b: Plan requires approval...", YELLOW))
lines.append(("  User approved: YES", GREEN))
scene(lines, 1000)

# --- Scene 5: Phase 2 Step 1 ---
lines.append(("", FG))
lines.append(("=" * 60, GREEN))
lines.append(("  PHASE 2: EXECUTION", GREEN))
lines.append(("=" * 60, GREEN))
lines.append(("", FG))
lines.append(("  Step 1: Create calculator.py with functions", FG))
lines.append(("    Creating file... done", GREEN))
lines.append(("    Post-check: calculator.py exists? YES", GREEN))
scene(lines, 1000)

# --- Scene 6: Step 1 VERIFY (the key part!) ---
lines.append(("", FG))
lines.append(("  VERIFY: aipipeline verify --step step-1", YELLOW))
lines.append(("    [PASS] step-1: calculator.py exists", GREEN))
lines.append(("    Verdict: PASSED", GREEN))
scene(lines, 1500)

# --- Scene 7: Step 2 ---
lines.append(("", FG))
lines.append(("  Step 2: Create test_calculator.py", FG))
lines.append(("    Creating test file... done", GREEN))
lines.append(("    Post-check: test file exists? YES", GREEN))
lines.append(("  VERIFY: aipipeline verify --step step-2", YELLOW))
lines.append(("    [PASS] step-2: test file created", GREEN))
scene(lines, 1200)

# --- Scene 8: Step 3 ---
lines.append(("", FG))
lines.append(("  Step 3: Run tests and verify output", FG))
lines.append(("    Running pytest... 4 passed", GREEN))
lines.append(("  VERIFY: aipipeline verify --step step-3", YELLOW))
lines.append(("    [PASS] step-3: all tests passing", GREEN))
scene(lines, 1200)

# Clear and continue (screen is getting full)
lines_page2 = []
lines_page2.append(("  Step 4: Add docstrings and type hints", FG))
lines_page2.append(("    Adding type hints... done", GREEN))
lines_page2.append(("  VERIFY: aipipeline verify --step step-4", YELLOW))
lines_page2.append(("    [PASS] step-4: docstrings added", GREEN))
scene(lines_page2, 1200)

# --- Scene 9: Phase 3 Report ---
lines_page2.append(("", FG))
lines_page2.append(("=" * 60, ORANGE))
lines_page2.append(("  PHASE 3: COMPLETION REPORT", ORANGE))
lines_page2.append(("=" * 60, ORANGE))
lines_page2.append(("", FG))
lines_page2.append(("  Steps completed: 4/4", GREEN))
lines_page2.append(("  Code verification: 4/4 PASSED", GREEN))
lines_page2.append(("  Files created: calculator.py, test_calculator.py", FG))
scene(lines_page2, 1500)

# --- Scene 10: Phase 4 Validation ---
lines_page2.append(("", FG))
lines_page2.append(("=" * 60, PURPLE))
lines_page2.append(("  PHASE 4: FINAL VALIDATION", PURPLE))
lines_page2.append(("=" * 60, PURPLE))
lines_page2.append(("", FG))
lines_page2.append(("  4a: aipipeline verify plan.yaml", YELLOW))
lines_page2.append(("      Result: 4/4 steps PASSED", GREEN))
lines_page2.append(("  4b: Rubber-duck review: No issues found", GREEN))
lines_page2.append(("", FG))
lines_page2.append(("  === PIPELINE COMPLETE ===", GREEN))
lines_page2.append(("  All 4 enforcement layers passed.", GREEN))
scene(lines_page2, 2000)

# --- Scene 11: Failure example ---
fail_lines = []
fail_lines.append(("", FG))
fail_lines.append(("--- What happens when a step FAILS ---", RED))
fail_lines.append(("", FG))
fail_lines.append(("  Step 2: Create test_calculator.py", FG))
fail_lines.append(("    Creating test file... done", GREEN))
fail_lines.append(("  VERIFY: aipipeline verify --step step-2", YELLOW))
fail_lines.append(("    [FAIL] step-2: test file not found!", RED))
fail_lines.append(("    Verdict: FAILED", RED))
fail_lines.append(("", FG))
fail_lines.append(("  >>> BLOCKED: Cannot proceed to Step 3", RED))
fail_lines.append(("  >>> AI must fix Step 2 before continuing", RED))
fail_lines.append(("", FG))
fail_lines.append(("  The code catches what instructions miss.", YELLOW))
scene(fail_lines, 3000)

# Generate GIF
print("Generating frames...")
images = []
durations = []
for lines_data, dur in frames_spec:
    img = make_frame(lines_data)
    images.append(img)
    durations.append(dur)

output_path = "docs/pipeline-demo.gif"
images[0].save(
    output_path,
    save_all=True,
    append_images=images[1:],
    duration=durations,
    loop=0,
    optimize=True,
)

import os
size_kb = os.path.getsize(output_path) / 1024
print(f"Done! Saved to {output_path} ({size_kb:.0f} KB, {len(images)} frames)")
