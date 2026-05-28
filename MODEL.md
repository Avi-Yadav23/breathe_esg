# Data Model Notes

## UUID Primary Keys

All models use UUID primary keys. The reasons are practical:

- **No sequence leakage across tenants.** Auto-increment PKs leak information. If tenant A creates record 1001 and tenant B creates record 1002, tenant B can infer tenant A's volume by probing adjacent IDs. UUIDs prevent this entirely.
- **Safe for external sharing.** Record identifiers appear in API responses, export files, and URLs. A UUID can be shared with an external auditor or system integrator without revealing anything about the database state.
- **No central coordination required.** IDs can be generated at the application layer before the INSERT, which simplifies bulk ingestion and eventual distributed writes.

The cost is slightly larger index size and less human-readable logs. Both are acceptable tradeoffs.

---

## RawRecord Immutability

`RawRecord` stores the original row exactly as it arrived — no normalization, no transformation, no cleaning. Once written, it is never updated.

The reason is audit trail integrity. When an analyst questions a normalized value, or when a regulator asks "what did you actually receive from SAP on this date?", the answer must be unambiguous. If the raw record could be edited post-ingestion, that question becomes unanswerable.

In practice this means:
- The ingestion pipeline writes to `RawRecord` first.
- All subsequent processing reads from `RawRecord` and writes to `NormalizedRecord`.
- No code path updates or deletes a `RawRecord`. The application layer enforces this; a database-level trigger or row-level security policy would be the production hardening step.

---

## Multi-Tenancy

Every queryable model carries a `tenant` foreign key. There is no shared data across tenants.

**Rule:** Every queryset must filter by tenant. This is enforced at the service layer. Views receive the tenant from the authenticated user's `TenantMembership` and pass it explicitly into service functions. No view constructs a raw queryset without a tenant filter.

`TenantMembership` is the join table between `User` and `Tenant`. It carries a `role` field (`analyst`, `admin`) that controls what the user can do within that tenant. A user can belong to multiple tenants; the API determines active tenant from the request context (currently: the user's primary membership; multi-tenant switching is not yet implemented).

Consequences:
- Cross-tenant queries are not possible through the normal service layer.
- Bulk admin operations (backfill, migration) must be scripted carefully and explicitly pass tenant IDs.
- Test fixtures must always include a tenant.

---

## Scope 1 / 2 / 3 Derivation

Scope classification is attached to `NormalizedRecord`. The derivation logic is:

| Scope | What it covers | How we classify it |
|-------|---------------|-------------------|
| 1 | Direct combustion — fuel burned on-site or in owned vehicles | Source type is `fuel` or `fleet`; the energy carrier is a combustible |
| 2 | Purchased electricity or heat | Source type is `utility`; commodity is `electricity` or `district_heat` |
| 3 | Value chain — travel, procurement, goods transport | Source type is `travel` or `procurement` |

Classification is rule-based and applied during normalization. It does not yet use emission factor tables (see "What the Model Does Not Handle"). The rules are encoded in `ingestion/scope_classifier.py`.

Edge cases and known gaps:
- Fugitive emissions (Scope 1) are not yet modeled — there is no source type for refrigerant leakage.
- Upstream electricity (Scope 3, category 3) is not distinguished from purchased electricity (Scope 2). This distinction requires knowing whether the electricity is for own operations or resale.
- Business travel by personal vehicle falls between Scope 3 category 6 (employee commuting) and category 7 (business travel). Currently all personal vehicle travel is classified as Scope 3/travel.

---

## Unit Normalization Philosophy

The normalization pipeline converts raw units to SI base units within the same physical quantity. The rule is:

**Convert within a physical quantity. Never convert across physical quantities without a lookup table you actually have.**

Examples of what we do:
- `kWh` → stored as `kWh` (electricity is kept in energy units, not converted to joules — analyst readability matters)
- `MWh`, `GWh` → normalized to `kWh`
- `litres`, `gallons`, `cubic feet` → normalized to `litres` for volumes
- `kg`, `tonnes`, `short tons`, `lbs` → normalized to `kg` for mass

Examples of what we deliberately do not do:
- We do not convert litres of diesel to kg. That requires a density factor (diesel density varies by grade and temperature). We store the volume as-is and flag the unit type.
- We do not convert volume of natural gas to energy content. That requires a calorific value, which varies by gas composition and country.
- We do not convert currency. Spend amounts stay in their original currency with the ISO code attached.

If a conversion would require a factor we do not have stored, the record is flagged with `unit_conversion_required = True` and passed to the analyst queue rather than silently applying a default factor.

---

## Source-of-Truth Tracking: IngestionRun and file_hash

`IngestionRun` records every file that enters the system. It stores:
- `file_hash` — SHA-256 of the raw file bytes, computed before parsing begins
- `uploaded_at` — timestamp
- `status` — `pending`, `processing`, `complete`, `failed`
- `row_count`, `error_count` — populated after processing

Before starting a new ingestion, the pipeline checks whether a `IngestionRun` with the same `file_hash` and `tenant` already exists in a non-failed state. If it does, the upload is rejected with a clear message. This prevents the common mistake of uploading the same monthly export twice when a user re-downloads a file.

Note: hash equality is a necessary but not sufficient condition for deduplication. Two different files can produce the same hash only under collision (negligible risk with SHA-256). However, a file that has been legitimately amended and re-exported will have a different hash and will be processed again — row-level deduplication handles the overlap.

---

## Audit Trail: AuditLog

`AuditLog` is append-only. Every state change on a `NormalizedRecord` writes a new row. Rows are never updated or deleted.

Each row stores:
- `actor` — the user who made the change (or `system` for automated pipeline actions)
- `timestamp` — UTC, set by the database default
- `action` — a short enum: `created`, `reviewed`, `approved`, `rejected`, `locked`, `flagged`
- `before_snapshot` — JSON of the record state before the change
- `after_snapshot` — JSON of the record state after the change

The before/after snapshots use the full serialized record, not a diff. This is intentional: storage is cheap, and reconstructing state from diffs is error-prone. A full snapshot means you can show an auditor exactly what the record looked like at any point in time without replaying a chain of patches.

Invariants:
- No code path deletes an `AuditLog` row.
- `AuditLog` has no foreign key to `NormalizedRecord` with `on_delete=CASCADE`. If a normalized record is ever deleted (edge case: full data reset), the audit log rows are retained with a null FK — the record of the action survives even if the subject does not.

---

## Why `locked_at` on NormalizedRecord (Not a Separate Status Table)

`NormalizedRecord` carries a nullable `locked_at` datetime field rather than a separate `LockedRecord` or status table.

The reasoning is simplicity. A status table would require a join on every read to determine mutability. A separate `locked_at` field means the mutability check is a single null check on the record itself:

```python
if record.locked_at is not None:
    raise RecordLockedError(record.id)
```

Once `locked_at` is set, the record is read-only at the application layer. The field is set by the `lock_record` service function, which also writes an `AuditLog` entry with action `locked`.

The field is a datetime rather than a boolean so that you know when the lock was applied, not just that it is locked. This is directly useful for audits ("these records were locked on 2024-Q4 close date").

Production hardening would add a database-level check: a trigger that raises an exception if any column other than an explicitly allowed set is updated when `locked_at IS NOT NULL`. For now, the application layer is the enforcement point.

---

## What This Model Does Not Yet Handle

The following are deliberate omissions, not oversights:

- **Emission factor tables.** Converting activity data (litres of diesel, kWh of electricity) to CO2-equivalent requires emission factors that vary by country, year, grid mix, fuel grade, and scope 3 category. This is a significant data problem in its own right. The platform produces clean, normalized activity data; a separate emissions engine consumes it.

- **CO2e computation.** Follows from the above. No GWP conversion, no CO2/CH4/N2O breakdown.

- **Currency conversion.** Spend-based Scope 3 categories need spend converted to a common currency. FX rates are time-varying and require a rates table. Not modeled.

- **Multi-period aggregations.** The model stores individual normalized records. Monthly, quarterly, and annual roll-ups are query-time operations. There is no pre-aggregated summary table. This is fine at prototype scale; a materialized view or summary table would be needed at reporting scale.

- **Emission factor versioning.** When emission factors are eventually added, they will need versioning — a record normalized against 2022 grid factors should not silently re-compute when 2023 factors are loaded.
