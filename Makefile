# Makefile for langgraph dev workflow
# Wraps the planning-with-files-engine + agentic-markdown-system flows
# under a single langgraph dev server.

.PHONY: help dev install install-langgraph test clean logs status

help:
	@echo "langgraph dev Makefile - Single-project agentic flows"
	@echo ""
	@echo "Targets:"
	@echo "  make dev              - Run langgraph dev server (port 2024)"
	@echo "  make dev-graph NAME=X  - Run a specific graph"
	@echo "  make install          - Install langgraph CLI + deps"
	@echo "  make install-langgraph - Install langgraph CLI only"
	@echo "  make test             - Run all 250+ IKIGAi tests + new graph tests"
	@echo "  make logs             - Tail langgraph dev logs"
	@echo "  make status           - Show all registered graphs + their status"
	@echo "  make clean            - Clear state + checkpoints"

dev:
	uv run langgraph dev

dev-graph:
	uv run langgraph dev --graph $(NAME)

install-langgraph:
	uv add "langgraph-cli[inmem]"

install: install-langgraph
	uv add langgraph langgraph-checkpoint
	uv add "vibe-ops[pae-maintainer]" --optional

test:
	uv run --with pydantic --with python-frontmatter pytest vibe-ops/tests/ -v --tb=short
	cd life-ops/operational && poetry run pytest tests/ -v --tb=short
	uv run --with langgraph --with pydantic pytest langgraph_tests/ -v --tb=short

logs:
	tail -f .langgraph/logs/dev.log 2>/dev/null || echo "No logs yet - run 'make dev' first"

status:
	@echo "Registered graphs (from langgraph.json):"
	@cat langgraph.json | python -c "import json, sys; d=json.load(sys.stdin); [print(f'  {n}: {p}') for n, p in d.get('graphs', {}).items()]"
	@echo ""
	@echo "Last 5 commits:"
	@git log --oneline -5

clean:
	rm -rf .langgraph/state.db .langgraph/checkpoints/
	@echo "Cleared langgraph state and checkpoints."