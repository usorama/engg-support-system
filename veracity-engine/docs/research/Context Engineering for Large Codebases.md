# **The Architecture of Intentional Compaction: Context Engineering and Agentic Workflows for Large-Scale Software Modification**

## **1\. The Context Efficiency Paradox in Brownfield Software Engineering**

### **1.1 The Failure of the "God Model" in Legacy Environments**

The trajectory of Large Language Model (LLM) development has been defined by an aggressive expansion of context windows, moving from the restrictive 4,096 tokens of early GPT architectures to the effective infinity of cached context in modern frontier models like Gemini 1.5 Pro and Claude 3.5 Sonnet. This expansion was predicated on the assumption that "more context equals better understanding." In the domain of software engineering, this hypothesis suggested that feeding an entire codebase into a model’s context would fundamentally solve the problem of autonomous coding.

However, empirical evidence from large-scale deployments—specifically in "brownfield" or legacy environments—contradicts this assumption. As context windows expand, the reasoning capabilities of models do not scale linearly. Instead, engineers encounter a phenomenon described by Dex Horthy of HumanLayer as the "Dumb Zone".1 This zone, typically emerging in the middle 40-60% of a saturated context window, represents a catastrophic degradation in the model's ability to retrieve specific instructions, adhere to negative constraints, and maintain logical consistency over long horizons.2

The underlying mechanism of this failure is rooted in the attention mechanisms of Transformer architectures. While models can theoretically "attend" to millions of tokens, the "Semantic Diffusion" caused by the sheer volume of irrelevant implementation details dilutes the signal of the user's intent. In a codebase of 300,000 lines, feeding the entire repository into the context does not empower the model; it paralyzes it. The model becomes overwhelmed by the noise of ten thousand variable declarations, resulting in hallucinations where it invents interfaces that "should" exist based on semantic patterns but do not exist in the actual graph of the code.1

Therefore, the frontier of AI software engineering has shifted from maximizing context volume to optimizing **Context Engineering**. This discipline is not merely prompt engineering (instruction optimization) but rather the architectural curation of the information state. It is the science of "Intentional Compaction"—the deliberate reduction of context to the absolute minimum required for a specific unit of work, ensuring that the model operates exclusively in its "Smart Zone" (the first 10-20% of context capacity) where instruction following is most robust.2

### **1.2 The "Cousin Problem" in Naive Retrieval Augmented Generation (RAG)**

To address context limits, early solutions adopted Retrieval Augmented Generation (RAG) using vector embeddings. This approach chunks code into text segments, embeds them into a high-dimensional vector space, and retrieves segments based on cosine similarity to a user's query. While effective for unstructured natural language (e.g., querying a wiki), naive RAG is fundamentally flawed for software engineering due to the "Cousin Problem".5

Code is not defined by semantic similarity but by functional dependency. A vector search for "User Authentication" might return every file containing the word "User" or "Auth"—including mock tests, documentation, and unrelated frontend components (the "cousins"). However, it may fail to retrieve the critical base class or the utility function defined in a separate file that strictly governs the authentication logic (the "parent" or "collaborator"), simply because those files use different variable names or lack the specific keywords in the query.5

The result is a context window filled with semantically similar but structurally irrelevant noise. The model sees five different implementations of a User class (production, test, legacy, migration) and hallucinates a hybrid implementation that breaks the build. To solve problems in large codebases, we must move beyond semantic retrieval to **Structural Context Engineering**, utilizing the inherent graph topology of source code.

## **2\. Structural Context Engineering: The Repository Map Algorithm**

The most proven solution to the context selection problem in large codebases is the **Repository Map**, a technique pioneered in the Aider framework and increasingly adopted in advanced agentic workflows. The Repository Map is not a simple file listing; it is a compressed, algorithmically ranked representation of the codebase's Abstract Syntax Tree (AST) and dependency graph.7

The objective of the Repository Map is to fit the "skeleton" of a massive repository into a strict token budget (typically 1,024–2,048 tokens) while preserving the critical relationships between files. This allows the LLM to "see" the entire architecture and hallucinate less, as it can reference the exact signatures of methods in files it hasn't fully read.

### **2.1 Stage 1: Polyglot AST Parsing via Tree-sitter**

The foundation of the Repository Map is deterministic static analysis, not probabilistic NLP. The system utilizes **Tree-sitter**, a high-performance parsing library, to generate concrete syntax trees for code in over 100 languages.9

Unlike Regex-based tools (like ctags), Tree-sitter understands the grammar of the language. It can differentiate between a variable definition, a function call, and a class inheritance. For every file in the repository, the context engine executes the following extraction process:

1. **Definition Extraction:** The parser identifies every "definitional" node (classes, functions, methods, global variables) and extracts its identifier, type signature, and docstring skeleton.  
2. **Reference Extraction:** The parser scans the function bodies to identify "reference" nodes—identifiers that call or access definitions located *outside* the current scope.9

This decoupling of definitions and references is the raw material for graph construction. It transforms the codebase from a bag of words into a structured dataset of symbols.

### **2.2 Stage 2: Dependency Graph Construction**

Once the symbols are extracted, the system constructs a Multi-Directed Graph using a library such as networkx.8

* **Nodes:** Represent source files within the repository.  
* **Edges:** Represent the dependency strength between files. If File A imports File B and calls three functions defined in File B, the edge weight from A to B increases.

This graph represents the "Connectome" of the application. In large legacy codebases, this graph reveals the "Hub" files—the core utilities, base classes, or configuration files that are referenced by a vast number of other components. These hubs are critical context; without them, the model cannot understand the code's foundational abstractions.6

### **2.3 Stage 3: Algorithmic Ranking via Personalized PageRank**

The crucial innovation in modern Context Engineering is the application of the **PageRank** algorithm to this dependency graph. Standard PageRank identifies nodes (files) that are inherently important because they are referenced by other important nodes. However, for a coding agent, "importance" is relative to the task at hand. A "Database Config" file is globally important, but irrelevant if the user is asking about "CSS styling."

To solve this, the system employs **Personalized PageRank**, injecting a "Personalization Vector" or bias into the ranking algorithm based on the user's current session state.10

The Weighting Heuristics:  
The algorithm assigns probability masses to specific nodes to bias the graph traversal:

1. **Chat Files (50x Weight):** Files that the user has explicitly added to the chat session or is currently editing are given a massive weighting boost. The algorithm assumes that dependencies *of* these files are the most critical context to retrieve.7  
2. **Mentioned Files (10x Weight):** If the user's natural language query mentions a filename (e.g., "Fix the bug in auth.py"), that node receives a significant boost, creating a gravity well that pulls in its connected dependencies.10  
3. **Snake\_Case / CamelCase Matching:** If the user query contains string tokens that match identifiers in the code (e.g., "Check the authenticateUser function"), the files containing those definitions are boosted.10

**Insight:** This personalization vector dynamically reshapes the "center" of the repository map. If the user shifts focus from the backend to the frontend, the PageRank scores recalculate, and the Repository Map completely changes, dropping backend utilities and populating with UI components. This ensures the 1,024-token map is always "centered" on the problem space.

### **2.4 Stage 4: Token-Optimized Binary Search Packing**

The final stage is the compression or "compaction" of this ranked data into the context window. The system possesses a sorted list of files by relevance score. It then employs a binary search algorithm to determine the "cut-off" point.6

The system attempts to render the top $N$ files into a text block containing their compressed signatures (class names, method headers, types). It measures the token count of this text block using the specific tokenizer of the target LLM (e.g., tiktoken for GPT-4).

* If the token count \< Budget (e.g., 1024), it attempts to include more files.  
* If the token count \> Budget, it reduces the number of files.

This binary search ensures that the context window is utilized to its exact maximum capacity with the highest-quality structural data available, leaving zero wasted space.7

| Feature | Naive RAG (Embeddings) | Repository Map (Graph \+ PageRank) |
| :---- | :---- | :---- |
| **Context Source** | Semantic Similarity (Vector Space) | Structural Dependency (Call Graph) |
| **Granularity** | Text Chunks / Snippets | File Signatures / Interfaces |
| **Handling of "Hubs"** | Poor (Often misses widely used utilities) | Excellent (PageRank identifies hubs) |
| **Relevance Signal** | "Sounds like" the query | "Is connected to" the focus |
| **Hallucination Risk** | High (Mixes unrelated implementations) | Low (Provides ground-truth signatures) |
| **Computation Cost** | High (Embedding huge codebases) | Low (Incremental AST parsing) |

## **3\. The RPI Workflow: Solving the Temporal Context Problem**

While the Repository Map solves the spatial problem (what to put in context), the **Research-Plan-Implement (RPI)** workflow solves the temporal problem (when to put it there). This workflow serves as a counter-measure to the "Dumb Zone" by enforcing **Frequent Intentional Compaction**—the systematic flushing of context to maintain high reasoning capabilities.1

The RPI Loop is based on the insight that "Coding" is actually three distinct cognitive tasks—Investigation, Architecture, and Syntax Generation—that compete for attention in a single context window. By separating them into distinct phases with "Hard Stops" between them, we prevent context pollution.

### **3.1 Phase 1: Research (The Wide Context)**

Objective: Establish "Ground Truth" without modification.  
The Problem: Most users ask agents to "Fix the bug in X." The agent immediately guesses the fix based on training data, often hallucinating libraries or patterns that don't exist in the legacy repo.  
The RPI Solution: The Research phase strictly prohibits code modification. The agent is configured with read-only tools (grep, ls, read\_file, find\_symbol).2  
In this phase, the agent acts as a detective. It uses the Repository Map to navigate the graph. It follows imports, reads documentation, and inspects test cases. The context fills up with "messy" investigation: failed searches, large file dumps, and error logs.

**The Output Artifact:** The result of this phase is *not* code, but a "Research Summary" or "Context Dump." This is a concise markdown document summarizing the findings: "The authentication logic is handled in AuthService.ts, which calls a legacy API in LegacyConnector.java. The bug appears to be a timeout configuration in config.yaml."

**Crucial Step: The Hard Stop.** Once the research is complete, the context is considered "polluted." The agent has likely entered the Dumb Zone. The workflow dictates that this chat session is **terminated** or the context is explicitly cleared, carrying forward *only* the Research Summary.2

### **3.2 Phase 2: Plan (The Compaction Event)**

Objective: Synthesize intent into an atomic specification.  
The Logic: A reasoning model (like OpenAI o1 or Claude 3.5 Sonnet in "Architect" mode) is instantiated with a fresh context. It receives:

1. The User Query.  
2. The Research Summary (from Phase 1).  
3. The Repository Map (freshly generated).

The model's sole task is to generate a **Step-by-Step Implementation Plan** (often saved as plan.md or spec.md). This plan acts as the "source of truth" for the rest of the workflow. It must be explicit, listing exact file paths, method names, and verification steps (tests) for each change.15

The "Mental Alignment" Effect:  
This phase allows for human intervention. Reviewing a 20-line plan is exponentially faster than reviewing 2,000 lines of code. If the plan is "Modify User.java to add a field," the human can catch the architectural error: "No, User.java is generated code; you must modify the User.proto definition." This correction happens before any code is written, saving massive amounts of token costs and rework.4  
Format of the Plan (plan.md):  
The plan serves as a "Context Externalization" mechanism. It moves the state of the task out of the LLM's ephemeral RAM and into the file system.19

# **Implementation Plan: OAuth Upgrade**

## **Context**

Research indicates AuthService uses deprecated flow.

## **Steps**

1. \[ \] Create integration test tests/integration/oauth\_test.py to reproduce failure.  
2. \[ \] Modify src/config/auth\_config.py to add new provider fields.  
3. \[ \] Refactor src/services/AuthService.py to consume new config.  
4. \[ \] Run tests and verify.

### **3.3 Phase 3: Implement (The Deep Context)**

Objective: High-fidelity syntax generation.  
The Execution: The implementation agent starts with a fresh context. It loads only the plan.md and the specific file required for Step 1\.  
Because the context usage is extremely low (often \< 5% of the window), the model operates in the "Smart Zone." It does not need to remember why it is making the change (that was the Architect's job); it only needs to know how to write valid Python/Rust/Go syntax to satisfy the plan.1  
**The Loop:**

1. Read Step 1 from plan.md.  
2. Execute edits.  
3. Run Tests.  
4. Mark Step 1 as \[x\].  
5. **Clear Context.**  
6. Read Step 2...

This iterative context clearing prevents "Context Rot," where errors from Step 1 confuse the model during Step 5\. Each step is executed with peak cognitive clarity.20

## **4\. Multi-Agent Orchestration: The Architect-Editor Pattern**

To implement RPI effectively, we utilize the **Architect-Editor** pattern. This splits the cognitive load across two specialized agent personas, often using different underlying models optimized for their specific tasks.22

### **4.1 The Architect (The Reasoning Engine)**

* **Model Profile:** High reasoning capability, slower inference, higher cost. (e.g., OpenAI o1-preview, DeepSeek R1, Claude 3.5 Sonnet).  
* **System Prompt:** "You are a Software Architect. You do not write code. You analyze problems, review the codebase, and produce detailed implementation plans. You must anticipate edge cases and dependencies.".23  
* **Tools:** Read-only access to the codebase, access to the Repo Map.  
* **Output:** plan.md, architecture.md, or natural language instructions.

The Architect is responsible for "Semantic Consistency." It ensures that the proposed changes fit the existing design patterns of the large codebase. It effectively "simulates" the coding process in its head to find logical flaws before they are committed to code.23

### **4.2 The Editor (The Syntax Engine)**

* **Model Profile:** High speed, high token throughput, strict instruction following. (e.g., GPT-4o, Claude 3.5 Sonnet, DeepSeek V3).  
* **System Prompt:** "You are an Expert Developer. You are given a specific plan and a set of files. Your job is to implement the plan exactly. Follow the coding style of the existing file. Use the diff format to apply changes.".23  
* **Tools:** File editing (write/replace), Test execution.  
* **Constraint:** The Editor should not "question" the plan unless it encounters a compile error. Its job is execution, not deliberation.

### **4.3 Orchestrating the Handoff**

In a manual workflow, the user acts as the router. In an automated system (using LangGraph or Claude Code scripts), the handoff is managed via **State Objects** or **File Artifacts**.

File-Based Handoff (The HumanLayer Approach):  
This approach is robust because it creates persistent checkpoints.

1. **Architect** creates/updates plan.md.  
2. **System** pauses for Human Review (optional but recommended).  
3. **Editor** reads plan.md and executes the first unchecked item.  
4. **Editor** updates plan.md to mark the item complete.  
5. **Loop** continues until all items are checked.

This method allows the user to kill the process in the middle, modify the plan (e.g., "Skip step 3, it's unnecessary"), and resume the agent, which will pick up exactly where it left off. This is superior to in-memory state chains which are lost if the script crashes or the context window overflows.18

| Feature | Single Agent Mode | Architect-Editor Mode |
| :---- | :---- | :---- |
| **Cognitive Load** | High (Must plan & code simultaneously) | Distributed (Separation of Concerns) |
| **Context Usage** | Accumulates rapidly (Context Rot) | Partitioned (Fresh context per role) |
| **Model Selection** | Compromise (Generalist model) | Specialized (Reasoning vs. Coding models) |
| **Error Recovery** | Difficult (Model gets confused by its own errors) | Robust (Architect can re-plan if Editor fails) |
| **Latency** | Single pass (Fast start, slow finish due to errors) | Multi-pass (Slower start, faster valid completion) |

## **5\. Actionable Implementation Intelligence**

The following section details how to implement these strategies using current tools like Claude Code, Aider, or custom scripts. This actionable intelligence is project-agnostic and relies on the principles of context engineering discussed above.

### **5.1 Directory Structure for Context Management**

To professionalize the RPI workflow, introduce a .context or thoughts directory in the root of your large repository. This directory serves as the "Long Term Memory" for your agents, separate from the code and the git history.14

Recommended Structure:  
/project-root  
├──.context/  
│ ├── active\_plan.md \# The current task's RPI plan  
│ ├── research\_notes.md \# Dump of findings (transient)  
│ ├── architecture.md \# High-level patterns (read-only for agents)  
│ └── knowledge\_graph.md \# Manual notes on tricky dependencies  
├── src/  
├── tests/  
**Implementation Tactic:** Configure your agent's system prompt or .aider.conf.yml to *always* read .context/architecture.md into the read-only context. This ensures that every agent, regardless of the task, is aware of the "Golden Rules" of the repo (e.g., "Always use Result\<T\>," "Never commit secrets") without cluttering the prompt with every rule every time.17

### **5.2 The "Spec-File" Anchor Technique**

When working with Aider or Claude Code, you can artificially manipulate the Repository Map's ranking algorithm to focus on specific subsystems.

The Technique:  
Before starting a complex task, create a file named spec.md and list the file paths you suspect are involved.

# **Spec**

Relates to:

* src/auth/login.py  
* src/auth/user.py  
* src/db/connector.py  
  Feed this file to the agent first. The PageRank algorithm (specifically the "Mentioned Files" vector) will immediately identify these paths as high-value nodes (10x weight). Consequently, the Repository Map will "re-center" itself around the authentication subsystem, pulling in the relevant dependencies of login.py into the context window before you even ask the first question. This "primes" the graph for deep work.10

### **5.3 Automating the "Context Wash"**

To strictly enforce the RPI loop using Claude Code or Aider, you can script the "Context Wash." This prevents the lazy tendency to keep a chat session running for 4 hours until the model degrades into the Dumb Zone.

**Script Logic (Pseudo-code for a wrapper):**

Python

def run\_rpi\_loop(task):  
    \# Phase 1: Research  
    research\_agent \= Agent(role="Researcher", model="o1-preview")  
    research \= research\_agent.run(f"Research: {task}", tools=\[read\_only\])  
    save\_to\_file(".context/research.md", research)  
      
    \# Phase 2: Plan  
    \# CLEAR CONTEXT (New Session)  
    architect\_agent \= Agent(role="Architect", model="o1-preview")  
    plan \= architect\_agent.run(f"Create plan from.context/research.md", context\_files=\[".context/research.md"\])  
    save\_to\_file(".context/active\_plan.md", plan)  
      
    \# Phase 3: Implement Loop  
    steps \= parse\_plan(plan)  
    for step in steps:  
        \# CLEAR CONTEXT (New Session)  
        editor\_agent \= Agent(role="Editor", model="sonnet-3.5")  
        editor\_agent.run(f"Execute {step}", context\_files=\[".context/active\_plan.md", step.related\_files\])  
        run\_tests()

This script enforces the "Hard Stop" mechanically. The agent *cannot* hallucinate based on previous errors because it literally doesn't remember them—it only sees the clean Plan and the current Code.20

### **5.4 Prompt Templates for the RPI Roles**

**The Research Prompt:**

"You are a Research Analyst. Your goal is to understand the codebase to prepare for.

1. Use ls and grep to find relevant files.  
2. Read the files to understand the implementation.  
3. DO NOT generate code to fix the issue.  
4. Output a summary of the current state, including file paths, relevant function names, and potential risks.  
5. Identify any 'Hub' files that control the logic.".13

**The Architect Prompt (Planning):**

"You are a Senior Architect. Review the following Research Summary.  
Create a detailed plan.md for the user.  
Rules:

* Break the task into atomic steps.  
* Each step must be verifiable (e.g., 'Add test case', 'Run build').  
* Specify exactly which files to edit in each step.  
* If the research is insufficient, ask for more research (do not guess).".16

**The Editor Prompt (Implementation):**

"You are a Code Editor. You are implementing Step 3 of .context/active\_plan.md.

* The plan says:.  
* Context: I have added to your session.  
* Action: specific diff edits to fulfill the step.  
* Constraint: Do not refactor unrelated code. Stick strictly to the plan.".23

## **6\. Benchmarks and Empirical Validation**

The shift from "God Model" contexts to Structural Context Engineering is supported by significant performance data.

### **6.1 SWE-bench Performance**

On the SWE-bench benchmark (a standard for evaluating LLMs on real-world GitHub issues), Aider—which utilizes the Repository Map and PageRank architecture—scored 26.3% on SWE-bench Lite. This was a state-of-the-art result, significantly outperforming systems that relied on standard RAG or massive context windows without structural filtering.27  
Notably, Aider achieved a 70.3% success rate in simply identifying the correct file to edit. This validates the efficacy of the PageRank algorithm in navigating the dependency graph to find the "needle" in the haystack.28

### **6.2 The Cost of Naive Context**

Analysis of "Dumb Zone" performance indicates that once the context window exceeds 60% saturation with "noise" tokens (irrelevant code), the model's ability to follow complex negative constraints (e.g., "Do not remove the legacy handler") drops by over 40%.1  
In contrast, the RPI workflow keeps the active context usage typically below 20% (The "Smart Zone"), maintaining near-peak reasoning performance throughout the lifecycle of a complex feature implementation.

## **7\. Conclusion: The Future is Graph-Based and Agentic**

The solution to engineering in large, brownfield codebases is not to wait for a 10-million-token context window. The solution is **Intentional Compaction**.

1. **Map the Territory:** Use AST-based Repository Maps with PageRank to give the model "Peripheral Vision" without "Context Pollution."  
2. **Architect the Workflow:** Adopt the RPI loop to strictly separate the distinct cognitive tasks of researching, planning, and coding.  
3. **Enforce Compaction:** Mechanically force "Hard Stops" and context resets to keep the model in its "Smart Zone."

By treating the Context Window as a scarce, high-value resource rather than a dumping ground, engineers can deploy agents that are not just chatty assistants, but robust, architectural operators capable of navigating the most complex legacy systems.

---

**References cited in text:**.1

#### **Works cited**

1. No Vibes Allowed: Solving Hard Problems in Complex Codebases – Dex Horthy, HumanLayer \- YouTube, accessed on December 27, 2025, [https://www.youtube.com/watch?v=rmvDxxNubIg](https://www.youtube.com/watch?v=rmvDxxNubIg)  
2. State of AI Coding: Context, Trust, and Subagents \- Turing Post, accessed on December 27, 2025, [https://www.turingpost.com/p/aisoftwarestack](https://www.turingpost.com/p/aisoftwarestack)  
3. Context Engineering — What AI Builders Know That You Don't: 5 Counter-Intuitive Lessons from the Trenches | by Rajesh Godavarthi \- Medium, accessed on December 27, 2025, [https://medium.com/@rajesh.godavarthi/context-engineering-what-ai-builders-know-that-you-dont-5-counter-intuitive-lessons-from-the-8435308183ca](https://medium.com/@rajesh.godavarthi/context-engineering-what-ai-builders-know-that-you-dont-5-counter-intuitive-lessons-from-the-8435308183ca)  
4. Spec Driven Development (SDD) vs Plan Research Implement (PRI) using claude \- Reddit, accessed on December 27, 2025, [https://www.reddit.com/r/ClaudeAI/comments/1pkvque/spec\_driven\_development\_sdd\_vs\_plan\_research/](https://www.reddit.com/r/ClaudeAI/comments/1pkvque/spec_driven_development_sdd_vs_plan_research/)  
5. How to generate accurate LLM responses on large code repositories: Presenting CGRAG, a new feature of dir-assistant | by Chase Adams | Medium, accessed on December 27, 2025, [https://medium.com/@djangoist/how-to-create-accurate-llm-responses-on-large-code-repositories-presenting-cgrag-a-new-feature-of-e77c0ffe432d](https://medium.com/@djangoist/how-to-create-accurate-llm-responses-on-large-code-repositories-presenting-cgrag-a-new-feature-of-e77c0ffe432d)  
6. An Exploratory Study of Code Retrieval Techniques in Coding Agents \- Preprints.org, accessed on December 27, 2025, [https://www.preprints.org/manuscript/202510.0924/v1](https://www.preprints.org/manuscript/202510.0924/v1)  
7. Repository map \- Aider, accessed on December 27, 2025, [https://aider.chat/docs/repomap.html](https://aider.chat/docs/repomap.html)  
8. RepoMapper: Your AI's GPS for Complex Codebases, accessed on December 27, 2025, [https://skywork.ai/skypage/en/repomapper-ai-gps-codebases/1980849506976722944](https://skywork.ai/skypage/en/repomapper-ai-gps-codebases/1980849506976722944)  
9. Building a better repository map with tree sitter \- Aider, accessed on December 27, 2025, [https://aider.chat/2023/10/22/repomap.html](https://aider.chat/2023/10/22/repomap.html)  
10. An Exploratory Study of Code Retrieval Techniques in Coding Agents \- Preprints.org, accessed on December 27, 2025, [https://www.preprints.org/manuscript/202510.0924/v1/download](https://www.preprints.org/manuscript/202510.0924/v1/download)  
11. Learn Aider: AI Coder \- TC blog, accessed on December 27, 2025, [https://www.tczhong.com/posts/llm/aider\_learning/](https://www.tczhong.com/posts/llm/aider_learning/)  
12. aider/repomap.py · main · external / Aider \- GitLab, accessed on December 27, 2025, [https://new.roya.tv/external/aider/-/blob/main/aider/repomap.py](https://new.roya.tv/external/aider/-/blob/main/aider/repomap.py)  
13. The Context Advantage \- Anup Jadhav, accessed on December 27, 2025, [https://www.anup.io/the-context-advantage/](https://www.anup.io/the-context-advantage/)  
14. Structured AI development framework for Claude Code. Research → Plan → Implement workflow with parallel agents, persistent context, and session management. \- GitHub, accessed on December 27, 2025, [https://github.com/brilliantconsultingdev/claude-research-plan-implement](https://github.com/brilliantconsultingdev/claude-research-plan-implement)  
15. Claude Code is a Beast – Tips from 6 Months of Hardcore Use : r/ClaudeAI \- Reddit, accessed on December 27, 2025, [https://www.reddit.com/r/ClaudeAI/comments/1oivjvm/claude\_code\_is\_a\_beast\_tips\_from\_6\_months\_of/](https://www.reddit.com/r/ClaudeAI/comments/1oivjvm/claude_code_is_a_beast_tips_from_6_months_of/)  
16. Set up a context engineering flow in VS Code, accessed on December 27, 2025, [https://code.visualstudio.com/docs/copilot/guides/context-engineering-guide](https://code.visualstudio.com/docs/copilot/guides/context-engineering-guide)  
17. Context Engineering:. A token-efficient SDLC. | by Atul Sakhala | Medium, accessed on December 27, 2025, [https://atulsakhala.medium.com/context-engineering-29f16a3d70ab](https://atulsakhala.medium.com/context-engineering-29f16a3d70ab)  
18. advanced-context-engineering-for-coding-agents/ace-fca.md at main \- GitHub, accessed on December 27, 2025, [https://github.com/humanlayer/advanced-context-engineering-for-coding-agents/blob/main/ace-fca.md](https://github.com/humanlayer/advanced-context-engineering-for-coding-agents/blob/main/ace-fca.md)  
19. Context Engineering: The Hidden Discipline Behind Smarter AI, accessed on December 27, 2025, [https://snehotoshbanerjee.medium.com/context-engineering-the-hidden-discipline-behind-smarter-ai-c505cb053e14](https://snehotoshbanerjee.medium.com/context-engineering-the-hidden-discipline-behind-smarter-ai-c505cb053e14)  
20. Spec Driven Development (SDD) vs Research Plan Implement (RPI) using claude \- Reddit, accessed on December 27, 2025, [https://www.reddit.com/r/aipromptprogramming/comments/1pkx8ky/spec\_driven\_development\_sdd\_vs\_research\_plan/](https://www.reddit.com/r/aipromptprogramming/comments/1pkx8ky/spec_driven_development_sdd_vs_research_plan/)  
21. claude-loop/README.md at main \- GitHub, accessed on December 27, 2025, [https://github.com/li0nel/claude-loop/blob/main/README.md](https://github.com/li0nel/claude-loop/blob/main/README.md)  
22. Chat modes | aider, accessed on December 27, 2025, [https://aider.chat/docs/usage/modes.html](https://aider.chat/docs/usage/modes.html)  
23. Separating code reasoning and editing | aider, accessed on December 27, 2025, [https://aider.chat/2024/09/26/architect.html](https://aider.chat/2024/09/26/architect.html)  
24. aider/aider/coders/architect\_coder.py at main \- GitHub, accessed on December 27, 2025, [https://github.com/paul-gauthier/aider/blob/main/aider/coders/architect\_coder.py](https://github.com/paul-gauthier/aider/blob/main/aider/coders/architect_coder.py)  
25. SWE-Fixer: Training Open-Source LLMs for Effective and Efficient GitHub Issue Resolution, accessed on December 27, 2025, [https://arxiv.org/html/2501.05040v3](https://arxiv.org/html/2501.05040v3)  
26. The only prompt template that made my AI Agents in n8n actually work every time \- Reddit, accessed on December 27, 2025, [https://www.reddit.com/r/n8n/comments/1l9zb4q/the\_only\_prompt\_template\_that\_made\_my\_ai\_agents/](https://www.reddit.com/r/n8n/comments/1l9zb4q/the_only_prompt_template_that_made_my_ai_agents/)  
27. Dissecting the SWE-Bench Leaderboards: Profiling Submitters and Architectures of LLM- and Agent-Based Repair Systems \- arXiv, accessed on December 27, 2025, [https://arxiv.org/html/2506.17208v2](https://arxiv.org/html/2506.17208v2)  
28. How aider scored SOTA 26.3% on SWE Bench Lite, accessed on December 27, 2025, [https://aider.chat/2024/05/22/swe-bench-lite.html](https://aider.chat/2024/05/22/swe-bench-lite.html)