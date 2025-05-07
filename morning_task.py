import json
from datetime import datetime

def load_memory():
    with open('memory.json', 'r') as f:
        return json.load(f)

def run_morning_ritual():
    memory = load_memory()
    rituals = memory.get('rituals', {})
    greeting = rituals.get('morning_greeting', 'Good morning!')

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"[{now}] Morning Greeting: {greeting}"
    
    # Log to a file
    with open('autonomy_log.txt', 'a') as log_file:
        log_file.write(log_message + '\n')

    print(log_message)

if __name__ == "__main__":
    run_morning_ritual()
