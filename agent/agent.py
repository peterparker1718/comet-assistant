"""
Comet Assistant — Master Agentic Agent
======================================
1704 Surf Avenue, Belmar, NJ 07719 | (609) 276-3372

Orchestrates a network of specialized sub-agents to produce supply chain
intelligence dossiers, perform browser automation, index GitHub repositories,
and synthesize research from multiple AI and web sources.

Architecture:
  MasterAgent
  ├── WebResearcherAgent   — crawls web sources, news, and government databases
  ├── DocAnalystAgent      — parses PDFs, filings, and structured documents
  ├── RiskScorerAgent      — applies ESG and geopolitical scoring models
  └── ReportWriterAgent    — synthesizes findings into structured dossiers

Usage:
  export ANTHROPIC_API_KEY="sk-..."
  python agent.py --task "Supply chain dossier: North Sumatra palm oil"
  python agent.py --task "GitHub index: palmoilmonitor/trase" --task-type github
  python agent.py --interactive
"""

import os
import sys
import json
import time
import argparse
import textwrap
from datetime import datetime, timezone
from typing import Any

import anthropic

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MODEL = "claude-opus-4-6"
ADDRESS = "1704 Surf Avenue, Belmar, NJ 07719"
PHONE = "(609) 276-3372"

MASTER_SYSTEM = f"""You are the Master Agentic Agent for Comet Assistant, an AI-powered
supply chain intelligence platform located at {ADDRESS}.

Your role is to orchestrate specialized sub-agents to gather, analyze, and
synthesize supply chain intelligence. You have access to web search, web fetch,
and code execution tools.

When given a research task:
1. Break it into sub-tasks (research, document analysis, risk scoring, report writing)
2. Execute each sub-task using your available tools
3. Synthesize all findings into a structured intelligence report
4. Deliver a final JSON-structured dossier with risk scores and key findings

Always think step-by-step with adaptive reasoning. Use your tools liberally —
the quality of your intelligence depends on the breadth of your research.

Company contact: {PHONE}
"""

SUB_AGENT_CONFIGS = {
    "web-researcher": {
        "description": "Specialized in crawling web sources, news, regulatory databases, and open datasets to gather raw intelligence.",
        "system": """You are the Web Researcher sub-agent for Comet Assistant.
Your job is to search for and retrieve current, authoritative information about
supply chains, companies, regulatory filings, trade data, and geopolitical events.
Always cite your sources. Return structured JSON with a list of findings.""",
        "tools": ["web_search", "web_fetch"],
    },
    "doc-analyst": {
        "description": "Specialized in parsing PDFs, Word documents, financial filings, and structured data to extract entities and relationships.",
        "system": """You are the Document Analyst sub-agent for Comet Assistant.
Your job is to analyze documents, extract key entities (companies, locations,
commodities, quantities, dates), identify relationships, and flag compliance issues.
Return structured JSON with extracted entities and key findings.""",
        "tools": ["code_execution"],
    },
    "risk-scorer": {
        "description": "Applies ESG, geopolitical, and supply chain risk models to score supplier entities and flag exposure.",
        "system": """You are the Risk Scorer sub-agent for Comet Assistant.
Your job is to evaluate supply chain entities against ESG criteria, geopolitical
risk factors, and regulatory compliance requirements. Produce a risk score
between 0.0 (low) and 1.0 (high), with a detailed breakdown by category.
Return structured JSON with scores and flags.""",
        "tools": ["code_execution"],
    },
    "report-writer": {
        "description": "Synthesizes research findings into clear, structured intelligence dossiers and executive summaries.",
        "system": """You are the Report Writer sub-agent for Comet Assistant.
Your job is to take raw research findings, risk scores, and entity data and
synthesize them into a clear, structured intelligence dossier. The dossier
should include an executive summary, key findings, risk scores, supplier
analysis, and recommended actions. Write in a professional, analytical tone.""",
        "tools": [],
    },
}


# ---------------------------------------------------------------------------
# Tool Definitions
# ---------------------------------------------------------------------------

WEB_SEARCH_TOOL = {
    "type": "web_search_20260209",
    "name": "web_search",
}

WEB_FETCH_TOOL = {
    "type": "web_fetch_20260209",
    "name": "web_fetch",
}

CODE_EXECUTION_TOOL = {
    "type": "code_execution_20260120",
    "name": "code_execution",
}

# User-defined tools for sub-agent dispatch
DISPATCH_TOOL = {
    "name": "dispatch_subagent",
    "description": "Dispatch a specialized sub-agent to handle a specific sub-task. Returns the sub-agent's findings.",
    "input_schema": {
        "type": "object",
        "properties": {
            "agent_name": {
                "type": "string",
                "enum": list(SUB_AGENT_CONFIGS.keys()),
                "description": "The sub-agent to dispatch.",
            },
            "task": {
                "type": "string",
                "description": "Clear, specific task description for the sub-agent.",
            },
            "context": {
                "type": "string",
                "description": "Any relevant context or prior findings to pass to the sub-agent.",
            },
        },
        "required": ["agent_name", "task"],
    },
}

RECORD_FINDING_TOOL = {
    "name": "record_finding",
    "description": "Record a key finding, risk score, or data point to the intelligence dossier being built.",
    "input_schema": {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "enum": ["supplier", "risk", "regulatory", "logistics", "market", "geopolitical"],
                "description": "Category of the finding.",
            },
            "title": {
                "type": "string",
                "description": "Short title for the finding.",
            },
            "detail": {
                "type": "string",
                "description": "Detailed description of the finding.",
            },
            "risk_score": {
                "type": "number",
                "description": "Optional risk score 0.0-1.0 for this finding.",
            },
            "sources": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Source URLs or document names.",
            },
        },
        "required": ["category", "title", "detail"],
    },
}


# ---------------------------------------------------------------------------
# Sub-Agent Runner
# ---------------------------------------------------------------------------

def run_subagent(
    client: anthropic.Anthropic,
    agent_name: str,
    task: str,
    context: str = "",
    verbose: bool = False,
) -> str:
    """Run a specialized sub-agent and return its output."""
    config = SUB_AGENT_CONFIGS[agent_name]

    # Build tool list for this sub-agent
    tool_list: list[dict] = []
    tool_names = config.get("tools", [])
    if "web_search" in tool_names:
        tool_list.append(WEB_SEARCH_TOOL)
    if "web_fetch" in tool_names:
        tool_list.append(WEB_FETCH_TOOL)
    if "code_execution" in tool_names:
        tool_list.append(CODE_EXECUTION_TOOL)

    messages: list[dict] = [
        {
            "role": "user",
            "content": (
                f"Task: {task}\n\n"
                + (f"Context from prior research:\n{context}\n\n" if context else "")
                + "Please complete this task and return your findings as structured JSON."
            ),
        }
    ]

    if verbose:
        print(f"  [{agent_name.upper()}] Starting task: {task[:80]}...")

    # Run sub-agent with its own tool loop
    max_iterations = 8
    for iteration in range(max_iterations):
        kwargs: dict[str, Any] = {
            "model": MODEL,
            "max_tokens": 8192,
            "system": config["system"],
            "messages": messages,
            "thinking": {"type": "adaptive"},
        }
        if tool_list:
            kwargs["tools"] = tool_list

        response = client.messages.create(**kwargs)

        if response.stop_reason == "end_turn":
            # Extract text from final response
            text_blocks = [b.text for b in response.content if hasattr(b, "text")]
            result = "\n".join(text_blocks)
            if verbose:
                print(f"  [{agent_name.upper()}] Done ({iteration+1} iteration(s))")
            return result

        if response.stop_reason == "tool_use":
            # Handle server-side tool execution (web search, web fetch, code execution)
            # These are handled server-side; we just continue
            messages.append({"role": "assistant", "content": response.content})

            # Check for any tool use blocks
            tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
            if not tool_use_blocks:
                # No client-side tools to handle; server-side tools ran
                continue

            tool_results = []
            for tool_block in tool_use_blocks:
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_block.id,
                    "content": "Tool executed successfully.",
                })

            messages.append({"role": "user", "content": tool_results})
            continue

        if response.stop_reason == "pause_turn":
            # Server-side tool loop hit limit; resume
            messages.append({"role": "assistant", "content": response.content})
            continue

        # Unexpected stop reason
        break

    text_blocks = [b.text for b in response.content if hasattr(b, "text")]
    return "\n".join(text_blocks) or "[Sub-agent produced no text output]"


# ---------------------------------------------------------------------------
# Master Agent
# ---------------------------------------------------------------------------

class MasterAgent:
    """
    Orchestrates specialized sub-agents to produce supply chain intelligence.
    Uses Claude Opus 4.6 with adaptive thinking and tool use.
    """

    def __init__(self, verbose: bool = True):
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable is not set. "
                "Please set it before running the agent."
            )
        self.client = anthropic.Anthropic(api_key=api_key)
        self.verbose = verbose
        self.dossier: dict[str, Any] = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "generated_by": f"Comet Assistant Master Agent | {ADDRESS} | {PHONE}",
            "model": MODEL,
            "task": "",
            "findings": [],
            "risk_summary": {},
            "report": "",
        }

    def _log(self, msg: str, prefix: str = "[MASTER]") -> None:
        if self.verbose:
            ts = datetime.now().strftime("%H:%M:%S")
            print(f"{ts} {prefix} {msg}")

    def _handle_dispatch(self, agent_name: str, task: str, context: str = "") -> str:
        """Execute a sub-agent dispatch and return its output."""
        self._log(f"Dispatching → {agent_name}: {task[:70]}...")
        result = run_subagent(
            self.client,
            agent_name,
            task,
            context=context,
            verbose=self.verbose,
        )
        self._log(f"Result from {agent_name}: {len(result)} chars", prefix="[RECV]")
        return result

    def _handle_record(
        self,
        category: str,
        title: str,
        detail: str,
        risk_score: float | None = None,
        sources: list[str] | None = None,
    ) -> str:
        """Record a finding to the dossier."""
        finding = {
            "category": category,
            "title": title,
            "detail": detail,
            "risk_score": risk_score,
            "sources": sources or [],
        }
        self.dossier["findings"].append(finding)
        self._log(f"Recorded [{category}]: {title}", prefix="[RECORD]")
        return f"Finding recorded: {title}"

    def run(self, task: str) -> dict[str, Any]:
        """
        Run the master agent on a given intelligence task.
        Returns the completed dossier as a dict.
        """
        self.dossier["task"] = task
        self._log(f"Starting task: {task}")
        self._log(f"Model: {MODEL} | Adaptive thinking: ON")

        master_tools = [
            DISPATCH_TOOL,
            RECORD_FINDING_TOOL,
            WEB_SEARCH_TOOL,
            WEB_FETCH_TOOL,
        ]

        messages: list[dict] = [
            {
                "role": "user",
                "content": (
                    f"Execute the following supply chain intelligence task:\n\n"
                    f"{task}\n\n"
                    "Use your dispatch_subagent tool to coordinate specialized agents. "
                    "Record key findings with record_finding as you go. "
                    "Deliver a comprehensive intelligence report at the end."
                ),
            }
        ]

        max_iterations = 20
        iteration = 0

        with client_stream_context(self.client, MODEL, MASTER_SYSTEM, messages, master_tools) as stream:
            pass  # Initial stream setup handled below

        # Non-streaming agentic loop
        while iteration < max_iterations:
            iteration += 1
            self._log(f"Iteration {iteration}/{max_iterations}")

            response = self.client.messages.create(
                model=MODEL,
                max_tokens=16384,
                system=MASTER_SYSTEM,
                messages=messages,
                tools=master_tools,
                thinking={"type": "adaptive"},
            )

            self._log(f"Stop reason: {response.stop_reason}")

            # Print any text output
            for block in response.content:
                if hasattr(block, "text") and block.text:
                    self._log(
                        textwrap.shorten(block.text, width=120, placeholder="..."),
                        prefix="[TEXT]",
                    )

            if response.stop_reason == "end_turn":
                # Extract final report text
                text_blocks = [b.text for b in response.content if hasattr(b, "text")]
                self.dossier["report"] = "\n\n".join(text_blocks)
                self._log("Task complete.")
                break

            if response.stop_reason in ("tool_use",):
                messages.append({"role": "assistant", "content": response.content})

                tool_results = []
                for block in response.content:
                    if block.type != "tool_use":
                        continue

                    tool_name = block.name
                    tool_input = block.input
                    tool_id = block.id

                    self._log(f"Tool call: {tool_name}", prefix="[TOOL]")

                    # Handle client-side tools
                    if tool_name == "dispatch_subagent":
                        result = self._handle_dispatch(
                            agent_name=tool_input["agent_name"],
                            task=tool_input["task"],
                            context=tool_input.get("context", ""),
                        )
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": result,
                        })

                    elif tool_name == "record_finding":
                        result = self._handle_record(
                            category=tool_input["category"],
                            title=tool_input["title"],
                            detail=tool_input["detail"],
                            risk_score=tool_input.get("risk_score"),
                            sources=tool_input.get("sources"),
                        )
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": result,
                        })

                    else:
                        # Server-side tools (web_search, web_fetch) — handled server-side
                        # but we still need to acknowledge any client-visible tool_use blocks
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": "Server-side tool executed.",
                        })

                if tool_results:
                    messages.append({"role": "user", "content": tool_results})
                continue

            if response.stop_reason == "pause_turn":
                # Server-side tool loop paused; resume
                messages.append({"role": "assistant", "content": response.content})
                continue

            # Unexpected stop; break
            self._log(f"Unexpected stop reason: {response.stop_reason}", prefix="[WARN]")
            break

        # Build risk summary from recorded findings
        scored_findings = [f for f in self.dossier["findings"] if f.get("risk_score") is not None]
        if scored_findings:
            avg_score = sum(f["risk_score"] for f in scored_findings) / len(scored_findings)
            self.dossier["risk_summary"] = {
                "average_score": round(avg_score, 3),
                "level": "HIGH" if avg_score > 0.65 else "MEDIUM" if avg_score > 0.35 else "LOW",
                "total_findings": len(self.dossier["findings"]),
                "scored_findings": len(scored_findings),
            }

        return self.dossier


# ---------------------------------------------------------------------------
# Stream context placeholder (non-streaming run, just a no-op)
# ---------------------------------------------------------------------------

class client_stream_context:
    """No-op context manager — streaming setup placeholder."""
    def __init__(self, *args, **kwargs):
        pass
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Comet Assistant — Master Agentic Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(f"""
        Examples:
          python agent.py --task "Supply chain intelligence: North Sumatra palm oil EUDR compliance"
          python agent.py --task "Risk assessment: Indonesian nickel exporters 2026"
          python agent.py --interactive

        Comet Assistant | {ADDRESS} | {PHONE}
        """),
    )
    parser.add_argument(
        "--task",
        type=str,
        help="Intelligence task to execute",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output JSON file path (default: auto-generated timestamp filename)",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Run in interactive mode (prompt for tasks)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress verbose agent output",
    )

    args = parser.parse_args()
    verbose = not args.quiet

    print(f"""
╔══════════════════════════════════════════════════════════════════╗
║          Comet Assistant — Master Agentic Agent                  ║
║  {ADDRESS:<60}║
║  {PHONE:<60}║
╚══════════════════════════════════════════════════════════════════╝
Model: {MODEL}
Adaptive Thinking: ON
Sub-agents: {", ".join(SUB_AGENT_CONFIGS.keys())}
""")

    if args.interactive:
        print("Interactive mode. Type 'quit' to exit.\n")
        while True:
            try:
                task = input("Task > ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nExiting.")
                break
            if task.lower() in ("quit", "exit", "q"):
                break
            if not task:
                continue
            _run_task(task, args.output, verbose)
    elif args.task:
        _run_task(args.task, args.output, verbose)
    else:
        parser.print_help()
        sys.exit(1)


def _run_task(task: str, output_path: str | None, verbose: bool) -> None:
    """Execute a single task and save the result."""
    start = time.time()
    agent = MasterAgent(verbose=verbose)

    try:
        dossier = agent.run(task)
    except anthropic.AuthenticationError:
        print("\nERROR: Invalid API key. Set ANTHROPIC_API_KEY and try again.")
        sys.exit(1)
    except anthropic.RateLimitError:
        print("\nERROR: Rate limit reached. Please wait and retry.")
        sys.exit(1)
    except anthropic.APIConnectionError:
        print("\nERROR: Network error. Check your internet connection.")
        sys.exit(1)

    elapsed = time.time() - start
    dossier["elapsed_seconds"] = round(elapsed, 1)

    # Determine output path
    if not output_path:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"dossier_{ts}.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dossier, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*60}")
    print(f"Task complete in {elapsed:.1f}s")
    print(f"Findings recorded: {len(dossier['findings'])}")
    if dossier.get("risk_summary"):
        rs = dossier["risk_summary"]
        print(f"Risk level: {rs.get('level', 'N/A')} (score: {rs.get('average_score', 0):.2f})")
    print(f"Dossier saved: {output_path}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
