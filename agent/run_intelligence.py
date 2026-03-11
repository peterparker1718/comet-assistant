"""
Comet Assistant — Indonesia US Import Intelligence Runner
Uses claude-agent-sdk (handles auth via Claude Code session)
"""

import anyio
import json
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage, SystemMessage

TASK = """
You are Comet Assistant's Master Intelligence Agent. Produce a comprehensive
supply chain intelligence dossier on the TOP items Indonesia exports to American
companies.

Focus areas (NOT palm oil):
1. Electronics & Components (e.g., circuit boards, semiconductor parts, phone components)
2. Apparel & Textiles (garments, footwear — major US brands sourcing from Indonesia)
3. Rubber & Tires (natural rubber, tire manufacturers)
4. Shrimp & Seafood (top Indonesian seafood imports to US)
5. Coffee (Indonesian coffee varieties imported by US brands)
6. Furniture & Wood Products (US furniture retailers sourcing from Indonesia)
7. Nickel & Metals (EV battery supply chain, stainless steel)
8. Petroleum Products (LNG, coal, crude)

For EACH category provide:
- Estimated US import value (USD, most recent year available)
- Top 3-5 named American companies importing from Indonesia
- Top 3-5 named Indonesian exporters/producers
- Key supply chain risks (tariffs, geopolitical, labor, logistics)
- Current tariff rates (Section 301, MFN rates, GSP eligibility)
- Any active trade disputes or regulatory changes in 2024-2026

Use web search to get current, accurate data. Cite sources.
Organize your final output as a structured intelligence dossier with:
- Executive Summary
- Category-by-category breakdown
- Risk Matrix table
- Key American Companies Exposure Summary
- Recommended Actions for US importers

Be specific with company names, dollar figures, and dates.
"""

async def main():
    print("""
╔══════════════════════════════════════════════════════════════╗
║        Comet Assistant — Indonesia → US Import Intel         ║
║   1704 Surf Avenue, Belmar, NJ 07719 | (609) 276-3372        ║
╚══════════════════════════════════════════════════════════════╝
Launching agentic intelligence run...
""")

    full_result = ""
    session_id = None

    async for message in query(
        prompt=TASK,
        options=ClaudeAgentOptions(
            allowed_tools=["WebSearch", "WebFetch"],
            max_turns=40,
            system_prompt=(
                "You are Comet Assistant's Master Intelligence Agent — an expert in "
                "global trade, supply chain analysis, and US-Indonesia commercial relationships. "
                "Be specific, cite sources, use real company names and dollar figures. "
                "Produce a professional intelligence dossier."
            ),
        ),
    ):
        if isinstance(message, SystemMessage) and message.subtype == "init":
            session_id = message.data.get("session_id", "unknown")
            print(f"Session: {session_id}\n")
        elif isinstance(message, ResultMessage):
            full_result = message.result
            print("\n" + "="*60)
            print("INTELLIGENCE DOSSIER COMPLETE")
            print("="*60 + "\n")
            print(full_result)

    # Save to file
    output = {
        "title": "Indonesia → United States: Top Import Supply Chain Intelligence",
        "generated_by": "Comet Assistant | 1704 Surf Avenue, Belmar, NJ 07719 | (609) 276-3372",
        "session_id": session_id,
        "dossier": full_result,
    }

    with open("/home/user/comet-assistant/agent/dossier_indonesia_us_imports.json", "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    with open("/home/user/comet-assistant/agent/dossier_indonesia_us_imports.md", "w") as f:
        f.write(f"# Indonesia → United States: Top Import Supply Chain Intelligence\n\n")
        f.write(f"*Comet Assistant | 1704 Surf Avenue, Belmar, NJ 07719 | (609) 276-3372*\n\n")
        f.write(full_result)

    print(f"\nSaved: dossier_indonesia_us_imports.json")
    print(f"Saved: dossier_indonesia_us_imports.md")

anyio.run(main)
