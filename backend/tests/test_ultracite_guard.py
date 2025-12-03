import os
import pytest
from app.watchdog.client import MockUltraciteClient
from app.watchdog.core import WatchdogEngine

@pytest.mark.ultracite
def test_watchdog_engine_run(tmp_path):
    # Setup mock client
    client = MockUltraciteClient()
    
    # Setup temporary directory structure
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    watchdog_dir = app_dir / "watchdog"
    watchdog_dir.mkdir()
    
    # Create dummy queries.yaml
    queries_yaml = watchdog_dir / "queries.yaml"
    queries_yaml.write_text("""
queries:
  - id: "test-query"
    title: "Test Query"
    description: "Description for test query"
    """)
    
    # Create docs structure relative to base_dir (which is tmp_path/backend)
    # In core.py: 
    # queries_path = base_dir/app/watchdog/queries.yaml
    # snapshots_dir = base_dir/../docs/regulations/snapshots
    # reports_dir = base_dir/../docs/regulations/reports
    
    # So we treat tmp_path as the 'backend' directory
    docs_dir = tmp_path.parent / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    
    # Instantiate engine with tmp_path as base_dir
    engine = WatchdogEngine(client, str(tmp_path))
    
    # Run 1: Initial run (creates snapshot)
    report_path_1 = engine.run()
    assert os.path.exists(report_path_1)
    
    # Verify snapshot created
    snapshot_path = engine.snapshots_dir + "/test-query.txt"
    assert os.path.exists(snapshot_path)
    with open(snapshot_path, 'r') as f:
        content = f.read()
        assert "Mock result" in content

    # Run 2: No change
    report_path_2 = engine.run()
    with open(report_path_2, 'r') as f:
        report_content = f.read()
        assert "No Change: Test Query" in report_content

    # Run 3: Change detected (simulate by modifying client behavior or snapshot)
    # Let's modify the snapshot to force a diff
    with open(snapshot_path, 'w') as f:
        f.write("Old content")
        
    report_path_3 = engine.run()
    with open(report_path_3, 'r') as f:
        report_content = f.read()
        assert "CHANGE DETECTED: Test Query" in report_content
        assert "Old content" in report_content

