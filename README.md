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

## Fidelity against the live API

`fidelity.py` sends ten requests, valid and invalid, to both the live Resend API and resend-dry, and compares the status code and error name. It uses Resend's test inbox `delivered@resend.dev`.

```
cp .env.example .env     # add RESEND_API_KEY
python fidelity.py
```

<!-- fidelity:start -->
# resend-dry fidelity, 2026-10-18

**Matched the live API's status and error name on 10 of 10 cases.**

Error messages matched word for word on 7 of 7 error cases.

| Case | Live Resend | resend-dry | Match |
|---|---|---|---|
| valid send | 200 ok | 200 ok | yes |
| text body only | 200 ok | 200 ok | yes |
| missing subject | 422 validation_error | 422 validation_error | yes |
| missing from | 422 validation_error | 422 validation_error | yes |
| missing to | 422 missing_required_field | 422 missing_required_field | yes |
| no html or text | 422 validation_error | 422 validation_error | yes |
| 51 recipients | 422 validation_error | 422 validation_error | yes |
| invalid from address | 422 validation_error | 422 validation_error | yes |
| batch of two | 200 ok | 200 ok | yes |
| batch with one bad | 422 validation_error | 422 validation_error | yes |

Live error messages, for calibrating mismatches:

- missing subject: Missing `subject` field.
- missing from: Missing `from` field.
- missing to: Missing `to` field.
- no html or text: Missing `html` or `text` field.
- 51 recipients: Field `to` has a maximum of 50 items.
- invalid from address: Invalid `from` field. The email address needs to follow the `email@example.com` or `Name <email@example.com>` format.
- batch with one bad: Missing `subject` field.
<!-- fidelity:end -->
