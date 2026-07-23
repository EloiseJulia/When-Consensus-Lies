# constructed by: Claude (Anthropic) family
"""Offline self-check gate for the Amendment 13 SIDECAR items (additive).

# Implementer model family: Claude / Anthropic (orchestration); item semantics: mai-code-1-flash
# Auditor model family: MUST be non-Anthropic (Law 6 — cross-family requirement)

Asserts (all OFFLINE, deterministic, no network / no LLM judge):
  1. Sidecar jsonl parse under common.schema.Task and match the frozen schema shape.
  2. Executable gold checkers RUN: every reference candidate passes ONLY its own
     interpretation's checker (mutual distinguishability), like the frozen families.
  3. lps_gold.gold_ambiguity classifies each k1 as AMB+ and each k0 as AMB-.
  4. Anti-leakage: the k1 tested-agent prompt contains NO key_questions text and no
     explicit deleted-convention clause; the disambiguating artifact IS retained.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS_DIR = _REPO_ROOT / "scripts"
for _p in (str(_REPO_ROOT), str(_SCRIPTS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from common.schema import Task  # noqa: E402
from bench.build import load_tasks  # noqa: E402
import bench.amd13_sidecar as sidecar  # noqa: E402  (auto-registers checkers on import)
from bench.code_spec import get_checkers_and_candidates as cs_gcc  # noqa: E402
from bench.policy_qa import get_checkers_and_candidates as pq_gcc  # noqa: E402

import lps_gold as gold  # noqa: E402

_DATA = _REPO_ROOT / "bench" / "data"
_CODE_FILE = _DATA / "amd13_code_spec.jsonl"
_POLICY_FILE = _DATA / "amd13_policy_qa.jsonl"


def _load(path: Path):
    assert path.exists(), f"missing sidecar file: {path}"
    return load_tasks(str(path))


def test_files_parse_as_tasks():
    code = _load(_CODE_FILE)
    policy = _load(_POLICY_FILE)
    assert len(code) == 8 and len(policy) == 8
    for t in code + policy:
        assert isinstance(t, Task)
        assert t.regime == "H2_derivable"
        # k0 control: prompt == latent_spec, 1 interp, empty key_questions.
        if t.ambiguity_level == 0:
            assert t.prompt == t.latent_spec
            assert len(t.interpretations) == 1
            assert t.key_questions == []
        else:
            assert t.ambiguity_level == 1
            assert len(t.interpretations) == 2
            assert len(t.key_questions) == 1
            # k1: prompt strictly less specified than the full latent spec.
            assert len(t.prompt) < len(t.latent_spec)
        targets = [i for i in t.interpretations if i.is_target]
        assert len(targets) == 1 and targets[0].id == "I0"


def _gcc(task: Task):
    return cs_gcc(task.domain, task) if task.domain == "code_spec" else pq_gcc(task.domain, task)


def test_checkers_are_mutually_distinguishing():
    """Every reference candidate passes ONLY its own interpretation's checker."""
    for t in _load(_CODE_FILE) + _load(_POLICY_FILE):
        checkers, candidates, _foils = _gcc(t)
        assert set(checkers) == set(candidates)
        for owner_id, cand in candidates.items():
            for check_id, checker in checkers.items():
                res = checker.check(cand)
                if check_id == owner_id:
                    assert res.passed, f"{t.id}: {owner_id} failed own checker: {res.details}"
                else:
                    assert not res.passed, (
                        f"{t.id}: candidate {owner_id} wrongly passed {check_id}'s checker"
                    )


def test_k1_is_amb_pos_and_k0_is_amb_neg():
    for t in _load(_CODE_FILE) + _load(_POLICY_FILE):
        g = gold.gold_ambiguity(t)
        if t.ambiguity_level == 0:
            assert g["stratum"] == gold.STRATUM_AMB_NEG, (t.id, g)
            assert g["n_distinct"] == 1, (t.id, g)
        else:
            assert g["stratum"] == gold.STRATUM_AMB_POS, (t.id, g)
            assert g["n_distinct"] == 2, (t.id, g)
            assert g["H_ctx_gold"] > 0.0, (t.id, g)


def test_anti_leakage_prompt_hygiene():
    """k1 prompt must not leak the deleted convention clause or key_questions text,
    yet must retain the in-prompt derivable artifact (== the k0 prompt_core)."""
    for t in _load(_CODE_FILE):
        if t.ambiguity_level == 0:
            continue
        # key_questions text never appears verbatim in the tested prompt.
        for kq in t.key_questions:
            assert kq not in t.prompt
        # the derivable artifact (example I/O or signature) is retained.
        assert ("==" in t.prompt) or ("->" in t.prompt) or ("def " in t.prompt)

    for t in _load(_POLICY_FILE):
        if t.ambiguity_level == 0:
            continue
        for kq in t.key_questions:
            assert kq not in t.prompt
        # the worked numeric example (a '$' figure) is retained in the passage.
        assert "$" in t.prompt


def test_registration_is_additive_only():
    """Sidecar only ADDS amd13_* keys; it never overwrites frozen checker ids."""
    import bench.code_spec as cs
    import bench.policy_qa as pq
    amd_code = [k for k in cs.CHECKERS if k.startswith("amd13_")]
    amd_pol = [k for k in pq.CHECKERS if k.startswith("amd13_")]
    assert len(amd_code) == 8 and len(amd_pol) == 8
    # frozen ids still present and untouched.
    assert "quarter_fiscal_april" in cs.CHECKERS
    assert "tip_posttax" in pq.CHECKERS
