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

*Studied: 2026-04-24*
