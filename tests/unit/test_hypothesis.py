from backend.hypothesis import HypothesisValidator


def test_hypothesis_passes_when_checks_succeed():
    validator = HypothesisValidator()
    assert validator.evaluate([{"value": 2, "threshold": 1}]) is True
