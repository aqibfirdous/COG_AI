import asyncio

from vanna.core.tool import ToolContext
from vanna.core.user import User

QA_PAIRS = [
    {
        "question": "How many patients do we have?",
        "sql": "SELECT COUNT(*) AS total_patients FROM patients;",
    },
    {
        "question": "List all patients from Mumbai",
        "sql": (
            "SELECT first_name, last_name, email, phone "
            "FROM patients WHERE city = 'Mumbai' ORDER BY last_name;"
        ),
    },
    {
        "question": "How many male and female patients do we have?",
        "sql": "SELECT gender, COUNT(*) AS count FROM patients GROUP BY gender;",
    },
    {
        "question": "Which city has the most patients?",
        "sql": (
            "SELECT city, COUNT(*) AS patient_count "
            "FROM patients GROUP BY city ORDER BY patient_count DESC LIMIT 1;"
        ),
    },
    {
        "question": "List all doctors and their specializations",
        "sql": (
            "SELECT name, specialization, department "
            "FROM doctors ORDER BY specialization, name;"
        ),
    },
    {
        "question": "Which doctor has the most appointments?",
        "sql": (
            "SELECT d.name, COUNT(a.id) AS appointment_count "
            "FROM doctors d "
            "LEFT JOIN appointments a ON a.doctor_id = d.id "
            "GROUP BY d.id, d.name ORDER BY appointment_count DESC LIMIT 1;"
        ),
    },
    {
        "question": "Show number of appointments per doctor",
        "sql": (
            "SELECT d.name, d.specialization, COUNT(a.id) AS appointment_count "
            "FROM doctors d "
            "LEFT JOIN appointments a ON a.doctor_id = d.id "
            "GROUP BY d.id, d.name, d.specialization "
            "ORDER BY appointment_count DESC;"
        ),
    },
    {
        "question": "How many appointments were cancelled?",
        "sql": "SELECT COUNT(*) AS cancelled_count FROM appointments WHERE status = 'Cancelled';",
    },
    {
        "question": "Show appointments by status",
        "sql": "SELECT status, COUNT(*) AS count FROM appointments GROUP BY status ORDER BY count DESC;",
    },
    {
        "question": "Show monthly appointment count for the past 6 months",
        "sql": (
            "SELECT strftime('%Y-%m', appointment_date) AS month, "
            "COUNT(*) AS appointment_count "
            "FROM appointments "
            "WHERE appointment_date >= date('now', '-6 months') "
            "GROUP BY month ORDER BY month;"
        ),
    },
    {
        "question": "What is the total revenue from paid invoices?",
        "sql": "SELECT SUM(paid_amount) AS total_revenue FROM invoices WHERE status = 'Paid';",
    },
    {
        "question": "Show revenue by doctor",
        "sql": (
            "SELECT d.name, SUM(i.total_amount) AS total_revenue "
            "FROM invoices i "
            "JOIN appointments a ON a.patient_id = i.patient_id "
            "JOIN doctors d ON d.id = a.doctor_id "
            "GROUP BY d.id, d.name ORDER BY total_revenue DESC;"
        ),
    },
    {
        "question": "Show unpaid invoices",
        "sql": (
            "SELECT p.first_name, p.last_name, i.invoice_date, "
            "i.total_amount, i.paid_amount, i.status "
            "FROM invoices i "
            "JOIN patients p ON p.id = i.patient_id "
            "WHERE i.status IN ('Pending', 'Overdue') "
            "ORDER BY i.status, i.invoice_date;"
        ),
    },
    {
        "question": "Show appointments from the last 3 months",
        "sql": (
            "SELECT a.id, p.first_name, p.last_name, d.name AS doctor, "
            "a.appointment_date, a.status "
            "FROM appointments a "
            "JOIN patients p ON p.id = a.patient_id "
            "JOIN doctors d ON d.id = a.doctor_id "
            "WHERE a.appointment_date >= date('now', '-3 months') "
            "ORDER BY a.appointment_date DESC;"
        ),
    },
    {
        "question": "Top 5 patients by total spending",
        "sql": (
            "SELECT p.first_name, p.last_name, SUM(i.total_amount) AS total_spending "
            "FROM invoices i "
            "JOIN patients p ON p.id = i.patient_id "
            "GROUP BY p.id, p.first_name, p.last_name "
            "ORDER BY total_spending DESC LIMIT 5;"
        ),
    },
]


async def preload_agent_memory(memory, *, conversation_id: str, request_id: str):
    context = ToolContext(
        user=User(id="seed-script", username="seed-script"),
        conversation_id=conversation_id,
        request_id=request_id,
        agent_memory=memory,
    )
    for pair in QA_PAIRS:
        await memory.save_tool_usage(
            question=pair["question"],
            tool_name="run_sql",
            args={"sql": pair["sql"]},
            context=context,
            success=True,
        )


def preload_agent_memory_sync(memory, *, conversation_id: str, request_id: str):
    asyncio.run(
        preload_agent_memory(
            memory, conversation_id=conversation_id, request_id=request_id
        )
    )
