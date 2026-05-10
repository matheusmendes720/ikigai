from tasklib import TaskWarrior
import os
import sys

tw_path = "c:/Users/mathe/code_space/produtividade/taskwarrior"
print(f"Testing TaskWarrior at {tw_path}")
try:
    tw = TaskWarrior(tw_path)
    print("TaskWarrior object created")
    # This usually triggers a call to 'task version' or similar
    print(f"TW config: {tw.config}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
