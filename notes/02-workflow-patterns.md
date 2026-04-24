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

## Interview Questions

### Conceptual

1. **Why does Prompt Chaining use multiple LLM calls instead of one large prompt?**
   > Breaking a complex task into sequential steps allows each step to be optimised independently — different prompts, different models, different temperatures. A single large prompt forces the LLM to do everything at once, which degrades quality on complex tasks. Chaining also makes debugging easier: you can inspect the intermediate output at each step and pinpoint exactly where quality drops.

2. **How does the Orchestrator-Worker pattern handle a situation where the orchestrator decides zero workers are needed?**
   > If the orchestrator determines no workers are needed (e.g., the query is already answered), it can route directly to an aggregation or END node without spawning any workers. The dynamic nature of the pattern means the number of workers is always a runtime decision — zero is a valid outcome, unlike Parallelisation where the worker set is always fixed.

3. **In the Evaluator-Optimiser pattern, why should the evaluator be a separate node from the generator rather than bundled together?**
   > Separation of concerns — the generator's job is to produce content, the evaluator's job is to critique it. Bundling them means the same LLM is judging its own output, which introduces bias and reduces quality. A separate evaluator node can use a different prompt, a different model, or even a rule-based checker — and can be swapped or upgraded without touching the generator.

4. **Why can the Routing pattern break down if the classifier node uses keyword matching instead of an LLM?**
   > Keyword matching is brittle — "I want a refund for my broken device" contains neither "refund" nor "technical" as isolated keywords, so it would likely misroute. An LLM-based classifier understands intent, not just surface tokens, making it far more robust to phrasing variations. The routing pattern's reliability is entirely dependent on classifier quality.

### Critical Thinking

1. **When would you choose Orchestrator-Worker over Parallelisation, even though both involve concurrent execution?**
   > Choose Orchestrator-Worker when the subtasks can't be predetermined — the query itself determines which workers are needed and how many. For example, a research assistant might search academic papers for a scientific query but social media for a trends query. Parallelisation is better when you always need the same fixed set of checks (like content moderation), since it's simpler, faster, and more predictable.

2. **Prompt Chaining makes errors propagate downstream. How would you defend against this architecturally?**
   > Insert validation nodes between chaining steps. Each validation node checks the quality or format of the previous step's output — if it fails, it either triggers a retry loop or halts with a clear error. Alternatively, wrap critical chaining steps in an Evaluator-Optimiser sub-pattern so quality is guaranteed before passing output forward. The key principle: never let a bad output silently flow to the next step.

3. **Could you combine multiple patterns in a single LangGraph workflow? Give a concrete example.**
   > Yes, patterns are composable. For a writing assistant: use Routing to classify the content type (blog vs. email vs. report); use Prompt Chaining within each branch (outline → draft → format); use Evaluator-Optimiser to refine the draft; use Parallelisation to simultaneously run grammar and plagiarism checks on the final draft. LangGraph's graph structure naturally supports this layering since each pattern is just nodes and edges.

### Scenario-Based

1. **You're building a YouTube video moderation system that must check policy violations, misinformation, and spam simultaneously. How do you design this?**
   > Use Parallelisation. Define three independent nodes — `check_policy`, `check_misinformation`, `check_spam` — that all fan out from an initial `prepare` node and receive the same video content from state. Use an `Annotated` list reducer on a `flags` state field so all three write results without overwriting each other. A final `decide` node reads all flags and issues the moderation verdict.

2. **A content pipeline is slow because outline → draft → edit → proofread runs fully sequentially. How do you redesign it?**
   > Keep outline → draft sequential since each depends on the previous. But if edit and proofread are independent of each other (both just need the draft), run them in parallel as two sibling nodes that both read `draft` from state and write to separate fields. This cuts the critical path. For scale, also consider running the entire pipeline for multiple articles concurrently using a map-reduce subgraph.

3. **Your Evaluator-Optimiser loop has been running for 20 iterations and hasn't converged. How do you prevent this in your LangGraph design?**
   > Add a hard iteration cap in the routing function — if `state["iteration"] >= max_iterations`, route to END regardless of score. Also add a "diminishing returns" check: if the score hasn't improved over the last N iterations, exit early. Both conditions should be in the conditional edge function, not inside the generator or evaluator nodes, so they remain easy to tune without changing business logic.

---

*Studied: 2026-04-24*
