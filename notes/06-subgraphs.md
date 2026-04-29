# Subgraphs in LangGraph

## What Are Subgraphs?

A **subgraph** is a compiled graph that functions as a node within another graph. It enables modular, reusable workflow design.

```
Parent Graph
┌────────────────────────────────────────────────┐
│                                                │
│  [Node A] → [Subgraph as Node] → [Node B]      │
│                    │                           │
│              ┌─────┴─────┐                     │
│              │ Child Graph│                    │
│              │ [X] → [Y]  │                    │
│              └───────────┘                     │
│                                                │
└────────────────────────────────────────────────┘
```

## Why Use Subgraphs?

| Use Case | Description |
|----------|-------------|
| **Multi-agent systems** | Multiple specialized agents collaborating, each as a subgraph |
| **Code reusability** | Reuse node collections across different graphs |
| **Distributed development** | Teams develop graph components independently |
| **Modularity** | Break complex workflows into manageable pieces |
| **Encapsulation** | Hide internal complexity, expose clean interfaces |

## Two Communication Patterns

### Pattern 1: Different State Schemas (Wrapper Function)

Use when parent and subgraph have **different state schemas** with no overlapping keys.

```python
from typing import TypedDict
from langgraph.graph import StateGraph, START, END

# Parent state
class ParentState(TypedDict):
    user_input: str
    final_result: str

# Subgraph state (different schema)
class SubgraphState(TypedDict):
    query: str
    response: str

# Build subgraph
def process_query(state: SubgraphState):
    return {"response": f"Processed: {state['query']}"}

subgraph_builder = StateGraph(SubgraphState)
subgraph_builder.add_node("process", process_query)
subgraph_builder.add_edge(START, "process")
subgraph_builder.add_edge("process", END)
subgraph = subgraph_builder.compile()

# Wrapper function transforms state between parent and child
def call_subgraph(state: ParentState):
    # Transform parent state → subgraph input
    subgraph_input = {"query": state["user_input"]}
    
    # Invoke subgraph
    subgraph_output = subgraph.invoke(subgraph_input)
    
    # Transform subgraph output → parent state update
    return {"final_result": subgraph_output["response"]}

# Parent graph uses wrapper as node
parent_builder = StateGraph(ParentState)
parent_builder.add_node("subgraph_node", call_subgraph)
parent_builder.add_edge(START, "subgraph_node")
parent_builder.add_edge("subgraph_node", END)
parent_graph = parent_builder.compile()

# Use
result = parent_graph.invoke({"user_input": "Hello"})
# result["final_result"] = "Processed: Hello"
```

### Pattern 2: Shared State Schema (Direct Node)

Use when parent and subgraph **share state keys**. Pass compiled subgraph directly to `add_node()`.

```python
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

# Shared state schema
class SharedState(TypedDict):
    messages: Annotated[list, add_messages]
    context: str

# Build subgraph with same state schema
def subgraph_node(state: SharedState):
    return {"messages": [("assistant", f"Subgraph received: {state['context']}")]}

subgraph_builder = StateGraph(SharedState)
subgraph_builder.add_node("process", subgraph_node)
subgraph_builder.add_edge(START, "process")
subgraph_builder.add_edge("process", END)
subgraph = subgraph_builder.compile()

# Parent graph - subgraph added directly (no wrapper needed)
def prepare_context(state: SharedState):
    return {"context": "Some context data"}

parent_builder = StateGraph(SharedState)
parent_builder.add_node("prepare", prepare_context)
parent_builder.add_node("child_graph", subgraph)  # Direct add
parent_builder.add_edge(START, "prepare")
parent_builder.add_edge("prepare", "child_graph")
parent_builder.add_edge("child_graph", END)
parent_graph = parent_builder.compile()
```

## When to Use Which Pattern

| Scenario | Pattern | Reason |
|----------|---------|--------|
| Different teams with different schemas | Wrapper function | Need explicit transformation |
| Multi-agent with shared messages | Direct node | Agents communicate via same state |
| Reusing existing graph with different state | Wrapper function | Adapt interface |
| Child needs subset of parent state | Either | Shared keys work directly |

## Nested Subgraphs

Subgraphs can contain subgraphs (grandchild → child → parent).

```python
# Level 3: Grandchild
class GrandchildState(TypedDict):
    value: int

def grandchild_node(state: GrandchildState):
    return {"value": state["value"] * 2}

grandchild_builder = StateGraph(GrandchildState)
grandchild_builder.add_node("double", grandchild_node)
grandchild_builder.add_edge(START, "double")
grandchild_builder.add_edge("double", END)
grandchild = grandchild_builder.compile()

# Level 2: Child (calls grandchild)
class ChildState(TypedDict):
    number: int

def call_grandchild(state: ChildState):
    result = grandchild.invoke({"value": state["number"]})
    return {"number": result["value"]}

child_builder = StateGraph(ChildState)
child_builder.add_node("process", call_grandchild)
child_builder.add_edge(START, "process")
child_builder.add_edge("process", END)
child = child_builder.compile()

# Level 1: Parent (calls child)
class ParentState(TypedDict):
    input_num: int
    output_num: int

def call_child(state: ParentState):
    result = child.invoke({"number": state["input_num"]})
    return {"output_num": result["number"]}

parent_builder = StateGraph(ParentState)
parent_builder.add_node("compute", call_child)
parent_builder.add_edge(START, "compute")
parent_builder.add_edge("compute", END)
parent = parent_builder.compile()

# input_num: 5 → grandchild doubles → output_num: 10
```

## Subgraph Persistence

The `checkpointer` parameter controls subgraph state retention:

| Mode | Setting | Behavior |
|------|---------|----------|
| **Per-invocation** | `None` (default) | Each call starts fresh; inherits parent's checkpointer for interrupts |
| **Per-thread** | `True` | State accumulates across calls on same thread |
| **Stateless** | `False` | No checkpointing; operates like plain function calls |

```python
# Per-invocation (default) - fresh state each call
subgraph = subgraph_builder.compile()

# Per-thread - state persists across calls
subgraph = subgraph_builder.compile(checkpointer=True)

# Stateless - no checkpointing at all
subgraph = subgraph_builder.compile(checkpointer=False)
```

**Important**: Per-thread subgraphs do not support parallel tool calls due to checkpoint conflicts.

## Inspecting Subgraph State

With persistence enabled, inspect subgraph state:

```python
# Get state including subgraphs
state = parent_graph.get_state(config, subgraphs=True)

# state contains nested subgraph states
```

## Streaming Subgraph Outputs

Stream outputs from subgraphs with `subgraphs=True`:

```python
for chunk in parent_graph.stream(input, config, subgraphs=True):
    # chunk contains 'ns' (namespace) field
    # ns = () for root graph
    # ns = ("subgraph_node:uuid",) for subgraph
    print(f"Namespace: {chunk.get('ns', ())}")
    print(f"Data: {chunk}")
```

## Complete Example: Multi-Agent System

```python
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_aws import ChatBedrockConverse

# Shared state for all agents
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    task: str
    result: str

llm = ChatBedrockConverse(model="us.anthropic.claude-sonnet-4-6")

# Research Agent (subgraph)
def research_agent(state: AgentState):
    prompt = f"Research this topic and provide key facts: {state['task']}"
    response = llm.invoke([("user", prompt)])
    return {"messages": [response], "result": response.content}

research_builder = StateGraph(AgentState)
research_builder.add_node("research", research_agent)
research_builder.add_edge(START, "research")
research_builder.add_edge("research", END)
research_graph = research_builder.compile()

# Writer Agent (subgraph)
def writer_agent(state: AgentState):
    prompt = f"Write a summary based on this research: {state['result']}"
    response = llm.invoke([("user", prompt)])
    return {"messages": [response], "result": response.content}

writer_builder = StateGraph(AgentState)
writer_builder.add_node("write", writer_agent)
writer_builder.add_edge(START, "write")
writer_builder.add_edge("write", END)
writer_graph = writer_builder.compile()

# Orchestrator (parent graph)
def assign_task(state: AgentState):
    return {"task": state["messages"][-1].content}

orchestrator_builder = StateGraph(AgentState)
orchestrator_builder.add_node("assign", assign_task)
orchestrator_builder.add_node("researcher", research_graph)  # Subgraph as node
orchestrator_builder.add_node("writer", writer_graph)        # Subgraph as node

orchestrator_builder.add_edge(START, "assign")
orchestrator_builder.add_edge("assign", "researcher")
orchestrator_builder.add_edge("researcher", "writer")
orchestrator_builder.add_edge("writer", END)

orchestrator = orchestrator_builder.compile()

# Use
result = orchestrator.invoke({
    "messages": [("user", "Explain quantum computing")],
    "task": "",
    "result": ""
})
```

## Key Concepts Summary

| Concept | Description |
|---------|-------------|
| **Subgraph** | Compiled graph used as a node in another graph |
| **Wrapper function** | Transforms state between different schemas |
| **Direct node** | Add subgraph directly when schemas match |
| **Nested subgraphs** | Subgraphs containing subgraphs |
| **Namespace (ns)** | Identifies subgraph in streaming/state inspection |
| **Per-invocation** | Fresh subgraph state each call (default) |
| **Per-thread** | Subgraph state persists across calls |

---

## Interview Questions

### Conceptual

1. **Why would you use a wrapper function to call a subgraph instead of adding it directly as a node?**
   > When the parent and subgraph have different state schemas with no overlapping keys, you need a wrapper function to transform state bidirectionally. The wrapper converts parent state fields to subgraph input fields before invoking, and converts subgraph output back to parent state updates. Without matching schemas, direct node addition would fail because the subgraph can't read/write the parent's state channels.

2. **How does state flow differently between Pattern 1 (wrapper) and Pattern 2 (direct node)?**
   > In Pattern 1, the wrapper function explicitly extracts fields from parent state, passes them to the subgraph, and maps outputs back — complete control over transformation. In Pattern 2, the subgraph directly reads and writes shared state channels — the parent's state is the subgraph's state for overlapping keys. Pattern 2 is simpler but requires schema coordination; Pattern 1 is more flexible but requires explicit mapping.

3. **Why does per-thread subgraph persistence not support parallel tool calls?**
   > Per-thread persistence means the subgraph maintains state across invocations on the same thread_id. If parallel tool calls invoke the same subgraph simultaneously, they'd conflict on the same checkpoint — one call's writes could overwrite another's, or race conditions could corrupt state. The checkpointer can't distinguish between concurrent calls on the same thread. Use per-invocation (default) for parallel safety.

### Critical Thinking

1. **Your team has 3 specialized agents (research, analysis, writing) each developed independently with their own state schemas. How do you integrate them into a single workflow?**
   > Use wrapper functions for each agent subgraph. Each wrapper transforms the orchestrator's state into the agent's expected input format, invokes the agent, and maps the output back to orchestrator state. This preserves each team's schema independence while enabling composition. Define a clear contract: what each agent needs as input, what it produces as output. The orchestrator manages the global workflow state; wrappers handle translation at boundaries.

2. **When would you choose subgraphs over just putting all nodes in a single flat graph?**
   > Choose subgraphs for: (1) Reusability — use the same agent logic in multiple parent graphs, (2) Team boundaries — different teams own different subgraphs, (3) Testing — test subgraphs in isolation, (4) Encapsulation — hide internal complexity, expose clean interface, (5) Dynamic composition — conditionally include different subgraphs based on runtime logic. Flat graphs are simpler for small workflows; subgraphs add value when modularity, reuse, or team independence matters.

3. **A subgraph works perfectly in isolation but produces wrong results when embedded in a parent graph. What could be wrong?**
   > Common causes: (1) State schema mismatch — subgraph expects keys that parent doesn't provide or provides differently, (2) Reducer conflicts — parent and subgraph define different reducers for same key, (3) State initialization — parent doesn't initialize fields subgraph expects, (4) Checkpointer interaction — per-thread persistence causing state bleed between calls, (5) State transformation bug in wrapper — mapping logic is incorrect. Debug by logging state at subgraph entry/exit and comparing with isolated runs.

### Scenario-Based

1. **You're building a document processing pipeline where different document types (PDF, Word, Excel) need different processing logic. How would you structure this with subgraphs?**
   > Create a subgraph for each document type (pdf_processor, word_processor, excel_processor), each with its own specialized nodes. The parent graph has a classifier node that routes to the appropriate subgraph using conditional edges. If schemas differ (PDF needs page numbers, Excel needs sheet names), use wrapper functions. If they share a common schema (all produce "extracted_text"), add subgraphs directly. This keeps processing logic isolated and testable per document type.

2. **Your multi-agent system has a researcher agent that sometimes needs to call a fact-checker agent recursively. How do you implement this?**
   > The researcher subgraph contains a conditional edge that routes to a fact-checker subgraph when claims need verification. The fact-checker is nested inside the researcher. Use shared state schema so the fact-checker can access research findings and append verification results. Add a recursion limit check in the routing function to prevent infinite loops — if depth exceeds N, skip fact-checking. This is a nested subgraph pattern where the child (researcher) contains a grandchild (fact-checker).

3. **You want to reuse an existing "summarization" subgraph that expects `{text: str, summary: str}` in a parent graph that uses `{document: str, abstract: str}`. How do you integrate it?**
   > Create a wrapper function that transforms state: extract `document` from parent state, pass as `text` to subgraph, invoke the summarizer, then map subgraph's `summary` output to parent's `abstract` field. The subgraph remains unchanged — the wrapper is the adapter. This is the key benefit of Pattern 1: you can reuse existing graphs without modifying them, just wrap them with appropriate state transformation.

---

*Studied: 2026-04-29*
