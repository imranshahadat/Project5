## 8.  `pyproject.toml` Setup

### The Problem
The old project used a `requirements.txt` file. This is an outdated way to manage Python projects. It doesn't lock Python versions, and it doesn't include tools for code formatting or testing.

### Why It's Bad
* Different developers might use different Python versions, causing weird bugs.
* No built-in way to check code quality or run tests.

### The Fix
 replaced `requirements.txt` with a  `pyproject.toml` file. This single file now controls:
* The exact Python version required (Python 3.12.x).
* All backend dependencies (FastAPI, SQLAlchemy, Alembic, etc.).
* Code formatting rules (using `ruff`).
* Testing rules (using `pytest`).

### How to Use It
1. Delete the old `requirements.txt` file.
2. Install everything cleanly by running:
   ```bash
   pip install -e ".[dev,test]"
   ```
3. To format your code automatically, run:
   ```bash
   ruff format .
   ```
4. To check for errors, run:
   ```bash
   ruff check .
   ```
