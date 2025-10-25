# **Git History Timestamp Adjustment Tool - Requirements Specification**

## **1. Overview**

A tool to rewrite git commit history timestamps (both author and committer dates) to make all commits appear as if they were made during specified "hobby hours" (20:00-04:00), while preserving relative timing relationships and maintaining realistic commit patterns.

## **2. Functional Requirements**

### **2.1 Input Requirements**
- **FR-1.1**: Tool shall operate on a single specified git branch
- **FR-1.2**: Tool shall read the complete git log including:
  - Commit hashes
  - Author dates
  - Committer dates
  - Commit statistics (lines added/deleted per commit)
  - Parent count (to detect merges)

### **2.2 Branch and Merge Handling**
- **FR-1.3**: Tool shall operate on ONE branch only
- **FR-1.4**: Tool shall detect merge commits (commits with multiple parents)
- **FR-1.5**: If any merge commits are found in the branch history:
  - Tool shall immediately exit with an error
  - Error message shall list all merge commit hashes found
  - Error message: "Cannot process branch with merge commits. Found merges at: <hash1>, <hash2>, ... Please use a linear history branch."
- **FR-1.6**: Tool shall NOT process multiple branches simultaneously

### **2.3 Time Window Configuration**
- **FR-2.1**: Default hobby hours: 20:00-04:00 (crosses midnight)
- **FR-2.2**: Tool shall support configurable time windows
- **FR-2.3**: Time window may span midnight (e.g., 20:00-04:00)

### **2.4 Timestamp Adjustment Rules**

#### **2.4.1 Temporal Distance Preservation**
- **FR-3.1**: For any two commits A and B where `original_distance = |timestamp_B - timestamp_A|`:
  - New distance must be ≥ `original_distance * 0.5`
  - Formula: `new_distance ≥ original_distance / 2`
- **FR-3.2**: This rule applies to all commit pairs, not just adjacent commits

#### **2.4.2 Realistic Coding Rate**
- **FR-3.3**: Minimum time between commits based on code changes:
  - Base rate: 100 lines of code per hour
  - Formula: `min_time_hours = total_line_changes / 100`
  - Where `total_line_changes = lines_added + lines_deleted`
- **FR-3.4**: If a commit has <100 lines changed, minimum gap is proportional (e.g., 50 lines = 30 minutes)

#### **2.4.3 Time Window Constraint**
- **FR-3.5**: All adjusted timestamps must fall within hobby hours (20:00-04:00)
- **FR-3.6**: If a sequence of commits cannot fit in one night's window:
  - Continue into subsequent nights
  - Maintain chronological order across nights
- **FR-3.7**: Preserve original date ordering (commit N+1 must be after commit N)

### **2.5 Git History Rewriting**
- **FR-4.1**: Tool shall rewrite both `GIT_AUTHOR_DATE` and `GIT_COMMITTER_DATE`
- **FR-4.2**: Tool shall preserve all other commit metadata:
  - Commit messages
  - Author name and email
  - Committer name and email
  - Tree content
  - Parent relationships (single parent only, since merges are rejected)
- **FR-4.3**: Tool shall only process the specified branch

## **3. Algorithm Requirements**

### **3.1 Constraint Satisfaction**
- **AR-1.1**: The algorithm must satisfy all three constraints simultaneously:
  1. Temporal distance preservation (FR-3.1)
  2. Realistic coding rate (FR-3.3)
  3. Time window constraint (FR-3.5)
- **AR-1.2**: When constraints conflict, priority order:
  1. Chronological ordering (mandatory)
  2. Realistic coding rate (mandatory minimum)
  3. Temporal distance preservation (best effort, minimum 50%)
  4. Maximize time window utilization

### **3.2 Optimization Goals**
- **AR-2.1**: Minimize the total time span across nights
- **AR-2.2**: Distribute commits naturally within available windows
- **AR-2.3**: Avoid unrealistic patterns (e.g., all commits at exactly 20:00)

## **4. Non-Functional Requirements**

### **4.1 Safety**
- **NFR-1.1**: Tool must create a backup branch before rewriting history
- **NFR-1.2**: Tool must provide dry-run mode showing proposed changes
- **NFR-1.3**: Tool must validate git repository state before operation
- **NFR-1.4**: Tool must warn if repository has uncommitted changes
- **NFR-1.5**: Tool must detect and reject branches with merge commits before any modifications

### **4.2 Usability**
- **NFR-2.1**: Tool shall provide clear progress indication
- **NFR-2.2**: Tool shall display summary of changes:
  - Original time span
  - New time span
  - Number of commits adjusted
  - Date range affected
- **NFR-2.3**: Tool shall validate that results meet all constraints

### **4.3 Performance**
- **NFR-3.1**: Tool should handle repositories with 1000+ commits
- **NFR-3.2**: Processing time should be reasonable (<5 minutes for 1000 commits)

## **5. Input/Output Specifications**

### **5.1 Interface Options**
The tool may be implemented as:
- Command-line application
- Python library/module
- Script
- Any other suitable format

Configuration parameters (however exposed):
- Start hour of hobby window (default: 20)
- End hour of hobby window (default: 4)
- Minimum coding rate in lines/hour (default: 100)
- Temporal distance preservation factor (default: 0.5)
- Branch name to process
- Dry-run mode flag
- Backup branch name (optional)

### **5.2 Output Format (Dry Run Example)**
```
Git History Timestamp Adjustment - Dry Run
==========================================

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
  def5678: 2024-01-15 14:22 -> 2024-01-15 22:47 (+8h25m)
  ...

Constraints satisfied: ✓
  ✓ All timestamps within hobby hours
  ✓ Chronological order preserved
  ✓ Minimum coding rate satisfied
  ✓ Temporal distance ≥50% preserved

Would rewrite 247 commits across 34 nights.
Run without --dry-run to apply changes.
```

### **5.3 Error Messages**

#### **Merge Commits Detected**
```
ERROR: Cannot process branch with merge commits.

Branch 'main' contains merge commits at:
  - a1b2c3d (Merge branch 'feature-x' - 2024-02-15)
  - e4f5g6h (Merge pull request #42 - 2024-03-01)

This tool only works with linear history (no merges).

Suggestions:
  1. Use a different branch with linear history
  2. Create a squashed copy of your branch
  3. Rebase to create linear history (git rebase -i)
```

## **6. Edge Cases**

- **EC-1**: Single commit with massive changes (>1000 lines)
  - Should span multiple sessions realistically
- **EC-2**: Many tiny commits in quick succession
  - Should be spaced at minimum realistic intervals
- **EC-3**: Empty commits or commits with 0 line changes
  - Use minimum time gap (e.g., 5 minutes)
- **EC-4**: Branch with only 1-2 commits
  - Should still apply time window constraints
- **EC-5**: Commits that already fall within hobby hours
  - Should still be adjusted to maintain relative distances

## **7. Validation Requirements**

- **VR-1**: Before processing, tool must verify:
  - Branch exists
  - No merge commits present in branch history
  - Repository is in clean state (or warn about uncommitted changes)

- **VR-2**: After rewriting, tool must verify:
  - All commits still present
  - Tree content unchanged
  - All timestamps within specified windows
  - Chronological order maintained

- **VR-3**: Tool must report any constraint violations

## **8. Documentation Requirements**

- **DR-1**: README with usage examples
- **DR-2**: Warning about force-push requirements for remote repositories
- **DR-3**: Explanation of algorithm and constraints
- **DR-4**: Clear documentation that only linear history (no merges) is supported
- **DR-5**: Troubleshooting guide

---

## **9. Success Criteria**

The tool shall be considered successful if:
1. It can process a linear branch with 100+ commits without errors
2. It correctly detects and rejects branches with merge commits
3. All adjusted timestamps fall within specified hobby hours
4. Temporal relationships are preserved (≥50% distance)
5. Coding rate constraint is satisfied for all commits
6. Git history integrity is maintained (no lost commits/content)
7. Tool provides clear feedback and safety mechanisms

---

**End of Requirements Specification**
