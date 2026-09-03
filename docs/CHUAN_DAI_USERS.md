# Chuan Dai console users

The console `/chuan-dai/users` page reads the H5 application's existing `User`
table through `DATABASE_URL_RESTAURANT`. Console login accounts remain in
`app_user` in the default database.

## API

Both endpoints require a valid console JWT and an existing console account with
the `admin` or `super_admin` role. Restaurant `HOST`/`GUEST` roles are separate
from these console permissions.

- `GET /api/chuan-dai/user/list`: accepts `pageNumber` (default 1), `pageSize`
  (default 10, maximum 100), `keyword` (account/nickname/phone, up to 100
  characters) and `role` (empty, `HOST`, or `GUEST`). Search is case-insensitive
  and treats `%` and `_` literally. Results are ordered by creation time
  descending, then ID, and out-of-range pages are clamped to the final page.
  Returns `{code: 200, data: {items, total, pageNumber, pageSize}, message}`.
- `GET /api/chuan-dai/user/:id`: returns the current profile or business code
  404 if it no longer exists.
- `POST /api/chuan-dai/user/:id/reset-password`: accepts `newPassword` and
  `confirmPassword`. Requires 6–64 UTF-16 code units, at least one ASCII letter
  and digit, and matching confirmation. Cookie authentication also requires
  the JWT `X-CSRF-TOKEN` header. No old password is needed for this admin action.
  Uses Argon2id PHC hashes compatible with H5's `@node-rs/argon2` verifier.
  Updates the password and `updatedAt`, removes all of the target user's H5
  sessions and clears their account login failure key in a single transaction.
  Other users' sessions and shared IP rate limits are preserved. Returns only
  `{code: 200, data: {id}, message}`; plaintext passwords and hashes are never
  returned or written to application logs. Audit logs record the actor and
  target IDs. IP throttling, if active, still expires on its normal schedule.

Responses use the existing business-code convention. Only explicitly mapped
profile fields are queried for list/detail; the password hash is deferred and
excluded from serialization. Login IPs and sessions are not returned.
Timestamp fields include UTC offsets. Birthday is returned as a date.

## Release

Deploy `server-console` first, then `portal-console-web`. No database migration
or user import is required. The model uses restaurant-only SQLAlchemy metadata
and does not add a `User` table to the console database.

After release, sign in as a console administrator and open
`https://console.tt829.cn/chuan-dai/users`. Check the list, search, role filters,
pagination and details. Use the row's **重置密码** button to set a new password
without knowing the old one. A failed request must show an error and retry action,
not a successful empty list. Users continue to register through the H5 app.

## Verification

Run offline tests with:

```sh
.venv/bin/python -m unittest tests.test_restaurant_user_api tests.test_dish_api -q
```

These tests use separate in-memory SQLite databases and never connect to the
configured production database. They cover admin authorization, database
isolation, paging, filters, wildcard escaping, empty results, invalid input,
safe profile serialization and database failure handling. Reset tests also cover
password validation, unchanged unrelated users, cookie CSRF protection and
transaction rollback if session revocation fails. New hashes were additionally
verified with the H5 application's actual `@node-rs/argon2` implementation:
the new password succeeds and the old password fails.
