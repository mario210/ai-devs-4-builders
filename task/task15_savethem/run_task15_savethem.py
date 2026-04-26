import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import json
import re
import os
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, TypedDict
from ai.agent import Agent
from ai.memory import SharedMemory
from ai.tools.hub_requests import post_json_request, verify_answer
from ai.agent import AGENTS_API_KEY
from urllib.parse import urljoin
from langgraph.graph import StateGraph, END

# Load environment variables
load_dotenv()

# --- Configuration ---
SUPERVISOR_MODEL = "google/gemini-3.1-pro-preview"
SUB_AGENT_MODEL = "openai/gpt-5.4"
BASE_URL = os.environ.get("HUB_API_BASE_URL")
TASK_NAME = "savethem"
MAX_RETRIES = 3
MAX_EXPLORATION_STEPS = 5
MAX_EXPLORATION_WORKERS = 4  # For parallel tool exploration


# --- Low-Level Tool Functions ---
def use_tool(tool_url: str, query: str):
    """The basic function that interacts with a tool's URL."""
    full_url = urljoin(BASE_URL, tool_url)
    print(f"  [Explorer] Probing tool at {full_url} with query: '{query}'")
    payload = {"apikey": AGENTS_API_KEY, "query": query}
    return post_json_request(payload, full_url)


# --- Sub-Agent Definitions ---
def get_next_query(tool: dict, history: list, model: str = SUB_AGENT_MODEL):
    """Spawns a sub-agent to decide the next query for a tool, based on history."""
    agent_name = f"Navigator ({tool.get('name', 'UnknownTool')})"
    print(f"\n--- Spawning {agent_name} Sub-Agent to decide next query ---")

    prompt = f"""
    You are a specialized navigation agent. Your mission is to decide the next best query to explore a tool.

    **Your Target Tool:**
    ```json
    {json.dumps(tool, indent=2)}
    ```

    **Exploration History (Query & Result):**
    ```json
    {json.dumps(history, indent=2)}
    ```

    **Your Plan:**
    1.  Analyze the history.
    2.  If the history is empty, start with a broad query. If the tool is for maps, query for "Skolwin". Otherwise, use "list" or "help".
    3.  If the previous results gave you a list, formulate a query for the details of the first undiscovered item.
    4.  If you believe all information has been gathered, respond with the single word "DONE".
    5.  Otherwise, return a short, specific query to continue the exploration.
    6.  Return ONLY the new query as a string, or "DONE".
    """

    sub_agent = Agent(default_model=model)
    messages = [{"role": "user", "content": prompt}]
    next_query = sub_agent.chat(messages)
    return next_query.strip() if next_query else "DONE"


def extract_json_from_response(response_str: str) -> (str, str):
    """Extracts the last JSON array from a string, separating it from preceding text."""
    # Regex to find a JSON array. This is more robust than the original.
    # It looks for ```json ... ``` or a naked array `[...]`.
    # It will find the LAST one in the string.
    json_pattern = re.compile(r"```json\s*([\s\S]*?)\s*```|(\[[\s\S]*\])")
    matches = list(json_pattern.finditer(response_str))

    if not matches:
        return response_str.strip(), ""

    last_match = matches[-1]
    json_str = last_match.group(1) or last_match.group(2)
    json_str = json_str.strip()

    reasoning = response_str[: last_match.start()].strip()
    return reasoning, json_str


# --- LangGraph Implementation ---


class AgentState(TypedDict):
    """Defines the state of our graph."""

    memory: SharedMemory
    messages: List[Dict[str, Any]]
    retries_left: int


def _explore_tool(tool: dict, memory: SharedMemory, navigator_model: str):
    """Orchestrates the deep-dive exploration of a single tool (standalone function)."""
    tool_name = tool.get("name", "UnknownTool")
    print(f"\n--- Beginning Exploration of Tool: {tool_name} ---")
    exploration_history = []
    consolidated_data = {}

    for i in range(MAX_EXPLORATION_STEPS):
        print(f"  [Explorer] Step {i+1}/{MAX_EXPLORATION_STEPS} for {tool_name}")
        next_query = get_next_query(tool, exploration_history, model=navigator_model)

        if next_query == "DONE":
            print(f"--- Exploration of {tool_name} complete (Agent decided). ---")
            break

        result = use_tool(tool["url"], next_query)
        exploration_history.append({"query": next_query, "result": result})

        if isinstance(result, dict):
            for key, value in result.items():
                if key not in consolidated_data:
                    consolidated_data[key] = value
                elif isinstance(consolidated_data.get(key), list) and isinstance(
                    value, list
                ):
                    consolidated_data[key].extend(
                        v for v in value if v not in consolidated_data[key]
                    )

    memory_key = f"data_from_{tool.get('name', 'unknown_tool')}"
    memory.set(memory_key, consolidated_data)
    print(f"--- Stored data for {tool_name} in memory key: {memory_key} ---")


# --- Graph Nodes ---


def discovery_and_exploration_node(state: AgentState) -> Dict[str, Any]:
    """
    First node in the graph: Discovers tools and explores them in parallel,
    populating the shared memory.
    """
    print("\n--- Phase 1: Tool Discovery & Exploration ---")
    memory = state["memory"]
    tools_info = post_json_request(
        {
            "apikey": AGENTS_API_KEY,
            "query": "I need notes about movement rules and terrain and vehicles.",
        },
        urljoin(BASE_URL, "/api/toolsearch"),
    )

    available_tools = []
    if tools_info and "tools" in tools_info:
        for tool in tools_info["tools"]:
            tool["url"] = urljoin(BASE_URL, tool["url"])
            available_tools.append(tool)

    if not available_tools:
        print("  [Error] Could not discover any tools. Aborting.")
        return {"memory": memory}

    print(
        f"--- Discovered {len(available_tools)} tools. Beginning parallel exploration. ---"
    )
    with ThreadPoolExecutor(max_workers=MAX_EXPLORATION_WORKERS) as executor:
        # We pass the memory object to each worker
        futures = [
            executor.submit(_explore_tool, tool, memory, SUB_AGENT_MODEL)
            for tool in available_tools
        ]
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as exc:
                print(
                    f"  [Error] A tool exploration worker generated an exception: {exc}"
                )

    # Prepare the initial prompt for the supervisor
    supervisor_prompt = f"""
    You are the Supervisor. Your goal is to find the optimal route to Skolwin.
    Your sub-agents have explored the environment and populated your memory with their findings.

    **Current Memory State:**
    ```json
    {json.dumps(memory.get_all(), indent=2)}
    ```

    **Core Rules for Pathfinding:**
    - You start with 10 provisions and 10 fuel.
    - Every move consumes provisions. Every move in a vehicle also consumes fuel. Walking consumes no fuel.
    - You can switch from a vehicle to walking at any point. To do this, add the string "dismount" to your path.
    - If fuel or food reach zero, the mission will fail.

    **Your Plan:**
    1.  **Analyze Data:** Review all information in your memory, paying close attention to the Core Rules.
    2.  **Explain and Calculate Path:** First, display the 10x10 map grid. Then, explain your step-by-step pathfinding logic. Finally, provide the JSON array.

    **Absolute Final Answer Rules:**
    - The final answer MUST be a JSON array (a list).
    - The first item MUST be the vehicle name (e.g., "horse", "car", "walk").
    - The following items MUST be the full names of the moves: "right", "left", "up", "down", or "dismount".
    - **DO NOT USE single-letter abbreviations like "R" or "U".**
    - After your reasoning, provide ONLY the final, correctly formatted JSON array, enclosed in ```json ... ```.
    """
    return {
        "memory": memory,
        "messages": [{"role": "user", "content": supervisor_prompt}],
    }


def supervisor_node(state: AgentState, supervisor_agent: Agent) -> Dict[str, Any]:
    """
    The main analysis node. It runs the supervisor, verifies the answer,
    and prepares feedback if the answer is wrong.
    """
    print(
        f"\n--- Supervisor Attempt {MAX_RETRIES - state['retries_left'] + 1}/{MAX_RETRIES} ---"
    )
    messages = state["messages"]
    response_str = supervisor_agent.chat(messages)

    if not response_str:
        feedback = "You did not provide an answer. Try again."
        messages.append({"role": "user", "content": feedback})
        return {"messages": messages, "retries_left": state["retries_left"] - 1}

    reasoning, final_answer_str = extract_json_from_response(response_str)
    print(
        "\n--- Supervisor's Reasoning ---\n"
        + reasoning
        + "\n----------------------------"
    )

    if not final_answer_str:
        feedback = "Your reasoning was good, but you did not provide the final JSON array in the required ```json ... ``` format. Please provide it now."
        messages.append({"role": "user", "content": feedback})
        return {"messages": messages, "retries_left": state["retries_left"] - 1}

    try:
        final_answer = json.loads(final_answer_str)
        if not isinstance(final_answer, list):
            raise TypeError("Final answer is not a list.")

        verification = verify_answer(TASK_NAME, final_answer)
        if verification and verification.get("code") == 0:
            print("\n--- Verification SUCCESSFUL! ---")
            print(f"Final Answer: {json.dumps(final_answer)}")
            # Signal success to the conditional edge by clearing the messages.
            return {"messages": []}
        else:
            error = verification.get("message", "Unknown error.")
            feedback = f"Your last path was incorrect. The server responded with: '{error}'. Re-analyze the data and provide a new, corrected path."
            messages.append({"role": "user", "content": feedback})

    except (json.JSONDecodeError, TypeError, IndexError) as e:
        feedback = f"Your last response was not valid or malformed. Error: {e}. Fix it."
        messages.append({"role": "user", "content": feedback})

    return {"messages": messages, "retries_left": state["retries_left"] - 1}


def should_continue_supervising(state: AgentState) -> str:
    """Conditional edge to decide whether to loop or end."""
    # The supervisor_node will stop returning updates if successful
    if not state["messages"] or state["retries_left"] <= 0:
        if state["retries_left"] <= 0:
            print(f"\n--- Max retries reached. Task failed. ---")
        return "end"
    return "continue"


if __name__ == "__main__":
    print("\n--- Running Task 15: Save Them (LangGraph Mode) ---")

    # Define the agent that will be used in the supervisor node
    supervisor_agent = Agent(default_model=SUPERVISOR_MODEL)

    # Define the state machine
    workflow = StateGraph(AgentState)

    # Define the nodes
    workflow.add_node("discover_and_explore", discovery_and_exploration_node)
    workflow.add_node(
        "supervisor", lambda state: supervisor_node(state, supervisor_agent)
    )

    # Build the graph
    workflow.set_entry_point("discover_and_explore")
    workflow.add_edge("discover_and_explore", "supervisor")
    workflow.add_conditional_edges(
        "supervisor",
        should_continue_supervising,
        {
            "continue": "supervisor",
            "end": END,
        },
    )

    # Compile the graph
    app = workflow.compile()

    # Run the graph
    initial_state = {
        "memory": SharedMemory(),
        "messages": [],
        "retries_left": MAX_RETRIES,
    }
    app.invoke(initial_state)

    supervisor_agent.print_usage_statistics()
