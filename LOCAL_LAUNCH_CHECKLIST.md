# Local Launch Checklist

This checklist gets THIH Clip Engine running locally as a practical OpusClip-style replacement: submit a YouTube URL or upload a video, let the worker process it, and download clips from the task page.

## 1. Prerequisites

- Docker Desktop with Docker Compose.
- Git.
- Node.js 20+ and pnpm only if you run the frontend outside Docker.
- Python 3.11 and uv only if you run the backend outside Docker.
- FFmpeg is included in the backend Docker image. Install FFmpeg locally only for non-Docker backend runs.
- Enough disk space for uploaded videos, downloaded YouTube sources, transcripts, and rendered clips.

## 2. Required API Keys

Minimum required for one successful clip generation:

- `ASSEMBLY_AI_API_KEY`: required for transcription.
- One LLM path:
  - `LLM=openai:<model>` with `OPENAI_API_KEY`, or
  - `LLM=google-gla:<model>` with `GOOGLE_API_KEY`, or
  - `LLM=anthropic:<model>` with `ANTHROPIC_API_KEY`, or
  - `LLM=ollama:<model>` with local Ollama available to the backend.
- `BACKEND_AUTH_SECRET`: required for trusted frontend to backend calls. Use a strong random value outside throwaway local testing.

Optional:

- `APIFY_API_TOKEN`: paid fallback for YouTube downloads.
- `YOUTUBE_DATA_API_KEY`: official YouTube metadata path.
- `PEXELS_API_KEY`: B-roll lookup.
- `RESEND_API_KEY` and `RESEND_FROM_EMAIL`: notification email flows.

## 3. Create `.env`

```powershell
Copy-Item .env.example .env
```

Edit `.env` and set at least:

```env
ASSEMBLY_AI_API_KEY=your_assemblyai_key
LLM=google-gla:gemini-3-flash-preview
GOOGLE_API_KEY=your_google_key
BACKEND_AUTH_SECRET=replace_me_with_a_long_random_string
APP_SETTINGS_ENCRYPTION_KEY=replace_me_with_a_long_random_string
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_URL=http://localhost:3107
BACKEND_INTERNAL_URL=http://backend:8000
POSTGRES_DB=supoclip
POSTGRES_USER=supoclip
POSTGRES_PASSWORD=supoclip_password
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
```

The `supoclip` database/container names are retained for local compatibility. Do not rename `x-supoclip-*` headers, queue names, temp prefixes, or compatibility URLs during launch setup.

## 4. Start Locally With Docker Compose

```powershell
docker compose up -d --build
```

If your Docker CLI uses the legacy command, use:

```powershell
docker-compose up -d --build
```

Services:

- `frontend`: Next.js app on `http://localhost:3107`.
- `backend`: FastAPI app on `http://localhost:8000`.
- `worker`: ARQ worker that consumes Redis jobs and renders clips.
- `postgres`: PostgreSQL 15 with `init.sql` mounted for first boot.
- `redis`: job queue and progress/cache dependency.

## 5. Migrations

Fresh Docker volume:

- PostgreSQL runs `init.sql` automatically on the first creation of the `postgres_data` volume.
- This does not re-run on later starts with the same volume.

Existing Docker volume:

- There is no automatic migration runner in the current Compose startup.
- Run additive SQL migrations manually after `postgres` is healthy.

PowerShell command for root backend migrations:

```powershell
Get-ChildItem backend\migrations\*.sql | Sort-Object Name | ForEach-Object { Get-Content $_.FullName | docker exec -i supoclip-postgres psql -U supoclip -d supoclip }
```

PowerShell command for backend `src` SQL migrations:

```powershell
Get-ChildItem backend\src\migrations\sql\*.sql | Sort-Object Name | ForEach-Object { Get-Content $_.FullName | docker exec -i supoclip-postgres psql -U supoclip -d supoclip }
```

If you want a truly clean local database, remove the volume and start again:

```powershell
docker compose down
docker volume rm supoclip_postgres_data
docker compose up -d --build
```

This deletes local database data.

## 6. Health Checks

```powershell
docker compose ps
curl http://localhost:8000/health
curl http://localhost:8000/health/db
curl http://localhost:8000/health/redis
curl http://localhost:3107/
```

PowerShell alternative:

```powershell
Invoke-WebRequest http://localhost:8000/health
Invoke-WebRequest http://localhost:8000/health/db
Invoke-WebRequest http://localhost:8000/health/redis
Invoke-WebRequest http://localhost:3107/
```

Expected backend responses include `status: healthy` for `/health`, `/health/db`, and `/health/redis`.

## 7. Submit a YouTube URL

1. Open `http://localhost:3107`.
2. Sign up or sign in locally.
3. Paste a YouTube URL into the source input.
4. Keep `fast` mode for the first smoke test.
5. Submit the task.
6. Open the task page and watch progress move through queueing, transcription, analysis, and clip rendering.

If YouTube download fails, check backend and worker logs. Some videos block direct download; set `APIFY_API_TOKEN` and use the Apify fallback when needed.

## 8. Upload a Video

1. Open `http://localhost:3107`.
2. Choose the upload/local video option in the source picker.
3. Select a local video file.
4. Submit the task.
5. Watch the task page for worker progress and rendered clips.

Uploaded videos are stored in the Docker `uploads` volume under `/app/uploads/uploads` inside backend/worker containers.

## 9. Confirm the Worker Is Processing

Stream worker logs:

```powershell
docker compose logs -f worker
```

Useful signs:

- `Worker processing task <task_id>`
- progress messages for transcript generation and AI analysis
- `Creating clip X/Y`
- `Task <task_id> completed successfully`

Check Redis queue names without renaming them:

```powershell
docker exec -it supoclip-redis redis-cli LLEN supoclip_tasks
```

If you set `REDIS_PASSWORD`, use:

```powershell
docker exec -it supoclip-redis redis-cli -a "$env:REDIS_PASSWORD" LLEN supoclip_tasks
```

## 10. Where Exports Are Saved

Rendered clips are saved inside the backend/worker container at:

```text
/app/uploads/clips
```

That path is backed by the Docker `uploads` named volume. The normal user path is the task page in the frontend, where clips are previewed and downloaded through backend routes.

To inspect files directly:

```powershell
docker exec -it supoclip-backend sh -lc "ls -lah /app/uploads/clips"
```

## 11. Common Failures And Fixes

- Frontend is up but tasks never progress:
  - Run `docker compose logs -f worker` and confirm the worker is alive.
  - Check `curl http://localhost:8000/health/redis`.
- Backend health fails:
  - Run `docker compose logs -f backend`.
  - Confirm `.env` does not contain malformed URLs or secrets with unescaped shell characters.
- Database errors after pulling new code:
  - Existing volumes do not re-run `init.sql`; run the migration commands in section 5.
- No clips generated:
  - Use a shorter, speech-heavy source for the first smoke test.
  - Confirm `ASSEMBLY_AI_API_KEY` and the selected LLM provider key are set.
  - Check worker logs for transcription or analysis errors.
- YouTube download fails:
  - Try another public YouTube URL.
  - Set `APIFY_API_TOKEN` for the paid fallback path.
- Upload fails from the browser:
  - Confirm `CORS_ORIGINS` includes `http://localhost:3107`.
  - Confirm backend is reachable at `http://localhost:8000`.
- Ollama cannot be reached from Docker:
  - Use `OLLAMA_BASE_URL=http://host.docker.internal:11434/v1`.

## 12. Stop Local Services

```powershell
docker compose down
```

To remove local database/cache/media volumes, use Docker Desktop or `docker volume rm` carefully. Removing volumes deletes local data.
