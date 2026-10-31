# Codebase GPS frontend

Dark, high-contrast React UI for the FastAPI backend. It accepts a GitHub repository URL, polls indexing progress, renders graph components, and calls the issue and impact analysis APIs.

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

Set `VITE_API_URL` when the API is not running on `http://localhost:8000`.
