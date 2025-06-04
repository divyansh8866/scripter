# Scripter

A Flask-based web application that allows users to browse, configure, and run Python scripts through a browser interface. Scripts are automatically introspected to discover their functions and parameters. A modern Bootstrap 5 UI dynamically generates forms (with type validation and default values) for each function. When executed, a dispatcher launches the chosen function as a subprocess, and real-time logs are streamed back to the web interface.

---

## Table of Contents

1. [Features](#features)
2. [Prerequisites](#prerequisites)
3. [Installation](#installation)
4. [Project Structure](#project-structure)
5. [Usage](#usage)
   - [Running the Server](#running-the-server)
   - [Web Interface Overview](#web-interface-overview)
6. [Adding New Scripts](#adding-new-scripts)
7. [Dispatcher Workflow](#dispatcher-workflow)
8. [Client-Side Validation](#client-side-validation)
9. [Example Script](#example-script)
10. [Troubleshooting](#troubleshooting)
11. [Contributing](#contributing)
12. [License](#license)

---

## Features

- **Automatic Function Discovery**
  Scans the `scripts/` directory for Python files, imports them, and extracts all top-level functions and their signatures.

- **Dynamic Form Generation**
  For each function, generates a Bootstrap 5 form with inputs for every parameter. Inputs are auto-typed (`number` for `int`/`float`, `text` for others) and pre-filled with default values if specified in the function signature.

- **Real-Time Log Streaming**
  Executes the selected function via a Python dispatcher subprocess. Standard output (and errors) are streamed line-by-line back to the browser in real time.

- **Client-Side Type Validation**
  Before submission, the UI validates each field’s data type against the function’s annotation (e.g., ensures integer fields only receive integers).

- **Modular Architecture**
  - `app.py` handles routing, template rendering, and launching the dispatcher.
  - `dispatcher.py` imports the target script, constructs an argument parser for the chosen function, and executes it.
  - Jinja templates (`index.html` and `run_script.html`) define a clean, Bootstrap-based interface.

---

## Prerequisites

1. **Python 3.7+** (ensure `python3` is in your PATH)
2. **pip** (for installing dependencies)
3. Virtual environment (recommended)
4. **Git** (optional, for version control)

> **Note**: If you plan to run AWS scripts (e.g., using `boto3`), you must have `boto3` installed and AWS credentials configured (via `~/.aws/credentials`, environment variables, or an IAM role).

---

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/your-username/python-script-server.git
   cd python-script-server
   ```

2. Create and activate a virtual environment:
   ```
   python3 -m venv venv
   source venv/bin/activate   # Mac/Linux
   venv\\Scripts\\activate    # Windows
   ```

3. Install required packages:
   ```
   pip install -r requirements.txt
   ```
> `requirements.txt` should include:
   ```
   Flask>=2.0
   boto3       # only if you use AWS-related scripts
   ```

4. Verify directory structure. After installation, your project root should look like this:
   ```
   python-script-server/
   ├── app.py
   ├── dispatcher.py
   ├── requirements.txt
   ├── README.md
   ├── scripts/
   │   └── (your Python scripts here)
   └── templates/
       ├── index.html
       └── run_script.html
   ```

---

## Project Structure

```
python-script-server/
├── app.py
├── dispatcher.py
├── requirements.txt
├── README.md
├── scripts/
│   └── example_script.py   # Your user scripts go here
└── templates/
    ├── index.html          # Lists available scripts
    └── run_script.html     # Dynamic form for running functions
```

- `app.py`:
  - Routes:
    - `/` → lists all scripts.
    - `/select/<script_name>` → introspects functions in the chosen script and renders `run_script.html`.
    - `/run` → receives form data, constructs a dispatcher command, and streams subprocess output back.

- `dispatcher.py`:
  - Phase 1: parses `--script` and `--function` flags (ignores other flags).
  - Phase 2: inspects the chosen function’s signature, builds a new argument parser that only accepts its parameters (plus `--script` and `--function`).
  - Executes the function via subprocess and logs start/finish messages.

- `templates/index.html`: Simple Bootstrap list of all `.py` files in `scripts/`. Clicking a script navigates to `/select/<script_name>`.

- `templates/run_script.html`:
  - Dropdown to choose a function.
  - Dynamically shows a Bootstrap form for the selected function’s parameters.
  - Each input’s `type` and `step` attributes reflect the Python annotation (`int` → `type=number step="1"`, `float` → `type=number step="any"`, otherwise `type=text`).
  - Client-side JS validates each value matches its annotation before sending a POST to `/run`.
  - Streams log output from the dispatcher into a scrolling code-style box.

- `scripts/`: Directory for user-provided scripts. Each script must be a `.py` file (no `__init__.py` needed).
  - Top-level functions in each script will be discovered automatically.
  - To add a new script: place it in `scripts/`, restart Flask, and it appears in the list.

---

## Usage

### Running the Server

1. Make sure your virtual environment is activated.
2. From the project root, run:
   ```
   python app.py
   ```
3. Open your browser and navigate to:
   ```
   http://localhost:5000/
   ```

### Web Interface Overview

1. **Script List**
   The home page displays all Python files under `scripts/`. Click on any script to see its functions.

2. **Function & Parameter Selection**
   On the “Run” page for a given script:
   - Select a function from the dropdown.
   - The form below updates to show each parameter:
     - If a parameter is annotated `int` → HTML `<input type="number" step="1">`.
     - If annotated `float` → `<input type="number" step="any">`.
     - Otherwise (including `str` or no annotation) → `<input type="text">`.
   - If the Python function provides a default, the field is pre-filled. If no default, it is blank and `required`.

3. **Real-Time Logs**
   - After filling parameters, click **Execute**.
   - The dispatcher subprocess is spawned with the appropriate flags.
   - All `stdout` and `stderr` lines from that subprocess stream back into the “Live Logs” panel.

4. **Client-Side Validation**
   - Before submission, JavaScript checks each field’s `data-type` (derived from the annotation).
   - If a user enters “abc” into an `int` field, an alert pops up, preventing submission.

---

## Adding New Scripts

1. Create a new Python file under `scripts/`, e.g. `scripts/my_script.py`.
2. Define top-level functions—each one must have distinct names and, optionally, type annotations and defaults. Example:
````python
# scripts/my_script.py

def say_hello(name: str, repeat: int = 1):
    """
    Prints “Hello <name>” <repeat> times and returns a summary string.
    """
    for i in range(repeat):
        print(f"[{i+1}/{repeat}] Hello, {name}!")
    return f"Greeted {name} {repeat} times."

def add_numbers(a: int, b: int):
    """
    Returns the sum of two integers.
    """
    result = a + b
    print(f"{a} + {b} = {result}")
    return result
````

3. Restart the Flask server (`Ctrl+C`, then `python app.py`).
4. Navigate to `/` and click `my_script.py`. You’ll see both `say_hello` and `add_numbers` in the dropdown.
5. Select one, fill out parameters, and click **Execute**.

---

## Dispatcher Workflow

1. **Client → `/run`**
   The form POSTs `script` (filename without `.py`), `function`, and all user-entered parameter values.

2. **`app.py` constructs a command**
   ```
   python dispatcher.py --script <script_name> --function <function_name> --param1 value1 --param2 value2 ...
   ```

3. **Subprocess Execution**
   - The dispatcher (`dispatcher.py`) does:
     1. Phase 1: parse `--script` and `--function` (ignores any other flags).
     2. Imports the specified module from `scripts/`.
     3. Uses `inspect.signature(...)` to get that function’s parameters.
     4. Builds a new `argparse.ArgumentParser` that defines only that function’s flags.
     5. Parses the full CLI to enforce exactly those flags and convert them to the correct types.
     6. Calls the function (`func(**kwargs)`).
     7. Logs start/finish and any return value or exception.

4. **Real-Time Streaming**
   - `dispatcher.py` writes messages to stdout.
   - `app.py`’s `/run` view reads `subprocess.stdout.readline()` in a loop and yields each line back to the browser.
   - The browser’s JavaScript appends each line to the “Live Logs” `<div>` in real time.

---

## Client-Side Validation

- Each `<input>` includes a `data-type` attribute (e.g. `data-type="int"` or `data-type="float"` or `data-type="string"`).
- On form “submit,” JavaScript iterates over all inputs in the active panel:
  1. Reads `input.getAttribute("data-type")`.
  2. If `int` → checks `value` is non-empty, is numeric, and is an integer.
  3. If `float` → checks `value` is non-empty and is numeric.
  4. Otherwise (`string` or other) → ensures non-empty.
- If any check fails, an alert pops up (e.g. “Invalid value for ‘age’: expected int.”), focus shifts to that field, and the form is not submitted.

---

## Example Script

Below is a simple example you can place in `scripts/hello_world.py` to confirm everything’s working:
```python
def hello_world():
    """
    A zero-parameter function that prints a greeting.
    """
    print("Hello, world!")
    return "Done"
```

- After restarting Flask, browse to `/`, click **hello_world.py**, select **hello_world()**, and click **Execute**. You should see “Hello, world!” appear in the logs.

---

## Troubleshooting

1. **No functions appear in the dropdown**
   - Ensure your script is in `scripts/` with a `.py` extension and has no import errors.
   - If you imported a library (e.g. `boto3`) that isn’t installed, the script won’t import cleanly and `get_functions()` returns `{}`.
   - Check Flask console for import exceptions.

2. **Form fields still treat everything as string**
   - Make sure your function’s parameter annotations are exactly `int` or `float`. If you use custom types or missing annotations, the UI falls back to `type="text"`.
   - Confirm that `app.py`’s `build_funcs_meta()` is correctly categorizing annotations.

3. **Dispatcher errors**
   - If dispatcher logs show an `ImportError` or missing module, verify your virtual environment is activated and all dependencies (Flask, boto3, etc.) are installed.
   - Run `python dispatcher.py --script=my_script --function=my_function --param1 val` directly in a terminal to debug.

4. **AWS/Boto3 errors**
   - Ensure AWS credentials are configured (`~/.aws/credentials` or environment variables).
   - Grant the IAM user/role the appropriate S3 or EC2 permissions.
   - If you see `botocore.exceptions.NoCredentialsError`, set environment variables:
     ```
     export AWS_ACCESS_KEY_ID="YOUR_KEY"
     export AWS_SECRET_ACCESS_KEY="YOUR_SECRET"
     export AWS_DEFAULT_REGION="us-east-1"
     ```

---

## Contributing

1. Fork the repository and create your feature branch (`git checkout -b feature/my-feature`).
2. Make your changes (e.g. fix bugs, add new functionality).
3. Write tests if applicable (this repo does not yet include a test suite, but contributions to add one are welcome).
4. Ensure code quality—PEP 8 compliance, clear variable names, and thorough docstrings.
5. Commit and push your changes (`git commit -m "Add new feature"`) to your fork.
6. Open a Pull Request against the main repository. Provide a clear description of your changes.

---

## License

This project is released under the [MIT License](LICENSE).

---

Thank you for using **Scripter**! If you have any questions or run into issues, please open an issue or submit a pull request.
