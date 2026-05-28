import asyncio
import os
import sys
import time
import json
from google import genai
from google.genai import types
from fastmcp import Client 

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

from pydantic import BaseModel, Field
from typing import Literal

# 1. Define the structural blueprint your code demands
class IntentClassification(BaseModel):
    intent: Literal["CHITCHAT", "DATABASE_QUERY"] = Field(
        description="The classified category matching the user input statement."
    )

def route_intent(ai_client: genai.Client, user_prompt: str) -> str:
    """
    LAYER 1: Structured Intent Router
    Guarantees the response conforms strictly to our IntentClassification Pydantic model.
    """
    router_prompt = f'Analyze the following user input and classify its intent: "{user_prompt}"'
    
    response = ai_client.models.generate_content(
        model='gemini-2.5-flash',
        contents=router_prompt,
        config=types.GenerateContentConfig(
            # Force the engine output format into structured validation
            response_mime_type="application/json",
            response_schema=IntentClassification,
            system_instruction=(
                "Classify casual chat, greetings, or meta-questions as CHITCHAT. "
                "Classify any request regarding inspecting, filtering, grouping, or counting "
                "books, prices, authors, or database schemas as DATABASE_QUERY."
            )
        )
    )
    
    # The SDK automatically parses the JSON text back into your Pydantic object!
    try:
        classification: IntentClassification = response.parsed
        return classification.intent
    except Exception:
        # Secure fallback protection line
        return "DATABASE_QUERY"

async def handle_database_intent(ai_client: genai.Client, prompt: str):
    """
    LAYER 2: Specialized Data Pipeline
    Executes deep tool discovery and connects to the FastMCP sidecar server.
    """
    print("[Router Action] ➔ Routing to Asynchronous Data Pipeline...")
    
    async with Client("http://127.0.0.1:8080/sse") as mcp_client:
        available_tools = await mcp_client.list_tools()
        
        gemini_tools = []
        for tool in available_tools:
            schema_dict = tool.inputSchema if hasattr(tool, 'inputSchema') else {}
            if hasattr(schema_dict, 'model_dump'):
                schema_dict = schema_dict.model_dump()
            
            clean_schema = sanitize_schema(schema_dict)
            gemini_tools.append(
                types.Tool(
                    function_declarations=[
                        types.FunctionDeclaration(
                            name=tool.name,
                            description=tool.description,
                            parameters=clean_schema
                        )
                    ]
                )
            )

        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=gemini_tools,
                system_instruction=(
                    "You are a database assistant for a PostgreSQL database managed by Django.\n"
                    "CRITICAL RULES FOR WRITING SQL:\n"
                    "1. The table containing book records is explicitly named \"testApp_book\" (NOT \"books\").\n"
                    "2. The column structures available inside \"testApp_book\" are: \"id\", \"title\", \"author\", \"price\", \"is_published\", \"created_at\", \"updated_at\".\n"
                    "3. Always wrap the mixed-case table name \"testApp_book\" in double quotes so PostgreSQL preserves the capital 'A'.\n"
                    "4. If a query returns data, read the resulting rows carefully to formulate your conversational text reply."
                )
            )
        )
        
        if response.function_calls:
            for call in response.function_calls:
                print(f"[Gemini selected Tool]: '{call.name}'")
                print(f"[Arguments passed]: {call.args}")
                
                # Execute the tool inside our running sidecar
                tool_result = await mcp_client.call_tool(call.name, arguments=call.args)
                
                raw_text_output = ""
                if hasattr(tool_result, "content") and tool_result.content:
                    raw_text_output = tool_result.content[0].text
                else:
                    raw_text_output = str(tool_result)
                    
                print(f"\n[Sidecar Execution Output]:\n{raw_text_output}")
                
                # Convert the sidecar JSON string output back into a true Python dictionary/list
                try:
                    parsed_response = json.loads(raw_text_output)
                    # If it's a list from Postgres (e.g., [{"count": 2}]), wrap it in a root key dictionary
                    if isinstance(parsed_response, list):
                        function_response_dict = {"data": parsed_response}
                    else:
                        function_response_dict = parsed_response
                except Exception:
                    # Fallback plain dictionary mapping if it's not JSON
                    function_response_dict = {"output": raw_text_output}

                # Send execution payload back to Gemini without the 'id' parameter
                final_response = ai_client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[
                        # 1. Maintain user's original query context
                        types.Content(role="user", parts=[types.Part.from_text(text=prompt)]),
                        # 2. Maintain Gemini's tool invocation intent
                        response.candidates[0].content,
                        # 3. Supply the parsed native response data structure
                        types.Content(
                            role="user",
                            parts=[
                                types.Part.from_function_response(
                                    name=call.name,
                                    response=function_response_dict # Clean Python object
                                )
                            ]
                        )
                    ]
                )
                print(f"\nAI: {final_response.text}")
                return

        print(f"\nAI: {response.text}")

def handle_chitchat_intent(ai_client: genai.Client, prompt: str):
    """
    LAYER 2: Lightweight Conversation Pipeline
    Responds directly to the user without calling tools or pinging the sidecar server.
    """
    print("[Router Action] ➔ Routing to Conversation Pipeline (Tools Bypassed)...")
    
    response = ai_client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt
    )
    print(f"\nAI: {response.text}")

async def main():
    print("-" * 50)
    prompt = input("Ask Gemini about your system or database:\n> ")
    if not prompt.strip():
        return

    # Initialize Client once
    ai_client = genai.Client()
    
    # 1. Evaluate user intent using our router logic
    intent = route_intent(ai_client, prompt)
    print(f"[Intent Detected]: {intent}")
    
    # Add a tiny breather for the free-tier API
    time.sleep(1.5)
    
    # 2. Route the execution pipeline based on classification
    if intent == "CHITCHAT":
        handle_chitchat_intent(ai_client, prompt)
    elif intent == "DATABASE_QUERY":
        await handle_database_intent(ai_client, prompt)

if __name__ == "__main__":
    if "GEMINI_API_KEY" not in os.environ:
        print("Error: Please set your GEMINI_API_KEY environment variable first.")
        sys.exit(1)
        
    asyncio.run(main())