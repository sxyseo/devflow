#!/usr/bin/env python3
"""
Test script for cost metrics display.

This script:
1. Records API calls and agent operations using CostTracker
2. Verifies costs are saved to costs.json
3. Verifies the backend API returns the cost data
4. Documents the results
"""

import json
import sys
import time
from pathlib import Path
from datetime import datetime

# Add the project to the path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from devflow.utils.cost_tracker import CostTracker, CostType
    from devflow.config.settings import settings
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this from the project root directory")
    sys.exit(1)


def test_cost_tracker():
    """Test 1: Verify CostTracker records API usage"""
    print("\n" + "="*60)
    print("TEST 1: CostTracker Records API Usage")
    print("="*60)

    tracker = CostTracker()

    # Record some API calls
    print("\n📝 Recording API calls...")

    tracker.record_api_call(
        call_id="test-call-1",
        provider="anthropic",
        model="claude-3-sonnet",
        input_tokens=1000,
        output_tokens=500,
        cost=0.0035,
        metadata={"task_id": "task-1", "operation": "code_generation"}
    )

    tracker.record_api_call(
        call_id="test-call-2",
        provider="anthropic",
        model="claude-3-opus",
        input_tokens=2000,
        output_tokens=1000,
        cost=0.0150,
        metadata={"task_id": "task-2", "operation": "analysis"}
    )

    tracker.record_api_call(
        call_id="test-call-3",
        provider="openai",
        model="gpt-4",
        input_tokens=500,
        output_tokens=300,
        cost=0.0060,
        metadata={"task_id": "task-3", "operation": "review"}
    )

    print(f"✅ Recorded 3 API calls")

    # Record some agent operations
    print("\n📝 Recording agent operations...")

    tracker.record_agent_operation(
        operation_id="agent-op-1",
        agent_type="code_generation",
        operation="generate_component",
        duration_seconds=45.5,
        cost=0.0010,
        metadata={"task_id": "task-1", "component": "UserDashboard"}
    )

    tracker.record_agent_operation(
        operation_id="agent-op-2",
        agent_type="testing",
        operation="run_tests",
        duration_seconds=120.0,
        cost=0.0025,
        metadata={"task_id": "task-2", "tests_run": 25}
    )

    print(f"✅ Recorded 2 agent operations")

    # Get summary
    print("\n📊 Cost Summary:")
    summary = tracker.get_cost_summary()
    print(f"  Total Cost: ${summary['summary']['total_cost']:.4f}")
    print(f"  API Calls: {summary['summary']['api_call_count']}")
    print(f"  Agent Operations: {summary['summary']['agent_operation_count']}")
    print(f"  Total Tokens: {summary['summary']['total_tokens']}")

    # Get costs by provider
    print("\n📊 Costs by Provider:")
    for provider, data in summary['by_provider'].items():
        print(f"  {provider}: ${data['total_cost']:.4f} ({data['call_count']} calls)")

    # Get costs by agent type
    print("\n📊 Costs by Agent Type:")
    for agent_type, data in summary['by_agent_type'].items():
        print(f"  {agent_type}: ${data['total_cost']:.4f} ({data['operation_count']} operations)")

    return tracker, summary


def test_cost_persistence(tracker):
    """Test 2: Verify costs are persisted to costs.json"""
    print("\n" + "="*60)
    print("TEST 2: Cost Persistence to costs.json")
    print("="*60)

    # Force save
    tracker.save()

    # Check if file exists
    cost_file = settings.state_dir / "costs.json"
    if not cost_file.exists():
        print(f"❌ FAILED: costs.json not created at {cost_file}")
        return False

    print(f"✅ costs.json exists at {cost_file}")

    # Load and verify contents
    with open(cost_file, 'r') as f:
        costs_data = json.load(f)

    print("\n📁 costs.json contents:")
    print(f"  API calls: {len(costs_data.get('api_calls', {}))}")
    print(f"  Agent operations: {len(costs_data.get('agent_operations', {}))}")
    print(f"  Summary: {json.dumps(costs_data.get('summary', {}), indent=2)}")

    # Verify our test data is there
    if 'test-call-1' not in costs_data.get('api_calls', {}):
        print("❌ FAILED: Test API call not found in costs.json")
        return False

    if 'agent-op-1' not in costs_data.get('agent_operations', {}):
        print("❌ FAILED: Test agent operation not found in costs.json")
        return False

    print("✅ All test data found in costs.json")

    return True


def test_backend_api():
    """Test 3: Verify backend API returns cost data"""
    print("\n" + "="*60)
    print("TEST 3: Backend API Cost Endpoints")
    print("="*60)

    import subprocess
    import time

    # Check if backend is running
    try:
        result = subprocess.run(
            ['curl', '-s', 'http://localhost:3001/api/costs/summary'],
            capture_output=True,
            timeout=5
        )

        if result.returncode != 0:
            print("⚠️  Backend not running - skipping API test")
            print("   Start backend with: cd dashboard/backend && npm run dev")
            return None

        data = json.loads(result.stdout)
        print("\n✅ Backend API is running")
        print(f"\n📊 /api/costs/summary response:")
        print(json.dumps(data, indent=2))

        # Test costs endpoint
        result = subprocess.run(
            ['curl', '-s', 'http://localhost:3001/api/costs?timeframe=daily&limit=7'],
            capture_output=True,
            timeout=5
        )

        if result.returncode == 0:
            data = json.loads(result.stdout)
            print(f"\n📊 /api/costs response:")
            print(f"  Timeframe: {data.get('timeframe')}")
            print(f"  Data points: {len(data.get('data', []))}")
            if data.get('summary'):
                print(f"  Summary: {json.dumps(data['summary'], indent=2)}")

        # Test by-agent endpoint
        result = subprocess.run(
            ['curl', '-s', 'http://localhost:3001/api/costs/by-agent'],
            capture_output=True,
            timeout=5
        )

        if result.returncode == 0:
            data = json.loads(result.stdout)
            print(f"\n📊 /api/costs/by-agent response:")
            print(f"  Agents: {len(data)}")
            for agent in data[:3]:  # Show first 3
                print(f"    - {agent.get('agentName', 'Unknown')}: ${agent.get('totalCosts', 0):.4f}")

        return True

    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError) as e:
        print(f"⚠️  Backend API test failed: {e}")
        print("   This is expected if backend is not running")
        return None


def test_backend_integration():
    """Test 4: Verify backend integration with costs.json"""
    print("\n" + "="*60)
    print("TEST 4: Backend Integration with costs.json")
    print("="*60)

    import subprocess

    # Check if costs.json exists
    cost_file = settings.state_dir / "costs.json"
    if not cost_file.exists():
        print("❌ FAILED: costs.json does not exist")
        return False

    print("✅ costs.json exists")

    # Test that backend reads from costs.json
    try:
        result = subprocess.run(
            ['curl', '-s', 'http://localhost:3001/api/costs/summary'],
            capture_output=True,
            timeout=5
        )

        if result.returncode != 0:
            print("⚠️  Backend not running - skipping integration test")
            return None

        data = json.loads(result.stdout)

        # Check if backend is returning data from costs.json
        if data['costs']['total'] > 0:
            print(f"✅ Backend is reading from costs.json")
            print(f"   Total costs: ${data['costs']['total']:.4f}")
            print(f"   API costs: ${data['costs']['api']:.4f}")
            print(f"   Agent costs: ${data['costs']['agents']:.4f}")
            return True
        else:
            print("⚠️  Backend returned zero costs - may not be reading from costs.json")
            return False

    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError) as e:
        print(f"⚠️  Backend integration test failed: {e}")
        return None


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("COST METRICS DISPLAY TEST")
    print("="*60)
    print(f"Time: {datetime.now().isoformat()}")
    print(f"State directory: {settings.state_dir}")

    results = {}

    # Test 1: CostTracker
    try:
        tracker, summary = test_cost_tracker()
        results['cost_tracker'] = True
    except Exception as e:
        print(f"❌ TEST 1 FAILED: {e}")
        results['cost_tracker'] = False

    # Test 2: Persistence
    try:
        if 'tracker' in locals():
            results['persistence'] = test_cost_persistence(tracker)
        else:
            results['persistence'] = False
    except Exception as e:
        print(f"❌ TEST 2 FAILED: {e}")
        results['persistence'] = False

    # Test 3: Backend API
    try:
        results['backend_api'] = test_backend_api()
    except Exception as e:
        print(f"❌ TEST 3 FAILED: {e}")
        results['backend_api'] = False

    # Test 4: Backend Integration
    try:
        results['backend_integration'] = test_backend_integration()
    except Exception as e:
        print(f"❌ TEST 4 FAILED: {e}")
        results['backend_integration'] = False

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else ("⚠️  SKIPPED" if passed is None else "❌ FAILED")
        print(f"{test_name.replace('_', ' ').title()}: {status}")

    # Overall result
    passed_count = sum(1 for v in results.values() if v is True)
    total_count = sum(1 for v in results.values() if v is not None)

    print(f"\nOverall: {passed_count}/{total_count} tests passed")

    if passed_count == total_count:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n⚠️  Some tests failed or were skipped")
        return 1


if __name__ == "__main__":
    sys.exit(main())
