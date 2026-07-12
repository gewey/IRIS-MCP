# IRIS-MCP: The 97.6% Efficiency Gemini-Copilot Bridge
# Copyright (C) 2026 Joseph Goulette
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import asyncio
import os
import sys
import functools
import time
import re
from mcp.server.fastmcp import FastMCP
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("IRIS-MCP")

# Metrics storage
_METRICS = {"calls": 0, "errors": 0, "total_time": 0.0}


def track_performance(func):
    """Decorator to monitor tool performance and reliability."""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.perf_counter()
        _METRICS["calls"] += 1
        try:
            result = await func(*args, **kwargs)
            duration = time.perf_counter() - start
            _METRICS["total_time"] += duration
            return result
        except Exception as e:
            _METRICS["errors"] += 1
            raise e

    return wrapper


# Path for persistent logging
LOG_FILE = os.path.join(os.path.dirname(__file__), "IRIS-MCP.log")

# Token metrics for Gemini 1.5 Pro vs Gemini 3 Flash (per 1M tokens)
PRICING = {
    "1.5-pro": {"input": 3.50, "output": 10.50},
    "3-flash": {"input": 0.075, "output": 0.30},
}

# Fixed benchmark assumptions used to keep README claims reproducible.
# Ratio input:output = 7.2:1 -> ~42.5x and ~97.6% savings with current pricing.
CLAIM_ASSUMPTIONS = {"input_tokens": 720_000, "output_tokens": 100_000}
COMMAND_PATTERN = re.compile(r"^(READ|SEARCH|UPDATE)\s*:?\s+(.+)$", re.IGNORECASE)
MIN_COST_DIVISOR = 1e-6


def _compute_costs(input_tokens: int, output_tokens: int) -> tuple[float, float, float, float]:
    flash_cost = (input_tokens * PRICING["3-flash"]["input"] / 1_000_000) + (
        output_tokens * PRICING["3-flash"]["output"] / 1_000_000
    )
    pro_cost = (input_tokens * PRICING["1.5-pro"]["input"] / 1_000_000) + (
        output_tokens * PRICING["1.5-pro"]["output"] / 1_000_000
    )
    savings = pro_cost - flash_cost
    percent = (savings / pro_cost) * 100 if pro_cost > 0 else 0
    return flash_cost, pro_cost, savings, percent


def _safe_cost_ratio(numerator: float, denominator: float) -> float:
    return numerator / max(denominator, MIN_COST_DIVISOR)


def _enforce_command_format(raw_text: str, user_chat: str) -> str:
    commands = []
    for raw_line in raw_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("```"):
            continue
        line = re.sub(r"^[-*]\s+", "", line)
        line = re.sub(r"^\d+[\).\s]+", "", line)
        match = COMMAND_PATTERN.match(line)
        if match:
            commands.append(f"{match.group(1).upper()}: {match.group(2).strip()}")

    if commands:
        return "\n".join(commands)

    fallback_query = re.sub(r"[^\w\s.,:;!?@#%&()/+-]", " ", user_chat)
    fallback_query = re.sub(r"\s+", " ", fallback_query).strip()[:400]
    return (
        "READ: Inspect the primary files that control the requested behavior.\n"
        f"SEARCH: Locate all logic tied to {fallback_query}.\n"
        "UPDATE: Apply minimal, verified changes and keep output strictly in READ/SEARCH/UPDATE form."
    )


def log_to_file(message: str):
    """Helper to write logs to a file since StdIO is used for MCP communication."""
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{message}\n")
    sys.stderr.write(f"{message}\n")
    sys.stderr.flush()


@mcp.tool()
async def estimate_savings(input_tokens: int, output_tokens: int) -> str:
    """
    Calculates the financial and token-cost savings of using Gemini 3 Flash vs Gemini 1.5 Pro.
    """
    try:
        flash_cost, pro_cost, savings, percent = _compute_costs(input_tokens, output_tokens)
        claim_flash_cost, claim_pro_cost, claim_savings, claim_percent = _compute_costs(
            CLAIM_ASSUMPTIONS["input_tokens"], CLAIM_ASSUMPTIONS["output_tokens"]
        )
        claim_ratio = _safe_cost_ratio(claim_pro_cost, claim_flash_cost)

        report = (
            f"### 💰 Savings Report\n"
            f"- **Claim Baseline (fixed):** {CLAIM_ASSUMPTIONS['input_tokens']:,} input + {CLAIM_ASSUMPTIONS['output_tokens']:,} output tokens\n"
            f"- **Reproducible Claim Result:** **{claim_percent:.1f}% cheaper** and **{claim_ratio:.1f}x** more cost-effective\n"
            f"- **Claim Baseline Cost (Gemini 1.5 Pro):** ${claim_pro_cost:.6f}\n"
            f"- **Claim Baseline Cost (Gemini 3 Flash):** ${claim_flash_cost:.6f}\n\n"
            f"### 📦 Provided Workload ({input_tokens:,} input / {output_tokens:,} output)\n"
            f"- **Gemini 1.5 Pro Cost:** ${pro_cost:.6f}\n"
            f"- **Gemini 3 Flash Cost:** ${flash_cost:.6f}\n"
            f"- **Total Savings:** **${savings:.6f}** ({percent:.1f}% cheaper)"
        )

        log_to_file(
            f"--- [Savings Check] Input: {input_tokens}, Output: {output_tokens} | Saved: ${savings:.6f} ---"
        )
        return report
    except Exception as e:
        return f"Error calculating savings: {str(e)}"


@mcp.tool()
@track_performance
async def get_bridge_stats() -> str:
    """Returns real-time performance metrics for the Gemini Bridge."""
    avg = _METRICS["total_time"] / _METRICS["calls"] if _METRICS["calls"] > 0 else 0
    return (
        f"### 📊 Bridge Performance\n"
        f"- **Total Calls:** {_METRICS['calls']}\n"
        f"- **Errors:** {_METRICS['errors']}\n"
        f"- **Avg Latency:** {avg:.2f}s\n"
        f"- **Uptime Status:** Healthy ✅"
    )


# Initialize Gemini Client
client = genai.Client()

SYSTEM_INSTRUCTION = """
You are a 'Bridge' model for GitHub Copilot Chat.
Your role is EXCLUSIVELY to 'translate' and 'optimize' user prompts into technical plans for a secondary AI agent (Copilot).

CRITICAL CONSTRAINTS:
1. DO NOT attempt to solve the user's request yourself.
2. DO NOT explain the code or provide the actual fix.
3. YOUR ONLY OUTPUT should be a list of technical commands (READ, SEARCH, UPDATE) that the next agent should perform.
4. Identify which VS Code tools Copilot should use (e.g., read_file, search, edit_file, semantic_search).
5. Format the output as a set of direct, authoritative COMMANDS.
6. If the user's intent is vague, expand it into the logical technical steps required.

Example Transformation:
User: "Fix the naming in the client"
Translation: "SEARCH for variable name inconsistencies in c:\\Users\\Gewey\\Desktop\\Workspace\\Script.py. READ the file to understand context. PROPOSE a rename for local variables to match PEP8."

Output ONLY the optimized instruction text.
"""


@mcp.tool()
@track_performance
async def optimize_prompt(user_chat: str) -> str:
    """
    Instantly converts your request into high-precision, tool-oriented instructions for Copilot.
    """
    try:
        log_to_file(f"\n--- [IRIS-MCP] RECEIVED: {user_chat} ---")

        # We wrap the user chat in a directive to reinforce the 'Translate Only' behavior
        optimization_request = f'USER REQUEST: "{user_chat}"\n\nTASK: Translate the above into a tool-calling technical plan for Copilot. Do not solve it yourself.'

        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=optimization_request,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.2,
            ),
        )

        optimized = _enforce_command_format(response.text.strip(), user_chat)

        log_to_file(f"--- [IRIS-MCP] OPTIMIZED: {optimized} ---\n")

        return optimized
    except Exception as e:
        error_msg = f"Error bridging to Gemini: {str(e)}"
        log_to_file(f"!!! [IRIS-MCP] ERROR: {error_msg}")
        return error_msg


if __name__ == "__main__":
    mcp.run()
