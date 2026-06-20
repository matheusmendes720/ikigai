# Cross-Platform Help System - Best Practices Implementation

## Overview

This document describes the cross-platform (WSL + PowerShell) help system implementation following CLI best practices for cross-environment setups.

---

## Implemented Features

### 1. UTF-8 Encoding Enforcement ✅

**PowerShell:**
```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:LESSCHARSET = "utf-8"
```

**WSL/Bash:**
```bash
export LC_ALL=C.UTF-8
export LANG=C.UTF-8
```

**Why:** Ensures special characters, emojis, and box-drawing characters display correctly across both environments.

---

### 2. TTY Detection & ANSI Color Handling ✅

**Python Formatters:**
- Detect if output is TTY using `sys.stdout.isatty()`
- Disable ANSI colors when output is piped/redirected
- Enable colors only in interactive terminals

**Implementation:**
```python
is_tty = sys.stdout.isatty()
if not is_tty:
    # Strip all ANSI codes
    RESET = BOLD = H1 = H2 = ... = ''
```

**Why:** Prevents ANSI control characters from corrupting redirected output (e.g., `thelp > help.txt`).

---

### 3. Pagination for Long Help Text ✅

**PowerShell:**
```powershell
if (-not [Console]::IsOutputRedirected) {
    $output | Out-Host -Paging
} else {
    $output
}
```

**WSL/Bash:**
```bash
if [ -t 1 ]; then
    # TTY: use less with colors
    "$FORMATTER" "$HELP_FILE" | less -R
else
    # Piped: no pagination
    "$FORMATTER" "$HELP_FILE"
fi
```

**Why:** Long help text doesn't fly past the terminal buffer; users can scroll through it.

---

### 4. Exit Code 0 for Help Commands ✅

**PowerShell:**
```powershell
# Always return exit code 0 for help
$LASTEXITCODE = 0
```

**WSL/Bash:**
```bash
# Always return exit code 0 for help
exit 0
```

**Why:** Allows chaining commands: `thelp aliases && echo "Success"`

---

### 5. Width Limits (80-100 chars) ✅

**Python Formatters:**
- Maximum width: 100 characters
- Word wrapping for long lines (preserves ANSI codes)
- Table formatting respects width limits

**Why:** Fits standard PowerShell windows and prevents horizontal scrolling.

---

### 6. WSL/Windows Interop Documentation ✅

Added dedicated section in `00-overview.md`:

**Path Handling:**
- Documents Windows path vs WSL path differences
- Explains automatic conversion by wrapper functions
- Provides examples for both environments

**Encoding:**
- Documents automatic UTF-8 handling
- Troubleshooting for garbled characters

**Exit Codes:**
- Documents exit code 0 behavior
- Explains command chaining support

---

### 7. Debug Mode ✅

**PowerShell:**
```powershell
# Enable debug mode
$env:TASK_HELP_DEBUG = "1"
thelp aliases
```

**Output:**
```
=== Help System Debug Info ===
OS: Microsoft Windows 10.0.26200
Shell: PowerShell 7.x.x
Encoding: Unicode (UTF-8)
Is TTY: True
Topic: aliases
```

**Why:** Helps diagnose encoding, TTY detection, and environment issues when users report problems.

---

## Help System Architecture

### Two Formats

1. **`thelp <topic>`** - Detailed format
   - Full markdown with explanations
   - Examples and use cases
   - For learning and deep understanding

2. **`thq <topic>`** - Quick reference (tabular)
   - Compact tabular format
   - Essential information only
   - For fast lookup

### Formatters

- **`format-markdown.py`** - Detailed help formatter
  - Full markdown processing
  - Rich formatting with colors
  - Width wrapping

- **`format-quick.py`** - Quick reference formatter
  - Table extraction and alignment
  - Compact output
  - Minimal formatting

---

## Usage Examples

### Basic Usage

```powershell
# PowerShell
thelp              # Overview
thelp aliases      # Detailed aliases guide
thq aliases        # Quick aliases table
```

```bash
# WSL/Bash
thelp              # Overview
thelp aliases      # Detailed aliases guide
thq aliases        # Quick aliases table
```

### Debug Mode

```powershell
# PowerShell
$env:TASK_HELP_DEBUG = "1"
thelp aliases
```

### Redirecting Output

```powershell
# PowerShell - colors automatically disabled
thelp aliases > help.txt

# WSL/Bash - colors automatically disabled
thelp aliases > help.txt
```

---

## Best Practices Checklist

- ✅ **Encoding:** UTF-8 enforced in both environments
- ✅ **TTY Detection:** Colors disabled when piped/redirected
- ✅ **Pagination:** Long help text uses pagination
- ✅ **Exit Codes:** Help commands return 0
- ✅ **Width Limits:** 100 character max width
- ✅ **Path Documentation:** WSL/Windows interop documented
- ✅ **Debug Mode:** Environment diagnostics available
- ✅ **Two Formats:** Detailed (`thelp`) and Quick (`thq`)

---

## Troubleshooting

### Garbled Characters

**Solution:** Encoding is automatically set. If issues persist:
```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
```

### Colors in Redirected Output

**Solution:** Automatically disabled. If you see ANSI codes in files:
- The formatter should detect `isatty() == False`
- Check that `format-markdown.py` and `format-quick.py` have TTY detection

### Exit Code Issues

**Solution:** Help commands always return 0. If chaining fails:
- Check that `exit 0` is in `main-help.sh`
- Check that `$LASTEXITCODE = 0` is in PowerShell functions

---

## Related Files

- `taskwarrior/help/format-markdown.py` - Detailed formatter
- `taskwarrior/help/format-quick.py` - Quick formatter
- `taskwarrior/help/main-help.sh` - WSL router
- `taskwarrior/help/main-help.ps1` - PowerShell router
- `scripts/task-aliases.ps1` - PowerShell wrapper functions
- `~/.task_aliases.sh` - WSL aliases

---

*This implementation follows CLI best practices for cross-platform help systems as documented in the comprehensive guide provided.*
