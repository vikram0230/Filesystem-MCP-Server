# Filesystem MCP Server

## Purpose

Build a local filesystem MCP server in this repository so a host such as Cursor can launch it and use a small set of file tools inside an explicit sandbox.

Success means:

- The host starts one Python process and speaks MCP over stdio.
- Every file operation stays inside the directories given on the command line.
- The four v1 tools work, and predicted failures come back as tool errors the model can read.
- The path checker, the tools, and a stdio handshake are covered by pytest.

This is a learning project. The official `mcp` SDK owns the session. The code we write owns the sandbox and the tools.

## Stack

- Python 3.10 or newer.
- Official MCP Python SDK, package `mcp` version 2 (`mcp>=2,<3`).
- High-level `MCPServer` from `mcp.server`. `run()` with no transport argument serves stdio.
- Project managed with `uv` and `pyproject.toml`.
- Tests run with pytest.

The server is a console script named `filesystem-mcp`.

## Out of scope

v1 does not implement resources, prompts, client roots, directory creation, move, search, edit, media reads, multi-file reads, or directory trees. Those can be later tools. They are not required for the first host session.

## Architecture

One process. The host launches `filesystem-mcp` and passes allowed directories as positional arguments. `MCPServer.run()` reads JSON-RPC from stdin and writes JSON-RPC to stdout. Logs go to stderr through the `logging` module. The process writes no ordinary text to stdout.

Three modules:

| Module | Job | Depends on |
| --- | --- | --- |
| `filesystem_mcp.server` | Parse allowed directories, build the `MCPServer` for those roots, call `run()` only from `main()` | SDK and tools |
| `filesystem_mcp.paths` | Turn a requested path into a canonical path inside an allowed root, or refuse it | Python standard library only |
| `filesystem_mcp.tools` | Register the four tools on a server for a given set of roots | Path checker, then ordinary file operations |

`paths` does not import the SDK. Tools call `resolve` before any filesystem operation. Tool functions stay thin: validate, do one operation, return text.

A `read_text_file` call arrives on stdin as `tools/call`. The SDK checks the arguments against the schema generated from the function. The tool calls `resolve`. When the path is inside a root, the tool reads the file and returns the text. The SDK writes that result to stdout.

The server exits before `run()` when no allowed directory was given, or when any allowed directory does not exist. The reason goes to stderr.

Suggested layout:

```
pyproject.toml
src/filesystem_mcp/__init__.py
src/filesystem_mcp/__main__.py
src/filesystem_mcp/server.py
src/filesystem_mcp/paths.py
src/filesystem_mcp/tools.py
tests/test_paths.py
tests/test_tools.py
tests/test_stdio.py
```

`__main__.py` calls `main`, so `python -m filesystem_mcp` and `filesystem-mcp` behave the same. Importing the package does not parse arguments and does not call `run()`.

`build_server(roots) -> MCPServer` creates a server named `filesystem` and registers the tools against those roots. `main()` parses the command line, checks that each allowed directory exists, calls `build_server`, then `run()`. Tests call `build_server` with a temporary root.

The server instructions are: "Call list_allowed_directories before guessing paths. Every path must stay inside those directories."

## Path checker

`resolve(path, roots) -> canonical path` is the only way a tool obtains a path.

### Roots at startup

Each command-line argument is expanded, including `~`, made absolute, and resolved with realpath. When the given path and its realpath differ, as with `/tmp` and `/private/tmp` on macOS, both spellings are stored and either one matches later. The roots are stored in command-line order.

A directory that does not exist is a startup error. Zero directories is a startup error. Both print a usage line to stderr and exit with a non-zero status before any MCP message.

### Resolve algorithm

1. Expand `~`.
2. An absolute path is taken as given. A relative path is joined, in command-line order, to each allowed root. The first candidate whose canonical path sits inside that same root wins.
3. If the path exists, realpath it. If it does not, realpath the nearest existing parent and rejoin the leftover names. The parent must exist and sit inside a root. A missing intermediate directory is a refusal, so `write_file` cannot create `a/b/c.txt` when `a/b` is absent.
4. Allow the result only when it equals an allowed root or is strictly inside one: `root` plus the platform path separator. Compare against both the original root and its realpath.
5. Any other result is a refusal. The error names the path the caller sent and says it is outside the allowed directories.

A symlink is judged by its real location. A link inside a root that points at another path inside a root is allowed. A link that points outside is refused. Tools receive only the canonical path `resolve` returns.

A sibling directory whose name merely starts with the root name is refused. If `/safe` is allowed, `/safe/notes.txt` is allowed and `/safe-but-secret` is refused.

## Tools

Each tool is a function registered with `@mcp.tool()`. The SDK builds the input schema from type hints and rejects a non-matching call before the function runs. Docstrings are the tool descriptions. Every path argument goes through `resolve` first.

Annotations use `mcp.types.ToolAnnotations`. They are host hints. The path checker remains the security boundary. All four tools set `open_world_hint=False`.

### `list_allowed_directories`

No arguments. Read-only. Returns the stored roots, one per line, in command-line order. When a root's given path and realpath differ, both lines are included, given path first.

### `list_directory`

Argument: `path: str`. Read-only. Lists immediate children of that directory, sorted by name, one per line, as `[DIR] name` or `[FILE] name`. Names are the entry names, not full paths. Hidden names are included. The listing does not recurse.

The label follows the entry type. A symlink is labeled `[DIR]` when its target is a directory inside an allowed root, and `[FILE]` otherwise, including a broken symlink or a symlink that points outside the roots. Listing does not open the target. A later read or listing of that entry still goes through `resolve`.

A path that resolves to a file is a tool error.

### `read_text_file`

Argument: `path: str`. Read-only. Reads the whole file as strict UTF-8 and returns that text with no added header.

A file whose size is greater than 1 MiB (1,048,576 bytes) is a tool error, checked before the file body is read. A file of exactly 1 MiB is allowed. Bytes that are not valid UTF-8 are a tool error. A directory is a tool error.

### `write_file`

Arguments: `path: str`, `content: str`. Annotations: `read_only_hint=False`, `destructive_hint=True`, `idempotent_hint=True`. Writing the same content twice leaves the same bytes.

The content is encoded as strict UTF-8 and written in one replacement of the file. An existing file is overwritten. The parent directory must already exist. This tool does not create directories. Content larger than 1 MiB after encoding is a tool error, and the file is left unchanged.

The success text is one line: `Wrote N bytes to <canonical path>`, where N is the number of bytes written.

## Errors

A tool failure stays inside the session. The process keeps running.

Predicted failures raise `ToolError` from `mcp.server.mcpserver.exceptions`. The SDK returns a result with `is_error` set and the message in the text content, prefixed with the tool name. The server logs that message at info level without a traceback. The model can read it and retry.

These cases raise `ToolError`:

- The path is outside the allowed directories.
- The path does not exist, for a read or a listing.
- A listing was given a file, or a read or write was given a directory.
- `write_file` was given a path whose parent directory does not exist.
- The file, or the write content, is not valid UTF-8.
- The file or the encoded write content is larger than 1 MiB.
- The operating system denies permission.

Argument schema mismatches are already `ToolError` from the SDK, before the tool function runs.

Any other exception is left for the SDK crash path. The model sees only `Error executing tool <name>`, and the traceback goes to stderr.

The server does not raise `MCPError` for filesystem failures. That type fails the JSON-RPC request, which is for a broken session.

Startup failures are outside the session: missing arguments or a missing allowed directory print the reason to stderr and exit non-zero before `run()`.

## Tests

pytest. Each test uses a temporary directory as the allowed root. Tests do not touch the developer's real files.

### Path checker (`tests/test_paths.py`)

Call `resolve` directly. No server.

- A file inside the root resolves to its canonical path.
- A `..` path that climbs out of the root is refused.
- A sibling whose name only starts with the root name is refused.
- A relative path resolves against the allowed root, not the process working directory.
- With two roots, a relative path uses the first root in command-line order when both could contain it.
- A symlink inside the root that points outside is refused.
- A symlink inside the root that points at another file inside the root is allowed.
- A missing intermediate directory is refused.
- When a root path and its realpath differ, both spellings resolve.

### Tools (`tests/test_tools.py`)

Use the SDK in-memory client pointed at the server object. No subprocess.

- `list_allowed_directories` returns the temp root.
- `list_directory` returns `[DIR]` and `[FILE]` lines for immediate children, sorted, including a hidden name.
- `read_text_file` returns the file text.
- `write_file` creates a file, and a second call with different content overwrites it. The confirmation line reports the byte count and the canonical path.
- Each of these comes back with `is_error` set and the reason in the text: a path outside the root, a missing file, a directory passed to read, a file passed to list, a missing parent on write, a non-UTF-8 file, a file over 1 MiB, and write content over 1 MiB. The oversized write leaves any existing file unchanged.

### Startup and stdio (`tests/test_stdio.py`)

- Launching with no directory exits non-zero, writes the reason to stderr, and writes nothing to stdout.
- Launching with a directory that does not exist does the same.
- Launching with a real temp directory, sending one `initialize` request on stdin, and reading stdout yields one JSON-RPC response for that request and no other stdout bytes. The request includes a protocol version the SDK accepts, client capabilities, and client info. The response matches that request id, names the server `filesystem`, and advertises the tools capability.

## Host check

After the tests pass, a host config points `command` at `uv` and `args` at `run`, the project directory, the `filesystem-mcp` script, and one allowed directory. A successful host session lists that directory and reads a file inside it. That check is manual and is not a pytest test.
