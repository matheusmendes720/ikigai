import asyncio, os, sys
sys.path.insert(0, 'C:\\Users\\mathe\\code_space\\life-oss\\life')
from src.ikigai.src.mcp_server.taskdog_tools import mcp
asyncio.run(mcp.run_stdio_async())