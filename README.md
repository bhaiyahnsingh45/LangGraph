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

*Last updated: 2026-07-16*
