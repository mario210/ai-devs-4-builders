import os
import json
import requests
import time
from loguru import logger
from dotenv import load_dotenv
from openai import OpenAI
from typing import List, Dict, Any, Optional, Callable, Union

# Load environment variables from .env file
load_dotenv()

# Centralized Configuration
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
AGENTS_API_KEY = os.environ.get("AGENTS_API_KEY")

class Agent:
    def __init__(self, api_key: str = None, base_url: str = "https://openrouter.ai/api/v1",
                 default_model: str = "openai/gpt-4o-mini", use_cache: bool = False):
        self.api_key = api_key or OPENROUTER_API_KEY
        self.base_url = base_url
        self.default_model = default_model
        self.client = OpenAI(base_url=self.base_url, api_key=self.api_key) if self.api_key else None
        self.use_cache = use_cache
        self.cache = {}
        
        # Statistics
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_cost = 0.0

    def chat(self, messages: List[Union[Dict[str, Any], Any]], tools: Optional[List[Dict]] = None,
             tool_map: Optional[Dict[str, Callable]] = None, response_format: Optional[Dict] = None,
             max_iterations: int = 5, model: str = None) -> Optional[str]:
        """
        Conducts a chat conversation with the LLM, handling tool calls automatically.

        Args:
            messages: The list of message dictionaries or ChatCompletionMessage objects (modified in-place).
            tools: List of tool definitions.
            tool_map: Mapping of tool names to callable functions.
            response_format: Schema for structured output.
            max_iterations: Limit for tool call loops.
            model: Model to use (overrides default).
            use_cache: Flag to enable caching of responses.

        Returns:
            str: The final text content from the assistant.
        """
        if not self.client:
            logger.error("OpenAI client not initialized.")
            return None

        current_model = model or self.default_model
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            # Ensure messages are consistently serialized (dicts) for both caching and the API
            serialized_messages = []

            for msg in messages:
                if isinstance(msg, dict):
                    serialized_messages.append(msg)
                elif isinstance(msg, str):
                    # assume it's a user message
                    serialized_messages.append({"role": "user", "content": msg})
                elif hasattr(msg, "model_dump"):
                    serialized_messages.append(msg.model_dump(exclude_none=True))
                else:
                    raise TypeError(f"Unsupported message type: {type(msg)}")

            completion_args = {
                "model": current_model,
                "messages": serialized_messages,
            }

            if tools:
                completion_args["tools"] = tools
                completion_args["tool_choice"] = "auto"

            if response_format:
                completion_args["response_format"] = response_format

            response = None
            cache_key = None

            # --- Caching Logic: Check cache before API call ---
            if self.use_cache:
                try:
                    key_payload = completion_args.copy()
                    cache_key = json.dumps(key_payload, sort_keys=True)

                    if cache_key in self.cache:
                        logger.debug("--- Agent retrieving response from cache ---")
                        response = self.cache[cache_key]
                except Exception as e:
                    logger.warning(f"Cache key generation/retrieval failed: {e}")

            # --- API Call: Execute if no cached response ---
            if response is None:
                try:
                    logger.debug(f"--- Calling LLM API with agent | model={current_model} ---")
                    
                    response = self.client.chat.completions.create(**completion_args)

                    if self.use_cache and cache_key:
                        logger.debug("--- Agent storing response in cache ---")
                        self.cache[cache_key] = response
                        
                    cost_found = False

                    # Accumulate token usage
                    if hasattr(response, 'usage') and response.usage:
                        self.total_prompt_tokens += response.usage.prompt_tokens
                        self.total_completion_tokens += response.usage.completion_tokens
                        
                        # Try to get cost directly from the immediate response (model_extra)
                        if response.usage.model_extra and 'cost' in response.usage.model_extra:
                            immediate_cost = response.usage.model_extra.get('cost')
                            if immediate_cost is not None and float(immediate_cost) > 0:
                                self.total_cost += float(immediate_cost)
                                cost_found = True
                                logger.debug(f"--- Cost immediately found in model_extra: {immediate_cost} ---")

                    # Fallback: Calculate cost using OpenRouter Generation API if immediate cost was 0 or missing
                    if not cost_found and hasattr(response, 'id') and self.api_key and "openrouter.ai" in self.base_url:
                        try:
                            res = requests.get(
                                f"https://openrouter.ai/api/v1/generation?id={response.id}",
                                headers={"Authorization": f"Bearer {self.api_key}"}
                            )
                            if res.status_code == 200:
                                gen_data = res.json().get('data', {})
                                cost = gen_data.get('total_cost')
                                logger.debug(f"Raw cost extracted from OpenRouter Fallback API: {cost}")
                                if cost is not None:
                                    self.total_cost += float(cost)
                        except Exception as e:
                            logger.warning(f"Could not fetch cost for generation {response.id}: {e}")

                except Exception as e:
                    logger.exception(f"Agent Chat Error during API call in iteration {iteration}")
                    return None

            # --- Process Response ---
            try:
                message = response.choices[0].message
                messages.append(message)

                if message.tool_calls:
                    for tool_call in message.tool_calls:
                        function_name = tool_call.function.name
                        arguments_str = tool_call.function.arguments

                        try:
                            arguments = json.loads(arguments_str)
                        except json.JSONDecodeError:
                            logger.error(f"Error decoding arguments for {function_name}")
                            arguments = {}

                        result_content = ""
                        if tool_map and function_name in tool_map:
                            try:
                                logger.debug(f"--- Agent executing tool: [{function_name}] ---")
                                result = tool_map[function_name](**arguments)
                                if isinstance(result, (dict, list)):
                                    result_content = json.dumps(result, ensure_ascii=False)
                                else:
                                    result_content = str(result)
                            except Exception as e:
                                error_msg = f"Error executing {function_name}: {str(e)}"
                                logger.error(error_msg)
                                result_content = json.dumps({"error": error_msg})
                        else:
                            error_msg = f"Tool '{function_name}' not found in tool_map."
                            logger.warning(error_msg)
                            result_content = json.dumps({"error": error_msg})

                        messages.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": result_content
                        })
                else:
                    return message.content

            except Exception as e:
                logger.exception(f"Agent Chat Error during response processing in iteration {iteration}")
                return None

        logger.warning(f"Max iterations ({max_iterations}) reached.")
        # Fix: Handle both dict and object types for the last message
        if messages:
            last_msg = messages[-1]
            if isinstance(last_msg, dict):
                return last_msg.get('content')
            elif hasattr(last_msg, 'content'):
                return last_msg.content
        return None

    def print_usage_statistics(self):
        time.sleep(2) # be nice and let Agents do the work. This should appear at the very end.
        """Prints the accumulated usage statistics."""
        logger.debug(f"----- Usage Statistics -----")
        logger.debug(f"Total Prompt Tokens: {self.total_prompt_tokens}")
        logger.debug(f"Total Completion Tokens: {self.total_completion_tokens}")
        logger.debug(f"Total Tokens: {self.total_prompt_tokens + self.total_completion_tokens}")
        logger.debug(f"Total Cost: ${self.total_cost:.6f}")
        logger.debug(f"----------------------------")