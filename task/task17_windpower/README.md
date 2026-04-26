# Task 17: Wind Power Management System

This project implements an AI-driven system to manage a wind turbine. It uses a series of specialized "agents" to gather information, make decisions, and apply configurations to optimize wind power generation while ensuring safety.

## 🏗️ Architecture: How It's Built

The system is designed around an **Agent Orchestrator** which acts like a project manager, coordinating various **Agents** (specialized workers). These agents communicate and share information through a central **Memory** system. All interactions with the outside world (like getting weather data or sending commands to the wind turbine) happen through a `verify_answer` tool that talks to an external service.

Here's a simple breakdown:

1.  **`AgentOrchestrator`**: The boss. It decides which agent runs when and makes sure everything happens in the right order.
2.  **`Agent` (Base Class)**: The blueprint for all our specialized workers.
3.  **`Memory`**: The shared whiteboard where all agents write down important information for others to read.
4.  **`verify_answer` Tool**: Our communication channel to the "outside world" (the AI Devs platform in this case). It sends requests and receives responses.

## 🚀 How It Works (For Everyone!)

Imagine you're managing a wind turbine, and you have a team of smart assistants (our agents) to help you.

### The Workflow Step-by-Step:

1.  **Start the Mission!** (`run_task17_windpower.py`):
    *   The whole process kicks off. We tell the main system, "Hey, we're starting the 'windpower' task!"
    *   We set up our shared whiteboard (`memory`) with some initial notes, like the task name and what kind of information we expect to get back later.

2.  **Read the Manual** (`DocumentationAgent`):
    *   Our first assistant goes and reads the wind turbine's instruction manual (documentation).
    *   It learns crucial things like:
        *   How much power the turbine can generate (rated power).
        *   How much power it makes at different wind speeds (wind yield table).
        *   What are the safe wind speeds for it to operate (safety rules, like `minOperationalWindMs` and `cutoffWindMs`).
    *   It writes all this important info on the shared whiteboard.

### Synchronous vs. Asynchronous Information Retrieval

It's important to understand how our assistants get their information. Some requests are **asynchronous**, meaning an assistant asks for something and then immediately moves on, expecting the result to arrive later. Other parts of the system then **synchronously** wait for these results.

*   **Asynchronous Request Initiation**: When agents like `WeatherAgent`, `PowerPlantAgent`, `TurbineAgent`, and `ConfigGeneratorAgent` (when it needs "unlock codes") need data from the external service, they don't wait for an immediate response. They simply send a request (e.g., "get weather forecast") and then continue with their next task. The `verify_answer` tool in these cases confirms the request was sent, but the actual data isn't returned right away. The system keeps track of how many results of each type are expected.

*   **Synchronous Polling**: This is where the `ResultsPollingAgent` comes in. It's the dedicated "fetcher" for all these asynchronously initiated results.

### The Role of `ResultsPollingAgent`

The `ResultsPollingAgent` is a crucial assistant with several key responsibilities:

1.  **Continuous Monitoring**: It constantly checks the external service's "inbox" for any completed results from the requests made by other agents.
2.  **Result Categorization**: When a result arrives, it identifies what kind of information it is (e.g., weather forecast, power plant status, turbine status, or an unlock code) based on its `sourceFunction`.
3.  **Data Storage**: It takes the received data and stores it in the shared `Memory` (our whiteboard), making it available for other agents that need it.
4.  **Tracking Completion**: It keeps a count of how many results are still expected. As each result arrives, it updates this count. It knows its job is done when all expected results have been received.
5.  **Timeout Handling**: To prevent the system from waiting forever, it has a built-in timer. If results don't arrive within a certain period, it raises an alarm (`TimeoutError`).
6.  **Decoupling**: It allows other agents to initiate requests without having to stop and wait for the response, making the overall system more efficient and responsive.

3.  **Check the Weather** (`WeatherAgent`):
    *   Another assistant calls the weather station to get the latest wind forecast.
    *   It doesn't wait for the answer; it just places the order.

4.  **Check the Power Plant's Needs** (`PowerPlantAgent`):
    *   This assistant checks with the main power plant to see how much electricity it needs (its "deficit").
    *   Again, it just places the order and doesn't wait.

5.  **Check the Turbine's Health** (`TurbineAgent`):
    *   This assistant quickly checks the current status of our wind turbine. Is it running? Is it okay?
    *   It places the order and moves on.

6.  **Wait for Information (First Time)** (`ResultsPollingAgent`):
    *   Now, a patient assistant sits by the "inbox" and waits for all the information we just ordered: the weather forecast, the power plant status, and the turbine's health report.
    *   It keeps checking every now and then until everything arrives. If it takes too long, it raises an alarm! (See "The Role of `ResultsPollingAgent`" above for more details).
    *   Once received, it writes these details on the shared whiteboard.

7.  **Make a Plan!** (`ConfigGeneratorAgent`):
    *   This is the "brain" of our operation. It looks at:
        *   The weather forecast (from the whiteboard).
        *   The power plant's needs (from the whiteboard).
        *   The turbine's manual (from the whiteboard).
    *   It decides, for each hour in the forecast, what the turbine should do:
        *   Should it be running to make power ("production")?
        *   Should it be stopped for safety ("idle") because the wind is too strong?
        *   What angle should its blades be at (pitch angle)?
    *   For each decision, it asks for a special "unlock code" from the external system. It places these orders and writes down its planned configurations (without the codes yet) on the whiteboard.

8.  **Wait for Unlock Codes (Second Time)** (`ResultsPollingAgent`):
    *   Our patient assistant is back! This time, it waits specifically for all the "unlock codes" we requested for our planned turbine settings.
    *   It adds these codes to the shared whiteboard. (Again, refer to "The Role of `ResultsPollingAgent`" for how this polling works).

9.  **Apply the Plan!** (`ConfigApplierAgent`):
    *   This assistant takes the planned turbine settings and their matching "unlock codes" from the whiteboard.
    *   It combines them and sends the final commands to the external system to actually configure the wind turbine.

10. **Final Check & Done!** (`FinalValidationAgent`):
    *   Our last assistant does a quick check to make sure the turbine is now operating correctly after applying the new settings.
    *   If everything looks good, it tells the external system, "Mission accomplished!"

This whole process ensures the wind turbine operates efficiently and safely, adapting to changing weather conditions and power demands.
```