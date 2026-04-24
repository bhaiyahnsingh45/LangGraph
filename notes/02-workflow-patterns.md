# LLM Workflow Patterns

Common patterns for building LLM workflows with LangGraph.

## 1. Prompt Chaining

**Definition**: Multiple sequential LLM calls where outputs feed into subsequent calls.

**Use Case**: Generating detailed content step-by-step.

```
[Input] → [LLM: Create Outline] → [LLM: Expand Section 1] → [LLM: Expand Section 2] → [Output]
```

**Example**: Report generation
1. First call: Generate outline
2. Second call: Expand each section
3. Third call: Polish and format

```python
def create_outline(state):
    outline = llm.invoke(f"Create outline for: {state['topic']}")
    return {"outline": outline}

def expand_content(state):
    content = llm.invoke(f"Expand this outline: {state['outline']}")
    return {"content": content}

graph.add_edge(START, "create_outline")
graph.add_edge("create_outline", "expand_content")
graph.add_edge("expand_content", END)
```

## 2. Routing

**Definition**: Decision-making to route tasks to the most appropriate handler based on input.

**Use Case**: Customer support chatbot routing queries.

```
                    ┌→ [Refund Handler]
[Input] → [Router] ─┼→ [Technical Support]
                    └→ [Sales Team]
```

**Example**: Support ticket routing

```python
def router(state):
    query = state["query"].lower()
    if "refund" in query:
        return "refund_handler"
    elif "error" in query or "bug" in query:
        return "technical_support"
    else:
        return "sales_team"

graph.add_conditional_edges(
    "classifier",
    router,
    {
        "refund_handler": "handle_refund",
        "technical_support": "handle_technical",
        "sales_team": "handle_sales"
    }
)
```

## 3. Parallelisation

**Definition**: Breaking a task into multiple subtasks executed in parallel, merging results later.

**Use Case**: Content moderation checking multiple aspects simultaneously.

```
              ┌→ [Check Guidelines] ─┐
[Input] → [Fan Out] → [Check Misinfo] → [Merge] → [Output]
              └→ [Check Content]   ─┘
```

**Example**: YouTube content moderation

```python
# Parallel nodes execute simultaneously
def check_guidelines(state):
    return {"guideline_score": analyze_guidelines(state["content"])}

def check_misinformation(state):
    return {"misinfo_score": analyze_misinfo(state["content"])}

def check_inappropriate(state):
    return {"inappropriate_score": analyze_content(state["content"])}

def merge_results(state):
    scores = [state["guideline_score"], state["misinfo_score"], state["inappropriate_score"]]
    return {"final_decision": "approved" if all(s > 0.8 for s in scores) else "rejected"}
```

## 4. Orchestrator-Worker

**Definition**: Like parallelisation but with **dynamic task assignment** - tasks not predetermined.

**Use Case**: Research assistant that searches different platforms based on query type.

```
[Query] → [Orchestrator] → [Dynamically Assign Workers] → [Aggregate] → [Output]
```

**Key Difference from Parallelisation**:
- Parallelisation: Fixed subtasks known in advance
- Orchestrator-Worker: Tasks determined at runtime

**Example**: Research assistant

```python
def orchestrator(state):
    query = state["query"]
    # Dynamically decide which sources to search
    sources = llm.invoke(f"Which sources should I search for: {query}")
    return {"assigned_sources": sources}

def worker(state):
    # Execute searches based on assigned sources
    results = []
    for source in state["assigned_sources"]:
        results.append(search(source, state["query"]))
    return {"search_results": results}
```

## 5. Evaluator-Optimiser

**Definition**: Iterative workflow where a generator produces solutions and an evaluator assesses them, looping until quality threshold met.

**Use Case**: Drafting emails, blog posts, creative writing with iterative refinement.

```
[Input] → [Generator] → [Evaluator] → (Score < Threshold?) → [Loop Back to Generator]
                                    → (Score >= Threshold?) → [Output]
```

**Example**: Blog post generation

```python
def generator(state):
    if state.get("feedback"):
        prompt = f"Improve this based on feedback: {state['draft']}\nFeedback: {state['feedback']}"
    else:
        prompt = f"Write a blog post about: {state['topic']}"
    draft = llm.invoke(prompt)
    return {"draft": draft}

def evaluator(state):
    evaluation = llm.invoke(f"Rate this draft 1-10 and provide feedback: {state['draft']}")
    score = extract_score(evaluation)
    feedback = extract_feedback(evaluation)
    return {"score": score, "feedback": feedback}

def should_continue(state):
    if state["score"] >= 8:
        return "end"
    return "generator"  # Loop back

graph.add_conditional_edges("evaluator", should_continue, {"generator": "generator", "end": END})
```

## Pattern Comparison Table

| Pattern | Task Assignment | Execution | Use When |
|---------|-----------------|-----------|----------|
| **Prompt Chaining** | Sequential, fixed | One at a time | Multi-step content generation |
| **Routing** | Conditional, single path | One handler | Different query types need different handlers |
| **Parallelisation** | Fixed, multiple | Concurrent | Independent subtasks known upfront |
| **Orchestrator-Worker** | Dynamic, multiple | Concurrent | Subtasks determined at runtime |
| **Evaluator-Optimiser** | Iterative | Loop | Quality improvement through feedback |

---

*Studied: 2026-04-24*
