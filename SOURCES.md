# Data Sources

This document covers each data source in the prototype: what real-world format was researched, what the sample data represents, and what would break when moving from prototype to production.

---

## SAP (Fuel and Energy Procurement)

**Real-world format researched:** SAP transaction ME2M (purchase orders with goods receipt history) and MB51 (material document list). Both can be exported from SAP GUI via List → Export → Spreadsheet or from SAP Fiori via download. The resulting file is typically XLSX or CSV with fixed column headers determined by the SAP layout variant in use.

Typical ME2M columns: Purchasing Document, Item, Material, Material Description, Plant, Storage Location, Order Quantity, Order Unit, Delivered Quantity, Delivery Unit, Net Price, Currency, Vendor, Posting Date.

MB51 adds: Movement Type, Material Document, Fiscal Year, Movement Type Description.

Movement type 101 is a goods receipt against a purchase order — this is the record created when fuel is delivered or a utilities invoice is goods-receipted.

**What the sample data represents:** The sample files simulate a manufacturing plant receiving monthly diesel and natural gas deliveries, recorded as goods receipts. Plant codes are fictional. Material numbers follow SAP's numeric convention.

**What would break in production:**

- **Custom Z-tables:** Many SAP installations route materials through custom transaction codes or Z-reports (customer-specific code prefixed with Z). The column structure in a Z-report may differ entirely from ME2M/MB51. The ingestion parser assumes standard SAP column headers; a customer using a Z-report needs a custom column mapping config.
- **Non-English material descriptions:** SAP material descriptions are stored in the logon language. A customer using German or Chinese SAP would have non-English descriptions. The description field is stored as-is; any downstream classification that relies on parsing descriptions would fail.
- **Different Werk (plant) numbering schemes:** SAP plant codes are four-character identifiers, but their meaning is client-specific. Plant "1000" at one company is a German factory; at another it is a US distribution center. Mapping plant codes to locations, business units, and reporting boundaries requires a plant lookup table sourced from the client's organizational data. The prototype uses static sample plant-to-location mappings.
- **Local currency amounts:** SAP stores purchase order amounts in the document currency. A UK subsidiary's diesel purchases may be in GBP; a Singapore entity in SGD. The ingestion pipeline stores the original currency code alongside the amount. Currency conversion requires an FX rate table that is not yet modeled (see TRADEOFFS.md).
- **Partial goods receipts:** A purchase order for 10,000 litres may have three goods receipt documents for 3,000 / 4,000 / 3,000 litres posted on different dates. The parser handles multiple rows per PO line, but the deduplication logic must be aware that the same PO line appearing across monthly exports does not mean the same physical delivery.

---

## Utility (Electricity and Gas)

**Real-world format researched:** Green Button Connect (the US standard for machine-readable utility data) and utility portal CSV exports. Green Button provides an Atom-based XML format with interval meter readings; portal CSV exports are utility-specific but typically provide monthly billing period summaries.

Common portal CSV columns (varies by utility): Account Number, Service Address, Billing Period Start, Billing Period End, kWh Used, Peak Demand (kW), Rate, Amount Due, Meter Number.

Gas bills may use therms, CCF (hundred cubic feet), or m³ depending on the utility and geography.

**What the sample data represents:** The sample files simulate monthly electricity and natural gas bills for two meter accounts at a single site, in the format of a US investor-owned utility's CSV download. Values represent plausible but fictional usage.

**What would break in production:**

- **Column name variation:** Every utility names its columns differently. "kWh Used", "Usage (kWh)", "Net kWh", and "Consumption" all mean the same thing. The ingestion parser uses a configurable column alias map; any utility not already in the alias map requires a new mapping before its files can be processed.
- **Peak vs. off-peak breakdown:** Time-of-use rate customers get bills that split consumption into peak, partial-peak, and off-peak tiers. Some utilities report these as separate rows; others as separate columns. The prototype sums all tiers into a single consumption figure. Demand-side management analytics would require the breakdown.
- **Bundled gas and electricity bills:** Some utilities issue a single bill for both gas and electricity to the same account. The CSV may have rows for both commodities. The parser must split these into separate records by commodity type.
- **Irregular billing periods:** Utility billing periods are nominally monthly but are often 28–34 days. Meters may be read on different dates each month. Aggregating to calendar months requires prorating, which introduces estimation error. The prototype stores records at billing-period granularity and leaves calendar-period aggregation to the analyst.
- **Green Button XML:** The prototype does not yet parse Green Button XML — it handles only the CSV portal export. Green Button XML is more structured and would enable automated ingestion from utilities that support it, but requires an XML parser and mapping from the Green Button schema.

---

## Travel (Business Flights and Ground Transport)

**Real-world format researched:** Navan (formerly TripActions) trip export CSV and Concur Travel itinerary export. Both platforms produce per-trip or per-segment records following a corporate travel booking. IATA airport codes are the standard identifier for origins and destinations.

Typical Navan trip export columns: Trip ID, Traveler Name, Traveler Email, Departure Date, Return Date, Origin Airport Code, Destination Airport Code, Travel Type (Air/Rail/Car), Cabin Class, Distance (miles), Cost, Currency, Cost Center.

Concur's format differs: it uses a multi-line expense report structure with separate line items for airfare, hotel, and ground transport.

**What the sample data represents:** The sample files simulate one quarter of business trips for a ten-person team, with flights between US and European cities. Airport codes are real. Distances are calculated from a static sample of major city-pair great-circle distances, not a full route database.

**What would break in production:**

- **Concur format differences:** Concur's CSV export structure is materially different from Navan's. A company using Concur would need a separate parser. Some companies run both Navan and Concur (e.g., Navan for booking, Concur for expense reimbursement). The same trip may appear in both exports. The ingestion pipeline has separate source type configs for each, but cross-system deduplication is not implemented.
- **IATA airport lookup:** The prototype uses a hardcoded sample of ~50 major airport codes mapped to city and country. A production system needs the full IATA airport database (~10,000 airports plus ICAO codes for airports not in IATA). Routes involving regional airports, private terminals, or recently renamed airports would fail to resolve without the full database.
- **Hotel emissions:** Corporate travel platforms often include hotel night bookings in the same export. Hotel emission factors depend on the hotel brand, star rating, and country — data that requires either a hotel brand emission factor database or a spend-based estimate. The prototype does not model hotel emissions; hotel rows in a travel export are currently skipped.
- **Rail and ground transport:** Train travel between European city pairs may appear in a Navan export as a trip type of "Rail." Rail emission factors vary significantly by country grid mix and rail operator. Car rental and taxi rows may have mileage or may only have cost. The prototype models air travel only; other modes are flagged for analyst review.
- **Canceled and refunded trips:** Corporate travel exports sometimes include trips that were booked and later canceled. These appear as rows with zero distance or with a "Canceled" status field. The parser checks for a status field and skips canceled rows; however, not all platforms include a status field, and some represent cancellations as a negative-amount row.
