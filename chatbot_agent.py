import asyncio
import os
from google import genai
from google.genai import types
from fastmcp import Client 

def sanitize_schema(schema: dict) -> dict:
    if not isinstance(schema, dict):
        return schema
    bad_keys = ["additional_properties", "additionalProperties", "$schema"]
    cleaned = {k: sanitize_schema(v) for k, v in schema.items() if k not in bad_keys}
    if "properties" in cleaned and cleaned["properties"] == {}:
        cleaned.pop("properties")
    return cleaned

async def main():
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

        ai_client = genai.Client()
        prompt = "How many users are currently registered in our database?"
        print(f"User: {prompt}")

        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(tools=gemini_tools)
        )
        
        if response.function_calls:
            for call in response.function_calls:
                print(f"\n[Gemini triggered tool]: '{call.name}' with args: {call.args}")
                
                # 1. Execute the tool via your FastMCP sidecar server
                tool_result = await mcp_client.call_tool(call.name, arguments=call.args)
                
                # FastMCP wraps the response text in a CallToolResult object. Let's pull out the raw text string.
                raw_text_output = ""
                if hasattr(tool_result, "content") and tool_result.content:
                    raw_text_output = tool_result.content[0].text
                else:
                    raw_text_output = str(tool_result)
                    
                print(f"[Sidecar Text Output]: {raw_text_output}")
                
                # 2. Package the execution payload cleanly using the official SDK types
                final_response = ai_client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[
                        # Keep history: original user prompt
                        types.Content(role="user", parts=[types.Part.from_text(text=prompt)]),
                        # Keep history: model's original tool call intent response
                        response.candidates[0].content,
                        # Send execution data back in a user/function response container block
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

        print(f"\nAI: {response.text}")

if __name__ == "__main__":
    if "GEMINI_API_KEY" not in os.environ:
        print("Error: Please set your GEMINI_API_KEY environment variable first.")
    else:
        asyncio.run(main())
        
        
