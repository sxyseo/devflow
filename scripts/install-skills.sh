#!/bin/bash

# DevFlow Auto-Dev - Install SKILLS to OpenClaw Workspace
# Copies all SKILL.md files from project skills/ to ~/.openclaw/workspace/skills/

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
OPENCLAW_DIR="$HOME/.openclaw"
OPENCLAW_SKILLS_DIR="$OPENCLAW_DIR/workspace/skills"

echo "========================================"
echo "DevFlow Auto-Dev - Install SKILLS"
echo "========================================"
echo ""

# Ensure OpenClaw skills directory exists
echo -e "${YELLOW}Ensuring OpenClaw workspace exists...${NC}"
mkdir -p "$OPENCLAW_SKILLS_DIR"
echo -e "${GREEN}OpenClaw workspace ready${NC}"
echo ""

# Check if project skills directory exists
if [ ! -d "$PROJECT_DIR/skills" ]; then
    echo -e "${RED}Error: No skills/ directory found in project${NC}"
    echo "Expected: $PROJECT_DIR/skills/"
    exit 1
fi

# Install skills from project to OpenClaw workspace
echo -e "${YELLOW}Installing SKILLS to OpenClaw workspace...${NC}"
echo "Source: $PROJECT_DIR/skills/"
echo "Target: $OPENCLAW_SKILLS_DIR/"
echo ""

INSTALLED_COUNT=0
FAILED_COUNT=0

for skill_dir in "$PROJECT_DIR/skills"/*/; do
    if [ -d "$skill_dir" ]; then
        skill_name=$(basename "$skill_dir")

        if [ -f "$skill_dir/SKILL.md" ]; then
            # Create target directory and copy skill files
            mkdir -p "$OPENCLAW_SKILLS_DIR/$skill_name"
            cp -r "$skill_dir"* "$OPENCLAW_SKILLS_DIR/$skill_name/"
            echo -e "${GREEN}  Installed: $skill_name${NC}"
            INSTALLED_COUNT=$((INSTALLED_COUNT + 1))
        else
            echo -e "${YELLOW}  Skipped: $skill_name (no SKILL.md)${NC}"
        fi
    fi
done

echo ""

# Create placeholder directories for expected skills that don't exist yet
EXPECTED_SKILLS=("taskmaster" "bmad" "spec-driven")
for skill in "${EXPECTED_SKILLS[@]}"; do
    if [ ! -d "$OPENCLAW_SKILLS_DIR/$skill" ]; then
        mkdir -p "$OPENCLAW_SKILLS_DIR/$skill"
        echo -e "${YELLOW}  Created placeholder: $skill${NC}"
    fi
done

echo ""

# Summary
echo "========================================"
echo -e "${GREEN}SKILLS Installation Complete${NC}"
echo "========================================"
echo ""
echo "Installed: $INSTALLED_COUNT skill(s)"
echo "Location:  $OPENCLAW_SKILLS_DIR/"
echo ""
echo "Installed skills:"
ls -1 "$OPENCLAW_SKILLS_DIR" 2>/dev/null | while read -r skill; do
    if [ -f "$OPENCLAW_SKILLS_DIR/$skill/SKILL.md" ]; then
        echo "  - $skill (SKILL.md present)"
    else
        echo "  - $skill (placeholder)"
    fi
done
echo ""
echo "Next steps:"
echo "  1. Start OpenClaw: openclaw start --port 4444"
echo "  2. Verify skills: curl http://localhost:4444/skills"
echo ""
