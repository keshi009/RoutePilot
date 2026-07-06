"""FastAPI 应用入口。

负责初始化日志、配置 CORS、注册聚合路由；业务逻辑不要写在这里。
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router
from .logging_setup import setup_logging

setup_logging()
app = FastAPI(title="RoutePilot AI Trip Assistant", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
