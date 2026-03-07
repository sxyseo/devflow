#!/usr/bin/env python
"""Test script to verify plugin manager integration into orchestrator."""

import sys
import os

# Add the project to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from devflow.core.orchestrator import Orchestrator

    # Create orchestrator instance
    o = Orchestrator()

    # Check if plugin manager exists
    has_plugins = hasattr(o, 'plugins')

    print(f"Has plugin manager: {has_plugins}")

    if has_plugins:
        # Check if it's a PluginManager instance
        from devflow.plugins.plugin_manager import PluginManager
        is_correct_type = isinstance(o.plugins, PluginManager)
        print(f"Plugin manager is correct type: {is_correct_type}")

        # Check plugin manager methods
        has_load_all = hasattr(o.plugins, 'load_all_plugins')
        has_start_all = hasattr(o.plugins, 'start_all_plugins')
        has_stop_all = hasattr(o.plugins, 'stop_all_plugins')
        has_get_metrics = hasattr(o.plugins, 'get_metrics')

        print(f"Has load_all_plugins: {has_load_all}")
        print(f"Has start_all_plugins: {has_start_all}")
        print(f"Has stop_all_plugins: {has_stop_all}")
        print(f"Has get_metrics: {has_get_metrics}")

        all_checks_passed = (
            has_plugins and
            is_correct_type and
            has_load_all and
            has_start_all and
            has_stop_all and
            has_get_metrics
        )

        if all_checks_passed:
            print("\n✓ All checks passed!")
            sys.exit(0)
        else:
            print("\n✗ Some checks failed")
            sys.exit(1)
    else:
        print("\n✗ Plugin manager not found")
        sys.exit(1)

except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
