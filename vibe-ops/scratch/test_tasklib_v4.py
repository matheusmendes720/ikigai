from tasklib import TaskWarrior
import os
import sys

tw_path = "c:/Users/mathe/code_space/produtividade/taskwarrior"
print(f"Testing TaskWarrior at {tw_path}")

def test_command(cmd):
    print(f"\n--- Testing with command: {cmd} ---")
    try:
        tw = TaskWarrior(tw_path, task_command=cmd)
        print("TaskWarrior object created")
        print(f"Version: {tw.version}")
        tasks = tw.tasks.all()
        print(f"Found {len(tasks)} tasks")
        if len(tasks) > 0:
            print(f"First task: {tasks[0]['description']}")
        return True
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

test_command("wsl -e task")
