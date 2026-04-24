# State and Reducers in LangGraph

## What is State?

**State** is a **shared, mutable memory** that flows through the graph during execution.

- Contains all data pieces necessary for execution
- Includes: inputs, intermediate results, scores, messages, etc.
- Dynamically evolves as nodes execute and update it
- Every node accesses current state → modifies it → passes to next node(s)

## Implementing State

State is implemented as a **typed dictionary** (Python's TypedDict or Pydantic).

### Basic State

```python
from typing import TypedDict

class SimpleState(TypedDict):
    input: str
    output: str
    score: int
```

### State with Messages (Common for Chatbots)

```python
from langgraph.graph.message import MessagesState

# MessagesState already includes a 'messages' field with proper reducer
class ChatState(MessagesState):
    context: str  # Add extra fields as needed
```

### Custom State with Multiple Fields

```python
from typing import TypedDict, List, Optional

class WorkflowState(TypedDict):
    query: str
    search_results: List[str]
    draft: str
    feedback: Optional[str]
    score: int
    iteration: int
```

## How State Flows

```
[START] → [Node A] → [Node B] → [Node C] → [END]
   │          │          │          │
   └── State ─┴── State ─┴── State ─┘
       v1         v2         v3
```

1. Initial state passed at START
2. Node A receives state, processes, returns updates
3. Updates merged into state (v2)
4. Node B receives updated state
5. Process continues until END

## Reducers: Managing State Updates

**Reducers** determine how state updates from nodes are applied to the shared state.

### Why Reducers Matter

Without reducers, updates simply **replace** existing values. This is problematic when:
- Multiple parallel nodes update the same field
- You want to preserve history (e.g., chat messages)
- You need to aggregate results

### Reducer Types

| Reducer Type | Behavior | Use Case |
|--------------|----------|----------|
| **Replace** (default) | New value replaces old | Simple values, latest result |
| **Append/Add** | New value added to list | Messages, history, logs |
| **Merge** | Combine with existing data | Aggregating parallel results |
| **Custom** | Any custom logic | Complex merge strategies |

### Implementing Reducers

```python
from typing import TypedDict, Annotated, List
from operator import add

class CounterState(TypedDict):
    # Default behavior - replace
    current_value: int
    
    # Append reducer - values are concatenated
    messages: Annotated[List[str], add]
    
    # Custom reducer
    scores: Annotated[List[int], lambda old, new: old + new]
```

### Built-in Message Reducer

```python
from langgraph.graph.message import add_messages

class ChatState(TypedDict):
    # add_messages handles message deduplication and proper ordering
    messages: Annotated[list, add_messages]
```

## Reducer Examples

### Example 1: Simple Arithmetic Workflow

Values can be replaced since we only care about the latest result.

```python
class ArithmeticState(TypedDict):
    a: int          # Replace
    b: int          # Replace
    result: int     # Replace

def add_numbers(state):
    return {"result": state["a"] + state["b"]}
```

### Example 2: Chatbot (Append Messages)

Messages should be appended to preserve conversation history.

```python
from langgraph.graph.message import add_messages

class ChatState(TypedDict):
    messages: Annotated[list, add_messages]

def chatbot(state):
    response = llm.invoke(state["messages"])
    # This APPENDS to messages, doesn't replace
    return {"messages": [response]}
```

### Example 3: Parallel Workflow (Merge Results)

Multiple nodes running in parallel need their results merged.

```python
class ParallelState(TypedDict):
    query: str
    # Results from parallel nodes are combined
    results: Annotated[List[str], add]

def search_google(state):
    return {"results": [google_search(state["query"])]}

def search_bing(state):
    return {"results": [bing_search(state["query"])]}

# Both results end up in the list, not overwritten
```

## Critical: Reducers in Parallel Workflows

**Problem**: Without proper reducers, parallel nodes can overwrite each other's results.

```
              ┌→ [Node A] returns {"data": "A"} ─┐
[State] → [Fan Out]                              → [Merge] → ???
              └→ [Node B] returns {"data": "B"} ─┘
```

Without reducer: `data = "B"` (last write wins, "A" lost!)
With append reducer: `data = ["A", "B"]` (both preserved)

**Rule**: Always use appropriate reducers when parallel nodes update the same state field.

## State Best Practices

1. **Define clear state schema** - Know what data flows through your graph
2. **Use TypedDict** - Type safety helps catch errors
3. **Choose reducers carefully** - Match reducer to your data needs
4. **Keep state minimal** - Only include what's needed
5. **Document state fields** - Explain purpose of each field

---

*Studied: 2026-04-24*
