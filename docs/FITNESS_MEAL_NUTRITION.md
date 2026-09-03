# Fitness meal nutrition

Console, H5 and this API use the same restaurant database. This release adds
`FITNESS_MEAL` and an optional one-to-one `DishNutrition` record; existing menus,
orders and gatherings are not rewritten. Price defaults to zero on creation.

## Release order

1. Deploy the H5 commit containing Prisma migration
   `20260903090000_add_fitness_meal_nutrition` and the category metadata. Its
   deployment workflow runs `prisma migrate deploy` before building the H5.
2. Deploy this backend only after that migration succeeds. The API reads the
   new table, so deploying it before the table exists would break dish reads.
3. Verify `GET /api/chuan-dai/dish/list` returns `nutrition: null` for ordinary
   dishes, then import the two approved products via `scripts/import_fitness_chicken.py`.

The migration only adds an enum value and a table with a cascading foreign key,
numeric limits and unit constraints. It does not delete or reset data. RLS is
enabled on the new table; access is through the application's configured server
database role, not anonymous Supabase clients. Do not rerun old destructive
category migrations or use `prisma migrate reset`.

## Payload

`POST /api/chuan-dai/dish` and `PUT /api/chuan-dai/dish/:id` accept the existing
base fields and optional `nutrition`. Fitness meals require nutrition.

```json
{
  "name": "饱饱博士香煎鸡排（原味）",
  "price": 0,
  "category": "FITNESS_MEAL",
  "nutrition": {
    "basis": "PER_100G",
    "defaultServingAmount": 100,
    "servingUnit": "g",
    "caloriesKcal": 97.28,
    "proteinG": 15.4,
    "carbohydrateG": 5.9,
    "fatG": 1.2,
    "fiberG": null,
    "sugarG": 0,
    "sodiumMg": 417,
    "labelImageUrl": null
  }
}
```

- Nutrients are the **label-basis values**, not the default serving totals.
- `PER_100G` requires `g`, `PER_100ML` requires `ml`; `PER_SERVING` requires
  `piece` or `serving` and describes one item. Mass/count conversions are not
  inferred. The chicken uses 100g as the order unit (approximately one piece).
- Missing optional nutrients are `null`; measured zero stays `0`.
- Omitting nutrition on PUT preserves it; full objects replace its values.
  `null` clears it only on ordinary dishes. Category changes preserve nutrition
  unless explicitly cleared.
- Invalid payloads return business code 400. Dish and nutrition writes are one
  transaction. IDs are generated server-side if omitted.
- The importer uses deterministic IDs, refuses conflicting existing data and
  verifies a GET after creation. It requires `--apply` to upload/write anything.
- Original label energy is converted as kcal = kJ / 4.184, rounded to two
  decimals. Source kJ and saturated fat are kept in the product description.

## Tests

`.venv/bin/python -m unittest discover -s tests -v`

Tests use only in-memory SQLite. Production import uses the existing HTTP API;
test data is never inserted into production. The H5 compatibility update does
not yet implement per-order nutrition snapshots or daily meal statistics.
