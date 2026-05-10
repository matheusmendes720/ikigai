from tasklib import TaskWarrior
import os
import sys

# Convert Windows path to WSL path
win_path = "c:/Users/mathe/code_space/produtividade/taskwarrior"
# c:/Users/... -> /mnt/c/Users/...
wsl_data_path = "/mnt/c/Users/mathe/code_space/produtividade/taskwarrior"

print(f"Testing TaskWarrior with WSL path: {wsl_data_path}")

def test_command(cmd, data_path):
    print(f"\n--- Testing with command: {cmd} and data_path: {data_path} ---")
    try:
        tw = TaskWarrior(data_path, task_command=cmd)
        print("TaskWarrior object created")
        # tw.version will trigger an execution. 
        # If the version check also uses the data_path, it might fail if it's not a valid linux path.
        # But usually 'task --version' doesn't care about the data path.
        # Wait, tasklib's _get_version does NOT use rc.data.location.
        
        tasks = tw.tasks.all()
        print(f"Found {len(tasks)} tasks")
        if len(tasks) > 0:
            print(f"First task: {tasks[0]['description']}")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

test_command("wsl -e task", wsl_data_path)
