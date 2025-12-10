# Installation and Testing

## Launch with Docker Compose

Use Docker Compose to build and start the entire stack:

```bash
docker-compose up --build
```

This command starts the backend API, frontend application, and supporting services such as Ollama and ChromaDB.

## Manual Backend Setup

Set up and run the backend without Docker:

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API will be available at <http://127.0.0.1:8000>.

## Manual Frontend Setup

To run the React frontend directly:

> **Note:** run `npm install` before `npm start` to ensure all dependencies are installed.

```bash
cd frontend
npm install
npm start
```

The development server runs on <http://localhost:3000> by default.

### Troubleshooting

If you see an error like `react-scripts: command not found`, the dependencies may not be installed or your Node version is unsupported. Install dependencies with `npm install` and use Node 18 for best compatibility.

## Running Tests

Install backend requirements and execute the test suite:

```bash
pip install -r backend/requirements.txt
pytest
```

