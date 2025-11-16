#!/bin/bash
# Issue-based development workflow helper script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_success() { echo -e "${GREEN}✓${NC} $1"; }
print_error() { echo -e "${RED}✗${NC} $1"; }
print_info() { echo -e "${BLUE}ℹ${NC} $1"; }
print_warning() { echo -e "${YELLOW}⚠${NC} $1"; }

# Check if gh CLI is authenticated
check_auth() {
    if ! gh auth status &>/dev/null; then
        print_error "GitHub CLI not authenticated"
        print_info "Run: gh auth login"
        exit 1
    fi
}

# Check if on main branch
check_main_branch() {
    current_branch=$(git rev-parse --abbrev-ref HEAD)
    if [ "$current_branch" != "main" ]; then
        print_warning "Not on main branch (currently on: $current_branch)"
        return 1
    fi
    return 0
}

# Show usage
usage() {
    cat << EOF
Usage: $0 <command> [options]

Commands:
    start <issue-number>              Start working on an issue (creates branch)
    create <title>                    Create a new issue and start working on it
    commit <message>                  Commit changes with proper formatting
    pr                                Create pull request for current branch
    merge <pr-number>                 Merge pull request (squash)
    finish                            Finish current issue (after PR merged)
    list                              List open issues
    status                            Show current issue status

Examples:
    $0 start 123                      # Start working on issue #123
    $0 create "Add login feature"     # Create issue and start working
    $0 commit "implement auth"        # Commit with message
    $0 pr                             # Create PR for current branch
    $0 merge 42                       # Merge PR #42
    $0 finish                         # Clean up after merge
    $0 list                           # Show open issues

EOF
    exit 1
}

# Start working on an issue
start_issue() {
    local issue_number=$1

    if [ -z "$issue_number" ]; then
        print_error "Issue number required"
        usage
    fi

    check_auth

    # Get issue title
    print_info "Fetching issue #$issue_number..."
    issue_title=$(gh issue view "$issue_number" --json title --jq .title 2>/dev/null)

    if [ -z "$issue_title" ]; then
        print_error "Issue #$issue_number not found"
        exit 1
    fi

    # Create branch name from title
    branch_suffix=$(echo "$issue_title" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | cut -c1-50)
    branch_name="issue-${issue_number}-${branch_suffix}"

    # Ensure we're on main and up to date
    print_info "Ensuring main branch is up to date..."
    if check_main_branch; then
        git pull origin main
    else
        git checkout main
        git pull origin main
    fi

    # Create and checkout branch
    print_info "Creating branch: $branch_name"
    git checkout -b "$branch_name"

    # Assign issue to self
    gh issue edit "$issue_number" --add-assignee @me 2>/dev/null || true

    print_success "Started working on issue #$issue_number"
    print_info "Branch: $branch_name"
    print_info "Title: $issue_title"
}

# Create new issue and start working
create_issue() {
    local title="$*"

    if [ -z "$title" ]; then
        print_error "Issue title required"
        usage
    fi

    check_auth

    print_info "Creating issue: $title"
    issue_number=$(gh issue create --title "$title" --body "" --assignee @me --json number --jq .number)

    if [ -z "$issue_number" ]; then
        print_error "Failed to create issue"
        exit 1
    fi

    print_success "Created issue #$issue_number"
    start_issue "$issue_number"
}

# Commit changes
commit_changes() {
    local message="$*"

    if [ -z "$message" ]; then
        print_error "Commit message required"
        usage
    fi

    # Extract issue number from branch name
    current_branch=$(git rev-parse --abbrev-ref HEAD)
    issue_number=$(echo "$current_branch" | grep -oP 'issue-\K\d+' || echo "")

    if [ -z "$issue_number" ]; then
        print_warning "Not on an issue branch, committing without issue reference"
        git add -A
        git commit -m "$message"
    else
        # Auto-detect commit type
        if echo "$message" | grep -qE '^(feat|fix|docs|refactor|test|chore):'; then
            commit_msg="$message #$issue_number"
        else
            commit_msg="feat: $message #$issue_number"
        fi

        print_info "Committing with message: $commit_msg"
        git add -A
        git commit -m "$commit_msg"
        print_success "Changes committed"
    fi
}

# Create pull request
create_pr() {
    check_auth

    current_branch=$(git rev-parse --abbrev-ref HEAD)

    if [ "$current_branch" = "main" ]; then
        print_error "Cannot create PR from main branch"
        exit 1
    fi

    # Extract issue number
    issue_number=$(echo "$current_branch" | grep -oP 'issue-\K\d+' || echo "")

    if [ -z "$issue_number" ]; then
        print_error "Cannot detect issue number from branch name"
        exit 1
    fi

    # Push current branch
    print_info "Pushing branch: $current_branch"
    git push -u origin "$current_branch"

    # Get issue title for PR
    issue_title=$(gh issue view "$issue_number" --json title --jq .title)

    # Create PR
    print_info "Creating pull request..."
    pr_url=$(gh pr create \
        --title "$issue_title" \
        --body "Closes #$issue_number" \
        --base main \
        --head "$current_branch" 2>&1)

    print_success "Pull request created"
    echo "$pr_url"
}

# Merge pull request
merge_pr() {
    local pr_number=$1

    if [ -z "$pr_number" ]; then
        print_error "PR number required"
        usage
    fi

    check_auth

    print_info "Merging PR #$pr_number (squash merge)..."
    gh pr merge "$pr_number" --squash --delete-branch

    print_success "PR #$pr_number merged and branch deleted"
    print_info "Run '$0 finish' to clean up local branches"
}

# Finish working on issue
finish_issue() {
    current_branch=$(git rev-parse --abbrev-ref HEAD)

    if [ "$current_branch" = "main" ]; then
        print_warning "Already on main branch"
        git pull origin main
        print_success "Main branch updated"
        return
    fi

    print_info "Switching to main and updating..."
    git checkout main
    git pull origin main

    print_info "Deleting local branch: $current_branch"
    git branch -d "$current_branch" 2>/dev/null || git branch -D "$current_branch"

    print_success "Issue workflow complete"
}

# List open issues
list_issues() {
    check_auth

    print_info "Open issues:"
    gh issue list --state open --limit 20
}

# Show current status
show_status() {
    check_auth

    current_branch=$(git rev-parse --abbrev-ref HEAD)
    print_info "Current branch: $current_branch"

    # Extract issue number
    issue_number=$(echo "$current_branch" | grep -oP 'issue-\K\d+' || echo "")

    if [ -n "$issue_number" ]; then
        print_info "Working on issue #$issue_number:"
        gh issue view "$issue_number"

        echo ""
        print_info "Git status:"
        git status --short

        # Check if PR exists
        pr_number=$(gh pr list --head "$current_branch" --json number --jq '.[0].number' 2>/dev/null || echo "")
        if [ -n "$pr_number" ]; then
            echo ""
            print_info "Pull Request #$pr_number:"
            gh pr view "$pr_number"
        fi
    else
        print_info "Not working on an issue branch"
        git status
    fi
}

# Main command routing
case "${1:-}" in
    start)
        start_issue "$2"
        ;;
    create)
        shift
        create_issue "$@"
        ;;
    commit)
        shift
        commit_changes "$@"
        ;;
    pr)
        create_pr
        ;;
    merge)
        merge_pr "$2"
        ;;
    finish)
        finish_issue
        ;;
    list)
        list_issues
        ;;
    status)
        show_status
        ;;
    *)
        usage
        ;;
esac
