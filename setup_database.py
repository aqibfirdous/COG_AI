import sqlite3
import random
from datetime import datetime, timedelta, date

DB_PATH = "clinic.db"

# ─── Schema ────────────────────────────────────────────────────────────────────

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS patients (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name      TEXT NOT NULL,
    last_name       TEXT NOT NULL,
    email           TEXT,
    phone           TEXT,
    date_of_birth   DATE,
    gender          TEXT CHECK(gender IN ('M','F')),
    city            TEXT,
    registered_date DATE
);

CREATE TABLE IF NOT EXISTS doctors (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    specialization  TEXT,
    department      TEXT,
    phone           TEXT
);

CREATE TABLE IF NOT EXISTS appointments (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id       INTEGER REFERENCES patients(id),
    doctor_id        INTEGER REFERENCES doctors(id),
    appointment_date DATETIME,
    status           TEXT CHECK(status IN ('Scheduled','Completed','Cancelled','No-Show')),
    notes            TEXT
);

CREATE TABLE IF NOT EXISTS treatments (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    appointment_id     INTEGER REFERENCES appointments(id),
    treatment_name     TEXT,
    cost               REAL,
    duration_minutes   INTEGER
);

CREATE TABLE IF NOT EXISTS invoices (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id   INTEGER REFERENCES patients(id),
    invoice_date DATE,
    total_amount REAL,
    paid_amount  REAL,
    status       TEXT CHECK(status IN ('Paid','Pending','Overdue'))
);
"""

# ─── Seed data ─────────────────────────────────────────────────────────────────

FIRST_NAMES_M = ["James","John","Robert","Michael","David","William","Richard","Joseph","Thomas","Charles",
                 "Arjun","Rahul","Vikram","Rohan","Aditya","Omar","Hassan","Ali","Yusuf","Ahmed",
                 "Chen","Wei","Ming","Hao","Jun","Carlos","Miguel","Pedro","Luis","Juan"]

FIRST_NAMES_F = ["Mary","Patricia","Jennifer","Linda","Barbara","Susan","Jessica","Sarah","Karen","Lisa",
                 "Priya","Anjali","Sneha","Pooja","Neha","Fatima","Zainab","Aisha","Layla","Nour",
                 "Mei","Ling","Xue","Fang","Lan","Maria","Ana","Sofia","Elena","Rosa"]

LAST_NAMES   = ["Smith","Johnson","Williams","Brown","Jones","Garcia","Miller","Davis","Wilson","Taylor",
                "Patel","Sharma","Singh","Kumar","Verma","Khan","Ahmed","Hassan","Ali","Rahman",
                "Chen","Wang","Zhang","Liu","Li","Rodriguez","Martinez","Hernandez","Lopez","Gonzalez"]

CITIES       = ["Mumbai","Delhi","Bangalore","Hyderabad","Chennai","Kolkata","Pune","Ahmedabad","Jaipur","Surat"]

SPECIALIZATIONS = {
    "Dermatology":  "Skin & Hair",
    "Cardiology":   "Heart & Vascular",
    "Orthopedics":  "Bone & Joint",
    "General":      "General Medicine",
    "Pediatrics":   "Child Health",
}

DOCTOR_NAMES = [
    ("Dr. Sarah Mitchell",   "Dermatology"),
    ("Dr. Ravi Patel",       "Dermatology"),
    ("Dr. Emily Chen",       "Dermatology"),
    ("Dr. James Okafor",     "Cardiology"),
    ("Dr. Priya Sharma",     "Cardiology"),
    ("Dr. Michael Torres",   "Cardiology"),
    ("Dr. Aisha Rahman",     "Orthopedics"),
    ("Dr. David Nguyen",     "Orthopedics"),
    ("Dr. Fatima Al-Sayed",  "Orthopedics"),
    ("Dr. Carlos Mendez",    "General"),
    ("Dr. Linda Zhao",       "General"),
    ("Dr. Raj Krishnamurthy","General"),
    ("Dr. Susan Park",       "Pediatrics"),
    ("Dr. Ahmed Hassan",     "Pediatrics"),
    ("Dr. Meera Iyer",       "Pediatrics"),
]

TREATMENT_NAMES = {
    "Dermatology":  ["Acne Treatment","Skin Biopsy","Chemical Peel","Laser Therapy","Eczema Treatment","Mole Removal"],
    "Cardiology":   ["ECG","Echocardiogram","Stress Test","Angioplasty","Holter Monitor","Cardiac Consult"],
    "Orthopedics":  ["X-Ray","MRI Scan","Joint Injection","Physiotherapy Session","Fracture Management","Arthroscopy"],
    "General":      ["General Checkup","Blood Test","Vaccination","BP Monitoring","Glucose Test","Prescription Review"],
    "Pediatrics":   ["Well-Child Visit","Immunization","Growth Assessment","Ear Check","Allergy Test","Developmental Screening"],
}

APPOINTMENT_NOTES = [
    "Patient reported improvement.", "Follow-up required in 2 weeks.",
    "Referred to specialist.", "Medication adjusted.",
    "No complications noted.", "Patient advised rest.",
    None, None, None,  # some nulls
]

def random_date(start_days_ago: int, end_days_ago: int = 0) -> date:
    delta = random.randint(end_days_ago, start_days_ago)
    return (datetime.today() - timedelta(days=delta)).date()

def random_datetime(start_days_ago: int, end_days_ago: int = 0) -> datetime:
    delta = random.randint(end_days_ago, start_days_ago)
    hour  = random.randint(8, 17)
    minute = random.choice([0, 15, 30, 45])
    return datetime.today() - timedelta(days=delta, hours=24 - hour, minutes=minute)

def random_email(first: str, last: str) -> str | None:
    if random.random() < 0.15:   # 15 % null
        return None
    domains = ["gmail.com","yahoo.com","outlook.com","hotmail.com","mail.com"]
    return f"{first.lower()}.{last.lower()}{random.randint(1,99)}@{random.choice(domains)}"

def random_phone() -> str | None:
    if random.random() < 0.10:
        return None
    return f"+91-{random.randint(7000000000, 9999999999)}"

# ─── Main builder ──────────────────────────────────────────────────────────────

def build_database():
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    # Drop existing tables so the script is idempotent
    for tbl in ("invoices","treatments","appointments","doctors","patients"):
        cur.execute(f"DROP TABLE IF EXISTS {tbl}")
    conn.executescript(SCHEMA_SQL)
    conn.commit()

    # ── Doctors ──────────────────────────────────────────────────────────────
    doctor_rows = []
    for name, spec in DOCTOR_NAMES:
        dept  = SPECIALIZATIONS[spec]
        phone = random_phone() or f"+91-{random.randint(7000000000,9999999999)}"
        doctor_rows.append((name, spec, dept, phone))

    cur.executemany(
        "INSERT INTO doctors (name, specialization, department, phone) VALUES (?,?,?,?)",
        doctor_rows
    )
    doctor_ids = [row[0] for row in cur.execute("SELECT id FROM doctors").fetchall()]
    doctor_spec = {row[0]: row[1] for row in cur.execute("SELECT id, specialization FROM doctors").fetchall()}
    conn.commit()

    # ── Patients ─────────────────────────────────────────────────────────────
    patient_rows = []
    for _ in range(200):
        gender = random.choice(["M","F"])
        first  = random.choice(FIRST_NAMES_M if gender == "M" else FIRST_NAMES_F)
        last   = random.choice(LAST_NAMES)
        dob    = random_date(365 * 70, 365 * 18)   # 18–70 years old
        reg    = random_date(365 * 3, 0)
        patient_rows.append((
            first, last,
            random_email(first, last),
            random_phone(),
            str(dob),
            gender,
            random.choice(CITIES),
            str(reg),
        ))

    cur.executemany(
        "INSERT INTO patients (first_name,last_name,email,phone,date_of_birth,gender,city,registered_date)"
        " VALUES (?,?,?,?,?,?,?,?)",
        patient_rows
    )
    patient_ids = [row[0] for row in cur.execute("SELECT id FROM patients").fetchall()]
    conn.commit()

    # ── Appointments ─────────────────────────────────────────────────────────
    # Make some patients repeat visitors (power users)
    power_patients = random.sample(patient_ids, k=40)
    appointment_map: dict[int, list[int]] = {}   # doctor_id → [appointment_ids]

    statuses       = ["Scheduled","Completed","Cancelled","No-Show"]
    status_weights = [0.10, 0.65, 0.15, 0.10]

    appt_rows = []
    for _ in range(500):
        pid    = random.choice(power_patients) if random.random() < 0.4 else random.choice(patient_ids)
        did    = random.choice(doctor_ids)
        dt     = random_datetime(365, 0)
        status = random.choices(statuses, weights=status_weights)[0]
        notes  = random.choice(APPOINTMENT_NOTES)
        appt_rows.append((pid, did, str(dt), status, notes))

    cur.executemany(
        "INSERT INTO appointments (patient_id,doctor_id,appointment_date,status,notes)"
        " VALUES (?,?,?,?,?)",
        appt_rows
    )
    appts = cur.execute(
        "SELECT id, doctor_id, status FROM appointments"
    ).fetchall()
    conn.commit()

    # ── Treatments (linked to Completed appointments only) ───────────────────
    completed_appts = [(a[0], a[1]) for a in appts if a[2] == "Completed"]
    # Use ~350 of them
    selected = random.sample(completed_appts, k=min(350, len(completed_appts)))

    treatment_rows = []
    for appt_id, doc_id in selected:
        spec   = doctor_spec[doc_id]
        tnames = TREATMENT_NAMES[spec]
        tname  = random.choice(tnames)
        cost   = round(random.uniform(50, 5000), 2)
        dur    = random.randint(10, 120)
        treatment_rows.append((appt_id, tname, cost, dur))

    cur.executemany(
        "INSERT INTO treatments (appointment_id, treatment_name, cost, duration_minutes)"
        " VALUES (?,?,?,?)",
        treatment_rows
    )
    conn.commit()

    # ── Invoices ─────────────────────────────────────────────────────────────
    inv_statuses       = ["Paid","Pending","Overdue"]
    inv_status_weights = [0.55, 0.25, 0.20]

    invoice_rows = []
    for _ in range(300):
        pid    = random.choice(patient_ids)
        inv_dt = random_date(365, 0)
        total  = round(random.uniform(100, 8000), 2)
        status = random.choices(inv_statuses, weights=inv_status_weights)[0]
        if status == "Paid":
            paid = total
        elif status == "Pending":
            paid = round(random.uniform(0, total * 0.5), 2)
        else:  # Overdue
            paid = round(random.uniform(0, total * 0.3), 2)
        invoice_rows.append((pid, str(inv_dt), total, paid, status))

    cur.executemany(
        "INSERT INTO invoices (patient_id, invoice_date, total_amount, paid_amount, status)"
        " VALUES (?,?,?,?,?)",
        invoice_rows
    )
    conn.commit()

    # ── Summary ──────────────────────────────────────────────────────────────
    counts = {
        "patients":     cur.execute("SELECT COUNT(*) FROM patients").fetchone()[0],
        "doctors":      cur.execute("SELECT COUNT(*) FROM doctors").fetchone()[0],
        "appointments": cur.execute("SELECT COUNT(*) FROM appointments").fetchone()[0],
        "treatments":   cur.execute("SELECT COUNT(*) FROM treatments").fetchone()[0],
        "invoices":     cur.execute("SELECT COUNT(*) FROM invoices").fetchone()[0],
    }
    conn.close()

    print(f"✅  clinic.db created successfully!")
    print(f"   Patients    : {counts['patients']}")
    print(f"   Doctors     : {counts['doctors']}")
    print(f"   Appointments: {counts['appointments']}")
    print(f"   Treatments  : {counts['treatments']}")
    print(f"   Invoices    : {counts['invoices']}")


if __name__ == "__main__":
    build_database()
