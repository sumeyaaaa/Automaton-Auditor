"""
Judicial nodes implementing the Dialectical Bench.
Three distinct personas analyze evidence independently.

DeepSeek-compatible: uses function_calling method for structured output,
with JSON-prompt fallback for providers that don't support it.
"""
import json
import logging
from typing import Dict, List, Literal

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import ValidationError

from src.config import get_llm
from src.state import AgentState, Evidence, JudicialOpinion

logger = logging.getLogger(__name__)

# ─── Persona Definitions ────────────────────────────────────────────────────

PERSONA_CONFIG: Dict[str, dict] = {
    "Prosecutor": {
        "philosophy": '"Trust No One. Assume Vibe Coding."',
        "role_description": (
            "Your role is to scrutinize evidence for:\n"
            "- Gaps and missing elements\n"
            "- Security flaws and vulnerabilities\n"
            "- Lazy implementations and shortcuts\n"
            "- Hallucinations and false claims"
        ),
        "scoring_guidance": (
            "Judicial Sentencing Guidelines:\n"
            "- If evidence shows linear flow instead of parallel orchestration: Score 1\n"
            "- If structured output is missing: Score 2 max\n"
            "- If security sandboxing is absent: Score 1 (Security Negligence)\n"
            "- If evidence is missing or confidence is low: Score 1-2"
        ),
        "evaluation_focus": (
            "Provide a harsh, critical assessment. "
            "Look for what's missing, not what's present."
        ),
        "user_prompt_directive": (
            "Be critical. Look for violations, gaps, and failures.\n"
            "What specific elements are missing? What security issues exist? "
            "What shortcuts were taken?"
        ),
        "default_no_evidence_score": 1,
        "default_error_score": 1,
        "no_evidence_argument": (
            "No evidence collected for {dimension_name}. "
            "This indicates a fundamental failure in the forensic process."
        ),
    },
    "Defense": {
        "philosophy": '"Reward Effort and Intent. Look for the \'Spirit of the Law\'."',
        "role_description": (
            "Your role is to highlight:\n"
            "- Creative workarounds and innovative solutions\n"
            "- Deep understanding despite implementation flaws\n"
            "- Engineering process and iterative development\n"
            "- Intent and architectural thinking"
        ),
        "scoring_guidance": (
            "Judicial Sentencing Guidelines:\n"
            "- If code shows deep understanding but has syntax errors: Argue for Score 3-4\n"
            "- If git history shows iterative development: Reward with higher score\n"
            "- If architecture is sound but incomplete: Focus on what's present\n"
            "- If evidence shows effort: Boost score based on 'Engineering Process'"
        ),
        "evaluation_focus": (
            "Provide a generous, optimistic assessment. "
            "Look for what's present and the intent behind it."
        ),
        "user_prompt_directive": (
            "Be generous. Look for effort, intent, and creative solutions.\n"
            "What shows deep understanding? What demonstrates good engineering process? "
            "What deserves credit even if imperfect?"
        ),
        "default_no_evidence_score": 3,
        "default_error_score": 3,
        "no_evidence_argument": (
            "Evidence collection may have failed, but this doesn't "
            "necessarily mean {dimension_name} is absent. "
            "Consider the possibility of implementation in progress."
        ),
    },
    "TechLead": {
        "philosophy": '"Does it actually work? Is it maintainable?"',
        "role_description": (
            "Your role is to evaluate:\n"
            "- Architectural soundness and modularity\n"
            "- Code cleanliness and maintainability\n"
            "- Practical viability and technical debt\n"
            "- Functionality over 'vibe' or 'effort'"
        ),
        "scoring_guidance": (
            "Judicial Sentencing Guidelines:\n"
            "- If architecture is modular and workable: Score 4-5\n"
            "- If code works but has technical debt: Score 3\n"
            "- If security is compromised: Score 1-2 (overrides other factors)\n"
            "- If structure is sound but incomplete: Score 2-3"
        ),
        "evaluation_focus": (
            "Provide a realistic, pragmatic assessment. "
            "Focus on artifacts, not intent."
        ),
        "user_prompt_directive": (
            "Be pragmatic. Focus on what works, what's maintainable, "
            "and what's technically sound.\n"
            "Does the architecture actually function? Is the code clean? "
            "What's the technical debt?"
        ),
        "default_no_evidence_score": 1,
        "default_error_score": 2,
        "no_evidence_argument": (
            "No evidence available for {dimension_name}. "
            "Cannot verify functionality without evidence."
        ),
    },
}


# ─── Shared Judge Logic ─────────────────────────────────────────────────────

def _collect_dimension_evidence(
    evidences: Dict, dimension_id: str
) -> List[Evidence]:
    """Filter all evidence across detective sources for a specific criterion."""
    result = []
    for source_list in evidences.values():
        if not isinstance(source_list, list):
            continue
        for ev in source_list:
            if isinstance(ev, Evidence) and ev.criterion_id == dimension_id:
                result.append(ev)
    return result


def _format_evidence_summary(evidence_list: List[Evidence]) -> str:
    """Build a formatted evidence block for the LLM prompt."""
    parts = []
    for ev in evidence_list:
        content_preview = ev.content[:1000] if ev.content else "N/A"
        parts.append(
            f"Location: {ev.location}\n"
            f"Goal: {ev.goal}\n"
            f"Found: {ev.found}\n"
            f"Confidence: {ev.confidence}\n"
            f"Rationale: {ev.rationale}\n"
            f"Content: {content_preview}"
        )
    return "\n---\n".join(parts)


def _build_system_prompt(
    persona: str, dimension_name: str, dimension_id: str, evidence_text: str
) -> str:
    """Assemble the system prompt from persona config + evidence."""
    cfg = PERSONA_CONFIG[persona]
    return (
        f"You are The {persona} in a Digital Courtroom.\n"
        f"Your core philosophy: {cfg['philosophy']}\n\n"
        f"{cfg['role_description']}\n\n"
        f"You are evaluating: {dimension_name}\n"
        f"Criterion ID: {dimension_id}\n\n"
        f"Evidence collected:\n{evidence_text}\n\n"
        f"{cfg['scoring_guidance']}\n\n"
        "CRITICAL: Your argument MUST cite specific evidence:\n"
        "- Include exact file paths and line numbers (e.g., 'src/graph.py:157')\n"
        "- Quote code snippets when relevant (use the Content field from evidence)\n"
        "- Reference specific locations from the evidence Location field\n"
        "- Be concise: 2-3 sentences maximum, no repetition\n"
        "- Focus on concrete findings, not generic observations\n\n"
        f"{cfg['evaluation_focus']}"
    )


def _invoke_structured(llm, system_prompt: str, user_prompt: str) -> JudicialOpinion:
    """Try structured output via function_calling, then JSON-prompt fallback.
    
    Strategy:
    1. Try .with_structured_output(method="function_calling") — works for
       OpenAI, Grok (via ChatOpenAI), and DeepSeek (via ChatDeepSeek).
    2. If that fails (unsupported API, response_format error, etc.),
       fall back to raw JSON prompt + manual parsing.
    """
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    # Attempt 1: structured output via function_calling
    try:
        structured_llm = llm.with_structured_output(
            JudicialOpinion, method="function_calling"
        )
        return structured_llm.invoke(messages)
    except (TypeError, NotImplementedError):
        # method kwarg not supported by this LLM class — go to fallback
        pass
    except Exception as e:
        error_str = str(e).lower()
        # Known failure modes that mean "try the fallback"
        recoverable_signals = [
            "response_format", "unavailable", "json_schema",
            "tool_choice", "400", "422", "unprocessable",
        ]
        if any(sig in error_str for sig in recoverable_signals):
            logger.info(
                "Structured output not supported by this provider, "
                "falling back to JSON prompt."
            )
        else:
            raise  # Unknown error — don't swallow it

    # Attempt 2: JSON-prompt fallback
    json_prompt = (
        f"{system_prompt}\n\n{user_prompt}\n\n"
        "Return your response as a valid JSON object matching this exact schema:\n"
        "{\n"
        '    "score": <integer 1-5>,\n'
        '    "argument": "<string, 2-3 sentences citing specific evidence>",\n'
        '    "cited_evidence": ["<list of file paths from evidence>"]\n'
        "}"
    )
    fallback_messages = [
        SystemMessage(content="You are a JSON-only assistant. Always return valid JSON."),
        HumanMessage(content=json_prompt),
    ]
    response = llm.invoke(fallback_messages)
    response_text = response.content if hasattr(response, "content") else str(response)

    # Strip markdown code fences if present
    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0].strip()
    elif "```" in response_text:
        response_text = response_text.split("```")[1].split("```")[0].strip()

    data = json.loads(response_text)
    return JudicialOpinion(
        score=data.get("score", 2),
        argument=data.get("argument", "Failed to parse argument from JSON fallback."),
        cited_evidence=data.get("cited_evidence", []),
    )


# ─── Judge Factory ───────────────────────────────────────────────────────────

def _make_judge_node(persona: Literal["Prosecutor", "Defense", "TechLead"]):
    """Factory: creates a judge node function with the given persona.
    
    Each returned function:
    1. Reads evidence + rubric from state
    2. For each rubric dimension, invokes the LLM with persona-specific prompts
    3. Returns opinions to be merged via operator.add reducer
    """
    cfg = PERSONA_CONFIG[persona]

    def judge_node(state: AgentState) -> AgentState:
        evidences = state.get("evidences", {})
        rubric_dimensions = state["rubric_dimensions"]
        llm = get_llm("layer2", temperature=0)
        opinions: List[JudicialOpinion] = []

        for dimension in rubric_dimensions:
            dim_id = dimension["id"]
            dim_name = dimension["name"]

            # Gather evidence for this criterion
            dim_evidence = _collect_dimension_evidence(evidences, dim_id)

            # No evidence → persona-appropriate default
            if not dim_evidence:
                opinions.append(JudicialOpinion(
                    judge=persona,
                    criterion_id=dim_id,
                    score=cfg["default_no_evidence_score"],
                    argument=cfg["no_evidence_argument"].format(
                        dimension_name=dim_name
                    ),
                    cited_evidence=[],
                ))
                continue

            # Build prompts
            evidence_text = _format_evidence_summary(dim_evidence)
            system_prompt = _build_system_prompt(
                persona, dim_name, dim_id, evidence_text
            )
            user_prompt = (
                f"Analyze the evidence for {dim_name} and provide your verdict.\n"
                "Cite specific file paths, line numbers, and code snippets "
                "from the evidence.\n"
                f"{cfg['user_prompt_directive']}"
            )

            try:
                opinion = _invoke_structured(llm, system_prompt, user_prompt)
                opinion.judge = persona
                opinion.criterion_id = dim_id

                # Ensure citations are populated
                if not opinion.cited_evidence:
                    opinion.cited_evidence = [
                        ev.location for ev in dim_evidence
                    ]
                opinions.append(opinion)

            except (ValidationError, json.JSONDecodeError) as e:
                logger.warning(
                    "Structured output parse error for %s/%s: %s",
                    persona, dim_id, e,
                )
                opinions.append(JudicialOpinion(
                    judge=persona,
                    criterion_id=dim_id,
                    score=cfg["default_error_score"],
                    argument=(
                        f"Structured output failed: {str(e)[:150]}. "
                        "Assessment incomplete."
                    ),
                    cited_evidence=[],
                ))
            except Exception as e:
                error_str = str(e)
                is_quota = "quota" in error_str.lower() or "429" in error_str
                logger.error(
                    "%s error for %s/%s: %s",
                    "Quota" if is_quota else "Unexpected",
                    persona, dim_id, error_str[:200],
                )
                opinions.append(JudicialOpinion(
                    judge=persona,
                    criterion_id=dim_id,
                    score=cfg["default_error_score"],
                    argument=(
                        f"API quota exceeded for {dim_name}. "
                        "Evidence exists but assessment incomplete."
                        if is_quota
                        else f"Critical error: {error_str[:200]}"
                    ),
                    cited_evidence=(
                        [ev.location for ev in dim_evidence]
                        if dim_evidence else []
                    ),
                ))

        return {"opinions": opinions}

    # Name the function for LangGraph node registration + tracing
    judge_node.__name__ = f"{persona.lower()}_node"
    judge_node.__qualname__ = f"{persona.lower()}_node"
    return judge_node


# ─── Public Node Functions ───────────────────────────────────────────────────

prosecutor_node = _make_judge_node("Prosecutor")
defense_node = _make_judge_node("Defense")
tech_lead_node = _make_judge_node("TechLead")