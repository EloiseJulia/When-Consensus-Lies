# constructed by: Claude (Anthropic) family
"""Latent-Premise Sensitivity (LPS) method — black-box, inference-only (Study 2).

# Implementer model family: Claude / Anthropic
# Auditor model family: MUST be non-Anthropic (Law 6 — cross-family requirement)

Implements the seed/context uncertainty decomposition and the Latent-Premise
Probing (LPP) detector defined in
``paper/plans/2026-07-23-study2-latent-premise-sensitivity-design.md`` (§1–§2).

Two uncertainty axes, per (item, model):
  * ``H_seed`` — semantic entropy of the answer distribution under RESAMPLING the
    SAME underspecified prompt (temperature>0, k samples). The SOTA signal.
    Clustering here is the FROZEN labeler's enumerated interpretations (exact).
  * ``H_ctx``  — answer dispersion under COUNTERFACTUAL PINNING of a candidate
    unstated dimension the model itself surfaced. High ``H_ctx`` ⇒ the answer
    depends on a dimension the prompt did not fix.

H_ctx CLUSTERING — MUTUAL ANSWER-EQUIVALENCE (gold-FREE; 2026-07-23 refinement):
    The pinned answers for a dimension are clustered by comparing them TO EACH
    OTHER (not to the gold answer):
      * numeric domains (policy_qa): each answer's numeric RESULT is extracted
        with the labeler's answer-EXTRACTION only (NOT its gold-matcher) and
        clustered by value-equality at cent tolerance.
      * code domains (code_spec, data_analysis): each candidate is EXECUTED on the
        task's own discriminating test inputs via the FROZEN execution harness
        (read-only reuse of ``bench.<domain>._runner``'s isolated bootstrap) and
        clustered by OUTPUT equality — two answers are equivalent iff they produce
        identical outputs on every input.
      * an answer that is unparseable/unrunnable (e.g. a "language=Java" pin that
        breaks the harness) is EXCLUDED from the clustering (contributes nothing,
        never its own singleton).
    ``H_ctx(d_i)`` = entropy (bits) over the resulting equivalence CLUSTERS across
    the PARSEABLE pins; if fewer than 2 parseable answers remain, ``H_ctx = 0``.

    WHY (root cause the earlier pilots exposed): self-generated counterfactual pin
    values live OFF the gold-enumerated interpretation grid, so gold-membership
    labeling collapsed genuine switches to I_perp → ~0 signal. Mutual equivalence
    detects that pinning "typical=mean" vs "=median" vs "=mode" yields three
    DIFFERENT results that disagree WITH EACH OTHER → 3 clusters → high H_ctx, even
    though none matches gold; while an in-prompt-fixed (H2) or nonexistent (k0)
    dimension yields the SAME result regardless of the pin → 1 cluster → low H_ctx.

DANGER quadrant = high ``H_ctx`` AND low ``H_seed`` (confident latent-premise
ambiguity — the SOTA blind spot this study targets).

ANTI-LEAKAGE (inviolable, design §2/§6): every prompt the model sees is
GENERIC — it uses ONLY ``task.prompt`` (+ the coarse domain name) and, for
pinning, the model's OWN self-generated dimension/value strings. NONE of
``task.interpretations`` (id / gold_check), ``task.key_questions``,
``task.latent_spec``, or any target/foil text ever enters a prompt. The mutual-
equivalence clustering compares the PINNED ANSWERS to each other only — it never
reads the gold answer. The gold axis (``key_questions``) is used ONLY for
EVALUATION/reporting downstream.

Entropy is reported in BITS (log base 2).
"""

from __future__ import annotations

import json
import math
import os
import re
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── Repo root on sys.path (scripts/ is not a package) ────────────────────────
_SCRIPTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPTS_DIR.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from common.schema import AgentRun, Task  # noqa: E402
from harness.label import label_run  # noqa: E402  (FROZEN executable-gold labeler)
from harness.run import answer_format_instruction  # noqa: E402  (FROZEN prompt contract)


# ── Defaults (pilot-tunable; FROZEN before the confirmatory run) ─────────────
DEFAULT_K = 5              # seed-resamples for H_seed
DEFAULT_TEMPERATURE = 0.7  # resampling temperature (omitted for reasoning slugs)
DEFAULT_MAX_DIMS = 4       # cap on surfaced assumption dimensions
DEFAULT_TAU = 0.5          # H_ctx flag threshold (bits) — pilot-calibrated
DEFAULT_TAU_S = 0.5        # H_seed low-confidence ceiling (bits) — pilot-calibrated
_ROLE = "tested_agents"    # generic answering role

#: Method-version stamp for run provenance / checkpoint fingerprinting. Bump this
#: whenever the H_seed/H_ctx measurement changes so a resume cannot silently reuse
#: results computed under an incompatible method. Current: mutual-equivalence
#: H_ctx clustering with tolerance-aware output signing (frozen-harness FLOAT_TOL).
METHOD_VERSION = "lps-2026-07-23-v4-tol-equiv"

#: The ineligible "degenerate/noise" label. Refinement 1 (2026-07-23): H_ctx is
#: computed over VALID enumerated interpretations only, EXCLUDING I_perp — mirror
#: cd_primary's rule that I_perp is ineligible. A pin like "language=Java" /
#: "output_format=…" breaks the executable-gold checker → I_perp, which spuriously
#: inflated H_ctx even on H2/k0. This is a pilot-stage refinement of the DETECTOR's
#: H_ctx, NOT a change to cd_primary or the frozen labeler.
I_PERP = "I_perp"

#: Refinement 2 backstop keyword filter: drop surfaced dimensions that are about
#: programming language / library / tooling / output-encoding / display-formatting
#: (they change HOW an answer is written, not WHAT the answer IS). Conservative —
#: deliberately excludes bare "format"/"rounding"/"date format" tokens because
#: those ARE genuine answer-semantic axes in the benchmark (e.g. date_format,
#: rounding_standard). Matched as whole tokens against the dimension name/values.
_FORMAT_TOOLING_TOKENS = frozenset(
    """language languages programming python javascript typescript java kotlin
    ruby php golang rust cpp csharp scala perl swift syntax library libraries
    framework frameworks module modules import imports package packages
    dependency dependencies tooling toolchain runtime interpreter compiler ide
    encoding charset unicode utf ascii whitespace indentation codestyle""".split()
)
#: Multiword phrases (substring match on the lowercased dimension name).
_FORMAT_TOOLING_PHRASES = (
    "programming language", "output format", "output encoding", "file type",
    "file format", "code style", "coding style", "display format",
    "string formatting", "which language", "output scope", "return type wrapper",
)
#: Known language tokens: a dim whose VALUES are all languages is a language pick.
_LANGUAGE_TOKENS = frozenset(
    """python javascript typescript java kotlin ruby php golang go rust cpp c
    csharp scala perl swift r matlab sql bash""".split()
)


# ── Generic prompts (NO gold; auditor-visible verbatim) ──────────────────────

#: Assumption-surfacing prompt. Uses ONLY task.prompt + coarse domain. Asks the
#: model to name decision-relevant unstated assumptions with alternative values.
ASSUMPTION_SURFACING_TEMPLATE = (
    "You are about to answer the following {domain} task:\n"
    "----- TASK -----\n"
    "{prompt}\n"
    "----- END TASK -----\n\n"
    "Before answering, list the decision-relevant assumptions your answer would "
    "depend on that are NOT fixed by the task text above.\n\n"
    "List ONLY assumptions that change WHAT the correct answer IS (its value or "
    "result). Do NOT list assumptions about how the answer is FORMATTED, rounded "
    "for display, which programming language / library / tool is used, output "
    "encoding, file type, or code style — those do not change the underlying "
    "answer. For each assumption, give a short dimension name and 2 or 3 concrete "
    "alternative values it could plausibly take. List at most {max_dims} "
    "dimensions, most decision-relevant first.\n\n"
    "Respond with ONLY a JSON array, no prose, in exactly this shape:\n"
    "[{{\"dimension\": \"<short name>\", \"values\": [\"<v1>\", \"<v2>\"]}}]"
)

#: Counterfactual-pinning template. Appends a NEUTRAL clause built from the
#: model's OWN surfaced dimension/value strings. No gold text.
PINNING_TEMPLATE = (
    "{prompt}\n\n"
    "For this answer, assume the following resolution of an otherwise "
    "unspecified detail: {dimension} = {value}.\n"
    "Give your final answer now."
)

#: EXECUTABLE ANSWER CONTRACT (2026-07-23 coverage fix). We APPEND the FROZEN
#: confirmatory answer-format contract (``answer_format_instruction(domain)``) to
#: the seed-resample AND pinning prompts so answers come back in the SAME
#: extractable/executable shape the confirmatory study uses — otherwise most
#: pinned answers were unparseable/unrunnable and H_ctx collapsed to 0. For
#: code / data_analysis we additionally require STANDARD-LIBRARY-ONLY code so it
#: runs under the scrubbed ``-S -E`` execution harness (no pandas/numpy). The
#: contract is DOMAIN-GENERIC (no gold/target/foil/key_questions) → anti-leakage
#: preserved. This changes the DETECTOR's prompts only, not any frozen metric.
_STDLIB_ONLY_CLAUSE = (
    "\nUse ONLY the Python standard library — do NOT import pandas, numpy, or any "
    "third-party package. The solution must run under a standard-library-only "
    "interpreter."
)


def _answer_contract(domain: str) -> str:
    """Frozen domain answer-format contract (+ stdlib-only clause for code)."""
    contract = answer_format_instruction(domain)
    if domain in ("code_spec", "data_analysis"):
        contract += _STDLIB_ONLY_CLAUSE
    return contract


def _with_contract(prompt: str, domain: str) -> str:
    """Append the executable answer contract to a prompt."""
    return f"{prompt}\n\n{_answer_contract(domain)}"


# ── Entropy (BITS) over exact label clusters ─────────────────────────────────

def semantic_entropy(labels: List[str]) -> float:
    """Shannon entropy (BITS) of the empirical distribution over EXACT labels.

    Each distinct label string is its own semantic cluster (``I_perp`` included).
    Returns 0.0 for an empty list or a degenerate (single-cluster) distribution.
    """
    n = len(labels)
    if n == 0:
        return 0.0
    counts = Counter(labels)
    h = 0.0
    for c in counts.values():
        p = c / n
        h -= p * math.log2(p)
    return h


# ── Labeling adapter (FROZEN labeler; gold used for LABELING only, not prompts) ─

def _label_answer(output: str, task: Task, *, model_id: str, seed: int) -> str:
    """Wrap a raw model answer in an AgentRun and label it via the frozen labeler."""
    run = AgentRun(
        task_id=task.id,
        config="lps",
        model_role=_ROLE,
        model_id=model_id,
        output=output,
        label="",
        verbalized_conf=0.0,
        logit_conf=None,
        seed=seed,
    )
    return label_run(run, task)


def _complete_text(
    client: Any,
    *,
    prompt: str,
    model: str,
    seed: int,
    temperature: Optional[float],
) -> str:
    """Call ``client.complete`` and return the completion text.

    Uses the generic answering role; the explicit ``model`` overrides role-based
    routing so a single client can sweep multiple models.
    """
    completion = client.complete(
        role=_ROLE,
        prompt=prompt,
        seed=seed,
        model=model,
        temperature=temperature,
    )
    return completion.text


# ── Stage A: H_seed (SOTA seed-resampling semantic entropy) ──────────────────

def H_seed(
    task: Task,
    client: Any,
    model: str,
    *,
    k: int = DEFAULT_K,
    temperature: float = DEFAULT_TEMPERATURE,
    base_seed: int = 0,
) -> Dict[str, Any]:
    """Semantic entropy (bits) over k resamples of the SAME underspecified prompt.

    The prompt is ``task.prompt`` + the executable answer contract (so H_seed and
    H_ctx are measured on comparably-extractable outputs); the contract is
    domain-generic (no gold) so anti-leakage holds. k distinct samples are
    obtained by advancing the seed (``base_seed + j``); temperature>0 drives the
    sampling variation.

    Returns ``{"H_seed", "labels", "k"}``.
    """
    labels: List[str] = []
    prompt = _with_contract(task.prompt, task.domain)
    for j in range(k):
        seed = base_seed + j
        text = _complete_text(
            client, prompt=prompt, model=model, seed=seed, temperature=temperature
        )
        labels.append(_label_answer(text, task, model_id=model, seed=seed))
    return {"H_seed": semantic_entropy(labels), "labels": labels, "k": k}


# ── Stage B: assumption surfacing (self-generated, generic) ──────────────────

def _extract_json_array(text: str) -> Optional[list]:
    """Best-effort extraction of the first top-level JSON array from model text.

    Handles ```json fences and surrounding prose. Returns a Python list or None.
    """
    if not text:
        return None
    # Strip common code fences.
    fenced = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.DOTALL)
    candidate = fenced.group(1) if fenced else None
    if candidate is None:
        # Fall back to the first balanced [...] span.
        start = text.find("[")
        if start == -1:
            return None
        depth = 0
        end = -1
        for i in range(start, len(text)):
            ch = text[i]
            if ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        if end == -1:
            return None
        candidate = text[start : end + 1]
    try:
        parsed = json.loads(candidate)
    except (json.JSONDecodeError, ValueError):
        return None
    return parsed if isinstance(parsed, list) else None


def _normalise_dims(parsed: Optional[list], *, max_dims: int) -> List[Dict[str, Any]]:
    """Coerce parsed JSON into a clean list of {dimension, values} dicts.

    Drops malformed entries, dedupes values, keeps dimensions with >= 2 values,
    and truncates to ``max_dims``.
    """
    dims: List[Dict[str, Any]] = []
    if not isinstance(parsed, list):
        return dims
    for entry in parsed:
        if not isinstance(entry, dict):
            continue
        name = entry.get("dimension")
        vals = entry.get("values")
        if not isinstance(name, str) or not name.strip():
            continue
        if not isinstance(vals, list):
            continue
        clean_vals: List[str] = []
        for v in vals:
            s = str(v).strip()
            if s and s not in clean_vals:
                clean_vals.append(s)
        if len(clean_vals) < 2:
            continue
        dims.append({"dimension": name.strip(), "values": clean_vals})
        if len(dims) >= max_dims:
            break
    return dims


def surface_assumptions(
    task: Task,
    client: Any,
    model: str,
    *,
    max_dims: int = DEFAULT_MAX_DIMS,
    seed: int = 0,
    apply_filter: bool = True,
) -> List[Dict[str, Any]]:
    """Ask the model to self-generate decision-relevant unstated dimensions.

    GENERIC prompt (design §2 stage 1): uses ONLY ``task.prompt`` + ``task.domain``.
    Returns a list of ``{"dimension": str, "values": [str, ...]}`` (>= 2 values each).
    Never includes any gold/interpretation/key-question text.

    Refinement 2 (2026-07-23): the prompt now instructs the model to list only
    ANSWER-SEMANTIC axes (what the answer IS, not formatting/language/tooling), and
    a backstop keyword filter drops any format/language/tooling dimension that slips
    through (``apply_filter=True``). Use ``surface_assumptions_detailed`` to also
    obtain the dropped dimensions for reporting.
    """
    kept, _dropped = surface_assumptions_detailed(
        task, client, model, max_dims=max_dims, seed=seed, apply_filter=apply_filter
    )
    return kept


def surface_assumptions_detailed(
    task: Task,
    client: Any,
    model: str,
    *,
    max_dims: int = DEFAULT_MAX_DIMS,
    seed: int = 0,
    apply_filter: bool = True,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Like ``surface_assumptions`` but returns ``(kept, dropped)`` dimensions.

    ``dropped`` are the surfaced dimensions removed by the format/language/tooling
    backstop filter (Refinement 2), for transparent reporting.
    """
    prompt = ASSUMPTION_SURFACING_TEMPLATE.format(
        domain=task.domain, prompt=task.prompt, max_dims=max_dims
    )
    # Deterministic surfacing (temperature=0 style) for reproducibility.
    text = _complete_text(client, prompt=prompt, model=model, seed=seed, temperature=0.0)
    dims = _normalise_dims(_extract_json_array(text), max_dims=max_dims)
    if not apply_filter:
        return dims, []
    kept: List[Dict[str, Any]] = []
    dropped: List[Dict[str, Any]] = []
    for dim in dims:
        (dropped if _is_format_dim(dim) else kept).append(dim)
    return kept, dropped


def _tokens(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _is_format_dim(dim: Dict[str, Any]) -> bool:
    """True iff the dimension is about language/tooling/output-encoding/format.

    Refinement 2 backstop (EVALUATION-side of surfacing, never enters a prompt).
    Conservative: matches whole-token language/tooling keywords, a few multiword
    format phrases in the name, or a values-list that is entirely language names.
    """
    name = dim.get("dimension", "")
    name_l = name.lower()
    name_toks = set(_tokens(name))
    if name_toks & _FORMAT_TOOLING_TOKENS:
        return True
    for phrase in _FORMAT_TOOLING_PHRASES:
        if phrase in name_l:
            return True
    values = dim.get("values", []) or []
    if values:
        val_all_lang = True
        for v in values:
            vt = set(_tokens(str(v)))
            if not (vt & _LANGUAGE_TOKENS):
                val_all_lang = False
                break
        if val_all_lang:
            return True
    return False


# ── Gold-FREE answer-equivalence signatures (mutual clustering) ──────────────
# These extract an answer's RESULT/BEHAVIOR without ever comparing to the gold
# answer: numeric domains reuse the labeler's numeric EXTRACTION; code domains
# EXECUTE the candidate on the task's own discriminating inputs (read-only reuse
# of the FROZEN bench ``_runner`` isolated bootstrap) and use the OUTPUT tuple.

_EXEC_TIMEOUT_SECONDS = 5.0

# ── Tolerance-aware pairwise output equivalence (mirrors frozen harness) ──────
# Executed-output clustering must agree EXACTLY with the frozen executable harness,
# whose output-equality is ``bench.<domain>._runner._compare``:
#   bool kept TYPE-DISTINCT from numbers; top-level float within FLOAT_TOL=1e-9
#   (``abs(a-b) < 1e-9``); int/float unified by value; everything else exact ``==``.
# Tolerance equality is NON-TRANSITIVE, so it CANNOT be bucketed by a hashable
# signature (rounding-to-signature has boundary artifacts and collapses distinct
# large ints). We therefore compare answers PAIRWISE via the harness ``_compare``
# and form clusters by connected components (union-find).


def _runner_compare(domain: str):
    """The FROZEN harness pairwise output-equality ``_runner._compare`` for a domain.

    Reusing it directly makes our mutual-equivalence clustering agree byte-for-byte
    with the executable gold harness (no rounding-bucket boundary artifacts, no
    int→float collapse). Returns ``None`` for non-executable domains.
    """
    if domain == "code_spec":
        from bench.code_spec._runner import _compare
    elif domain == "data_analysis":
        from bench.data_analysis._runner import _compare
    else:
        return None
    return _compare


def _code_results_equal(domain: str, a: Any, b: Any) -> bool:
    """Pairwise equality of two ordered per-input result lists via the harness compare.

    Elementwise ``_compare`` (tolerance on scalar floats, exact otherwise) — the
    SAME semantics the gold harness uses to judge a candidate's outputs.
    """
    cmp = _runner_compare(domain)
    if cmp is None:
        return a == b
    if not (isinstance(a, list) and isinstance(b, list)) or len(a) != len(b):
        return a == b
    try:
        return all(bool(cmp(x, y)) for x, y in zip(a, b))
    except Exception:  # noqa: BLE001  — any comparison error → treat as not-equal
        return False


def _sig_equal(domain: str, a: Any, b: Any) -> bool:
    """Domain-aware pairwise equality of two answer signatures.

    code/data result LISTS → tolerance-aware harness ``_compare`` (elementwise);
    everything else (policy cent-strings, exact tokens, test stubs) → exact ``==``.
    """
    if domain in ("code_spec", "data_analysis") and isinstance(a, list) and isinstance(b, list):
        return _code_results_equal(domain, a, b)
    return a == b


def _equivalence_labels(items: List[Any], eq) -> List[int]:
    """Connected-components labels under a (possibly NON-TRANSITIVE) pairwise ``eq``.

    Two items share a cluster iff connected by a CHAIN of pairwise-equal items
    (union-find). This is the principled clustering for tolerance equality, which
    is not transitive and cannot be bucketed by a hashable signature.
    """
    n = len(items)
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: int, y: int) -> None:
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[rx] = ry

    for i in range(n):
        for j in range(i + 1, n):
            if eq(items[i], items[j]):
                union(i, j)
    return [find(i) for i in range(n)]


def cluster_entropy(items: List[Any], eq) -> Tuple[float, int]:
    """Shannon entropy (BITS) over connected-component clusters of ``items``.

    Returns ``(H_bits, n_clusters)``; ``(0.0, len(items))`` for < 2 items.
    """
    n = len(items)
    if n == 0:
        return 0.0, 0
    if n == 1:
        return 0.0, 1
    labels = _equivalence_labels(items, eq)
    counts = Counter(labels)
    h = 0.0
    for c in counts.values():
        p = c / n
        h -= p * math.log2(p)
    return h, len(counts)


def _numeric_signature(output_text: str) -> Optional[str]:
    """Signature for numeric answers: extracted value at cent tolerance.

    Reuses the labeler's answer-EXTRACTION ONLY (``_extract_numeric_from_output``
    after ``_strip_reasoning``) — NEVER its gold-matcher. Returns None when no
    numeric answer is parseable (→ excluded from clustering).
    """
    from harness.label import _extract_numeric_from_output, _strip_reasoning

    amount = _extract_numeric_from_output(_strip_reasoning(output_text))
    if amount is None:
        return None
    return f"num:{int(round(amount * 100))}"  # cent tolerance


def _task_code_inputs(task: Task) -> Tuple[List[Any], Optional[str]]:
    """Union of the task's discriminating test inputs + the shared entrypoint.

    Read-only reuse of the frozen domain checkers (their ``.test_cases`` inputs
    are exactly the interpretation-distinguishing inputs). Gold outputs are
    ignored — only the INPUTS and the entrypoint are used.
    """
    if task.domain == "code_spec":
        from bench.code_spec import get_checkers_and_candidates
    elif task.domain == "data_analysis":
        from bench.data_analysis import get_checkers_and_candidates
    else:
        return [], None
    try:
        checkers, _, _ = get_checkers_and_candidates(task.domain, task)
    except (ValueError, KeyError, RuntimeError):
        return [], None  # unknown/synthetic task → no discriminating inputs
    inputs: List[Any] = []
    seen: set = set()
    entrypoint: Optional[str] = None
    for checker in checkers.values():
        entrypoint = getattr(checker, "entrypoint", entrypoint)
        for inp, _expected in getattr(checker, "test_cases", []):
            key = repr(inp)
            if key not in seen:
                seen.add(key)
                inputs.append(inp)
    return inputs, entrypoint


def _run_code_results(
    domain: str, code: str, entrypoint: str, inputs: List[Any]
) -> Optional[List[Any]]:
    """Execute *code* on each input via the frozen bootstrap; return the RAW outputs.

    Reuses ``bench.<domain>._runner.CANDIDATE_BOOTSTRAP`` (the SAME isolated worker
    the gold harness uses) so execution semantics are identical. Returns the ORDERED
    list of raw per-input results (JSON values, compared later via the harness's
    tolerance-aware ``_compare``), or None if the candidate fails to produce a clean
    result on ANY input (→ unrunnable → excluded from clustering).
    """
    if domain == "code_spec":
        from bench.code_spec._runner import CANDIDATE_BOOTSTRAP
    elif domain == "data_analysis":
        from bench.data_analysis._runner import CANDIDATE_BOOTSTRAP
    else:
        return None

    results: List[Any] = []
    sandbox = tempfile.mkdtemp(prefix="lps_exec_")
    try:
        bootstrap_path = os.path.join(sandbox, "_candidate_bootstrap.py")
        with open(bootstrap_path, "w", encoding="utf-8") as fh:
            fh.write(CANDIDATE_BOOTSTRAP)
        clean_env = {
            key: val
            for key, val in os.environ.items()
            if not key.startswith("PYTHON")
            and key not in ("PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV")
        }
        for inp in inputs:
            multi = isinstance(inp, tuple)
            worker_input = {
                "candidate": code,
                "entrypoint": entrypoint,
                "input": list(inp) if multi else inp,
                "multi": multi,
            }
            fd_in, in_path = tempfile.mkstemp(prefix="lps_in_", suffix=".json", dir=sandbox)
            os.close(fd_in)
            fd_out, out_path = tempfile.mkstemp(prefix="lps_out_", suffix=".json", dir=sandbox)
            os.close(fd_out)
            with open(in_path, "w", encoding="utf-8") as fh:
                fh.write(json.dumps(worker_input))
            cmd = [sys.executable, "-S", "-E", "-B", bootstrap_path, in_path, out_path]
            try:
                if sys.platform == "win32":
                    subprocess.run(
                        cmd, cwd=sandbox, env=clean_env, timeout=_EXEC_TIMEOUT_SECONDS,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        creationflags=0x00000200,
                    )
                else:
                    subprocess.run(
                        cmd, cwd=sandbox, env=clean_env, timeout=_EXEC_TIMEOUT_SECONDS,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        start_new_session=True,
                    )
            except (subprocess.TimeoutExpired, OSError):
                return None
            try:
                with open(out_path, "r", encoding="utf-8") as fh:
                    out = json.load(fh)
            except (OSError, ValueError):
                return None
            if out.get("status") != "ok":
                return None
            results.append(out.get("result"))
    finally:
        _rmtree_quiet(sandbox)
    return results


def _rmtree_quiet(path: str) -> None:
    import shutil
    try:
        shutil.rmtree(path, ignore_errors=True)
    except OSError:
        pass


def answer_signature(task: Task, output_text: str) -> Optional[Any]:
    """Gold-FREE equivalence signature of a single answer, or None if unparseable.

    Two answers are mutually equivalent iff ``_sig_equal(domain, a, b)`` (pairwise,
    tolerance-aware for executed code/data outputs). Compares answers to EACH OTHER
    only — the gold answer is never consulted. Returns a string (policy cent-sig) or
    the raw ordered per-input result list (code/data), never compared by hashing.
    """
    domain = task.domain
    if domain == "policy_qa":
        return _numeric_signature(output_text)
    if domain in ("code_spec", "data_analysis"):
        from harness.label import _extract_code_candidates

        cands = _extract_code_candidates(output_text)
        if not cands:
            return None
        inputs, entrypoint = _task_code_inputs(task)
        if not inputs or not entrypoint:
            return None
        variants: List[List[Any]] = []
        for code in cands:
            res = _run_code_results(domain, code, entrypoint, inputs)
            if res is None:
                return None  # any unrunnable block → whole answer excluded
            variants.append(res)
        # Multiple code blocks in one answer must AGREE (tolerance-aware) to be a
        # single unambiguous signature; disagreement → excluded.
        first = variants[0]
        for other in variants[1:]:
            if not _code_results_equal(domain, first, other):
                return None
        return first
    return None


# ── Stage C: H_ctx (counterfactual pinning, mutual-equivalence clustering) ────

def H_ctx(
    task: Task,
    client: Any,
    model: str,
    dims: List[Dict[str, Any]],
    *,
    base_seed: int = 0,
) -> Dict[str, Any]:
    """Per-dimension answer dispersion under counterfactual pinning.

    For each surfaced dimension d_i with values {v_ij}, build a pinned prompt
    ``task.prompt ⊕ "assume d_i = v_ij"`` (model's OWN strings — no gold) and
    answer. Two entropies are reported per dimension:
      * ``H_ctx``      — MUTUAL-EQUIVALENCE entropy (bits): cluster the pinned
        answers by answer-to-answer equivalence via ``answer_signature`` (gold-
        FREE); unparseable/unrunnable answers are EXCLUDED. If fewer than 2
        parseable answers remain, ``H_ctx = 0``.
      * ``H_ctx_all``  — legacy gold-label rule (entropy over the FROZEN labeler's
        labels incl. I_perp), kept for before/after comparison only.

    ``H_ctx_max`` / ``flagged_dimension`` use the mutual-equivalence ``H_ctx``.

    Returns ``{"per_dim", "H_ctx_max", "H_ctx_max_all", "flagged_dimension"}`` where
    ``per_dim`` items carry ``{dimension, values, labels, signatures, n_parseable,
    n_clusters, H_ctx, H_ctx_all}``.
    """
    per_dim: List[Dict[str, Any]] = []
    for di, dim in enumerate(dims):
        name = dim["dimension"]
        values = dim["values"]
        labels: List[str] = []
        signatures: List[Optional[str]] = []
        for vj, value in enumerate(values):
            prompt = PINNING_TEMPLATE.format(
                prompt=task.prompt, dimension=name, value=value
            )
            prompt = _with_contract(prompt, task.domain)
            # Distinct seed per (dim, value) so the cache never collapses cells.
            seed = base_seed + di * 100 + vj
            text = _complete_text(
                client, prompt=prompt, model=model, seed=seed, temperature=0.0
            )
            labels.append(_label_answer(text, task, model_id=model, seed=seed))
            signatures.append(answer_signature(task, text))
        parseable = [s for s in signatures if s is not None]
        if len(parseable) >= 2:
            h_ctx, n_clusters = cluster_entropy(
                parseable, lambda a, b: _sig_equal(task.domain, a, b)
            )
        else:
            h_ctx, n_clusters = 0.0, len(parseable)
        per_dim.append(
            {
                "dimension": name,
                "values": values,
                "labels": labels,
                "signatures": signatures,
                "n_parseable": len(parseable),
                "n_clusters": n_clusters,
                "H_ctx": h_ctx,
                "H_ctx_all": semantic_entropy(labels),
            }
        )

    if not per_dim:
        return {
            "per_dim": [],
            "H_ctx_max": 0.0,
            "H_ctx_max_all": 0.0,
            "flagged_dimension": None,
        }

    best = max(per_dim, key=lambda d: d["H_ctx"])
    return {
        "per_dim": per_dim,
        "H_ctx_max": best["H_ctx"],
        "H_ctx_max_all": max(d["H_ctx_all"] for d in per_dim),
        "flagged_dimension": best["dimension"] if best["H_ctx"] > 0 else None,
    }


# ── Detector: Latent-Premise Probing (LPP) ───────────────────────────────────

def lpp_detect(
    task: Task,
    client: Any,
    model: str,
    *,
    tau: float = DEFAULT_TAU,
    tau_s: float = DEFAULT_TAU_S,
    k: int = DEFAULT_K,
    temperature: float = DEFAULT_TEMPERATURE,
    max_dims: int = DEFAULT_MAX_DIMS,
    base_seed: int = 0,
) -> Dict[str, Any]:
    """Full black-box detector: surface → pin → decompose → flag danger quadrant.

    PRIMARY (item-level) metric: item is flagged AMBIGUOUS iff
    ``H_ctx_max > 0`` (some surfaced-dimension pinning changes the answer among
    mutual-equivalence clusters) AND ``H_seed <= tau_s`` (the danger quadrant:
    the answer depends on an unstated dimension yet resampling looks confident).
    Localization (which dimension) is a SECONDARY metric, reported separately.

    Returns a dict with H_seed, H_ctx_max, flagged_dimension, is_flagged, plus the
    per-dimension breakdown, surfaced dims, and seed labels (for reporting/audit).
    """
    seed_res = H_seed(
        task, client, model, k=k, temperature=temperature, base_seed=base_seed
    )
    dims, dropped_dims = surface_assumptions_detailed(
        task, client, model, max_dims=max_dims, seed=base_seed
    )
    ctx_res = H_ctx(task, client, model, dims, base_seed=base_seed)

    h_seed = seed_res["H_seed"]
    h_ctx_max = ctx_res["H_ctx_max"]
    # PRIMARY item-level flag: an answer-changing dimension ABOVE tau + confident
    # reseed. tau is the operating threshold on H_ctx (default operating point in
    # the pilot is tau=0.0, i.e. "any answer-changing dimension"); a higher tau
    # suppresses borderline flags.
    is_flagged = bool(h_ctx_max > tau and h_seed <= tau_s)

    # Coverage: how many pinned answers came back parseable/runnable (contract fix).
    n_pins_total = sum(len(d["values"]) for d in ctx_res["per_dim"])
    n_parseable_total = sum(d["n_parseable"] for d in ctx_res["per_dim"])

    return {
        "task_id": task.id,
        "model": model,
        "regime": task.regime,
        "ambiguity_level": task.ambiguity_level,
        "H_seed": h_seed,
        "H_ctx_max": h_ctx_max,
        "H_ctx_max_all": ctx_res["H_ctx_max_all"],
        "flagged_dimension": ctx_res["flagged_dimension"],
        "is_flagged": is_flagged,
        "n_pins_total": n_pins_total,
        "n_parseable_total": n_parseable_total,
        "tau": tau,
        "tau_s": tau_s,
        "surfaced_dims": dims,
        "filtered_dims": dropped_dims,
        "per_dim": ctx_res["per_dim"],
        "seed_labels": seed_res["labels"],
    }


# ── Localization evaluation (gold axis used for REPORTING ONLY) ───────────────

_STOPWORDS = frozenset(
    """a an the of to for in on at by is are be do does which what when where how
    that this these those or and it its with as your you answer value single
    should would could may might rounded decimal places returns return function
    given between from into per each""".split()
)


def _keywords(text: str) -> set:
    """Lowercased alphanumeric tokens of length>=3, minus generic stopwords."""
    toks = re.findall(r"[a-z0-9]+", text.lower())
    return {t for t in toks if len(t) >= 3 and t not in _STOPWORDS}


def axis_match(dimension_text: str, key_questions: List[str]) -> bool:
    """Heuristic: does the surfaced dimension name overlap the true deleted axis?

    EVALUATION-ONLY (never influences any prompt). Returns True iff the surfaced
    dimension shares >= 2 salient keywords with some gold key_question, OR shares
    >= 1 keyword when that question has only one salient keyword. This is a coarse
    localization sanity check, reported honestly as such.
    """
    if not dimension_text or not key_questions:
        return False
    dim_kw = _keywords(dimension_text)
    if not dim_kw:
        return False
    for q in key_questions:
        q_kw = _keywords(q)
        if not q_kw:
            continue
        overlap = dim_kw & q_kw
        need = 1 if len(q_kw) <= 1 else 2
        if len(overlap) >= need:
            return True
    return False
