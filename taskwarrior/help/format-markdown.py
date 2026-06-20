#!/usr/bin/env python3
"""
Markdown formatter with ANSI colors for terminal display
Formats markdown files with colors for better readability
Enhanced with better markdown rendering and vibrant colors
"""
import re
import sys

# ANSI color codes - Enhanced vibrant palette
RESET = '\033[0m'
BOLD = '\033[1m'
DIM = '\033[2m'
UNDERLINE = '\033[4m'

# Header colors - More vibrant
H1 = '\033[1;96m'      # Bright Cyan
H2 = '\033[1;93m'      # Bright Yellow
H3 = '\033[1;92m'      # Bright Green
H4 = '\033[1;95m'      # Bright Magenta

# Content colors - More vibrant
CODE = '\033[0;96m'    # Bright Cyan
CODE_BG = '\033[46m'   # Cyan background
CODE_BLOCK = '\033[0;90m\033[47m'  # Dark gray on white background
ALIAS = '\033[1;93m'   # Bright Yellow
ALIAS_BG = '\033[43m'  # Yellow background
COMMAND = '\033[0;96m' # Bright Cyan
EMPHASIS = '\033[1;97m' # Bright White
EMPHASIS_BG = '\033[107m' # White background
SEPARATOR = '\033[0;36m' # Cyan
BULLET = '\033[1;33m'  # Yellow
LINK = '\033[0;94m'    # Blue
QUOTE = '\033[0;90m'   # Dark Gray
VALUE = '\033[0;92m'   # Green (for values in key-value pairs)

def format_line(line, in_code_block):
    """Format a single line of markdown with enhanced rendering"""
    
    # Code blocks - Clean tabular style, no borders
    if line.startswith('```'):
        lang = line[3:].strip()
        if in_code_block:
            # End of code block - no extra spacing
            return (False, "")
        else:
            # Start of code block - no borders, clean tabular style
            return (True, "")
    
    if in_code_block:
        # Inside code block - plain tabular style, no highlights
        return (True, f"{CODE}{line}{RESET}")
    
    # Headers - Subtle styling, no double lines, no uppercase
    if re.match(r'^#+\s+', line):
        level = len(re.match(r'^(#+)', line).group(1))
        text = line[level:].strip()
        colors = {1: H1, 2: H2, 3: H3, 4: H4}
        color = colors.get(level, H3)
        
        # Simple single-line headers, no double lines, no uppercase
        if level == 1:
            return (False, f"{color}{BOLD}{text}{RESET}\n")
        elif level == 2:
            return (False, f"\n{color}{BOLD}{text}{RESET}\n")
        else:
            return (False, f"{color}{BOLD}{text}{RESET}\n")
    
    # Horizontal rules - remove entirely to reduce spacing
    if line.startswith('---'):
        return (False, "")
    
    # Process formatting
    formatted = line
    
    # Protect inline code from other replacements
    code_placeholders = {}
    code_idx = 0
    
    def protect_code(match):
        nonlocal code_idx
        placeholder = f"__CODE_{code_idx}__"
        code_placeholders[placeholder] = match.group(0)
        code_idx += 1
        return placeholder
    
    # 1. Protect inline code first
    formatted = re.sub(r'`([^`]+)`', protect_code, formatted)
    
    # 2. Bold text (**text**) - Enhanced
    formatted = re.sub(r'\*\*([^*]+)\*\*', lambda m: f"{EMPHASIS}{BOLD}{m.group(1)}{RESET}", formatted)
    
    # 3. Italic text (*text*)
    formatted = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', lambda m: f"{DIM}{m.group(1)}{RESET}", formatted)
    
    # 4. Links [text](url)
    formatted = re.sub(r'\[([^\]]+)\]\([^\)]+\)', lambda m: f"{LINK}{UNDERLINE}{m.group(1)}{RESET}", formatted)
    
    # 5. Aliases/Commands (word boundaries) - Enhanced highlighting
    aliases = ['thelp', 'th', 'thq', 'ta', 'tl', 'tn', 'td', 'tc', 'tm', 'te', 'twk', 
               'tsonho', 'tobj', 'tmeta', 'tmicro', 'tbloco',
               'tctxw', 'tctxft', 'tctxwk', 'tctxrev', 'tctxciclo', 'tctxonda', 'tctxtf', 'tctx0',
               'trecurd', 'trecurw', 'trecur15', 'trecurm', 'twd', 'task', 'wt']
    
    for alias in aliases:
        pattern = r'\b(' + re.escape(alias) + r')\b'
        formatted = re.sub(pattern, lambda m: f"{ALIAS}{BOLD}{m.group(1)}{RESET}", formatted)
    
    # 6. Restore inline code with enhanced styling
    for placeholder, code_text in code_placeholders.items():
        code_content = code_text[1:-1]  # Remove backticks
        formatted = formatted.replace(placeholder, f"{CODE_BG}{CODE}{BOLD} {code_content} {RESET}")
    
    # 7. Bullet points - Enhanced
    if formatted.startswith('-') and (len(formatted) == 1 or formatted[1] == ' '):
        formatted = f"{BULLET}▶{RESET} " + formatted[1:].lstrip()
    
    # 8. Numbered lists
    if re.match(r'^\d+\.\s+', formatted):
        formatted = re.sub(r'^(\d+)\.\s+', lambda m: f"{BULLET}{m.group(1)}.{RESET} ", formatted)
    
    # 9. Commands starting with task or #
    if re.match(r'^\s*(task|#)\s', formatted) and ALIAS not in formatted:
        formatted = re.sub(r'^(\s*)(task|#)(.*)', 
                          lambda m: f"{m.group(1)}{COMMAND}{BOLD}{m.group(2)}{m.group(3)}{RESET}", 
                          formatted)
    
    # 10. Key-value pairs (Key: Value) - Only if not already formatted
    if ':' in formatted and not formatted.startswith(' ') and not formatted.startswith('\033') and EMPHASIS not in formatted:
        parts = formatted.split(':', 1)
        if len(parts) == 2 and not any(c in parts[0] for c in ['http', 'www', '@', '//']):
            key = parts[0].strip()
            value = parts[1].strip()
            # Only format if it looks like a key-value pair (key is short, no special chars)
            if len(key) < 30 and not re.search(r'[<>(){}[\]]', key):
                formatted = f"{EMPHASIS}{BOLD}{key}:{RESET} {VALUE}{value}{RESET}"
    
    return (False, formatted)

def format_file(filepath):
    """Format entire markdown file with H2 section splitting"""
    try:
        import sys
        import os
        
        # Detect if output is TTY (terminal) or piped/redirected
        is_tty = sys.stdout.isatty()
        
        # Force colors if environment variable is set (for WSL->PowerShell interop)
        force_colors = os.environ.get('TASK_HELP_FORCE_COLORS', '').lower() in ('1', 'true', 'yes')
        
        # Enable ANSI colors on Windows if TTY
        if sys.platform == 'win32' and is_tty:
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)  # Enable ANSI
            except:
                pass  # Fallback if ctypes fails
        
        # Disable colors if output is piped/redirected (unless forced)
        if not is_tty and not force_colors:
            # Override color codes with empty strings
            global RESET, BOLD, H1, H2, H3, H4, CODE, CODE_BLOCK, ALIAS, COMMAND, EMPHASIS, SEPARATOR, BULLET, CODE_BG, ALIAS_BG, EMPHASIS_BG, LINK, QUOTE, DIM, UNDERLINE, VALUE
            RESET = BOLD = H1 = H2 = H3 = H4 = CODE = CODE_BLOCK = ALIAS = COMMAND = EMPHASIS = SEPARATOR = BULLET = CODE_BG = ALIAS_BG = EMPHASIS_BG = LINK = QUOTE = DIM = UNDERLINE = VALUE = ''
        
        # Width limit for cross-platform compatibility (80-100 chars)
        MAX_WIDTH = 100
        
        # Section separator marker for H2 splitting (PowerShell will split on this)
        SECTION_BREAK = '\n__H2_SECTION_BREAK__\n'
        
        # Track if we've seen the first H2 (don't break before first section)
        first_h2_seen = False
        h2_count = 0
        
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # First pass: identify H2 sections
        h2_positions = []
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('## ') and not stripped.startswith('###'):
                h2_positions.append(i)
        
        # Second pass: format and output with section breaks
        in_code_block = False
        last_was_empty = False
        last_was_header = False
        for i, line in enumerate(lines):
            original_line = line.rstrip('\n\r')
            
            # Check if this is an H2 header (before formatting) - must be exactly ## (not ###)
            stripped = original_line.strip()
            is_h2 = stripped.startswith('## ') and not stripped.startswith('###')
            is_h3 = stripped.startswith('### ') and not stripped.startswith('####')
            is_header = is_h2 or is_h3 or stripped.startswith('# ')
            
            # Skip multiple consecutive empty lines to reduce spacing
            is_empty = not original_line.strip()
            if is_empty:
                # Only allow one empty line max, and skip if last was also empty or was a header
                if last_was_empty or last_was_header:
                    last_was_empty = True
                    continue
                last_was_empty = True
                last_was_header = False
            else:
                last_was_empty = False
                last_was_header = is_header
            
            # Insert section break before H2 (except the first one)
            if is_h2:
                h2_count += 1
                if h2_count > 1:  # Not the first H2
                    print(SECTION_BREAK, end='', flush=True)
            
            in_code_block, formatted = format_line(original_line, in_code_block)
            
            # Skip empty formatted lines (except in code blocks and headers)
            if not in_code_block and not formatted.strip() and not is_header:
                continue
            
            # Wrap long lines if not in code block and not a header/separator
            if not in_code_block and len(formatted) > MAX_WIDTH and not formatted.startswith('\033[1;') and not formatted.startswith('\033[0;36m─'):
                # Simple word wrap (preserve ANSI codes)
                # Extract ANSI codes and text
                ansi_pattern = r'\033\[[0-9;]+m'
                words = re.split(r'(\s+)', formatted)
                current_line = ''
                current_ansi = ''
                
                for word in words:
                    # Check if word contains ANSI codes
                    ansi_matches = re.findall(ansi_pattern, word)
                    if ansi_matches:
                        current_ansi = ''.join(ansi_matches)
                    
                    # Calculate length without ANSI codes
                    clean_word = re.sub(ansi_pattern, '', word)
                    clean_current = re.sub(ansi_pattern, '', current_line)
                    
                    if len(clean_current + clean_word) > MAX_WIDTH and clean_current.strip():
                        print(current_line.rstrip(), flush=True)
                        current_line = current_ansi + clean_word
                    else:
                        current_line += word
                
                if current_line.strip():
                    print(current_line.rstrip(), flush=True)
            else:
                # Print formatted line, handling newlines properly
                if formatted:
                    print(formatted, end='', flush=True)
                    if not formatted.endswith('\n'):
                        print(flush=True)
    except FileNotFoundError:
        print(f"Error: File not found: {filepath}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: format-markdown.py <file.md>", file=sys.stderr)
        sys.exit(1)
    
    format_file(sys.argv[1])
