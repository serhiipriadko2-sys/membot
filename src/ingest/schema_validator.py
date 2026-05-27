"""
SCHEMA-02: Адаптивная валидация схем с Dead Letter Queue.
Обработка «грязных» данных, изоляция некорректных записей.
"""
import json
import logging
from typing import Optional, Any, Literal
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ValidationStatus(str, Enum):
    """Статусы валидации."""
    VALID = "valid"
    INVALID = "invalid"
    PARTIAL = "partial"
    UNKNOWN = "unknown"


@dataclass
class ValidationError:
    """Ошибка валидации."""
    field: str
    expected_type: str
    actual_value: Any
    message: str
    
    def to_dict(self) -> dict:
        return {
            "field": self.field,
            "expected_type": self.expected_type,
            "actual_value": str(self.actual_value),
            "message": self.message
        }


@dataclass
class ValidationResult:
    """Результат валидации записи."""
    status: ValidationStatus
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    sanitized_data: Optional[dict] = None
    
    def is_valid(self) -> bool:
        return self.status == ValidationStatus.VALID
    
    def to_dict(self) -> dict:
        return {
            "status": self.status.value,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": self.warnings,
            "sanitized_data": self.sanitized_data
        }


class DeadLetterQueue:
    """
    Очередь некорректных записей (DLQ).
    
    Сохраняет:
    - Исходные данные
    - Ошибки валидации
    - Метаданные (время, источник)
    """
    
    def __init__(self, output_path: str = "data/dlq"):
        self.output_path = Path(output_path)
        self.output_path.mkdir(parents=True, exist_ok=True)
        self._buffer: list[dict] = []
        self._flush_threshold = 100
    
    def add(self, original_data: Any, validation_result: ValidationResult, 
            source: str = "unknown") -> None:
        """Добавление записи в DLQ."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "source": source,
            "original_data": original_data if isinstance(original_data, (dict, list)) else str(original_data),
            "validation_result": validation_result.to_dict(),
            "error_count": len(validation_result.errors)
        }
        
        self._buffer.append(entry)
        
        if len(self._buffer) >= self._flush_threshold:
            self.flush()
    
    def flush(self) -> str:
        """Сброс буфера в файл."""
        if not self._buffer:
            return ""
        
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"dlq_{timestamp}.jsonl"
        filepath = self.output_path / filename
        
        with open(filepath, "a") as f:
            for entry in self._buffer:
                f.write(json.dumps(entry) + "\n")
        
        logger.info(f"Flushed {len(self._buffer)} records to {filepath}")
        self._buffer.clear()
        
        return str(filepath)
    
    def get_stats(self) -> dict:
        """Статистика DLQ."""
        return {
            "buffer_size": len(self._buffer),
            "output_path": str(self.output_path),
            "files": [f.name for f in self.output_path.glob("dlq_*.jsonl")]
        }


class AdaptiveSchemaValidator:
    """
    SCHEMA-02: Адаптивный валидатор схем.
    
    Поддерживает:
    - Динамическое определение типов
    - Частичную валидацию
    - Санитизацию данных
    - Интеграцию с DLQ
    """
    
    def __init__(self, dlq: Optional[DeadLetterQueue] = None):
        self.dlq = dlq or DeadLetterQueue()
        self._strict_mode = False
    
    def set_strict_mode(self, strict: bool) -> None:
        """Переключение режима строгой валидации."""
        self._strict_mode = strict
    
    def validate_log_event(self, data: dict, source: str = "unknown") -> ValidationResult:
        """
        Валидация события лога (для SolanaLogIngester).
        
        Ожидаемая схема:
        {
            "signature": str (required),
            "slot": int (required),
            "program_id": str (required),
            "data": list[str] (optional),
            "timestamp": str (optional)
        }
        """
        errors = []
        warnings = []
        sanitized = {}
        
        # Проверка signature
        if "signature" not in data:
            errors.append(ValidationError(
                field="signature",
                expected_type="str",
                actual_value=None,
                message="Missing required field 'signature'"
            ))
        elif not isinstance(data["signature"], str):
            errors.append(ValidationError(
                field="signature",
                expected_type="str",
                actual_value=data["signature"],
                message="Field 'signature' must be a string"
            ))
        else:
            sanitized["signature"] = data["signature"]
        
        # Проверка slot
        if "slot" not in data:
            errors.append(ValidationError(
                field="slot",
                expected_type="int",
                actual_value=None,
                message="Missing required field 'slot'"
            ))
        elif not isinstance(data["slot"], (int, float)):
            errors.append(ValidationError(
                field="slot",
                expected_type="int",
                actual_value=data["slot"],
                message="Field 'slot' must be a number"
            ))
        else:
            sanitized["slot"] = int(data["slot"])
        
        # Проверка program_id
        if "program_id" not in data:
            errors.append(ValidationError(
                field="program_id",
                expected_type="str",
                actual_value=None,
                message="Missing required field 'program_id'"
            ))
        elif not isinstance(data["program_id"], str):
            errors.append(ValidationError(
                field="program_id",
                expected_type="str",
                actual_value=data["program_id"],
                message="Field 'program_id' must be a string"
            ))
        else:
            sanitized["program_id"] = data["program_id"]
        
        # Проверка data (опционально)
        if "data" in data:
            if not isinstance(data["data"], list):
                warnings.append("Field 'data' should be a list, converting")
                sanitized["data"] = [str(data["data"])]
            else:
                sanitized["data"] = [str(item) for item in data["data"]]
        else:
            sanitized["data"] = []
        
        # Проверка timestamp (опционально)
        if "timestamp" in data:
            if not isinstance(data["timestamp"], str):
                warnings.append("Field 'timestamp' should be a string, converting")
                sanitized["timestamp"] = str(data["timestamp"])
            else:
                sanitized["timestamp"] = data["timestamp"]
        else:
            sanitized["timestamp"] = datetime.utcnow().isoformat()
        
        # Определение статуса
        if errors:
            status = ValidationStatus.INVALID if self._strict_mode else ValidationStatus.PARTIAL
        elif warnings:
            status = ValidationStatus.PARTIAL
        else:
            status = ValidationStatus.VALID
        
        result = ValidationResult(
            status=status,
            errors=errors,
            warnings=warnings,
            sanitized_data=sanitized if status != ValidationStatus.INVALID else None
        )
        
        # Отправка в DLQ при ошибках
        if status == ValidationStatus.INVALID:
            self.dlq.add(data, result, source)
        
        return result
    
    def validate_batch(self, records: list[dict], source: str = "batch") -> list[ValidationResult]:
        """Валидация пакета записей."""
        results = []
        for record in records:
            result = self.validate_log_event(record, source)
            results.append(result)
        return results


def example_usage():
    """Пример использования валидатора."""
    validator = AdaptiveSchemaValidator()
    
    # Валидная запись
    valid_record = {
        "signature": "5KtPv9xG...",
        "slot": 123456789,
        "program_id": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
        "data": ["base64_encoded_data"]
    }
    
    # Невалидная запись (отсутствует slot)
    invalid_record = {
        "signature": "5KtPv9xG...",
        "program_id": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
    }
    
    result1 = validator.validate_log_event(valid_record, "test")
    result2 = validator.validate_log_event(invalid_record, "test")
    
    print(f"Valid record: {result1.status.value}")
    print(f"Invalid record: {result2.status.value}")
    print(f"DLQ stats: {validator.dlq.get_stats()}")
    
    # Сброс DLQ
    validator.dlq.flush()


if __name__ == "__main__":
    example_usage()
