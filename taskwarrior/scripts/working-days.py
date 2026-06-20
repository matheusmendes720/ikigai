#!/usr/bin/env python3
"""Convert working days offset to calendar date.
Usage: working-days.py <YYYY-MM-DD> <days>
"""

from datetime import datetime, timedelta
import sys


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: working-days.py <YYYY-MM-DD> <days>")
        return 1

    start = datetime.strptime(sys.argv[1], "%Y-%m-%d")
    days = int(sys.argv[2])
    current = start
    count = 0
    while count < days:
        current += timedelta(days=1)
        if current.weekday() < 5:
            count += 1
    print(current.strftime("%Y-%m-%d"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
