#!/usr/bin/env python3
"""PostToolUse hook executor for hookify.

Called by Claude Code after a tool executes.
Reads .claude/hookify.*.local.md files and evaluates matching rules.
"""

import os
import sys
import json

# Add .claude/ to sys.path so "from hookify.core..." imports resolve.
_claude_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _claude_dir not in sys.path:
    sys.path.insert(0, _claude_dir)

try:
    from hookify.core.config_loader import load_rules
    from hookify.core.rule_engine import RuleEngine
except ImportError as e:
    print(json.dumps({"systemMessage": f"Hookify import error: {e}"}))
    sys.exit(0)


def main():
    """Main entry point for PostToolUse hook."""
    try:
        input_data = json.load(sys.stdin)

        tool_name = input_data.get('tool_name', '')
        if tool_name == 'Bash':
            event = 'bash'
        elif tool_name in ['Edit', 'Write', 'MultiEdit']:
            event = 'file'
        else:
            event = None

        rules = load_rules(event=event)
        result = RuleEngine().evaluate_rules(rules, input_data)
        print(json.dumps(result))

    except Exception as e:
        print(json.dumps({"systemMessage": f"Hookify error: {str(e)}"}))

    finally:
        sys.exit(0)


if __name__ == '__main__':
    main()
