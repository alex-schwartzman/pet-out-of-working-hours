#!/usr/bin/env python3
"""
Git History Timestamp Adjustment Tool

Rewrites git commit history to make all commits appear as if they were made
during specified "hobby hours" (default: 20:00-04:00), while preserving
relative timing relationships and maintaining realistic commit patterns.
"""

import argparse
import subprocess
import sys
import re
from datetime import datetime, timedelta
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class Commit:
    """Represents a git commit with relevant metadata."""
    hash: str
    author_date: datetime
    committer_date: datetime
    lines_added: int
    lines_deleted: int
    message: str
    parent_count: int

    @property
    def total_lines_changed(self) -> int:
        return self.lines_added + self.lines_deleted

    @property
    def min_time_hours(self) -> float:
        """Minimum time required based on coding rate (100 lines/hour)."""
        if self.total_lines_changed == 0:
            return 5.0 / 60.0  # 5 minutes for empty commits
        return self.total_lines_changed / 100.0


class GitTimestampAdjuster:
    """Main class for adjusting git commit timestamps."""

    def __init__(
        self,
        branch: str,
        start_hour: int = 20,
        end_hour: int = 4,
        min_rate: int = 100,
        distance_factor: float = 0.5,
        dry_run: bool = False,
        backup_branch: Optional[str] = None,
        new_email: Optional[str] = None
    ):
        self.branch = branch
        self.start_hour = start_hour
        self.end_hour = end_hour
        self.min_rate = min_rate
        self.distance_factor = distance_factor
        self.dry_run = dry_run
        self.backup_branch = backup_branch or f"backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        self.new_email = new_email

        # Weekend hours (Saturday and Sunday): all day
        self.weekend_start_hour = 0
        self.weekend_end_hour = 24

        # Calculate window duration in hours
        if self.end_hour <= self.start_hour:
            # Crosses midnight (e.g., 20:00 to 04:00)
            self.window_hours = (24 - self.start_hour) + self.end_hour
        else:
            # Same day (e.g., 08:00 to 17:00)
            self.window_hours = self.end_hour - self.start_hour

    def run_git_command(self, cmd: List[str], check: bool = True) -> str:
        """Run a git command and return output."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=check
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"Error running git command: {' '.join(cmd)}", file=sys.stderr)
            print(f"Error: {e.stderr}", file=sys.stderr)
            sys.exit(1)

    def check_repository_state(self):
        """Validate repository state before processing."""
        # Check if we're in a git repository
        self.run_git_command(['git', 'rev-parse', '--git-dir'])

        # Check if branch exists
        branches = self.run_git_command(['git', 'branch', '--list', self.branch])
        if not branches:
            print(f"ERROR: Branch '{self.branch}' does not exist.", file=sys.stderr)
            sys.exit(1)

        # Check for uncommitted changes
        status = self.run_git_command(['git', 'status', '--porcelain'])
        if status:
            print("WARNING: Repository has uncommitted changes.")
            print("Uncommitted changes will not affect the history rewrite,")
            print("but you may want to commit or stash them first.")
            response = input("Continue anyway? [y/N]: ")
            if response.lower() != 'y':
                print("Aborted.")
                sys.exit(0)

    def get_commits(self) -> List[Commit]:
        """Retrieve all commits from the specified branch."""
        # Get commit list with format: hash|author_date|committer_date|parent_count|subject
        log_format = "%H|%aI|%cI|%P|%s"
        log_output = self.run_git_command([
            'git', 'log', self.branch,
            f'--format={log_format}',
            '--reverse'  # Start from oldest
        ])

        commits = []
        for line in log_output.split('\n'):
            if not line:
                continue

            parts = line.split('|', 4)
            commit_hash = parts[0]
            author_date = datetime.fromisoformat(parts[1].replace('Z', '+00:00'))
            committer_date = datetime.fromisoformat(parts[2].replace('Z', '+00:00'))
            parents = parts[3].split() if parts[3] else []
            message = parts[4] if len(parts) > 4 else ""

            # Get line statistics
            stat_output = self.run_git_command([
                'git', 'show', '--numstat', '--format=', commit_hash
            ])

            lines_added = 0
            lines_deleted = 0
            for stat_line in stat_output.split('\n'):
                if not stat_line:
                    continue
                match = re.match(r'(\d+)\s+(\d+)\s+', stat_line)
                if match:
                    lines_added += int(match.group(1))
                    lines_deleted += int(match.group(2))

            commits.append(Commit(
                hash=commit_hash,
                author_date=author_date,
                committer_date=committer_date,
                lines_added=lines_added,
                lines_deleted=lines_deleted,
                message=message,
                parent_count=len(parents)
            ))

        return commits

    def check_for_merges(self, commits: List[Commit]):
        """Check for merge commits and exit if found."""
        merge_commits = [c for c in commits if c.parent_count > 1]

        if merge_commits:
            print("\nERROR: Cannot process branch with merge commits.\n", file=sys.stderr)
            print(f"Branch '{self.branch}' contains merge commits at:", file=sys.stderr)
            for commit in merge_commits:
                date_str = commit.author_date.strftime('%Y-%m-%d')
                print(f"  - {commit.hash[:7]} ({commit.message[:50]} - {date_str})", file=sys.stderr)

            print("\nThis tool only works with linear history (no merges).\n", file=sys.stderr)
            print("Suggestions:", file=sys.stderr)
            print("  1. Use a different branch with linear history", file=sys.stderr)
            print("  2. Create a squashed copy of your branch", file=sys.stderr)
            print("  3. Rebase to create linear history (git rebase -i)", file=sys.stderr)
            sys.exit(1)

    def is_weekend(self, dt: datetime) -> bool:
        """Check if a datetime falls on a weekend (Saturday=5, Sunday=6)."""
        return dt.weekday() in (5, 6)

    def is_in_hobby_window(self, dt: datetime) -> bool:
        """Check if a datetime is within hobby hours."""
        # Work with naive datetime (local time)
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)

        # Weekend: all day (00:00-24:00)
        if self.is_weekend(dt):
            return True

        # Weekday: use configured hours
        hour = dt.hour
        if self.start_hour < self.end_hour:
            # Same day window
            return self.start_hour <= hour < self.end_hour
        else:
            # Crosses midnight
            return hour >= self.start_hour or hour < self.end_hour

    def get_next_hobby_start(self, dt: datetime) -> datetime:
        """Get the next hobby window start time from a given datetime."""
        # Convert to naive local time for calculation
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)

        # If it's a weekend, start immediately (00:00 or current time if already in weekend)
        if self.is_weekend(dt):
            # Start at midnight of the weekend day
            return dt.replace(hour=0, minute=0, second=0, microsecond=0)

        # Check if we can start today (weekday evening)
        start_time = dt.replace(hour=self.start_hour, minute=0, second=0, microsecond=0)

        if self.start_hour < self.end_hour:
            # Same day window
            if dt.hour >= self.start_hour:
                # Already past start time, check if next day is weekend
                next_day = dt + timedelta(days=1)
                if self.is_weekend(next_day):
                    # Next day is weekend, start at midnight
                    return next_day.replace(hour=0, minute=0, second=0, microsecond=0)
                else:
                    # Next day is weekday
                    return start_time + timedelta(days=1)
        else:
            # Crosses midnight
            if self.start_hour <= dt.hour < 24:
                # Can start today
                pass
            elif dt.hour < self.end_hour:
                # We're in the early morning part of the window from yesterday
                # Go back to yesterday's start
                start_time -= timedelta(days=1)
            else:
                # Past the morning part, check what's next
                # Check if tomorrow is a weekend
                next_day = dt + timedelta(days=1)
                if self.is_weekend(next_day):
                    return next_day.replace(hour=0, minute=0, second=0, microsecond=0)
                # Otherwise wait until evening

        return start_time

    def get_window_end(self, start: datetime) -> datetime:
        """Get the end time of a hobby window given its start."""
        # Work with naive datetime
        if start.tzinfo is not None:
            start = start.replace(tzinfo=None)

        # Weekend: end at midnight Monday (covers whole weekend)
        if self.is_weekend(start):
            # If it's Saturday, end at midnight Monday (2 days)
            # If it's Sunday, end at midnight Monday (1 day)
            days_until_monday = 7 - start.weekday()  # weekday: Sat=5, Sun=6
            if start.weekday() == 5:  # Saturday
                days_until_monday = 2
            else:  # Sunday
                days_until_monday = 1
            end = start + timedelta(days=days_until_monday)
            return end.replace(hour=0, minute=0, second=0, microsecond=0)

        # Weekday logic
        if self.start_hour < self.end_hour:
            # Same day
            return start.replace(hour=self.end_hour, minute=0, second=0, microsecond=0)
        else:
            # Next day
            end = start + timedelta(days=1)
            return end.replace(hour=self.end_hour, minute=0, second=0, microsecond=0)

    def calculate_new_timestamps(self, commits: List[Commit]) -> List[Tuple[Commit, datetime, datetime]]:
        """
        Calculate new timestamps for all commits.

        Returns list of tuples: (commit, new_author_date, new_committer_date)
        """
        if not commits:
            return []

        adjusted = []

        # Start from the first hobby window after the first commit
        # Convert to naive datetime for calculations
        first_commit_date = commits[0].author_date
        if first_commit_date.tzinfo is not None:
            first_commit_date = first_commit_date.replace(tzinfo=None)

        current_time = self.get_next_hobby_start(first_commit_date)

        # Track which window we're currently in
        window_start = current_time
        window_end = self.get_window_end(window_start)

        for i, commit in enumerate(commits):
            # Calculate minimum time from previous commit
            if i > 0:
                prev_commit = commits[i - 1]

                # FR-3.1: Temporal distance preservation (50% minimum)
                original_distance = (commit.author_date - prev_commit.author_date).total_seconds()
                min_distance_seconds = original_distance * self.distance_factor

                # FR-3.3: Realistic coding rate
                min_coding_time_seconds = commit.min_time_hours * 3600

                # Take the maximum of both constraints
                min_gap_seconds = max(min_distance_seconds, min_coding_time_seconds)
                min_gap = timedelta(seconds=min_gap_seconds)

                # Add the gap to current time
                next_time = current_time + min_gap

                # Check if next_time fits in current window
                if next_time >= window_end:
                    # Doesn't fit, move to next window
                    # Move past the current window end to find the next window
                    next_window_search = window_end + timedelta(hours=1)
                    window_start = self.get_next_hobby_start(next_window_search)
                    window_end = self.get_window_end(window_start)
                    current_time = window_start
                else:
                    current_time = next_time
            else:
                # First commit - just use the window start
                current_time = window_start

            # Set both author and committer date to the same value
            adjusted.append((commit, current_time, current_time))

        return adjusted

    def validate_adjustments(
        self,
        original_commits: List[Commit],
        adjusted: List[Tuple[Commit, datetime, datetime]]
    ) -> bool:
        """Validate that all constraints are satisfied."""
        errors = []

        for i, (commit, new_author_date, new_committer_date) in enumerate(adjusted):
            # Check hobby window constraint
            if not self.is_in_hobby_window(new_author_date):
                errors.append(
                    f"Commit {commit.hash[:7]} timestamp {new_author_date} "
                    f"is outside hobby hours"
                )

            # Check chronological order
            if i > 0:
                prev_new_date = adjusted[i-1][1]
                if new_author_date <= prev_new_date:
                    errors.append(
                        f"Commit {commit.hash[:7]} breaks chronological order"
                    )

                # Check temporal distance preservation
                original_distance = (
                    original_commits[i].author_date -
                    original_commits[i-1].author_date
                ).total_seconds()
                new_distance = (new_author_date - prev_new_date).total_seconds()
                min_required = original_distance * self.distance_factor

                if new_distance < min_required - 1:  # -1 for floating point tolerance
                    errors.append(
                        f"Commit {commit.hash[:7]} temporal distance too small: "
                        f"{new_distance:.0f}s < {min_required:.0f}s required"
                    )

                # Check coding rate
                min_coding_seconds = commit.min_time_hours * 3600
                if new_distance < min_coding_seconds - 1:
                    errors.append(
                        f"Commit {commit.hash[:7]} coding rate too fast: "
                        f"{new_distance:.0f}s for {commit.total_lines_changed} lines"
                    )

        if errors:
            print("\nVALIDATION ERRORS:", file=sys.stderr)
            for error in errors:
                print(f"  - {error}", file=sys.stderr)
            return False

        return True

    def print_summary(
        self,
        commits: List[Commit],
        adjusted: List[Tuple[Commit, datetime, datetime]]
    ):
        """Print a summary of the proposed changes."""
        print("\nGit History Timestamp Adjustment", end="")
        if self.dry_run:
            print(" - Dry Run")
        else:
            print()
        print("=" * 60)

        print(f"\nConfiguration:")
        print(f"  Branch: {self.branch}")
        print(f"  Weekday hobby hours: {self.start_hour:02d}:00 - {self.end_hour:02d}:00")
        print(f"  Weekend hobby hours: 00:00 - 24:00 (all day)")
        print(f"  Minimum rate: {self.min_rate} lines/hour")
        print(f"  Distance factor: {self.distance_factor}")
        if self.new_email:
            print(f"  New email: {self.new_email}")

        print(f"\nAnalysis:")
        print(f"  Total commits: {len(commits)}")

        merge_count = sum(1 for c in commits if c.parent_count > 1)
        print(f"  Merge commits: {merge_count} ✓")

        if commits:
            orig_start = commits[0].author_date
            orig_end = commits[-1].author_date
            orig_span = (orig_end - orig_start).days

            new_start = adjusted[0][1]
            new_end = adjusted[-1][1]
            new_span_days = (new_end - new_start).days

            print(f"  Original span: {orig_start.strftime('%Y-%m-%d %H:%M')} to "
                  f"{orig_end.strftime('%Y-%m-%d %H:%M')} ({orig_span} days)")
            print(f"  Adjusted span: {new_start.strftime('%Y-%m-%d %H:%M')} to "
                  f"{new_end.strftime('%Y-%m-%d %H:%M')} ({new_span_days} nights)")

        # Show sample changes (first 5)
        print(f"\nSample changes:")
        for i, (commit, new_author, new_committer) in enumerate(adjusted[:5]):
            # Convert to naive for comparison if needed
            orig_date = commit.author_date
            if orig_date.tzinfo is not None:
                orig_date = orig_date.replace(tzinfo=None)

            time_diff = new_author - orig_date
            hours = int(time_diff.total_seconds() / 3600)
            minutes = int((time_diff.total_seconds() % 3600) / 60)
            sign = "+" if time_diff.total_seconds() > 0 else ""

            print(f"  {commit.hash[:7]}: "
                  f"{orig_date.strftime('%Y-%m-%d %H:%M')} -> "
                  f"{new_author.strftime('%Y-%m-%d %H:%M')} "
                  f"({commit.total_lines_changed} lines, {sign}{hours}h{minutes:02d}m)")

        if len(adjusted) > 5:
            print(f"  ... and {len(adjusted) - 5} more commits")

        # Validation
        print(f"\nConstraints satisfied:")
        print(f"  ✓ All timestamps within hobby hours")
        print(f"  ✓ Chronological order preserved")
        print(f"  ✓ Minimum coding rate satisfied")
        print(f"  ✓ Temporal distance ≥{int(self.distance_factor*100)}% preserved")

        if self.dry_run:
            print(f"\nWould rewrite {len(commits)} commits across {new_span_days} nights.")
            print("Run without --dry-run to apply changes.")
        else:
            print(f"\nWill rewrite {len(commits)} commits across {new_span_days} nights.")

    def apply_changes(self, adjusted: List[Tuple[Commit, datetime, datetime]]):
        """Apply the timestamp changes to the git repository."""
        if self.dry_run:
            return

        print(f"\nCreating backup branch '{self.backup_branch}'...")
        self.run_git_command(['git', 'branch', self.backup_branch, self.branch])

        print(f"Rewriting history on branch '{self.branch}'...")

        # Use git filter-branch to rewrite commits
        # Build the env filter script
        filter_script = "case $GIT_COMMIT in\n"

        for commit, new_author, new_committer in adjusted:
            # Format dates as git expects (Unix timestamp + timezone)
            author_timestamp = int(new_author.timestamp())
            committer_timestamp = int(new_committer.timestamp())

            # Use local timezone
            tz_offset = new_author.strftime('%z')
            if not tz_offset:
                tz_offset = '+0000'

            filter_script += f"    {commit.hash})\n"
            filter_script += f"        export GIT_AUTHOR_DATE='{author_timestamp} {tz_offset}'\n"
            filter_script += f"        export GIT_COMMITTER_DATE='{committer_timestamp} {tz_offset}'\n"

            # Change email if specified
            if self.new_email:
                filter_script += f"        export GIT_AUTHOR_EMAIL='{self.new_email}'\n"
                filter_script += f"        export GIT_COMMITTER_EMAIL='{self.new_email}'\n"

            filter_script += f"        ;;\n"

        filter_script += "esac"

        # Run filter-branch
        try:
            self.run_git_command([
                'git', 'filter-branch',
                '--force',
                '--env-filter', filter_script,
                '--', self.branch
            ])

            print(f"\n✓ History rewritten successfully!")
            print(f"  Original branch backed up as '{self.backup_branch}'")
            print(f"  Modified branch: '{self.branch}'")
            print(f"\nNOTE: If you need to push this branch, use:")
            print(f"  git push --force origin {self.branch}")

        except Exception as e:
            print(f"\nERROR during history rewrite: {e}", file=sys.stderr)
            print(f"Your original branch is safe at '{self.backup_branch}'", file=sys.stderr)
            sys.exit(1)

    def run(self):
        """Main execution flow."""
        print("Checking repository state...")
        self.check_repository_state()

        print(f"Loading commits from branch '{self.branch}'...")
        commits = self.get_commits()

        if not commits:
            print("No commits found on branch.", file=sys.stderr)
            sys.exit(1)

        print(f"Found {len(commits)} commits.")

        print("Checking for merge commits...")
        self.check_for_merges(commits)

        print("Calculating new timestamps...")
        adjusted = self.calculate_new_timestamps(commits)

        print("Validating adjustments...")
        if not self.validate_adjustments(commits, adjusted):
            print("\nValidation failed. Aborting.", file=sys.stderr)
            sys.exit(1)

        self.print_summary(commits, adjusted)

        if not self.dry_run:
            print("\n" + "="*60)
            response = input("\nProceed with history rewrite? [y/N]: ")
            if response.lower() != 'y':
                print("Aborted.")
                sys.exit(0)

            self.apply_changes(adjusted)


def main():
    parser = argparse.ArgumentParser(
        description='Adjust git commit timestamps to appear within hobby hours',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run (show what would be done)
  %(prog)s --branch main --dry-run

  # Apply changes with custom hours (9 PM to 2 AM)
  %(prog)s --branch feature-x --start-hour 21 --end-hour 2

  # With custom coding rate (50 lines per hour)
  %(prog)s --branch main --min-rate 50
"""
    )

    parser.add_argument(
        '--branch',
        required=True,
        help='Branch to process (required)'
    )
    parser.add_argument(
        '--start-hour',
        type=int,
        default=20,
        help='Start of hobby hours (0-23, default: 20)'
    )
    parser.add_argument(
        '--end-hour',
        type=int,
        default=4,
        help='End of hobby hours (0-23, default: 4)'
    )
    parser.add_argument(
        '--min-rate',
        type=int,
        default=100,
        help='Minimum coding rate in lines/hour (default: 100)'
    )
    parser.add_argument(
        '--distance-factor',
        type=float,
        default=0.5,
        help='Temporal distance preservation factor 0-1 (default: 0.5)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show proposed changes without applying them'
    )
    parser.add_argument(
        '--backup-branch',
        help='Name for backup branch (default: backup-TIMESTAMP)'
    )
    parser.add_argument(
        '--new-email',
        help='Replace author and committer email with this address'
    )

    args = parser.parse_args()

    # Validate arguments
    if not (0 <= args.start_hour < 24):
        print("Error: --start-hour must be 0-23", file=sys.stderr)
        sys.exit(1)

    if not (0 <= args.end_hour < 24):
        print("Error: --end-hour must be 0-23", file=sys.stderr)
        sys.exit(1)

    if args.min_rate <= 0:
        print("Error: --min-rate must be positive", file=sys.stderr)
        sys.exit(1)

    if not (0 < args.distance_factor <= 1):
        print("Error: --distance-factor must be between 0 and 1", file=sys.stderr)
        sys.exit(1)

    # Run the adjuster
    adjuster = GitTimestampAdjuster(
        branch=args.branch,
        start_hour=args.start_hour,
        end_hour=args.end_hour,
        min_rate=args.min_rate,
        distance_factor=args.distance_factor,
        dry_run=args.dry_run,
        backup_branch=args.backup_branch,
        new_email=args.new_email
    )

    adjuster.run()


if __name__ == '__main__':
    main()
