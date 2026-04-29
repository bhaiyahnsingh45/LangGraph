# LangGraph Learning Repository

My personal learning journey with LangGraph - an orchestration framework for building intelligent, stateful, multi-step LLM workflows.

## Repository Structure

```
LangGraph/
├── notes/                    # Topic-wise study notes
│   ├── 01-core-concepts.md
│   ├── 02-workflow-patterns.md
│   ├── 03-state-and-reducers.md
│   ├── 04-execution-model.md
│   └── ...
└── README.md
```

## Study Progress

| # | Topic | Status | Date |
|---|-------|--------|------|
| 1 | [Core Concepts](notes/01-core-concepts.md) | Completed | 2026-04-24 |
| 2 | [Workflow Patterns](notes/02-workflow-patterns.md) | Completed | 2026-04-24 |
| 3 | [State & Reducers](notes/03-state-and-reducers.md) | Completed | 2026-04-24 |
| 4 | [Execution Model](notes/04-execution-model.md) | Completed | 2026-04-24 |
| 5 | [Persistence](notes/05-persistence.md) | Completed | 2026-04-29 |
| 6 | [Human-in-the-Loop](notes/06-human-in-the-loop.md) | Pending | - |
| 7 | [Streaming](notes/07-streaming.md) | Pending | - |
| 8 | [Subgraphs](notes/08-subgraphs.md) | Pending | - |
| 9 | [Tool Integration](notes/09-tool-integration.md) | Pending | - |
| 10 | [Multi-Agent Systems](notes/10-multi-agent.md) | Pending | - |

## Quick Reference

### What is LangGraph?

LangGraph represents any LLM workflow as a **directed graph** where:
- **Nodes** = Individual tasks (Python functions)
- **Edges** = Execution flow between tasks
- **State** = Shared memory flowing through the graph

### Installation

```bash
pip install -U langgraph
```

## Resources

- [Official Documentation](https://docs.langchain.com/oss/python/langgraph/)
- [LangSmith](https://smith.langchain.com/) - Observability & Deployment
- [LangChain](https://docs.langchain.com/) - Integrations

---

*Last updated: 2026-04-29*
