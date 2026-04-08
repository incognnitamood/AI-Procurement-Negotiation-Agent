import inspect
import openenv.env

# Get all classes
classes = [name for name, obj in inspect.getmembers(openenv.env) if inspect.isclass(obj)]
print("Classes in openenv.env:")
for cls in classes:
    obj = getattr(openenv.env, cls)
    print(f"  {cls}: {obj}")
    # Check for subclasses
    try:
        bases = inspect.getmro(obj)[1:-1]  # Skip self and object
        if bases:
            print(f"    Base classes: {[b.__name__ for b in bases]}")
    except:
        pass

# Check for base classes named Action, Observation, State
print("\nLooking for Action, Observation, or State classes...")
all_items = dir(openenv.env)
for item in all_items:
    if item.lower() in ['action', 'observation', 'state']:
        obj = getattr(openenv.env, item)
        print(f"  Found: {item} = {obj}")

# Look in openenv.env.env (the nested module)
print("\nChecking openenv.env.env...")
try:
    import openenv.env.env
    nested_env = openenv.env.env
    nested_classes = [name for name, obj in inspect.getmembers(nested_env) if inspect.isclass(obj)]
    print(f"Found {len(nested_classes)} classes:")
    for cls in nested_classes:
        print(f"  - {cls}")
except Exception as e:
    print(f"  Error: {e}")
