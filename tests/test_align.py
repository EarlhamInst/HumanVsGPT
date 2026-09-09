"""Row matching, and the assignment solver underneath it."""

import random

from manifest_compare.align import _assign, _brute_force, _hungarian


def _random_cost(rows, cols, rng):
    # Costs in use are negated similarities, hence non-positive.
    return [[-round(rng.uniform(0, 1), 3) for _ in range(cols)] for _ in range(rows)]


def test_hungarian_is_optimal_against_exhaustive_search():
    # Greedy matching can be defeated by near-ties between replicate rows, which
    # these manifests are full of, so optimality is the property that matters.
    rng = random.Random(7)
    for _ in range(120):
        cost = _random_cost(rng.randint(1, 6), rng.randint(1, 6), rng)
        assignment = _hungarian(cost)
        total = sum(cost[i][j] for i, j in enumerate(assignment) if j >= 0)
        assert total - _brute_force(cost) <= 1e-9


def test_hungarian_never_assigns_a_column_twice():
    rng = random.Random(11)
    for _ in range(120):
        cost = _random_cost(rng.randint(1, 7), rng.randint(1, 7), rng)
        used = [c for c in _hungarian(cost) if c >= 0]
        assert len(used) == len(set(used))


def test_the_two_solver_paths_agree():
    # SciPy is optional; a result must not depend on whether it is installed.
    rng = random.Random(13)
    for _ in range(80):
        cost = _random_cost(rng.randint(1, 8), rng.randint(1, 8), rng)
        fast = sum(cost[i][j] for i, j in enumerate(_assign(cost)) if j >= 0)
        pure = sum(cost[i][j] for i, j in enumerate(_hungarian(cost)) if j >= 0)
        assert abs(fast - pure) <= 1e-9


def test_empty_inputs_are_handled():
    assert _hungarian([]) == []
    assert _assign([]) == []
    assert _hungarian([[]]) == [-1]
