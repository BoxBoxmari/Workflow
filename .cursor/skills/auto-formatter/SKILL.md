---
name: auto-formatter
description: Automatically formats code after edits using language-specific formatters (Prettier, Black, gofmt, rustfmt, php-cs-fixer). Use when editing code files to ensure consistent formatting.
---

# Auto Formatter

Automatically formats code after edits using language-specific formatters.

## When to Use

This skill automatically activates when editing code files. It formats code after Edit or MultiEdit operations.

## Supported Languages

- **JavaScript/TypeScript**: Prettier (`.js`, `.ts`, `.jsx`, `.tsx`, `.json`, `.css`, `.html`)
- **Python**: Black (`.py`)
- **Go**: gofmt (`.go`)
- **Rust**: rustfmt (`.rs`)
- **PHP**: php-cs-fixer (`.php`)

## Setup

Add this hook configuration to your `.cursorrules` file:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|MultiEdit",
        "hooks": [
          {
            "type": "command",
            "command": "if [[ \"$CLAUDE_TOOL_FILE_PATH\" == *.js || \"$CLAUDE_TOOL_FILE_PATH\" == *.ts || \"$CLAUDE_TOOL_FILE_PATH\" == *.jsx || \"$CLAUDE_TOOL_FILE_PATH\" == *.tsx || \"$CLAUDE_TOOL_FILE_PATH\" == *.json || \"$CLAUDE_TOOL_FILE_PATH\" == *.css || \"$CLAUDE_TOOL_FILE_PATH\" == *.html ]]; then npx prettier --write \"$CLAUDE_TOOL_FILE_PATH\" 2>/dev/null || true; elif [[ \"$CLAUDE_TOOL_FILE_PATH\" == *.py ]]; then black \"$CLAUDE_TOOL_FILE_PATH\" 2>/dev/null || true; elif [[ \"$CLAUDE_TOOL_FILE_PATH\" == *.go ]]; then gofmt -w \"$CLAUDE_TOOL_FILE_PATH\" 2>/dev/null || true; elif [[ \"$CLAUDE_TOOL_FILE_PATH\" == *.rs ]]; then rustfmt \"$CLAUDE_TOOL_FILE_PATH\" 2>/dev/null || true; elif [[ \"$CLAUDE_TOOL_FILE_PATH\" == *.php ]]; then php-cs-fixer fix \"$CLAUDE_TOOL_FILE_PATH\" 2>/dev/null || true; fi"
          }
        ]
      }
    ]
  }
}
```

## How It Works

1. **Trigger**: After any Edit or MultiEdit operation
2. **Detection**: Checks file extension to determine formatter
3. **Formatting**: Runs appropriate formatter command
4. **Error Handling**: Silently fails if formatter not available (won't block edits)

## Formatter Commands

### JavaScript/TypeScript (Prettier)
```bash
npx prettier --write "$CLAUDE_TOOL_FILE_PATH"
```

### Python (Black)
```bash
black "$CLAUDE_TOOL_FILE_PATH"
```

### Go (gofmt)
```bash
gofmt -w "$CLAUDE_TOOL_FILE_PATH"
```

### Rust (rustfmt)
```bash
rustfmt "$CLAUDE_TOOL_FILE_PATH"
```

### PHP (php-cs-fixer)
```bash
php-cs-fixer fix "$CLAUDE_TOOL_FILE_PATH"
```

## Prerequisites

Ensure formatters are available:

**Prettier** (JavaScript/TypeScript):
```bash
npm install -g prettier
# or use npx (no install needed)
```

**Black** (Python):
```bash
pip install black
```

**gofmt** (Go):
- Included with Go installation

**rustfmt** (Rust):
```bash
rustup component add rustfmt
```

**php-cs-fixer** (PHP):
```bash
composer global require friendsofphp/php-cs-fixer
# or
wget https://cs.symfony.com/download/php-cs-fixer-v3.phar
```

## Behavior

- **Automatic**: Formats code immediately after edits
- **Non-blocking**: If formatter fails or isn't installed, edit still succeeds
- **Silent**: Errors are suppressed (redirected to `/dev/null`)
- **In-place**: Formatters modify files directly

## Customization

To add more languages or formatters, extend the command:

```bash
elif [[ "$CLAUDE_TOOL_FILE_PATH" == *.java ]]; then
  google-java-format -i "$CLAUDE_TOOL_FILE_PATH" 2>/dev/null || true
elif [[ "$CLAUDE_TOOL_FILE_PATH" == *.kt ]]; then
  ktlint -F "$CLAUDE_TOOL_FILE_PATH" 2>/dev/null || true
fi
```

## Notes

- Formatters use their default configuration
- Project-specific config files (`.prettierrc`, `pyproject.toml`, etc.) are respected
- Formatting happens after the edit, so you may see formatting changes in git diff
- Works on Windows, macOS, and Linux (uses bash-compatible syntax)
