#!/usr/bin/env python3
"""
dispatcher.py

A generic dispatcher that imports and executes exactly one function from any
Python file under `scripts/`. It uses named flags (`--script` and `--function`)
plus only the flags required by that function’s signature—never requiring
parameters for other functions in the same script.

Usage examples:
  python dispatcher.py --script=test --function=greet --name Alice --repeat 2
  python dispatcher.py --script=test --function=add   --a 5     --b 7

Logging:
  - INFO: logs function start, returned value (if any), and successful completion.
  - ERROR: logs any unhandled exception with full traceback.
"""

import argparse
import importlib
import inspect
import logging
import os
import sys
from typing import Dict

# ------------------------------------------------------------------------------
# CONFIGURE LOGGING (INFO and ERROR only)
# ------------------------------------------------------------------------------
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------
# CONSTANTS
# ------------------------------------------------------------------------------
# Directory containing user‑provided scripts
SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "scripts")


# ------------------------------------------------------------------------------
# HELPER FUNCTIONS
# ------------------------------------------------------------------------------
def discover_functions(module_name: str) -> Dict[str, inspect.Signature]:
    """
    Import `module_name` from SCRIPTS_DIR and return a mapping of
    top‑level function names to their inspect.Signature objects.
    """
    sys.path.insert(0, SCRIPTS_DIR)
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:
        logger.error("Failed to import module '%s': %s", module_name, exc)
        sys.exit(1)
    finally:
        sys.path.pop(0)

    functions = {}
    for attr_name, attr_val in vars(module).items():
        if inspect.isfunction(attr_val) and attr_val.__module__ == module_name:
            functions[attr_name] = inspect.signature(attr_val)
    return functions


def import_module(module_name: str):
    """
    Import and return the specified module from SCRIPTS_DIR.
    """
    sys.path.insert(0, SCRIPTS_DIR)
    try:
        return importlib.import_module(module_name)
    except Exception as exc:
        logger.error("Failed to import module '%s': %s", module_name, exc)
        sys.exit(1)
    finally:
        sys.path.pop(0)


# ------------------------------------------------------------------------------
# MAIN DISPATCHER
# ------------------------------------------------------------------------------
def main():
    """
    1) Phase 1: Parse only --script and --function (ignore other flags initially).
    2) Discover that function’s signature.
    3) Phase 2: Build a new ArgumentParser that only defines flags for the chosen function.
    4) Re‑parse the full CLI via parse_args() to enforce exactly those flags.
    5) Invoke the function.
    """
    # Phase 1: Base parser to extract script + function
    base_parser = argparse.ArgumentParser(add_help=False)
    base_parser.add_argument(
        "--script",
        required=True,
        help="Name of the Python file under scripts/ (without .py)."
    )
    base_parser.add_argument(
        "--function",
        required=True,
        help="Name of the function to call inside the script."
    )
    # parse_known_args() returns (args, unknown) so we ignore other flags here
    args, _ = base_parser.parse_known_args()
    script_name = args.script
    func_name = args.function

    # Verify that scripts/<script_name>.py exists
    script_path = os.path.join(SCRIPTS_DIR, f"{script_name}.py")
    if not os.path.isfile(script_path):
        logger.error("Script '%s.py' not found in '%s'.", script_name, SCRIPTS_DIR)
        sys.exit(1)

    # Discover all top‑level functions in that script
    func_map = discover_functions(script_name)
    if func_name not in func_map:
        logger.error(
            "Function '%s' not found in '%s.py'. Available: %s",
            func_name, script_name, ", ".join(func_map.keys())
        )
        sys.exit(1)
    signature = func_map[func_name]

    # Phase 2: Build a parser that only accepts flags for the chosen function
    func_parser = argparse.ArgumentParser(
        description=f"Run {script_name}.{func_name}{signature}"
    )
    # Re‑add --script and --function so parse_args() won’t treat them as unknown
    func_parser.add_argument("--script", required=True)
    func_parser.add_argument("--function", required=True)

    # Add flags for only that function’s parameters
    for param_name, param in signature.parameters.items():
        flag = f"--{param_name}"
        annotation = param.annotation if param.annotation in (int, float, str) else str
        if param.default is param.empty:
            # required argument
            func_parser.add_argument(
                flag,
                type=annotation,
                required=True,
                help=f"{param_name} (type={annotation.__name__})"
            )
        else:
            # optional argument with default
            func_parser.add_argument(
                flag,
                type=annotation,
                default=param.default,
                help=(
                    f"{param_name} (type={annotation.__name__}, "
                    f"default={param.default!r})"
                )
            )

    # Phase 3: parse the full CLI exactly; any missing or extra flags will cause an error
    parsed = func_parser.parse_args()

    # Build kwargs by dropping 'script' and 'function'
    kwargs = {
        k: v for k, v in vars(parsed).items()
        if k not in ("script", "function")
    }

    # Import the module and retrieve the function reference
    module = import_module(script_name)
    target_func = getattr(module, func_name)

    # Invoke the function with structured logging
    try:
        logger.info("=== Starting: %s.%s with args: %s", script_name, func_name, kwargs)
        result = target_func(**kwargs)
        if result is not None:
            logger.info("Return value: %s", result)
    except Exception as exc:
        logger.exception("Unhandled exception in %s.%s: %s", script_name, func_name, exc)
        sys.exit(1)
    else:
        logger.info("=== Completed: %s.%s without errors", script_name, func_name)


if __name__ == "__main__":
    main()