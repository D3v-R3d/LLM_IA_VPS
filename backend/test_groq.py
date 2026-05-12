import json
import asyncio
from app.services.agent_tools.registry import get_tool_definitions
from app.providers.llm.groq_provider import GroqProvider

async def test():
    provider = GroqProvider()
    tools = get_tool_definitions()
    
    # Simulate context after tool execution (4 iterations of back and forth)
    msgs = [
        {'role': 'system', 'content': 'You are a helpful assistant with access to various tools.'},
        {'role': 'user', 'content': 'Cree un meme qui montre un chat qui code'},
        {'role': 'assistant', 'content': '', 'tool_calls': [{'id': 'call_1', 'type': 'function', 'function': {'name': 'web_search', 'arguments': '{"query": "chat programmer meme"}'}}]},
        {'role': 'tool', 'content': 'Search results: cat programmer memes...', 'tool_call_id': 'call_1'},
        {'role': 'assistant', 'content': "Voici le meme que j'ai cree..."},
    ]
    
    payload = {
        'model': 'llama-3.1-8b-instant',
        'messages': msgs,
        'tools': tools,
        'stream': False,
    }
    
    payload_str = json.dumps(payload)
    print(f"Payload after tool iteration: {len(payload_str)} bytes ({len(payload_str)/1024:.1f} KB)")
    
    # Try with longer context (20 messages)
    long_msgs = [{'role': 'system', 'content': 'You are a helpful assistant.'}]
    for i in range(20):
        long_msgs.append({'role': 'user', 'content': f'Message {i} with some content here'})
        long_msgs.append({'role': 'assistant', 'content': f'Response {i} with some assistant content here'})
    
    payload2 = {
        'model': 'llama-3.1-8b-instant',
        'messages': long_msgs,
        'tools': tools,
        'stream': False,
    }
    
    payload_str2 = json.dumps(payload2)
    print(f"Payload with 20 exchanges: {len(payload_str2)} bytes ({len(payload_str2)/1024:.1f} KB)")
    
    # Try actual API call with longer context
    try:
        result = await provider.chat_with_tools('llama-3.1-8b-instant', long_msgs, tools)
        print("OK with long context")
    except Exception as e:
        print(f"Error with long context: {e}")

asyncio.run(test())
