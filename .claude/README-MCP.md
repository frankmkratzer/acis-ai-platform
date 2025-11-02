# MCP (Model Context Protocol) Setup

## What is MCP?

MCP allows Claude to interact with external tools and data sources. For ACIS AI Platform, we've configured a PostgreSQL MCP server that gives Claude direct database access.

## Quick Start

### Option 1: Using npx (Simplest - No Installation Required)

The MCP configuration in `.claude/mcp.json` uses `npx` which automatically downloads the MCP server when needed. **No installation required!**

Just restart Claude Code or Claude Desktop and the MCP server will work automatically.

### Option 2: Install Globally (Faster Startup)

```bash
# Run the installation script
bash .claude/install-mcp.sh
```

OR manually:

```bash
# Install with npm (may need sudo)
npm install -g @modelcontextprotocol/server-postgres

# OR with sudo if permission denied
sudo npm install -g @modelcontextprotocol/server-postgres
```

## Configuration Files

### For Claude Code (VS Code Extension)
- Location: `.claude/mcp.json` (this file)
- Auto-detected when you open the project

### For Claude Desktop
- Location: `~/.config/Claude/claude_desktop_config.json`
- Run `bash .claude/install-mcp.sh` to auto-configure

## Database Access

### Current Configuration (Full Access)
```
postgresql://postgres:$@nJose420@localhost:5432/acis-ai
```

Uses the main `postgres` user with full database access.

### Read-Only Access (Optional - More Secure)
If you want Claude to have read-only access, update `.claude/mcp.json`:

```json
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
```

**Note**: The `claude_readonly` user has been created but may need pg_hba.conf configuration for password auth.

## Available MCP Tools

Once configured, Claude will have access to these tools:

### 1. `query` - Execute SQL Queries
```
Example: "Query the last 10 rows from daily_bars"
```

### 2. `list_tables` - List All Tables
```
Example: "Show me all tables in the database"
```

### 3. `describe_table` - Get Table Schema
```
Example: "Describe the ml_training_features table"
```

### 4. `list_schemas` - List Database Schemas
```
Example: "What schemas are in the database?"
```

## Usage Examples

Once MCP is configured, you can ask Claude natural language questions:

```
"Show me all tables in the acis-ai database"
"Describe the structure of the daily_bars table"
"Query the latest 5 entries from paper_positions"
"How many rows are in ml_training_features?"
"Get all clients with risk_tolerance = 'aggressive'"
"Show me the columns in the ratios table"
```

Claude will use the MCP tools automatically instead of bash commands.

## Verification

To verify MCP is working:

1. **Claude Code**: Look for MCP server status in the bottom status bar
2. **Claude Desktop**: Look for the 🔌 icon indicating MCP tools are available
3. **Ask Claude**: "What MCP tools do you have available?"

## Troubleshooting

### MCP Server Not Showing Up

1. **Check npx is in PATH**:
   ```bash
   which npx
   # Should return: /usr/bin/npx or similar
   ```

2. **Test MCP server manually**:
   ```bash
   npx @modelcontextprotocol/server-postgres --help
   ```

3. **Restart Claude**:
   - Claude Desktop: Quit and reopen
   - Claude Code: Reload VS Code window (`Ctrl+Shift+P` → "Reload Window")

### Connection Errors

1. **Verify PostgreSQL is running**:
   ```bash
   systemctl status postgresql
   ```

2. **Test database connection**:
   ```bash
   PGPASSWORD='$@nJose420' psql -U postgres -d acis-ai -h localhost -c "SELECT 1;"
   ```

3. **Check connection string** in `.claude/mcp.json`

### Permission Denied

1. **Verify database user has permissions**:
   ```bash
   PGPASSWORD='$@nJose420' psql -U postgres -d acis-ai -h localhost -c "\du"
   ```

2. **Check pg_hba.conf** for localhost password authentication:
   ```bash
   sudo cat /etc/postgresql/*/main/pg_hba.conf | grep localhost
   ```

## Security Considerations

⚠️ **The database password is in plain text in the MCP config file.**

### Options to Improve Security:

1. **Use read-only user** (already created: `claude_readonly`)
2. **Use environment variables**:
   ```json
   "postgresql://postgres:${PGPASSWORD}@localhost:5432/acis-ai"
   ```
3. **Use .pgpass file** for password management
4. **Restrict MCP to SELECT only** by using read-only user

### Creating Read-Only User (Already Done)

The `claude_readonly` user has been created with SELECT-only permissions:
```sql
-- Already executed:
CREATE USER claude_readonly WITH PASSWORD 'claude_read_2025!';
GRANT CONNECT ON DATABASE "acis-ai" TO claude_readonly;
GRANT USAGE ON SCHEMA public TO claude_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO claude_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO claude_readonly;
```

## Next Steps

1. ✅ MCP configuration created (`.claude/mcp.json`)
2. ✅ Read-only database user created (`claude_readonly`)
3. ⏭️ Restart Claude Desktop or VS Code to activate MCP
4. ⏭️ Test by asking Claude to "Show all tables"
5. ⏭️ (Optional) Switch to read-only user for better security

## Resources

- [MCP Documentation](https://modelcontextprotocol.io)
- [PostgreSQL MCP Server](https://github.com/modelcontextprotocol/servers/tree/main/src/postgres)
- [Claude MCP Guide](https://docs.anthropic.com/claude/docs/mcp)
