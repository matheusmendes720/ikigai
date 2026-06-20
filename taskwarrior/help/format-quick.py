#!/usr/bin/env python3
"""
Quick reference formatter - Tabular compact format for CLI help
Extracts and formats tables from markdown into compact CLI-style output
Enhanced with vibrant colors and better visual design
"""
import re
import sys
import os

# ANSI color codes - Enhanced color palette
RESET = '\033[0m'
BOLD = '\033[1m'
DIM = '\033[2m'

# Header colors - Subtle and professional
HEADER = '\033[0;96m'      # Cyan (less bold)
SECTION = '\033[0;93m'     # Yellow (less bold)
SUBSECTION = '\033[0;92m'  # Green (less bold)

# Table colors - Colorful and distinct
TABLE_HEADER = '\033[1;95m'     # Bright Magenta (for table headers)
TABLE_ROW_EVEN = '\033[0;37m'   # White (for even rows)
TABLE_ROW_ODD = '\033[0;90m'    # Dark Gray (for odd rows)
TABLE_BORDER = '\033[0;36m'     # Cyan (for table borders)

# Content colors - More vibrant
ALIAS = '\033[1;93m'       # Bright Yellow
ALIAS_BG = '\033[43m'      # Yellow background
CODE = '\033[0;96m'        # Bright Cyan
CODE_BG = '\033[46m'       # Cyan background
CODE_BLOCK = '\033[0;90m\033[47m'  # Dark gray on white background
EMPHASIS = '\033[1;97m'    # Bright White
VALUE = '\033[0;92m'       # Green (for values)
FILTER = '\033[0;94m'      # Blue (for filters)
DESC = '\033[0;37m'        # White (for descriptions)

SEPARATOR = '\033[0;36m'   # Cyan
BULLET = '\033[1;33m'      # Yellow

def visual_length(text):
    """Calculate visual length ignoring ANSI codes and markdown"""
    # Remove ANSI escape sequences
    ansi_pattern = re.compile(r'\033\[[0-9;]+m')
    # Remove markdown formatting
    clean = re.sub(r'[`*]', '', text)
    # Remove ANSI codes
    clean = ansi_pattern.sub('', clean)
    return len(clean)

def apply_colors_to_cell(cell, col_idx, header_row):
    """Apply colors to a cell and return colored version"""
    header_lower = str(header_row[col_idx]).lower() if col_idx < len(header_row) else ""
    
    if col_idx == 0:  # First column
        cell = re.sub(r'`([^`]+)`', lambda m: f"{CODE}{BOLD}{m.group(1)}{RESET}", cell)
        cell = re.sub(r'\b(ta|tl|tn|td|tc|tm|te|twk|tsonho|tobj|tmeta|tmicro|tbloco|tctxw|tctxft|tctxwk|tctxrev|tctxciclo|tctxonda|tctxtf|tctx0|trecurd|trecurw|trecur15|trecurm|twd|task|wt|th|thelp|thq|narrativa|relatorios|revisao|supervisao|sonho|objetivo|meta|tarefa|blocos)\b', 
                     lambda m: f"{ALIAS}{BOLD}{m.group(1)}{RESET}", cell)
    elif 'filter' in header_lower or 'columns' in header_lower:
        cell = re.sub(r'`([^`]+)`', lambda m: f"{CODE}{m.group(1)}{RESET}", cell)
        cell = f"{FILTER}{cell}{RESET}"
    elif 'description' in header_lower or 'desc' in header_lower:
        cell = f"{DESC}{cell}{RESET}"
    elif 'alias' in header_lower:
        cell = re.sub(r'`([^`]+)`', lambda m: f"{ALIAS}{m.group(1)}{RESET}", cell)
        cell = f"{ALIAS}{BOLD}{cell}{RESET}"
    elif 'type' in header_lower or 'level' in header_lower:
        cell = f"{VALUE}{BOLD}{cell}{RESET}"
    elif 'values' in header_lower or 'purpose' in header_lower:
        cell = f"{DESC}{DIM}{cell}{RESET}"
    else:
        cell = re.sub(r'`([^`]+)`', lambda m: f"{CODE}{m.group(1)}{RESET}", cell)
        cell = f"{VALUE}{cell}{RESET}"
    return cell

def format_table(table_lines):
    """Format markdown table into aligned columns with vibrant colors"""
    if not table_lines:
        return []
    
    # Parse table
    rows = []
    for line in table_lines:
        if '|' in line:
            # Split and clean cells
            cells = [cell.strip() for cell in line.split('|')[1:-1]]
            if cells and not all(c.startswith('-') for c in cells):  # Skip separator row
                rows.append(cells)
    
    if not rows:
        return []
    
    # Calculate column widths
    num_cols = max(len(row) for row in rows) if rows else 0
    
    # Step 1: Calculate base widths from raw content (no colors)
    base_widths = [0] * num_cols
    for row in rows:
        for i, cell in enumerate(row):
            if i < num_cols:
                # Remove markdown formatting for base width calculation
                clean_cell = re.sub(r'[`*]', '', cell)
                base_widths[i] = max(base_widths[i], len(clean_cell))
    
    # Step 2: Apply colors to all cells and recalculate widths
    header_row = rows[0]
    colored_header_cells = []
    for j in range(num_cols):
        if j < len(header_row):
            cell = header_row[j]
            # Highlight header cells
            cell = re.sub(r'`([^`]+)`', lambda m: f"{CODE}{m.group(1)}{RESET}", cell)
            # Make header bold and colored
            cell = f"{TABLE_HEADER}{BOLD}{cell.upper()}{RESET}"
            colored_header_cells.append(cell)
        else:
            colored_header_cells.append('')
    
    # Recalculate widths including colored header
    widths = [0] * num_cols
    for j in range(num_cols):
        widths[j] = max(base_widths[j], visual_length(colored_header_cells[j]))
    
    # Step 3: Color and measure data rows, update widths
    colored_data_rows = []
    for i, row in enumerate(rows[1:], 1):
        colored_row = []
        for j in range(num_cols):
            if j < len(row):
                cell = row[j]
                # Apply colors
                cell = apply_colors_to_cell(cell, j, header_row)
                colored_row.append(cell)
                # Update width if this cell is wider
                visual_len = visual_length(cell)
                if visual_len > widths[j]:
                    widths[j] = visual_len
            else:
                colored_row.append('')
        colored_data_rows.append(colored_row)
    
    # Step 4: Format output with proper padding
    formatted = []
    
    # Header row with proper padding
    padded_header = []
    for j in range(num_cols):
        cell = colored_header_cells[j]
        visual_len = visual_length(cell)
        padding_needed = max(0, widths[j] - visual_len)
        padded_header.append(cell + (' ' * padding_needed))
    
    # Add border above header
    total_width = sum(widths) + (num_cols - 1) * 2
    border = f"{TABLE_BORDER}{'─' * total_width}{RESET}"
    formatted.append(border)
    formatted.append('  '.join(padded_header))
    formatted.append(f"{TABLE_BORDER}{'─' * total_width}{RESET}")
    
    # Data rows with proper padding
    for i, colored_row in enumerate(colored_data_rows):
        row_color = TABLE_ROW_EVEN if (i + 1) % 2 == 0 else TABLE_ROW_ODD
        padded_row = []
        for j in range(num_cols):
            cell = colored_row[j] if j < len(colored_row) else ''
            visual_len = visual_length(cell)
            padding_needed = max(0, widths[j] - visual_len)
            padded_row.append(cell + (' ' * padding_needed))
        
        formatted.append(f"{row_color}{'  '.join(padded_row)}{RESET}")
    
    return formatted

def format_quick_reference(filepath):
    """Format quick reference from markdown file"""
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
                pass
        
        # Disable colors if output is piped/redirected (unless forced)
        colors_disabled = False
        if not is_tty and not force_colors:
            # Override color codes with empty strings
            global RESET, BOLD, HEADER, SECTION, SUBSECTION, TABLE_HEADER, TABLE_ROW_EVEN, TABLE_ROW_ODD, TABLE_BORDER, ALIAS, CODE, EMPHASIS, SEPARATOR, BULLET, VALUE, FILTER, DESC, DIM, CODE_BLOCK
            RESET = BOLD = HEADER = SECTION = SUBSECTION = TABLE_HEADER = TABLE_ROW_EVEN = TABLE_ROW_ODD = TABLE_BORDER = ALIAS = CODE = EMPHASIS = SEPARATOR = BULLET = VALUE = FILTER = DESC = DIM = CODE_BLOCK = ''
            colors_disabled = True
        
        # Width limit for tables (100 chars max)
        MAX_WIDTH = 100
        
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        output = []
        in_table = False
        table_lines = []
        in_code_block = False
        last_was_code_block = False
        code_block_lines = []
        
        for i, line in enumerate(lines):
            line = line.rstrip('\n\r')
            next_line = lines[i + 1].rstrip('\n\r') if i + 1 < len(lines) else ''
            
            # Handle code blocks - render them with colors
            if line.startswith('```'):
                lang = line[3:].strip()
                if in_code_block:
                    # End of code block - render accumulated lines
                    if code_block_lines:
                        # Remove leading and trailing empty lines from code block
                        while code_block_lines and not code_block_lines[0].strip():
                            code_block_lines.pop(0)
                        while code_block_lines and not code_block_lines[-1].strip():
                            code_block_lines.pop()
                        
                        # Compact header - single line (only if we have content)
                        if code_block_lines:
                            # Only add newline before if previous line wasn't empty and wasn't a code block
                            if output and output[-1].strip() and not last_was_code_block:
                                output.append('')
                            # Render code lines - clean, no highlights, no borders (tabular style)
                            for code_line in code_block_lines:
                                # Just render as plain code, no alias highlighting, no borders
                                output.append(f"{CODE}{code_line}{RESET}")
                            # Don't add extra newline after code block
                    in_code_block = False
                    code_block_lines = []
                    last_was_code_block = True
                else:
                    # Start of code block
                    in_code_block = True
                    code_block_lines = []
                    last_was_code_block = False
                continue
            if in_code_block:
                # Accumulate code lines (always add, we'll trim later)
                code_block_lines.append(line)
                continue
            
            # Headers - Subtle and clean
            if line.startswith('# '):
                title = line[2:]
                # Only add newline if previous content exists
                if output and output[-1].strip():
                    output.append('')
                output.append(f"{HEADER}{BOLD}{title}{RESET}")
                output.append(f"{HEADER}{'─' * min(70, len(title) + 2)}{RESET}")
                continue
            elif line.startswith('## '):
                # Only add newline if previous content exists and wasn't a header
                if output and output[-1].strip() and not output[-1].startswith('\033[0;96m'):
                    output.append('')
                output.append(f"{SECTION}{line[3:]}{RESET}")
                continue
            elif line.startswith('### '):
                # Subsection - minimal styling
                if output and output[-1].strip():
                    output.append('')
                output.append(f"{SUBSECTION}{BOLD}{line[4:]}{RESET}")
                continue
            
            # Horizontal rules
            if line.startswith('---'):
                output.append(f"{SEPARATOR}{'─' * 70}{RESET}\n")
                continue
            
            # Tables
            if '|' in line:
                # Start or continue table
                if not in_table:
                    in_table = True
                    table_lines = []
                table_lines.append(line)
                continue
            elif in_table:
                # End of table
                formatted_table = format_table(table_lines)
                if formatted_table:
                    output.extend(formatted_table)
                    output.append('')  # Empty line after table
                in_table = False
                table_lines = []
                # Continue processing the current line
                if line.strip() == '':
                    continue
            
            # Skip empty lines in quick mode (unless after table)
            if not in_table and line.strip() == '':
                # Skip empty lines, especially after code blocks
                if last_was_code_block:
                    continue  # Skip empty line right after code block
                if output and not output[-1].strip():
                    continue  # Skip consecutive empty lines
                # Skip single empty lines in quick mode
                continue
            
            # Reset code block flag after processing one non-empty line
            if last_was_code_block and line.strip():
                last_was_code_block = False
            
            # Keep key-value pairs with colors
            if line.startswith('**') and ':' in line:
                # Key-value pairs - subtle styling
                parts = line.split(':', 1)
                if len(parts) == 2:
                    key = parts[0].replace('**', '').strip()
                    value = parts[1].replace('**', '').strip()
                    output.append(f"{EMPHASIS}{key}:{RESET} {value}")
            elif line.startswith('- ') and len(line) < 80:
                # Short bullet points - minimal
                output.append(f"{BULLET}•{RESET} {line[2:]}")
            elif line.strip() and not line.startswith('|'):
                # Regular text lines - preserve but don't over-style
                output.append(line)
        
        # Handle last table if file ends with table
        if in_table and table_lines:
            formatted_table = format_table(table_lines)
            if formatted_table:
                output.extend(formatted_table)
        
        # Join output
        result = '\n'.join(output)
        
        # Wrap very long lines (but preserve table formatting)
        wrapped_lines = []
        for line in result.split('\n'):
            if '|' not in line and len(line) > MAX_WIDTH and not line.startswith('\033'):
                # Word wrap for non-table, non-ANSI lines
                words = line.split(' ')
                current = ''
                for word in words:
                    if len(current + word) > MAX_WIDTH:
                        wrapped_lines.append(current.rstrip())
                        current = word + ' '
                    else:
                        current += word + ' '
                if current.strip():
                    wrapped_lines.append(current.rstrip())
            else:
                wrapped_lines.append(line)
        
        return '\n'.join(wrapped_lines)
    
    except FileNotFoundError:
        return f"Error: File not found: {filepath}"
    except Exception as e:
        return f"Error: {e}"

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: format-quick.py <file.md>", file=sys.stderr)
        sys.exit(1)
    
    result = format_quick_reference(sys.argv[1])
    print(result)
