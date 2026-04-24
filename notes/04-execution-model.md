# LangGraph Execution Model

Inspired by **Google's Pregel** graph processing system.

## Three Phases of Execution

### 1. Graph Definition

Define the structure: nodes, edges, and state schema.

```python
from langgraph.graph import StateGraph, START, END

# Define state
class MyState(TypedDict):
    data: str

# Create graph
graph = StateGraph(MyState)

# Add nodes
graph.add_node("node_a", function_a)
graph.add_node("node_b", function_b)

# Add edges
graph.add_edge(START, "node_a")
graph.add_edge("node_a", "node_b")
graph.add_edge("node_b", END)
```

### 2. Compilation

Validate graph structure and prepare for execution.

```python
app = graph.compile()
```

**Validation checks**:
- No orphan nodes (nodes without edges)
- No disconnected subgraphs
- Valid edge connections
- Proper START and END connections

### 3. Execution

Run the compiled graph with input state.

```python
result = app.invoke({"data": "input"})
```

## Execution Flow (Message Passing)

LangGraph uses **message passing** between nodes:

```
┌─────────────────────────────────────────────────────┐
│                    SUPERSTEP 1                       │
│  [START] ──(state)──> [Node A]                       │
│                          │                           │
│                    (updated state)                   │
└──────────────────────────┼──────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────┐
│                    SUPERSTEP 2                       │
│  [Node A output] ──(state)──> [Node B]              │
│                                  │                   │
│                            (updated state)           │
└──────────────────────────────────┼──────────────────┘
                                   ▼
┌─────────────────────────────────────────────────────┐
│                    SUPERSTEP 3                       │
│  [Node B output] ──(state)──> [END]                 │
└─────────────────────────────────────────────────────┘
```

## Supersteps

A **superstep** is a unit of work in graph execution:

1. All active nodes receive their input messages (state)
2. Nodes execute their functions in parallel (if independent)
3. Nodes produce output messages (state updates)
4. Messages are passed to next nodes via edges
5. Repeat until no active nodes or messages remain

### Parallel Execution in Supersteps

```
                    SUPERSTEP N
    ┌────────────────────────────────────┐
    │     ┌→ [Node B] ─┐                 │
    │     │            │                 │
[Node A] ─┼→ [Node C] ─┼→ [Node E]       │
    │     │            │                 │
    │     └→ [Node D] ─┘                 │
    └────────────────────────────────────┘
    
Nodes B, C, D execute in PARALLEL within same superstep
```

## Execution Details

### Step-by-Step Process

1. **Initialize**: Create initial state from input
2. **Start**: Pass state to first node(s) after START
3. **Execute**: Node runs its Python function
4. **Update**: Node returns state updates
5. **Merge**: Updates merged into state (using reducers)
6. **Route**: Determine next node(s) based on edges
7. **Pass**: Send updated state to next node(s)
8. **Repeat**: Continue until END reached

### Conditional Routing

```python
def route_decision(state):
    if state["score"] > 0.8:
        return "approved"
    return "rejected"

graph.add_conditional_edges(
    "evaluator",
    route_decision,
    {
        "approved": "success_handler",
        "rejected": "retry_handler"
    }
)
```

### Loop/Cycle Execution

Loops continue until a condition routes to END:

```python
def should_continue(state):
    if state["iteration"] >= 3 or state["score"] >= 0.9:
        return "end"
    return "continue"

graph.add_conditional_edges(
    "evaluator",
    should_continue,
    {
        "continue": "generator",  # Loop back
        "end": END
    }
)
```

## Execution Methods

### invoke() - Run to Completion

```python
result = app.invoke({"input": "data"})
# Returns final state after graph completes
```

### stream() - Stream Results

```python
for event in app.stream({"input": "data"}):
    print(event)
# Yields state updates as execution progresses
```

### Stream Modes

```python
# Stream full state at each step
for state in app.stream(input, stream_mode="values"):
    print(state)

# Stream only updates
for update in app.stream(input, stream_mode="updates"):
    print(update)
```

## Abstraction Benefits

The execution model **abstracts away**:
- Manual node invocation
- State passing between nodes
- Parallel execution coordination
- Error handling and retries
- Checkpoint management

**You define WHAT** (nodes and edges), **LangGraph handles HOW** (execution).

## Key Concepts Summary

| Concept | Description |
|---------|-------------|
| **Graph Definition** | Structure of nodes and edges |
| **Compilation** | Validation and preparation |
| **Execution** | Running the workflow |
| **Message Passing** | State flows between nodes |
| **Superstep** | Unit of parallel execution |
| **Routing** | Determining next nodes |

---

## Interview Questions

### Conceptual

1. **Why does LangGraph have a separate compile step instead of running the graph directly from its definition?**
   > Compilation validates the graph structure upfront — orphan nodes, missing START/END connections, disconnected subgraphs. This catches bugs before any execution happens, which is critical for long-running agents where discovering a structural error at step 50 wastes all prior computation. Compilation also performs optimisations and wires up internal execution machinery that `invoke()` then just runs.

2. **How does message passing between nodes differ from nodes directly calling each other?**
   > In message passing, a node doesn't know who comes next — it just returns a state update and hands off to LangGraph, which routes to the next node(s) based on edge definitions. Direct calls would tightly couple nodes together. Message passing keeps nodes fully decoupled: you can rewire the graph (change edges) without modifying any node's code.

3. **Why does LangGraph execute parallel nodes within the same superstep rather than scheduling them as separate sequential steps?**
   > Nodes that have no data dependency on each other can safely run concurrently — there's no need to wait. Batching them into one superstep maximises throughput and minimises latency. Running them sequentially when they're independent would be artificially slow. The superstep model (from Pregel) makes it explicit: all nodes in a superstep receive the same state snapshot and execute concurrently.

4. **What determines when graph execution terminates?**
   > Execution terminates when there are no more active nodes or pending messages — i.e., all currently executing nodes have completed and no edges lead to any further nodes. In practice, this means all execution paths have reached an END node. For loops, termination depends on the conditional edge eventually routing to END rather than looping back.

### Critical Thinking

1. **`invoke()` vs `stream()` — when would you choose streaming even if you don't need real-time output?**
   > For long-running graphs, `stream()` lets you observe intermediate state updates as they happen — useful for debugging, logging, and monitoring which nodes are executing and in what order. With `invoke()` you only get the final result; if the graph hangs or produces a wrong result, you have no visibility into where it went wrong. Streaming gives you a live execution trace without needing LangSmith.

2. **If a graph has a cycle (loop), how does LangGraph know it hasn't entered an infinite loop?**
   > LangGraph itself doesn't enforce a loop limit — that's the developer's responsibility via the conditional edge routing function. You must write the exit condition explicitly (e.g., max iterations, quality threshold). If you forget the exit condition, the graph will loop forever. This is a deliberate design choice: LangGraph gives you the power to build cycles, but doesn't impose arbitrary limits on your workflow logic.

3. **Two developers debate: one says compile the graph once at startup and reuse it; the other says compile it fresh per request. Who's right?**
   > Compile once at startup. Compilation is an expensive structural operation (validation, wiring), while `invoke()` is cheap. Recompiling per request wastes CPU and adds latency. The compiled graph is stateless and thread-safe — state lives in the invocation call, not in the compiled object, so the same compiled graph can safely handle concurrent requests with different states.

### Scenario-Based

1. **Your graph has 6 nodes but after calling `compile()` you get a validation error about an orphan node. What does this mean and how do you fix it?**
   > An orphan node is a node that was added via `add_node()` but has no edges connecting it to the rest of the graph — it can never be reached during execution. Fix it by either adding the appropriate `add_edge()` calls to connect it into the flow, or removing it with the knowledge that it was never meant to be part of this graph. The error is a design-time signal, not a runtime bug.

2. **You have a parallel fan-out where 3 nodes execute concurrently. One of them takes 10x longer than the others. How does LangGraph handle this, and does it affect the other nodes?**
   > LangGraph waits for all nodes in a superstep to complete before advancing to the next superstep. So the 2 fast nodes complete but their results aren't passed forward until the slow node also finishes. This is the barrier synchronisation model from Pregel. The other nodes aren't slowed during their own execution, but the overall superstep is gated by the slowest node. If this is a bottleneck, the slow node should be moved to its own sequential step rather than being in the parallel fan-out.

3. **You invoke a graph and it returns a result, but one of the intermediate node outputs looks wrong. How do you investigate using LangGraph's execution model?**
   > Switch from `invoke()` to `stream(stream_mode="updates")` — this yields each node's state update as it happens. You can see exactly what each node returned and in what order. If using LangSmith, the full execution trace shows node inputs, outputs, and timing. You can also add an `interrupt_before` on the suspicious node at compile time to pause execution and inspect state before that node runs.

---

*Studied: 2026-04-24*
