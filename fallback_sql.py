def get_fallback_sql(question: str) -> str | None:
    normalized = " ".join(question.lower().split())
    return _FALLBACK_SQL.get(normalized)


_FALLBACK_SQL = {
    "how many patients do we have?": "SELECT COUNT(*) AS total_patients FROM patients;",
    "list all doctors and their specializations": (
        "SELECT name, specialization, department "
        "FROM doctors ORDER BY specialization, name;"
    ),
    "show me appointments for last month": (
        "SELECT a.id, p.first_name, p.last_name, d.name AS doctor, a.appointment_date, a.status "
        "FROM appointments a "
        "JOIN patients p ON p.id = a.patient_id "
        "JOIN doctors d ON d.id = a.doctor_id "
        "WHERE date(a.appointment_date) >= date('now', 'start of month', '-1 month') "
        "AND date(a.appointment_date) < date('now', 'start of month') "
        "ORDER BY a.appointment_date DESC;"
    ),
    "which doctor has the most appointments?": (
        "SELECT d.name, COUNT(a.id) AS appointment_count "
        "FROM doctors d "
        "LEFT JOIN appointments a ON a.doctor_id = d.id "
        "GROUP BY d.id, d.name "
        "ORDER BY appointment_count DESC LIMIT 1;"
    ),
    "what is the total revenue?": (
        "SELECT SUM(total_amount) AS total_revenue FROM invoices;"
    ),
    "show revenue by doctor": (
        "SELECT d.name, SUM(t.cost) AS total_revenue "
        "FROM treatments t "
        "JOIN appointments a ON a.id = t.appointment_id "
        "JOIN doctors d ON d.id = a.doctor_id "
        "GROUP BY d.id, d.name "
        "ORDER BY total_revenue DESC;"
    ),
    "how many cancelled appointments last quarter?": (
        "SELECT COUNT(*) AS cancelled_appointments "
        "FROM appointments "
        "WHERE status = 'Cancelled' "
        "AND date(appointment_date) >= date('now', 'start of month', '-3 months') "
        "AND date(appointment_date) < date('now', 'start of month');"
    ),
    "top 5 patients by spending": (
        "SELECT p.first_name, p.last_name, SUM(i.total_amount) AS total_spending "
        "FROM invoices i "
        "JOIN patients p ON p.id = i.patient_id "
        "GROUP BY p.id, p.first_name, p.last_name "
        "ORDER BY total_spending DESC LIMIT 5;"
    ),
    "show me the top 5 patients by total spending": (
        "SELECT p.first_name, p.last_name, SUM(i.total_amount) AS total_spending "
        "FROM invoices i "
        "JOIN patients p ON p.id = i.patient_id "
        "GROUP BY p.id, p.first_name, p.last_name "
        "ORDER BY total_spending DESC LIMIT 5;"
    ),
    "average treatment cost by specialization": (
        "SELECT d.specialization, AVG(t.cost) AS average_treatment_cost "
        "FROM treatments t "
        "JOIN appointments a ON a.id = t.appointment_id "
        "JOIN doctors d ON d.id = a.doctor_id "
        "GROUP BY d.specialization "
        "ORDER BY average_treatment_cost DESC;"
    ),
    "show monthly appointment count for the past 6 months": (
        "SELECT strftime('%Y-%m', appointment_date) AS month, COUNT(*) AS appointment_count "
        "FROM appointments "
        "WHERE date(appointment_date) >= date('now', '-6 months') "
        "GROUP BY month ORDER BY month;"
    ),
    "which city has the most patients?": (
        "SELECT city, COUNT(*) AS patient_count "
        "FROM patients GROUP BY city ORDER BY patient_count DESC LIMIT 1;"
    ),
    "list patients who visited more than 3 times": (
        "SELECT p.first_name, p.last_name, COUNT(a.id) AS visit_count "
        "FROM patients p "
        "JOIN appointments a ON a.patient_id = p.id "
        "GROUP BY p.id, p.first_name, p.last_name "
        "HAVING COUNT(a.id) > 3 "
        "ORDER BY visit_count DESC;"
    ),
    "show unpaid invoices": (
        "SELECT p.first_name, p.last_name, i.invoice_date, i.total_amount, i.paid_amount, i.status "
        "FROM invoices i "
        "JOIN patients p ON p.id = i.patient_id "
        "WHERE i.status IN ('Pending', 'Overdue') "
        "ORDER BY i.status, i.invoice_date;"
    ),
    "what percentage of appointments are no-shows?": (
        "SELECT ROUND(100.0 * SUM(CASE WHEN status = 'No-Show' THEN 1 ELSE 0 END) / COUNT(*), 2) "
        "AS no_show_percentage "
        "FROM appointments;"
    ),
    "show the busiest day of the week for appointments": (
        "SELECT CASE strftime('%w', appointment_date) "
        "WHEN '0' THEN 'Sunday' WHEN '1' THEN 'Monday' WHEN '2' THEN 'Tuesday' "
        "WHEN '3' THEN 'Wednesday' WHEN '4' THEN 'Thursday' WHEN '5' THEN 'Friday' "
        "WHEN '6' THEN 'Saturday' END AS day_of_week, "
        "COUNT(*) AS appointment_count "
        "FROM appointments "
        "GROUP BY strftime('%w', appointment_date) "
        "ORDER BY appointment_count DESC LIMIT 1;"
    ),
    "revenue trend by month": (
        "SELECT strftime('%Y-%m', invoice_date) AS month, SUM(total_amount) AS total_revenue "
        "FROM invoices GROUP BY month ORDER BY month;"
    ),
    "average appointment duration by doctor": (
        "SELECT d.name, AVG(t.duration_minutes) AS average_duration_minutes "
        "FROM doctors d "
        "JOIN appointments a ON a.doctor_id = d.id "
        "JOIN treatments t ON t.appointment_id = a.id "
        "GROUP BY d.id, d.name "
        "ORDER BY average_duration_minutes DESC;"
    ),
    "list patients with overdue invoices": (
        "SELECT p.first_name, p.last_name, i.invoice_date, i.total_amount, i.paid_amount "
        "FROM invoices i "
        "JOIN patients p ON p.id = i.patient_id "
        "WHERE i.status = 'Overdue' "
        "ORDER BY i.invoice_date DESC;"
    ),
    "compare revenue between departments": (
        "SELECT d.department, SUM(t.cost) AS total_revenue "
        "FROM treatments t "
        "JOIN appointments a ON a.id = t.appointment_id "
        "JOIN doctors d ON d.id = a.doctor_id "
        "GROUP BY d.department "
        "ORDER BY total_revenue DESC;"
    ),
    "show patient registration trend by month": (
        "SELECT strftime('%Y-%m', registered_date) AS month, COUNT(*) AS registrations "
        "FROM patients GROUP BY month ORDER BY month;"
    ),
}
