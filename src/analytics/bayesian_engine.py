"""
HYP-04: Байесовское ядро обновления гипотез.
Динамическое обновление вероятностей на основе событий.
"""
import logging
from typing import Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import math

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HypothesisStatus(str, Enum):
    """Статусы гипотезы."""
    ACTIVE = "active"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    PAUSED = "paused"


@dataclass
class BayesianHypothesis:
    """
    Гипотеза с байесовской вероятностью.
    
    Атрибуты:
        id: Уникальный идентификатор
        name: Название гипотезы
        prior: Априорная вероятность (0-1)
        posterior: Апостериорная вероятность (обновляется)
        likelihood_ratio: Отношение правдоподобия P(E|H) / P(E|¬H)
        status: Текущий статус
        evidence_count: Количество собранных свидетельств
        created_at: Время создания
        updated_at: Время последнего обновления
    """
    id: str
    name: str
    prior: float
    posterior: float = field(init=False)
    likelihood_ratio: float = 1.0
    status: HypothesisStatus = HypothesisStatus.ACTIVE
    evidence_count: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        self.posterior = self.prior
    
    def update(self, evidence_strength: float) -> None:
        """
        Обновление апостериорной вероятности по формуле Байеса.
        
        Args:
            evidence_strength: Сила свидетельства (>1 подтверждает, <1 опровергает)
        """
        if self.status == HypothesisStatus.REJECTED:
            logger.warning(f"Cannot update rejected hypothesis: {self.id}")
            return
        
        # Байесовское обновление
        # P(H|E) = P(E|H) * P(H) / P(E)
        # Используем odds form: O(H|E) = LR * O(H)
        
        prior_odds = self.posterior / (1 - self.posterior + 1e-10)
        posterior_odds = evidence_strength * prior_odds
        
        new_posterior = posterior_odds / (posterior_odds + 1)
        
        # Ограничение диапазона [0.001, 0.999]
        self.posterior = max(0.001, min(0.999, new_posterior))
        self.evidence_count += 1
        self.updated_at = datetime.utcnow()
        
        # Автоматическая смена статуса
        if self.posterior >= 0.95:
            self.status = HypothesisStatus.CONFIRMED
            logger.info(f"Hypothesis {self.id} CONFIRMED with p={self.posterior:.3f}")
        elif self.posterior <= 0.05:
            self.status = HypothesisStatus.REJECTED
            logger.info(f"Hypothesis {self.id} REJECTED with p={self.posterior:.3f}")
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "prior": self.prior,
            "posterior": self.posterior,
            "likelihood_ratio": self.likelihood_ratio,
            "status": self.status.value,
            "evidence_count": self.evidence_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


class BayesianEngine:
    """
    HYP-04: Байесовский движок для управления гипотезами.
    
    Поддерживает:
    - Множественные гипотезы
    - Динамическое обновление
    - Пороговые алерты
    - Историю обновлений
    """
    
    def __init__(self, confirmation_threshold: float = 0.95, rejection_threshold: float = 0.05):
        self._hypotheses: dict[str, BayesianHypothesis] = {}
        self.confirmation_threshold = confirmation_threshold
        self.rejection_threshold = rejection_threshold
        self._update_history: list[dict] = []
    
    def add_hypothesis(
        self,
        id: str,
        name: str,
        prior: float,
        likelihood_ratio: float = 1.0
    ) -> BayesianHypothesis:
        """Добавление новой гипотезы."""
        if not 0 < prior < 1:
            raise ValueError("Prior must be in range (0, 1)")
        
        hypothesis = BayesianHypothesis(
            id=id,
            name=name,
            prior=prior,
            likelihood_ratio=likelihood_ratio
        )
        
        self._hypotheses[id] = hypothesis
        logger.info(f"Added hypothesis: {id} ({name}) with prior={prior:.3f}")
        
        return hypothesis
    
    def get_hypothesis(self, id: str) -> Optional[BayesianHypothesis]:
        """Получение гипотезы по ID."""
        return self._hypotheses.get(id)
    
    def update_hypothesis(
        self,
        id: str,
        evidence_strength: float,
        event_context: Optional[dict] = None
    ) -> Optional[BayesianHypothesis]:
        """
        Обновление гипотезы на основе свидетельства.
        
        Args:
            id: ID гипотезы
            evidence_strength: Сила свидетельства
            event_context: Контекст события (для логирования)
        
        Returns:
            Обновленная гипотеза или None
        """
        hypothesis = self._hypotheses.get(id)
        
        if not hypothesis:
            logger.error(f"Hypothesis not found: {id}")
            return None
        
        old_posterior = hypothesis.posterior
        hypothesis.update(evidence_strength)
        
        # Логирование обновления
        update_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "hypothesis_id": id,
            "old_posterior": old_posterior,
            "new_posterior": hypothesis.posterior,
            "evidence_strength": evidence_strength,
            "event_context": event_context or {}
        }
        
        self._update_history.append(update_record)
        
        # Проверка порогов
        if hypothesis.posterior >= self.confirmation_threshold:
            logger.warning(f"ALERT: Hypothesis {id} crossed confirmation threshold!")
        elif hypothesis.posterior <= self.rejection_threshold:
            logger.warning(f"ALERT: Hypothesis {id} crossed rejection threshold!")
        
        return hypothesis
    
    def update_multiple(
        self,
        updates: list[tuple[str, float, Optional[dict]]]
    ) -> list[Optional[BayesianHypothesis]]:
        """
        Массовое обновление гипотез.
        
        Args:
            updates: Список кортежей (hypothesis_id, evidence_strength, context)
        
        Returns:
            Список обновленных гипотез
        """
        results = []
        
        for hypothesis_id, strength, context in updates:
            result = self.update_hypothesis(hypothesis_id, strength, context)
            results.append(result)
        
        return results
    
    def get_all_hypotheses(self) -> list[BayesianHypothesis]:
        """Получение всех гипотез."""
        return list(self._hypotheses.values())
    
    def get_active_hypotheses(self) -> list[BayesianHypothesis]:
        """Получение активных гипотез."""
        return [
            h for h in self._hypotheses.values()
            if h.status == HypothesisStatus.ACTIVE
        ]
    
    def get_confirmed_hypotheses(self) -> list[BayesianHypothesis]:
        """Получение подтвержденных гипотез."""
        return [
            h for h in self._hypotheses.values()
            if h.status == HypothesisStatus.CONFIRMED
        ]
    
    def get_update_history(
        self,
        hypothesis_id: Optional[str] = None,
        limit: int = 100
    ) -> list[dict]:
        """Получение истории обновлений."""
        history = self._update_history
        
        if hypothesis_id:
            history = [h for h in history if h["hypothesis_id"] == hypothesis_id]
        
        return history[-limit:]
    
    def get_stats(self) -> dict:
        """Статистика движка."""
        hypotheses = list(self._hypotheses.values())
        
        return {
            "total_hypotheses": len(hypotheses),
            "active": len([h for h in hypotheses if h.status == HypothesisStatus.ACTIVE]),
            "confirmed": len([h for h in hypotheses if h.status == HypothesisStatus.CONFIRMED]),
            "rejected": len([h for h in hypotheses if h.status == HypothesisStatus.REJECTED]),
            "total_updates": len(self._update_history),
            "avg_posterior": sum(h.posterior for h in hypotheses) / len(hypotheses) if hypotheses else 0
        }
    
    def export_to_dict(self) -> dict:
        """Экспорт состояния в словарь."""
        return {
            "hypotheses": [h.to_dict() for h in self._hypotheses.values()],
            "recent_updates": self._update_history[-50:],
            "stats": self.get_stats()
        }


def example_usage():
    """Пример использования байесовского движка."""
    engine = BayesianEngine()
    
    # Добавление гипотез
    engine.add_hypothesis(
        id="HYP-001",
        name="MEME token launches increase on weekends",
        prior=0.5,
        likelihood_ratio=2.0
    )
    
    engine.add_hypothesis(
        id="HYP-002",
        name="High parser confidence correlates with successful trades",
        prior=0.6,
        likelihood_ratio=3.0
    )
    
    # Обновление на основе событий
    engine.update_hypothesis("HYP-001", evidence_strength=1.5, event_context={"day": "Saturday"})
    engine.update_hypothesis("HYP-001", evidence_strength=1.8, event_context={"day": "Sunday"})
    engine.update_hypothesis("HYP-002", evidence_strength=2.0, event_context={"confidence": 0.95})
    
    # Получение результатов
    print("\nAll hypotheses:")
    for h in engine.get_all_hypotheses():
        print(f"  {h.name}: p={h.posterior:.3f} [{h.status.value}]")
    
    print(f"\nStats: {engine.get_stats()}")
    
    print("\nUpdate history:")
    for update in engine.get_update_history(limit=5):
        print(f"  {update['hypothesis_id']}: {update['old_posterior']:.3f} -> {update['new_posterior']:.3f}")


if __name__ == "__main__":
    example_usage()
