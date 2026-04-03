#!/bin/bash
# Hook: inject DockLabs engineering principles before any file edit.

REPO_NAME=$(basename "$CLAUDE_PROJECT_DIR")
PRINCIPLES="$HOME/.claude/projects/-Users-dok-Code-CT-${REPO_NAME}/memory/docklabs_principles.md"

# Fall back to harbor (the original home)
if [ ! -f "$PRINCIPLES" ]; then
  PRINCIPLES="$HOME/.claude/projects/-Users-dok-Code-CT-harbor/memory/docklabs_principles.md"
fi

if [ ! -f "$PRINCIPLES" ]; then
  echo "REMINDER: DockLabs Engineering Principles doc not found. Ensure docklabs_principles.md exists in project memory."
  exit 0
fi

cat <<'EOF'
DOCKLABS PRINCIPLES CHECK — Before editing, verify:
- Does this change comply with the DockLabs Engineering Principles?
- If this adds agency-submitted content or communications, is it registered with foia_export_registry?
- If this change establishes a new cross-product pattern or decision, update docklabs_principles.md.
EOF

exit 0
