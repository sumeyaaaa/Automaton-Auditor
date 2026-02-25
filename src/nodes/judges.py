"""
Judicial nodes implementing the Dialectical Bench.
Three distinct personas analyze evidence independently.
"""
import json
from typing import Dict, List

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import ValidationError

from src.config import get_llm
from src.state import AgentState, Evidence, JudicialOpinion


def prosecutor_node(state: AgentState) -> AgentState:
    """The Prosecutor: The Critical Lens.
    
    Core Philosophy: "Trust No One. Assume Vibe Coding."
    Scrutinizes evidence for gaps, security flaws, and laziness.
    """
    evidences = state.get("evidences", {})
    rubric_dimensions = state["rubric_dimensions"]
    
    # Use layer2 model (judges need high-quality reasoning)
    llm = get_llm("layer2", temperature=0)  # Temperature 0 for deterministic scoring
    opinions = []
    
    for dimension in rubric_dimensions:
        dimension_id = dimension["id"]
        dimension_name = dimension["name"]
        
        # Get relevant evidence
        dimension_evidence = evidences.get(dimension_id, [])
        if not dimension_evidence:
            # No evidence found - harsh penalty
            opinions.append(JudicialOpinion(
                judge="Prosecutor",
                criterion_id=dimension_id,
                score=1,
                argument=f"No evidence collected for {dimension_name}. "
                        "This indicates a fundamental failure in the forensic process.",
                cited_evidence=[],
            ))
            continue
        
        # Build evidence summary
        evidence_summary = []
        for ev in dimension_evidence:
            evidence_summary.append(
                f"Goal: {ev.goal}\n"
                f"Found: {ev.found}\n"
                f"Confidence: {ev.confidence}\n"
                f"Rationale: {ev.rationale}"
            )
        
        # Prosecutor system prompt
        system_prompt = f"""You are The Prosecutor in a Digital Courtroom.
Your core philosophy: "Trust No One. Assume Vibe Coding."

Your role is to scrutinize evidence for:
- Gaps and missing elements
- Security flaws and vulnerabilities
- Lazy implementations and shortcuts
- Hallucinations and false claims

You are evaluating: {dimension_name}
Criterion ID: {dimension_id}

Evidence collected:
{chr(10).join(evidence_summary)}

Judicial Sentencing Guidelines:
- If evidence shows linear flow instead of parallel orchestration: Score 1
- If structured output is missing: Score 2 max
- If security sandboxing is absent: Score 1 (Security Negligence)
- If evidence is missing or confidence is low: Score 1-2

Provide a harsh, critical assessment. Look for what's missing, not what's present.
Return your opinion as JSON matching the JudicialOpinion schema."""

        try:
            # Use structured output with system prompt
            structured_llm = llm.with_structured_output(JudicialOpinion)
            
            user_prompt = f"""Analyze the evidence for {dimension_name} and provide your verdict.
Be critical. Look for violations, gaps, and failures.
What specific elements are missing? What security issues exist?
What shortcuts were taken?"""
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
            
            opinion = structured_llm.invoke(messages)
            opinion.judge = "Prosecutor"
            opinion.criterion_id = dimension_id
            
            # Add evidence citations
            opinion.cited_evidence = [ev.location for ev in dimension_evidence]
            
            opinions.append(opinion)
        
        except ValidationError as e:
            # Fallback if structured output fails
            opinions.append(JudicialOpinion(
                judge="Prosecutor",
                criterion_id=dimension_id,
                score=1,
                argument=f"Error in structured output: {str(e)}. "
                        "This indicates a technical failure in the judicial process.",
                cited_evidence=[],
            ))
        except Exception as e:
            opinions.append(JudicialOpinion(
                judge="Prosecutor",
                criterion_id=dimension_id,
                score=1,
                argument=f"Critical error: {str(e)}",
                cited_evidence=[],
            ))
    
    return {
        "opinions": opinions,
    }


def defense_node(state: AgentState) -> AgentState:
    """The Defense Attorney: The Optimistic Lens.
    
    Core Philosophy: "Reward Effort and Intent. Look for the 'Spirit of the Law'."
    Highlights creative workarounds, deep thought, and effort.
    """
    evidences = state.get("evidences", {})
    rubric_dimensions = state["rubric_dimensions"]
    
    # Use layer2 model (judges need high-quality reasoning)
    llm = get_llm("layer2", temperature=0)  # Temperature 0 for deterministic scoring
    opinions = []
    
    for dimension in rubric_dimensions:
        dimension_id = dimension["id"]
        dimension_name = dimension["name"]
        
        # Get relevant evidence
        dimension_evidence = evidences.get(dimension_id, [])
        if not dimension_evidence:
            # Give benefit of the doubt
            opinions.append(JudicialOpinion(
                judge="Defense",
                criterion_id=dimension_id,
                score=3,
                argument=f"Evidence collection may have failed, but this doesn't "
                        f"necessarily mean {dimension_name} is absent. "
                        "Consider the possibility of implementation in progress.",
                cited_evidence=[],
            ))
            continue
        
        # Build evidence summary
        evidence_summary = []
        for ev in dimension_evidence:
            evidence_summary.append(
                f"Goal: {ev.goal}\n"
                f"Found: {ev.found}\n"
                f"Confidence: {ev.confidence}\n"
                f"Rationale: {ev.rationale}"
            )
        
        # Defense system prompt
        system_prompt = f"""You are The Defense Attorney in a Digital Courtroom.
Your core philosophy: "Reward Effort and Intent. Look for the 'Spirit of the Law'."

Your role is to highlight:
- Creative workarounds and innovative solutions
- Deep understanding despite implementation flaws
- Engineering process and iterative development
- Intent and architectural thinking

You are evaluating: {dimension_name}
Criterion ID: {dimension_id}

Evidence collected:
{chr(10).join(evidence_summary)}

Judicial Sentencing Guidelines:
- If code shows deep understanding but has syntax errors: Argue for Score 3-4
- If git history shows iterative development: Reward with higher score
- If architecture is sound but incomplete: Focus on what's present
- If evidence shows effort: Boost score based on "Engineering Process"

Provide a generous, optimistic assessment. Look for what's present and the intent behind it.
Return your opinion as JSON matching the JudicialOpinion schema."""

        try:
            # Use structured output with system prompt
            structured_llm = llm.with_structured_output(JudicialOpinion)
            
            user_prompt = f"""Analyze the evidence for {dimension_name} and provide your verdict.
Be generous. Look for effort, intent, and creative solutions.
What shows deep understanding? What demonstrates good engineering process?
What deserves credit even if imperfect?"""
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
            
            opinion = structured_llm.invoke(messages)
            opinion.judge = "Defense"
            opinion.criterion_id = dimension_id
            
            # Add evidence citations
            opinion.cited_evidence = [ev.location for ev in dimension_evidence]
            
            opinions.append(opinion)
        
        except ValidationError as e:
            opinions.append(JudicialOpinion(
                judge="Defense",
                criterion_id=dimension_id,
                score=3,
                argument=f"Technical error occurred, but the system attempted structured output. "
                        "This shows effort toward proper implementation.",
                cited_evidence=[],
            ))
        except Exception as e:
            opinions.append(JudicialOpinion(
                judge="Defense",
                criterion_id=dimension_id,
                score=3,
                argument=f"Error occurred: {str(e)}. Consider the intent behind the implementation.",
                cited_evidence=[],
            ))
    
    return {
        "opinions": opinions,
    }


def tech_lead_node(state: AgentState) -> AgentState:
    """The Tech Lead: The Pragmatic Lens.
    
    Core Philosophy: "Does it actually work? Is it maintainable?"
    Evaluates architectural soundness, code cleanliness, and practical viability.
    """
    evidences = state.get("evidences", {})
    rubric_dimensions = state["rubric_dimensions"]
    
    # Use layer2 model (judges need high-quality reasoning)
    llm = get_llm("layer2", temperature=0)  # Temperature 0 for deterministic scoring
    opinions = []
    
    for dimension in rubric_dimensions:
        dimension_id = dimension["id"]
        dimension_name = dimension["name"]
        
        # Get relevant evidence
        dimension_evidence = evidences.get(dimension_id, [])
        if not dimension_evidence:
            opinions.append(JudicialOpinion(
                judge="TechLead",
                criterion_id=dimension_id,
                score=1,
                argument=f"No evidence available for {dimension_name}. "
                        "Cannot verify functionality without evidence.",
                cited_evidence=[],
            ))
            continue
        
        # Build evidence summary
        evidence_summary = []
        for ev in dimension_evidence:
            evidence_summary.append(
                f"Goal: {ev.goal}\n"
                f"Found: {ev.found}\n"
                f"Confidence: {ev.confidence}\n"
                f"Rationale: {ev.rationale}"
            )
        
        # Tech Lead system prompt
        system_prompt = f"""You are The Tech Lead in a Digital Courtroom.
Your core philosophy: "Does it actually work? Is it maintainable?"

Your role is to evaluate:
- Architectural soundness and modularity
- Code cleanliness and maintainability
- Practical viability and technical debt
- Functionality over "vibe" or "effort"

You are evaluating: {dimension_name}
Criterion ID: {dimension_id}

Evidence collected:
{chr(10).join(evidence_summary)}

Judicial Sentencing Guidelines:
- If architecture is modular and workable: Score 4-5
- If code works but has technical debt: Score 3
- If security is compromised: Score 1-2 (overrides other factors)
- If structure is sound but incomplete: Score 2-3

Provide a realistic, pragmatic assessment. Focus on artifacts, not intent.
Return your opinion as JSON matching the JudicialOpinion schema."""

        try:
            # Use structured output with system prompt
            structured_llm = llm.with_structured_output(JudicialOpinion)
            
            user_prompt = f"""Analyze the evidence for {dimension_name} and provide your verdict.
Be pragmatic. Focus on what works, what's maintainable, and what's technically sound.
Does the architecture actually function? Is the code clean? What's the technical debt?"""
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
            
            opinion = structured_llm.invoke(messages)
            opinion.judge = "TechLead"
            opinion.criterion_id = dimension_id
            
            # Add evidence citations
            opinion.cited_evidence = [ev.location for ev in dimension_evidence]
            
            opinions.append(opinion)
        
        except ValidationError as e:
            opinions.append(JudicialOpinion(
                judge="TechLead",
                criterion_id=dimension_id,
                score=2,
                argument=f"Structured output validation failed: {str(e)}. "
                        "This indicates a technical implementation issue.",
                cited_evidence=[],
            ))
        except Exception as e:
            opinions.append(JudicialOpinion(
                judge="TechLead",
                criterion_id=dimension_id,
                score=2,
                argument=f"Technical error: {str(e)}",
                cited_evidence=[],
            ))
    
    return {
        "opinions": opinions,
    }

