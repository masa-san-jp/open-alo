import unittest

from packages.providers.openai_compatible import ProviderError
from packages.studio.assistant import AssistantError, draft_alo


class FakeProviderError(ProviderError):
    pass


class StudioAssistantTests(unittest.TestCase):
    def test_returns_fenced_yaml_as_clean_text(self):
        calls = []

        def transport(payload):
            calls.append(payload)
            return {
                "choices": [
                    {
                        "message": {
                            "content": "```yaml\nalo:\n  spec_version: \"0.1\"\n```"
                        }
                    }
                ]
            }

        result = draft_alo("Route urgent support requests.", model="fake", transport=transport)

        self.assertEqual(result, 'alo:\n  spec_version: "0.1"')
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["temperature"], 0)
        self.assertEqual(calls[0]["model"], "fake")

    def test_empty_description_fails_before_transport(self):
        calls = []

        def transport(payload):
            calls.append(payload)
            return {}

        with self.assertRaises(AssistantError):
            draft_alo("  \n", model="fake", transport=transport)
        self.assertEqual(calls, [])

    def test_provider_error_propagates_unchanged(self):
        error = FakeProviderError("offline")

        def transport(payload):
            raise error

        with self.assertRaises(FakeProviderError) as context:
            draft_alo("Describe a workflow.", model="fake", transport=transport)
        self.assertIs(context.exception, error)


if __name__ == "__main__":
    unittest.main()
