"""
MON-07: FastAPI сервер для мониторинга здоровья системы.
REST API для получения статистики всех компонентов.
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Any
import os
import sys

# Добавляем src в path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = FastAPI(
    title="Membot Health Monitor",
    description="API для мониторинга здоровья системы membot",
    version="1.0.0"
)


class HealthStatus(BaseModel):
    status: str
    component: str
    details: dict[str, Any]


class SystemHealth(BaseModel):
    overall_status: str
    components: dict[str, HealthStatus]
    timestamp: str


@app.get("/", tags=["Root"])
async def root():
    """Корневой эндпоинт."""
    return {
        "message": "Membot Health Monitor API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health", response_model=SystemHealth, tags=["Health"])
async def get_health():
    """Получение общего состояния системы."""
    from datetime import datetime
    
    components = {}
    
    # Проверка хранилища данных
    try:
        from src.storage.parquet_store import ParquetDataStore
        store = ParquetDataStore()
        stats = store.get_stats()
        components["storage"] = HealthStatus(
            status="healthy",
            component="storage",
            details=stats
        )
    except Exception as e:
        components["storage"] = HealthStatus(
            status="unhealthy",
            component="storage",
            details={"error": str(e)}
        )
    
    # Проверка DLQ
    try:
        from src.ingest.schema_validator import DeadLetterQueue
        dlq = DeadLetterQueue()
        stats = dlq.get_stats()
        components["dlq"] = HealthStatus(
            status="healthy",
            component="dlq",
            details=stats
        )
    except Exception as e:
        components["dlq"] = HealthStatus(
            status="unhealthy",
            component="dlq",
            details={"error": str(e)}
        )
    
    # Определение общего статуса
    unhealthy_count = sum(1 for c in components.values() if c.status == "unhealthy")
    overall_status = "healthy" if unhealthy_count == 0 else "degraded" if unhealthy_count < len(components) else "unhealthy"
    
    return SystemHealth(
        overall_status=overall_status,
        components=components,
        timestamp=datetime.utcnow().isoformat()
    )


@app.get("/health/storage", response_model=HealthStatus, tags=["Health"])
async def get_storage_health():
    """Статус хранилища данных."""
    try:
        from src.storage.parquet_store import ParquetDataStore
        store = ParquetDataStore()
        stats = store.get_stats()
        
        return HealthStatus(
            status="healthy",
            component="storage",
            details=stats
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/health/dlq", response_model=HealthStatus, tags=["Health"])
async def get_dlq_health():
    """Статус Dead Letter Queue."""
    try:
        from src.ingest.schema_validator import DeadLetterQueue
        dlq = DeadLetterQueue()
        stats = dlq.get_stats()
        
        return HealthStatus(
            status="healthy",
            component="dlq",
            details=stats
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/metrics", tags=["Metrics"])
async def get_metrics():
    """Получение метрик системы."""
    from datetime import datetime
    
    metrics = {
        "timestamp": datetime.utcnow().isoformat(),
        "components": {}
    }
    
    # Метрики хранилища
    try:
        from src.storage.parquet_store import ParquetDataStore
        store = ParquetDataStore()
        stats = store.get_stats()
        metrics["components"]["storage"] = {
            "file_count": stats.get("file_count", 0),
            "total_records": stats.get("total_records", 0),
            "total_size_mb": stats.get("total_size_mb", 0)
        }
    except Exception:
        metrics["components"]["storage"] = {"error": "unavailable"}
    
    # Метрики DLQ
    try:
        from src.ingest.schema_validator import DeadLetterQueue
        dlq = DeadLetterQueue()
        stats = dlq.get_stats()
        metrics["components"]["dlq"] = {
            "buffer_size": stats.get("buffer_size", 0),
            "file_count": len(stats.get("files", []))
        }
    except Exception:
        metrics["components"]["dlq"] = {"error": "unavailable"}
    
    return metrics


@app.get("/ready", tags=["Health"])
async def readiness_check():
    """Проверка готовности сервиса (для Kubernetes)."""
    return {"status": "ready"}


@app.get("/live", tags=["Health"])
async def liveness_check():
    """Проверка живости сервиса (для Kubernetes)."""
    return {"status": "alive"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
