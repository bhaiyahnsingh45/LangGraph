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

## Interview Questions

### Conceptual

1. **Why does state need to be a typed dictionary rather than a plain Python dict?**
   > TypedDict enforces a schema at definition time — every field has a declared type, which catches errors early (wrong field name, wrong type) rather than at runtime when a node silently reads `None`. It also makes the state self-documenting: anyone reading the graph code immediately knows exactly what data flows through the workflow without having to trace every node.

2. **Why does the default reducer (replace) cause data loss in parallel workflows, and how does the reducer solve it?**
   > When two parallel nodes write to the same state field, one write will overwrite the other — the last write wins. The reducer replaces this default with a merge strategy. For example, an `add` reducer concatenates lists instead of replacing, so both parallel nodes' outputs are preserved. Without this, you'd silently lose half your results with no error raised.

3. **Why does `add_messages` exist as a special reducer instead of just using a plain `add` (list append)?**
   > `add_messages` handles LangChain message-specific concerns that `add` doesn't: it deduplicates messages by ID (so re-sending the same message doesn't create duplicates), maintains correct role ordering, and handles message updates. A plain `add` would blindly append everything including duplicates, which would corrupt the conversation history and confuse the LLM.

4. **If a node returns a field that doesn't exist in the state schema, what happens?**
   > LangGraph raises a validation error — nodes can only return updates for fields declared in the state schema. This is another benefit of TypedDict: it creates a strict contract between nodes and state. This prevents nodes from accidentally polluting state with arbitrary data.

### Critical Thinking

1. **A senior developer says "just make state a global variable, it's simpler." What's wrong with that approach in an LLM workflow?**
   > Global state breaks parallelism — two parallel nodes writing to a global variable at the same time creates race conditions and non-deterministic results. It also breaks resumability: checkpointing works by snapshotting state at each step, which only works if state is an explicit, serializable object passed through the graph. Global variables can't be checkpointed or resumed. LangGraph's explicit state passing is what makes all its advanced features possible.

2. **You have a parallel workflow where 5 nodes each append to a `results` list. After execution, the list has only 3 items. What's the most likely cause?**
   > The reducer is missing or wrong. Without `Annotated[List, add]` on the `results` field, each node's return value replaces the previous one — so only the last 3 nodes to write (or however the timing works out) survive. The fix is adding the correct append reducer to the `results` field in the state schema.

3. **When would you choose a custom reducer over the built-in `add` reducer for a list field?**
   > When you need merge logic beyond simple concatenation — for example: deduplication (don't add if the item already exists), bounded lists (keep only the last N items), sorted insertion, or conditional merging (only add if a confidence score exceeds a threshold). The built-in `add` just concatenates; any business logic in the merge requires a custom reducer.

### Scenario-Based

1. **You're building a research agent where 4 parallel nodes each return search results. How do you design the state to correctly capture all results?**
   > Define the state field as `results: Annotated[List[str], add]`. Each parallel node returns `{"results": [its_own_results]}`. LangGraph calls the `add` reducer for each update, concatenating lists so no results are lost. Without the `Annotated` reducer, you'd get only the last node's results.

2. **In a multi-turn chatbot, a bug causes the same assistant message to appear twice in the conversation history. What's the likely cause and fix?**
   > The likely cause is using a plain `add` reducer instead of `add_messages`. Plain `add` appends every message unconditionally, so if a message is emitted twice (e.g., due to a retry or a graph re-execution), it appears twice. The fix is switching to `add_messages`, which deduplicates by message ID so re-emitting the same message is idempotent.

3. **You're designing state for an Evaluator-Optimiser workflow. The evaluator must see all previous drafts and scores, not just the latest. How do you model the state?**
   > Use append reducers: `drafts: Annotated[List[str], add]` and `scores: Annotated[List[float], add]`. Each generator iteration appends its new draft; each evaluator appends its score. The evaluator node can then read the full history (`state["scores"]`) to detect convergence or stagnation, rather than just comparing against the single latest score.

---

*Studied: 2026-04-24*
