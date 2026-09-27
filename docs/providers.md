# Decision providers

`OpenAICompatibleProvider` accepts an injectable `transport` callable. The
callable receives the JSON Chat Completions request payload and returns the
parsed response payload, so tests can use a deterministic fake without an API
key or network access. When `transport` is omitted, the provider uses the
stdlib `urllib` transport and posts to `{base_url}/chat/completions` with the
optional Bearer token.

The test suite always supplies a fake transport; running it requires neither
an API key nor network access.
