"""LangGraph API wrapper — loaded by langgraph dev via langgraph.json.

This file is loaded directly by langgraph dev's module loader, which uses
spec_from_file_location (no package context). All imports here must be
absolute (not relative) so Python can resolve them via sys.path.
"""
from agents.ikigai_maintainer.graph import graph
