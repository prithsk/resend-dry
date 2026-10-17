# resend-dry

A local Resend that doesn't send. Every email lands in a browsable outbox.

Point your SDK's base URL at `http://localhost:3123` in dev. `POST /emails` and `POST /emails/batch` are accepted, validated the way Resend validates, stored to disk, and shown at `/` with the rendered HTML. Nothing leaves your machine.

```
python resend_dry.py                    # http://localhost:3123
python resend_dry.py --port 4000 --store ./outbox
```

Responses match Resend's shape: `200 {"id": ...}` on success, `422 {"name": "validation_error", "message": ...}` on a missing `from`, `to`, `subject` or body, on more than 50 recipients, and on bad JSON. So the failures you'd hit in prod show up in dev.

Zero dependencies, standard library only. Set `RESEND_BASE_URL` or your SDK's `baseUrl` option.

## Tests

```
python3 test_resend_dry.py
```

## License

MIT
