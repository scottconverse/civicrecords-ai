#!/usr/bin/env bash
# civicrecords-ai/scripts/verify-release.sh - recovery release gate.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

FAILED=0
pass() { printf '  \033[0;32m[PASS]\033[0m %s\n' "$*"; }
fail() { printf '  \033[0;31m[FAIL]\033[0m %s\n' "$*" >&2; FAILED=1; }
info() { printf '\n\033[1;34m%s\033[0m\n' "$*"; }

PYTHON_CMD=""
if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD="python"
elif command -v py >/dev/null 2>&1; then
    PYTHON_CMD="py -3"
fi

if [ -z "$PYTHON_CMD" ]; then
    fail "python: no python3/python/py executable found on PATH"
fi

info "1. recovery gates"
if [ -n "$PYTHON_CMD" ] && $PYTHON_CMD scripts/verify-recovery-gates.py; then
    pass "recovery gates passed"
else
    fail "recovery gates failed"
fi

info "2. tracked-file secret scan"
if [ -n "$PYTHON_CMD" ] && $PYTHON_CMD scripts/verify-secret-scan.py; then
    pass "secret scan passed"
else
    fail "secret scan failed"
fi

info "3. provision local Compose runtime and verify sovereignty"
if ! command -v docker >/dev/null 2>&1; then
    fail "docker: not installed or not on PATH"
elif [ ! -f .env ]; then
    fail ".env missing; create a local runtime .env from .env.example with real secrets before release verification"
else
    if docker compose up -d --wait postgres redis ollama api; then
        pass "compose runtime provisioned"
    else
        fail "compose runtime failed to become healthy"
        echo ""
        echo "============================================"
        echo "  Container logs (compose health-check failed)"
        echo "============================================"
        echo ""
        echo "## docker compose ps"
        docker compose ps || true
        echo ""
        echo "## docker compose logs --no-color --tail 100 api"
        docker compose logs --no-color --tail 100 api || true
        echo ""
        echo "## docker compose logs --no-color --tail 50 postgres"
        docker compose logs --no-color --tail 50 postgres || true
        echo ""
        echo "## docker compose logs --no-color --tail 30 redis"
        docker compose logs --no-color --tail 30 redis || true
        echo ""
        echo "## docker compose logs --no-color --tail 30 ollama"
        docker compose logs --no-color --tail 30 ollama || true
        echo ""
        echo "## .env shape (secrets redacted)"
        grep -v -E '^(JWT_SECRET|FIRST_ADMIN_PASSWORD|ENCRYPTION_KEY)=' .env || true
        echo "## (secret vars elided)"
        echo ""
        echo "============================================"
        echo ""
    fi
fi

if [ -f scripts/verify-sovereignty.sh ]; then
    if bash scripts/verify-sovereignty.sh; then
        pass "sovereignty guard passed"
    else
        fail "sovereignty guard failed"
    fi
else
    fail "scripts/verify-sovereignty.sh missing"
fi

info "4. version lockstep"
declare -a SURFACES=()
declare -a VALUES=()

extract() {
    local label="$1" file="$2" gregex="$3" sedexpr="$4"
    if [ ! -f "$file" ]; then
        SURFACES+=("$label")
        VALUES+=("<missing>")
        return 0
    fi
    local val
    val=$(grep -oE "$gregex" "$file" 2>/dev/null | head -1 | sed -E "$sedexpr" || true)
    if [ -z "${val:-}" ]; then
        val="<no match>"
    fi
    SURFACES+=("$label")
    VALUES+=("$val")
}

extract "backend/pyproject.toml" "backend/pyproject.toml" \
    '^version[[:space:]]*=[[:space:]]*"[^"]+"' \
    's/^version[[:space:]]*=[[:space:]]*"([^"]+)"/\1/'
extract "frontend/package.json" "frontend/package.json" \
    '"version"[[:space:]]*:[[:space:]]*"[^"]+"' \
    's/.*"version"[[:space:]]*:[[:space:]]*"([^"]+)".*/\1/'
extract "CHANGELOG.md" "CHANGELOG.md" \
    '^##[[:space:]]*\[[0-9]+\.[0-9]+\.[0-9]+\]' \
    's/^##[[:space:]]*\[([0-9]+\.[0-9]+\.[0-9]+)\].*/\1/'
extract "docs/UNIFIED-SPEC.md (Current release)" "docs/UNIFIED-SPEC.md" \
    'Current release[[:space:]]*\|[[:space:]]*v[0-9]+\.[0-9]+\.[0-9]+' \
    's/.*v([0-9]+\.[0-9]+\.[0-9]+).*/\1/'

for i in "${!SURFACES[@]}"; do
    printf '      %-40s %s\n' "${SURFACES[$i]}" "${VALUES[$i]}"
done

UNIQ=$(printf '%s\n' "${VALUES[@]}" | sort -u \
    | grep -vE '^<(no match|missing)>$' | wc -l | tr -d ' ')
if [ "$UNIQ" -eq 1 ]; then
    pass "one unique version across ${#SURFACES[@]} surface(s)"
else
    fail "version drift: $UNIQ unique values across ${#SURFACES[@]} surface(s)"
fi

info "5. required docs present"
for f in README.md README.txt CHANGELOG.md CONTRIBUTING.md LICENSE .gitignore docs/index.html USER-MANUAL.md USER-MANUAL.txt; do
    if [ -f "$f" ]; then
        pass "$f"
    else
        fail "missing: $f"
    fi
done

info "6. ruff lint"
if command -v ruff >/dev/null 2>&1; then
    RUFF_CMD="ruff"
elif [ -n "$PYTHON_CMD" ] && $PYTHON_CMD -m ruff --version >/dev/null 2>&1; then
    RUFF_CMD="$PYTHON_CMD -m ruff"
elif python -m ruff --version >/dev/null 2>&1; then
    RUFF_CMD="python -m ruff"
elif python3 -m ruff --version >/dev/null 2>&1; then
    RUFF_CMD="python3 -m ruff"
else
    RUFF_CMD=""
fi

if [ -n "$RUFF_CMD" ]; then
    if (cd backend && $RUFF_CMD check .) > /tmp/civicrecords-ruff.out 2>&1; then
        pass "ruff: 0 violations"
    else
        fail "ruff: violations present (see /tmp/civicrecords-ruff.out)"
    fi
elif command -v docker >/dev/null 2>&1; then
    if docker compose run --rm --no-deps api python -m ruff check . > /tmp/civicrecords-ruff.out 2>&1; then
        pass "ruff via api container: 0 violations"
    else
        fail "container ruff: violations present or ruff unavailable (see /tmp/civicrecords-ruff.out)"
    fi
fi

info "7. backend tests"
if command -v docker >/dev/null 2>&1; then
    collected=""
    passed=""
    if docker compose run --rm --no-deps api python -m pytest tests --collect-only -q > /tmp/civicrecords-pytest-collect.out 2>&1; then
        collected=$(grep -oE '[0-9]+ tests? collected' /tmp/civicrecords-pytest-collect.out | tail -1 | grep -oE '[0-9]+' || true)
        pass "pytest collect-only: ${collected:-unknown} test(s)"
    else
        fail "pytest collect-only failed (see /tmp/civicrecords-pytest-collect.out)"
    fi
    if docker compose run --rm --no-deps api python -m pytest tests -q > /tmp/civicrecords-pytest-run.out 2>&1; then
        passed=$(grep -oE '[0-9]+ passed' /tmp/civicrecords-pytest-run.out | tail -1 | grep -oE '[0-9]+' || true)
        if [ -n "$collected" ] && [ -n "$passed" ] && [ "$collected" != "$passed" ]; then
            fail "pytest collected/pass mismatch: collected=$collected passed=$passed"
        else
            pass "pytest full suite: ${passed:-unknown} passed"
        fi
    else
        fail "pytest full suite failed (see /tmp/civicrecords-pytest-run.out)"
    fi
fi

info "8. frontend checks"
if command -v npm >/dev/null 2>&1; then
    if (cd frontend && npm ci); then pass "npm ci"; else fail "npm ci failed"; fi
    if (cd frontend && npm audit --audit-level=moderate); then pass "npm audit --audit-level=moderate"; else fail "npm audit --audit-level=moderate failed"; fi
    if (cd frontend && npm test); then pass "frontend vitest"; else fail "frontend vitest failed"; fi
    if (cd frontend && npm run build); then pass "frontend production build"; else fail "frontend production build failed"; fi
    if (cd frontend && npx playwright install chromium && npm run test:e2e); then pass "Playwright user-flow tests"; else fail "Playwright user-flow tests failed"; fi
else
    fail "npm: not installed or not on PATH"
fi

info "9. runtime install proof"
if [ -n "$PYTHON_CMD" ] && $PYTHON_CMD scripts/verify-runtime-install.py; then
    pass "runtime install proof"
else
    fail "runtime install proof failed"
fi

echo ""
if [ "$FAILED" -eq 0 ]; then
    printf '\033[0;32mVERIFY-RELEASE: PASSED\033[0m\n'
    exit 0
else
    printf '\033[0;31mVERIFY-RELEASE: FAILED\033[0m\n'
    exit 1
fi
