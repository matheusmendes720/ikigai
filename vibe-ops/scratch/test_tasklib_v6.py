from tasklib import TaskWarrior
import os
import sys

wsl_data_path = "/mnt/c/Users/mathe/code_space/produtividade/taskwarrior"

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

test_command("wsl task", wsl_data_path)
