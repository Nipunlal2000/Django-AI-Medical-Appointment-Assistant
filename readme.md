# 🏥 AI-Powered Medical Appointment Assistant

An intelligent medical appointment booking system built using **Django**, **FastMCP**, **Google Gemini**, **ChromaDB**, and **PostgreSQL**.

This project was created as an exploration into **Agentic AI**, **Model Context Protocol (MCP)**, semantic search, memory systems, and AI-assisted healthcare workflows.

The application combines a traditional Django backend with a dedicated AI sidecar service powered by FastMCP, enabling natural language interactions for doctor discovery, appointment booking, patient lookup, and conversational memory management.

---

# 🚀 Project Overview

Traditional healthcare applications require users to manually search for doctors, browse schedules, and fill multiple forms before booking appointments.

This project introduces an AI assistant capable of understanding natural language requests such as:

> "I have chest pain."

> "Find me a heart specialist."

> "Book an appointment tomorrow."

> "Show available slots for Dr. John."

The assistant can:

* Understand symptoms
* Identify the appropriate medical specialty
* Recommend available doctors
* Search patients
* Retrieve appointment slots
* Book appointments
* Remember useful user preferences

---

# 🧠 Key Concepts Implemented

## 1. Model Context Protocol (MCP)

This was my first implementation using MCP.

The FastMCP server acts as a tool execution layer that exposes business capabilities as AI-callable tools.

Examples:

* semantic_search_doctors
* get_doctors
* search_patients
* get_patient
* get_available_slots
* book_appointment
* save_memory
* recall_memory

Instead of giving the LLM direct database access, all actions are routed through MCP tools, creating a safer and more structured architecture.

---

## 2. Sidecar Architecture

The system follows a Sidecar AI pattern.

```text
+------------------+
| Django Backend   |
| Business Logic   |
+--------+---------+
         |
         |
         v
+------------------+
| PostgreSQL       |
+------------------+

         ^
         |
         |
+------------------+
| FastMCP Sidecar  |
| Tool Layer       |
+--------+---------+
         |
         |
         v
+------------------+
| Gemini Agent     |
+------------------+
```

### Why Sidecar?

Keeping the AI layer separate from Django provides:

* Loose coupling
* Independent scaling
* Easier experimentation
* Cleaner AI integrations
* Safer tool execution

The Django application remains the source of truth while FastMCP acts as the AI orchestration layer.

---

## 3. Agentic AI Workflow

The chatbot operates as an AI agent capable of:

### Reasoning

Understanding user intent from natural language.

Example:

```text
User:
"My heart hurts."
```

The agent determines that:

```text
Intent = Find Doctor
Speciality = Cardiology
```

---

### Tool Selection

The model dynamically decides which MCP tool should be executed.

Example:

```text
semantic_search_doctors()
```

---

### State Management

The chatbot maintains conversation state:

```python
{
    "intent": None,
    "doctor_id": None,
    "doctor_name": None,
    "appointment_date": None,
    "slot_id": None,
    "patient_id": None
}
```

This allows the agent to collect information across multiple user messages before completing a task.

---

### Multi-Step Planning

Example booking flow:

```text
User:
Book an appointment.
```

Agent plan:

1. Identify doctor
2. Identify patient
3. Ask for date
4. Retrieve slots
5. Select slot
6. Book appointment

The agent gathers missing information step-by-step before executing the final booking action.

---

# 🔍 Semantic Doctor Discovery

Instead of relying on exact keyword matching, doctor discovery uses embeddings.

## Workflow

Doctor profiles are converted into vector embeddings using:

```text
Gemini Embedding Model
```

Stored inside:

```text
ChromaDB
```

When a user describes symptoms:

```text
"I have chest pain."
```

The symptom description is embedded and compared against stored doctor vectors.

The most relevant specialty is selected automatically.

---

# 🧠 Long-Term Memory System

The project includes a basic semantic memory implementation.

## Save Memory

Stores important user facts:

* Chronic conditions
* Preferred doctors
* Preferred appointment times

Tool:

```text
save_memory()
```

---

## Recall Memory

Retrieves semantically related memories.

Tool:

```text
recall_memory()
```

Memory retrieval is vector-based rather than keyword-based.

---

# 🏗 Technology Stack

## Backend

* Django
* Django ORM
* PostgreSQL

## AI Layer

* Google Gemini 2.5 Flash
* Gemini Embeddings

## Agent Framework

* FastMCP
* MCP Tools

## Vector Database

* ChromaDB

## Communication

* MCP SSE Transport

---

# 📂 Project Architecture

```text
project/
│
├── Django Backend
│   ├── Models
│   ├── APIs Views
│   ├── Serializers
│   ├── urls
│   └── PostgreSQL
│
├── FastMCP Sidecar
│   ├── Tool Registry
│   ├── Memory Tools
│   ├── Doctor Search Tools
│   ├── Appointment Tools
│   └── ChromaDB Integration
│
├── Gemini Agent
│   ├── Function Calling
│   ├── Planning
│   ├── Tool Selection
│   └── Conversation Management
│
└── ChromaDB
    ├── Doctor Vectors
    ├── Intent Vectors
    └── Memory Vectors
```

---

# ⚙ Available MCP Tools

| Tool                    | Description                          |
| ----------------------- | ------------------------------------ |
| semantic_search_doctors | Find doctors using symptom semantics |
| get_doctors             | Retrieve doctors by filters          |
| search_patients         | Search patient records               |
| get_patient             | Retrieve patient details             |
| get_available_slots     | Fetch appointment availability       |
| book_appointment        | Book appointment                     |
| save_memory             | Store conversation memories          |
| recall_memory           | Retrieve memories                    |

---

# 💡 Example Conversation

### Doctor Discovery

```text
User:
I have chest pain.
```

```text
AI:
I found the following cardiologists available.
Would you like to book an appointment?
```

---

### Slot Retrieval

```text
User:
Tomorrow.
```

```text
AI:
Available slots:

1. 10:00 AM
2. 10:30 AM
3. 11:00 AM
```

---

### Booking

```text
User:
Book the first slot.
```

```text
AI:
Appointment booked successfully.
```

---

# 🔒 Safety Considerations

The AI agent:

* Never generates SQL queries
* Never fabricates IDs
* Relies exclusively on MCP tool outputs
* Validates doctor existence
* Validates patient existence
* Validates slot ownership
* Prevents double booking

This keeps business logic under backend control rather than the LLM.

---

# 📈 Future Improvements

Planned enhancements:

* Appointment cancellation
* Appointment rescheduling
* Multi-patient context management
* Doctor recommendation ranking
* RAG-based medical knowledge assistant
* Authentication-aware memory
* Multi-agent orchestration
* Voice-enabled consultations

---

# 🎯 What I Learned

This project was my first hands-on implementation of:

* Model Context Protocol (MCP)
* Agentic AI workflows
* AI tool calling
* Semantic search
* Vector databases
* Long-term memory systems
* Sidecar architecture patterns

A major takeaway was understanding how LLMs can act as orchestrators while business logic remains securely controlled through MCP tools and backend services.

The result is a practical AI-powered healthcare assistant capable of reasoning, planning, retrieving information, and executing actions through structured tool usage.
