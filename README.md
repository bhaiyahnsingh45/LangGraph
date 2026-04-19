# LangGraph Applications

A repository for building AI agent applications using LangGraph - a low-level orchestration framework for stateful, long-running agents.

## What is LangGraph?

LangGraph is a framework for building, managing, and deploying long-running, stateful agents. It provides graph-based orchestration where you define workflows as nodes (processing units) connected by edges (control flow). Trusted by Klarna, Uber, and J.P. Morgan for production agent deployments.

**Inspired by**: Pregel and Apache Beam | **Interface influenced by**: NetworkX

## Installation

```bash
# Using pip
pip install -U langgraph

# Using uv
uv add langgraph
```

## Core Concepts

### Graph Components

| Component | Description |
|-----------|-------------|
| **StateGraph** | The main graph structure that holds nodes and edges |
| **Nodes** | Individual processing units that execute functions or logic |
| **Edges** | Connections defining flow between nodes (including conditional routing) |
| **State** | Data structure (e.g., `MessagesState`) that persists throughout execution |
| **START/END** | Special nodes marking entry and exit points of the graph |

### Basic Graph Structure

```python
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import MessagesState

# Define a node function
def process_message(state: MessagesState):
    # Your logic here
    return {"messages": [{"role": "assistant", "content": "Hello!"}]}

# Build the graph
graph = StateGraph(MessagesState)
graph.add_node("processor", process_message)
graph.add_edge(START, "processor")
graph.add_edge("processor", END)

# Compile and run
app = graph.compile()
result = app.invoke({"messages": [{"role": "user", "content": "Hi"}]})
```

## Key Features

### 1. Durable Execution
Agents persist through failures and can run for extended periods, resuming from where they left off.

```python
from langgraph.checkpoint.memory import MemorySaver

# Add checkpointing for persistence
memory = MemorySaver()
app = graph.compile(checkpointer=memory)

# Run with thread ID for persistence
config = {"configurable": {"thread_id": "user-123"}}
result = app.invoke({"messages": [...]}, config=config)
```

### 2. Human-in-the-Loop
Inspect and modify agent state at any point during execution.

```python
from langgraph.graph import StateGraph

graph = StateGraph(MessagesState)
# Add interrupt points for human review
app = graph.compile(
    checkpointer=memory,
    interrupt_before=["sensitive_action"]  # Pause before this node
)
```

### 3. Memory Architecture

**Short-term Memory**: Working memory for immediate reasoning within a session.

**Long-term Memory**: Persistent memory across multiple sessions.

```python
from langgraph.store.memory import InMemoryStore

# Long-term memory store
store = InMemoryStore()
app = graph.compile(checkpointer=memory, store=store)
```

### 4. Streaming Support
Built-in capabilities for handling continuous data flows.

```python
# Stream events as they happen
for event in app.stream({"messages": [...]}):
    print(event)

# Stream specific modes
for event in app.stream({"messages": [...]}, stream_mode="values"):
    print(event)
```

### 5. Conditional Routing
Dynamic edge routing based on state.

```python
def route_decision(state: MessagesState):
    if "error" in state:
        return "error_handler"
    return "continue"

graph.add_conditional_edges(
    "check_state",
    route_decision,
    {"error_handler": "handle_error", "continue": "next_step"}
)
```

## Application Patterns

### ReAct Agent (Reasoning + Acting)

```python
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4")
tools = [search_tool, calculator_tool]

agent = create_react_agent(llm, tools)
result = agent.invoke({"messages": [{"role": "user", "content": "What's 2+2?"}]})
```

### Chatbot with Memory

```python
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import MessagesState
from langgraph.checkpoint.memory import MemorySaver

def chatbot(state: MessagesState):
    response = llm.invoke(state["messages"])
    return {"messages": [response]}

graph = StateGraph(MessagesState)
graph.add_node("chatbot", chatbot)
graph.add_edge(START, "chatbot")
graph.add_edge("chatbot", END)

memory = MemorySaver()
app = graph.compile(checkpointer=memory)

# Conversations persist across invocations with same thread_id
config = {"configurable": {"thread_id": "conversation-1"}}
```

### Multi-Agent System

```python
from langgraph.graph import StateGraph

# Define specialized agent nodes
def researcher(state):
    # Research agent logic
    return {"research_results": "..."}

def writer(state):
    # Writer agent logic
    return {"draft": "..."}

def reviewer(state):
    # Reviewer agent logic
    return {"feedback": "..."}

# Build multi-agent workflow
graph = StateGraph(TeamState)
graph.add_node("researcher", researcher)
graph.add_node("writer", writer)
graph.add_node("reviewer", reviewer)

graph.add_edge(START, "researcher")
graph.add_edge("researcher", "writer")
graph.add_edge("writer", "reviewer")
graph.add_edge("reviewer", END)
```

### Tool-Calling Agent

```python
from langchain_core.tools import tool

@tool
def search(query: str) -> str:
    """Search the web for information."""
    return f"Results for: {query}"

@tool
def calculator(expression: str) -> str:
    """Evaluate a math expression."""
    return str(eval(expression))

tools = [search, calculator]
llm_with_tools = llm.bind_tools(tools)

def agent_node(state):
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}

def tool_node(state):
    # Execute tool calls from the last message
    tool_calls = state["messages"][-1].tool_calls
    results = []
    for call in tool_calls:
        tool = {"search": search, "calculator": calculator}[call["name"]]
        result = tool.invoke(call["args"])
        results.append({"role": "tool", "content": result, "tool_call_id": call["id"]})
    return {"messages": results}
```

### RAG (Retrieval-Augmented Generation)

```python
def retrieve(state):
    query = state["messages"][-1].content
    docs = retriever.invoke(query)
    return {"context": docs}

def generate(state):
    context = state["context"]
    question = state["messages"][-1].content
    response = llm.invoke(f"Context: {context}\n\nQuestion: {question}")
    return {"messages": [response]}

graph = StateGraph(RAGState)
graph.add_node("retrieve", retrieve)
graph.add_node("generate", generate)
graph.add_edge(START, "retrieve")
graph.add_edge("retrieve", "generate")
graph.add_edge("generate", END)
```

### Subgraphs

```python
# Define a subgraph
def build_inner_graph():
    inner = StateGraph(InnerState)
    inner.add_node("step1", step1_fn)
    inner.add_node("step2", step2_fn)
    inner.add_edge(START, "step1")
    inner.add_edge("step1", "step2")
    inner.add_edge("step2", END)
    return inner.compile()

# Use subgraph as a node in outer graph
outer = StateGraph(OuterState)
outer.add_node("subgraph", build_inner_graph())
outer.add_edge(START, "subgraph")
outer.add_edge("subgraph", END)
```

## State Management

### Custom State Schema

```python
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages

class CustomState(TypedDict):
    messages: Annotated[list, add_messages]  # Reducer for message handling
    context: str
    iteration_count: int

graph = StateGraph(CustomState)
```

### Reducers

```python
from operator import add

class CounterState(TypedDict):
    count: Annotated[int, add]  # Values are summed
    items: Annotated[list, lambda x, y: x + y]  # Lists are concatenated
```

## LangSmith Integration

For debugging, visualization, and production deployment:

```python
import os
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = "your-api-key"

# All graph executions are now traced in LangSmith
```

## Project Structure

```
LangGraph/
├── README.md
├── requirements.txt
├── src/
│   ├── agents/           # Agent implementations
│   ├── graphs/           # Graph definitions
│   ├── tools/            # Custom tools
│   ├── state/            # State schemas
│   └── utils/            # Utility functions
├── examples/
│   ├── chatbot.py
│   ├── react_agent.py
│   ├── multi_agent.py
│   ├── rag_agent.py
│   └── human_in_loop.py
└── tests/
```

## Quick Start

1. Clone this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up environment variables:
   ```bash
   export OPENAI_API_KEY="your-key"
   export LANGCHAIN_API_KEY="your-key"  # Optional, for LangSmith
   ```
4. Run an example:
   ```bash
   python examples/chatbot.py
   ```

## Resources

- [LangGraph Documentation](https://docs.langchain.com/oss/python/langgraph/)
- [LangSmith](https://smith.langchain.com/) - Observability and deployment
- [LangChain](https://docs.langchain.com/) - Integrations and components

## License

MIT
