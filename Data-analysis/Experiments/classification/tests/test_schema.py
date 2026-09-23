"""STAP 7 tests: ClassificationResult validation, including UNKNOWN status."""
import unittest

from pydantic import ValidationError

from schemas.result import ClassificationResult


def _base_kwargs(**overrides):
    kwargs = dict(
        fragment_id="tiny_manual_fixture",
        center_turn_id=2,
        context_turn_ids=[1, 2],
        indicator_id="PLACEHOLDER_INDICATOR",
        detected=True,
        evidence="fixed mock evidence",
        status="OK",
        model_name="mock",
        model_version="0.1",
        prompt_version="placeholder-v0",
    )
    kwargs.update(overrides)
    return kwargs


class TestClassificationResultSchema(unittest.TestCase):
    def test_valid_ok_result(self):
        result = ClassificationResult(**_base_kwargs())
        self.assertEqual(result.status, "OK")
        self.assertTrue(result.detected)

    def test_unknown_status_allows_none_detected_and_evidence(self):
        result = ClassificationResult(**_base_kwargs(status="UNKNOWN", detected=None, evidence=None))
        self.assertEqual(result.status, "UNKNOWN")
        self.assertIsNone(result.detected)

    def test_invalid_status_rejected(self):
        with self.assertRaises(ValidationError):
            ClassificationResult(**_base_kwargs(status="MAYBE"))

    def test_center_turn_must_be_in_context_turn_ids(self):
        with self.assertRaises(ValidationError):
            ClassificationResult(**_base_kwargs(center_turn_id=99, context_turn_ids=[1, 2]))

    def test_missing_required_field_rejected(self):
        kwargs = _base_kwargs()
        del kwargs["model_name"]
        with self.assertRaises(ValidationError):
            ClassificationResult(**kwargs)


if __name__ == "__main__":
    unittest.main()
