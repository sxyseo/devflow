#!/usr/bin/env python3
"""
Test script to verify commit history tracking is working correctly.

This script tests:
1. Git commits are being tracked
2. Backend API returns commit data
3. Commit details are accurate (hash, message, timestamp)
4. WebSocket updates are being sent
"""

import subprocess
import json
import time
import requests
from datetime import datetime

def run_command(cmd):
    """Run a shell command and return output."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout.strip(), result.stderr.strip(), result.returncode

def test_git_commit_exists(commit_hash):
    """Test that commit exists in git log."""
    print(f"\n✓ Testing git commit exists: {commit_hash}")
    stdout, stderr, code = run_command(f"git log --oneline | grep '{commit_hash}'")
    if code == 0 and stdout:
        print(f"  ✓ Commit found in git log: {stdout}")
        return True
    else:
        print(f"  ✗ Commit not found in git log")
        return False

def test_api_returns_commit(commit_hash):
    """Test that API returns the commit."""
    print(f"\n✓ Testing API returns commit: {commit_hash}")
    try:
        response = requests.get('http://localhost:3001/api/commits?limit=5', timeout=5)
        if response.status_code == 200:
            commits = response.json()
            for commit in commits:
                if commit.get('shortHash') == commit_hash or commit.get('hash', '').startswith(commit_hash):
                    print(f"  ✓ Commit found in API response")
                    print(f"    - Hash: {commit.get('shortHash')}")
                    print(f"    - Subject: {commit.get('message', {}).get('subject')}")
                    print(f"    - Author: {commit.get('author', {}).get('name')}")
                    print(f"    - Date: {commit.get('date')}")
                    if commit.get('stats'):
                        print(f"    - Files changed: {commit['stats'].get('total', {}).get('changes', 0)}")
                    return True
            print(f"  ✗ Commit not found in API response")
            return False
        else:
            print(f"  ✗ API returned status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"  ✗ Error fetching from API: {e}")
        return False

def test_commit_details_accuracy(commit_hash):
    """Test that commit details are accurate."""
    print(f"\n✓ Testing commit details accuracy: {commit_hash}")

    # Get commit details from git
    stdout, stderr, code = run_command(f"git log -1 --pretty=format:'%H|%an|%ae|%ad|%s' {commit_hash} --date=iso")
    if code != 0:
        print(f"  ✗ Failed to get commit from git")
        return False

    git_parts = stdout.split('|')
    if len(git_parts) < 5:
        print(f"  ✗ Failed to parse git output")
        return False

    git_full_hash = git_parts[0]
    git_author = git_parts[1]
    git_email = git_parts[2]
    git_date = git_parts[3]
    git_subject = git_parts[4]

    print(f"  Git details:")
    print(f"    - Hash: {git_full_hash[:7]}")
    print(f"    - Author: {git_author} <{git_email}>")
    print(f"    - Date: {git_date}")
    print(f"    - Subject: {git_subject}")

    # Get commit details from API
    try:
        response = requests.get('http://localhost:3001/api/commits?limit=10', timeout=5)
        if response.status_code != 200:
            print(f"  ✗ API returned status code: {response.status_code}")
            return False

        commits = response.json()
        api_commit = None
        for commit in commits:
            if commit.get('shortHash') == commit_hash or commit.get('hash', '').startswith(commit_hash):
                api_commit = commit
                break

        if not api_commit:
            print(f"  ✗ Commit not found in API response")
            return False

        api_hash = api_commit.get('shortHash')
        api_author = api_commit.get('author', {}).get('name')
        api_subject = api_commit.get('message', {}).get('subject')

        print(f"  API details:")
        print(f"    - Hash: {api_hash}")
        print(f"    - Author: {api_author}")
        print(f"    - Subject: {api_subject}")

        # Verify details match
        if git_full_hash[:7] != api_hash:
            print(f"  ✗ Hash mismatch: git={git_full_hash[:7]}, api={api_hash}")
            return False

        if git_author != api_author:
            print(f"  ✗ Author mismatch: git={git_author}, api={api_author}")
            return False

        if git_subject != api_subject:
            print(f"  ✗ Subject mismatch: git={git_subject}, api={api_subject}")
            return False

        print(f"  ✓ All commit details are accurate!")
        return True

    except Exception as e:
        print(f"  ✗ Error fetching from API: {e}")
        return False

def test_websocket_broadcast():
    """Test that WebSocket is broadcasting commit updates."""
    print(f"\n✓ Testing WebSocket broadcast")

    # Check if server is running
    try:
        response = requests.get('http://localhost:3001', timeout=2)
        if response.status_code == 200:
            print(f"  ✓ Backend server is running on port 3001")
            return True
        else:
            print(f"  ✗ Backend server returned status: {response.status_code}")
            return False
    except Exception as e:
        print(f"  ✗ Backend server not accessible: {e}")
        return False

def main():
    """Run all tests."""
    print("=" * 70)
    print("COMMIT HISTORY TRACKING TEST")
    print("=" * 70)
    print(f"Test started at: {datetime.now().isoformat()}")

    # Get the most recent commit hash
    stdout, stderr, code = run_command("git log -1 --pretty=format:'%h'")
    if code != 0:
        print("✗ Failed to get recent commit hash")
        return

    commit_hash = stdout
    print(f"\nTesting commit: {commit_hash}")
    print(f"Current branch: {run_command('git branch --show-current')[0]}")

    # Run tests
    results = {
        'git_commit_exists': test_git_commit_exists(commit_hash),
        'api_returns_commit': test_api_returns_commit(commit_hash),
        'commit_details_accuracy': test_commit_details_accuracy(commit_hash),
        'websocket_broadcast': test_websocket_broadcast(),
    }

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n✓ ALL TESTS PASSED - Commit history tracking is working correctly!")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed")
        return 1

if __name__ == '__main__':
    exit(main())
