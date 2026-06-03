# 🏥 Django-AI-Medical-Appointment-Assistant Wiki

Welcome to the comprehensive documentation for the **Django-AI-Medical-Appointment-Assistant** project!

This wiki covers everything you need to understand, set up, and extend this intelligent medical appointment booking system.

---

## 📚 Wiki Navigation

### Getting Started
- **[Quick Start Guide](Quick-Start-Guide)** - Set up the project in minutes
- **[Architecture Overview](Architecture-Overview)** - Understanding the system design
- **[Technology Stack](Technology-Stack)** - Tools and frameworks used

### Core Concepts
- **[Model Context Protocol (MCP)](Model-Context-Protocol)** - Understanding MCP and FastMCP
- **[Agentic AI Workflow](Agentic-AI-Workflow)** - How the AI agent works
- **[Semantic Search](Semantic-Search)** - Vector-based doctor discovery
- **[Memory System](Memory-System)** - Long-term conversation memory

### Development
- **[API Documentation](API-Documentation)** - MCP tools and endpoints
- **[Database Schema](Database-Schema)** - Understanding the data models
- **[Configuration Guide](Configuration-Guide)** - Environment setup and settings
- **[Development Guide](Development-Guide)** - Tips for extending the project

### Features & Examples
- **[Conversation Flows](Conversation-Flows)** - Example user interactions
- **[Use Cases](Use-Cases)** - Real-world scenarios
- **[Troubleshooting](Troubleshooting)** - Common issues and solutions

### Advanced Topics
- **[Sidecar Architecture](Sidecar-Architecture)** - Design pattern explanation
- **[Vector Embeddings](Vector-Embeddings)** - How semantic search works
- **[ChromaDB Integration](ChromaDB-Integration)** - Vector database usage
- **[Security Considerations](Security-Considerations)** - Safety measures

### Contributing & Resources
- **[Contributing Guide](Contributing-Guide)** - How to contribute
- **[Future Roadmap](Future-Roadmap)** - Planned features
- **[FAQ](FAQ)** - Frequently asked questions

---

## 🚀 Quick Overview

The **Django-AI-Medical-Appointment-Assistant** is an intelligent healthcare application that combines:

- **Django Backend** - Traditional business logic and data management
- **FastMCP Sidecar** - Tool execution layer for AI operations
- **Google Gemini AI** - Intelligent agent for natural language understanding
- **ChromaDB** - Vector database for semantic search
- **PostgreSQL** - Relational data storage

### Key Features

✅ Natural language medical assistant  
✅ Semantic doctor discovery based on symptoms  
✅ Intelligent appointment booking workflow  
✅ Long-term conversation memory  
✅ MCP-based tool calling architecture  
✅ Safety-first design with validated tool execution  

---

## 💡 Core Use Cases

### 1. **Doctor Discovery**
User: *"I have chest pain"*
Assistant: Identifies cardiology as the relevant specialty and recommends available cardiologists

### 2. **Appointment Booking**
User: *"Book an appointment for tomorrow"*
Assistant: Retrieves available slots and guides user through booking process

### 3. **Patient Management**
Assistant: Searches and validates patient records before any action

### 4. **Memory & Context**
Assistant: Remembers user preferences like favorite doctors and preferred appointment times

---

## 🏗 Project Structure

```
Django-AI-Medical-Appointment-Assistant/
├── testproject/              # Django project settings
├── testApp/                  # Django app with models
├── mcp_server.py            # FastMCP server with tool definitions
├── chatbot_agent.py         # Gemini agent orchestration
├── chatbot_utils.py         # Helper utilities
├── manage.py                # Django management script
├── docker-compose.yaml      # Docker setup
├── requirements.txt         # Python dependencies
└── chroma_db/              # Vector database storage
```

---

## 🎯 What You'll Learn

By exploring this wiki, you'll understand:

1. **Model Context Protocol (MCP)** - A modern approach to AI tool calling
2. **Sidecar Architecture** - How to decouple AI logic from core business logic
3. **Agentic AI** - Multi-step reasoning and planning with LLMs
4. **Semantic Search** - Vector embeddings and similarity matching
5. **Conversation Management** - Stateful AI conversations with context
6. **Safety in AI** - How to keep AI operations under control

---

## 🔧 Getting Started

**New to the project?** Start here:

1. Read the **[Quick Start Guide](Quick-Start-Guide)**
2. Understand the **[Architecture Overview](Architecture-Overview)**
3. Explore **[Conversation Flows](Conversation-Flows)** to see it in action
4. Check **[API Documentation](API-Documentation)** for available tools

---

## 📖 Documentation Standards

- 📝 Code examples are provided in Python
- 🔗 All concepts link to related topics
- 💾 Database examples use PostgreSQL syntax
- 🚀 Setup instructions are platform-specific

---

## ❓ Need Help?

- **Setup Issues?** → Check **[Troubleshooting](Troubleshooting)**
- **Want to Extend?** → See **[Development Guide](Development-Guide)**
- **Common Questions?** → Visit **[FAQ](FAQ)**
- **Not Sure Where to Start?** → Read **[Quick Start Guide](Quick-Start-Guide)**

---

## 🤝 Contributing

Contributions are welcome! Please refer to the **[Contributing Guide](Contributing-Guide)** before submitting changes.

---

## 📜 License & Attribution

This project was created to explore and demonstrate:
- Model Context Protocol (MCP)
- Agentic AI workflows
- Semantic search with vector embeddings
- Sidecar architecture patterns

For more information, see the project README.

---

**Last Updated:** June 2026  
**Maintained by:** Nipunlal2000
