# Core Concepts of LangGraph

## What is LangGraph?

LangGraph is an **orchestration framework** that represents any LLM workflow as a **directed graph**.

- Built for **intelligent, stateful, multi-step LLM workflows**
- Inspired by **Google's Pregel** graph processing system
- Interface influenced by **NetworkX**

## Graph Components

### Nodes

- Each node = **single task** in the workflow
- Nodes are **Python functions** that perform individual tasks
- Nodes receive state, process it, and return updates

```python
def my_node(state):
    # Process state
    result = do_something(state["input"])
    return {"output": result}
```

### Edges

Edges define the **execution flow** between nodes. Types of flow:

| Flow Type | Description |
|-----------|-------------|
| **Sequential** | One node after another |
| **Parallel** | Multiple nodes execute simultaneously |
| **Conditional** | Branching based on conditions |
| **Loops (Cycles)** | Repeated execution until condition met |

```python
# Sequential edge
graph.add_edge("node_a", "node_b")

# Conditional edge
graph.add_conditional_edges("node_a", route_function, {"path1": "node_b", "path2": "node_c"})
```

### Special Nodes

- **START** - Entry point of the graph
- **END** - Exit point of the graph

```python
from langgraph.graph import StateGraph, START, END

graph.add_edge(START, "first_node")
graph.add_edge("last_node", END)
```

## Basic Graph Structure

```python
from langgraph.graph import StateGraph, START, END
from typing import TypedDict

# 1. Define State
class MyState(TypedDict):
    input: str
    output: str

# 2. Define Nodes
def process(state: MyState):
    return {"output": f"Processed: {state['input']}"}

# 3. Build Graph
graph = StateGraph(MyState)
graph.add_node("process", process)
graph.add_edge(START, "process")
graph.add_edge("process", END)

# 4. Compile
app = graph.compile()

# 5. Execute
result = app.invoke({"input": "Hello"})
```

## Key Features Enabled by Graph Structure

1. **Parallel execution** - Multiple tasks run simultaneously
2. **Loops/cycles** - Iterative workflows
3. **Conditional branching** - Decision-based routing
4. **Memory** - State persists across execution
5. **Resumability** - Restart from failure points

## Why Graphs for LLM Workflows?

- **Modularity** - Each task is isolated
- **Flexibility** - Easy to add/modify tasks
- **Visibility** - Clear visualization of flow
- **Control** - Fine-grained execution control
- **Debugging** - Trace execution through nodes

---

*Studied: 2026-04-24*
