# constructed by: Claude (Anthropic) family
"""default_check_frontier.py — FRONTIER-ROSTER default-check re-validation driver.

Amendment 06 (paper/preregistration/2026-07-17-amendment-06-frontier-roster-DRAFT.md):
re-validate the two-regime demarcation (H1 convergent-delusion persists; H2 reasoners
resolve, weak models default wrong) on the Copilot-proxy FRONTIER models, now that the
proxy provider is merged (common/llm.py provider="copilot_proxy", no token, unlimited).

DRY: this driver REUSES the entire GitHub-Models pipeline in scripts/default_check.py —
the SAME task set, executable-gold labeling, enumerated-vs-frozen CD / I_perp math, the
two-pass Runner orchestration, the report assembly and the human-readable table. The ONLY
thing that changes is the MODEL plane, expressed as a ``default_check.Roster`` (the A06 §2
frontier roster) plus a SEPARATE checkpoint + cache so it never collides with the
GitHub-Models run.

Passes (identical structure to the GitHub driver, different roster):
  A. homogeneous sc (k=5) for the REASONING models AND the WEAK models (the reasoner-vs-
     weak H2 contrast + H1 persistence) — plus the gpt-5.4 ρ→1 logprobs baseline (A06 §2
     homogeneous role, "sampled repeatedly"). code_invoice is EXCLUDED from this pass.
  B. heterogeneous single-pass across the 3-family cross-model pool (gpt-5.4 / claude-
     sonnet-4.6 / gemini-3.1-pro-preview) — one independent sample per family.

OFFLINE / CI SAFE: ``main()`` does NOTHING unless the RUN_FRONTIER_CHECK=1 flag is set AND
(unless bypassed) the local proxy is reachable. The proxy needs NO token, so the second
guard is a best-effort proxy-reachability probe rather than a token check. Offline → prints
"skipped" and exits 0 (no network). LIVE execution is the MANAGER's job (after a clean
cross-family audit). The offline unit test drives ``run_frontier`` against the deterministic
mock client with provider="copilot_proxy" and NO network.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


# ── Import the shared GitHub-Models driver (scripts/ is not a package) ─────────
_THIS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _THIS_DIR.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_DC_PATH = _THIS_DIR / "default_check.py"
_spec = importlib.util.spec_from_file_location("default_check", _DC_PATH)
default_check = importlib.util.module_from_spec(_spec)
# Register before exec so any module-name lookups resolve to this instance.
sys.modules.setdefault("default_check", default_check)
_spec.loader.exec_module(default_check)  # type: ignore[union-attr]


# ── Frontier roster (Amendment 06 §2) ─────────────────────────────────────────
# Reasoning arm (H2 strong-reasoner condition): frontier top models, 3 families.
FRONTIER_REASONING_MODELS: Tuple[Tuple[str, str], ...] = (
    ("tested_agents", "gpt-5.6-sol"),           # OpenAI  reasoner
    ("tested_agents", "claude-opus-4.8"),       # Claude  reasoner
    ("tested_agents", "gemini-3.1-pro-preview"),# Gemini  reasoner
)
# Weak arm (H2 weak-model contrast — reasoner-vs-weak): 4 families, now including a
# GENUINELY-WEAK non-frontier model (gpt-3.5-turbo) added per the 2026-07-17 owner ruling.
# The 3 frontier-weak models (claude-haiku-4.5 / gemini-3.5-flash / gpt-4o-mini) resolve
# the ORIGINAL easy median-skew H2 item, collapsing the reasoner-vs-weak contrast; adding a
# genuinely-weak model plus the HARDER H2 demonstrators (data_avgprice_001, data_rate_001)
# restores a measurable split. All run on the copilot_proxy.
FRONTIER_WEAK_MODELS: Tuple[Tuple[str, str], ...] = (
    ("tested_agents", "gpt-4o-mini"),           # OpenAI  weak (logprobs-capable)
    ("tested_agents", "gemini-3.5-flash"),      # Gemini  weak
    ("tested_agents", "claude-haiku-4.5"),      # Claude  weak
    ("tested_agents", "gpt-3.5-turbo"),         # OpenAI  genuinely-weak (non-frontier)
)
# ρ→1 fake-redundancy baseline (A06 §2 homogeneous role — OpenAI logprobs+temperature,
# "sampled repeatedly"). Included in the homogeneous-sc pass so H1 persistence is also
# observed on a non-reasoner frontier model with a clean logit_conf silent-failure home.
FRONTIER_RHO_BASELINE: Tuple[str, str] = ("tested_agents", "gpt-5.4")
# Heterogeneous cross-family pool (⭐ the row-35 cross-model MAD headline): 3 families,
# ONE independent sample per family.
FRONTIER_POOL_MODELS: Tuple[Tuple[str, str], ...] = (
    ("tested_agents", "gpt-5.4"),               # OpenAI
    ("tested_agents", "claude-sonnet-4.6"),     # Claude
    ("tested_agents", "gemini-3.1-pro-preview"),# Gemini
)

# Pass A (homogeneous sc): ρ-baseline + reasoners + weak — each its OWN sc ensemble.
FRONTIER_HOMOGENEOUS_MODELS: Tuple[Tuple[str, str], ...] = (
    (FRONTIER_RHO_BASELINE,)
    + FRONTIER_REASONING_MODELS
    + FRONTIER_WEAK_MODELS
)

FRONTIER_REASONER_SLUGS = frozenset(m for _r, m in FRONTIER_REASONING_MODELS)
FRONTIER_WEAK_SLUGS = frozenset(m for _r, m in FRONTIER_WEAK_MODELS)
FRONTIER_RHO_BASELINE_SLUGS = frozenset({FRONTIER_RHO_BASELINE[1]})

# code_invoice k-gradient EXCLUDED from the homogeneous-sc (reasoner) pass — exactly as
# in the GitHub-Models driver; the kgrad family survives in the heterogeneous single pass.
FRONTIER_ROSTER = default_check.Roster(
    name="copilot_proxy_frontier",
    homogeneous_models=FRONTIER_HOMOGENEOUS_MODELS,
    pool_models=FRONTIER_POOL_MODELS,
    reasoner_slugs=FRONTIER_REASONER_SLUGS,
    weak_slugs=FRONTIER_WEAK_SLUGS,
    reasoner_sc_excluded_ids=frozenset(default_check.K_GRADIENT_IDS),
    rho_baseline_slugs=FRONTIER_RHO_BASELINE_SLUGS,
)


# ── Frontier run constants (SEPARATE from the GitHub-Models run) ───────────────
PROVIDER = "copilot_proxy"
DEFAULT_PROXY_BASE_URL = "http://127.0.0.1:8313/v1"
FRONTIER_CHECKPOINT = "default_check_frontier_checkpoint.jsonl"
FRONTIER_CACHE_DIR = ".llm_cache_default_check_frontier"
FRONTIER_SUMMARY_JSONL = "default_check_frontier_summary.jsonl"
FRONTIER_TABLE_TXT = "default_check_frontier_table.txt"

SC_K = default_check.SC_K                       # within-ensemble samples (k=5)
# Proxy is local + unlimited → cost is 0.0 per call, but keep a sane non-None cap as a
# defensive guardrail (it never triggers on the free proxy). RPM can be higher than the
# GitHub-Models run since the proxy is not daily-capped.
FRONTIER_BUDGET_USD = 5.00
FRONTIER_RPM = 30
# Raised token budget so frontier reasoners complete reasoning + answer (reasoning tokens
# count toward max_completion_tokens). Reuses the GitHub driver's raised value (12288).
FRONTIER_MAX_TOKENS_PER_CALL = default_check.MAX_TOKENS_PER_CALL


# ── Base-URL / guard helpers (offline-testable, no network at import) ──────────

def resolve_base_url(
    env: Optional[Dict[str, str]] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """Resolve the proxy base URL (host/port overridable) WITHOUT touching the network.

    Precedence (first match wins):
      1. ``FRONTIER_PROXY_BASE_URL`` env var (full URL).
      2. ``FRONTIER_PROXY_HOST`` / ``FRONTIER_PROXY_PORT`` env vars → ``http://host:port/v1``
         (either may be omitted; defaults derive from the built-in proxy base URL).
      3. config ``providers.copilot_proxy.base_url`` (when *config* is supplied) — the
         SAME source ``LLMClient`` uses, so the guard probes exactly what will run.
      4. ``None`` → let ``LLMClient`` resolve it from config / the built-in default
         (http://127.0.0.1:8313/v1).

    NOTE: when *config* is None this returns None for case 3 so ``LLMClient`` still owns
    resolution at construction; :func:`resolve_probe_url` collapses None to a concrete
    URL for the reachability probe.
    """
    env = os.environ if env is None else env
    explicit = env.get("FRONTIER_PROXY_BASE_URL")
    if explicit:
        return explicit
    host = env.get("FRONTIER_PROXY_HOST")
    port = env.get("FRONTIER_PROXY_PORT")
    if host or port:
        host = host or "127.0.0.1"
        port = port or "8313"
        return f"http://{host}:{port}/v1"
    if isinstance(config, dict):
        providers = config.get("providers")
        if isinstance(providers, dict):
            proxy = providers.get(PROVIDER)
            if isinstance(proxy, dict) and proxy.get("base_url"):
                return proxy["base_url"]
    return None  # LLMClient resolves from config / built-in default


def resolve_probe_url(
    env: Optional[Dict[str, str]] = None,
    config: Optional[Dict[str, Any]] = None,
) -> str:
    """Concrete URL for the reachability probe: the resolved base_url, or the built-in
    default when unresolved. Always the SAME endpoint the live LLMClient will target."""
    return resolve_base_url(env, config) or DEFAULT_PROXY_BASE_URL


def _flag_set(env: Optional[Dict[str, str]] = None) -> bool:
    env = os.environ if env is None else env
    return env.get("RUN_FRONTIER_CHECK", "0") == "1"


def proxy_reachable(base_url: str, timeout: float = 2.0) -> bool:
    """Best-effort probe: GET ``<base_url>/models``; True on any HTTP response.

    Any exception (connection refused, timeout, DNS) → False. HTTP error codes still
    mean the endpoint is *listening* → True. Never raises. Used only as the second
    live-guard (the proxy needs no token, so reachability replaces the token check)."""
    url = base_url.rstrip("/") + "/models"
    try:
        with urllib.request.urlopen(url, timeout=timeout):  # nosec - localhost probe
            return True
    except urllib.error.HTTPError:
        return True  # listening, just returned an error status
    except Exception:
        return False


def _should_run(
    env: Optional[Dict[str, str]] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, str]:
    """Double-guard. Returns (ok, reason). ok=False → print reason, exit 0.

    Guard 1: RUN_FRONTIER_CHECK=1 (explicit opt-in).
    Guard 2: proxy reachable (skippable via FRONTIER_SKIP_PROXY_PROBE=1 for the Manager
             when reachability is already established / probed out-of-band).

    The reachability probe targets the SAME base_url the live ``LLMClient`` will use —
    resolved from env override → config ``providers.copilot_proxy.base_url`` → default —
    so a configured alternate endpoint is never wrongly skipped nor the wrong host probed.
    """
    env = os.environ if env is None else env
    if not _flag_set(env):
        return False, "RUN_FRONTIER_CHECK != 1"
    if env.get("FRONTIER_SKIP_PROXY_PROBE", "0") == "1":
        return True, "flag set; proxy probe skipped"
    base_url = resolve_probe_url(env, config)
    if not proxy_reachable(base_url):
        return False, f"proxy not reachable at {base_url}"
    return True, f"flag set; proxy reachable at {base_url}"


# ── Client construction + run (offline-testable) ──────────────────────────────

def build_client(
    config: Dict[str, Any],
    *,
    offline: bool,
    base_url: Optional[str] = None,
    cache_dir: str = FRONTIER_CACHE_DIR,
    budget_usd: Optional[float] = FRONTIER_BUDGET_USD,
    rpm: int = FRONTIER_RPM,
    max_tokens_per_call: int = FRONTIER_MAX_TOKENS_PER_CALL,
):
    """Build the copilot_proxy LLMClient (no token). ``offline`` selects mock vs live."""
    from common.llm import LLMClient

    return LLMClient(
        config,
        cache_dir=cache_dir,
        offline=offline,
        base_url=base_url,             # None → resolved from config/provider default
        max_budget_usd=budget_usd,
        max_requests_per_min=rpm,
        max_tokens_per_call=max_tokens_per_call,
        provider=PROVIDER,             # copilot_proxy
        # require_auth left None → resolves to False for the proxy (no token needed).
    )


def run_frontier(
    client,
    *,
    checkpoint_path: str = FRONTIER_CHECKPOINT,
    sc_k: int = SC_K,
    budget_usd: Optional[float] = FRONTIER_BUDGET_USD,
    rpm: int = FRONTIER_RPM,
) -> Dict[str, Any]:
    """Run the frontier default-check against *client* and return the report.

    Thin wrapper over ``default_check.run_diagnostic`` with the frontier roster + a
    SEPARATE checkpoint. ``client`` fully controls online/offline, so the offline unit
    test and the Manager's live run share this code path."""
    tasks, task_role = default_check.select_tasks()
    report = default_check.run_diagnostic(
        client, tasks, task_role,
        checkpoint_path=checkpoint_path,
        sc_k=sc_k,
        budget_usd=budget_usd,
        rpm=rpm,
        roster=FRONTIER_ROSTER,
    )
    # Frontier-ONLY provenance. Added here (never in the shared default_check
    # run_diagnostic) so the GitHub-Models default report schema stays byte-identical.
    report["roster_name"] = FRONTIER_ROSTER.name
    return report


def write_report(report: Dict[str, Any], out_dir: str = ".") -> Tuple[str, str]:
    """Write frontier-named JSONL + human table (separate from the GitHub-Models files)."""
    import json

    out = Path(out_dir)
    jsonl_path = out / FRONTIER_SUMMARY_JSONL
    table_path = out / FRONTIER_TABLE_TXT
    with open(jsonl_path, "w", encoding="utf-8") as fh:
        for row in report["rows"]:
            fh.write(json.dumps({"type": "row", **row}) + "\n")
        summary = {k: v for k, v in report.items() if k != "rows"}
        fh.write(json.dumps({"type": "summary", **summary}) + "\n")
    with open(table_path, "w", encoding="utf-8") as fh:
        fh.write(default_check.render_table(report) + "\n")
    return str(jsonl_path), str(table_path)


# ── CLI entry point (double-guarded) ──────────────────────────────────────────

def main() -> None:
    from common.config import load_config

    # Fast path: no explicit opt-in → skip before loading anything.
    if not _flag_set():
        print(
            "default_check_frontier: skipped (RUN_FRONTIER_CHECK != 1). "
            "Set RUN_FRONTIER_CHECK=1 (and ensure the Copilot proxy is reachable, or set "
            "FRONTIER_SKIP_PROXY_PROBE=1) to run live."
        )
        sys.exit(0)

    # Load config BEFORE the reachability guard so the probe targets the SAME base_url
    # the live LLMClient will use (env override → config providers.copilot_proxy → default).
    cfg = load_config()
    ok, reason = _should_run(config=cfg)
    if not ok:
        print(
            f"default_check_frontier: skipped ({reason}). "
            "Ensure the Copilot proxy is reachable, or set FRONTIER_SKIP_PROXY_PROBE=1."
        )
        sys.exit(0)

    base_url = resolve_base_url(config=cfg)

    print("=" * 74)
    print("DEFAULT-CHECK FRONTIER RE-VALIDATION — LIVE (EXPLORATORY, Amendment 06)")
    print(f"  provider={PROVIDER}  base_url={base_url or '(config/provider default)'}")
    print(f"  sc_k={SC_K}  budget=${FRONTIER_BUDGET_USD:.2f}  rpm={FRONTIER_RPM}")
    print(f"  max_tokens_per_call={FRONTIER_MAX_TOKENS_PER_CALL}  (raised for reasoners)")
    print(f"  checkpoint={FRONTIER_CHECKPOINT}  cache={FRONTIER_CACHE_DIR}")
    print(f"  reasoner-sc excludes: {sorted(FRONTIER_ROSTER.reasoner_sc_excluded_ids)}")
    print(f"  homogeneous sc models={[m for _r, m in FRONTIER_HOMOGENEOUS_MODELS]}")
    print(f"    (ρ-baseline={FRONTIER_RHO_BASELINE[1]}, "
          f"reasoners={sorted(FRONTIER_REASONER_SLUGS)}, "
          f"weak={sorted(FRONTIER_WEAK_SLUGS)})")
    print(f"  heterogeneous pool={[m for _r, m in FRONTIER_POOL_MODELS]}")
    print("=" * 74)

    client = build_client(cfg, offline=False, base_url=base_url)
    report = run_frontier(client)
    jsonl_path, table_path = write_report(report)
    print(default_check.render_table(report))
    print(f"\nWrote machine summary -> {jsonl_path}")
    print(f"Wrote human table     -> {table_path}")
    print("\nNOTE: EXPLORATORY re-validation (Amendment 06) — report to the Manager; "
          "does NOT count toward H1/H2.")


if __name__ == "__main__":
    main()
