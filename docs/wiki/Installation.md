# Installation

## System requirements

- Python 3.10 or higher
- pip and venv
- Linux, macOS, or Windows (CPU-only build)

## From source

1. Clone the repository:
   ```bash
   git clone https://github.com/kiprutobeauttah/mulch.git
   cd mulch
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   python3 -m venv .venv
   .venv/bin/python -m pip install --index-url https://download.pytorch.org/whl/cpu torch torchvision
   .venv/bin/python -m pip install -r requirements.txt
   ```

3. Launch:
   ```bash
   ./run.sh
   ```

## Bundled release

Prebuilt packages are stored in the `packages/` directory of the repository (tracked with Git LFS) and attached to the GitHub Release page.

On Linux:

```bash
unzip packages/Mulch-linux-x64-v1.0.0.zip
./Mulch/Mulch
```

The server starts at `http://127.0.0.1:5005` and opens your browser automatically.

To install a desktop shortcut on Linux, copy the `Mulch` folder to `~/.local/share/mulch`, add a `mulch.desktop` entry in `~/.local/share/applications`, and place `favicon.svg` at `~/.local/share/icons/mulch.svg`.

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `MULCH_PORT` | `5005` | HTTP port the server listens on |
| `MULCH_DATA_DIR` | `~/.mulch` (bundled) / `mulch/records` (from source) | Directory for saved records and images |