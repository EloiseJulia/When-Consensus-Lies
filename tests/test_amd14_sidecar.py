# constructed by: Claude (Anthropic) family
"""Offline self-check gate for the Amendment 14 SIDECAR items (additive).

# Implementer model family: Claude / Anthropic (orchestration); item semantics: mai-code-1-flash
# Auditor model family: MUST be non-Anthropic (Law 6 — cross-family requirement)

The Amendment 14 sidecar is the UNFILTERED-sample replication (RATIFIED prereg
2026-07-23): underspecified items built by the SAME reversal rule as the frozen
benchmark (a genuine non-default I0 in the hidden latent_spec + a DELETED EXTERNAL
disambiguator), KEPT regardless of expected model behavior (no default-screen
inclusion filter). All checks are OFFLINE, deterministic, no network / no LLM judge:

  1. Sidecar jsonl parse under common.schema.Task and match the frozen schema shape
     (k0 control: prompt==latent_spec, 1 interp; k1: H1_external, 2 interps, 1 kq).
  2. Executable gold checkers RUN: every reference candidate passes ONLY its own
     interpretation's checker (mutual distinguishability), like the frozen families.
  3. lps_gold.gold_ambiguity classifies each k1 as AMB+ (distinguishable) and each
     k0 as AMB- — i.e. the enumerated interpretations are genuinely distinct where
     the item is meant to be ambiguous.
  4. Anti-leakage: the k1 tested-agent prompt contains NO key_questions text and NO
     fragment of the deleted disambiguator clause, and is strictly less specified
     than the latent_spec.
  5. Additive-only registration: the sidecar only ADDS amd14_* checker ids; it never
     overwrites a frozen checker id (cannot shadow frozen ids).
  6. Unfiltered-sample integrity (AUDITABLE no-filter guarantee): the items biject
     with a pre-declared enumeration FRAME of (domain x convention-axis) cells (none
     dropped) — so a silent cherry-pick would fail CI — and the pooled
     amd14_unfiltered.jsonl equals the union of the per-domain sidecar files. The
     constructor's default-pull tags are non-authoritative and gate nothing.
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
import bench.amd14_sidecar as sidecar  # noqa: E402  (auto-registers checkers on import)
from bench.code_spec import get_checkers_and_candidates as cs_gcc  # noqa: E402
from bench.policy_qa import get_checkers_and_candidates as pq_gcc  # noqa: E402
from bench.data_analysis import get_checkers_and_candidates as da_gcc  # noqa: E402

import lps_gold as gold  # noqa: E402

_DATA = _REPO_ROOT / "bench" / "data"
_CODE_FILE = _DATA / "amd14_code_spec.jsonl"
_POLICY_FILE = _DATA / "amd14_policy_qa.jsonl"
_DATAAN_FILE = _DATA / "amd14_data_analysis.jsonl"
_POOL_FILE = _DATA / "amd14_unfiltered.jsonl"

_GCC = {"code_spec": cs_gcc, "policy_qa": pq_gcc, "data_analysis": da_gcc}


def _load(path: Path):
    assert path.exists(), f"missing sidecar file: {path}"
    return load_tasks(str(path))


def _all_tasks():
    return _load(_CODE_FILE) + _load(_POLICY_FILE) + _load(_DATAAN_FILE)


def test_files_parse_as_tasks():
    code = _load(_CODE_FILE)
    policy = _load(_POLICY_FILE)
    dataan = _load(_DATAAN_FILE)
    assert len(code) == 20 and len(policy) == 16 and len(dataan) == 12
    for t in code + policy + dataan:
        assert isinstance(t, Task)
        # The unfiltered replication mirrors the frozen H1_external construction:
        # a deleted EXTERNAL disambiguator (not derivable from the tested prompt).
        assert t.regime == "H1_external"
        if t.ambiguity_level == 0:
            # k0 control: prompt == latent_spec, single interp, no clarifying q.
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


def test_checkers_are_mutually_distinguishing():
    """Every reference candidate passes ONLY its own interpretation's checker."""
    for t in _all_tasks():
        checkers, candidates, _foils = _GCC[t.domain](t.domain, t)
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
    """Interpretations are genuinely distinct where the item is meant ambiguous."""
    for t in _all_tasks():
        g = gold.gold_ambiguity(t)
        if t.ambiguity_level == 0:
            assert g["stratum"] == gold.STRATUM_AMB_NEG, (t.id, g)
            assert g["n_distinct"] == 1, (t.id, g)
        else:
            assert g["stratum"] == gold.STRATUM_AMB_POS, (t.id, g)
            assert g["n_distinct"] == 2, (t.id, g)
            assert g["H_ctx_gold"] > 0.0, (t.id, g)


def test_anti_leakage_prompt_hygiene():
    """k1 prompt must not leak the deleted convention clause or key_questions text.

    Unlike the H2_derivable Amendment 13 sidecar, these H1_external items retain NO
    disambiguating artifact: the deleted clause is EXTERNAL and must vanish entirely
    from the tested prompt.
    """
    for t in _all_tasks():
        if t.ambiguity_level == 0:
            continue
        for kq in t.key_questions:
            assert kq not in t.prompt, f"{t.id}: key_question leaked into prompt"
        # The deleted disambiguator is exactly the latent_spec text absent from prompt.
        deleted = t.latent_spec.replace(t.prompt, "").strip()
        assert deleted, f"{t.id}: no detectable deleted clause"
        assert deleted not in t.prompt, f"{t.id}: deleted clause present in prompt"
        # Prompt is strictly less specified (the disambiguator was removed).
        assert len(t.prompt) < len(t.latent_spec)


def test_registration_is_additive_only():
    """Sidecar only ADDS amd14_* keys; it never overwrites frozen checker ids."""
    import bench.code_spec as cs
    import bench.policy_qa as pq
    import bench.data_analysis as da

    amd_code = [k for k in cs.CHECKERS if k.startswith("amd14_")]
    amd_pol = [k for k in pq.CHECKERS if k.startswith("amd14_")]
    amd_data = [k for k in da.CHECKERS if k.startswith("amd14_")]
    # 24 base items x 2 interpretations = 48 checker ids, split across domains.
    assert len(amd_code) == 20  # 10 code_spec items x 2
    assert len(amd_pol) == 16   # 8 policy_qa items x 2
    assert len(amd_data) == 12  # 6 data_analysis items x 2

    # Frozen ids still present and untouched (never shadowed).
    assert "quarter_fiscal_april" in cs.CHECKERS
    assert "overtime_ot35" in pq.CHECKERS
    assert "typical_median" in da.CHECKERS

    # Idempotent + non-destructive: a second register() must not change anything.
    before = (dict(cs.CHECKERS), dict(pq.CHECKERS), dict(da.CHECKERS))
    sidecar.register()
    assert (cs.CHECKERS, pq.CHECKERS, da.CHECKERS) == before

    # amd14 ids can never collide with a frozen id (prefix guarantee).
    for cid in amd_code + amd_pol + amd_data:
        assert cid.startswith("amd14_")


def test_sidecar_cannot_shadow_frozen_ids():
    """Directly assert setdefault semantics: re-registering a frozen id is a no-op."""
    import bench.code_spec as cs

    frozen_id = "quarter_fiscal_april"
    original = cs.CHECKERS[frozen_id]
    cs.CHECKERS.setdefault(frozen_id, object())  # what register() does
    assert cs.CHECKERS[frozen_id] is original


def test_unfiltered_sample_covers_the_declared_frame():
    """AUDITABLE no-filter guarantee: the items biject with the declared FRAME.

    Amendment 14's credibility rests on including the ENTIRE pre-declared enumeration
    frame of (domain x convention-axis) cells and dropping NONE. If a candidate item
    had been silently cherry-picked/discarded during construction, the realized cells
    would no longer equal the frame and this test would FAIL. This does NOT rely on
    trusting the constructor's self-assigned pull tags.
    """
    frame = sidecar.frame_cells()
    realized = sidecar.item_cells()
    # No cell is dropped and none is duplicated: exact bijection with the frame.
    assert len(realized) == len(frame), (len(realized), len(frame))
    assert set(realized) == frame, {
        "missing": frame - set(realized),
        "extra": set(realized) - frame,
    }
    assert len(realized) == len(set(realized)), "duplicate frame cell realized"
    # Per-domain counts match the declared frame exactly.
    for dom, axes in sidecar.FRAME.items():
        got = [c for c in realized if c[0] == dom]
        assert len(got) == len(axes), (dom, len(got), len(axes))
    # Frame spans all three confirmatory domains.
    assert set(sidecar.FRAME) == {"code_spec", "policy_qa", "data_analysis"}
    assert len(frame) == 24


def test_default_pull_tags_are_non_authoritative_only():
    """The pull tags are advisory colour, never a gate; result must not depend on them.

    We only assert the tag vocabulary is well-formed. We deliberately do NOT assert any
    particular strong/even_odds ratio: the no-filter guarantee is carried by frame
    completeness, and the real default-pull is measured empirically at run time.
    """
    meta = sidecar.item_metadata()
    assert len(meta) == 24
    for m in meta:
        assert m["provisional_default_pull"] in {"strong", "even_odds"}
        assert m["axis"]  # every item records the convention axis (its frame cell)


def test_pool_file_is_union_of_domain_files():
    """The pooled unfiltered file equals the union of the per-domain sidecar files."""
    pool_ids = [t.id for t in _load(_POOL_FILE)]
    domain_ids = [t.id for t in _all_tasks()]
    assert sorted(pool_ids) == sorted(domain_ids)
    assert len(pool_ids) == 48
