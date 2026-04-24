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

## Interview Questions

### Conceptual

1. **How does LangGraph differ from simply chaining LLM calls in plain Python code?**
   > Plain chaining is linear and rigid — no native support for parallelism, loops, or dynamic routing. LangGraph models the workflow explicitly as a graph, so you get parallel branches, conditional routing based on LLM output, cycles with exit conditions, shared state, and resumability from failures — all things that are extremely error-prone to implement manually in code.

2. **Why does a node only return the fields it wants to change, rather than the full state?**
   > Because nodes are modular and should only be responsible for their own output. Returning the full state would mean every node needs to know about every field, creating tight coupling. Returning only updates keeps nodes isolated — LangGraph merges the partial update into the shared state internally.

3. **Why does LangGraph validate the graph at compile time rather than at runtime?**
   > Catching structural errors (orphan nodes, disconnected subgraphs, missing START/END connections) at compile time prevents silent failures mid-execution — especially important for long-running agents where a bug discovered at step 50 wastes all prior work. Compile-time validation is a design contract: if `compile()` succeeds, the graph structure is sound.

4. **Can a single graph have multiple paths that all lead to END? What does that mean for execution?**
   > Yes. Different conditional branches can independently route to END. It means the graph has multiple valid termination paths — whichever branch executes will eventually reach END. Only the path that actually runs during a given invocation completes; the other branches are simply not activated.

### Critical Thinking

1. **If you needed to add a new processing step to an existing workflow, how does LangGraph's structure make that safer than modifying a plain pipeline?**
   > In LangGraph you add a new node function and wire it into the graph with edges — the existing nodes are untouched. In a plain pipeline you'd modify the sequential logic directly, risking breaking upstream or downstream steps. The node boundary acts as an isolation layer; changes are additive, not in-place edits to existing logic.

2. **A node in your graph is producing wrong outputs. What does LangGraph's structure give you that helps you debug this faster than a plain Python pipeline?**
   > LangGraph's graph structure lets you trace exactly which node fired, in what order, with what state it received, and what update it returned. With LangSmith integration you get a full execution trace per invocation. In a plain pipeline you'd have to instrument logging manually throughout. You can also test the node function in isolation since it's just a Python function that takes state and returns a dict.

3. **Why is it important that edges define flow rather than nodes calling each other directly?**
   > If nodes called each other directly, they'd be tightly coupled — changing one node's output would require updating every node that calls it. Edges keep nodes decoupled: a node only knows its own logic, not who comes next. The graph definition owns the flow, which means you can rewire execution without touching node code.

### Scenario-Based

1. **You're building a customer support bot that handles billing, technical, and general queries differently. How would you model this in LangGraph?**
   > Define a `classifier` node that reads the user query and returns a category string. Use `add_conditional_edges` from `classifier` with a routing function mapping each category to a dedicated handler node (`billing_handler`, `tech_handler`, `general_handler`). Each handler processes independently and routes to END. The routing logic lives in the edge function, not inside any node.

2. **A teammate says "just use a for loop to retry the LLM if output quality is low." Why would you use LangGraph instead, and what do you gain?**
   > The LangGraph way is an Evaluator-Optimiser loop: a `generator` node, an `evaluator` node, and a conditional edge that loops back to `generator` if the score is below threshold. You gain: state (drafts, scores, feedback) tracked cleanly across iterations; checkpointing so a mid-loop failure doesn't lose progress; the loop exit condition is explicit in the graph structure and inspectable; and you can interrupt mid-loop for human review — none of which a plain for-loop gives you.

---

*Studied: 2026-04-24*
