# Filesystem MCP Server

A local MCP server that reads and writes files over stdio. Every path must stay inside the directories you pass on the command line.

Requires Python 3.10 or newer and [uv](https://docs.astral.sh/uv/).

## Run

Each argument is an allowed directory. It must already exist.

```bash
uv run filesystem-mcp /absolute/path/you/allow
```

The process stays quiet. It waits for a client on stdin. Stop it with Ctrl-C.

To try it in the MCP Inspector, from a second terminal:

```bash
npx @modelcontextprotocol/inspector --cwd . -- uv run filesystem-mcp /absolute/path/you/allow
```

## Tools

- `list_allowed_directories`
- `list_directory`
- `read_text_file`
- `write_file`

Text files must be valid UTF-8 and at most 1 MiB. `write_file` overwrites an existing file and does not create parent directories.

## Tests

```bash
uv run pytest
```
