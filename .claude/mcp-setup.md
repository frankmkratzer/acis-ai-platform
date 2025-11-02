# MCP Server Setup for ACIS AI Platform

## PostgreSQL MCP Server

This project uses the Model Context Protocol (MCP) to give Claude direct access to the PostgreSQL database.

### What is MCP?

MCP (Model Context Protocol) allows Claude to interact with external tools and data sources securely. Instead of manually writing SQL queries via bash, Claude can use specialized database tools.

### Installed MCP Servers

#### 1. PostgreSQL Server (`postgres-acis`)

**Purpose**: Direct database access for queries, schema inspection, and data retrieval.

**Configuration**: See `.claude/mcp.json`

**Available Tools**:
- `query` - Execute SQL queries (read-only recommended)
- `list_tables` - Show all tables in database
- `describe_table` - Get table schema
- `list_schemas` - Show database schemas

**Connection String**:
```
postgresql://postgres:$@nJose420@localhost:5432/acis-ai
```

### Setup Instructions

#### For Claude Desktop

1. **Install the MCP server**:
   ```bash
   npm install -g @modelcontextprotocol/server-postgres
   ```

2. **Configure Claude Desktop** (`~/.config/Claude/claude_desktop_config.json` on Linux):
   ```json
   {
     "mcpServers": {
       "postgres-acis": {
         "command": "npx",
         "args": [
           "-y",
           "@modelcontextprotocol/server-postgres",
           "postgresql://postgres:$@nJose420@localhost:5432/acis-ai"
         ]
       }
     }
   }
   ```

3. **Restart Claude Desktop**

4. **Verify**: Look for MCP tools in Claude's tool list (🔌 icon)

#### For Claude Code (VS Code Extension)

The `.claude/mcp.json` file in this project is automatically detected by Claude Code.

1. **Install the MCP server** (if not already installed):
   ```bash
   npm install -g @modelcontextprotocol/server-postgres
   ```

2. **Restart VS Code**

3. **Verify**: Claude Code will show available MCP tools when you start a conversation

### Usage Examples

Once configured, you can ask Claude:

```
"Show me all tables in the database"
"Describe the daily_bars table schema"
"Query the last 10 trades from paper_positions"
"Get the latest date in ml_training_features"
"Show me clients with risk_tolerance = 'aggressive'"
```

Claude will use the MCP tools instead of bash commands.

### Security Considerations

⚠️ **Important Security Notes**:

1. **Read-Only Access**: Consider creating a read-only database user for MCP:
   ```sql
   CREATE USER claude_readonly WITH PASSWORD 'secure_password';
   GRANT CONNECT ON DATABASE "acis-ai" TO claude_readonly;
   GRANT USAGE ON SCHEMA public TO claude_readonly;
   GRANT SELECT ON ALL TABLES IN SCHEMA public TO claude_readonly;
   ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO claude_readonly;
   ```

2. **Connection String**: The password is in plain text in config files. Options:
   - Use environment variables: `postgresql://postgres:${PGPASSWORD}@localhost:5432/acis-ai`
   - Use `.pgpass` file for password management
   - Use read-only user (recommended)

3. **Query Limits**: The MCP server doesn't have built-in query limits. Monitor usage.

### Future MCP Servers to Consider

Other useful MCP servers for this project:

1. **Filesystem MCP** - Direct file access for logs, models, results
   ```bash
   npm install -g @modelcontextprotocol/server-filesystem
   ```

2. **GitHub MCP** - Repository operations
   ```bash
   npm install -g @modelcontextprotocol/server-github
   ```

3. **Custom ACIS MCP Server** - Platform-specific tools
   - `get_ml_features(ticker, date_range)`
   - `get_portfolio_positions(account_id)`
   - `get_model_performance(model_name)`
   - `backtest_strategy(config)`

### Troubleshooting

**MCP server not showing up**:
1. Check that `npx` is in PATH
2. Restart Claude Desktop/VS Code
3. Check logs: `~/.config/Claude/logs/` (Claude Desktop)

**Connection errors**:
1. Verify PostgreSQL is running: `systemctl status postgresql`
2. Test connection: `psql postgresql://postgres:$@nJose420@localhost:5432/acis-ai`
3. Check firewall rules

**Permission denied**:
1. Verify database user has permissions
2. Check `pg_hba.conf` for localhost connections

### Creating a Custom MCP Server (Optional)

If you want ACIS-specific tools, we can create a custom Python MCP server:

**File**: `mcp_server/acis_mcp_server.py`

**Custom Tools**:
- Portfolio health checks
- Model performance queries
- Feature extraction helpers
- Trade signal generation
- Backtest shortcuts

See `mcp_server/README.md` for implementation guide.

### Resources

- [MCP Documentation](https://modelcontextprotocol.io)
- [PostgreSQL MCP Server](https://github.com/modelcontextprotocol/servers/tree/main/src/postgres)
- [Claude Desktop MCP Setup](https://docs.anthropic.com/claude/docs/mcp)

---

**Last Updated**: November 2, 2025
