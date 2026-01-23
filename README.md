# dtachwrap

Python wrapper for **dtach** with built-in binary management and multi-task CLI.
It packages the `dtach` binary in the wheel (Linux x86_64 / aarch64), so it works out of the box without compilation during installation.

## Features

- **Portable**: Includes pre-compiled `dtach` binaries (GPL compliant).
- **Easy Management**: `start`, `attach`, `ls`, `logs`, `stop` commands.
- **Logging**: Automatically captures stdout/stderr to files.
- **Recovery**: Keeps tasks running even if you disconnect.

## Installation

```bash
pip install dtachwrap
```

Or run directly with `uvx`:

```bash
uvx dtachwrap start my-task -- python script.py
```

## Usage

### Start a task

```bash
dtachwrap start train-exp1 -- python train.py --cfg exp1.yaml
```

The task runs in the background.

- Socket: `~/.dtachwrap/sockets/train-exp1`
- Logs: `~/.dtachwrap/logs/train-exp1.out`

### List tasks

```bash
dtachwrap ls
```

Shows running tasks. Use `dtachwrap ls --all` to see stopped tasks.

### View logs

```bash
dtachwrap logs train-exp1 -f
```

### Attach to a task

```bash
dtachwrap attach train-exp1
```

- Detach key: `^\` (Ctrl+\)
- Redraw: `Ctrl+l`

### Stop a task

```bash
dtachwrap stop train-exp1
```

## License

This project is licensed under MIT.
The bundled `dtach` binary is GPL-2.0. See `src/dtachwrap/_vendor/licenses/DTACH_COPYING`.

## Development

This project uses `uv` for dependency management.

1. **Setup**:
   ```bash
   uv sync
   ```

2. **Run locally**:
   ```bash
   uv run dtachwrap --help
   ```

3. **Build**:
   ```bash
   uv build
   ```

