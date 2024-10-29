import threading
from server import app
from client import StatusClient, RetryConfig

def test_status_flow():
    server_thread = threading.Thread(target=app.run, kwargs={"port": 5000, "use_reloader": False})
    server_thread.setDaemon(True)
    server_thread.start()    

    # Initialize client with custom configuration
    client = StatusClient(
        base_url="http://127.0.0.1:5000",
        retry_config=RetryConfig(
            initial_delay=0.5,
            max_delay=5.0,
            max_retries=20
        ),
        status_callback=lambda resp: print(f"Status update: {resp.status.value}")
    )

    # Test immediate status check
    status = client.get_status()
    assert status.status.value == "pending"

    # Test waiting for completion
    final_status = client.wait_for_completion(timeout=10)
    assert final_status.status.value == "completed"