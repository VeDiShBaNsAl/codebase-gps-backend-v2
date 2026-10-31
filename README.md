# Codebase GPS

### Navigate Your Codebase. Understand Its Dependencies. Ship Changes with Confidence.

Codebase GPS is an AI-powered code intelligence and developer productivity platform designed to help developers understand unfamiliar repositories, investigate GitHub issues, explore code dependencies, and assess the impact of code changes.

Instead of manually searching through hundreds of files, Codebase GPS helps identify the most relevant parts of a codebase and provides insights into how components are connected.

---

## Key Features

- **Repository Indexing** — Import and index GitHub repositories for code analysis.
- **Code Intelligence** — Parse source code and extract symbols such as functions, classes, and dependencies.
- **Dependency Graph** — Explore relationships between files and code components.
- **Issue Intelligence** — Analyze GitHub issues and identify potentially relevant files and symbols.
- **Impact Analysis** — Understand which parts of a codebase may be affected by a proposed change.
- **Symbol Exploration** — Inspect individual code components and their relationships.
- **Developer Dashboard** — Visualize repository insights through an interactive frontend.

## How It Works

1. **Import:** Provide a GitHub repository.
2. **Index:** The backend clones and processes the repository.
3. **Analyze:** Source files are parsed to extract code symbols and dependencies.
4. **Investigate:** Submit an issue or select a code component.
5. **Explore:** View relevant files, symbols, relationships, and potential change impact.

## Architecture

Codebase GPS is built around three major components:

| Component | Responsibility |
|---|---|
| Backend API | Repository management, indexing, and analysis |
| Code Intelligence | Source parsing, symbol extraction, and dependency graph |
| Frontend | Interactive dashboard and code exploration |

### Technology Stack

**Backend**
- Python
- FastAPI
- Pydantic
- NetworkX
- SQLite

**Code Analysis**
- Tree-sitter
- Abstract Syntax Tree (AST) parsing
- Dependency graph analysis

**Frontend**
- React
- TypeScript
- Vite
- CSS

**Developer Tools**
- Git & GitHub
- Pytest
- Uvicorn
- Swagger / OpenAPI

## Project Structure

```text
codebase-gps-backend-v2/
│
├── app/
│   ├── main.py
│   └── ...
│
├── tests/
│
├── .env.example
├── requirements.txt
├── .gitignore
│
└── frontend/
    ├── src/
    ├── package.json
    └── vite.config.ts
```

*The frontend directory is part of the integrated project structure and may depend on the frontend branch being merged.*

## Getting Started

### Prerequisites

Make sure you have installed:

- Python 3.10+
- Git
- Node.js and npm (for the frontend)

### 1. Clone the Repository

```bash
git clone https://github.com/VeDiShBaNsAl/codebase-gps-backend-v2.git

cd codebase-gps-backend-v2
```

### 2. Create a Python Virtual Environment

**macOS / Linux**

```bash
python3 -m venv .venv

source .venv/bin/activate
```

**Windows**

```bash
python -m venv .venv

.venv\Scripts\activate
```

### 3. Install Dependencies

```bash
python -m pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file from the example:

```bash
cp .env.example .env
```

Configure the following variables:

| Variable | Description |
|---|---|
| `GITHUB_TOKEN` | Optional GitHub access token |
| `DATA_DIR` | Directory used for application data |
| `DATABASE_URL` | SQLite database location |
| `CORS_ORIGINS` | Allowed frontend origins |
| `MAX_REPO_SIZE_MB` | Maximum repository size |
| `CLONE_TIMEOUT_SECONDS` | Repository cloning timeout |
| `MAX_FILES` | Maximum number of files to process |
| `LOG_LEVEL` | Application logging level |

Never commit your actual `.env` file or expose your GitHub token.

### 5. Start the Backend

```bash
uvicorn app.main:app --reload
```

The backend should now be available at:

- API: http://127.0.0.1:8000
- Swagger Documentation: http://127.0.0.1:8000/docs

### 6. Start the Frontend

If the frontend directory is available:

```bash
cd frontend

npm install

npm run dev
```

Configure the frontend API URL using its environment configuration:

```env
VITE_API_URL=http://127.0.0.1:8000
```

Use the Vite URL printed in your terminal to open the frontend.

## API Overview

The backend exposes REST endpoints for repository indexing, code exploration, issue analysis, and impact assessment.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/api/repos/index` | Index a repository |
| GET | `/api/repos/{repo_id}/status` | Check indexing status |
| GET | `/api/repos/{repo_id}` | Retrieve repository information |
| GET | `/api/repos/{repo_id}/graph` | Retrieve dependency graph |
| GET | `/api/repos/{repo_id}/search` | Search repository symbols |
| GET | `/api/repos/{repo_id}/symbols/{symbol_id}` | Inspect a symbol |
| POST | `/api/repos/{repo_id}/issues/analyze` | Analyze an issue |
| POST | `/api/repos/{repo_id}/impact` | Analyze change impact |

For request and response schemas, visit the Swagger documentation at `/docs`.

## Running Tests

Run the backend test suite:

```bash
python -m pytest -q
```

## Deployment

The application is designed to support separate frontend and backend deployments.

- **Frontend:** Vercel
- **Backend:** A Python-compatible hosting platform
- **Database:** Persistent SQLite storage or an appropriate persistent database service

For production deployments, configure environment variables, CORS origins, and persistent data storage appropriately.

## Project Goal

Our goal is to make navigating complex codebases easier, faster, and more understandable.

Codebase GPS aims to reduce the time developers spend figuring out where changes belong, what code is relevant, and what might break when they make those changes.

## Team

Built collaboratively by a team of four developers, with contributions across:

- Backend Engineering
- Frontend Development
- Code Intelligence and Dependency Analysis
- Issue Intelligence and Impact Analysis

---

**Codebase GPS — Your GPS for navigating complex codebases.**
