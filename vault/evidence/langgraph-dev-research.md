# LangGraph Dev Research

## Executive Summary

langgraph dev is a CLI command that starts a local development server with hot reloading for LangGraph applications. It requires graphs to be compiled LangGraph StateGraph instances (from the langgraph SDK) - custom Python graphs that do not import from langgraph cannot be directly registered.

---

## 1. What is langgraph dev?

langgraph dev runs the LangGraph API server locally in development mode with hot reloading. Key characteristics:

- No Docker required - runs directly in your Python environment
- Hot reloading - automatically reloads on code changes
- Port 2024 by default - configurable via --port
- State persisted to local directory
- DAP debugging support - attach IDE debugger via --debug-port

Install: uv add langgraph-cli[inmem] or pip install langgraph-cli[inmem]

---

## 2. Standard Project Structure

### langgraph.json - Core Configuration

json:
{
  dollar_sign schema: https://langchain-ai.github.io/langgraph/schemas/langgraph.json,
  dependencies: [.],
  graphs: {
    agent: ./path/to/graph.py:graph
  },
  env: .env,
  python_version: 3.11
}

### graphs Field Format

The graphs dict maps graph ID to import path:

json:
{
  graphs: {
    graph_name: ./package/file.py:variable,
    graph_name: ./package/file.py:make_graph
  }
}

- Variable: Must be an instance of CompiledStateGraph
- Factory function: Takes RunnableConfig dict, returns StateGraph or CompiledStateGraph

### Directory Layout Example

my-langgraph-project/
  langgraph.json
  pyproject.toml
  .env
  src/
    my_agent/
      __init__.py
      graph.py
      nodes.py
      state.py

---

## 3. How LangGraph Dev Discovers Graphs

The CLI:

1. Reads langgraph.json
2. For each entry in graphs, parses path:attribute
3. Uses importlib to dynamically import the module
4. Extracts the attribute (must be CompiledStateGraph instance or callable)
5. Validates the graph is a proper LangGraph instance

From config.py source (lines 866-919):
- Graph paths support both relative paths (./my_agent/graph.py:graph) and module-style (my_package.graph:graph)
- Relative paths are resolved relative to langgraph.json location
- Local dependencies are copied to /deps/ inside containers

---

## 4. Graph Registration Requirement

### CRITICAL: SDK Dependency

The graph MUST be an instance of langgraph.graph.state.CompiledStateGraph (or a factory returning same).

From official docs:
graphs: Mapping from graph ID to path where the compiled graph or a function that makes a graph is defined. Example: ./your_package/file.py:variable, where variable is an instance of langgraph.graph.state.CompiledStateGraph

### What This Means for Your Project

Your current vibe-ops/src/agents/pae_maintainer/ uses a custom graph that:
- Has state.py, nodes.py, channels.py, graph.py, main.py, __main__.py
- Does NOT import from langgraph SDK (per plan guardrail)
- Mimics LangGraph patterns but is custom Python

This custom graph CANNOT be directly registered with langgraph dev because langgraph dev expects a CompiledStateGraph instance.

---

## 5. Can Custom Python Graphs Be Registered?

No - not without rewriting to use LangGraph SDK.

However, there are two options:

### Option A: Wrap Your Graph as a LangGraph SDK Graph

Your custom graph logic can be wrapped inside a StateGraph node:

python:
from langgraph.graph import StateGraph, START, END

def pae_maintainer_node(state: dict) -> dict:
    result = your_existing_process(state)
    return result

builder = StateGraph(dict)
builder.add_node(pae_maintainer, pae_maintainer_node)
builder.add_edge(START, pae_maintainer)
builder.add_edge(pae_maintainer, END)
graph = builder.compile()

### Option B: Keep Custom Runtime, Expose via Custom HTTP

Use http.app to mount your custom application:

json:
{
  graphs: {},
  http: {
    app: ./my_custom_app.py:app
  }
}

This requires FastAPI app with LangGraph SDK client calls.

---

## 6. Multiple Graphs in One Project

LangGraph dev supports multiple graphs - each gets its own endpoint:

json:
{
  dependencies: [.],
  graphs: {
    pae_maintainer: ./vibe_ops/src/agents/pae_maintainer/graph.py:graph,
    quarterly_replan: ./workflows/quarterly_replan.py:graph,
    test_de_fogo: ./workflows/test_de_fogo_rollup.py:graph,
    correction: ./workflows/correction_protocol.py:graph,
    dream: ./workflows/dream_falsification.py:graph
  },
  python_version: 3.11
}

Each graph is then accessible at:
- POST /runs/{graph_id}
- POST /runs/stream/{graph_id}

---

## 7. pyproject.toml Requirements

toml:
[project]
name = my-langgraph-project
version = 0.1.0
requires-python = >=3.11

[project.optional-dependencies]
dev = [
    langgraph-cli[inmem],
]

Minimal install for langgraph dev:
bash:
uv add langgraph-cli -G dev
pip install langgraph-cli[inmem]

---

## 8. Step-by-Step Migration Plan

### Phase 1: Assess Graph Compatibility
1. Examine vibe-ops/src/agents/pae_maintainer/graph.py
2. Identify state schema, node functions, edges
3. Determine if logic can be wrapped as StateGraph nodes

### Phase 2: Create SDK Wrapper (if viable)
1. Create vibe-ops/src/agents/pae_maintainer/langgraph_wrapper.py
2. Import your existing node/channel logic
3. Wrap in StateGraph(...).compile()

### Phase 3: Create langgraph.json
1. Place langgraph.json at project root
2. Add all graphs as entries

### Phase 4: Test with langgraph dev
bash:
langgraph dev --config ./langgraph.json

---

## 9. Identified Gaps and Refactoring Needs

| Gap | Impact | Remediation |
|-----|--------|-------------|
| Custom graph uses no langgraph imports | Cannot register directly | Rewrite graph.py to use StateGraph |
| YAML workflows (quarterly-replan, etc.) | Not graphs - just config | Need Python wrapper that invokes YAML-driven logic |
| No pyproject.toml in vibe-ops | CLI cant find dependencies | Add pyproject.toml or use dependencies: [.] |
| Plan guardrail: NO langgraph SDK imports | Blocks direct adoption | Plan revision needed - guardrail conflicts with goal |

---

## 10. Key References

- LangGraph CLI README: https://github.com/langchain-ai/langgraph/blob/main/libs/cli/README.md
- LangGraph JSON Schema: https://github.com/langchain-ai/langgraph/blob/main/libs/cli/schemas/schema.json
- Local Dev Server Guide: https://docs.langchain.com/oss/python/langgraph/local-server
- CopilotKit Example: https://github.com/CopilotKit/CopilotKit/blob/main/examples/showcases/deep-agents-finance-erp/agent/langgraph.json

---

## 200-Word Summary

langgraph dev is the official CLI for running LangGraph applications locally with hot reloading. It reads a langgraph.json configuration file that maps graph names to Python module paths (./package/file.py:variable). The critical requirement is that each graph must be a CompiledStateGraph instance (or a factory function returning one) from the langgraph SDK - this is how the CLI discovers and validates graphs.

For the users project (vibe-ops/src/agents/pae_maintainer/ with custom state.py, nodes.py, channels.py, graph.py), direct registration is not possible because the existing code deliberately avoids langgraph SDK imports per plan guardrail. The custom graph mimics LangGraph patterns but uses pure Python.

Two paths forward: (1) Wrap the existing node/channel logic inside a StateGraph node function and compile it - enabling langgraph dev compatibility - or (2) keep the custom runtime and use the http.app extension point for a custom FastAPI wrapper.

For multiple graphs, simply add entries to the graphs dict in langgraph.json. However, the YAML workflows (quarterly-replan, test-de-fogo-rollup, correction-protocol, dream-falsification) are not LangGraph graphs and would need Python wrappers to become graph-invokable. The plan guardrail prohibiting langgraph SDK imports directly conflicts with the goal of using langgraph dev - this requires a strategic decision.
