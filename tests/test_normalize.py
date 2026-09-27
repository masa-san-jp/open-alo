import unittest

from packages.providers import (
    normalize_binary,
    normalize_categorical,
    normalize_scalar,
)


class NormalizeTests(unittest.TestCase):
    def test_normalize_binary(self):
        self.assertEqual(normalize_binary(3, 1), {"p_true": 0.75, "p_false": 0.25})

    def test_normalize_categorical(self):
        self.assertEqual(
            normalize_categorical({"technical": 3, "billing": 1}),
            {"technical": 0.75, "billing": 0.25},
        )

    def test_negative_probability_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "cannot be negative"):
            normalize_binary(-1, 2)

        with self.assertRaisesRegex(ValueError, "cannot be negative"):
            normalize_categorical({"technical": -1, "billing": 2})

    def test_zero_total_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "positive total"):
            normalize_binary(0, 0)

        with self.assertRaisesRegex(ValueError, "positive total"):
            normalize_categorical({"technical": 0, "billing": 0})

    def test_scalar_accepts_inclusive_bounds(self):
        self.assertEqual(
            normalize_scalar(0, 0, {"min": 0, "max": 10}),
            {"score": 0.0, "confidence": 0.0},
        )
        self.assertEqual(
            normalize_scalar(10, 1, {"min": 0, "max": 10}),
            {"score": 10.0, "confidence": 1.0},
        )

    def test_scalar_rejects_out_of_scale_score(self):
        with self.assertRaisesRegex(ValueError, "outside scale"):
            normalize_scalar(11, 0.5, {"min": 0, "max": 10})

    def test_scalar_rejects_out_of_range_confidence(self):
        with self.assertRaisesRegex(ValueError, "between 0 and 1"):
            normalize_scalar(5, 1.1, {"min": 0, "max": 10})


if __name__ == "__main__":
    unittest.main()
