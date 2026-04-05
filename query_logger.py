import json
import os
from datetime import datetime
from pathlib import Path

LOG_FILE = Path(__file__).parent / "data" / "logs" / "llm_queries.log"

def log_query(model: str, system_prompt: str, user_prompt: str, response: str, task_name: str = "general"):
    """
    Logs every interaction with the local models to track usage for Frugal AI tracking.
    """
    os.makedirs(LOG_FILE.parent, exist_ok=True)
    
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "task_name": task_name,
        "model": model,
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "response": response
    }
    
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(log_entry) + '\n')
