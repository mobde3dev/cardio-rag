# CardioRAG

CardioRAG is a clinical question-answering application with a Next.js web interface and a FastAPI retrieval service backed by Supabase.

## Project structure

```text
cardio-rag-backend/    FastAPI retrieval API
cardio-rag-web/        Next.js web application
```

## Requirements

- Node.js 18.17 or newer
- npm
- Python 3.10 or newer
- A Supabase project with the schema in `cardio-rag-web/supabase_schema.sql`
- A Groq API key for chat responses
- Cloudflare credentials if embeddings are generated or ingested

## Environment setup

Create local environment files from the committed templates.

PowerShell:

```powershell
Copy-Item cardio-rag-backend/.env.example cardio-rag-backend/.env
Copy-Item cardio-rag-web/.env.example cardio-rag-web/.env.local
```

Set the values in these local files:

### Backend: `cardio-rag-backend/.env`

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_service_role_key
CLOUDFLARE_ACCOUNT_ID=your_cloudflare_account_id
CLOUDFLARE_API_TOKEN=your_cloudflare_api_token
CLOUDFLARE_EMBED_MODEL=@cf/baai/bge-m3
FRONTEND_URL=http://localhost:3000
```

### Web: `cardio-rag-web/.env.local`

```env
GROQ_API_KEY=your_groq_api_key
RAG_BACKEND_URL=http://127.0.0.1:8000
DEFAULT_GROQ_MODEL=openai/gpt-oss-120b
DEFAULT_TRANSLATION_MODEL=openai/gpt-oss-20b
```

The real `.env` and `.env.local` files are intentionally ignored by Git. Never commit API keys, Supabase service-role keys, or Cloudflare tokens. Use GitHub Actions, Render, Vercel, or another deployment provider's secret settings for hosted values.

## Supabase setup

1. Create a Supabase project.
2. Open the SQL Editor.
3. Run `cardio-rag-web/supabase_schema.sql`.
4. Put the project URL and service-role key in the backend environment file.
5. Ensure your Supabase tables contain the guideline chunks and embeddings required by the retriever.

## Run locally

Open two terminals from the repository root.

### Terminal 1: backend

PowerShell:

```powershell
Set-Location cardio-rag-backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-runtime.txt
uvicorn src.api:app --reload --host 0.0.0.0 --port 8000
```

Verify the API at <http://127.0.0.1:8000/health>. It should return `{"status":"ok"}`.

### Terminal 2: web

PowerShell:

```powershell
Set-Location cardio-rag-web
npm install
npm run dev
```

Open <http://localhost:3000> in a browser.

For a production web build:

```powershell
npm run build
npm start
```

## Deployment

### Backend on Render

The backend includes `cardio-rag-backend/render.yaml`.

1. Create a new Render Blueprint from this GitHub repository.
2. Select the `cardio-rag-backend` directory if Render asks for the service root.
3. Add `SUPABASE_URL`, `SUPABASE_KEY`, `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_TOKEN`, and `FRONTEND_URL` as Render environment variables.
4. Deploy and copy the service URL.

### Web on Vercel

1. Import this GitHub repository into Vercel.
2. Set the project root directory to `cardio-rag-web`.
3. Add `GROQ_API_KEY`, `RAG_BACKEND_URL`, `DEFAULT_GROQ_MODEL`, and `DEFAULT_TRANSLATION_MODEL` in Vercel Project Settings.
4. Set `RAG_BACKEND_URL` to the deployed Render backend URL.
5. Redeploy after saving the environment variables.

## Useful API endpoints

```text
GET  /health
POST /retrieve   { "query": "..." }
```

The Next.js application exposes its own API routes under `/api`, including `/api/chat`, `/api/retrieve`, and `/api/translate`.

## GitHub environment files

GitHub contains `.env.example` templates only. This is deliberate: uploading real environment files would expose credentials publicly and can compromise Supabase, Groq, or Cloudflare resources. Configure production secrets in the hosting provider instead.