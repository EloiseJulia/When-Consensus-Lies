"""Secondary-metric tests: marginal_rho = mean pairwise error correlation.

Locks in the corrected semantics (corr(E_i, E_j) over binary error vectors),
NOT a majority-share. marginal_rho is the SECONDARY bridge metric; the primary
metric remains convergent_delusion (false_consensus_rate).
"""

from harness.metrics import marginal_rho, error_indicators


def test_error_indicators():
    assert error_indicators(["I0", "I1", "I0", "I_perp"], "I0") == [0, 1, 0, 1]


def test_perfectly_correlated_errors():
    """Two agents err on exactly the same tasks -> rho = 1.0."""
    matrix = [[1, 0, 1, 0], [1, 0, 1, 0]]
    assert marginal_rho(matrix) == 1.0


def test_perfectly_anticorrelated_errors():
    """Errors never co-occur -> rho = -1.0 (impossible for a majority-share impl)."""
    matrix = [[1, 0, 1, 0], [0, 1, 0, 1]]
    assert marginal_rho(matrix) == -1.0


def test_all_correct_has_zero_rho_not_one():
    """No errors -> no variance to correlate -> 0.0 (guards the old ρ=1.0 bug)."""
    matrix = [[0, 0, 0], [0, 0, 0]]
    assert marginal_rho(matrix) == 0.0


def test_all_wrong_has_zero_rho_not_one():
    """Constant all-error series is undefined variance -> 0.0, not spurious 1.0."""
    matrix = [[1, 1, 1], [1, 1, 1]]
    assert marginal_rho(matrix) == 0.0


def test_single_agent_returns_zero():
    assert marginal_rho([[1, 0, 1]]) == 0.0
