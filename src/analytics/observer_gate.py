"""
OBS-05: Observer Gate v2.0 (Real-time).
Алерты при пересечении порога уверенности гипотез, задержка < 2 секунд.
"""
import asyncio
import logging
from typing import Optional, Callable, Any, Awaitable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """Уровни серьезности алертов."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Alert:
    """Структура алерта."""
    id: str
    hypothesis_id: str
    hypothesis_name: str
    severity: AlertSeverity
    message: str
    posterior_value: float
    threshold: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "hypothesis_id": self.hypothesis_id,
            "hypothesis_name": self.hypothesis_name,
            "severity": self.severity.value,
            "message": self.message,
            "posterior_value": self.posterior_value,
            "threshold": self.threshold,
            "timestamp": self.timestamp.isoformat()
        }


class ObserverGate:
    """
    OBS-05: Observer Gate для мониторинга гипотез в реальном времени.
    
    Поддерживает:
    - Мониторинг порогов подтверждений/отклонений
    - Асинхронные алерты с задержкой < 2 сек
    - Callback-обработчики
    - Историю алертов
    """
    
    def __init__(
        self,
        confirmation_threshold: float = 0.95,
        rejection_threshold: float = 0.05,
        alert_callback: Optional[Callable[[Alert], Awaitable[None]]] = None
    ):
        self.confirmation_threshold = confirmation_threshold
        self.rejection_threshold = rejection_threshold
        self.alert_callback = alert_callback
        
        self._alerts: list[Alert] = []
        self._alert_counter = 0
        self._running = False
    
    async def check_hypothesis(
        self,
        hypothesis_id: str,
        hypothesis_name: str,
        posterior: float
    ) -> Optional[Alert]:
        """
        Проверка гипотезы на пересечение порогов.
        
        Args:
            hypothesis_id: ID гипотезы
            hypothesis_name: Название гипотезы
            posterior: Текущая апостериорная вероятность
        
        Returns:
            Alert если порог пересечен, иначе None
        """
        alert = None
        
        # Проверка подтверждения
        if posterior >= self.confirmation_threshold:
            alert = self._create_alert(
                hypothesis_id=hypothesis_id,
                hypothesis_name=hypothesis_name,
                severity=AlertSeverity.CRITICAL,
                message=f"Hypothesis CONFIRMED: posterior {posterior:.3f} >= {self.confirmation_threshold}",
                posterior_value=posterior,
                threshold=self.confirmation_threshold
            )
        
        # Проверка отклонения
        elif posterior <= self.rejection_threshold:
            alert = self._create_alert(
                hypothesis_id=hypothesis_id,
                hypothesis_name=hypothesis_name,
                severity=AlertSeverity.WARNING,
                message=f"Hypothesis REJECTED: posterior {posterior:.3f} <= {self.rejection_threshold}",
                posterior_value=posterior,
                threshold=self.rejection_threshold
            )
        
        if alert:
            await self._dispatch_alert(alert)
        
        return alert
    
    def _create_alert(
        self,
        hypothesis_id: str,
        hypothesis_name: str,
        severity: AlertSeverity,
        message: str,
        posterior_value: float,
        threshold: float
    ) -> Alert:
        """Создание алерта."""
        self._alert_counter += 1
        
        alert = Alert(
            id=f"ALERT-{self._alert_counter:06d}",
            hypothesis_id=hypothesis_id,
            hypothesis_name=hypothesis_name,
            severity=severity,
            message=message,
            posterior_value=posterior_value,
            threshold=threshold
        )
        
        self._alerts.append(alert)
        logger.warning(f"{alert.id}: {message}")
        
        return alert
    
    async def _dispatch_alert(self, alert: Alert) -> None:
        """Отправка алерта обработчикам."""
        # Встроенный логгер
        logger.info(f"Dispatching alert: {alert.id}")
        
        # Кастомный callback
        if self.alert_callback:
            try:
                start_time = datetime.utcnow()
                await self.alert_callback(alert)
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                
                if elapsed > 2.0:
                    logger.error(f"Alert callback took {elapsed:.2f}s (> 2s SLA)")
                else:
                    logger.debug(f"Alert dispatched in {elapsed:.3f}s")
                    
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")
    
    def get_alerts(
        self,
        hypothesis_id: Optional[str] = None,
        severity: Optional[AlertSeverity] = None,
        limit: int = 100
    ) -> list[Alert]:
        """Получение алертов с фильтрацией."""
        alerts = self._alerts
        
        if hypothesis_id:
            alerts = [a for a in alerts if a.hypothesis_id == hypothesis_id]
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        return alerts[-limit:]
    
    def get_stats(self) -> dict:
        """Статистика Observer Gate."""
        alerts = self._alerts
        
        return {
            "total_alerts": len(alerts),
            "critical": len([a for a in alerts if a.severity == AlertSeverity.CRITICAL]),
            "warning": len([a for a in alerts if a.severity == AlertSeverity.WARNING]),
            "info": len([a for a in alerts if a.severity == AlertSeverity.INFO]),
            "confirmation_threshold": self.confirmation_threshold,
            "rejection_threshold": self.rejection_threshold
        }
    
    def clear_alerts(self) -> None:
        """Очистка истории алертов."""
        self._alerts.clear()
        logger.info("Alerts cleared")


async def example_alert_handler(alert: Alert):
    """Пример обработчика алертов."""
    print(f"[ALERT HANDLER] Received: {alert.to_dict()}")
    # Здесь можно отправить в Slack, Telegram, email и т.д.
    await asyncio.sleep(0.1)  # Симуляция работы


async def main():
    """Пример использования Observer Gate."""
    gate = ObserverGate(
        confirmation_threshold=0.95,
        rejection_threshold=0.05,
        alert_callback=example_alert_handler
    )
    
    # Симуляция обновления гипотез
    test_cases = [
        ("HYP-001", "Test Hypothesis 1", 0.50),
        ("HYP-001", "Test Hypothesis 1", 0.75),
        ("HYP-001", "Test Hypothesis 1", 0.90),
        ("HYP-001", "Test Hypothesis 1", 0.96),  # Должен сработать алерт
        ("HYP-002", "Test Hypothesis 2", 0.30),
        ("HYP-002", "Test Hypothesis 2", 0.10),
        ("HYP-002", "Test Hypothesis 2", 0.04),  # Должен сработать алерт
    ]
    
    for hyp_id, hyp_name, posterior in test_cases:
        print(f"\nChecking {hyp_id} with posterior={posterior:.2f}")
        await gate.check_hypothesis(hyp_id, hyp_name, posterior)
        await asyncio.sleep(0.5)
    
    print(f"\nObserver Gate Stats: {gate.get_stats()}")
    print(f"\nRecent Alerts:")
    for alert in gate.get_alerts(limit=5):
        print(f"  {alert.id}: {alert.message}")


if __name__ == "__main__":
    asyncio.run(main())
