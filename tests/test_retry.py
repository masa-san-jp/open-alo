import unittest

from packages.providers import (
    ProviderResponseError,
    ProviderTimeoutError,
    call_with_retry,
)


class RetryTests(unittest.TestCase):
    def test_succeeds_after_transient_failures_with_exponential_delays(self):
        attempts = 0
        delays = []

        def call():
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise ProviderTimeoutError("temporary")
            return "ok"

        result = call_with_retry(call, base_delay=0.25, sleep=delays.append)

        self.assertEqual(result, "ok")
        self.assertEqual(attempts, 3)
        self.assertEqual(delays, [0.25, 0.5])

    def test_exhaustion_reraises_the_final_exception(self):
        error = ProviderTimeoutError("still unavailable")
        attempts = 0

        def call():
            nonlocal attempts
            attempts += 1
            raise error

        with self.assertRaises(ProviderTimeoutError) as raised:
            call_with_retry(call, max_attempts=3, sleep=lambda _: None)

        self.assertIs(raised.exception, error)
        self.assertEqual(attempts, 3)

    def test_non_retryable_exception_is_not_caught(self):
        error = ProviderResponseError("malformed")
        attempts = 0

        def call():
            nonlocal attempts
            attempts += 1
            raise error

        with self.assertRaises(ProviderResponseError) as raised:
            call_with_retry(call, sleep=lambda _: self.fail("unexpected retry"))

        self.assertIs(raised.exception, error)
        self.assertEqual(attempts, 1)


if __name__ == "__main__":
    unittest.main()
