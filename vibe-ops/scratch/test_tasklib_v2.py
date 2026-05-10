from tasklib import TaskWarrior
import os
import sys
import subprocess

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

# Try just 'task' (fails)
# test_command("task")

# Try full path to task.bat
# bat_path = os.path.abspath("c:/Users/mathe/code_space/produtividade/life/vibe-ops/task.bat")
# test_command(bat_path)

# Try wsl directly
test_command("wsl") # This will likely call 'wsl --version' which might work for _get_version but fail later

# Try list
test_command(["wsl", "-e", "task"])
