# scripts/mysql_to_duckdb.py
#
# This script:
#  1) Connects to MySQL and pulls your eight dwpikp tables into pandas DataFrames.
#  2) Writes those DataFrames into a DuckDB database (dwpikp.duckdb).
#  3) Creates a star‐schema view `fact_with_dim` (including kupec_id for KPI 3).
#  4) Computes three KPIs (with their research‐question breakdowns):
#       KPI 1: Avg spend per transaction (overall, by discount, by new/returning)
#       KPI 2: Conversion rate (overall, by discount, by year/month)
#       KPI 3: % of e-commerce customers by education level (izobrazba)
#  5) Saves three (actually four) matplotlib charts:
#       • KPI1 ⇒ kpi1_avg_spend_by_discount.png
#       • KPI2 ⇒ kpi2_conversion_rate_over_time.png
#       • KPI3 ⇒ kpi3_pct_by_education.png          (drops any NULL izobrazba)
#       • KPI3 ⇒ kpi3_pct_by_education_filled.png   (fills NULL with “Nepojasnjena izobrazba”)
#
import os
import duckdb
import pandas as pd
import mysql.connector
import matplotlib.pyplot as plt

# --- CONFIGURE THESE VARIABLES ---
MYSQL_HOST     = "localhost"        # or your MySQL server IP/hostname
MYSQL_PORT     = 3306               # default MySQL port
MYSQL_USER     = "root"             # your MySQL user
MYSQL_PASSWORD = "nekipass123"      # your MySQL password
MYSQL_DATABASE = "dwpikp"           # your schema name

PROJECT_ROOT   = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DUCKDB_PATH    = os.path.join(PROJECT_ROOT, "duckdb_database", "dwpikp.duckdb")

# Ensure the duckdb_database folder exists
os.makedirs(os.path.dirname(DUCKDB_PATH), exist_ok=True)


# -----------------------------------------------------------------------------
# 1) CONNECT TO MySQL and load all eight tables into pandas DataFrames
# -----------------------------------------------------------------------------
print("▶ Connecting to MySQL...")
mysql_conn = mysql.connector.connect(
    host=MYSQL_HOST,
    port=MYSQL_PORT,
    user=MYSQL_USER,
    password=MYSQL_PASSWORD,
    database=MYSQL_DATABASE
)

tables = [
    "Cas",
    "Izdelek",
    "Kupec",
    "Lokacija",
    "Popust",
    "SocioekonomskiProfil",
    "Demografija",
    "tabela_dejstev"
]

print("▶ Reading tables from MySQL into pandas DataFrames...")
dfs = {}
for tbl in tables:
    print(f"   • Pulling `{tbl}` ...", end=" ")
    query = f"SELECT * FROM {tbl};"
    dfs[tbl] = pd.read_sql(query, mysql_conn)
    print(f"→ Read {len(dfs[tbl])} rows from `{tbl}`")

mysql_conn.close()


# -----------------------------------------------------------------------------
# 2) OPEN (OR CREATE) the DuckDB database and load those DataFrames as tables
# -----------------------------------------------------------------------------
print("\n▶ Creating/Opening DuckDB database at:", DUCKDB_PATH)
duck_conn = duckdb.connect(database=DUCKDB_PATH, read_only=False)

for tbl, df in dfs.items():
    print(f"   • Registering DataFrame for `{tbl}` in DuckDB...")
    temp_name = f"df_{tbl}"
    duck_conn.register(temp_name, df)
    print(f"       → Creating DuckDB table `{tbl}` AS SELECT * FROM `{temp_name}`")
    duck_conn.execute(f"DROP TABLE IF EXISTS {tbl};")
    duck_conn.execute(f"CREATE TABLE {tbl} AS SELECT * FROM {temp_name};")
    duck_conn.unregister(temp_name)

print("\n▶ All tables imported into DuckDB. Current DuckDB tables:")
print(duck_conn.execute("SHOW TABLES;").fetchall())


# -----------------------------------------------------------------------------
# 3) CREATE THE STAR‐SCHEMA VIEW (`fact_with_dim`) WITH kupec_id INCLUDED
# -----------------------------------------------------------------------------
print("\n▶ Creating view `fact_with_dim` ...")
duck_conn.execute("DROP VIEW IF EXISTS fact_with_dim;")
duck_conn.execute("""
CREATE VIEW fact_with_dim AS
SELECT
  f.id                                          AS fact_id,
  f.tk_id_kupec                                 AS kupec_id,                    -- raw customer ID
  c.PolniDatum                                  AS datum,
  c.DanVTednu                                   AS dan_v_tednu,
  c.Teden                                       AS teden,
  c.Mesec                                       AS mesec,
  c.Leto                                        AS leto,
  l.Drzava                                      AS drzava,
  l.Mesto                                       AS mesto,
  k.novAliVracajoc                              AS kupec_status,               -- 'Nov' vs 'Vračajoč'
  k.steviloTransakcij                           AS steviloTransakcijKupec,
  i.Koda                                        AS izdelek_koda,
  i.NazivIzdelka                                AS izdelek_naziv,
  i.Kategorija                                  AS kategorija,
  i.Cena                                        AS cena_izdelek,
  p.popustUporabljen                            AS popust_uporabljen,          -- 'Yes' / 'No'
  s.izobrazbenaRaven                            AS izobrazba,                  -- education level
  s.zaposlitveniStatus                          AS zaposlitveni_status,
  d.spol                                        AS spol,                       -- 'Moski', 'Zenski', 'Skupno'
  d.starostnaSkupina                            AS starostna_skupina,          -- e.g. 'Od 18 do 24 let', etc.
  f.kolicinaIzdelkov                            AS kolicina_izdelkov,
  f.skupniPrihodek                              AS skupni_prihodek,
  f.povprecnoPorabljenoNaTransakcijo            AS povprecno_na_transakcijo,
  f.PoglediPredNakupom                          AS pogledi_pred_nakupom,
  f.znesekPopusta                               AS znesek_popusta,
  f.obiskiNaUporabnika                          AS obiski_na_uporabnika,
  f.steviloTransakcijPoClanstvu                 AS steviloTransakcijPoClanstvu,
  f.steviloKupcevPoDemografiji                  AS steviloKupcevPoDemografiji,
  f.stopnjaVracil                               AS stopnja_vracil
FROM tabela_dejstev f
LEFT JOIN Cas                   c ON f.tk_id_datum = c.idDatum
LEFT JOIN Lokacija              l ON f.tk_id_lokacija = l.idLokacija
LEFT JOIN Kupec                 k ON f.tk_id_kupec = k.idKupec
LEFT JOIN Izdelek               i ON f.tk_id_izdelek = i.idIzdelek
LEFT JOIN Popust                p ON f.tk_id_popust = p.idPopust
LEFT JOIN SocioekonomskiProfil  s ON f.tk_id_socioekonomski_profil = s.idSocioekonomskiProfil
LEFT JOIN Demografija           d ON f.tk_id_demografija = d.idDemografija
;
""")
print("   → View `fact_with_dim` created.\n")


# -----------------------------------------------------------------------------
# 4) RUN KPI QUERIES
# -----------------------------------------------------------------------------
print("▶ Running KPI queries against `fact_with_dim`:\n")

# -----------------------------------------------------
# KPI 1: Povprečna poraba na transakcijo
# -----------------------------------------------------
kpi1_overall = duck_conn.execute("""
  SELECT
    AVG(povprecno_na_transakcijo) AS avg_spend_per_transaction
  FROM fact_with_dim;
""").fetchone()[0]
print(f"KPI 1 (Overall) – Povprečna poraba na transakcijo: {kpi1_overall:.2f}")

kpi1_by_discount = duck_conn.execute("""
  SELECT
    popust_uporabljen,
    AVG(povprecno_na_transakcijo) AS avg_spend
  FROM fact_with_dim
  GROUP BY popust_uporabljen;
""").df()
print("\nKPI 1 – Povprečna poraba glede na popust_uporabljen:")
print(kpi1_by_discount)

kpi1_by_customer_type = duck_conn.execute("""
  SELECT
    kupec_status,
    AVG(povprecno_na_transakcijo) AS avg_spend
  FROM fact_with_dim
  GROUP BY kupec_status;
""").df()
print("\nKPI 1 – Povprečna poraba: Nov vs. Vračajoč:")
print(kpi1_by_customer_type)


# -----------------------------------------------------
# KPI 2: Stopnja konverzije
# -----------------------------------------------------
kpi2_overall = duck_conn.execute("""
  SELECT
    100.0 * COUNT(*) / NULLIF(SUM(obiski_na_uporabnika), 0) AS conversion_rate_percent
  FROM fact_with_dim;
""").fetchone()[0]
print(f"\nKPI 2 (Overall) – Stopnja konverzije: {kpi2_overall:.2f}%")

kpi2_by_discount = duck_conn.execute("""
  SELECT
    popust_uporabljen,
    100.0 * COUNT(*) / NULLIF(SUM(obiski_na_uporabnika), 0) AS conv_rate_percent
  FROM fact_with_dim
  GROUP BY popust_uporabljen;
""").df()
print("\nKPI 2 – Stopnja konverzije glede na popust_uporabljen:")
print(kpi2_by_discount)

kpi2_by_time = duck_conn.execute("""
  SELECT
    leto,
    mesec,
    100.0 * COUNT(*) / NULLIF(SUM(obiski_na_uporabnika), 0) AS conv_rate_percent
  FROM fact_with_dim
  GROUP BY leto, mesec
  ORDER BY leto, mesec;
""").df()
print("\nKPI 2 – Stopnja konverzije po letih in mesecih:")
print(kpi2_by_time)


# -----------------------------------------------------
# KPI 3: Delež e-trgovinskih kupcev glede na izobrazbo
# -----------------------------------------------------
# (We will ignore starostna_skupina for KPI 3 and use izobrazba instead.)

# 4g) Total distinct customers for denominator
total_customers = duck_conn.execute("""
  SELECT COUNT(DISTINCT kupec_id) 
  FROM fact_with_dim;
""").fetchone()[0]

# 4h) Percentage by education level (izobrazba)
kpi3_by_education = duck_conn.execute(f"""
  WITH unique_customers AS (
    SELECT DISTINCT kupec_id, izobrazba
    FROM fact_with_dim
  )
  SELECT
    izobrazba,
    100.0 * COUNT(*) / {total_customers} AS pct_of_customers
  FROM unique_customers
  GROUP BY izobrazba
  ORDER BY izobrazba;
""").df()
print(f"\nKPI 3 – Delež kupcev po izobrazbeni ravni (skupno kupcev = {total_customers}):")
print(kpi3_by_education)




# -----------------------------------------------------------------------------
# 5) VISUALIZATIONS (MATPLOTLIB)
#     – KPI 1 chart (bar): kpi1_avg_spend_by_discount.png
#     – KPI 2 chart (line): kpi2_conversion_rate_over_time.png
#     – KPI 3 chart (bar): kpi3_pct_by_education.png (drop NULL izobrazba)
#     – KPI 3 chart (bar): kpi3_pct_by_education_filled.png (fill NULL with "Nepojasnjena izobrazba")
# -----------------------------------------------------------------------------

screenshots_dir = os.path.join(PROJECT_ROOT, "documentation", "screenshots")
os.makedirs(screenshots_dir, exist_ok=True)

# 5a) KPI 1: Avg spend by discount usage
plt.figure(figsize=(6,4))
plt.bar(
    kpi1_by_discount["popust_uporabljen"].astype(str),
    kpi1_by_discount["avg_spend"]
)
plt.title("KPI 1: Povprečna poraba na transakcijo (po popust_uporabljen)")
plt.xlabel("Popust uporabljen")
plt.ylabel("Povprečna poraba")
plt.grid(axis="y", linestyle="--", alpha=0.5)
out_kpi1 = os.path.join(screenshots_dir, "kpi1_avg_spend_by_discount.png")
plt.savefig(out_kpi1, dpi=150, bbox_inches="tight")
print(f"\nSaved KPI 1 chart → {out_kpi1}")
plt.close()

# 5b) KPI 2: Conversion rate over time (Year + Month)
plt.figure(figsize=(8, 5))
for year in kpi2_by_time["leto"].unique():
    subset = kpi2_by_time[kpi2_by_time["leto"] == year]
    plt.plot(
        subset["mesec"],
        subset["conv_rate_percent"],
        marker="o",
        label=str(year)
    )
plt.title("KPI 2: Stopnja konverzije po letih in mesecih")
plt.xlabel("Mesec")
plt.ylabel("Stopnja konverzije (%)")
plt.xticks(range(1, 13))
plt.legend(title="Leto")
plt.grid(linestyle="--", alpha=0.5)
out_kpi2 = os.path.join(screenshots_dir, "kpi2_conversion_rate_over_time.png")
plt.savefig(out_kpi2, dpi=150, bbox_inches="tight")
print(f"Saved KPI 2 chart → {out_kpi2}\n")
plt.close()

# 5c) KPI 3: Percentage of customers by education level (drop NULL)
df_kpi3_edu = kpi3_by_education.dropna(subset=["izobrazba", "pct_of_customers"])

plt.figure(figsize=(8, 5))
plt.bar(
    df_kpi3_edu["izobrazba"].astype(str),
    df_kpi3_edu["pct_of_customers"]
)
plt.title("KPI 3: Delež e-trgovinskih kupcev po izobrazbeni ravni")
plt.xlabel("Izobrazbena raven")
plt.ylabel("Delež kupcev (%)")
plt.xticks(rotation=45, ha="right")
plt.grid(axis="y", linestyle="--", alpha=0.5)
out_kpi3_edu = os.path.join(screenshots_dir, "kpi3_pct_by_education.png")
plt.savefig(out_kpi3_edu, dpi=150, bbox_inches="tight")
print(f"Saved KPI 3 chart (by education, dropping NULL) → {out_kpi3_edu}")
plt.close()



duck_conn.close()
print("\n▶ Done. DuckDB file is at:", DUCKDB_PATH)
