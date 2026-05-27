import asyncio
import os
import sys
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

async def main():
    # 1. Connect to your running FastMCP Sidecar on port 8080
    async with Client("http://127.0.0.1:8080/sse") as mcp_client:
        
        # Discover all tools currently exposed by your sidecar server
        available_tools = await mcp_client.list_tools()
        
        # Translate the MCP tools into structures Gemini understands
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

        # 2. Get user input directly from the terminal prompt
        print("-" * 50)
        prompt = input("Ask Gemini about your system or database:\n> ")
        if not prompt.strip():
            print("Empty prompt. Exiting.")
            return

        # 3. Initialize the Google Gen AI Client
        ai_client = genai.Client()
        
        print("\nThinking...")
        # Ask Gemini the question, giving it access to our clean tools
        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=gemini_tools,
                # ADD THIS SYSTEM INSTRUCTION FOR POSTGRESQL LAYER PROTECTION:
                system_instruction=(
                    "You are a database helper. When writing SQL queries for PostgreSQL, "
                    "always wrap mixed-case or CamelCase table names and column names "
                    'in double quotes. For example, write "testApp_book" instead of testApp_book.'
                )
            )
        )
        
        # 4. Handle tool execution loop if Gemini decides it needs data
        if response.function_calls:
            for call in response.function_calls:
                print(f"\n[Gemini triggered tool]: '{call.name}'")
                print(f"[Arguments passed]: {call.args}")
                
                # Run the selected tool through the sidecar server
                tool_result = await mcp_client.call_tool(call.name, arguments=call.args)
                
                # Extract the text results out of the CallToolResult structure
                raw_text_output = ""
                if hasattr(tool_result, "content") and tool_result.content:
                    raw_text_output = tool_result.content[0].text
                else:
                    raw_text_output = str(tool_result)
                    
                print(f"\n[Sidecar Execution Output]:\n{raw_text_output}")
                print("\nFormulating final response...")
                
                # Pass the database results back into Gemini's context history
                final_response = ai_client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[
                        types.Content(role="user", parts=[types.Part.from_text(text=prompt)]),
                        response.candidates[0].content,
                        types.Content(
                            role="user",
                            parts=[
                                types.Part.from_function_response(
                                    name=call.name,
                                    response={"result": raw_text_output}
                                )
                            ]
                        )
                    ]
                )
                print(f"\nAI: {final_response.text}")
                return

        # Default fallback if no database tools were needed to answer the question
        print(f"\nAI: {response.text}")

if __name__ == "__main__":
    if "GEMINI_API_KEY" not in os.environ:
        print("Error: Please set your GEMINI_API_KEY environment variable first.")
        sys.exit(1)
        
    asyncio.run(main())