# Deliberate Non-Builds

This document describes three significant features that were considered and deliberately not built. Each entry explains what was scoped out, why, and what a real production implementation would look like.

---

## 1. Async Processing (Celery / Redis)

**What was not built:** A background task queue for file ingestion. Files are currently parsed and processed synchronously within the Django request/response cycle.

**Why it was not built:** The files in scope are small. A monthly SAP ME2M export, a utility portal CSV, or a Navan trip export typically contains a few hundred to a few thousand rows. Synchronous processing of these completes in well under a second on any modern hardware. The cost of adding Celery and Redis — two additional services to deploy, configure, monitor, and maintain — is not justified by the file sizes being processed.

Adding a task queue would also require:
- A result-polling endpoint so the frontend can show ingestion progress
- Handling of task failures and retries with appropriate user feedback
- Dead-letter queue behavior for repeatedly failing tasks
- Celery worker deployment alongside the web process

None of these add value when the synchronous path is faster than the HTTP round-trip.

**What production would need:** Any file over roughly 50,000 rows, or any scenario where ingestion latency would block the user, warrants async processing. A production implementation would use Celery with a Redis or RabbitMQ broker. The ingestion service layer in this codebase is written as a pure function (`ingest_file(file, tenant)`) that returns a result object — it is already structured to be called from a Celery task without modification. The missing pieces are the task wrapper, the status endpoint, and the worker deployment config.

---

## 2. Emission Factor Computation (CO2e)

**What was not built:** Conversion of activity data to CO2-equivalent (CO2e) figures. The platform produces normalized activity data — kWh, litres, tonne-km — but does not multiply these by emission factors.

**Why it was not built:** Emission factors are themselves a significant and unresolved data problem. They vary along multiple dimensions simultaneously:

- **Geography:** The emission factor for grid electricity in Norway (mostly hydro) is an order of magnitude lower than in Poland (mostly coal). Applying a wrong country factor produces a number that looks precise but is systematically wrong.
- **Year:** Factors are updated annually as grid mixes shift. A 2019 factor applied to 2024 activity data is incorrect.
- **Fuel type and grade:** Diesel emission factors differ between EN 590 road diesel and marine gas oil. Natural gas factors differ by calorific value, which varies by gas composition.
- **Scope 3 category:** Scope 3 emission factors for purchased goods require spend-based or physical-quantity-based factors by commodity type, which vary by supplier geography and production method.
- **Reporting framework:** DEFRA, EPA, GHG Protocol, and IPCC publish different factor sets with different system boundaries and GWP values.

Including a partial emission factor table — covering only some geographies, only some fuel types, only current year — would produce numbers that appear authoritative but are wrong for any customer outside the covered parameters. A customer using the wrong factors for their jurisdiction and reporting year could produce a materially incorrect disclosure.

The platform delivers clean, normalized activity data. An emissions engine that correctly manages factor versioning, geography, and framework selection consumes this data. This boundary is a feature, not a limitation.

**What production would need:** A factor table with at minimum: source (DEFRA/EPA/GHG Protocol), version/year, geography, activity type, unit, CO2 factor, CH4 factor, N2O factor, and GWP basis. A versioning system so that historical records are always computed against the factor version that was current at the time of reporting. A re-computation job for when factors are updated. A UI to show which factor version was applied to which records.

---

## 3. Cross-Run Duplicate Detection

**What was not built:** Full fuzzy duplicate detection across historical ingestion runs.

**What is built:** The current deduplication logic checks two things:
1. File-level: if the SHA-256 hash of an uploaded file matches an existing `IngestionRun` for the same tenant, the upload is rejected immediately.
2. Row-level within a run: duplicate rows within the same upload are detected and collapsed.

**Why full dedup was not built:** True cross-run deduplication — identifying that a row in the current upload refers to the same real-world event as a row ingested three months ago — requires fuzzy matching. Exact key matching on source identifiers (SAP document number, utility account + billing period) handles the clean cases but misses:

- Records where the source system has re-keyed the document
- Records where a partial month was re-exported with additional rows
- Records where the same event appears in two different source exports (e.g., a fuel purchase appearing in both a fleet system export and a SAP goods receipt export)

Fuzzy matching across potentially millions of historical records is a non-trivial engineering and data quality problem. Getting it wrong in either direction is costly: false positives silently drop valid records; false negatives double-count real emissions.

**What production would need:** A configurable deduplication key per source type (e.g., for SAP: material document number + line item; for utility: account number + billing period start date). Exact matching on these keys as the first pass. A review queue for candidate duplicates that do not match exactly but score above a similarity threshold. Analyst sign-off before a cross-run duplicate is suppressed. This is deferred to v2 of the ingestion pipeline.
