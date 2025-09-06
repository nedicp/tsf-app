# **Electricity consumption forecasting application**

# 1. Environment Setup (Poetry)

This project uses [**Poetry**](https://python-poetry.org/) for dependency management, virtual environments, and packaging. Follow the steps below to get your development environment up and running.

## 1.1 Install Poetry

> Linux & macOS

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

Then add Poetry to your shell config:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc   # or ~/.zshrc
source ~/.bashrc                                           # or source ~/.zshrc
```

> Windows (PowerShell)

```powershell
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -
```

Make sure Poetry is in your system PATH:
  1. Poetry is typically installed in the following directory:
      ```
      C:\Users\<YourUsername>\AppData\Roaming\pypoetry\venv\Scripts
      ```
      or
      ```
      C:\Users\<YourUsername>\.poetry\bin
      ```
      Replace `<YourUsername>` with your actual Windows username.
  2. Edit the PATH Variable
  3. Restart Your Terminal.
  4. Verify Installation:
     Run the following command to check if Poetry is correctly installed:
     ```powershell
     poetry --version
     ```

## 1.2 Clone the Repository

```bash
git clone https://github.com/nedicp/tsf-app.git
cd tsf-app
```

## 1.3 Configure Poetry

It is recommended that Poetry uses a local `.venv` Folder.

```bash
poetry config virtualenvs.in-project true
```

This will create the virtual environment inside your project (e.g., `./.venv/`), making it easier to use with editors and Docker.

## 1.4 Install Dependencies

```bash
poetry install
```

This command will:
- Create a virtual environment (if not already present)
- Install all dependencies listed in `pyproject.toml` and `poetry.lock`

## 1.5 Activate the Virtual Environment

> On **Linux**, use:
1. Make the command executable:
   ```bash
   chmod +x activate.sh
   ```
2. Then simpy run:
    ```bash
    source activate.sh
    ```

> On **Windows (cmd.exe or PowerShell)**, use:
```powershell
.\activate.ps1
```

## 1.6 Run a file

```bash
poetry run python file_to_run.py
```

## 1.7 Install new libraries

If you want to install new libraries open your terminal in the root directory of project (where the pyproject.toml file is located) and run the following command:

```bash
poetry add <new-library>
```

This command will:

- Find the latest compatible version of `new-library`.
- Add `new-library` to the [project.dependencies] section in your pyproject.toml file.
- Install the package and its dependencies into your project's virtual environment.
- Update the poetry.lock file to lock the specific versions installed.
- After running the command, you should see `new-library` listed under the dependencies in your pyproject.toml.


# 2. Pre-Commit Hooks

This project uses [**pre-commit**](https://pre-commit.com) to ensure code quality, formatting, type checking, and config validity before any code is committed.

## 2.1 What it Does

Pre-commit runs a set of configured "hooks" (small checks or scripts) every time you run `git commit`. If any hook modifies a file or fails, the commit is aborted, allowing you to review the changes or fix the errors before trying to commit again.

The hooks configured for this project likely include:
- **Formatting:** Tools like `black` and `isort` to ensure consistent code style.
- **Linting:** Tools like `ruff` or `flake8` to catch potential errors and style violations.
- **Type Checking:** `mypy` to verify static type hints.
- **Security Checks:** Tools to prevent committing secrets or known vulnerabilities.
- *(Add/remove based on your actual `.pre-commit-config.yaml`)*

## 2.2 Setup

First, ensure you have installed the development dependencies:

```bash
poetry install --with dev  # Or just `poetry install` if pre-commit is a main dependency
```

Then, install the git hooks:

```bash
poetry run pre-commit install
```

This command only needs to be run once per project clone. It sets up the hooks to run automatically on git commit.

## 2.3 Usage

**Automatic:** Simply run git commit as usual. If any hooks fail, address the reported issues (some hooks like formatters might fix files automatically) and git add the changes before committing again.

**Manual:** You can run all hooks on all files manually at any time:

```bash
poetry run pre-commit run --all-files
```

This is useful for checking the entire codebase or after making significant changes.

# 3. Usage
## Run the app
```python
poetry run python run.py
```

Enjoy!

