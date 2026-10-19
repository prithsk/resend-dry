# resend-dry fidelity, 2026-10-19

**Matched the live API's status and error name on 10 of 10 cases.**

resend-dry answered in 13.1 ms median against 129 ms for the live API, 10x faster, with no rate limit and nothing sent.

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