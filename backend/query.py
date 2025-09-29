import asyncio
import json
from typing import Dict, List, AsyncGenerator
import httpx
from utils import *

# global variable to store cancellation status
cancelled_tasks = set()

class QueryProcessor:
    def __init__(self):
        self.cancelled_tasks = set()
        # store task IDs for active queries
        self.active_tasks = {}
    
    def cancel_task(self, task_id):
        """Cancel a specific task"""
        self.cancelled_tasks.add(task_id)
    
    def is_cancelled(self, task_id):
        """Check if a task is cancelled"""
        return task_id in self.cancelled_tasks
    
    def remove_cancelled_task(self, task_id):
        """Remove a task from the cancelled set"""
        if task_id in self.cancelled_tasks:
            self.cancelled_tasks.remove(task_id)
    
    def register_task(self, user_id, task_id):
        """Register a task for a specific user"""
        self.active_tasks[user_id] = task_id
    
    def get_task_for_user(self, user_id):
        """Get the active task ID for a user"""
        return self.active_tasks.get(user_id)
    
    def unregister_task(self, user_id):
        """Unregister a task for a user"""
        if user_id in self.active_tasks:
            del self.active_tasks[user_id]

# global query processor instance
query_processor = QueryProcessor()

async def process_query(query: str, llm_credentials: Dict, user_id: str = "default_user") -> AsyncGenerator[str, None]:
    """
    Process a query through the entire pipeline:
    1. Get top Reddit URLs
    2. Extract content chunks
    3. Get top chunks by similarity
    4. Generate response with LLM
    """
    task_id = id(asyncio.current_task())
    
    # task registration with query processor
    query_processor.register_task(user_id, task_id)
    
    try:
        if query_processor.is_cancelled(task_id):
            yield f"data: {json.dumps({'status': 'cancelled', 'message': 'Task was cancelled'})}\n\n"
            yield "data: [DONE]\n\n"
            return

        # step 1: get top reddit urls
        yield f"data: {json.dumps({'status': 'info', 'message': 'Finding relevant Reddit discussions...'})}\n\n"
        urls = await get_top_reddit_urls(query)
        
        if query_processor.is_cancelled(task_id):
            yield f"data: {json.dumps({'status': 'cancelled', 'message': 'Task was cancelled'})}\n\n"
            yield "data: [DONE]\n\n"
            return

        # step 2: extract content chunks
        yield f"data: {json.dumps({'status': 'info', 'message': 'Extracting content from Reddit posts...'})}\n\n"
        all_chunks = []
        count = 0
        number_of_urls = 10
        for url in urls:
            if count >= number_of_urls:
                break

            if query_processor.is_cancelled(task_id):
                yield f"data: {json.dumps({'status': 'cancelled', 'message': 'Task was cancelled'})}\n\n"
                yield "data: [DONE]\n\n"
                return 
                
            chunks = await asyncio.to_thread(extract_post_and_comments, url)
            all_chunks.extend(chunks)
            count += 1
            await asyncio.sleep(0.1)
        
        if query_processor.is_cancelled(task_id):
            yield f"data: {json.dumps({'status': 'cancelled', 'message': 'Task was cancelled'})}\n\n"
            yield "data: [DONE]\n\n"
            return

        # step 3: get top chunks by similarity
        yield f"data: {json.dumps({'status': 'info', 'message': 'Analyzing and selecting most relevant content...'})}\n\n"
        selected_chunks = await asyncio.to_thread(get_top_chunks_by_token_limit, query, all_chunks)
        
        if query_processor.is_cancelled(task_id):
            yield f"data: {json.dumps({'status': 'cancelled', 'message': 'Task was cancelled'})}\n\n"
            yield "data: [DONE]\n\n"
            return
        
        # llm response stream
        async for chunk in generate_llm_response(query, selected_chunks, llm_credentials, task_id):
            if query_processor.is_cancelled(task_id):
                yield f"data: {json.dumps({'status': 'cancelled', 'message': 'Task was cancelled'})}\n\n"
                yield "data: [DONE]\n\n"
                return
            yield chunk
            
    except Exception as e:
        yield f"data: {json.dumps({'status': 'error', 'message': f'An error occurred: {str(e)}'})}\n\n"
    finally:
        yield "data: [DONE]\n\n"

        # clean up task id if it exists
        query_processor.remove_cancelled_task(task_id)

        # unregister the task
        query_processor.unregister_task(user_id)


async def generate_llm_response(query: str, chunks: List[str], credentials: Dict, task_id: int) -> AsyncGenerator[str, None]:
    """
    Generate a response using the LLM with the provided chunks as context.
    """
    context = "\n\n".join(chunks)
    contextual_info = gather_contextual_info()

    prompt = f"""
{contextual_info}
Context information is below.
---------------------
{context}
---------------------
Query: "{query}"

Answer:
"""

    system_prompt = """
You are a "Reddit Opinion" bot.

Instructions:
1. Use the context information to answer the query without mentioning the context.
2. Apply inline citations using the format [Source: URL] at the end of relevant sentences.

   Example:
   - "The Nintendo Switch has sold over 125 million units globally. [Source: https://www.nintendo.com/financials/]"
   - "Studies show that people who sleep less than 6 hours a night are more prone to heart disease. [Source: https://www.ncbi.nlm.nih.gov/pmc/articles/PMC2656292/]"

3. Be detailed, and apply a lot of markdown formatting for better readability.
"""

    api_key = credentials.get("api_key")
    base_url = credentials.get("base_url", "https://api.openai.com/v1")
    model = credentials.get("model", "gpt-3.5-turbo")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    input_tokens = len(tokenizer.encode(prompt, add_special_tokens=False))
    output_tokens = 0

    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "stream": True
    }

    async with httpx.AsyncClient() as client:
        try:
            async with client.stream("POST", f"{base_url}/chat/completions", headers=headers, json=data) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    yield f"data: {json.dumps({'status': 'error', 'message': f'LLM API error: {response.status_code} - {error_text.decode()}'})}\n\n"
                    return

                async for chunk in response.aiter_text():
                    if query_processor.is_cancelled(task_id):
                        yield f"data: {json.dumps({'status': 'cancelled', 'message': 'Task was cancelled'})}\n\n"
                        return

                    if chunk.startswith("data: "):
                        if chunk.strip() == "data: [DONE]":
                            return  # Cleanup will happen in `finally`

                        json_str = chunk[6:]
                        try:
                            stream_data = json.loads(json_str)
                            if "choices" in stream_data and len(stream_data["choices"]) > 0:
                                choice = stream_data["choices"][0]
                                if "delta" in choice and "content" in choice["delta"]:
                                    content = choice["delta"]["content"]
                                    if content:
                                        output_tokens += len(tokenizer.encode(content, add_special_tokens=False))
                                        yield f"data: {json.dumps({'status': 'stream', 'content': content})}\n\n"
                        except json.JSONDecodeError:
                            continue  # Ignore bad chunks

                    await asyncio.sleep(0.05)

        except Exception as e:
            yield f"data: {json.dumps({'status': 'error', 'message': f'Error connecting to LLM API: {str(e)}'})}\n\n"

        finally:
            yield f"data: {json.dumps({'status': 'token_usage', 'input_tokens': input_tokens, 'output_tokens': output_tokens})}\n\n"
            yield "data: [DONE]\n\n"

def cancel_task(user_id: str = "default_user"):
    """
    Cancel the current task for a specific user
    """
    try:
        task_id = query_processor.get_task_for_user(user_id)
        if task_id:
            query_processor.cancel_task(task_id)
            return {"status": "success", "message": "Task cancellation requested"}
        else:
            return {"status": "error", "message": "No active task found for user"}
    except Exception as e:
        return {"status": "error", "message": f"Error cancelling task: {str(e)}"}

cancelled_tasks = query_processor.cancelled_tasks
