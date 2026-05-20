"""Generate an animated GIF demo of Copilot Project Memory commands using Pillow."""
from PIL import Image, ImageDraw, ImageFont
import os

W, H = 700, 520
BG = (40, 42, 54)
FG = (248, 248, 242)
GREEN = (80, 250, 123)
YELLOW = (241, 250, 140)
CYAN = (139, 233, 253)
PURPLE = (189, 147, 249)
ORANGE = (255, 184, 108)
DIM = (98, 114, 164)
TITLE_BG = (30, 31, 41)

# Try to find a monospace font
FONT_CANDIDATES = [
    "C:/Windows/Fonts/consola.ttf",
    "C:/Windows/Fonts/cour.ttf",
    "C:/Windows/Fonts/lucon.ttf",
]
font_path = None
for fp in FONT_CANDIDATES:
    if os.path.exists(fp):
        font_path = fp
        break

font = ImageFont.truetype(font_path, 14) if font_path else ImageFont.load_default()
font_bold = ImageFont.truetype(font_path.replace(".ttf", "b.ttf"), 14) if font_path else font
font_title = ImageFont.truetype(font_path, 12) if font_path else font

PAD_X, PAD_Y = 16, 48
LINE_H = 20

# Define the demo script as (delay_ms, lines_to_show)
# Each entry: (text, color, bold)
script = [
    # Scene 1: prompt + :status
    [("$ :status", CYAN, False)],
    # :status output
    [("$ :status", CYAN, False),
     ("", None, False),
     ("Project Memory -- my-api", YELLOW, True),
     ("------------------------------------", DIM, False),
     ("  Stack: Node.js, Express, TypeScript", FG, False),
     ("  Rules: 4 (3 do, 1 don't)", FG, False),
     ("  Prefs: language=typescript, indent=2", FG, False),
     ("  Sessions: 12 saved", FG, False),
     ('  Last: 2h ago -- "Added rate limiting"', FG, False)],

    # Scene 2: prompt + :resume
    [("$ :status", CYAN, False),
     ("", None, False),
     ("Project Memory -- my-api", YELLOW, True),
     ("------------------------------------", DIM, False),
     ("  Stack: Node.js, Express, TypeScript", FG, False),
     ("  Rules: 4 (3 do, 1 don't)", FG, False),
     ("  Prefs: language=typescript, indent=2", FG, False),
     ("  Sessions: 12 saved", FG, False),
     ('  Last: 2h ago -- "Added rate limiting"', FG, False),
     ("", None, False),
     ("$ :resume", CYAN, False)],

    # :resume output
    [("$ :status", CYAN, False),
     ("", None, False),
     ("Project Memory -- my-api", YELLOW, True),
     ("------------------------------------", DIM, False),
     ("  Stack: Node.js, Express, TypeScript", FG, False),
     ("  Rules: 4 (3 do, 1 don't)", FG, False),
     ("  Prefs: language=typescript, indent=2", FG, False),
     ("  Sessions: 12 saved", FG, False),
     ('  Last: 2h ago -- "Added rate limiting"', FG, False),
     ("", None, False),
     ("$ :resume", CYAN, False),
     ("", None, False),
     ("[+] Resuming last session...", GREEN, True),
     ("    Summary: Added rate limiting to auth endpoints", FG, False),
     ("    Files: src/auth/middleware.ts, src/api/routes.ts", FG, False),
     ("    Decision: Use sliding window algorithm", FG, False)],

    # Scene 3: :remember
    [("$ :remember Never use any type", CYAN, False)],
    [("$ :remember Never use any type", CYAN, False),
     ("", None, False),
     ('[OK] Remembered: "Never use any type"', GREEN, True),
     ("     Scope: project  |  Shared: yes", DIM, False)],

    # Scene 4: another remember
    [("$ :remember Never use any type", CYAN, False),
     ("", None, False),
     ('[OK] Remembered: "Never use any type"', GREEN, True),
     ("     Scope: project  |  Shared: yes", DIM, False),
     ("", None, False),
     ("$ :remember Always validate inputs with Zod", CYAN, False)],
    [("$ :remember Never use any type", CYAN, False),
     ("", None, False),
     ('[OK] Remembered: "Never use any type"', GREEN, True),
     ("     Scope: project  |  Shared: yes", DIM, False),
     ("", None, False),
     ("$ :remember Always validate inputs with Zod", CYAN, False),
     ("", None, False),
     ('[OK] Remembered: "Always validate inputs with Zod"', GREEN, True),
     ("     Scope: project  |  Shared: yes", DIM, False)],

    # Final
    [("$ :remember Never use any type", CYAN, False),
     ("", None, False),
     ('[OK] Remembered: "Never use any type"', GREEN, True),
     ("     Scope: project  |  Shared: yes", DIM, False),
     ("", None, False),
     ("$ :remember Always validate inputs with Zod", CYAN, False),
     ("", None, False),
     ('[OK] Remembered: "Always validate inputs with Zod"', GREEN, True),
     ("     Scope: project  |  Shared: yes", DIM, False),
     ("", None, False),
     ("Next session -- Copilot already knows your rules.", ORANGE, True)],
]

# Frame durations in ms
durations = [1200, 3000, 1200, 3000, 1200, 2500, 1200, 2500, 3500]


def draw_frame(scene_lines):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # Title bar
    draw.rectangle([0, 0, W, 32], fill=TITLE_BG)
    draw.ellipse([10, 10, 22, 22], fill=(255, 85, 85))
    draw.ellipse([28, 10, 40, 22], fill=(241, 250, 140))
    draw.ellipse([46, 10, 58, 22], fill=(80, 250, 123))
    try:
        draw.text((W // 2, 10), "Copilot CLI — Project Memory Demo", fill=DIM, font=font_title, anchor="mt")
    except Exception:
        draw.text((W // 2 - 100, 10), "Copilot CLI — Project Memory Demo", fill=DIM, font=font_title)

    y = PAD_Y
    for text, color, bold in scene_lines:
        if text == "":
            y += LINE_H // 2
            continue
        f = font_bold if bold else font
        # Handle emoji/special chars gracefully
        try:
            draw.text((PAD_X, y), text, fill=color, font=f)
        except Exception:
            # Fallback: strip problematic chars
            clean = text.encode("ascii", "replace").decode()
            draw.text((PAD_X, y), clean, fill=color, font=f)
        y += LINE_H

    return img


frames = [draw_frame(scene) for scene in script]

# Add a blank "reset" frame at the end
frames.append(draw_frame([]))
durations.append(1500)

output_path = r"C:\Repo\copilot-project-memory-clean\demo.gif"
frames[0].save(
    output_path,
    save_all=True,
    append_images=frames[1:],
    duration=durations,
    loop=0,
    optimize=True,
)

size_kb = os.path.getsize(output_path) / 1024
print(f"Generated demo.gif ({size_kb:.0f} KB, {len(frames)} frames)")
