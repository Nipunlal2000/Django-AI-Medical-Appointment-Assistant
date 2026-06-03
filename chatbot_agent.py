# chatbot_agent.py
import asyncio
import os
import sys
import json
from google import genai
from google.genai import types
from fastmcp import Client
import logging

logger = logging.getLogger(__name__)

from mcp_server import format_tool_response
from testproject import settings
from chatbot_utils import send_to_gemini

def sanitize_schema(schema: dict) -> dict:
    """
    Recursively removes non-standard metadata keys like 'additional_properties'
    that cause Gemini's Function Declaration validator to throw a 400 error.
    """
    if not isinstance(schema, dict):
        return schema
        
    bad_keys = ["additional_properties", "additionalProperties", "$schema"]
    cleaned = {k: sanitize_schema(v) for k, v in schema.items() if k not in bad_keys}
    
    if "properties" in cleaned and cleaned["properties"] == {}:
        cleaned.pop("properties")
        
    return cleaned

# Initialize conversation state container
from datetime import date

conversation_state = {
    "intent": None,
    "symptoms": None,
    "doctor_id": None,
    "doctor_name": None,
    "appointment_date": None,
    "slot_id": None,
    "patient_id": None,
    "patient_name": None,
    "available_slots": [],
    "candidate_doctors": [],
}

def update_state(**kwargs):
    """
    Update only provided values.
    """
    for key, value in kwargs.items():
        if value is not None:
            conversation_state[key] = value


def reset_state():
    global conversation_state

    conversation_state = {
        "intent": None,
        "symptoms": None,
        "doctor_id": None,
        "doctor_name": None,
        "appointment_date": None,
        "slot_id": None,
        "patient_id": None,
        "patient_name": None,
        "available_slots": [],
        "candidate_doctors": [],
    }


def print_state():
    print("\n[Conversation State]")
    print(json.dumps(conversation_state, indent=2))


def detect_slot_selection(user_input: str):
    """
    Detect simple slot selection phrases.
    Returns slot index or None.
    """

    text = user_input.lower().strip()

    mappings = {
        "first": 0,
        "1": 0,
        "one": 0,

        "second": 1,
        "2": 1,
        "two": 1,

        "third": 2,
        "3": 2,
        "three": 2,

        "fourth": 3,
        "4": 3,
        "four": 3,

        "fifth": 4,
        "5": 4,
        "five": 4,
    }

    for word, index in mappings.items():
        if word in text:
            return index

    return None

def detect_doctor_selection(user_input):

    doctors = conversation_state.get("candidate_doctors", [])

    text = user_input.lower().strip()

    # Number selection
    mappings = {
        "first": 0,
        "1": 0,
        "one": 0,
        "second": 1,
        "2": 1,
        "two": 1,
        "third": 2,
        "3": 2,
        "three": 2,
    }

    for word, index in mappings.items():
        if word in text and index < len(doctors):
            return doctors[index]

    # Name selection

    for doctor in doctors:
        if doctor["name"].lower() in text:
            return doctor
    return None

async def run_chatbot():
    api_key = settings.config('GEMINI_API_KEY')

    if not api_key:
        print("Error: Please set your GEMINI_API_KEY environment variable.")
        sys.exit(1)

    # FIX: Explicitly pass the resolved configuration key to the SDK client initializer
    ai_client = genai.Client(api_key=api_key)

    async with Client("http://127.0.0.1:8080/sse") as mcp_client:
        # Discover and translate vector tools
        available_tools = await mcp_client.list_tools()
        gemini_tools = []
        for tool in available_tools:
            schema_dict = tool.inputSchema if hasattr(tool, 'inputSchema') else {}
            if hasattr(schema_dict, 'model_dump'):
                schema_dict = schema_dict.model_dump()
            gemini_tools.append(
                types.Tool(
                    function_declarations=[
                        types.FunctionDeclaration(
                            name=tool.name,
                            description=tool.description,
                            parameters=sanitize_schema(schema_dict)
                        )
                    ]
                )
            )

        system_instruction = """
            You are an advanced medical appointment assistant.

            Current year: 2026.

            Your job is to help users find appropriate doctors, check appointment availability, and book appointments using the available MCP tools.

            CONVERSATION RULES

            1. Always use the conversation state provided in the prompt as the source of truth for previously collected information.

            2. Never assume missing information. If required information is missing, ask a follow-up question.

            3. Keep responses concise, conversational, and focused on completing the user's goal.

            INTENT HANDLING

            When a user describes symptoms, medical concerns, illnesses, discomfort, pain, or requests medical help:

            * If the detected intent is find_doctor, call semantic_search_doctors.

            Examples:

            * "My heart hurts"
            * "I have chest pain"
            * "I feel dizzy"
            * "My skin has a rash"

            MEMORY RULES

            Use recall_memory when previous user preferences,
            medical history,
            or prior interactions may be relevant.

            Use save_memory for important persistent facts such as:

            - Preferred appointment times
            - Chronic conditions
            - Frequently consulted specialties

            DOCTOR DISCOVERY WORKFLOW

            When the user is looking for medical help:

            1. Call semantic_search_doctors.
            2. Present the most relevant doctor(s).
            3. Save the selected doctor information into conversation state when available.
            4. Ask whether the user would like to book an appointment.
            5. If doctor_id already exists in conversation state, do not search for doctors again unless the user requests a different doctor.

            APPOINTMENT BOOKING WORKFLOW

            Before booking an appointment you must have:

            * patient_id
            * doctor_id
            * appointment_date
            * slot_id

            If any are missing, ask for them.

            When doctor_id and appointment_date are available:

            * Call get_available_slots.
            * get_available_slots accepts:

                doctor_id
                date_query

                Examples:
                today
                tomorrow
                this week
                next week
                05-06-2026
            
            Never call get_available_slots without a date_query.

            If date_query is missing, ask the user:
            "Which date would you like to check? Examples: today, tomorrow, this week, next week."

            When all required information is available:

            * Call book_appointment.
            * Confirm the booking result to the user.

            DOCTOR LOOKUP

            When the user asks for doctors directly:

            * Call get_doctors.
            * Use speciality and location filters when provided.

            PATIENT LOOKUP

            When patient identity is unknown:

            1. Call search_patients.
            2. Allow user to choose patient.
            3. Store selected patient_id.

            When patient information is required:

            * Call get_patient.

            ERROR HANDLING

            If any tool returns:

            {
            "success": false
            }

            Explain the issue clearly and help the user continue.

            Examples:

            * Doctor not found
            * Patient not found
            * No available slots found
            * Slot already booked

            TOOL USAGE RULES

            Use only the provided MCP tools.

            Available tools:

            * semantic_search_doctors
            * search_patients
            * get_doctors
            * get_available_slots
            * get_patient
            * book_appointment

            Do not generate SQL.
            Do not invent doctor IDs.
            Do not invent patient IDs.
            Do not invent slot IDs.
            Always rely on tool responses.

        """

        # Initialize an ongoing historical chat session context block natively
        from chatbot_utils import create_chat

        chat = create_chat(
            ai_client,
            gemini_tools,
            system_instruction
        )

        if not chat:
            print("AI: Assistant is temporarily unavailable.")
            return

        print("="*60)
        print("System Live: Conceptual Semantic AI Assistant Activated.")
        print("Type 'exit' to quit.")
        print("="*60)

        while True:
            user_input = input("\nYou: ")
            if user_input.strip().lower() == "exit":
                break

            # Print current conversation state for debugging
            if user_input.strip().lower() == "state":
                print_state()
                continue

            # -----------------------------
            # DOCTOR SELECTION EXTRACTION
            # -----------------------------

            selected_doctor = detect_doctor_selection(
                user_input
            )

            if selected_doctor:

                update_state(
                    doctor_id=selected_doctor["id"],
                    doctor_name=selected_doctor["name"],
                    available_slots=[],
                    slot_id=None
                )

            # -----------------------------
            # SLOT SELECTION EXTRACTION
            # -----------------------------

            slot_index = detect_slot_selection(
                user_input
            )

            if (
                slot_index is not None
                and conversation_state["available_slots"]
            ):
                slots = conversation_state[
                    "available_slots"
                ]

                if slot_index < len(slots):

                    update_state(
                        slot_id=slots[slot_index]["id"]
                    )

            # -----------------------------------
            # SEND TO GEMINI
            # -----------------------------------

            # Send message down the native chat session lifecycle
            state_context = f"""
            
            Current Conversation State:
            {json.dumps(conversation_state, indent=2)}
            
            Latest User Message:
            {user_input}
            """

            response = send_to_gemini(chat, state_context)

            if isinstance(response, dict) and not response.get("success", True):
                print(f"\nAI: {response['message']}")
                continue

            # Handle execution if a tool is requested
            current_response = response

            while current_response.function_calls:

                calls = current_response.function_calls

                for call in calls:

                    print(f"\n[AI Core Triggered Tool]: {call.name}")
                    print(f"[Payload Arguments]: {call.args}")

                    # Call sidecar vector tool
                    tool_result = await mcp_client.call_tool(call.name, arguments=call.args)
                    raw_text_output = tool_result.content[0].text if hasattr(tool_result, "content") else str(tool_result)

                    print("\nTOOL OUTPUT:")
                    print(raw_text_output)    

                    # Parse results cleanly
                    try:
                        parsed_response = json.loads(raw_text_output)

                        if call.name == "semantic_search_doctors":

                            if (
                                parsed_response.get("success")
                                and parsed_response.get("data")
                            ):

                                data = parsed_response["data"]

                                doctors = data["doctors"]

                                update_state(
                                    intent="find_doctor",
                                    symptoms=user_input,
                                    candidate_doctors=doctors
                                )

                                # Auto-select only when exactly one doctor found
                                if len(doctors) == 1:
                                    update_state(
                                        doctor_id=doctors[0]["id"],
                                        doctor_name=doctors[0]["name"]
                                    )

                        if call.name == "get_patient":

                            if parsed_response.get("success"):

                                patient = parsed_response["data"]

                                update_state(
                                    patient_id=patient["id"]
                                )

                        if call.name == "search_patients":

                            if parsed_response.get("success"):

                                patients = parsed_response["data"]

                                # Auto-select when exactly one match exists
                                if len(patients) == 1:

                                    update_state(
                                        patient_id=patients[0]["id"],
                                        patient_name=patients[0]["name"]
                                    )

                        if call.name == "get_available_slots":

                            if parsed_response.get("success"):

                                update_state(
                                    available_slots=parsed_response["data"]["slots"],
                                    appointment_date=parsed_response["data"]["resolved_date_range"]
                                )

                        if call.name == "book_appointment":

                            if parsed_response.get("success"):

                                reset_state()

                        # Format tool response
                        function_response_dict = {"data": parsed_response} if isinstance(parsed_response, list) else parsed_response

                    except Exception:

                        parsed_response = {
                            "success": False,
                            "message": raw_text_output
                        }

                    # Feed execution metrics straight back into active chat loop sequence
                    try:
                        current_response = send_to_gemini(
                            chat,
                            types.Part.from_function_response(
                                name=call.name,
                                response=parsed_response
                            )
                        )

                        if isinstance(current_response, dict):
                            print(f"\nAI: {current_response['message']}")
                            current_response = None
                            break

                    except Exception as e:

                        print(
                            f"\n[Gemini Follow-up Failed]: {e}"
                        )

                        print(
                            "\nAI:",
                            format_tool_response(
                                call.name,
                                parsed_response
                            )
                        )

                        current_response = None
                        break

                if current_response is None:
                    break

                # print("\nDEBUG RESPONSE:")
            if current_response and current_response.text:
                print(f"\nAI: {current_response.text}")

if __name__ == "__main__":
    asyncio.run(run_chatbot())
