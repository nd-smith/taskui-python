# Issue-Based Development Workflow

## Overview
This guide establishes a systematic workflow for feature development using GitHub issues, proper branching, and pull requests.

## Initial Setup

### 1. Authenticate GitHub CLI
```bash
gh auth login
```
Follow the prompts to authenticate with your GitHub account.

### 2. Verify Authentication
```bash
gh auth status
```

## Development Workflow

### Step 1: Create or Select an Issue

**Create a new issue:**
```bash
gh issue create --title "Feature: Add user authentication" --body "Description of the feature"
```

**List existing issues:**
```bash
gh issue list
```

**View issue details:**
```bash
gh issue view <issue-number>
```

### Step 2: Create Feature Branch

**Naming convention:** `issue-<number>-<short-description>`

```bash
# For issue #123 about adding authentication
git checkout -b issue-123-add-authentication
```

**Alternative using gh CLI:**
```bash
gh issue develop <issue-number> --checkout
```

### Step 3: Development

Make your changes following these practices:

1. **Make atomic commits** with clear messages:
   ```bash
   git add <files>
   git commit -m "feat: implement authentication middleware

   - Add JWT token validation
   - Create auth middleware for protected routes
   - Add user session management

   Related to #123"
   ```

2. **Commit message format:**
   - `feat:` for new features
   - `fix:` for bug fixes
   - `docs:` for documentation
   - `refactor:` for code refactoring
   - `test:` for test additions/changes
   - `chore:` for maintenance tasks

3. **Reference the issue** in commits using `#<issue-number>`

### Step 4: Keep Branch Updated

```bash
# Fetch latest changes from main
git fetch origin main

# Rebase your branch on main (preferred for clean history)
git rebase origin/main

# Or merge if conflicts are complex
git merge origin/main
```

### Step 5: Push Branch

**First push:**
```bash
git push -u origin issue-123-add-authentication
```

**Subsequent pushes:**
```bash
git push
```

### Step 6: Create Pull Request

**Using gh CLI (recommended):**
```bash
gh pr create --title "feat: Add user authentication" \
  --body "## Summary
  Implements JWT-based authentication system

  ## Changes
  - JWT token validation
  - Auth middleware
  - Session management
  - Unit tests for auth flow

  ## Testing
  - [x] Unit tests pass
  - [x] Manual testing completed
  - [x] Documentation updated

  Closes #123" \
  --base main
```

**Or create via web interface:**
```bash
gh pr create --web
```

### Step 7: Code Review Process

**Request reviewers:**
```bash
gh pr edit <pr-number> --add-reviewer <username>
```

**View PR status:**
```bash
gh pr view <pr-number>
```

**Address feedback:**
```bash
# Make changes based on feedback
git add <files>
git commit -m "refactor: address PR feedback"
git push
```

### Step 8: Merge Pull Request

**After approval, merge via CLI:**
```bash
# Squash merge (recommended for feature branches)
gh pr merge <pr-number> --squash --delete-branch

# Regular merge (preserves all commits)
gh pr merge <pr-number> --merge --delete-branch

# Rebase merge (clean linear history)
gh pr merge <pr-number> --rebase --delete-branch
```

**Or use GitHub web interface for merge**

### Step 9: Cleanup

**Update local main:**
```bash
git checkout main
git pull origin main
```

**Delete local feature branch:**
```bash
git branch -d issue-123-add-authentication
```

## Quick Reference Commands

### Issue Management
```bash
# Create issue
gh issue create

# List issues
gh issue list --state open

# View issue
gh issue view <number>

# Close issue
gh issue close <number>

# Assign issue
gh issue edit <number> --add-assignee @me
```

### Branch Management
```bash
# Create and checkout feature branch
git checkout -b issue-<number>-<description>

# List branches
git branch -a

# Delete branch
git branch -d <branch-name>

# Delete remote branch
git push origin --delete <branch-name>
```

### Pull Request Management
```bash
# Create PR
gh pr create

# List PRs
gh pr list

# View PR
gh pr view <number>

# Check out PR locally
gh pr checkout <number>

# Merge PR
gh pr merge <number>

# Close PR without merging
gh pr close <number>
```

## Best Practices

### Branch Naming
- ✅ `issue-123-add-authentication`
- ✅ `issue-456-fix-login-bug`
- ✅ `issue-789-update-docs`
- ❌ `new-feature` (no issue reference)
- ❌ `fix` (not descriptive)

### Commit Messages
- ✅ `feat: add JWT authentication middleware #123`
- ✅ `fix: resolve login redirect bug #456`
- ✅ `docs: update API documentation #789`
- ❌ `update` (not descriptive)
- ❌ `fixes` (no context)
- ❌ `WIP` (commit when ready)

### Pull Requests
- **Title**: Clear, descriptive, starts with type (`feat:`, `fix:`, etc.)
- **Description**: Summary, changes, testing done
- **References**: Always include `Closes #<issue-number>`
- **Size**: Keep PRs focused and reviewable (< 400 lines preferred)
- **Tests**: Include tests for new features
- **Documentation**: Update docs when needed

### Branch Strategy
- **main**: Production-ready code, protected
- **feature branches**: One branch per issue
- **No direct commits to main**: All changes via PR
- **Delete after merge**: Keep repository clean

## Workflow Automation

### GitHub Actions Integration
Consider setting up:
- Automated tests on PR
- Code quality checks
- Auto-label based on files changed
- Auto-assignment of reviewers

### Protected Branch Rules
Configure main branch protection:
- Require PR reviews before merging
- Require status checks to pass
- Require branches to be up to date
- Restrict who can push to main

## Troubleshooting

### Authentication Issues
```bash
# Re-authenticate
gh auth login

# Check status
gh auth status
```

### Branch Conflicts
```bash
# Rebase approach (preferred)
git fetch origin main
git rebase origin/main
# Resolve conflicts, then:
git rebase --continue

# Merge approach
git fetch origin main
git merge origin/main
# Resolve conflicts, then commit
```

### Accidental Commits to Main
```bash
# Create branch with current changes
git branch issue-<number>-<description>

# Reset main to remote
git reset --hard origin/main

# Switch to feature branch
git checkout issue-<number>-<description>
```

## Examples

### Full Feature Development Cycle
```bash
# 1. Create issue
gh issue create --title "feat: Add user profile page"

# 2. Note the issue number (e.g., #42)

# 3. Create feature branch
git checkout -b issue-42-user-profile

# 4. Make changes and commit
git add src/pages/profile.tsx
git commit -m "feat: create user profile page component #42"

# 5. Push branch
git push -u origin issue-42-user-profile

# 6. Create PR
gh pr create --title "feat: Add user profile page" \
  --body "Closes #42"

# 7. After review and approval, merge
gh pr merge 42 --squash --delete-branch

# 8. Update local main
git checkout main
git pull origin main

# 9. Delete local branch
git branch -d issue-42-user-profile
```

### Bug Fix Cycle
```bash
# 1. Create bug issue
gh issue create --title "fix: Login button not clickable on mobile"

# 2. Create branch (e.g., issue #99)
git checkout -b issue-99-fix-mobile-login

# 3. Fix and test
git add src/components/LoginButton.tsx
git commit -m "fix: make login button clickable on mobile #99"

# 4. Push and create PR
git push -u origin issue-99-fix-mobile-login
gh pr create --title "fix: Login button clickable on mobile" --body "Closes #99"

# 5. Merge after approval
gh pr merge 99 --squash --delete-branch
git checkout main && git pull
```

## Additional Resources

- [GitHub CLI Manual](https://cli.github.com/manual/)
- [Git Branching Strategies](https://git-scm.com/book/en/v2/Git-Branching-Branching-Workflows)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [GitHub Flow](https://guides.github.com/introduction/flow/)
