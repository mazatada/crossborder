import os
import yaml
import datetime
from typing import List, Dict, Optional
from .client import UltraciteClient

class WatchdogEngine:
    def __init__(self, client: UltraciteClient, base_dir: str):
        self.client = client
        self.base_dir = base_dir
        self.queries_path = os.path.join(base_dir, "app/watchdog/queries.yaml")
        self.snapshots_dir = os.path.join(base_dir, "../docs/regulations/snapshots")
        self.reports_dir = os.path.join(base_dir, "../docs/regulations/reports")
        
        # Ensure directories exist
        os.makedirs(self.snapshots_dir, exist_ok=True)
        os.makedirs(self.reports_dir, exist_ok=True)

    def load_queries(self) -> List[Dict]:
        with open(self.queries_path, 'r') as f:
            data = yaml.safe_load(f)
        return data.get('queries', [])

    def run(self) -> str:
        queries = self.load_queries()
        report_lines = [f"# Ultracite Regulation Watchdog Report", f"Date: {datetime.datetime.now().isoformat()}", ""]
        changes_detected = False

        for q in queries:
            q_id = q['id']
            title = q['title']
            description = q['description']
            
            # Fetch current data
            current_content = self.client.search(description)
            
            # Load previous snapshot
            snapshot_path = os.path.join(self.snapshots_dir, f"{q_id}.txt")
            previous_content = ""
            if os.path.exists(snapshot_path):
                with open(snapshot_path, 'r') as f:
                    previous_content = f.read()
            
            # Compare
            if current_content != previous_content:
                changes_detected = True
                report_lines.append(f"## CHANGE DETECTED: {title}")
                report_lines.append(f"**Query ID**: `{q_id}`")
                report_lines.append("### Diff Summary")
                report_lines.append("Content has changed since last snapshot.")
                report_lines.append("#### Previous")
                report_lines.append(f"```\n{previous_content}\n```")
                report_lines.append("#### Current")
                report_lines.append(f"```\n{current_content}\n```")
                report_lines.append("---")
                
                # Update snapshot
                with open(snapshot_path, 'w') as f:
                    f.write(current_content)
            else:
                report_lines.append(f"## No Change: {title}")
                report_lines.append("---")

        report_content = "\n".join(report_lines)
        
        # Save report
        report_filename = f"report-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}.md"
        report_path = os.path.join(self.reports_dir, report_filename)
        with open(report_path, 'w') as f:
            f.write(report_content)
            
        return report_path
