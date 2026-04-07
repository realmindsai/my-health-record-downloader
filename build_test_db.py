# ABOUTME: Builds a SQLite database of medical test results extracted from pathology PDF reports.
# ABOUTME: Populates test_results and imaging_reports tables from Dorevitch, Austin, and SCMI PDFs.

import sqlite3
import click
from pathlib import Path

DB_PATH = Path(__file__).parent / "personal" / "medical_results.db"


def create_schema(conn):
    conn.executescript("""
        DROP TABLE IF EXISTS test_results;
        DROP TABLE IF EXISTS imaging_reports;

        CREATE TABLE test_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            collected_date TEXT NOT NULL,
            lab_number TEXT,
            laboratory TEXT,
            doctor TEXT,
            test_panel TEXT NOT NULL,
            test_name TEXT NOT NULL,
            value REAL,
            value_text TEXT,
            units TEXT,
            ref_range_low REAL,
            ref_range_high REAL,
            ref_range_text TEXT,
            is_abnormal INTEGER DEFAULT 0,
            source_file TEXT,
            UNIQUE(collected_date, test_name)
        );

        CREATE TABLE imaging_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exam_date TEXT NOT NULL,
            exam_type TEXT NOT NULL,
            laboratory TEXT,
            referring_doctor TEXT,
            reporting_doctor TEXT,
            clinical_notes TEXT,
            findings TEXT,
            conclusion TEXT,
            source_file TEXT
        );

        CREATE INDEX idx_results_date ON test_results(collected_date);
        CREATE INDEX idx_results_panel ON test_results(test_panel);
        CREATE INDEX idx_results_name ON test_results(test_name);
        CREATE INDEX idx_imaging_date ON imaging_reports(exam_date);
    """)


def insert_result(conn, collected_date, lab_number, laboratory, doctor,
                   test_panel, test_name, value, value_text, units,
                   ref_low, ref_high, ref_text, is_abnormal, source_file):
    try:
        conn.execute("""
            INSERT OR REPLACE INTO test_results
            (collected_date, lab_number, laboratory, doctor, test_panel,
             test_name, value, value_text, units, ref_range_low, ref_range_high,
             ref_range_text, is_abnormal, source_file)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (collected_date, lab_number, laboratory, doctor, test_panel,
              test_name, value, value_text, units, ref_low, ref_high,
              ref_text, is_abnormal, source_file))
    except sqlite3.IntegrityError:
        pass


def insert_imaging(conn, exam_date, exam_type, laboratory, referring_doctor,
                   reporting_doctor, clinical_notes, findings, conclusion, source_file):
    conn.execute("""
        INSERT INTO imaging_reports
        (exam_date, exam_type, laboratory, referring_doctor, reporting_doctor,
         clinical_notes, findings, conclusion, source_file)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (exam_date, exam_type, laboratory, referring_doctor, reporting_doctor,
          clinical_notes, findings, conclusion, source_file))


def r(conn, date, lab, laboratory, doctor, panel, name, val, val_txt, units,
      lo, hi, ref_txt, abnormal, src):
    """Shorthand for insert_result."""
    insert_result(conn, date, lab, laboratory, doctor, panel, name,
                  val, val_txt, units, lo, hi, ref_txt, abnormal, src)


def populate_data(conn):
    DV = "Dorevitch Pathology"
    AU = "Austin Pathology"

    # =========================================================================
    # 2011-10-15 (Lab 6525665) - B12 only historical
    # =========================================================================
    r(conn, "2011-10-15", "6525665", DV, None,
      "Vitamin B12 and Folate", "Vitamin B12", 250, "250", "pmol/L",
      150, 700, "(150-700)", 0, "Pathology_Report_-_10th_March_2026__01.pdf")
    r(conn, "2011-10-15", "6525665", DV, None,
      "Vitamin B12 and Folate", "R.C.Folate", 955, "955", "nmol/L",
      570, None, "(> 570)", 0, "Pathology_Report_-_10th_March_2026__01.pdf")

    # =========================================================================
    # 2023-03-18 (Lab 46331515)
    # =========================================================================
    lab = "46331515"
    date = "2023-03-18"
    doc_ghosh = "DR GHOSH, AJANTA"
    doc_ngu = "DR NGU, JING JING"
    doc_yannas = "DR YANNAS, DIANA"
    doc_bala = "DR BALA, SWARN"

    r(conn, date, lab, DV, None,
      "Vitamin B12 and Folate", "Vitamin B12", 219, "219", "pmol/L",
      150, 700, "(150-700)", 0, "Pathology_Report_-_10th_March_2026__01.pdf")
    r(conn, date, lab, DV, None,
      "Vitamin D", "25-Hydroxy Vitamin D", 87, "87", "nmol/L",
      50, None, "(> 50)", 0, "Pathology_Report_-_10th_July_2025__32.pdf")
    r(conn, date, lab, DV, None,
      "PSA", "PSA Alinity", 6.0, "6.0", "ug/L",
      0.3, 4.5, "(0.3-4.5)", 1, "Pathology_Report_-_03rd_December_2025__14.pdf")
    r(conn, date, lab, DV, None,
      "PSA", "Free PSA", 0.95, "0.95", "ug/L",
      None, None, None, 0, "Pathology_Report_-_03rd_December_2025__14.pdf")
    r(conn, date, lab, DV, None,
      "PSA", "Free/Total PSA Ratio", 16.0, "16.0", "%",
      None, None, None, 0, "Pathology_Report_-_03rd_December_2025__14.pdf")
    r(conn, date, lab, DV, None,
      "HbA1c", "HbA1c %", 5.2, "5.2", "%",
      None, 6.5, "Diabetes cutoff 6.5%", 0,
      "Pathology_Report_-_10th_March_2026__04.pdf")
    r(conn, date, lab, DV, None,
      "HbA1c", "HbA1c mmol/mol", 33, "33", "mmol/mol",
      None, None, None, 0, "Pathology_Report_-_10th_March_2026__04.pdf")

    # =========================================================================
    # 2024-03-21 (Lab 47840339)
    # =========================================================================
    lab = "47840339"
    date = "2024-03-21"

    # FBE
    for name, val, units, lo, hi in [
        ("Haemoglobin", 142, "g/L", 130, 180),
        ("WCC", 4.2, "x10^9/L", 4.0, 11.0),
        ("Platelets", 170, "x10^9/L", 150, 450),
        ("RCC", 4.62, "x10^12/L", 4.50, 6.50),
        ("PCV", 0.43, "L/L", 0.40, 0.54),
        ("MCV", 93, "fL", 80, 96),
        ("MCH", 31, "pg", 27, 32),
        ("MCHC", 329, "g/L", 320, 360),
        ("RDW", 12.6, "%", 11.0, 16.0),
        ("Neutrophils", 2.6, "x10^9/L", 2.0, 8.0),
        ("Lymphocytes", 1.0, "x10^9/L", 1.0, 4.0),
        ("Monocytes", 0.4, "x10^9/L", 0.0, 1.0),
        ("Eosinophils", 0.1, "x10^9/L", 0.0, 0.5),
        ("Basophils", 0.0, "x10^9/L", 0.0, 0.2),
    ]:
        abnormal = 1 if (lo and val < lo) or (hi and val > hi) else 0
        r(conn, date, lab, DV, doc_bala,
          "Full Blood Examination", name, val, str(val), units,
          lo, hi, f"({lo}-{hi})", abnormal,
          "Pathology_Report_-_10th_March_2026__02.pdf")

    # Ferritin
    r(conn, date, lab, DV, doc_bala,
      "Iron Studies", "Ferritin", 72, "72", "ug/L",
      30, 320, "(30-320)", 0, "Pathology_Report_-_10th_March_2026__08.pdf")

    # HbA1c
    r(conn, date, lab, DV, doc_bala,
      "HbA1c", "HbA1c %", 5.2, "5.2", "%",
      None, 6.5, "Diabetes cutoff 6.5%", 0,
      "Pathology_Report_-_10th_March_2026__04.pdf")
    r(conn, date, lab, DV, doc_bala,
      "HbA1c", "HbA1c mmol/mol", 33, "33", "mmol/mol",
      None, None, None, 0, "Pathology_Report_-_10th_March_2026__04.pdf")

    # PSA
    r(conn, date, lab, DV, doc_yannas,
      "PSA", "PSA Alinity", 5.8, "5.8", "ug/L",
      0.3, 4.5, "(0.3-4.5)", 1,
      "Pathology_Report_-_03rd_December_2025__14.pdf")
    r(conn, date, lab, DV, doc_yannas,
      "PSA", "Free PSA", 0.99, "0.99", "ug/L",
      None, None, None, 0, "Pathology_Report_-_03rd_December_2025__14.pdf")
    r(conn, date, lab, DV, doc_yannas,
      "PSA", "Free/Total PSA Ratio", 17.0, "17.0", "%",
      None, None, None, 0, "Pathology_Report_-_03rd_December_2025__14.pdf")

    # =========================================================================
    # 2025-07-10 (Lab 92847682)
    # =========================================================================
    lab = "92847682"
    date = "2025-07-10"

    # FBE
    for name, val, units, lo, hi in [
        ("Haemoglobin", 150, "g/L", 130, 180),
        ("WCC", 4.1, "x10^9/L", 4.0, 11.0),
        ("Platelets", 161, "x10^9/L", 150, 450),
        ("RCC", 4.83, "x10^12/L", 4.50, 6.50),
        ("PCV", 0.44, "L/L", 0.40, 0.54),
        ("MCV", 92, "fL", 80, 96),
        ("MCH", 31, "pg", 27, 32),
        ("MCHC", 339, "g/L", 320, 360),
        ("RDW", 12.4, "%", 11.0, 16.0),
        ("Neutrophils", 2.3, "x10^9/L", 2.0, 8.0),
        ("Lymphocytes", 1.3, "x10^9/L", 1.0, 4.0),
        ("Monocytes", 0.5, "x10^9/L", 0.0, 1.0),
        ("Eosinophils", 0.0, "x10^9/L", 0.0, 0.5),
        ("Basophils", 0.0, "x10^9/L", 0.0, 0.2),
    ]:
        abnormal = 1 if (lo is not None and val < lo) or (hi is not None and val > hi) else 0
        r(conn, date, lab, DV, doc_ngu,
          "Full Blood Examination", name, val, str(val), units,
          lo, hi, f"({lo}-{hi})", abnormal,
          "Pathology_Report_-_10th_March_2026__02.pdf")

    # Biochemistry
    for name, val, units, lo, hi in [
        ("Sodium", 139, "mmol/L", 135, 145),
        ("Potassium", 4.2, "mmol/L", 3.5, 5.2),
        ("Chloride", 104, "mmol/L", 95, 110),
        ("Bicarbonate", 31, "mmol/L", 22, 32),
        ("Anion gap", 8, "mmol/L", 7, 17),
        ("Urea", 6.5, "mmol/L", 3.0, 10.0),
        ("eGFR", 76, "mL/min/1.73m2", 60, None),
        ("Creatinine", 93, "umol/L", 60, 110),
        ("Bilirubin", 14, "umol/L", 0, 20),
        ("ALT", 25, "U/L", 0, 45),
        ("AST", 28, "U/L", 0, 35),
        ("ALP", 63, "U/L", 30, 110),
        ("GGT", 17, "U/L", 0, 50),
        ("Total Protein", 74, "g/L", 60, 80),
        ("Albumin", 41, "g/L", 34, 47),
        ("Globulin", 33, "g/L", 22, 40),
    ]:
        ref = f"({lo}-{hi})" if hi else f"(> {lo})"
        abnormal = 0
        if lo is not None and val < lo:
            abnormal = 1
        if hi is not None and val > hi:
            abnormal = 1
        r(conn, date, lab, DV, doc_ngu,
          "Biochemistry", name, val, str(val), units,
          lo, hi, ref, abnormal,
          "Pathology_Report_-_10th_March_2026__07.pdf")

    # Lipids
    for name, val, units in [
        ("Total Cholesterol", 5.0, "mmol/L"),
        ("Triglyceride", 1.6, "mmol/L"),
        ("HDL-C", 1.0, "mmol/L"),
        ("LDL-C", 3.3, "mmol/L"),
        ("Non HDL-C", 4.0, "mmol/L"),
        ("Chol/HDL Ratio", 5.0, None),
    ]:
        r(conn, date, lab, DV, doc_ngu,
          "Lipid Studies", name, val, str(val), units,
          None, None, "Targets vary by CV risk", 0,
          "Pathology_Report_-_10th_March_2026__03.pdf")

    # Iron Studies
    r(conn, date, lab, DV, doc_ngu,
      "Iron Studies", "Ferritin", 88, "88", "ug/L",
      30, 320, "(30-320)", 0, "Pathology_Report_-_10th_March_2026__08.pdf")
    r(conn, date, lab, DV, doc_ngu,
      "Iron Studies", "Iron", 15, "15", "umol/L",
      10, 30, "(10-30)", 0, "Pathology_Report_-_10th_March_2026__08.pdf")
    r(conn, date, lab, DV, doc_ngu,
      "Iron Studies", "Transferrin", 2.4, "2.4", "g/L",
      2.0, 3.6, "(2.0-3.6)", 0, "Pathology_Report_-_10th_March_2026__08.pdf")
    r(conn, date, lab, DV, doc_ngu,
      "Iron Studies", "Transferrin Saturation", 25, "25", "%",
      13, 47, "(13-47)", 0, "Pathology_Report_-_10th_March_2026__08.pdf")

    # Vitamin D
    r(conn, date, lab, DV, doc_ngu,
      "Vitamin D", "25-Hydroxy Vitamin D", 71, "71", "nmol/L",
      50, None, "(> 50)", 0, "Pathology_Report_-_10th_July_2025__32.pdf")

    # Glucose
    r(conn, date, lab, DV, doc_ngu,
      "Glucose", "Glucose (Fasting)", 5.2, "5.2", "mmol/L",
      4.0, 6.0, "Fasting (4.0-6.0)", 0,
      "Pathology_Report_-_22nd_November_2025__20.pdf")

    # HbA1c
    r(conn, date, lab, DV, doc_ngu,
      "HbA1c", "HbA1c %", 5.2, "5.2", "%",
      None, 6.5, "Diabetes cutoff 6.5%", 0,
      "Pathology_Report_-_10th_March_2026__04.pdf")
    r(conn, date, lab, DV, doc_ngu,
      "HbA1c", "HbA1c mmol/mol", 33, "33", "mmol/mol",
      None, None, None, 0, "Pathology_Report_-_10th_March_2026__04.pdf")

    # PSA
    r(conn, date, lab, DV, doc_yannas,
      "PSA", "PSA Alinity", 6.5, "6.5", "ug/L",
      0.3, 4.5, "(0.3-4.5)", 1,
      "Pathology_Report_-_03rd_December_2025__14.pdf")
    r(conn, date, lab, DV, doc_yannas,
      "PSA", "Free PSA", 1.08, "1.08", "ug/L",
      None, None, None, 0, "Pathology_Report_-_03rd_December_2025__14.pdf")
    r(conn, date, lab, DV, doc_yannas,
      "PSA", "Free/Total PSA Ratio", 16.6, "16.6", "%",
      None, None, None, 0, "Pathology_Report_-_03rd_December_2025__14.pdf")

    # =========================================================================
    # 2025-10-28 - MRI Brain (SCMI)
    # =========================================================================
    insert_imaging(conn, "2025-10-28", "MRI Brain", "SCMI - Southern Cross Medical Imaging",
                   doc_ngu, "Dr Lok Wong",
                   "Weakness of left side of mouth. ?Intracranial lesion, stroke.",
                   "T2 white matter hyperintensities in the frontal lobes bilaterally, within normal limits for age. "
                   "No restricted diffusion. No abnormal susceptibility artefact. Gyral pattern within normal limits. "
                   "No extra-axial collection. Ventricles and sulci appropriate for age. Midline structures unremarkable. "
                   "No cerebellopontine angle lesions. 7th and 8th cranial nerves normal bilaterally. "
                   "Normal signal in major intracranial arteries on MRA.",
                   "No significant intracranial abnormality.",
                   "Diagnostic_Imaging_Report_-_28th_October_2025__30.pdf")

    # =========================================================================
    # 2025-11-14 - CT Abdomen & Pelvis (SCMI)
    # =========================================================================
    insert_imaging(conn, "2025-11-14", "CT Abdomen and Pelvis",
                   "SCMI - Southern Cross Medical Imaging",
                   doc_ghosh, "Dr Larry Mak",
                   "Ongoing upper abdominal pain. Fullness feeling. Nausea. ?Abdominal pathology.",
                   "5mm calcified granuloma in segment 8 of liver. No other liver lesions. "
                   "Normal gallbladder, pancreas, adrenals, kidneys and spleen. "
                   "Moderate faecal loading from caecum to splenic flexure. No diverticular disease or diverticulitis. "
                   "Bowel loops unremarkable. No bowel obstruction. No hiatus hernia. "
                   "No free fluid or gas. No lymphadenopathy. "
                   "Prostatomegaly ~98cc. Trabeculated bladder contour. "
                   "Lung bases clear. No destructive osseous lesions.",
                   "1. No intra-abdominal mass lesion, focal collection or acute abnormality. "
                   "2. No hiatus hernia. Moderate faecal loading in right hemicolon. No diverticular disease. "
                   "3. Prostatomegaly. Trabeculated bladder contour suggests chronic bladder outlet obstruction.",
                   "Diagnostic_Imaging_Report_-_14th_November_2025__29.pdf")

    # =========================================================================
    # 2025-11-22 (Lab 98374959)
    # =========================================================================
    lab = "98374959"
    date = "2025-11-22"

    # FBE
    for name, val, units, lo, hi in [
        ("Haemoglobin", 140, "g/L", 130, 180),
        ("WCC", 4.1, "x10^9/L", 4.0, 11.0),
        ("Platelets", 167, "x10^9/L", 150, 450),
        ("RCC", 4.53, "x10^12/L", 4.50, 6.50),
        ("PCV", 0.41, "L/L", 0.40, 0.54),
        ("MCV", 91, "fL", 80, 96),
        ("MCH", 31, "pg", 27, 32),
        ("MCHC", 339, "g/L", 320, 360),
        ("RDW", 12.3, "%", 11.0, 16.0),
        ("Neutrophils", 2.3, "x10^9/L", 2.0, 8.0),
        ("Lymphocytes", 1.2, "x10^9/L", 1.0, 4.0),
        ("Monocytes", 0.5, "x10^9/L", 0.0, 1.0),
        ("Eosinophils", 0.1, "x10^9/L", 0.0, 0.5),
        ("Basophils", 0.0, "x10^9/L", 0.0, 0.2),
    ]:
        abnormal = 0
        if lo is not None and val < lo:
            abnormal = 1
        if hi is not None and val > hi:
            abnormal = 1
        r(conn, date, lab, DV, doc_ghosh,
          "Full Blood Examination", name, val, str(val), units,
          lo, hi, f"({lo}-{hi})", abnormal,
          "Pathology_Report_-_22nd_November_2025__21.pdf")

    # Biochemistry
    for name, val, units, lo, hi in [
        ("Sodium", 139, "mmol/L", 135, 145),
        ("Potassium", 4.0, "mmol/L", 3.5, 5.2),
        ("Chloride", 105, "mmol/L", 95, 110),
        ("Bicarbonate", 29, "mmol/L", 22, 32),
        ("Anion gap", 9, "mmol/L", 7, 17),
        ("Urea", 5.4, "mmol/L", 3.0, 10.0),
        ("eGFR", 89, "mL/min/1.73m2", 60, None),
        ("Creatinine", 81, "umol/L", 60, 110),
        ("Bilirubin", 12, "umol/L", 0, 20),
        ("ALT", 25, "U/L", 0, 45),
        ("AST", 26, "U/L", 0, 35),
        ("ALP", 70, "U/L", 30, 110),
        ("GGT", 18, "U/L", 0, 50),
        ("Total Protein", 69, "g/L", 60, 80),
        ("Albumin", 39, "g/L", 34, 47),
        ("Globulin", 30, "g/L", 22, 40),
        ("Calcium", 2.24, "mmol/L", 2.15, 2.65),
        ("Corrected Calcium", 2.26, "mmol/L", 2.15, 2.65),
        ("Phosphate", 0.93, "mmol/L", 0.75, 1.50),
        ("Magnesium", 0.78, "mmol/L", 0.60, 1.10),
    ]:
        ref = f"({lo}-{hi})" if hi else f"(> {lo})"
        abnormal = 0
        if lo is not None and val < lo:
            abnormal = 1
        if hi is not None and val > hi:
            abnormal = 1
        r(conn, date, lab, DV, doc_ghosh,
          "Biochemistry", name, val, str(val), units,
          lo, hi, ref, abnormal,
          "Pathology_Report_-_22nd_November_2025__25.pdf")

    # Lipids
    for name, val, units in [
        ("Total Cholesterol", 4.5, "mmol/L"),
        ("Triglyceride", 1.8, "mmol/L"),
        ("HDL-C", 0.9, "mmol/L"),
        ("LDL-C", 2.8, "mmol/L"),
        ("Non HDL-C", 3.6, "mmol/L"),
        ("Chol/HDL Ratio", 5.0, None),
    ]:
        r(conn, date, lab, DV, doc_ghosh,
          "Lipid Studies", name, val, str(val), units,
          None, None, "Targets vary by CV risk", 0,
          "Pathology_Report_-_10th_March_2026__03.pdf")

    # Iron Studies
    r(conn, date, lab, DV, doc_ghosh,
      "Iron Studies", "Ferritin", 101, "101", "ug/L",
      30, 320, "(30-320)", 0, "Pathology_Report_-_22nd_November_2025__23.pdf")
    r(conn, date, lab, DV, doc_ghosh,
      "Iron Studies", "Iron", 15, "15", "umol/L",
      10, 30, "(10-30)", 0, "Pathology_Report_-_22nd_November_2025__23.pdf")
    r(conn, date, lab, DV, doc_ghosh,
      "Iron Studies", "Transferrin", 2.4, "2.4", "g/L",
      2.0, 3.6, "(2.0-3.6)", 0, "Pathology_Report_-_22nd_November_2025__23.pdf")
    r(conn, date, lab, DV, doc_ghosh,
      "Iron Studies", "Transferrin Saturation", 25, "25", "%",
      13, 47, "(13-47)", 0, "Pathology_Report_-_22nd_November_2025__23.pdf")

    # Thyroid
    r(conn, date, lab, DV, doc_ghosh,
      "Thyroid Function", "Free T4", 16.4, "16.4", "pmol/L",
      10.0, 23.0, "(10.0-23.0)", 0,
      "Pathology_Report_-_22nd_November_2025__24.pdf")
    r(conn, date, lab, DV, doc_ghosh,
      "Thyroid Function", "TSH", 2.43, "2.43", "mIU/L",
      0.50, 4.00, "(0.50-4.00)", 0,
      "Pathology_Report_-_22nd_November_2025__24.pdf")
    r(conn, date, lab, DV, doc_ghosh,
      "Thyroid Function", "Free T3", 5.1, "5.1", "pmol/L",
      3.5, 6.5, "(3.5-6.5)", 0,
      "Pathology_Report_-_22nd_November_2025__24.pdf")

    # Glucose
    r(conn, date, lab, DV, doc_ghosh,
      "Glucose", "Glucose (Fasting)", 4.9, "4.9", "mmol/L",
      4.0, 6.0, "Fasting (4.0-6.0)", 0,
      "Pathology_Report_-_22nd_November_2025__20.pdf")

    # HbA1c
    r(conn, date, lab, DV, doc_ghosh,
      "HbA1c", "HbA1c %", 5.1, "5.1", "%",
      None, 6.5, "Diabetes cutoff 6.5%", 0,
      "Pathology_Report_-_10th_March_2026__04.pdf")
    r(conn, date, lab, DV, doc_ghosh,
      "HbA1c", "HbA1c mmol/mol", 32, "32", "mmol/mol",
      None, None, None, 0, "Pathology_Report_-_10th_March_2026__04.pdf")

    # CRP
    r(conn, date, lab, DV, doc_ghosh,
      "CRP", "CRP", 3, "3", "mg/L",
      None, 4, "(< 4)", 0,
      "Pathology_Report_-_22nd_November_2025__22.pdf")

    # =========================================================================
    # 2025-12-01 - Renal Tract Ultrasound (SCMI)
    # =========================================================================
    insert_imaging(conn, "2025-12-01", "Renal Tract Ultrasound",
                   "SCMI - Southern Cross Medical Imaging",
                   doc_yannas, "Dr Larry Mak",
                   "Prostatomegaly. Trabeculated bladder on CT.",
                   "Right and left kidney 120mm each. Normal corticomedullary differentiation and cortical thickness. "
                   "No renal lesion or hydronephrosis. Trabeculated bladder contour. "
                   "Pre-void bladder volume 290cc, post-void 118cc. Patient unable to void further. "
                   "Both ureteric jets seen. Prostate enlarged, measuring 105cc.",
                   "1. Prostatomegaly. Large residual bladder volume post void (118cc). "
                   "Trabeculated bladder contour suggestive of chronic bladder obstruction. "
                   "2. No renal abnormality.",
                   "Diagnostic_Imaging_Report_-_01st_December_2025__19.pdf")

    # =========================================================================
    # 2025-12-02 (Lab 37803169) - Urine tests
    # =========================================================================
    lab = "37803169"
    date = "2025-12-02"

    # Urine Microalbumin
    r(conn, date, lab, DV, doc_yannas,
      "Urine Microalbumin", "Albumin Concentration", 9, "9", "mg/L",
      0, 25, "(0-25)", 0, "Pathology_Report_-_02nd_December_2025__17.pdf")
    r(conn, date, lab, DV, doc_yannas,
      "Urine Microalbumin", "Creatinine Concentration (Urine)", 15.3, "15.3", "mmol/L",
      None, None, None, 0, "Pathology_Report_-_02nd_December_2025__17.pdf")
    r(conn, date, lab, DV, doc_yannas,
      "Urine Microalbumin", "Albumin/Creatinine Ratio", 0.6, "0.6", "mg/mmol creat",
      None, 2.5, "(< 2.5)", 0, "Pathology_Report_-_02nd_December_2025__17.pdf")

    # Urine Examination
    r(conn, date, lab, DV, doc_yannas,
      "Urine Examination", "Urine pH", 6.0, "6.0", None,
      None, None, None, 0, "Pathology_Report_-_02nd_December_2025__18.pdf")
    r(conn, date, lab, DV, doc_yannas,
      "Urine Examination", "Urine Protein", None, "Neg", None,
      None, None, None, 0, "Pathology_Report_-_02nd_December_2025__18.pdf")
    r(conn, date, lab, DV, doc_yannas,
      "Urine Examination", "Urine Glucose", None, "Neg", None,
      None, None, None, 0, "Pathology_Report_-_02nd_December_2025__18.pdf")
    r(conn, date, lab, DV, doc_yannas,
      "Urine Examination", "Urine Ketones", None, "Neg", None,
      None, None, None, 0, "Pathology_Report_-_02nd_December_2025__18.pdf")
    r(conn, date, lab, DV, doc_yannas,
      "Urine Examination", "Urine Blood/Hb", None, "Neg", None,
      None, None, None, 0, "Pathology_Report_-_02nd_December_2025__18.pdf")
    r(conn, date, lab, DV, doc_yannas,
      "Urine Examination", "Urine Culture", None, "No growth", None,
      None, None, None, 0, "Pathology_Report_-_02nd_December_2025__18.pdf")

    # =========================================================================
    # 2025-12-03 (Lab 98616609) - PSA, ECG, Lipoprotein(a)
    # =========================================================================
    lab = "98616609"
    date = "2025-12-03"

    # PSA
    r(conn, date, lab, DV, doc_yannas,
      "PSA", "PSA Alinity", 5.5, "5.5", "ug/L",
      0.3, 4.5, "(0.3-4.5)", 1,
      "Pathology_Report_-_03rd_December_2025__14.pdf")
    r(conn, date, lab, DV, doc_yannas,
      "PSA", "Free PSA", 0.84, "0.84", "ug/L",
      None, None, None, 0, "Pathology_Report_-_03rd_December_2025__14.pdf")
    r(conn, date, lab, DV, doc_yannas,
      "PSA", "Free/Total PSA Ratio", 15.3, "15.3", "%",
      None, None, None, 0, "Pathology_Report_-_03rd_December_2025__14.pdf")

    # Lipoprotein(a)
    r(conn, date, lab, DV, doc_yannas,
      "Lipoprotein(a)", "Lipoprotein(a)", 9, "9", "nmol/L",
      None, 75, "(< 75)", 0,
      "Pathology_Report_-_03rd_December_2025__15.pdf")

    # ECG
    r(conn, date, lab, DV, doc_yannas,
      "ECG", "Heart Rate", 59, "59", "/min",
      None, None, None, 0, "Pathology_Report_-_03rd_December_2025__16.pdf")
    r(conn, date, lab, DV, doc_yannas,
      "ECG", "PR Interval", 198, "198", "ms",
      None, None, None, 0, "Pathology_Report_-_03rd_December_2025__16.pdf")
    r(conn, date, lab, DV, doc_yannas,
      "ECG", "QRS Duration", 110, "110", "ms",
      None, None, None, 0, "Pathology_Report_-_03rd_December_2025__16.pdf")
    r(conn, date, lab, DV, doc_yannas,
      "ECG", "QT Interval", 416, "416", "ms",
      None, None, None, 0, "Pathology_Report_-_03rd_December_2025__16.pdf")
    r(conn, date, lab, DV, doc_yannas,
      "ECG", "QTc", 415, "415", "ms",
      None, None, None, 0, "Pathology_Report_-_03rd_December_2025__16.pdf")
    r(conn, date, lab, DV, doc_yannas,
      "ECG", "ECG Interpretation", None, "Sinus rhythm. Within normal limits.", None,
      None, None, None, 0, "Pathology_Report_-_03rd_December_2025__16.pdf")

    # =========================================================================
    # 2026-03-03 (Austin ED - Lab 19163707)
    # =========================================================================
    lab = "19163707"
    date = "2026-03-03"

    # Full Blood Count (Austin)
    for name, val, units, lo, hi in [
        ("Haemoglobin", 141, "g/L", 120, 170),
        ("WCC", 6.6, "x10^9/L", 4.0, 12.0),
        ("Platelets", 192, "x10^9/L", 150, 400),
        ("MCV", 92, "fL", 80, 99),
        ("RCC", 4.64, "x10^12/L", 3.80, 5.70),
        ("PCV", 0.43, "L/L", 0.36, 0.50),
        ("MCH", 30.4, "pg", 26.0, 34.0),
        ("MCHC", 329, "g/L", 315, 365),
        ("RDW", 12.6, "%", 11.6, 14.0),
        ("Neutrophils", 4.0, "x10^9/L", 2.0, 8.0),
        ("Lymphocytes", 1.9, "x10^9/L", 1.0, 3.5),
        ("Monocytes", 0.6, "x10^9/L", 0.2, 1.0),
        ("Eosinophils", 0.1, "x10^9/L", 0.0, 0.5),
        ("Basophils", 0.0, "x10^9/L", 0.0, 0.2),
    ]:
        abnormal = 0
        if lo is not None and val < lo:
            abnormal = 1
        if hi is not None and val > hi:
            abnormal = 1
        r(conn, date, lab, AU, "Dr J HOWELL",
          "Full Blood Examination", name, val, str(val), units,
          lo, hi, f"({lo} - {hi})", abnormal,
          "Pathology_Report_-_03rd_March_2026__11.pdf")

    # Biochemistry (Austin)
    for name, val, units, lo, hi in [
        ("Sodium", 141, "mmol/L", 135, 145),
        ("Potassium", 4.3, "mmol/L", 3.5, 5.2),
        ("Chloride", 104, "mmol/L", 95, 110),
        ("Bicarbonate", 28, "mmol/L", 22, 32),
        ("Urea", 6.5, "mmol/L", 3.0, 9.2),
        ("Creatinine", 88, "umol/L", 60, 110),
        ("eGFR", 81, "mL/min/1.73m2", 90, None),
        ("hs Troponin I", 3, "ng/L", None, 26),
        ("Calcium", 2.32, "mmol/L", 2.10, 2.60),
        ("Corrected Calcium", 2.26, "mmol/L", 2.10, 2.60),
        ("Magnesium", 0.92, "mmol/L", 0.70, 1.10),
        ("Total Protein", 75, "g/L", 60, 80),
        ("Albumin", 43, "g/L", 32, 46),
        ("Globulin", 32, "g/L", 25, 40),
        ("Bilirubin", 10.9, "umol/L", None, 20.0),
        ("ALT", 26, "U/L", 5, 40),
        ("AST", 32, "U/L", 6, 35),
        ("ALP", 76, "U/L", 30, 110),
        ("GGT", 21, "U/L", 5, 50),
        ("CRP", 2.2, "mg/L", None, 5.0),
    ]:
        if lo is not None and hi is not None:
            ref = f"({lo} - {hi})"
        elif lo is not None:
            ref = f"(> {lo})"
        elif hi is not None:
            ref = f"(< {hi})"
        else:
            ref = None
        abnormal = 0
        if lo is not None and val < lo:
            abnormal = 1
        if hi is not None and val > hi:
            abnormal = 1
        r(conn, date, lab, AU, "Dr J HOWELL",
          "Biochemistry", name, val, str(val), units,
          lo, hi, ref, abnormal,
          "Pathology_Report_-_03rd_March_2026__12.pdf")

    # =========================================================================
    # 2026-03-04 (Austin ED - Labs 19163959, 19163992)
    # =========================================================================

    # D-Dimer
    r(conn, "2026-03-04", "19163959", AU, "Unknown Doctor",
      "Haematology", "D-Dimer", 1146, "1146", "ng/mL FEU",
      None, 500, "(< 500)", 1,
      "Pathology_Report_-_04th_March_2026__10.pdf")

    # SARS-CoV-2/Flu
    r(conn, "2026-03-04", "19163992", AU, "EMERGENCY DEPARTMENT",
      "Molecular", "SARS-CoV-2", None, "Not Detected", None,
      None, None, None, 0, "Pathology_Report_-_04th_March_2026__09.pdf")
    r(conn, "2026-03-04", "19163992", AU, "EMERGENCY DEPARTMENT",
      "Molecular", "Influenza A", None, "Not Detected", None,
      None, None, None, 0, "Pathology_Report_-_04th_March_2026__09.pdf")
    r(conn, "2026-03-04", "19163992", AU, "EMERGENCY DEPARTMENT",
      "Molecular", "Influenza B", None, "Not Detected", None,
      None, None, None, 0, "Pathology_Report_-_04th_March_2026__09.pdf")

    # =========================================================================
    # 2026-03-10 (Dorevitch Lab 79304480 + Lab 39780724)
    # =========================================================================
    lab = "79304480"
    date = "2026-03-10"

    # FBE
    for name, val, units, lo, hi in [
        ("Haemoglobin", 147, "g/L", 130, 180),
        ("WCC", 3.7, "x10^9/L", 4.0, 11.0),
        ("Platelets", 168, "x10^9/L", 150, 450),
        ("RCC", 4.78, "x10^12/L", 4.50, 6.50),
        ("PCV", 0.42, "L/L", 0.40, 0.54),
        ("MCV", 88, "fL", 80, 96),
        ("MCH", 31, "pg", 27, 32),
        ("MCHC", 349, "g/L", 320, 360),
        ("RDW", 12.5, "%", 11.0, 16.0),
        ("Neutrophils", 2.0, "x10^9/L", 2.0, 8.0),
        ("Lymphocytes", 1.3, "x10^9/L", 1.0, 4.0),
        ("Monocytes", 0.4, "x10^9/L", 0.0, 1.0),
        ("Eosinophils", 0.0, "x10^9/L", 0.0, 0.5),
        ("Basophils", 0.0, "x10^9/L", 0.0, 0.2),
    ]:
        abnormal = 0
        if lo is not None and val < lo:
            abnormal = 1
        if hi is not None and val > hi:
            abnormal = 1
        r(conn, date, lab, DV, doc_bala,
          "Full Blood Examination", name, val, str(val), units,
          lo, hi, f"({lo}-{hi})", abnormal,
          "Pathology_Report_-_10th_March_2026__02.pdf")

    # Biochemistry
    for name, val, units, lo, hi in [
        ("Sodium", 139, "mmol/L", 135, 145),
        ("Potassium", 4.0, "mmol/L", 3.5, 5.2),
        ("Chloride", 103, "mmol/L", 95, 110),
        ("Bicarbonate", 28, "mmol/L", 22, 32),
        ("Anion gap", 12, "mmol/L", 7, 17),
        ("Urea", 5.1, "mmol/L", 3.0, 10.0),
        ("eGFR", 85, "mL/min/1.73m2", 60, None),
        ("Creatinine", 84, "umol/L", 60, 110),
        ("Bilirubin", 13, "umol/L", 0, 20),
        ("ALT", 22, "U/L", 0, 45),
        ("AST", 25, "U/L", 0, 35),
        ("ALP", 61, "U/L", 30, 110),
        ("GGT", 18, "U/L", 0, 50),
        ("Total Protein", 71, "g/L", 60, 80),
        ("Albumin", 39, "g/L", 34, 47),
        ("Globulin", 32, "g/L", 22, 40),
    ]:
        ref = f"({lo}-{hi})" if hi else f"(> {lo})"
        abnormal = 0
        if lo is not None and val < lo:
            abnormal = 1
        if hi is not None and val > hi:
            abnormal = 1
        r(conn, date, lab, DV, doc_bala,
          "Biochemistry", name, val, str(val), units,
          lo, hi, ref, abnormal,
          "Pathology_Report_-_10th_March_2026__07.pdf")

    # Lipids
    for name, val, units in [
        ("Total Cholesterol", 4.8, "mmol/L"),
        ("Triglyceride", 1.7, "mmol/L"),
        ("HDL-C", 1.0, "mmol/L"),
        ("LDL-C", 3.0, "mmol/L"),
        ("Non HDL-C", 3.8, "mmol/L"),
        ("Chol/HDL Ratio", 4.8, None),
    ]:
        r(conn, date, lab, DV, doc_bala,
          "Lipid Studies", name, val, str(val), units,
          None, None, "Targets vary by CV risk", 0,
          "Pathology_Report_-_10th_March_2026__03.pdf")

    # Thyroid
    r(conn, date, lab, DV, doc_bala,
      "Thyroid Function", "Free T4", 17.9, "17.9", "pmol/L",
      10.0, 23.0, "(10.0-23.0)", 0,
      "Pathology_Report_-_10th_March_2026__06.pdf")
    r(conn, date, lab, DV, doc_bala,
      "Thyroid Function", "TSH", 1.98, "1.98", "mIU/L",
      0.50, 4.00, "(0.50-4.00)", 0,
      "Pathology_Report_-_10th_March_2026__06.pdf")
    r(conn, date, lab, DV, doc_bala,
      "Thyroid Function", "Free T3", 5.2, "5.2", "pmol/L",
      3.5, 6.5, "(3.5-6.5)", 0,
      "Pathology_Report_-_10th_March_2026__06.pdf")

    # Iron Studies
    r(conn, date, lab, DV, doc_bala,
      "Iron Studies", "Ferritin", 120, "120", "ug/L",
      30, 320, "(30-320)", 0, "Pathology_Report_-_10th_March_2026__08.pdf")
    r(conn, date, lab, DV, doc_bala,
      "Iron Studies", "Iron", 17, "17", "umol/L",
      10, 30, "(10-30)", 0, "Pathology_Report_-_10th_March_2026__08.pdf")
    r(conn, date, lab, DV, doc_bala,
      "Iron Studies", "Transferrin", 2.6, "2.6", "g/L",
      2.0, 3.6, "(2.0-3.6)", 0, "Pathology_Report_-_10th_March_2026__08.pdf")
    r(conn, date, lab, DV, doc_bala,
      "Iron Studies", "Transferrin Saturation", 26, "26", "%",
      13, 47, "(13-47)", 0, "Pathology_Report_-_10th_March_2026__08.pdf")

    # HbA1c
    r(conn, date, lab, DV, doc_bala,
      "HbA1c", "HbA1c %", 5.3, "5.3", "%",
      None, 6.5, "Diabetes cutoff 6.5%", 0,
      "Pathology_Report_-_10th_March_2026__04.pdf")
    r(conn, date, lab, DV, doc_bala,
      "HbA1c", "HbA1c mmol/mol", 34, "34", "mmol/mol",
      None, None, None, 0, "Pathology_Report_-_10th_March_2026__04.pdf")

    # B12 and Folate (Lab 39780724)
    r(conn, date, "39780724", DV, doc_ghosh,
      "Vitamin B12 and Folate", "Vitamin B12", 197, "197", "pmol/L",
      150, 700, "(150-700)", 0,
      "Pathology_Report_-_10th_March_2026__01.pdf")
    r(conn, date, "39780724", DV, doc_ghosh,
      "Vitamin B12 and Folate", "Serum Homocysteine", 15.7, "15.7", "nmol/L",
      None, None, None, 0,
      "Pathology_Report_-_10th_March_2026__01.pdf")
    r(conn, date, "39780724", DV, doc_ghosh,
      "Vitamin B12 and Folate", "Holotranscobalamin", 65, "65", "pmol/L",
      70, 140, "(70-140)", 1,
      "Pathology_Report_-_10th_March_2026__01.pdf")
    r(conn, date, "39780724", DV, doc_ghosh,
      "Vitamin B12 and Folate", "Serum Folate", 20.1, "20.1", "nmol/L",
      9.0, None, "(> 9.0)", 0,
      "Pathology_Report_-_10th_March_2026__01.pdf")


def print_summary(conn):
    """Print database summary stats."""
    cur = conn.cursor()

    count = cur.execute("SELECT COUNT(*) FROM test_results").fetchone()[0]
    dates = cur.execute("SELECT COUNT(DISTINCT collected_date) FROM test_results").fetchone()[0]
    panels = cur.execute("SELECT COUNT(DISTINCT test_panel) FROM test_results").fetchone()[0]
    tests = cur.execute("SELECT COUNT(DISTINCT test_name) FROM test_results").fetchone()[0]
    imaging = cur.execute("SELECT COUNT(*) FROM imaging_reports").fetchone()[0]
    abnormal = cur.execute("SELECT COUNT(*) FROM test_results WHERE is_abnormal = 1").fetchone()[0]

    click.echo(f"\nDatabase created at: {DB_PATH}")
    click.echo(f"  Total result rows:    {count}")
    click.echo(f"  Unique dates:         {dates}")
    click.echo(f"  Test panels:          {panels}")
    click.echo(f"  Unique test names:    {tests}")
    click.echo(f"  Abnormal results:     {abnormal}")
    click.echo(f"  Imaging reports:      {imaging}")

    click.echo("\n--- Collection dates ---")
    for row in cur.execute(
        "SELECT collected_date, COUNT(*) as n FROM test_results "
        "GROUP BY collected_date ORDER BY collected_date"
    ):
        click.echo(f"  {row[0]}  ({row[1]} tests)")

    click.echo("\n--- Test panels ---")
    for row in cur.execute(
        "SELECT test_panel, COUNT(*) as n FROM test_results "
        "GROUP BY test_panel ORDER BY test_panel"
    ):
        click.echo(f"  {row[0]:30s}  ({row[1]} results)")

    click.echo("\n--- Abnormal results ---")
    for row in cur.execute(
        "SELECT collected_date, test_name, value_text, units, ref_range_text "
        "FROM test_results WHERE is_abnormal = 1 ORDER BY collected_date"
    ):
        click.echo(f"  {row[0]}  {row[1]:30s} = {row[2]} {row[3] or ''} {row[4] or ''}")

    click.echo("\n--- Imaging reports ---")
    for row in cur.execute(
        "SELECT exam_date, exam_type, conclusion FROM imaging_reports ORDER BY exam_date"
    ):
        click.echo(f"  {row[0]}  {row[1]}")
        click.echo(f"    Conclusion: {row[2][:120]}...")


@click.command()
@click.option("--rebuild", is_flag=True, help="Rebuild database from scratch")
def main(rebuild):
    """Build the medical test results database from extracted PDF data."""
    if DB_PATH.exists() and not rebuild:
        click.echo(f"Database already exists at {DB_PATH}")
        click.echo("Use --rebuild to recreate it.")
        conn = sqlite3.connect(DB_PATH)
        print_summary(conn)
        conn.close()
        return

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    create_schema(conn)
    populate_data(conn)
    conn.commit()
    print_summary(conn)
    conn.close()
    click.echo("\nDone!")


if __name__ == "__main__":
    main()
