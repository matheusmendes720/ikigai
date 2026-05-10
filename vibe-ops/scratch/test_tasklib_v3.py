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
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

test_command("wsl -e task")
