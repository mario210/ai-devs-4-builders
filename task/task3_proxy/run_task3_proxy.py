from task.task3_proxy import proxy_server


# --- Task 3: Proxy (No FastAPI)---
def run_task3_proxy():
    port = 3000
    print("\n--- Running Task 3: Proxy (Logistics Server) ---")
    print(f"Starting server on port {port}. Press Ctrl+C to stop.")
    proxy_server.run_server(port)


if __name__ == "__main__":
    run_task3_proxy()
