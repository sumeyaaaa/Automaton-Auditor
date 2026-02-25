"""
Detective nodes for forensic evidence collection.
These agents collect objective facts without opinion.
"""
import json
from pathlib import Path
from typing import Dict

from src.state import AgentState, Evidence
from src.tools.ast_tools import (
    check_parallel_edges,
    check_pydantic_models,
    check_sandboxing,
    check_security,
    check_stategraph,
    check_structured_output,
)
from src.tools.git_tools import extract_git_history, safe_clone
from src.tools.pdf_tools import (
    extract_file_path_claims,
    extract_images_from_pdf,
    ingest_pdf,
    search_keywords,
)


def repo_investigator_node(state: AgentState) -> AgentState:
    """RepoInvestigator: The Code Detective.
    
    Collects forensic evidence about the repository structure,
    git history, graph architecture, and code quality.
    """
    repo_url = state["repo_url"]
    rubric_dimensions = state["rubric_dimensions"]
    
    try:
        # Clone repository (sandboxed)
        repo_path, commit_hash = safe_clone(repo_url)
        
        # Collect evidence for each relevant dimension
        evidences = {}
        
        for dimension in rubric_dimensions:
            if dimension.get("target_artifact") != "github_repo":
                continue
            
            dimension_id = dimension["id"]
            forensic_instruction = dimension.get("forensic_instruction", "")
            
            evidence_list = []
            
            # Execute forensic protocols based on dimension
            if dimension_id == "git_forensic_analysis":
                git_data = extract_git_history(repo_path)
                evidence_list.append(Evidence(
                    criterion_id=dimension_id,
                    goal=forensic_instruction,
                    found=git_data.get("total_commits", 0) > 0,
                    content=json.dumps(git_data, indent=2),
                    location=f"git log of {repo_url}",
                    rationale=f"Found {git_data.get('total_commits', 0)} commits. "
                              f"Atomic progression: {git_data.get('is_atomic', False)}. "
                              f"Progression pattern: {git_data.get('has_progression', False)}",
                    confidence=1.0 if git_data.get("total_commits", 0) > 3 else 0.5,
                ))
            
            elif dimension_id == "state_management_rigor":
                state_data = check_pydantic_models(repo_path)
                evidence_list.append(Evidence(
                    criterion_id=dimension_id,
                    goal=forensic_instruction,
                    found=state_data.get("found", False),
                    content=json.dumps(state_data, indent=2),
                    location="src/state.py or equivalent",
                    rationale=f"Pydantic: {state_data.get('has_pydantic', False)}, "
                              f"TypedDict: {state_data.get('has_typeddict', False)}, "
                              f"Reducers: {state_data.get('has_reducers', False)}. "
                              f"AST analysis confirmed structure.",
                    confidence=1.0 if state_data.get("is_properly_typed", False) and state_data.get("has_reducers", False) else 0.3,
                ))
            
            elif dimension_id == "graph_orchestration":
                graph_data = check_stategraph(repo_path)
                parallel_data = check_parallel_edges(repo_path)
                evidence_list.append(Evidence(
                    criterion_id=dimension_id,
                    goal=forensic_instruction,
                    found=graph_data.get("found", False),
                    content=json.dumps({**graph_data, **parallel_data}, indent=2),
                    location="src/graph.py",
                    rationale=f"StateGraph: {graph_data.get('has_stategraph', False)}, "
                              f"Parallel edges: {parallel_data.get('has_parallel_edges', False)}, "
                              f"Fan-out: {parallel_data.get('has_fan_out', False)}, "
                              f"Fan-in: {parallel_data.get('has_fan_in', False)}. "
                              f"AST analysis confirmed structure.",
                    confidence=0.8 if parallel_data.get("has_fan_out", False) and parallel_data.get("has_fan_in", False) else 0.4,
                ))
            
            elif dimension_id == "safe_tool_engineering":
                sandbox_data = check_sandboxing(repo_path)
                security_data = check_security(repo_path)
                evidence_list.append(Evidence(
                    criterion_id=dimension_id,
                    goal=forensic_instruction,
                    found=sandbox_data.get("found", False),
                    content=json.dumps({**sandbox_data, **security_data}, indent=2),
                    location="src/tools/",
                    rationale=f"Sandboxing: {sandbox_data.get('has_sandboxing', False)}, "
                              f"Security: {sandbox_data.get('security_score', 'unknown')}, "
                              f"Security issues: {len(security_data.get('security_issues', []))}. "
                              f"AST analysis confirmed patterns.",
                    confidence=1.0 if sandbox_data.get("security_score") == "safe" and security_data.get("is_secure", False) else 0.2,
                ))
            
            elif dimension_id == "structured_output_enforcement":
                output_data = check_structured_output(repo_path)
                evidence_list.append(Evidence(
                    criterion_id=dimension_id,
                    goal=forensic_instruction,
                    found=output_data.get("found", False),
                    content=json.dumps(output_data, indent=2),
                    location="src/nodes/judges.py",
                    rationale=f"Structured output: {output_data.get('has_structured_output', False)}, "
                              f"Pydantic validation: {output_data.get('has_pydantic_validation', False)}. "
                              f"AST analysis confirmed usage.",
                    confidence=1.0 if output_data.get("has_structured_output", False) else 0.3,
                ))
            
            if evidence_list:
                evidences[dimension_id] = evidence_list
        
        # Flatten evidences into a single list for repo source
        repo_evidences = []
        for ev_list in evidences.values():
            repo_evidences.extend(ev_list)
        
        return {
            "evidences": {"repo": repo_evidences},
            "git_commit_hash": commit_hash,
        }
    
    except Exception as e:
        # Return error evidence
        error_evidence = Evidence(
            criterion_id="error",
            goal="Repository investigation",
            found=False,
            content=f"Error: {str(e)}",
            location=repo_url,
            rationale="Failed to clone or analyze repository",
            confidence=0.0,
        )
        return {
            "evidences": {"repo": [error_evidence]},
            "git_commit_hash": "",
        }


def doc_analyst_node(state: AgentState) -> AgentState:
    """DocAnalyst: The Paperwork Detective.
    
    Analyzes PDF reports for theoretical depth and accuracy.
    """
    pdf_path = Path(state["pdf_path"])
    rubric_dimensions = state["rubric_dimensions"]
    
    try:
        # Ingest PDF
        doc_data = ingest_pdf(pdf_path)
        
        if not doc_data.get("success"):
            error_evidence = Evidence(
                criterion_id="error",
                goal="PDF ingestion",
                found=False,
                content=f"Error: {doc_data.get('error', 'Unknown error')}",
                location=str(pdf_path),
                rationale="Failed to parse PDF",
                confidence=0.0,
            )
            return {
                "evidences": {"doc": [error_evidence]},
            }
        
        chunks = doc_data.get("chunks", [])
        evidences = {}
        
        for dimension in rubric_dimensions:
            if dimension.get("target_artifact") != "pdf_report":
                continue
            
            dimension_id = dimension["id"]
            forensic_instruction = dimension.get("forensic_instruction", "")
            
            evidence_list = []
            
            if dimension_id == "theoretical_depth":
                # Search for key terms
                keywords = [
                    "Dialectical Synthesis",
                    "Fan-In / Fan-Out",
                    "Fan-In/Fan-Out",
                    "Metacognition",
                    "State Synchronization",
                ]
                keyword_results = search_keywords(chunks, keywords)
                
                evidence_list.append(Evidence(
                    criterion_id=dimension_id,
                    goal=forensic_instruction,
                    found=keyword_results["summary"]["total_occurrences"] > 0,
                    content=json.dumps(keyword_results, indent=2),
                    location=str(pdf_path),
                    rationale=f"Found {keyword_results['summary']['total_occurrences']} occurrences, "
                              f"{keyword_results['summary']['substantive_occurrences']} substantive. "
                              f"Keyword dropping: {keyword_results['summary']['keyword_dropping']}",
                    confidence=0.8 if keyword_results["summary"]["substantive_occurrences"] > 0 else 0.3,
                ))
            
            elif dimension_id == "report_accuracy":
                # Extract file paths and prepare for cross-reference
                claimed_paths = extract_file_path_claims(chunks)
                
                evidence_list.append(Evidence(
                    criterion_id=dimension_id,
                    goal=forensic_instruction,
                    found=len(claimed_paths) > 0,
                    content=json.dumps({"claimed_paths": claimed_paths}, indent=2),
                    location=str(pdf_path),
                    rationale=f"Extracted {len(claimed_paths)} file path claims from PDF. "
                              f"Will be cross-referenced by evidence_aggregator.",
                    confidence=0.9 if len(claimed_paths) > 0 else 0.0,
                ))
            
            if evidence_list:
                evidences[dimension_id] = evidence_list
        
        # Flatten evidences into a single list for doc source
        doc_evidences = []
        for ev_list in evidences.values():
            doc_evidences.extend(ev_list)
        
        return {
            "evidences": {"doc": doc_evidences},
        }
    
    except Exception as e:
        error_evidence = Evidence(
            criterion_id="error",
            goal="PDF analysis",
            found=False,
            content=f"Error: {str(e)}",
            location=str(pdf_path),
            rationale="Failed to analyze PDF",
            confidence=0.0,
        )
        return {
            "evidences": {"doc": [error_evidence]},
        }


def vision_inspector_node(state: AgentState) -> AgentState:
    """VisionInspector: The Diagram Detective.
    
    Analyzes architectural diagrams from PDF reports.
    Note: Implementation required, execution optional per requirements.
    """
    pdf_path = Path(state["pdf_path"])
    rubric_dimensions = state["rubric_dimensions"]
    
    try:
        # Extract images
        images = extract_images_from_pdf(pdf_path)
        
        evidences = {}
        
        for dimension in rubric_dimensions:
            if dimension.get("target_artifact") != "pdf_images":
                continue
            
            dimension_id = dimension["id"]
            
            if dimension_id == "swarm_visual":
                # Placeholder for diagram analysis
                evidence_list = [Evidence(
                    criterion_id=dimension_id,
                    goal=dimension.get("forensic_instruction", "Analyze diagram"),
                    found=len(images) > 0,
                    content=json.dumps({"images_found": len(images)}, indent=2),
                    location=str(pdf_path),
                    rationale=f"Found {len(images)} images in PDF. "
                              "Vision analysis requires model configuration.",
                    confidence=0.5 if len(images) > 0 else 0.0,
                )]
                evidences[dimension_id] = evidence_list
        
        # Flatten evidences into a single list for vision source
        vision_evidences = []
        for ev_list in evidences.values():
            vision_evidences.extend(ev_list)
        
        return {
            "evidences": {"vision": vision_evidences},
        }
    
    except Exception as e:
        error_evidence = Evidence(
            criterion_id="error",
            goal="Image analysis",
            found=False,
            content=f"Error: {str(e)}",
            location=str(pdf_path),
            rationale="Failed to extract or analyze images",
            confidence=0.0,
        )
        return {
            "evidences": {"vision": [error_evidence]},
        }


def evidence_aggregator_node(state: AgentState) -> AgentState:
    """Aggregates evidence from all detectives and performs cross-referencing.
    
    This is the fan-in point after parallel detective execution.
    Cross-references doc claims against repo findings to detect hallucinations.
    """
    evidences = state.get("evidences", {})
    
    # Flatten evidences structure
    all_evidences = {}
    for source, evidence_list in evidences.items():
        for ev in evidence_list:
            if ev.criterion_id not in all_evidences:
                all_evidences[ev.criterion_id] = []
            all_evidences[ev.criterion_id].append(ev)
    
    # Cross-reference: Check doc claims against repo evidence
    doc_evidence = evidences.get("doc", [])
    repo_evidence = evidences.get("repo", [])
    
    hallucination_evidences = []
    
    # Find report_accuracy evidence from doc
    for doc_ev in doc_evidence:
        if doc_ev.criterion_id == "report_accuracy":
            try:
                claimed_paths_data = json.loads(doc_ev.content)
                claimed_paths = claimed_paths_data.get("claimed_paths", [])
                
                # Get actual files from repo evidence
                actual_files = []
                for repo_ev in repo_evidence:
                    if repo_ev.location and "src/" in repo_ev.location:
                        actual_files.append(repo_ev.location)
                
                # Check each claimed path
                for claimed_path in claimed_paths:
                    # Normalize path
                    normalized = claimed_path.replace("./", "").replace("src/", "")
                    
                    # Check if exists in actual files
                    found = False
                    for actual in actual_files:
                        if normalized in actual or actual.endswith(normalized):
                            found = True
                            break
                    
                    if not found:
                        # Hallucination detected
                        hallucination_evidences.append(Evidence(
                            criterion_id="report_accuracy",
                            goal=f"HALLUCINATION: Report claims {claimed_path} exists",
                            found=False,
                            content=f"Report claims file exists: {claimed_path}",
                            location=claimed_path,
                            rationale="Cross-reference check: file path mentioned in PDF but not found in repository",
                            confidence=0.95,
                        ))
            except Exception:
                pass
    
    # Add hallucination evidences to doc evidence
    if hallucination_evidences:
        if "doc" not in evidences:
            evidences["doc"] = []
        evidences["doc"].extend(hallucination_evidences)
    
    return {
        "evidences": evidences,
    }
