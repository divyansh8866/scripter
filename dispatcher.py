#!/usr/bin/env python3
import argparse
import importlib
import inspect
import logging
import os
import sys

# -----------------------------------------------------------------------------
# 1) Configure logging so Flask can stream it
# -----------------------------------------------------------------------------
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# 2) Base scripts directory
# -----------------------------------------------------------------------------
BASE_DIR = os.path.dirname(__file__)
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")


def list_functions(module_name: str, module_folder: str):
    """
    Import the module (module_name) from module_folder,
    inspect top-level functions, and return a dict {func_name: signature}.
    """
    sys.path.insert(0, module_folder)
    try:
        module = importlib.import_module(module_name)
    except Exception as e:
        logger.error("Failed to import module '%s' from '%s': %s", module_name, module_folder, e)
        sys.exit(1)
    finally:
        sys.path.pop(0)

    funcs = {}
    for attr_name, attr_val in vars(module).items():
        if inspect.isfunction(attr_val) and attr_val.__module__ == module_name:
            funcs[attr_name] = inspect.signature(attr_val)
    return funcs


def main():
    # -----------------------------------------------------------------------------
    # 3) Parse --script and --function
    # -----------------------------------------------------------------------------
    parser = argparse.ArgumentParser(
        description="Generic dispatcher: import a script from scripts/ and run one of its functions."
    )
    parser.add_argument(
        "--script",
        required=True,
        help=(
            "Path to the script module relative to 'scripts/' (omit '.py'). "
            "Examples: 'Other/sample_scr' or 'sample_script'."
        )
    )
    parser.add_argument("--function", required=True, help="Function to call in that script.")
    args, remaining = parser.parse_known_args()
    script_arg = args.script  # e.g. "Other/sample_scr" or "sample_script"
    func_name = args.function

    # -----------------------------------------------------------------------------
    # 4) Split script_arg into folder (optional) and module_name
    # -----------------------------------------------------------------------------
    # Split script_arg on “/” to allow nested folders:
    parts = script_arg.split("/")
    module_name = parts[-1]  # last segment is the .py filename (without “.py”)
    if len(parts) > 1:
        # Any preceding segments form the folder path under scripts/
        folder_part = os.path.join(*parts[:-1])
        module_folder = os.path.join(SCRIPTS_DIR, folder_part)
    else:
        folder_part = ""
        module_folder = SCRIPTS_DIR  # no subfolder, use scripts/ directly

    # -----------------------------------------------------------------------------
    # 5) Verify module_folder exists and module_name.py exists inside it
    # -----------------------------------------------------------------------------
    if not os.path.isdir(module_folder):
        logger.error("Folder '%s' not found under '%s'", folder_part, SCRIPTS_DIR)
        sys.exit(1)

    script_filename = module_name + ".py"
    script_path = os.path.join(module_folder, script_filename)
    if not os.path.isfile(script_path):
        logger.error(
            "Script '%s' not found under '%s'",
            script_filename,
            module_folder
        )
        sys.exit(1)

    # -----------------------------------------------------------------------------
    # 6) List functions in the module to verify func_name
    # -----------------------------------------------------------------------------
    func_map = list_functions(module_name, module_folder)
    if func_name not in func_map:
        logger.error(
            "Function '%s' not found in script '%s'. Available: %s",
            func_name, script_filename, ", ".join(func_map.keys())
        )
        sys.exit(1)

    # -----------------------------------------------------------------------------
    # 7) Build ArgumentParser based on the chosen function’s signature
    # -----------------------------------------------------------------------------
    sig = func_map[func_name]
    dispatcher_parser = argparse.ArgumentParser(
        description=f"Run {script_arg}.{func_name}{sig}"
    )
    # Re-add --script and --function (we ignore them when calling func)
    dispatcher_parser.add_argument("--script", help="(ignored)", required=True)
    dispatcher_parser.add_argument("--function", help="(ignored)", required=True)

    for param_name, param in sig.parameters.items():
        annotation = param.annotation if param.annotation in (int, float, str) else str
        if param.default is param.empty:
            dispatcher_parser.add_argument(f"--{param_name}", type=annotation, required=True)
        else:
            dispatcher_parser.add_argument(
                f"--{param_name}", type=annotation, default=param.default
            )

    # -----------------------------------------------------------------------------
    # 8) Parse only the flags relevant to this function; ignore unknowns
    # -----------------------------------------------------------------------------
    parsed, extras = dispatcher_parser.parse_known_args()
    kwargs = {k: v for k, v in vars(parsed).items() if k not in ("script", "function")}

    # -----------------------------------------------------------------------------
    # 9) Warn about any extra flags
    # -----------------------------------------------------------------------------
    if extras:
        logger.warning("Ignoring unrecognized flags: %s", extras)

    # -----------------------------------------------------------------------------
    # 10) Import the module and get the function object
    # -----------------------------------------------------------------------------
    sys.path.insert(0, module_folder)
    try:
        module = importlib.import_module(module_name)
    except Exception as e:
        logger.error("Failed to import module '%s' from '%s': %s", module_name, module_folder, e)
        sys.exit(1)
    finally:
        sys.path.pop(0)

    func = getattr(module, func_name)

    # -----------------------------------------------------------------------------
    # 11) Invoke the function and stream logs
    # -----------------------------------------------------------------------------
    try:
        logger.info("=== Starting: %s.%s with args: %s", script_arg, func_name, kwargs)
        result = func(**kwargs)
        if result is not None:
            logger.info("Return value: %s", result)
    except Exception as e:
        logger.exception("Unhandled exception in %s.%s: %s", script_arg, func_name, e)
        sys.exit(1)
    else:
        logger.info("=== Completed: %s.%s without errors", script_arg, func_name)


if __name__ == "__main__":
    main()