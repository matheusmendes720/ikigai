"""Fix ALL mismatched quote characters in seed.py.

Looks for any string that starts with " and ends with ' (ASCII 0x27)
when the ' appears before , ) or ] — indicating a closing quote typo.
"""
import re
import sys

path = r"C:\Users\mathe\code_space\life-oss\life\life-ops\operational\src\operational\cli\seed.py"

with open(path, "rb") as f:
    data = f.read()

# Find all occurrences of: "...WORD'  where ' should be "
# Pattern: double-quote, then any content, then single-quote before comma/paren/bracket
# We use a simple bytes search: find all ' that appear after a word char and before ,)] 
# and are preceded by a " on the same "line logical string"
lines = data.split(b"\n")
fixed = []
count = 0
for i, line in enumerate(lines, 1):
    # Check for pattern: " (any chars except ") ' followed by , ) or ]
    # This happens when a double-quoted string is closed with single quote
    new_line = line

    # Strategy: in each line, if there's an odd number of " and at least one ' before ,)]
    # replace the last ' before ,)] with "
    # Simpler: find all occurrences of char+' where char is > 0x7F (non-ASCII) or alphanumeric
    # and ' is followed by comma, close paren, or close bracket

    # Use regex on string (decode line)
    try:
        text = line.decode("utf-8")
    except UnicodeDecodeError:
        continue

    # Pattern: "..."' followed by , ) or ]
    # This catches strings that start with " but end with '
    import re

    new_text = re.sub(
        r'("[^"]*?)\'(?=[,\)\]])',
        lambda m: m.group(1) + '"',
        text,
    )
    if new_text != text:
        sys.stdout.write(f"  Fixed line {i}: {text.strip()[:60]}\n")
        sys.stdout.flush()
        count += 1

    fixed.append(new_text.encode("utf-8"))

data = b"\n".join(fixed)
sys.stdout.write(f"Total fixed: {count} lines\n")
sys.stdout.flush()

with open(path, "wb") as f:
    f.write(data)
