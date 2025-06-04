import os
import sys
import inspect
import subprocess
import datetime

from flask import Flask, render_template, request, Response, url_for, redirect

app = Flask(__name__, static_folder="static", template_folder="templates")
SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "scripts")


def build_script_tree(base_path):
    """
    Recursively walk base_path and return a nested dict structure:
      {
        "files": [list of .py filenames in this directory],
        "subdirs": {
           subfolder_name: { ... same structure ... },
           ...
        }
      }
    """
    tree = {"files": [], "subdirs": {}}
    for entry in sorted(os.listdir(base_path)):
        full = os.path.join(base_path, entry)
        if os.path.isdir(full) and not entry.startswith("__"):
            # Recurse into subfolder
            tree["subdirs"][entry] = build_script_tree(full)
        elif os.path.isfile(full) and entry.endswith(".py") and not entry.startswith("__"):
            tree["files"].append(entry)
    return tree


@app.context_processor
def inject_current_year():
    return {"current_year": datetime.datetime.now().year}


@app.route("/", methods=["GET"])
def index():
    """
    Build a nested folder→scripts tree and pass into the template.
    """
    tree = build_script_tree(SCRIPTS_DIR)
    return render_template("index.html", script_tree=tree, parent_path="") 


# (Other routes like /select/<...> and /run remain unchanged)


def list_functions(module_name: str, module_folder: str):
    sys.path.insert(0, module_folder)
    try:
        module = __import__(module_name)
    except Exception:
        return {}
    finally:
        sys.path.pop(0)

    funcs = {}
    for attr_name, attr_val in vars(module).items():
        if inspect.isfunction(attr_val) and attr_val.__module__ == module_name:
            funcs[attr_name] = inspect.signature(attr_val)
    return funcs


@app.route("/select/<path:folder_and_script>", methods=["GET"])
def select_script(folder_and_script):
    """
    folder_and_script will be something like "Category/Subcategory/sample_script.py"
    We split on the last slash to find folder vs. filename.
    """
    # Split into folder path and script filename
    folder_part, script_filename = os.path.split(folder_and_script)
    if folder_part == "":
        module_folder = SCRIPTS_DIR
    else:
        module_folder = os.path.join(SCRIPTS_DIR, folder_part)

    # Verify file exists
    script_path = os.path.join(module_folder, script_filename)
    if not os.path.isfile(script_path):
        return redirect(url_for("index"))

    module_name, _ = os.path.splitext(script_filename)
    sys.path.insert(0, module_folder)
    try:
        funcs_signatures = list_functions(module_name, module_folder)
    finally:
        sys.path.pop(0)

    # Build metadata for each function (same as before)
    def build_funcs_meta(functions_signatures):
        meta = {}
        _empty = inspect._empty
        for fname, sig in functions_signatures.items():
            params = []
            for param_name, param_obj in sig.parameters.items():
                ann = param_obj.annotation
                default_val = None if param_obj.default is _empty else param_obj.default

                if ann == int:
                    input_type = "number"
                    step = "1"
                    dtype = "int"
                    type_name = "int"
                elif ann == float:
                    input_type = "number"
                    step = "any"
                    dtype = "float"
                    type_name = "float"
                else:
                    input_type = "text"
                    step = None
                    if ann != _empty and isinstance(ann, type):
                        dtype = ann.__name__
                        type_name = ann.__name__
                    else:
                        dtype = "string"
                        type_name = "string"

                params.append({
                    "name": param_name,
                    "annotation": ann,
                    "default": default_val,
                    "input_type": input_type,
                    "step": step,
                    "dtype": dtype,
                    "type_name": type_name,
                })
            meta[fname] = params
        return meta

    funcs_meta = build_funcs_meta(funcs_signatures)

    return render_template(
        "run_script.html",
        script_name=folder_and_script,
        functions_signatures=funcs_signatures,
        functions_meta=funcs_meta
    )


def stream_subprocess(cmd, workdir):
    proc = subprocess.Popen(
        cmd,
        cwd=workdir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1,
        universal_newlines=True,
    )
    for line in proc.stdout:
        yield line
    proc.stdout.close()
    return_code = proc.wait()
    if return_code != 0:
        yield f"\n[Process exited with code {return_code}]\n"


@app.route("/run", methods=["POST"])
def run_script():
    """
    Receive:
      - 'script': e.g. "Category/Subcategory/sample_script.py"
      - 'function': function name
      - plus all parameter fields
    Build a dispatcher command: python dispatcher.py --script Category/Subcategory/sample_script --function ...
    """
    full_script = request.form.get("script")  # includes ".py"
    function = request.form.get("function")

    folder_part, script_filename = os.path.split(full_script)
    module_name, _ = os.path.splitext(script_filename)

    if folder_part == "":
        workdir = SCRIPTS_DIR
        script_module_arg = module_name
    else:
        workdir = os.path.join(SCRIPTS_DIR, folder_part)
        script_module_arg = f"{folder_part}/{module_name}"

    # Collect parameters
    params = {
        key: val
        for key, val in request.form.items()
        if key not in ("script", "function")
    }

    dispatcher_path = os.path.join(os.path.dirname(__file__), "dispatcher.py")
    full_cmd = [
        sys.executable,
        dispatcher_path,
        "--script",
        script_module_arg,
        "--function",
        function,
    ]
    for k, v in params.items():
        full_cmd.extend([f"--{k}", str(v)])

    def generate():
        yield f"Running: {' '.join(full_cmd)}\n\n"
        for out in stream_subprocess(full_cmd, workdir):
            yield out

    return Response(generate(), mimetype="text/plain")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)