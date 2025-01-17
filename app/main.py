import fastapi

import app.domains.pipelines.top5.endpoint as endpoint

app = fastapi.FastAPI()
app.include_router(endpoint.router, prefix='/api/pipelines/top5')