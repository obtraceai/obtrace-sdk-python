# Troubleshooting

## No events in ingest
- Verify `ingest_base_url` and API key.
- Enable `debug=True`.
- Confirm network egress to ingest endpoint.

## 429 or 401
- 429: server quota/rate limit.
- 401: invalid API key.
