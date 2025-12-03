import os
import sys
from app.watchdog.client import MockUltraciteClient
from app.watchdog.core import WatchdogEngine

def main():
    # Base dir is /app (parent of app package)
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
    
    print(f"Starting Ultracite Watchdog...")
    print(f"Base Directory: {base_dir}")
    
    # Use Mock client for now
    client = MockUltraciteClient()
    engine = WatchdogEngine(client, base_dir)
    
    try:
        report_path = engine.run()
        print(f"SUCCESS: Report generated at {report_path}")
    except Exception as e:
        print(f"ERROR: Watchdog failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
