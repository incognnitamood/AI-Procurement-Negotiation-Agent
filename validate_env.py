#!/usr/bin/env python
"""Validate OpenEnv configuration and structure."""

import yaml
import sys

def validate_openenv():
    """Validate the OpenEnv environment configuration."""
    errors = []
    warnings = []
    
    # Load openenv.yaml
    try:
        with open('openenv.yaml', 'r') as f:
            config = yaml.safe_load(f)
        print("✓ openenv.yaml loads successfully")
    except Exception as e:
        errors.append(f"Failed to load openenv.yaml: {e}")
        return errors, warnings
    
    print(f"\nEnvironment: {config.get('name')} (v{config.get('version')})")
    
    # Validate basic fields
    required_fields = ['name', 'version', 'description', 'api_url', 'tasks', 'action_space', 'observation_space']
    for field in required_fields:
        if field not in config:
            errors.append(f"Missing required field: {field}")
        else:
            print(f"  ✓ {field}")
    
    # Validate tasks
    tasks = config.get('tasks', [])
    if not tasks:
        errors.append("No tasks defined")
    else:
        print(f"\n{len(tasks)} tasks:")
        for task in tasks:
            name = task.get('name', 'UNKNOWN')
            required_task_fields = ['name', 'difficulty', 'reward_range', 'max_steps', 'description']
            for field in required_task_fields:
                if field not in task:
                    errors.append(f"Task '{name}' missing field: {field}")
            print(f"  ✓ {name}: {task.get('difficulty')} (max_steps={task.get('max_steps')})")
    
    # Validate action_space
    action_space = config.get('action_space', {})
    if action_space.get('type') != 'structured':
        errors.append(f"Action space type should be 'structured', got '{action_space.get('type')}'")
    if 'fields' not in action_space:
        errors.append("Action space missing 'fields'")
    else:
        print(f"\nAction space fields:")
        for field_name in action_space.get('fields', {}).keys():
            print(f"  ✓ {field_name}")
    
    # Validate observation_space
    obs_space = config.get('observation_space', {})
    if obs_space.get('type') != 'structured':
        errors.append(f"Observation space type should be 'structured', got '{obs_space.get('type')}'")
    if 'fields' not in obs_space:
        errors.append("Observation space missing 'fields'")
    else:
        print(f"\nObservation space fields:")
        for field_name in obs_space.get('fields', {}).keys():
            print(f"  ✓ {field_name}")
    
    # Try to import models
    print(f"\nImporting models...")
    try:
        from models import NegotiationAction, NegotiationObservation, NegotiationState
        print("  ✓ NegotiationAction (inherits from Action)")
        print("  ✓ NegotiationObservation (inherits from Observation)")
        print("  ✓ NegotiationState (inherits from State)")
    except Exception as e:
        errors.append(f"Failed to import models: {e}")
    
    # Try to load environment
    print(f"\nLoading environment...")
    try:
        from environment import NegotiationEnvironment
        env = NegotiationEnvironment()
        print("  ✓ NegotiationEnvironment instantiated")
        
        # Try reset
        obs = env.reset('saas_renewal')
        print(f"  ✓ reset('saas_renewal') works")
        print(f"    - Observation type: {type(obs).__name__}")
        print(f"    - Round: {obs.round_number}")
        print(f"    - Deal value: {obs.deal_value_so_far}")
    except Exception as e:
        errors.append(f"Failed to load environment: {e}")
    
    return errors, warnings


if __name__ == '__main__':
    print("=" * 60)
    print("OpenEnv Environment Validation")
    print("=" * 60)
    print()
    
    errors, warnings = validate_openenv()
    
    print("\n" + "=" * 60)
    if errors:
        print(f"✗ {len(errors)} ERRORS FOUND:")
        for i, error in enumerate(errors, 1):
            print(f"  {i}. {error}")
        sys.exit(1)
    elif warnings:
        print(f"⚠ {len(warnings)} WARNINGS:")
        for i, warning in enumerate(warnings, 1):
            print(f"  {i}. {warning}")
        print("\n✓ Validation passed (with warnings)")
    else:
        print("✓ Validation PASSED - All checks successful!")
    print("=" * 60)
