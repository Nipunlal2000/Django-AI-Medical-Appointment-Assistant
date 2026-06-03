# mcp_server.py
import asyncio

from fastmcp import FastMCP
import chromadb
from google import genai
import asyncpg
import json

from mcp_utils import error_response, success_response, tool_error_handler
from testproject import settings
from datetime import datetime, timedelta

mcp = FastMCP("Medical Semantic Core Engine")

ai_client = genai.Client(api_key=settings.config('GEMINI_API_KEY'))
for model in ai_client.models.list():
    print(model.name)

chroma_client = chromadb.PersistentClient(path="./chroma_db")

# Long term memory collection
doctor_collection = chroma_client.get_or_create_collection(name="doctor_specialties")
intent_collection = chroma_client.get_or_create_collection(name="intent_collection")
memory_collection = chroma_client.get_or_create_collection(name="conversation_memory")

DB_CONFIG = {
    "user": settings.DATABASES["default"]["USER"],
    "password": settings.DATABASES["default"]["PASSWORD"],
    "database": settings.DATABASES["default"]["NAME"],
    "host": settings.DATABASES["default"]["HOST"],
    "port": settings.DATABASES["default"]["PORT"],
}

# --- HELPER FUNCTIONS ---

# def success_response(data=None, message=None):
#     return json.dumps({
#         "success": True,
#         "message": message,
#         "data": data
#     }, default=str)


# def error_response(message):
#     return json.dumps({
#         "success": False,
#         "message": message,
#         "data": None
#     })


def resolve_date_query(date_query: str | None):
    if not date_query:
        return None, None

    text = str(date_query).lower().strip()
    today = datetime.now().date()

    if "today" in text:
        return today, today

    if "tomorrow" in text:
        d = today + timedelta(days=1)
        return d, d

    if "next week" in text:
        start = today + timedelta(days=7)
        end = start + timedelta(days=6)
        return start, end

    if "this week" in text:
        end = today + timedelta(days=6)
        return today, end

    # DD-MM-YYYY
    try:
        d = datetime.strptime(text, "%d-%m-%Y").date()
        return d, d

    except ValueError:
        return None, None


def format_tool_response(tool_name: str, parsed_response: dict) -> str:

    if not parsed_response.get("success"):
        return (
            parsed_response.get("message")
            or "Operation failed."
        )

    data = parsed_response.get("data")

    # ----------------------------
    # SEMANTIC SEARCH
    # ----------------------------
    if tool_name == "semantic_search_doctors":

        speciality = data["speciality"]
        doctors = data["doctors"]

        response = (
            f"I found the following available "
            f"{speciality} doctor(s):\n\n"
        )

        for idx, doctor in enumerate(doctors, start=1):

            response += (
                # f"{idx}. "
                f"{doctor['name']} "
                f"({doctor['location']})\n"
            )

        response += (
            "\nWould you like to book an appointment "
            "with one of them?"
        )

        return response

    # ----------------------------
    # GET DOCTORS
    # ----------------------------
    if tool_name == "get_doctors":

        response = "Available doctors:\n\n"

        for doctor in data:

            response += (
                f"• {doctor['name']} "
                f"({doctor['speciality']}) "
                f"- {doctor['location']}\n"
            )

        return response

    # ----------------------------
    # SEARCH PATIENTS
    # ----------------------------
    if tool_name == "search_patients":

        if len(data) == 1:

            return (
                f"Patient found: "
                f"{data[0]['name']} "
                f"(ID: {data[0]['id']})"
            )

        response = "Multiple patients found:\n\n"

        for patient in data:

            response += (
                f"• {patient['id']} - "
                f"{patient['name']}\n"
            )

        response += (
            "\nPlease specify which patient."
        )

        return response

    # ----------------------------
    # AVAILABLE SLOTS
    # ----------------------------
    if tool_name == "get_available_slots":

        response = "Available slots:\n\n"

        for idx, slot in enumerate(data, start=1):

            response += (
                f"{idx}. "
                f"{slot['start_time']} - "
                f"{slot['end_time']}\n"
            )

        response += (
            "\nPlease choose a slot."
        )

        return response

    # ----------------------------
    # BOOK APPOINTMENT
    # ----------------------------
    if tool_name == "book_appointment":

        return (
            f"Appointment booked successfully.\n\n"
            f"Appointment ID: "
            f"{data['appointment_id']}"
        )

    # ----------------------------
    # MEMORY
    # ----------------------------
    if tool_name == "save_memory":
        return parsed_response["message"]

    if tool_name == "recall_memory":

        if not data:
            return "No relevant memories found."

        response = "Relevant memories:\n\n"

        for item in data:
            response += f"• {item}\n"

        return response

    return json.dumps(
        parsed_response,
        indent=2
    )

async def get_available_doctors_by_speciality(
    speciality: str
):

    conn = await asyncpg.connect(**DB_CONFIG)

    try:

        rows = await conn.fetch(
            """
            SELECT
                id,
                name,
                speciality,
                location,
                is_available
            FROM "testApp_doctor"
            WHERE speciality ILIKE $1
            AND is_available = TRUE
            ORDER BY name
            """,
            speciality
        )

        return [
            dict(row)
            for row in rows
        ]

    finally:
        await conn.close()


# --- SYSTEM INITIALIZATION / VECTOR SEEDING ---

@mcp.tool()
@tool_error_handler
async def build_semantic_index() -> str:
    """
    Scrapes the live Django doctors database, converts their text specialties/profiles 
    into mathematical vectors, and indexes them into ChromaDB.
    """
    conn = await asyncpg.connect(**DB_CONFIG)
    try:
        rows = await conn.fetch('SELECT id, name, speciality, location, is_available FROM "testApp_doctor"')
        if not rows:
            return "No records found in Django database to seed vectors."
            
        for row in rows:
            doc_id = str(row["id"])
            text_context = f"Doctor {row['name']} is a specialist in {row['speciality']} located at {row['location']}."
            
            embedding_response = ai_client.models.embed_content(
                model="models/gemini-embedding-2",
                contents=text_context
            )
            vector = embedding_response.embeddings[0].values
            
            doctor_collection.upsert(
                ids=[doc_id],
                embeddings=[vector],
                documents=[text_context],
                metadatas=[{
                    "id": row["id"],
                    "name": row["name"],
                    "speciality": row["speciality"],
                    "location": row["location"],
                    "is_available": row["is_available"]
                }]

            )
        return f"Successfully vectorized and indexed {len(rows)} doctors into ChromaDB."
    finally:
        await conn.close()

@mcp.tool()
@tool_error_handler
async def build_intent_index() -> str:
    """
    Creates semantic intent vectors for routing user requests.
    """

    INTENTS = [
        ("find_doctor", "I have chest pain"),
        ("find_doctor", "My heart hurts"),
        ("find_doctor", "I have a skin rash"),
        ("find_doctor", "I need a doctor"),

        ("book_appointment", "Book an appointment"),
        ("book_appointment", "Schedule a consultation"),
        ("book_appointment", "I need an appointment tomorrow"),

        ("cancel_appointment", "Cancel my booking"),
        ("cancel_appointment", "I no longer need my appointment"),

        ("general_conversation", "Hello"),
        ("general_conversation", "How are you")
    ]

    for idx, (intent, text) in enumerate(INTENTS):

        embedding_response = ai_client.models.embed_content(
            model="models/gemini-embedding-2",
            contents=text
        )

        vector = embedding_response.embeddings[0].values

        intent_collection.upsert(
            ids=[str(idx)],
            embeddings=[vector],
            documents=[text],
            metadatas=[{
                "intent": intent
            }]
        )

    return success_response(
        message="Intent index built successfully."
    )


# --- MEMORY MANAGEMENT ---

@mcp.tool()
@tool_error_handler
async def save_memory(
    memory_text: str
) -> str:
    """
    Stores important conversation facts.
    """

    try:

        embedding_response = ai_client.models.embed_content(
            model="models/gemini-embedding-2",
            contents=memory_text
        )

        vector = embedding_response.embeddings[0].values

        memory_id = str(
            int(datetime.now().timestamp() * 1000)
        )

        memory_collection.upsert(
            ids=[memory_id],
            embeddings=[vector],
            documents=[memory_text]
        )

        return success_response(
            message="Memory saved."
        )

    except Exception as e:
        return error_response(str(e))

# --- MEMORY RETRIEVAL ---

@mcp.tool()
@tool_error_handler
async def recall_memory(
    query: str
) -> str:
    """
    Retrieves relevant memories.
    """

    try:

        embedding_response = ai_client.models.embed_content(
            model="models/gemini-embedding-2",
            contents=query
        )

        query_vector = embedding_response.embeddings[0].values

        results = memory_collection.query(
            query_embeddings=[query_vector],
            n_results=5
        )

        docs = results.get(
            "documents",
            [[]]
        )[0]

        return success_response(
            docs
        )

    except Exception as e:
        return error_response(str(e))


# --- SEMANTIC VECTOR SEARCH ---

@mcp.tool()
@tool_error_handler
async def semantic_search_doctors(
    user_symptom_prompt: str
) -> str:
    """
    Performs semantic similarity search against ChromaDB
    to find doctors relevant to a patient's symptoms.
    """

    try:
        embedding_response = ai_client.models.embed_content(
            model="models/gemini-embedding-2",
            contents=user_symptom_prompt
        )

        query_vector = embedding_response.embeddings[0].values

        results = doctor_collection.query(
            query_embeddings=[query_vector],
            n_results=5,
            include=["metadatas", "distances"]
        )

        if (
            not results
            or not results.get("metadatas")
            or not results["metadatas"][0]
        ):
            return error_response(
                "No matching doctors found."
            )

        matches = []

        metadatas = results["metadatas"][0]
        distances = results["distances"][0]
        best_speciality = metadatas[0]["speciality"]

        # print(
        #     f"[Semantic Match] "
        #     f"{user_symptom_prompt} "
        #     f"→ {best_speciality}"
        # )

        available_doctors = (
            await get_available_doctors_by_speciality(
                best_speciality
            )
        )

        if not available_doctors:

            return error_response(
                f"No available {best_speciality} doctors found."
            )

        return success_response(
            data={
                "speciality": best_speciality,
                "doctors": available_doctors
            },
            message=(
                f"Found "
                f"{len(available_doctors)} "
                f"available "
                f"{best_speciality} doctor(s)."
            )
        )

    except Exception as e:

        return error_response(
            f"Semantic search failed: {str(e)}"
        )

# --- TRADITIONAL CRUD OPERATIONS ---

@mcp.tool()
@tool_error_handler
async def get_doctors(
    speciality: str | None = None,
    location: str | None = None,
) -> str:
    """
    Returns doctors filtered by speciality and/or location.
    Used after semantic symptom matching identifies the required speciality.
    """

    conn = await asyncpg.connect(**DB_CONFIG)

    try:
        query = """
            SELECT
                id,
                name,
                speciality,
                location,
                is_available
            FROM "testApp_doctor"
            WHERE is_available = TRUE
        """

        params = []
        idx = 1

        if speciality:
            query += f" AND speciality ILIKE ${idx}"
            params.append(f"%{speciality}%")
            idx += 1

        if location:
            query += f" AND location ILIKE ${idx}"
            params.append(f"%{location}%")

        rows = await conn.fetch(query, *params)

        if not rows:
            return error_response("No doctors found")

        return success_response(
            [dict(row) for row in rows],
            "Doctors fetched successfully."
        )

    finally:
        await conn.close()


@mcp.tool()
@tool_error_handler
async def get_available_slots(
    doctor_id: int,
    date_query: str | None = None
) -> str:
    """
    Returns unbooked slots for a doctor on a given date.
    """

    conn = await asyncpg.connect(**DB_CONFIG)

    try:
        # Validate doctor
        doctor = await conn.fetchrow(
            """
            SELECT id
            FROM "testApp_doctor"
            WHERE id = $1
            """,
            doctor_id
        )

        if not doctor:
            return error_response("Doctor not found")

        if not date_query:
            return error_response(
                "Date is required. Examples: today, tomorrow, this week, next week."
            )

        start_date, end_date = resolve_date_query(
            date_query
        )

        if not start_date:
            return error_response(
                "Please provide a valid date or date range."
            )

        # Fetch slots

        rows = await conn.fetch(
            """
            SELECT
                das.id,
                das.start_time,
                das.end_time,
                da.date
            FROM "testApp_doctoravailabilityslot" das
            INNER JOIN "testApp_doctoravailability" da
                ON da.id = das.doctor_availability_id
            WHERE da.doctor_id = $1
            AND da.date BETWEEN $2 AND $3
            AND das.id NOT IN (
                    SELECT slot_id
                    FROM "testApp_bookappointment"
            )
            ORDER BY da.date, das.start_time
            """,
            doctor_id,
            start_date,
            end_date
        )

        if not rows:
            return error_response(
                "No available slots found"
            )

        return success_response(
            {
                "resolved_date_range": {
                    "start": str(start_date),
                    "end": str(end_date)
                },
                "slots": [dict(row) for row in rows]
            },
            "Available slots found"
        )

    finally:
        await conn.close()


@mcp.tool()
@tool_error_handler
async def search_patients(
    patient_name: str
) -> str:
    """
    Search patients by name.
    """

    conn = await asyncpg.connect(**DB_CONFIG)

    try:
        rows = await conn.fetch(
            """
            SELECT
                id,
                name,
                doctor_id
            FROM "testApp_patient"
            WHERE name ILIKE $1
            LIMIT 10
            """,
            f"%{patient_name}%"
        )

        if not rows:
            return error_response(
                "No matching patients found."
            )

        return success_response(
            [dict(row) for row in rows],
            f"Found {len(rows)} patient(s)."
        )

    except Exception as e:
        return error_response(str(e))

    finally:
        await conn.close()


@mcp.tool()
@tool_error_handler
async def get_patient(patient_id: int) -> str:
    """
    Fetches patient details.
    """

    conn = await asyncpg.connect(**DB_CONFIG)

    try:
        row = await conn.fetchrow(
            """
            SELECT
                id,
                name,
                doctor_id
            FROM "testApp_patient"
            WHERE id = $1
            """,
            patient_id,
        )

        if not row:
            return error_response("Patient not found")

        return success_response(dict(row))

    finally:
        await conn.close()

@mcp.tool()
@tool_error_handler
async def book_appointment(
    patient_id: int,
    doctor_id: int,
    slot_id: int,
) -> str:
    """
    Books an appointment for a patient with a doctor on a specific slot.
    """

    conn = await asyncpg.connect(**DB_CONFIG)

    try:
        async with conn.transaction():
            # Step 1: Validate Patient
            patient = await conn.fetchrow(
                """
                SELECT id
                FROM "testApp_patient"
                WHERE id = $1
                """,
                patient_id
            )

            if not patient:
                return error_response(
                    "Patient not found"
                )

            # Step 2: Validate Doctor
            doctor = await conn.fetchrow(
                """
                SELECT id
                FROM "testApp_doctor"
                WHERE id = $1
                """,
                doctor_id
            )

            if not doctor:
                return error_response(
                    "Doctor not found"
                )

            # Step 3: Validate Slot Exists
            slot = await conn.fetchrow(
                """
                SELECT
                    das.id,
                    da.doctor_id
                FROM "testApp_doctoravailabilityslot" das
                INNER JOIN "testApp_doctoravailability" da
                    ON da.id = das.doctor_availability_id
                WHERE das.id = $1
                """,
                slot_id
            )

            if not slot:
                return error_response(
                    "Slot not found"
                )

            # Step 4: Verify Slot Belongs To Doctor
            if slot["doctor_id"] != doctor_id:
                return error_response(
                    "Selected slot does not belong to selected doctor"
                )

            # Step 5: Check Existing Booking
            existing_booking = await conn.fetchrow(
                """
                SELECT id
                FROM "testApp_bookappointment"
                WHERE slot_id = $1
                """,
                slot_id
            )

            if existing_booking:
                return error_response(
                    "Slot already booked"
                )

            # Step 6: Insert Appointment
            appointment_id = await conn.fetchval(
                """
                INSERT INTO "testApp_bookappointment"
                (
                    patient_id,
                    doctor_id,
                    slot_id,
                    created_at,
                    updated_at
                )
                VALUES
                (
                    $1,
                    $2,
                    $3,
                    CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP
                )
                RETURNING id
                """,
                patient_id,
                doctor_id,
                slot_id
            )

            # Step 7: Return Structured Response
            return success_response(
                {
                    "appointment_id": appointment_id,
                    "patient_id": patient_id,
                    "doctor_id": doctor_id,
                    "slot_id": slot_id
                },
                "Appointment booked successfully"
            )

    finally:
        await conn.close()


# Create an automatic boot-up initializer
async def auto_seed_if_empty():
    """Checks if ChromaDB collections are empty and seeds them automatically."""

    try:
        doctor_count = doctor_collection.count()

        if doctor_count == 0:
            print(
                "\n[ChromaDB Notice]: Doctor collection is empty. Building doctor index..."
            )
            result = await build_semantic_index()
            print(f"[ChromaDB Notice]: {result}\n")
        else:
            print(
                f"\n[ChromaDB Notice]: Loaded {doctor_count} doctor vectors.\n"
            )

        intent_count = intent_collection.count()

        if intent_count == 0:
            print(
                "\n[ChromaDB Notice]: Intent collection is empty. Building intent index..."
            )
            result = await build_intent_index()
            print(f"[ChromaDB Notice]: {result}\n")
        else:
            print(
                f"\n[ChromaDB Notice]: Loaded {intent_count} intent vectors.\n"
            )

    except Exception as e:
        print(
            f"[ChromaDB Warning]: Could not initialize collections: {str(e)}"
        )


if __name__ == "__main__":
    # Run the async initialization function inside the local loop before starting the server
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(auto_seed_if_empty())
    
    # Fire up the Server-Sent Events transport framework
    mcp.run(transport="sse", port=8080)
