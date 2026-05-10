from tasklib import TaskWarrior
import os

# Use the full path to task.bat
task_bat = r"c:\Users\mathe\code_space\produtividade\life\vibe-ops\task.bat"
# Use the WSL data path found in diagnostics
wsl_data_path = "/home/flytwist/.task"

def test_command(cmd, data_path):
    print(f"\n--- Testing with command: {cmd} and data_path: {data_path} ---")
    try:
        tw = TaskWarrior(data_path, task_command=cmd)
        print("TaskWarrior object created")
        tasks = tw.tasks.all()
        print(f"Found {len(tasks)} tasks")
        if len(tasks) > 0:
            print(f"First task: {tasks[0]['description']}")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

test_command(task_bat, wsl_data_path)
