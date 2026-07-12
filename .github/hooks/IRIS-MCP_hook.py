# IRIS-MCP Hook: Prompt Interception Layer
# Copyright (C) 2026 Joseph Goulette
# Licensed under the GNU Affero General Public License v3.0
import sys
import json
import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def main():
    try:
        # Read the hook input from stdin
        input_data = json.load(sys.stdin)
        user_prompt = input_data.get("prompt", "")

        if not user_prompt:
            print(json.dumps({"continue": True}))
            return

        # Initialize Gemini Client
        # Assumes GOOGLE_API_KEY is set in environment
        client = genai.Client()

        SYSTEM_INSTRUCTION = """
        You are an 'Optimization Hook' for GitHub Copilot.
        Your ONLY goal is to intercept the user's raw prompt and rewrite it into a high-signal technical command set for the Copilot agent.

        CRITICAL: DO NOT attempt to solve the request yourself. DO NOT provide code fixes.
        ONLY provide the plan of action using authoritative commands (READ, SEARCH, UPDATE).

        FORMAT: Output ONLY the rewritten prompt plan.
        """

        # Reinforce the directive in the user message
        optimization_request = f'USER PROMPT: "{user_prompt}"\n\nTRANSLATION TASK: Rewrite this into a technical tool-calling plan. Do not execute or solve.'

        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=optimization_request,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.1,
            ),
        )

        optimized = response.text.strip()

        # Verbatim logging to stderr
        sys.stderr.write(f"\n--- [IRIS-MCP Hook] Input ---\n{user_prompt}\n")
        sys.stderr.write(
            f"--- [IRIS-MCP Hook] Verbatim Output ---\n{optimized}\n----------------------------------\n"
        )

        # In a UserPromptSubmit hook, we can inject context or modify behavior.
        # Note: Depending on the specific Copilot implementation, we might
        # return the optimized text as 'additionalContext' or similar.
        # For this logic, we'll suggest it as a system message/context injection.

        output = {
            "continue": True,
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": f"OPTIMIZED PLAN (FOLLOW THIS): {optimized}",
            },
        }

        print(json.dumps(output))

    except Exception as e:
        # Log the error to stderr so the user can see why it failed in the Output panel
        sys.stderr.write(f"--- [IRIS-MCP Hook] ERROR: {str(e)} ---\n")
        # If it fails, just continue with original prompt so we don't break the chat
        print(json.dumps({"continue": True}))


if __name__ == "__main__":
    main()
