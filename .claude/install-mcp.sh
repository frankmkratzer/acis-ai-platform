#!/bin/bash
# Install MCP servers for ACIS AI Platform

set -e

echo "Installing MCP servers for ACIS AI Platform..."

# Install PostgreSQL MCP server
echo "1. Installing PostgreSQL MCP server..."
if command -v npm &> /dev/null; then
    npm install -g @modelcontextprotocol/server-postgres || {
        echo "Permission denied. Trying with sudo..."
        sudo npm install -g @modelcontextprotocol/server-postgres
    }
    echo "✅ PostgreSQL MCP server installed"
else
    echo "❌ npm not found. Please install Node.js first."
    exit 1
fi

# Test installation
echo ""
echo "2. Testing MCP server installation..."
if npx @modelcontextprotocol/server-postgres --version &> /dev/null; then
    echo "✅ MCP server is working"
else
    echo "⚠️  MCP server installed but test failed. This may be normal."
fi

# Create Claude Desktop config (if applicable)
echo ""
echo "3. Claude Desktop Configuration"
CLAUDE_CONFIG_DIR="$HOME/.config/Claude"
CLAUDE_CONFIG_FILE="$CLAUDE_CONFIG_DIR/claude_desktop_config.json"

if [ -d "$CLAUDE_CONFIG_DIR" ]; then
    echo "Claude Desktop detected at $CLAUDE_CONFIG_DIR"

    # Backup existing config
    if [ -f "$CLAUDE_CONFIG_FILE" ]; then
        echo "Backing up existing config..."
        cp "$CLAUDE_CONFIG_FILE" "$CLAUDE_CONFIG_FILE.backup.$(date +%Y%m%d_%H%M%S)"
    fi

    # Create or update config
    cat > "$CLAUDE_CONFIG_FILE" << 'EOF'
{
  "mcpServers": {
    "postgres-acis": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-postgres",
        "postgresql://claude_readonly:claude_read_2025!@localhost:5432/acis-ai"
      ]
    }
  }
}
EOF
    echo "✅ Claude Desktop config updated at $CLAUDE_CONFIG_FILE"
    echo "   Please restart Claude Desktop to activate MCP server"
else
    echo "ℹ️  Claude Desktop not found. Skipping desktop configuration."
    echo "   MCP will still work in Claude Code (VS Code extension)"
fi

echo ""
echo "═══════════════════════════════════════════════════════"
echo "✅ MCP Setup Complete!"
echo "═══════════════════════════════════════════════════════"
echo ""
echo "Next steps:"
echo "1. Restart Claude Desktop (if installed)"
echo "2. Restart VS Code (if using Claude Code extension)"
echo "3. Look for the 🔌 icon in Claude to see available MCP tools"
echo ""
echo "Available MCP tools:"
echo "  - query: Execute SQL queries (read-only)"
echo "  - list_tables: Show all database tables"
echo "  - describe_table: Get table schema"
echo "  - list_schemas: Show database schemas"
echo ""
echo "Try asking Claude:"
echo '  "Show me all tables in the database"'
echo '  "Describe the daily_bars table"'
echo '  "Query the last 10 rows from paper_positions"'
echo ""
