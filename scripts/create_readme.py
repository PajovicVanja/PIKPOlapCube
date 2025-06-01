# scripts/generate_readme.py

import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.lib import utils
from textwrap import wrap

# --- CONFIGURE PATHS AND LABELS ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DOCS_ROOT    = os.path.join(PROJECT_ROOT, "documentation")
IMG_DIR      = os.path.join(DOCS_ROOT, "screenshots")
OUTPUT_PDF   = os.path.join(DOCS_ROOT, "README.pdf")

# Filenames of the images we want to embed (must exactly match your filenames):
IMAGES = {
    "duckdb_schema": "duckdb_schema.png",
    "sample_rows":   "sample_query_results.png",
    "kpi1_chart":    "kpi1_avg_spend_by_discount.png",
    "kpi2_chart":    "kpi2_conversion_rate_over_time.png",
    "kpi3_chart":    "kpi3_pct_by_age_filled.png",
}

def scale_image(path, max_width, max_height):
    """
    Returns (width, height) scaled so that:
      - width <= max_width
      - height <= max_height
    while preserving aspect ratio.
    """
    img = utils.ImageReader(path)
    orig_width, orig_height = img.getSize()
    ratio = min(max_width / orig_width, max_height / orig_height)
    return orig_width * ratio, orig_height * ratio

def draw_wrapped_text(c: canvas.Canvas, text: str, x, y, max_width,
                      font_name="Helvetica", font_size=10, leading=None):
    """
    Wraps 'text' to fit within max_width, then draws line by line
    starting at (x,y) going downward. Returns the final y-coordinate.
    """
    if leading is None:
        leading = font_size * 1.2

    c.setFont(font_name, font_size)
    wrapped_lines = []
    for paragraph in text.split("\n"):
        wrapped_lines.extend(
            wrap(paragraph, width=int(max_width / (font_size * 0.57)))
        )
        wrapped_lines.append("")  # blank line between paragraphs

    # Remove the final extra blank line, if any
    if wrapped_lines and wrapped_lines[-1] == "":
        wrapped_lines.pop()

    curr_y = y
    for line in wrapped_lines:
        c.drawString(x, curr_y, line)
        curr_y -= leading
    return curr_y

def build_readme():
    # Check for missing images and print a warning if any are missing
    missing_images = [img for img in IMAGES.values() if not os.path.exists(os.path.join(IMG_DIR, img))]
    if missing_images:
        print("Warning: The following images are missing and will not be included in the PDF:")
        for img in missing_images:
            print(f" - {img}")
        print("Please run mysql_to_duckdb.py to generate the KPI charts.\n")

    # 1. Create the canvas
    c = canvas.Canvas(OUTPUT_PDF, pagesize=A4)
    width, height = A4
    margin = 2 * cm
    usable_width = width - 2 * margin

    # 2. Title
    title = "DuckDB-Based OLAP Cube & KPI Visualization"
    c.setFont("Helvetica-Bold", 16)
    c.drawString(margin, height - margin, title)

    # 3. Subtitle / Team Info
    subtitle = (
        "Raziskovanje digitalnega nakupovalnega vedenja potrošnikov\n"
        "Ekipa 6 (Emilija Mitrovic, Vanja Pajovic, Bogdan Kascelan)"
    )
    c.setFont("Helvetica", 10)
    y = height - margin - 1.2 * cm
    for line in subtitle.split("\n"):
        c.drawString(margin, y, line)
        y -= 12

    # 4. Section: Overview
    overview_title = "1. Overview"
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, y - 12, overview_title)

    overview_text = (
        "This project ingests eight dimension/fact tables from a MySQL schema (`dwpikp`) into DuckDB, "
        "builds a star schema view named `fact_with_dim`, computes three key KPIs, and visualizes them "
        "with matplotlib. All code, the DuckDB database, and screenshots are provided.\n\n"
        "The workflow is:\n"
        "  • Read MySQL tables into pandas DataFrames\n"
        "  • Store them in a DuckDB database file (`duckdb_database/dwpikp.duckdb`)\n"
        "  • Create a star schema view `fact_with_dim` that joins fact and dimension tables "
        "(including `kupec_id` for KPI3)\n"
        "  • Compute KPI 1, KPI 2, and KPI 3 (with research question breakdowns)\n"
        "  • Generate and export three PNG charts under `documentation/screenshots/`:\n"
        "     – KPI 1: Average spend by discount usage\n"
        "     – KPI 2: Conversion rate over time\n"
        "     – KPI 3: Customer share by age group\n"
        "  • Embed these images, plus schema/sample‐row screenshots, into this README."
    )
    c.setFont("Helvetica", 10)
    y = draw_wrapped_text(c, overview_text, margin, y - 30, usable_width, font_size=10)

    # 5. Section: DuckDB Schema (with embedded image)
    schema_title = "2. DuckDB Schema"
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, y - 20, schema_title)
    y = y - 32

    img_path = os.path.join(IMG_DIR, IMAGES["duckdb_schema"])
    print(f"DEBUG: Looking for DuckDB schema image at: {img_path}")
    if os.path.exists(img_path):
        iw, ih = scale_image(img_path, max_width=usable_width, max_height=8 * cm)
        c.drawImage(img_path, margin, y - ih, width=iw, height=ih)
        y = y - ih - 12
        c.setFont("Helvetica-Oblique", 8)
        c.drawString(
            margin,
            y,
            "Figure 1: Output of SHOW TABLES; in DuckDB, listing all dimension/fact tables plus `fact_with_dim` view."
        )
        y -= 24
    else:
        c.setFont("Helvetica-Italic", 10)
        c.drawString(margin, y, "[duckdb_schema.png not found]")
        y -= 24

    # 6. Section: Sample Rows from fact_with_dim
    sample_title = "3. Sample Rows from fact_with_dim"
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, y, sample_title)
    y -= 16

    img_path = os.path.join(IMG_DIR, IMAGES["sample_rows"])
    print(f"DEBUG: Looking for sample rows image at: {img_path}")
    if os.path.exists(img_path):
        iw, ih = scale_image(img_path, max_width=usable_width, max_height=8 * cm)
        c.drawImage(img_path, margin, y - ih, width=iw, height=ih)
        y = y - ih - 12
        c.setFont("Helvetica-Oblique", 8)
        c.drawString(
            margin,
            y,
            "Figure 2: Sample 5 rows from the joined view `fact_with_dim`, showing dimension attributes and fact measures."
        )
        y -= 24
    else:
        c.setFont("Helvetica-Italic", 10)
        c.drawString(margin, y, "[sample_query_results.png not found]")
        y -= 24

    # 7. Section: KPI Definitions & Results
    kpi_title = "4. KPI Definitions & Results"
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, y, kpi_title)
    y -= 18

    # KPI 1 Text
    kpi1_text = (
        "KPI 1: Povprečna poraba na transakcijo (Average spend per transaction)\n"
        "  • Formula: Skupni prihodki / Število transakcij\n"
        "  • Research Q1: Kako popusti vplivajo na povprečno porabo?\n"
        "  • Research Q2: Ali obstaja razlika med novimi in vračajočimi se kupci?\n"
    )
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margin, y, "4.1 KPI 1")
    y -= 14
    c.setFont("Helvetica", 10)
    y = draw_wrapped_text(c, kpi1_text, margin, y, usable_width, font_size=10)
    y -= 4

    img_path = os.path.join(IMG_DIR, IMAGES["kpi1_chart"])
    print(f"DEBUG: Looking for KPI1 chart at: {img_path}")
    if os.path.exists(img_path):
        iw, ih = scale_image(img_path, max_width=usable_width, max_height=6 * cm)
        c.drawImage(img_path, margin, y - ih, width=iw, height=ih)
        y = y - ih - 12
        c.setFont("Helvetica-Oblique", 8)
        c.drawString(
            margin,
            y,
            "Figure 3: KPI 1 – Average spend per transaction by discount usage."
        )
        y -= 24
    else:
        c.setFont("Helvetica-Italic", 10)
        c.drawString(margin, y, "[kpi1_avg_spend_by_discount.png not found]")
        y -= 24

    # KPI 2 Text
    kpi2_text = (
        "KPI 2: Stopnja konverzije (Conversion rate)\n"
        "  • Formula: (Število nakupov / Število obiskov) × 100\n"
        "  • Research Q1: Kako popusti vplivajo na stopnjo konverzije?\n"
        "  • Research Q2: Kakšen je trend stopnje konverzije po letih in mesecih?\n"
    )
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margin, y, "4.2 KPI 2")
    y -= 14
    c.setFont("Helvetica", 10)
    y = draw_wrapped_text(c, kpi2_text, margin, y, usable_width, font_size=10)
    y -= 4

    img_path = os.path.join(IMG_DIR, IMAGES["kpi2_chart"])
    print(f"DEBUG: Looking for KPI2 chart at: {img_path}")
    if os.path.exists(img_path):
        iw, ih = scale_image(img_path, max_width=usable_width, max_height=6 * cm)
        c.drawImage(img_path, margin, y - ih, width=iw, height=ih)
        y = y - ih - 12
        c.setFont("Helvetica-Oblique", 8)
        c.drawString(
            margin,
            y,
            "Figure 4: KPI 2 – Conversion rate over time (line chart by year)."
        )
        y -= 24
    else:
        c.setFont("Helvetica-Italic", 10)
        c.drawString(margin, y, "[kpi2_conversion_rate_over_time.png not found]")
        y -= 24

    # KPI 3 Text
    kpi3_text = (
        "KPI 3: Delež e-trgovinskih kupcev glede na starost (Customer share by age group)\n"
        "  • Formula: (Število kupcev v tej skupini / Skupno število kupcev) × 100\n"
        "  • Research Q1: Kako se odstotek kupcev razlikuje po starostnih skupinah?\n"
        "  • Research Q2: Ali obstajajo razlike med spoloma?\n"
    )
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margin, y, "4.3 KPI 3")
    y -= 14
    c.setFont("Helvetica", 10)
    y = draw_wrapped_text(c, kpi3_text, margin, y, usable_width, font_size=10)
    y -= 4

    img_path = os.path.join(IMG_DIR, IMAGES["kpi3_chart"])
    print(f"DEBUG: Looking for KPI3 chart at: {img_path}")
    if os.path.exists(img_path):
        iw, ih = scale_image(img_path, max_width=usable_width, max_height=6 * cm)
        c.drawImage(img_path, margin, y - ih, width=iw, height=ih)
        y = y - ih - 12
        c.setFont("Helvetica-Oblique", 8)
        c.drawString(
            margin,
            y,
            "Figure 5: KPI 3 – Customer share by age group."
        )
        y -= 24
    else:
        c.setFont("Helvetica-Italic", 10)
        c.drawString(margin, y, "[kpi3_pct_by_age_filled.png not found]")
        y -= 24

    # 8. Reproducibility Instructions
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, y, "5. Reproducibility Instructions")
    y -= 16
    instructions = (
        "1. Activate the virtual environment:\n"
        "     > cd PIKPOlap\n"
        "     > .venv\\Scripts\\activate    (on Windows PowerShell)\n"
        "     > activate.bat               (on Windows cmd.exe)\n"
        "2. Install dependencies:\n"
        "     > pip install -r requirements.txt\n"
        "3. Edit `scripts/mysql_to_duckdb.py` if you need to update MySQL credentials (host/user/password).\n"
        "4. Run the ingestion/KPI script:\n"
        "     > python scripts\\mysql_to_duckdb.py\n"
        "   This will:\n"
        "     • Create/overwrite `duckdb_database/dwpikp.duckdb`  \n"
        "     • Build the `fact_with_dim` view  \n"
        "     • Print all KPI results to the console  \n"
        "     • Save three PNG charts under `documentation/screenshots/`  \n"
        "5. (Optional) Inspect the DuckDB schema or sample rows in Python:\n"
        "     > python scripts\\inspect_duckdb.py\n"
        "6. Open and review this README.pdf under `documentation/README.pdf`.\n"
    )
    c.setFont("Helvetica", 10)
    y = draw_wrapped_text(c, instructions, margin, y, usable_width, font_size=10)

    # 9. Dependencies & Versions
    dep_title = "6. Dependencies & Versions"
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, y - 12, dep_title)
    y -= 30

    deps = (
        "• duckdb==0.8.1  \n"
        "• pandas==1.5.3  \n"
        "• mysql-connector-python==8.0.34  \n"
        "• matplotlib==3.7.1  \n"
        "• reportlab>=3.6.0  \n"
    )
    c.setFont("Helvetica", 10)
    y = draw_wrapped_text(c, deps, margin, y, usable_width, font_size=10)

    # 10. Finalize and save
    c.showPage()
    c.save()
    print(f"\n▶ README.pdf generated at: {OUTPUT_PDF}")

if __name__ == "__main__":
    build_readme()