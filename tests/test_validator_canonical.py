import copy
import unittest

from packages.core import load_document, validate_alo


CANONICAL_MINIMAL = load_document("examples/canonical-minimal/alo.yaml")


class CanonicalValidatorTests(unittest.TestCase):
    def test_accepts_canonical_minimal_example(self):
        self.assertEqual(validate_alo(CANONICAL_MINIMAL), [])

    def test_rejects_missing_main_obj(self):
        document = copy.deepcopy(CANONICAL_MINIMAL)
        del document["alo"]["mainObj"]
        self.assertIn("alo.mainObj is required", validate_alo(document))

    def test_rejects_missing_sub_obj_list(self):
        document = copy.deepcopy(CANONICAL_MINIMAL)
        del document["alo"]["subObjList"]
        self.assertIn("alo.subObjList is required", validate_alo(document))

    def test_rejects_missing_state(self):
        document = copy.deepcopy(CANONICAL_MINIMAL)
        del document["alo"]["State"]
        self.assertIn("alo.State is required", validate_alo(document))

    def test_rejects_missing_manager_obj(self):
        document = copy.deepcopy(CANONICAL_MINIMAL)
        del document["alo"]["managerObj"]
        self.assertIn("alo.managerObj is required", validate_alo(document))

    def test_a_decision_workflow_dag_alone_is_not_conformant(self):
        # The whole point of the correction: a decision-only shape must not
        # silently satisfy the canonical model even if it "looks complete."
        document = {
            "alo": {
                "spec_version": "0.2",
                "id": "not-canonical",
                "version": "0.1.0",
                "mainObj": {"id": "x", "purpose": "x"},
                # subObjList/State/managerObj deliberately absent.
            }
        }
        errors = validate_alo(document)
        self.assertIn("alo.subObjList is required", errors)
        self.assertIn("alo.State is required", errors)
        self.assertIn("alo.managerObj is required", errors)

    def test_accepts_optional_main_and_sub_obj_versions(self):
        document = copy.deepcopy(CANONICAL_MINIMAL)
        document["alo"]["mainObj"]["version"] = "1.2.0"
        document["alo"]["subObjList"][0]["version"] = "0.3.0"
        self.assertEqual(validate_alo(document), [])

    def test_rejects_empty_main_obj_version(self):
        document = copy.deepcopy(CANONICAL_MINIMAL)
        document["alo"]["mainObj"]["version"] = ""
        errors = validate_alo(document)
        self.assertIn("alo.mainObj.version must be a non-empty string", errors)

    def test_rejects_duplicate_sub_obj_id(self):
        document = copy.deepcopy(CANONICAL_MINIMAL)
        document["alo"]["subObjList"].append(
            copy.deepcopy(document["alo"]["subObjList"][0])
        )
        errors = validate_alo(document)
        self.assertTrue(any("duplicate subObj id" in error for error in errors))

    def test_rejects_sub_obj_missing_purpose(self):
        document = copy.deepcopy(CANONICAL_MINIMAL)
        del document["alo"]["subObjList"][0]["purpose"]
        errors = validate_alo(document)
        self.assertTrue(any("purpose must be a non-empty string" in error for error in errors))

    def test_rejects_state_field_missing_type_or_value(self):
        document = copy.deepcopy(CANONICAL_MINIMAL)
        document["alo"]["State"]["level"] = {"value": 1}
        errors = validate_alo(document)
        self.assertIn("alo.State.level.type is required", errors)

    def test_rejects_manager_obj_without_process_steps(self):
        document = copy.deepcopy(CANONICAL_MINIMAL)
        document["alo"]["managerObj"]["process"] = []
        errors = validate_alo(document)
        self.assertIn(
            "alo.managerObj.process must have at least one step", errors
        )

    def test_rejects_duplicate_process_step_id(self):
        document = copy.deepcopy(CANONICAL_MINIMAL)
        step = copy.deepcopy(document["alo"]["managerObj"]["process"][0])
        document["alo"]["managerObj"]["process"].append(step)
        errors = validate_alo(document)
        self.assertTrue(
            any("duplicate managerObj process step id" in error for error in errors)
        )

    def test_jev_calculation_type_must_be_a_known_primitive(self):
        document = copy.deepcopy(CANONICAL_MINIMAL)
        document["alo"]["managerObj"]["process"][1]["calculation"]["jev"]["type"] = "Maybe"
        errors = validate_alo(document)
        self.assertTrue(any("jev.type must be one of" in error for error in errors))

    def test_state_update_key_must_be_declared_in_state(self):
        document = copy.deepcopy(CANONICAL_MINIMAL)
        document["alo"]["managerObj"]["state_updates"] = [
            {"key": "not_declared", "value": 1}
        ]
        errors = validate_alo(document)
        self.assertTrue(
            any("is not declared in alo.State" in error for error in errors)
        )


if __name__ == "__main__":
    unittest.main()
