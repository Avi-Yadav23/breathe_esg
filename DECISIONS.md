# Decision Log

This document records the significant design and integration decisions made during the prototype, with the reasoning behind each. Where alternatives were considered, they are noted.

---

## SAP Integration: Flat File over IDoc or OData

**Decision:** Ingest SAP data via flat file export (CSV/XLSX from SAP GUI or SAP Fiori).

**Alternatives considered:**

- **IDoc (Intermediate Document):** IDoc is SAP's native EDI format — XML-like, segment-based, transferred over RFC or file. The problems: it requires a direct SAP system connection (RFC port, credentials), the schema is highly version-dependent, and parsing IDoc without an SAP library adds significant complexity. No enterprise IT team will open an RFC connection to a third-party prototype.
- **OData API (SAP Gateway):** SAP exposes data via OData through an SAP Gateway layer. The problems: Gateway setup requires BASIS administrator work and authorization object configuration. Permissions for external OData access are non-trivial and go through a formal IT approval process. Not feasible in a prototype timeline.

**Why flat file:** Flat file export is the realistic enterprise offboarding method. An SAP user with the right report authorization can run a transaction, export to spreadsheet, and hand it over. No IT involvement, no network connectivity, no credentials shared with an external party. This is how enterprise ESG data collection actually works in the field.

---

## SAP: ME2M / MB51 over FI Transactions

**Decision:** Use ME2M (purchase order history) and MB51 (material document list) as the source transactions, not FI (financial accounting) transactions such as FB03 or FBL3N.

**Reasoning:** Fuel and energy consumption in SAP shows up as goods movements, not as financial postings directly. A fuel delivery is recorded as a goods receipt against a purchase order — movement type 101 in MM (Materials Management). ME2M lists purchase orders with goods receipt history; MB51 lists material documents including goods receipts.

FI transactions show the accounting entry (debit to cost center, credit to GR/IR), which gives you the amount in local currency but not the physical quantity and unit of measure. For emissions, you need the physical quantity (litres, kg, kWh) — the financial amount is secondary.

The tradeoff is that ME2M/MB51 access requires MM module authorization, which some finance-only users do not have. In practice, the ESG or facilities team typically has this access.

---

## Utility Data: CSV Portal Export over PDF Bills or Green Button API

**Decision:** Ingest utility data from CSV exports downloaded from the utility's customer portal.

**Alternatives considered:**

- **PDF bills:** Utility bills are often available as PDF. The problem: extracting structured data from PDFs requires OCR and layout parsing. PDF layouts differ across every utility and change without notice. OCR-based ingestion is fragile — misread digits in an energy reading can introduce silent errors that are hard to detect. Ruled out for a prototype that needs to be demonstrably reliable.
- **Green Button API:** Green Button is a US standard for customer-authorized utility data sharing. The problem: it requires the customer to explicitly enroll in Green Button data sharing with their utility, and not all utilities support it or have the same implementation. It also requires OAuth flow with the utility, adding a complex integration dependency. Not universally available.

**Why CSV portal export:** Every major utility has an online customer portal with a usage history download option. The CSV format is at least machine-readable without OCR. The tradeoff is that column names and date formats vary across utilities — the ingestion pipeline handles this with per-utility column mapping configs.

---

## Travel Data: Navan-Style CSV Export over Concur API

**Decision:** Ingest travel data from Navan-style CSV trip exports, not from the Concur API.

**Alternatives considered:**

- **Concur API (SAP Concur Travel & Expense):** Concur has a well-documented REST API for expense and travel data. The problem: accessing it requires OAuth 2.0 client credentials approved by the company's Concur administrator. This approval process involves IT, legal review of the data sharing agreement, and typically takes weeks. Not feasible in a prototype timeline.

**Why Navan CSV:** Navan (formerly TripActions) is a common corporate travel platform that provides clean trip-level CSV exports. The format includes origin/destination airport codes, travel class, and trip dates — the fields needed for travel emissions estimation. A user can export this themselves from the Navan portal without IT involvement.

The limitation is that Concur's export format differs from Navan's, and some companies use both. The ingestion pipeline treats these as distinct source types with separate column mappings.

---

## Ingestion Method: File Upload over API Pull

**Decision:** All data enters the system via user-initiated file upload, not via scheduled API pulls from source systems.

**Reasoning:** Enterprise IT will not provide API credentials or network access to a third-party prototype. Even where an API exists (Concur, SAP OData), the authorization process is long and involves security review. File upload puts control in the hands of the user — they decide what to share and when, without requiring their IT team to grant external access.

The downside is that file upload is manual and not continuous. In a production system, API pulls with proper IT-approved credentials would reduce manual effort and enable more frequent data updates. This is a deliberate deferral, not a permanent architectural choice.

---

## No Async Processing (No Celery)

**Decision:** File ingestion is processed synchronously in the Django request/response cycle. No Celery, no Redis, no task queue.

**Reasoning:** The files being ingested in this prototype are small — monthly exports from SAP, utility portals, or travel platforms typically contain hundreds to low thousands of rows. Synchronous processing completes in under a second for these sizes. Adding Celery and Redis adds two more services to deploy, configure, and monitor, plus a result-polling endpoint on the API, plus handling of task failures and retries. The complexity cost exceeds the benefit at prototype scale.

A production system processing large annual exports or real-time feeds would need async processing. The ingestion service layer is written to be callable from a Celery task without structural changes — it is a pure function that takes a file and tenant and returns results.

---

## No Emission Factor Computation

**Decision:** The platform does not compute CO2-equivalent figures. It produces normalized activity data only.

**Reasoning:** Emission factors are themselves a significant data problem. They vary by country, year, fuel type, electricity grid mix, and Scope 3 category. They are updated annually by bodies such as the IEA, EPA, DEFRA, and GHG Protocol. Including a partial or outdated emission factor table would be worse than omitting it — it would produce numbers that look authoritative but are potentially wrong for the customer's geography and reporting year.

The platform's output is clean, unit-normalized activity data (kWh consumed, litres of fuel, km traveled) that a dedicated emissions engine can consume. This is a deliberate boundary.

---

## Auth: Token Authentication over JWT

**Decision:** Use DRF's built-in token authentication, not JWT.

**Reasoning:** JWT adds complexity that provides no benefit in a prototype: refresh token rotation, token blacklisting on logout, token expiry handling on the client, and the subtlety that a JWT is valid until expiry even after the user's account is deactivated (requiring a blacklist to mitigate). DRF's token auth stores a single opaque token per user in the database; revoking it is a single database delete. Checking it is a single database lookup. The implementation is two lines of settings configuration and zero custom code.

For a production system with mobile clients or cross-domain single sign-on, JWT or OAuth 2.0 would be the right choice. For a prototype API consumed by a single-origin React app, token auth is sufficient and auditable.
