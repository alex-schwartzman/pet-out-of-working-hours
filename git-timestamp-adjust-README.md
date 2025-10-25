# Git Timestamp Adjuster

A tool to rewrite git commit history timestamps to make all commits appear as if they were made during specified "hobby hours" (default: 20:00-04:00).

## Features

✅ **All Requirements Satisfied:**
- Adjusts timestamps to hobby hours (20:00-04:00 by default)
- Preserves temporal distance (≥50% of original)
- Maintains realistic coding rate (100 lines/hour default)
- Detects and rejects merge commits
- Creates backup branch automatically
- Dry-run mode for safety
- Comprehensive validation

## Installation

No installation needed! Just make sure you have Python 3.6+ installed.

```bash
chmod +x git-timestamp-adjust.py
```

## Usage

### Dry Run (Recommended First Step)

```bash
./git-timestamp-adjust.py --branch main --dry-run
```

This shows what would be changed without actually modifying anything.

### Apply Changes

```bash
./git-timestamp-adjust.py --branch main
```

### Custom Hobby Hours (9 PM to 2 AM)

```bash
./git-timestamp-adjust.py --branch main --start-hour 21 --end-hour 2
```

### Custom Coding Rate (50 lines per hour)

```bash
./git-timestamp-adjust.py --branch main --min-rate 50
```

### All Options

```bash
./git-timestamp-adjust.py \
  --branch feature-x \
  --start-hour 20 \
  --end-hour 4 \
  --min-rate 100 \
  --distance-factor 0.5 \
  --backup-branch my-backup \
  --dry-run
```

## Options

- `--branch` (required): Branch to process
- `--start-hour`: Start of hobby hours (0-23, default: 20)
- `--end-hour`: End of hobby hours (0-23, default: 4)
- `--min-rate`: Minimum coding rate in lines/hour (default: 100)
- `--distance-factor`: Temporal distance preservation factor 0-1 (default: 0.5)
- `--dry-run`: Show proposed changes without applying them
- `--backup-branch`: Name for backup branch (default: backup-TIMESTAMP)

## How It Works

1. **Validation**: Checks for uncommitted changes and merge commits
2. **Analysis**: Reads all commits with their timestamps and line changes
3. **Calculation**: Computes new timestamps satisfying all constraints:
   - Hobby hours window (20:00-04:00)
   - Minimum 50% temporal distance preservation
   - Realistic coding rate (100 lines/hour)
4. **Backup**: Creates a backup branch
5. **Rewrite**: Uses `git filter-branch` to rewrite history
6. **Validation**: Verifies all constraints are satisfied

## Constraints

The tool enforces three main constraints:

### 1. Hobby Hours Window
All commits must fall within the specified time window (default 20:00-04:00).
If commits don't fit in one night, they continue into subsequent nights.

### 2. Temporal Distance Preservation
The time between any two commits in the adjusted history must be at least
50% (configurable) of the original distance.

**Example:**
- Original: Commit A at 10:00, Commit B at 14:00 (4 hours apart)
- Adjusted: Must be at least 2 hours apart

### 3. Realistic Coding Rate
Minimum time between commits based on lines changed:
- Default: 100 lines per hour
- 50 lines changed = minimum 30 minutes
- 300 lines changed = minimum 3 hours

## Safety Features

- ✅ Detects and rejects branches with merge commits
- ✅ Creates automatic backup branch before any changes
- ✅ Dry-run mode to preview changes
- ✅ Warns about uncommitted changes
- ✅ Validates all constraints before and after rewriting
- ✅ Confirmation prompt before applying changes

## Example Output

```
Git History Timestamp Adjustment - Dry Run
============================================================

Configuration:
  Branch: main
  Hobby hours: 20:00 - 04:00
  Minimum rate: 100 lines/hour
  Distance factor: 0.5

Analysis:
  Total commits: 247
  Merge commits: 0 ✓
  Original span: 2024-01-15 09:30 to 2024-03-20 14:45 (65 days)
  Adjusted span: 2024-01-15 20:00 to 2024-02-18 03:30 (34 nights)

Sample changes:
  abc1234: 2024-01-15 09:30 -> 2024-01-15 20:15 (150 lines, +10h45m)
  def5678: 2024-01-15 14:22 -> 2024-01-15 22:47 (225 lines, +8h25m)
  ...

Constraints satisfied:
  ✓ All timestamps within hobby hours
  ✓ Chronological order preserved
  ✓ Minimum coding rate satisfied
  ✓ Temporal distance ≥50% preserved

Would rewrite 247 commits across 34 nights.
Run without --dry-run to apply changes.
```

## After Running

If you have already pushed the branch to a remote repository, you'll need to force push:

```bash
git push --force origin <branch-name>
```

⚠️ **Warning**: Force pushing rewrites remote history. Only do this on branches you own or coordinate with your team.

## Restoring Original History

If something goes wrong, restore from the backup branch:

```bash
git branch -f main backup-20241025-143022
```

## Limitations

- ❌ Does not work with branches containing merge commits
- ❌ Requires linear history (use `git rebase` to linearize if needed)
- ⚠️ Requires force push if branch was already pushed remotely
- ⚠️ GPG signatures will be invalidated (you'll need to re-sign)

## Troubleshooting

### "Branch contains merge commits"

The tool only works with linear history. Options:
1. Use a different branch
2. Create a squashed version: `git checkout -b linear-main && git rebase -i --root`
3. Use interactive rebase to flatten: `git rebase -i <base>`

### "Repository has uncommitted changes"

Commit or stash your changes first:
```bash
git stash
./git-timestamp-adjust.py --branch main
git stash pop
```

### Force Push Rejected

If force push is rejected, ensure you have permission:
```bash
git push --force-with-lease origin main
```

## Requirements Satisfied

This script fully implements all requirements from `git-timestamp-requirements.md`:

- ✅ FR-1.x: Single branch operation, linear history only
- ✅ FR-2.x: Configurable time windows with midnight crossing
- ✅ FR-3.x: Temporal distance preservation, realistic coding rate, time window constraints
- ✅ FR-4.x: Proper git history rewriting with metadata preservation
- ✅ AR-1.x: Constraint satisfaction with proper prioritization
- ✅ NFR-1.x: Safety features (backup, dry-run, validation)
- ✅ NFR-2.x: Clear output and progress indication
- ✅ VR-1.x: Pre and post validation
- ✅ All edge cases handled

## License

This tool was created for personal use. Use at your own risk.

## Author

Generated by Claude AI based on formal requirements specification.
