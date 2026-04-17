#!/usr/bin/env python3
"""UserPromptSubmit hook executor for hookify.

Called by Claude Code when the user submits a prompt.
Reads .claude/hookify.*.local.md files and evaluates prompt rules.
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
    """Main entry point for UserPromptSubmit hook."""
    try:
        input_data = json.load(sys.stdin)

        rules = load_rules(event='prompt')
        result = RuleEngine().evaluate_rules(rules, input_data)
        print(json.dumps(result))

    except Exception as e:
        print(json.dumps({"systemMessage": f"Hookify error: {str(e)}"}))

    finally:
        sys.exit(0)


if __name__ == '__main__':
    main()
