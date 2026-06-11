"""Pipeline demo script — simulates the full pipeline flow with realistic timing."""
import sys
import time

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

def typed(text, delay=0.02):
    for ch in text:
        print(ch, end="", flush=True)
        time.sleep(delay)
    print()

def fast(text):
    print(text)
    time.sleep(0.3)

def pause(t=0.8):
    time.sleep(t)

# Prompt
print()
typed("❯ :pipeline Create calculator.py with add/subtract, write tests, run them", 0.03)
pause(1)

# Phase 0
fast("\033[96m● 🔄 Pipeline mode activated\033[0m (reason: explicit :pipeline command)")
pause(0.5)

# Phase 1
fast("")
fast("\033[1m═══ PIPELINE PLAN ═══\033[0m")
fast("  Task: Create calculator with tests")
fast("  Steps: 4")
fast("")
pause(0.3)
fast("  1. [\033[96mcheck-python\033[0m]      — Verify Python is installed")
pause(0.2)
fast("  2. [\033[96mcreate-calculator\033[0m] — Create calculator.py with add/subtract")
pause(0.2)
fast("  3. [\033[96mcreate-tests\033[0m]      — Write unit tests")
pause(0.2)
fast("  4. [\033[96mcreate-tests\033[0m]      — Run the tests")
fast("")
fast("\033[1m═══════════════════════\033[0m")
pause(0.5)

fast("")
fast("  ⏳ Approve this plan? → \033[92m✅ Yes\033[0m")
pause(1)

# Step 1
fast("")
fast("\033[1m━━━ STEP [1/4]: check-python ━━━\033[0m")
pause(0.3)
fast("  📋 PRE-CHECK:  (none)")
pause(0.2)
fast("  🔨 EXECUTE:    python --version → Python 3.11.9")
pause(0.3)
fast("  📋 POST-CHECK: \033[92m✅\033[0m exit code 0 (evidence: Python 3.11.9)")
pause(0.3)
fast("  🔍 VERIFY:     aipipeline verify --step check-python → \033[92m✅ PASSED\033[0m")
pause(0.2)
fast("  📊 RESULT:     \033[92m✅ PASSED\033[0m")
pause(0.5)

# Step 2
fast("")
fast("\033[1m━━━ STEP [2/4]: create-calculator ━━━\033[0m")
pause(0.3)
fast("  📋 PRE-CHECK:  \033[92m✅\033[0m check-python completed")
pause(0.2)
fast("  🔨 EXECUTE:    Created calculator.py (add, subtract functions)")
pause(0.4)
fast("  📋 POST-CHECK: \033[92m✅\033[0m file exists, functions verified via AST")
pause(0.3)
fast("  🔍 VERIFY:     aipipeline verify --step create-calculator → \033[92m✅ PASSED\033[0m")
pause(0.2)
fast("  📊 RESULT:     \033[92m✅ PASSED\033[0m")
pause(0.5)

# Step 3
fast("")
fast("\033[1m━━━ STEP [3/4]: create-tests ━━━\033[0m")
pause(0.3)
fast("  📋 PRE-CHECK:  \033[92m✅\033[0m calculator.py exists")
pause(0.2)
fast("  🔨 EXECUTE:    Created test_calculator.py (8 test cases)")
pause(0.4)
fast("  📋 POST-CHECK: \033[92m✅\033[0m TestAdd, TestSubtract classes verified")
pause(0.3)
fast("  🔍 VERIFY:     aipipeline verify --step create-tests → \033[92m✅ PASSED\033[0m")
pause(0.2)
fast("  📊 RESULT:     \033[92m✅ PASSED\033[0m")
pause(0.5)

# Step 4
fast("")
fast("\033[1m━━━ STEP [4/4]: run-tests ━━━\033[0m")
pause(0.3)
fast("  📋 PRE-CHECK:  \033[92m✅\033[0m both files exist")
pause(0.2)
fast("  🔨 EXECUTE:    python -m unittest → 8 tests, all OK")
pause(0.5)
fast("  📋 POST-CHECK: \033[92m✅\033[0m All 8 tests passed (exit code 0)")
pause(0.3)
fast("  🔍 VERIFY:     aipipeline verify --step run-tests → \033[92m✅ PASSED\033[0m")
pause(0.2)
fast("  📊 RESULT:     \033[92m✅ PASSED\033[0m")
pause(0.8)

# Report
fast("")
fast("\033[1m═══ PIPELINE REPORT ═══\033[0m")
fast("")
fast("  Step              Status  Evidence")
fast("  ─────────────────────────────────────────────")
pause(0.2)
fast("  check-python      \033[92m✅ PASS\033[0m  Python 3.11.9")
pause(0.15)
fast("  create-calculator \033[92m✅ PASS\033[0m  add, subtract defined")
pause(0.15)
fast("  create-tests      \033[92m✅ PASS\033[0m  TestAdd, TestSubtract (8 cases)")
pause(0.15)
fast("  run-tests         \033[92m✅ PASS\033[0m  8/8 tests passed")
fast("  ─────────────────────────────────────────────")
fast("  Total: 4 steps | \033[92m✅ 4 passed\033[0m")
fast("  \033[92m✅ Code verified\033[0m | \033[92m✅ AI validated\033[0m")
fast("")
fast("\033[1m═══════════════════════\033[0m")
pause(2)
