import os
import sys
import inspect
import subprocess
from flask import Flask, render_template, request, Response, url_for, redirect

app = Flask(__name__)
SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "scripts")


def list_scripts():
    """
    Return a sorted list of all .py files under scripts/ (excluding __init__.py).
    """
    return sorted(
        fname
        for fname in os.listdir(SCRIPTS_DIR)
        if fname.endswith(".py") and not fname.startswith("__")
    )


def get_functions(script_name):
    """
    Import the given script (by filename) and return a dict mapping each
    top-level function name to its inspect.Signature (which includes annotations).
    """
    module_name = script_name[:-3]
    sys.path.insert(0, SCRIPTS_DIR)
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


def build_funcs_meta(functions_signatures):
    """
    Given a dict {func_name: Signature}, return a dict:
      {
        func_name: [
          {
            "name": param_name,
            "annotation": annotation,
            "default": default or None,
            "input_type": "number"/"text",
            "step": "1"/"any"/None,
            "dtype": "int"/"float"/"string"/<other>,
            "type_name": annotation.__name__ or "string"
          },
          ...
        ],
        ...
      }
    """
    meta = {}
    _empty = inspect._empty
    for func_name, sig in functions_signatures.items():
        params = []
        for param_name, param_obj in sig.parameters.items():
            ann = param_obj.annotation
            default_val = None if param_obj.default is _empty else param_obj.default

            # Decide input_type/step/dtype/type_name based on annotation
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
                # anything else (including str or no annotation) → text
                input_type = "text"
                step = None
                # If annotation is a type, use its __name__; otherwise "string"
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
        meta[func_name] = params
    return meta


@app.route("/", methods=["GET"])
def index():
    """
    List all available scripts. User picks one to see its functions.
    """
    scripts = list_scripts()
    return render_template("index.html", scripts=scripts)


@app.route("/select/<script_name>", methods=["GET"])
def select_script(script_name):
    """
    After the user selects a script, introspect its functions and show a second page.
    If script_name is invalid, redirect back to index.
    """
    scripts = list_scripts()
    if script_name not in scripts:
        return redirect(url_for("index"))

    funcs_signatures = get_functions(script_name)
    funcs_meta = build_funcs_meta(funcs_signatures)

    return render_template(
        "run_script.html",
        script_name=script_name,
        functions_signatures=funcs_signatures,
        functions_meta=funcs_meta
    )


def stream_subprocess(cmd, workdir):
    """
    Run the given command as a subprocess, yield stdout/stderr lines as they appear.
    """
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
    Receive form fields:
      - script    (script name without .py)
      - function  (name of the function)
      - other fields matching that function’s parameters

    Builds and runs:
      python dispatcher.py --script <script> --function <function> --<param> <value> …

    Streams stdout+stderr back to the client.
    """
    script = request.form.get("script")
    function = request.form.get("function")

    # Collect only other form fields as function parameters
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
        script,
        "--function",
        function,
    ]
    for param, value in params.items():
        full_cmd.append(f"--{param}")
        full_cmd.append(str(value))

    workdir = SCRIPTS_DIR  # run from within scripts/ so imports resolve correctly

    def generate():
        yield f"Running: {' '.join(full_cmd)}\n\n"
        for output_line in stream_subprocess(full_cmd, workdir):
            yield output_line

    return Response(generate(), mimetype="text/plain")


if __name__ == "__main__":
    # Listen on 0.0.0.0 so Docker (or local) can forward ports
    app.run(host="0.0.0.0", port=5000, debug=False)