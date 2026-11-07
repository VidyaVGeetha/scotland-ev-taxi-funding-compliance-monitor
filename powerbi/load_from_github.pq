// Power Query (M) — load every clean table straight from this GitHub repo.
// In Power BI Desktop: Home > Transform data > New Source > Blank Query > Advanced Editor,
// paste one block per query and name the query exactly as the CSV (e.g. dim_council).
// Alternative: Get data > Text/CSV and pick the files in data/clean after cloning.

// ---- Shared parameter: create a query called BaseUrl with this text ----
"https://raw.githubusercontent.com/VidyaVGeetha/scotland-ev-taxi-funding-compliance-monitor/main/data/clean/"

// ---- dim_council ----
let
    Source = Csv.Document(Web.Contents(BaseUrl & "dim_council.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {{"ons_code", type text}, {"council", type text}, {"is_island_council", type logical}})
in
    Typed

// ---- fact_taxi_fleet ----
let
    Source = Csv.Document(Web.Contents(BaseUrl & "fact_taxi_fleet.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {
        {"ons_code", type text}, {"year", Int64.Type}, {"taxi_vehicles", type number},
        {"private_hire_cars", type number}, {"total_vehicles", type number},
        {"wheelchair_accessible_taxis", type number}, {"quality_flag", type text}, {"is_reliable", type logical}})
in
    Typed

// ---- fact_ev_taxi_funding_by_council ----
let
    Source = Csv.Document(Web.Contents(BaseUrl & "fact_ev_taxi_funding_by_council.csv"), [Delimiter = ",", Encoding = 65001]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {
        {"ons_code", type text}, {"hackney_loans_gbp", Currency.Type}, {"switched_on_taxis_gbp", Currency.Type},
        {"ev_taxi_funding_gbp", Currency.Type}, {"all_lctl_loans_gbp", Currency.Type}})
in
    Typed

// ---- fact_funding_by_year ----
let
    Source = Csv.Document(Web.Contents(BaseUrl & "fact_funding_by_year.csv"), [Delimiter = ",", Encoding = 65001]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {
        {"financial_year", type text}, {"fy_start_year", Int64.Type}, {"stream", type text},
        {"is_ev_taxi_stream", type logical}, {"amount_gbp", Currency.Type}})
in
    Typed

// ---- fact_plugin_cars ----
let
    Source = Csv.Document(Web.Contents(BaseUrl & "fact_plugin_cars.csv"), [Delimiter = ",", Encoding = 65001]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {
        {"ons_code", type text}, {"period", type text}, {"year", Int64.Type}, {"is_year_end", type logical},
        {"fuel", type text}, {"keepership", type text}, {"vehicles", Int64.Type}})
in
    Typed

// ---- council_risk_indicators, fact_loan_counts_2022_23, fact_taxi_fleet_scotland, data_quality_log ----
// Same pattern: Csv.Document(Web.Contents(BaseUrl & "<file>.csv")) > PromoteHeaders > set types.

// ---- dim_year (calculated table in DAX, not Power Query) ----
// dim_year = DATATABLE ( "year", INTEGER, { {2020}, {2021}, {2022}, {2023}, {2024}, {2025}, {2026} } )
