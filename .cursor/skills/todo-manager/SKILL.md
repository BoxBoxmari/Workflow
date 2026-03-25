---
name: todo-manager
description: Manage project todos in todos.md file. Use when the user wants to add, complete, remove, list, or manage todos, or when they mention todos, tasks, or todo management.
---

# Project Todo Manager

Manage todos in a `todos.md` file at the project root.

## When to Use

- User requests to add, complete, remove, or list todos
- User mentions managing tasks or todos
- User wants to track project tasks

## Usage

```
todo add "task description"
todo add "task description" [due date]
todo complete N
todo remove N
todo undo N
todo list [N]
todo due N [date]
todo past due
todo next
```

## Project Root Detection

Find project root by checking for:
- `.git` directory
- `package.json`, `requirements.txt`, `go.mod`, `Cargo.toml`
- `README.md` or `README`
- `pyproject.toml`, `setup.py`

Use the first directory containing any of these as project root.

## Todo File Location

- **File**: `todos.md` in project root
- **Create if missing**: Initialize with basic structure

## File Format

```markdown
# Project Todos

## Active
- [ ] Task description | Due: MM/DD/YYYY
- [ ] Another task | Due: MM/DD/YYYY @ HH:MM AM/PM
- [ ] Task without due date

## Completed
- [x] Finished task | Done: MM/DD/YYYY
- [x] Another completed task | Due: MM/DD/YYYY | Done: MM/DD/YYYY @ HH:MM AM/PM
```

## Commands

### Add Todo

**Syntax**: `add "task description" [due date]`

- Add new todo to Active section
- Parse due date from various formats:
  - Relative: "tomorrow", "next week", "in 3 days", "in 2 hours"
  - Absolute: "June 9", "12-24-2025", "MM/DD/YYYY"
  - Time: "tomorrow at 3pm", "June 9 at 2:30 PM"
- Format dates as MM/DD/YYYY (or DD/MM/YYYY based on locale)
- Include time only if specified: `MM/DD/YYYY @ HH:MM AM/PM`
- Insert in correct position (sorted by due date)

**Examples**:
```
todo add "Fix navigation bug"
todo add "Review PR" tomorrow
todo add "Deploy to staging" next week
todo add "Meeting" June 9 at 2pm
todo add "Task" in 3 days
```

### Complete Todo

**Syntax**: `complete N`

- Find todo #N in Active section
- Move to Completed section
- Add completion timestamp: `Done: MM/DD/YYYY` (or with time if due date had time)
- Preserve original due date if present
- Renumber remaining todos

### Remove Todo

**Syntax**: `remove N`

- Find todo #N (check both Active and Completed)
- Remove entirely from file
- Renumber remaining todos

### Undo Todo

**Syntax**: `undo N`

- Find todo #N in Completed section
- Move back to Active section
- Remove completion timestamp
- Preserve due date if present
- Insert in correct sorted position

### List Todos

**Syntax**: `list [N]`

- Display all todos numbered (1, 2, 3...)
- If N provided, show only first N active todos
- Show Active section first, then Completed
- Format: `N. [ ] Task description | Due: MM/DD/YYYY`
- Highlight past due items

### Set Due Date

**Syntax**: `due N [date]`

- Find todo #N in Active section
- Update or add due date
- Re-sort Active section
- Parse date same as `add` command

### Past Due

**Syntax**: `past due`

- List all active todos with due dates in the past
- Show days overdue
- Format: `N. [ ] Task | Due: MM/DD/YYYY (X days overdue)`

### Next Todo

**Syntax**: `next`

- Find next active todo to work on
- Prioritize by due date (earliest first)
- If no due dates, show first in Active list
- Display: `Next: N. [ ] Task description | Due: MM/DD/YYYY`

## Date Parsing

Support these formats:

**Relative**:
- "tomorrow", "today", "yesterday"
- "next week", "next month", "next year"
- "in N days", "in N hours", "in N weeks"
- "Monday", "next Monday" (next occurrence)

**Absolute**:
- "MM/DD/YYYY", "DD/MM/YYYY"
- "MM-DD-YYYY", "YYYY-MM-DD"
- "Month DD, YYYY" (e.g., "June 9, 2025")
- "DD Month YYYY" (e.g., "9 June 2025")

**With Time**:
- "at HH:MM AM/PM" (e.g., "at 3pm", "at 2:30 PM")
- "HH:MM" (24-hour format)

**Default**: Use MM/DD/YYYY format unless locale suggests DD/MM/YYYY.

## Sorting Rules

**Active Section**:
1. Todos with due dates (sorted ascending by date)
2. Todos without due dates (in order added)

**Completed Section**:
- Keep in reverse chronological order (most recent first)

## Implementation Steps

### 1. Find Project Root

```bash
# Check for project indicators
[ -d .git ] && echo "Found .git"
[ -f package.json ] && echo "Found package.json"
[ -f requirements.txt ] && echo "Found requirements.txt"
```

### 2. Read/Create todos.md

- Read file if exists
- If missing, create with:
```markdown
# Project Todos

## Active

## Completed
```

### 3. Parse Command

Extract action and arguments:
- Action: `add`, `complete`, `remove`, `undo`, `list`, `due`, `past due`, `next`
- Arguments: task description, number, date

### 4. Execute Action

**Add**:
- Parse date if provided
- Format date consistently
- Insert in sorted position
- Number: highest existing + 1

**Complete/Remove/Undo**:
- Find todo by number
- Validate number exists
- Update file accordingly
- Renumber if needed

**List**:
- Parse todos from file
- Number sequentially
- Format for display
- Show count if N provided

### 5. Write File

- Preserve formatting
- Maintain section structure
- Update numbering
- Sort Active section

### 6. Provide Feedback

- Confirm action completed
- Show affected todo
- Display updated count
- Highlight any issues

## Error Handling

- **Invalid number**: "Todo #N not found"
- **Missing file**: Create todos.md automatically
- **Invalid date**: "Could not parse date. Use format: MM/DD/YYYY or 'tomorrow'"
- **Missing arguments**: Show usage help
- **File read error**: "Could not read todos.md"

## Examples

**Adding todos**:
```
> todo add "Fix bug in login"
✓ Added: 1. [ ] Fix bug in login

> todo add "Review code" tomorrow
✓ Added: 2. [ ] Review code | Due: 02/06/2025

> todo add "Meeting" June 9 at 2pm
✓ Added: 3. [ ] Meeting | Due: 06/09/2025 @ 2:00 PM
```

**Completing**:
```
> todo complete 1
✓ Completed: Fix bug in login | Done: 02/05/2025
```

**Listing**:
```
> todo list
Active:
1. [ ] Review code | Due: 02/06/2025
2. [ ] Meeting | Due: 06/09/2025 @ 2:00 PM
3. [ ] Another task

Completed:
1. [x] Fix bug in login | Done: 02/05/2025
```

**Past due**:
```
> todo past due
Past Due:
1. [ ] Overdue task | Due: 01/30/2025 (6 days overdue)
```

## Best Practices

- Always preserve file structure
- Number todos consistently
- Sort Active section after any date change
- Provide clear, concise feedback
- Handle edge cases gracefully
- Use consistent date formatting
