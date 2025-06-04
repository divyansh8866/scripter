import argparse
import time
import inspect

def greet(name: str = "test", repeat: int = 1):
    """
    Prints “Hello, <name>!” <repeat> times, with a small pause between each.
    """
    for i in range(repeat):
        print(f"[{i+1}/{repeat}] Hello, {name}!")
        time.sleep(0.5)

def add(a: int, b: int):
    """
    Adds two integers, prints result.
    """
    res = a + b
    print(f"{a} + {b} = {res}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run one of the functions in this script.")
    parser.add_argument("function", help="Function name to run (e.g., greet or add).")

    # Dynamically add flags based on the function name
    args, unknown = parser.parse_known_args()
    func_name = args.function

    # Map of available functions
    func_map = {
        "greet": greet,
        "add": add
    }

    if func_name not in func_map:
        print(f"Error: function '{func_name}' not found.")
        exit(1)

    # Re‑parse with the right signature
    func = func_map[func_name]
    sig = inspect.signature(func)
    parser = argparse.ArgumentParser()
    parser.add_argument("function", help="Ignore")
    for param_name, param in sig.parameters.items():
        # Only support simple types: int, str, float. You could expand this.
        arg_type = param.annotation if param.annotation in (int, float, str) else str
        if param.default is param.empty:
            parser.add_argument(f"--{param_name}", type=arg_type, required=True)
        else:
            parser.add_argument(f"--{param_name}", type=arg_type, default=param.default)
    parsed = parser.parse_args()
    kwargs = {k: v for k, v in vars(parsed).items() if k != "function"}

    func(**kwargs)