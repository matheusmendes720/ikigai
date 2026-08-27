---
name: "source-command-agents-spawn"
description: "Spawn a new agent with V3 capabilities"
---

# source-command-agents-spawn

Use this skill when the user asks to run the migrated source command `agents-spawn`.

## Command Template

# Agent Spawn Command

Spawn a new agent with full V3 capabilities including neural patterns, memory integration, and swarm coordination.

## Usage

```bash
npx Codex-flow agent spawn [options]
```

## Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--type` | `-t` | Agent type to spawn | Required |
| `--name` | `-n` | Agent name/identifier | Auto-generated |
| `--provider` | `-p` | AI provider (anthropic, openrouter, ollama) | anthropic |
| `--model` | `-m` | Model to use | Provider default |
| `--task` | | Initial task for the agent | None |
| `--timeout` | | Agent timeout in seconds | 300 |
| `--auto-tools` | | Enable automatic tool usage | true |

## Agent Types (87 Available)

### Core Development
```bash
npx Codex-flow agent spawn -t coder      # Code implementation
npx Codex-flow agent spawn -t reviewer   # Code review
npx Codex-flow agent spawn -t tester     # Testing
npx Codex-flow agent spawn -t planner    # Planning
npx Codex-flow agent spawn -t researcher # Research
```

### V3 Specialized
```bash
npx Codex-flow agent spawn -t security-architect     # Security design
npx Codex-flow agent spawn -t security-auditor       # CVE remediation
npx Codex-flow agent spawn -t memory-specialist      # AgentDB (150x-12,500x faster)
npx Codex-flow agent spawn -t performance-engineer   # 2.49x-7.47x optimization
npx Codex-flow agent spawn -t core-architect         # DDD design
```

### Swarm Coordination
```bash
npx Codex-flow agent spawn -t hierarchical-coordinator  # Queen-led
npx Codex-flow agent spawn -t mesh-coordinator          # P2P network
npx Codex-flow agent spawn -t adaptive-coordinator      # Dynamic topology
npx Codex-flow agent spawn -t collective-intelligence-coordinator
```

### Consensus Agents
```bash
npx Codex-flow agent spawn -t byzantine-coordinator  # BFT consensus
npx Codex-flow agent spawn -t raft-manager          # Leader-based
npx Codex-flow agent spawn -t gossip-coordinator    # Eventual consistency
npx Codex-flow agent spawn -t crdt-synchronizer     # CRDT replication
npx Codex-flow agent spawn -t quorum-manager        # Quorum-based
```

### GitHub Integration
```bash
npx Codex-flow agent spawn -t pr-manager           # PR lifecycle
npx Codex-flow agent spawn -t code-review-swarm    # Multi-agent review
npx Codex-flow agent spawn -t issue-tracker        # Issue management
npx Codex-flow agent spawn -t release-manager      # Release coordination
npx Codex-flow agent spawn -t workflow-automation  # CI/CD automation
```

### SPARC Methodology
```bash
npx Codex-flow agent spawn -t sparc-coordinator    # SPARC orchestration
npx Codex-flow agent spawn -t specification        # Requirements
npx Codex-flow agent spawn -t pseudocode          # Algorithm design
npx Codex-flow agent spawn -t architecture        # System design
npx Codex-flow agent spawn -t refinement          # Iterative improvement
```

## Examples

```bash
# Spawn with custom name
npx Codex-flow agent spawn -t coder --name feature-bot

# Spawn with initial task
npx Codex-flow agent spawn -t researcher --task "Research React 19 features"

# Spawn with specific model
npx Codex-flow agent spawn -t architect -m Codex-3-opus-20240229

# Spawn with custom timeout
npx Codex-flow agent spawn -t tester --timeout 600

# Spawn using OpenRouter
npx Codex-flow agent spawn -t coder -p openrouter -m anthropic/Codex-3.5-sonnet
```

## Using Codex's Task Tool

For actual execution, always use Codex's Task tool:

```javascript
// Spawn ALL agents in ONE message for parallel execution
Task("Coder", "Implement authentication feature", "coder")
Task("Tester", "Write unit tests for auth", "tester")
Task("Reviewer", "Review auth implementation", "reviewer")
```

## MCP Coordination (Optional)

Use MCP tools only for swarm coordination setup:

```javascript
mcp__claude-flow__swarm_init({ topology: "hierarchical", maxAgents: 15 })
mcp__claude-flow__agent_spawn({ type: "coordinator", name: "queen" })
```

## Output

```
Spawning coder agent: feature-bot

+-----------+----------------------------------+
| Property  | Value                            |
+-----------+----------------------------------+
| ID        | coder-lx7m9k2                    |
| Type      | coder                            |
| Name      | feature-bot                      |
| Status    | active                           |
| Created   | 2026-01-08T03:30:00.000Z         |
| Capabilities | code, debug, refactor, test   |
+-----------+----------------------------------+

Agent feature-bot spawned successfully
```
