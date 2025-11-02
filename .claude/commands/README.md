# ACIS AI Platform - Slash Commands

Quick commands for daily operations and common tasks.

## Available Commands

### Daily Operations

#### `/status`
Quick system health check - shows database, API, models, and service status.
```
Usage: /status
```

#### `/today`
Shows today's tasks and what needs to be done (EOD pipeline, rebalancing, checks).
```
Usage: /today
```

#### `/logs`
Show recent logs with filtering options.
```
Usage: /logs
```

### Model Management

#### `/models`
List all trained models with performance metrics and production status.
```
Usage: /models
```

#### `/train`
Quick model training with sensible defaults.
```
Usage: /train
```

#### `/deploy`
Deploy a model to production with safety checks.
```
Usage: /deploy
```

### Database

#### `/db`
Quick database queries and information.
```
Usage: /db
```

#### `/clients`
Access client information and portfolios.
```
Usage: /clients
```

## How Slash Commands Work

Slash commands are simpler and more focused than skills. They:
- Execute quickly with minimal user input
- Use sensible defaults
- Are perfect for daily operations
- Format output consistently

## Slash Commands vs Skills

**Use Slash Commands for:**
- Quick status checks
- Daily routine tasks
- Simple queries
- Fast information retrieval

**Use Skills for:**
- Complex multi-step workflows
- Tasks requiring configuration
- Interactive processes
- Full automation workflows

## Creating New Commands

1. Create a markdown file in `.claude/commands/`
2. Add frontmatter with description:
   ```markdown
   ---
   description: What this command does
   ---

   Command instructions here...
   ```
3. Commands are automatically available as `/command-name`

## Examples

```bash
# Check system health
/status

# See what needs to be done today
/today

# List all models
/models

# Check recent logs
/logs

# Train a new model
/train

# Deploy model to production
/deploy

# Query database
/db

# View client portfolios
/clients
```

## Tips

- Commands execute faster than skills
- Use `/status` first thing each day
- Use `/today` to plan your work
- Use `/logs` when troubleshooting
- Chain commands for workflows: `/status` → `/today` → `/logs`

## Documentation

For more complex workflows, use skills in `.claude/skills/`
