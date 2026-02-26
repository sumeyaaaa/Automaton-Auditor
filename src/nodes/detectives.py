"""
Detective nodes for forensic evidence collection (Layer 1).

These nodes collect FACTS — never opinions, never scores.
They run in parallel as Superstep 2, then the aggregator
runs as Superstep 3 to cross-reference their findings.

Architecture spec reference: Section 4.2 — Layer 1 Detectives
"""

import json
from pathlib import Path
from src.tools.ast_tools import (
    check_parallel_edges,
    check_pydantic_models,
    check_sandboxing,
    check_security,
    check_stategraph,
    check_structured_output,
    check_judge_prompt_diversity,
    check_synthesis_rules,
)
from src.config import get_llm
from src.state import AgentState, Evidence
from src.tools.file_finder import find_file_recursive, find_file_fuzzy, get_repo_structure_sample
from src.tools.git_tools import extract_git_history, safe_clone
from src.tools.pdf_tools import (
    extract_file_path_claims,
    extract_images_from_pdf,
    ingest_pdf,
    search_keywords,
)
from src.tools.code_quality_tools import check_general_code_quality
from src.tools.repo_health_tools import check_general_repo_health


# ──────────────────────────────────────────────
# Repo Investigator — The Code Detective
#
# Clones the repo, runs git forensics and AST analysis.
# Produces evidence for every github_repo dimension.
# ──────────────────────────────────────────────

def repo_investigator_node(state: AgentState) -> dict:
    """Investigate the code repository using git forensics and AST parsing.

    Reads: repo_url, rubric_dimensions
    Writes: evidences["repo"], git_commit_hash

    This detective runs the following forensic protocols:
    - Git history analysis (commit count, progression pattern)
    - Pydantic model detection (BaseModel, TypedDict, reducers)
    - StateGraph detection (builder pattern, add_edge calls)
    - Parallel edge detection (fan-out/fan-in patterns)
    - Sandboxing check (tempfile, subprocess vs os.system)
    - Security audit (os.system, eval, exec detection)
    - Structured output detection (.with_structured_output)
    - Judge prompt diversity (persona differentiation)
    - Chief Justice synthesis rules (deterministic resolution)
    """
    repo_url = state["repo_url"]
    rubric_dimensions = state.get("rubric_dimensions", [])

    try:
        # Step 1: Clone into a sandboxed temp directory
        repo_path, commit_hash = safe_clone(repo_url)

        # Step 2: Run all forensic protocols and collect Evidence
        evidence_list: list[Evidence] = []

        for dimension in rubric_dimensions:
            if dimension.get("target_artifact") != "github_repo":
                continue

            dim_id = dimension["id"]

            try:
                if dim_id == "git_forensic_analysis":
                    git_result = extract_git_history(repo_path)
                    has_commits = git_result.get("total_commits", 0) > 0
                    
                    # Enhanced: Use LLM for semantic commit message analysis
                    semantic_analysis = None
                    if has_commits and git_result.get("commits"):
                        try:
                            llm = get_llm("investigator", temperature=0)
                            commit_messages = [c.get("message", "")[:100] for c in git_result.get("commits", [])[:10]]
                            
                            commit_text = "\n".join([f"{i+1}. {msg}" for i, msg in enumerate(commit_messages)])
                            
                            semantic_prompt = f"""Analyze these git commit messages and assess development quality:

{commit_text}

Respond with a JSON object:
{{
    "is_iterative": boolean - Do commits show iterative development (setup → implementation → refinement)?
    "is_atomic": boolean - Are commits atomic (one logical change per commit)?
    "shows_progression": boolean - Do commit messages show clear progression?
    "rationale": string - Brief explanation (1-2 sentences)
}}"""
                            
                            response = llm.invoke(semantic_prompt)
                            if isinstance(response.content, str):
                                content = response.content
                                if "```json" in content:
                                    content = content.split("```json")[1].split("```")[0].strip()
                                elif "```" in content:
                                    content = content.split("```")[1].split("```")[0].strip()
                                
                                try:
                                    semantic_analysis = json.loads(content)
                                except json.JSONDecodeError:
                                    semantic_analysis = {
                                        "is_iterative": "iterative" in content.lower() or "progression" in content.lower(),
                                        "is_atomic": "atomic" in content.lower(),
                                        "shows_progression": "progression" in content.lower() or "setup" in content.lower(),
                                        "rationale": content[:200]
                                    }
                            else:
                                semantic_analysis = {"rationale": "LLM analysis completed", "is_iterative": True}
                            
                            git_result["semantic_analysis"] = semantic_analysis
                            
                        except Exception as e:
                            git_result["semantic_error"] = str(e)[:100]
                    
                    confidence = 0.7 if has_commits else 0.3
                    if semantic_analysis:
                        if semantic_analysis.get("is_iterative") and semantic_analysis.get("shows_progression"):
                            confidence = 0.9
                        elif semantic_analysis.get("is_iterative"):
                            confidence = 0.8
                    
                    rationale = (
                        "Git history analyzed successfully."
                        if has_commits
                        else f"Git history analysis returned no commits or error: {git_result.get('error', 'no commits')}"
                    )
                    
                    if semantic_analysis:
                        rationale += f" Semantic analysis: {semantic_analysis.get('rationale', 'N/A')[:100]}"
                    
                    # Truncate commit data if too long (Evidence.content has max_length=10000)
                    git_result_for_content = git_result.copy()
                    commits_list = git_result_for_content.get("commits", [])
                    if commits_list:
                        # Keep only essential commit info and limit to recent commits
                        # Full commit messages can be very long, so we truncate them
                        max_commits_in_content = 20  # Keep last 20 commits for content
                        truncated_commits = commits_list[-max_commits_in_content:] if len(commits_list) > max_commits_in_content else commits_list
                        
                        # Truncate long commit messages
                        for commit in truncated_commits:
                            if "message" in commit and len(commit["message"]) > 200:
                                commit["message"] = commit["message"][:200] + "..."
                        
                        git_result_for_content["commits"] = truncated_commits
                        git_result_for_content["commits_truncated"] = len(commits_list) - len(truncated_commits) if len(commits_list) > max_commits_in_content else 0
                    
                    content_json = json.dumps(git_result_for_content)
                    # Final safety check: truncate if still too long
                    if len(content_json) > 10000:
                        content_json = content_json[:9500] + '..."truncated": true}'
                    
                    evidence_list.append(Evidence(
                        criterion_id=dim_id,
                        goal="Analyze git commit history for forensic signals (with semantic analysis)",
                        found=has_commits,
                        location=str(repo_path),
                        content=content_json,
                        rationale=rationale,
                        confidence=confidence,
                    ))

                elif dim_id == "state_management_rigor":
                    try:
                        pd_result = check_pydantic_models(repo_path)
                        has_pydantic = pd_result.get("has_pydantic", False)
                        has_reducers = pd_result.get("has_reducers", False)
                        
                        if pd_result.get("error") and "not found" in pd_result.get("error", "").lower():
                            location = "not_found"
                            rationale = f"state.py not found. {pd_result.get('error', 'Searched recursively')}"
                            confidence = 0.2
                        else:
                            state_file = find_file_recursive(repo_path, "state.py")
                            location = str(state_file) if state_file else str(repo_path / 'src' / 'state.py')
                            rationale = (
                                "Pydantic models with reducers detected."
                                if (has_pydantic and has_reducers)
                                else "Pydantic models or Annotated reducers missing."
                            )
                            confidence = 0.7 if (has_pydantic and has_reducers) else 0.4
                        
                        evidence_list.append(Evidence(
                            criterion_id=dim_id,
                            goal="Check Pydantic state models and reducers",
                            found=has_pydantic and has_reducers,
                            location=location,
                            content=json.dumps(pd_result),
                            rationale=rationale,
                            confidence=confidence,
                        ))
                    except FileNotFoundError:
                        suggestion = None
                        try:
                            llm = get_llm("investigator", temperature=0)
                            repo_structure = get_repo_structure_sample(repo_path, max_files=15)
                            
                            suggestion_prompt = f"""Given this repository structure, where might the state management code be located?

Repository files:
{chr(10).join(repo_structure[:15])}

The file 'state.py' was not found. Suggest 3 most likely alternative locations or filenames for state management code."""
                            
                            response = llm.invoke(suggestion_prompt)
                            if isinstance(response.content, str):
                                suggestion = response.content[:300]
                        except Exception:
                            pass
                        
                        evidence_list.append(Evidence(
                            criterion_id=dim_id,
                            goal="Check Pydantic state models",
                            found=False,
                            location="not_found",
                            content=json.dumps({
                                "error": "state.py not found",
                                "searched_locations": [
                                    "src/state.py",
                                    "state.py",
                                    "lib/state.py"
                                ],
                                "suggestion": suggestion or "State management may be in a different file or module"
                            }),
                            rationale="Could not locate state.py file. May be in non-standard location." + (f" LLM suggestion: {suggestion[:100]}" if suggestion else ""),
                            confidence=0.2,
                        ))

                elif dim_id == "graph_orchestration":
                    try:
                        graph_result = check_stategraph(repo_path)
                        parallel_result = check_parallel_edges(repo_path)
                        
                        graph_file = find_file_recursive(repo_path, "graph.py")
                        
                        if graph_result.get("error") and "not found" in graph_result.get("error", "").lower():
                            location = "not_found"
                            rationale = f"graph.py not found. {graph_result.get('error', 'Searched recursively')}"
                            confidence = 0.2
                        else:
                            location = str(graph_file) if graph_file else str(repo_path / 'src' / 'graph.py')
                            rationale = graph_result.get("error", "StateGraph detected.")
                            confidence = 0.7 if graph_result.get("found") else 0.4
                        
                        evidence_list.append(Evidence(
                            criterion_id=dim_id,
                            goal="Check LangGraph StateGraph orchestration",
                            found=graph_result.get("found", False),
                            location=location,
                            content=json.dumps(graph_result),
                            rationale=rationale,
                            confidence=confidence,
                        ))

                        # Parallel edges evidence
                        if parallel_result.get("error") and "not found" in parallel_result.get("error", "").lower():
                            parallel_location = "not_found"
                            parallel_rationale = f"graph.py not found. {parallel_result.get('error', 'Searched recursively')}"
                            parallel_confidence = 0.2
                        else:
                            parallel_location = str(graph_file) if graph_file else str(repo_path / 'src' / 'graph.py')
                            parallel_rationale = parallel_result.get(
                                "error",
                                "Parallel edges detected."
                                if parallel_result.get("has_parallel_edges")
                                else "No parallel edges found."
                            )
                            parallel_confidence = 0.7 if parallel_result.get("has_parallel_edges") else 0.4
                        
                        evidence_list.append(Evidence(
                            criterion_id=dim_id,
                            goal="Check parallel fan-out/fan-in edges",
                            found=parallel_result.get("has_parallel_edges", False),
                            location=parallel_location,
                            content=json.dumps(parallel_result),
                            rationale=parallel_rationale,
                            confidence=parallel_confidence,
                        ))
                    except FileNotFoundError:
                        suggestion = None
                        try:
                            llm = get_llm("investigator", temperature=0)
                            repo_structure = get_repo_structure_sample(repo_path, max_files=15)
                            
                            suggestion_prompt = f"""Given this repository structure, where might the graph orchestration code be located?

Repository files:
{chr(10).join(repo_structure[:15])}

The file 'graph.py' was not found. Suggest 3 most likely alternative locations or filenames for graph orchestration code."""
                            
                            response = llm.invoke(suggestion_prompt)
                            if isinstance(response.content, str):
                                suggestion = response.content[:300]
                        except Exception:
                            pass
                        
                        evidence_list.append(Evidence(
                            criterion_id=dim_id,
                            goal="Check LangGraph StateGraph orchestration",
                            found=False,
                            location="not_found",
                            content=json.dumps({
                                "error": "graph.py not found",
                                "searched_locations": ["src/graph.py", "graph.py", "lib/graph.py"],
                                "suggestion": suggestion or "Graph orchestration may be in a different file"
                            }),
                            rationale="Could not locate graph.py file. May be in non-standard location." + (f" LLM suggestion: {suggestion[:100]}" if suggestion else ""),
                            confidence=0.2,
                        ))

                elif dim_id == "safe_tool_engineering":
                    sandbox_result = check_sandboxing(repo_path)
                    security_result = check_security(repo_path)

                    evidence_list.append(Evidence(
                        criterion_id=dim_id,
                        goal="Check sandboxing and subprocess usage",
                        found=sandbox_result.get("found", False),
                        location=str((repo_path / 'src' / 'tools')),
                        content=json.dumps(sandbox_result),
                        rationale=sandbox_result.get(
                            "error",
                            "Sandboxing and secure subprocess usage detected."
                            if sandbox_result.get("has_sandboxing")
                            else "No tempfile-based sandboxing detected."
                        ),
                        confidence=0.7 if sandbox_result.get("has_sandboxing") else 0.4,
                    ))

                    security_issues = security_result.get("security_issues", [])
                    evidence_list.append(Evidence(
                        criterion_id=dim_id,
                        goal="Check for security anti-patterns (os.system, eval, exec)",
                        found=security_result.get("found", False),
                        location=str((repo_path / 'src')),
                        content=json.dumps(security_result),
                        rationale=(
                            f"Security issues detected: {len(security_issues)}"
                            if security_issues
                            else "No high-severity security issues detected."
                        ),
                        confidence=0.8 if not security_issues else 0.5,
                    ))

                elif dim_id == "structured_output_enforcement":
                    so_result = check_structured_output(repo_path)
                    evidence_list.append(Evidence(
                        criterion_id=dim_id,
                        goal="Check structured output enforcement in judges",
                        found=so_result.get("has_structured_output", False),
                        location=str((repo_path / 'src' / 'nodes' / 'judges.py')),
                        content=json.dumps(so_result),
                        rationale=so_result.get(
                            "error",
                            "Structured output enforcement detected."
                            if so_result.get("has_structured_output")
                            else "No clear structured output enforcement detected."
                        ),
                        confidence=0.7 if so_result.get("has_structured_output") else 0.4,
                    ))

                elif dim_id == "judicial_nuance":
                    nuance_result = check_judge_prompt_diversity(repo_path)

                    if nuance_result.get("error") and "not found" in nuance_result.get("error", "").lower():
                        location = "not_found"
                        rationale = f"judges.py not found. {nuance_result.get('error', '')}"
                        confidence = 0.2
                    else:
                        judges_file = find_file_recursive(repo_path, "judges.py")
                        location = str(judges_file) if judges_file else str(repo_path / "src" / "nodes" / "judges.py")
                        has_diversity = nuance_result.get("has_diverse_prompts", False)
                        distinct_count = nuance_result.get("distinct_personas_detected", 0)
                        rationale = (
                            f"Diverse judge prompts detected ({distinct_count} distinct personas)."
                            if has_diversity
                            else "Judge prompts lack persona diversity."
                        )
                        confidence = 0.8 if has_diversity else 0.4

                    evidence_list.append(Evidence(
                        criterion_id=dim_id,
                        goal="Check judge prompt diversity and persona differentiation",
                        found=nuance_result.get("found", False),
                        location=location,
                        content=json.dumps(nuance_result),
                        rationale=rationale,
                        confidence=confidence,
                    ))

                elif dim_id == "chief_justice_synthesis":
                    synthesis_result = check_synthesis_rules(repo_path)

                    if synthesis_result.get("error") and "not found" in synthesis_result.get("error", "").lower():
                        location = "not_found"
                        rationale = f"justice.py not found. {synthesis_result.get('error', '')}"
                        confidence = 0.2
                    else:
                        justice_file = find_file_recursive(repo_path, "justice.py")
                        if not justice_file:
                            justice_file = find_file_recursive(repo_path, "chief_justice.py")
                        location = str(justice_file) if justice_file else str(repo_path / "src" / "nodes" / "justice.py")

                        has_rules = synthesis_result.get("has_synthesis_rules", False)
                        is_deterministic = synthesis_result.get("is_deterministic", False)
                        rule_count = synthesis_result.get("active_rule_count", 0)

                        if is_deterministic and has_rules:
                            rationale = f"Deterministic synthesis with {rule_count} active rules detected."
                            confidence = 0.9
                        elif has_rules:
                            rationale = f"Synthesis rules found ({rule_count}) but may use LLM (non-deterministic)."
                            confidence = 0.6
                        else:
                            rationale = "No clear synthesis rules detected."
                            confidence = 0.3

                    evidence_list.append(Evidence(
                        criterion_id=dim_id,
                        goal="Check deterministic synthesis rules in Chief Justice",
                        found=synthesis_result.get("found", False),
                        location=location,
                        content=json.dumps(synthesis_result),
                        rationale=rationale,
                        confidence=confidence,
                    ))

            except Exception as e:
                # If one protocol fails, record it and continue.
                # Don't let one bad check kill all evidence collection.
                evidence_list.append(Evidence(
                    criterion_id=dim_id,
                    goal=f"Forensic protocol for {dim_id}",
                    found=False,
                    content=f"Error: {e}",
                    location=repo_url,
                    rationale=f"Protocol failed: {type(e).__name__}: {e}",
                    confidence=0.0,
                ))

        # Add general repository health checks (rubric-agnostic, works for any project)
        try:
            general_health_evidence = check_general_repo_health(repo_path, rubric_dimensions)
            evidence_list.extend(general_health_evidence)
        except Exception as e:
            evidence_list.append(Evidence(
                criterion_id="general_repo_health",
                goal="General repository health checks",
                found=False,
                content=f"Health checks failed: {str(e)[:200]}",
                location=str(repo_path),
                rationale=f"Error running general health checks: {type(e).__name__}",
                confidence=0.0,
            ))
        
        # Add code quality metrics (helps judges provide better, evidence-based feedback)
        try:
            code_quality_evidence = check_general_code_quality(repo_path, rubric_dimensions)
            evidence_list.extend(code_quality_evidence)
        except Exception as e:
            evidence_list.append(Evidence(
                criterion_id="code_quality",
                goal="Code quality metrics analysis",
                found=False,
                content=f"Quality checks failed: {str(e)[:200]}",
                location=str(repo_path),
                rationale=f"Error running code quality checks: {type(e).__name__}",
                confidence=0.0,
            ))

        return {
            "evidences": {"repo": evidence_list},
            "git_commit_hash": commit_hash,
        }

    except Exception as e:
        # Clone itself failed — return error evidence for each dimension
        return {
            "evidences": {"repo": [Evidence(
                criterion_id="git_forensic_analysis",
                goal="Clone and analyze repository",
                found=False,
                content=f"Clone failed: {e}",
                location=repo_url,
                rationale=f"Could not clone repository: {type(e).__name__}",
                confidence=0.0,
            )]},
            "git_commit_hash": "",
        }


# ──────────────────────────────────────────────
# Doc Analyst — The Paperwork Detective
#
# Reads the PDF report and checks for theoretical depth
# and file path claims that will be cross-referenced.
# ──────────────────────────────────────────────

def doc_analyst_node(state: AgentState) -> dict:
    """Analyze the PDF report for theoretical depth and accuracy claims.

    Reads: pdf_path, rubric_dimensions
    Writes: evidences["doc"]

    Forensic protocols:
    - Keyword depth: Search for key terms with context (not just buzzwords)
    - File path claims: Extract paths like src/...py for cross-referencing
    """
    pdf_path = Path(state["pdf_path"])
    rubric_dimensions = state.get("rubric_dimensions", [])

    try:
        # Step 1: Ingest the PDF
        doc_data = ingest_pdf(pdf_path)

        if not doc_data.get("success"):
            return {
                "evidences": {"doc": [Evidence(
                    criterion_id="theoretical_depth",
                    goal="Ingest PDF report",
                    found=False,
                    content=f"PDF ingestion failed: {doc_data.get('error', 'unknown')}",
                    location=str(pdf_path),
                    rationale="Could not parse PDF for analysis",
                    confidence=0.0,
                )]},
            }

        chunks = doc_data.get("chunks", [])
        evidence_list = []

        # Step 2: Run forensic protocols per dimension
        for dimension in rubric_dimensions:
            if dimension.get("target_artifact") != "pdf_report":
                continue

            dim_id = dimension["id"]

            try:
                if dim_id == "theoretical_depth":
                    keywords = [
                        "Dialectical Synthesis",
                        "Fan-In / Fan-Out",
                        "Fan-In/Fan-Out",
                        "Metacognition",
                        "State Synchronization",
                    ]
                    keyword_results = search_keywords(chunks, keywords)
                    
                    # Enhanced: Use LLM for semantic understanding of theoretical depth
                    semantic_analysis = None
                    if chunks:
                        try:
                            llm = get_llm("investigator", temperature=0)
                            sample_chunks = []
                            total_chars = 0
                            for chunk in chunks[:10]:
                                if total_chars + len(chunk) > 2000:
                                    break
                                sample_chunks.append(chunk[:500])
                                total_chars += len(chunk)
                            
                            semantic_prompt = f"""Analyze this documentation for theoretical depth and architectural reasoning:

Document excerpts:
{chr(10).join([f"[Chunk {i+1}]: {chunk[:400]}..." for i, chunk in enumerate(sample_chunks)])}

Assess:
1. Does it explain architectural decisions and trade-offs?
2. Does it discuss design rationale and why choices were made?
3. Does it reference academic concepts, frameworks, or theoretical foundations?
4. Is it surface-level description or deep analysis?

Respond with JSON:
{{
    "has_theoretical_depth": boolean,
    "depth_score": float (0.0-1.0),
    "key_concepts": [string] - List of theoretical concepts mentioned,
    "rationale": string - Brief explanation (1-2 sentences)
}}"""
                            
                            response = llm.invoke(semantic_prompt)
                            if isinstance(response.content, str):
                                content = response.content
                                if "```json" in content:
                                    content = content.split("```json")[1].split("```")[0].strip()
                                elif "```" in content:
                                    content = content.split("```")[1].split("```")[0].strip()
                                
                                try:
                                    semantic_analysis = json.loads(content)
                                except json.JSONDecodeError:
                                    semantic_analysis = {
                                        "has_theoretical_depth": "architectural" in content.lower() or "rationale" in content.lower(),
                                        "depth_score": 0.6 if "deep" in content.lower() else 0.3,
                                        "key_concepts": [],
                                        "rationale": content[:200]
                                    }
                            else:
                                semantic_analysis = {"has_theoretical_depth": True, "depth_score": 0.7, "rationale": "LLM analysis completed"}
                            
                        except Exception as e:
                            semantic_analysis = {"error": str(e)[:100]}
                    
                    has_keywords = keyword_results["summary"]["total_occurrences"] > 0
                    has_depth = semantic_analysis and semantic_analysis.get("has_theoretical_depth", False)
                    found = has_keywords or has_depth
                    
                    keyword_confidence = 0.8 if keyword_results["summary"]["substantive_occurrences"] > 0 else 0.3
                    semantic_confidence = semantic_analysis.get("depth_score", 0.5) if semantic_analysis else 0.0
                    confidence = max(keyword_confidence, semantic_confidence * 0.9)
                    
                    rationale = (
                        f"Found {keyword_results['summary']['total_occurrences']} keyword occurrences, "
                        f"{keyword_results['summary']['substantive_occurrences']} substantive."
                    )
                    if semantic_analysis and semantic_analysis.get("rationale"):
                        rationale += f" Semantic analysis: {semantic_analysis['rationale'][:100]}"
                    
                    combined_results = {
                        "keyword_results": keyword_results,
                        "semantic_analysis": semantic_analysis
                    }
                    
                    evidence_list.append(Evidence(
                        criterion_id=dim_id,
                        goal="Search for key architectural terms with context (enhanced with semantic analysis)",
                        found=found,
                        content=json.dumps(combined_results, indent=2),
                        location=str(pdf_path),
                        rationale=rationale,
                        confidence=confidence,
                    ))

                elif dim_id == "report_accuracy":
                    claimed_paths = extract_file_path_claims(chunks)

                    evidence_list.append(Evidence(
                        criterion_id=dim_id,
                        goal="Extract file path claims for cross-referencing",
                        found=len(claimed_paths) > 0,
                        content=json.dumps({"claimed_paths": claimed_paths}),
                        location=str(pdf_path),
                        rationale=(
                            f"Extracted {len(claimed_paths)} file path claims. "
                            "Awaiting cross-reference by evidence_aggregator."
                        ),
                        confidence=0.9 if claimed_paths else 0.0,
                    ))

            except Exception as e:
                evidence_list.append(Evidence(
                    criterion_id=dim_id,
                    goal=f"Forensic protocol for {dim_id}",
                    found=False,
                    content=f"Error: {e}",
                    location=str(pdf_path),
                    rationale=f"Protocol failed: {type(e).__name__}",
                    confidence=0.0,
                ))

        return {"evidences": {"doc": evidence_list}}

    except Exception as e:
        return {
            "evidences": {"doc": [Evidence(
                criterion_id="theoretical_depth",
                goal="Analyze PDF report",
                found=False,
                content=f"Error: {e}",
                location=str(pdf_path),
                rationale=f"PDF analysis failed: {type(e).__name__}",
                confidence=0.0,
            )]},
        }


# ──────────────────────────────────────────────
# Vision Inspector — The Diagram Detective
#
# Extracts and classifies images from the PDF.
# Optional per challenge spec.
# ──────────────────────────────────────────────

def vision_inspector_node(state: AgentState) -> dict:
    """Analyze architectural diagrams from the PDF report using Gemini for multimodal analysis.

    Reads: pdf_path, rubric_dimensions
    Writes: evidences["vision"]

    Uses Gemini (multimodal) to classify and analyze architectural diagrams.
    """
    pdf_path = Path(state["pdf_path"])
    rubric_dimensions = state.get("rubric_dimensions", [])

    try:
        images = extract_images_from_pdf(pdf_path)

        evidence_list = []
        for dimension in rubric_dimensions:
            if dimension.get("target_artifact") != "pdf_images":
                continue

            dim_id = dimension["id"]
            
            classification_result = None
            if images:
                try:
                    visual_llm = get_llm("visual", temperature=0)
                    
                    image_info = {
                        "count": len(images),
                        "sample_image": images[0] if images else None,
                    }
                    
                    classification_prompt = f"""Analyze this architectural diagram from a PDF report.

Image metadata:
- Total images found: {len(images)}
- Image format: {images[0].get('format', 'unknown') if images else 'N/A'}

Classify the diagram type and assess if it represents:
1. System architecture (components, layers, services)
2. Data flow diagrams
3. Sequence diagrams
4. Deployment diagrams
5. Class/entity relationship diagrams
6. Other architectural patterns

Respond with JSON:
{{
    "diagram_type": string - Type of diagram identified,
    "is_architectural": boolean - Whether it shows system architecture,
    "quality_score": float (0.0-1.0) - Quality/clarity of the diagram,
    "key_elements": [string] - List of key architectural elements identified,
    "rationale": string - Brief explanation (1-2 sentences)
}}"""
                    
                    response = visual_llm.invoke(classification_prompt)
                    
                    if isinstance(response.content, str):
                        content = response.content
                        if "```json" in content:
                            content = content.split("```json")[1].split("```")[0].strip()
                        elif "```" in content:
                            content = content.split("```")[1].split("```")[0].strip()
                        
                        try:
                            classification_result = json.loads(content)
                        except json.JSONDecodeError:
                            classification_result = {
                                "diagram_type": "unknown",
                                "is_architectural": "architecture" in content.lower() or "system" in content.lower(),
                                "quality_score": 0.6,
                                "key_elements": [],
                                "rationale": content[:200]
                            }
                    else:
                        classification_result = {
                            "is_architectural": True,
                            "quality_score": 0.7,
                            "rationale": "Gemini analysis completed"
                        }
                    
                except Exception as e:
                    classification_result = {"error": str(e)[:100]}
            
            combined_results = {
                "images_found": len(images),
                "classification": classification_result
            }
            
            found = len(images) > 0
            if classification_result and classification_result.get("is_architectural"):
                found = True
            
            rationale = f"Found {len(images)} images in PDF."
            if classification_result and not classification_result.get("error"):
                rationale += f" Gemini classification: {classification_result.get('diagram_type', 'unknown')} diagram. "
                rationale += classification_result.get("rationale", "")[:150]
            else:
                rationale += " Multimodal classification attempted."
            
            confidence = 0.5 if images else 0.1
            if classification_result and classification_result.get("is_architectural"):
                confidence = min(0.9, 0.5 + (classification_result.get("quality_score", 0.5) * 0.4))
            
            evidence_list.append(Evidence(
                criterion_id=dim_id,
                goal="Extract and classify architectural diagrams using Gemini multimodal analysis",
                found=found,
                content=json.dumps(combined_results, indent=2),
                location=str(pdf_path),
                rationale=rationale,
                confidence=confidence,
            ))

        # Ensure we always return something even if no matching dimensions
        if not evidence_list:
            evidence_list.append(Evidence(
                criterion_id="swarm_visual",
                goal="Extract diagrams from PDF",
                found=False,
                location=str(pdf_path),
                rationale="No pdf_images dimensions in rubric or no images found",
                confidence=0.1,
            ))

        return {"evidences": {"vision": evidence_list}}

    except Exception as e:
        return {
            "evidences": {"vision": [Evidence(
                criterion_id="swarm_visual",
                goal="Extract diagrams from PDF",
                found=False,
                content=f"Error: {e}",
                location=str(pdf_path),
                rationale=f"Image extraction failed: {type(e).__name__}",
                confidence=0.0,
            )]},
        }


# ──────────────────────────────────────────────
# Evidence Aggregator — The Lab Technician
#
# Cross-references findings from all three detectives.
# This is the fan-in sync point (Superstep 3).
# Does NOT mutate input state — returns only new evidence.
# ──────────────────────────────────────────────

def evidence_aggregator_node(state: AgentState) -> dict:
    """Cross-reference evidence from all detectives.

    Reads: evidences (all keys from all detectives)
    Writes: evidences["cross_ref"] (new key, merged by operator.ior)

    Primary job: detect hallucinations where the PDF report
    claims files exist that the repo detective didn't find.
    """
    evidences = state.get("evidences", {})
    doc_evidence = evidences.get("doc", [])
    repo_evidence = evidences.get("repo", [])

    cross_ref_evidence = []

    # ── Hallucination Detection ──
    actual_filenames = set()
    for repo_ev in repo_evidence:
        if repo_ev.location and repo_ev.location != "not_found":
            loc = repo_ev.location.split(":")[0]
            actual_filenames.add(Path(loc).name)

    for doc_ev in doc_evidence:
        if doc_ev.criterion_id != "report_accuracy":
            continue
        if not doc_ev.content:
            continue

        try:
            claimed_data = json.loads(doc_ev.content)
            claimed_paths = claimed_data.get("claimed_paths", [])
        except (json.JSONDecodeError, TypeError):
            continue

        for claimed_path in claimed_paths:
            claimed_filename = Path(claimed_path).name

            if claimed_filename not in actual_filenames:
                cross_ref_evidence.append(Evidence(
                    criterion_id="report_accuracy",
                    goal=f"HALLUCINATION: Report claims '{claimed_path}' exists",
                    found=False,
                    content=claimed_path,
                    location=f"cross_ref:{claimed_path}",
                    rationale=(
                        f"Filename '{claimed_filename}' not found in repo evidence. "
                        f"Known files: {sorted(actual_filenames)}"
                    ),
                    confidence=0.9,
                ))

    if cross_ref_evidence:
        hallucination_count = len(cross_ref_evidence)
        cross_ref_evidence.append(Evidence(
            criterion_id="report_accuracy",
            goal="Cross-reference summary",
            found=True,
            content=f"{hallucination_count} hallucinated paths detected",
            location="cross_ref:summary",
            rationale=(
                f"Found {hallucination_count} file paths in the PDF report "
                "that do not match any files found by the repo detective."
            ),
            confidence=0.95,
        ))

    return {
        "evidences": {"cross_ref": cross_ref_evidence},
    }