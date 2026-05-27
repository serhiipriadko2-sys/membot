"""
STORE-03: Хранилище данных с поддержкой Parquet и партиционированием.
Ускорение чтения агрегаций, уменьшение размера файлов.
"""
import json
import logging
from typing import Optional, Any
from pathlib import Path
from datetime import datetime
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ParquetDataStore:
    """
    STORE-03: Хранилище данных на базе Parquet.
    
    Поддерживает:
    - Партиционирование по дате/program_id
    - Сжатие (snappy, gzip, zstd)
    - Инкрементальную запись
    - Быструю агрегацию
    """
    
    def __init__(
        self,
        base_path: str = "data/processed",
        partition_by: list[str] = None,
        compression: str = "snappy"
    ):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        self.partition_by = partition_by or ["date"]
        self.compression = compression
        
        self._buffer: list[dict] = []
        self._buffer_size_threshold = 10000
    
    def _get_partition_path(self, record: dict) -> Path:
        """Генерация пути партиции."""
        path_parts = [self.base_path]
        
        for partition_key in self.partition_by:
            if partition_key == "date":
                date_str = record.get("timestamp", datetime.utcnow().isoformat())[:10]
                path_parts.append(f"date={date_str}")
            elif partition_key == "program_id":
                program_id = record.get("program_id", "unknown")
                # Сокращаем program_id для имени папки
                short_id = program_id[:8] if len(program_id) > 8 else program_id
                path_parts.append(f"program_id={short_id}")
            else:
                value = record.get(partition_key, "unknown")
                path_parts.append(f"{partition_key}={value}")
        
        return Path(*path_parts)
    
    def add(self, record: dict) -> None:
        """Добавление записи в буфер."""
        self._buffer.append(record)
        
        if len(self._buffer) >= self._buffer_size_threshold:
            self.flush()
    
    def add_batch(self, records: list[dict]) -> None:
        """Добавление пакета записей."""
        self._buffer.extend(records)
        
        if len(self._buffer) >= self._buffer_size_threshold:
            self.flush()
    
    def flush(self) -> list[str]:
        """
        Сброс буфера в Parquet файлы.
        
        Returns:
            Список созданных файлов
        """
        if not self._buffer:
            return []
        
        # Группировка по партициям
        partitions: dict[str, list[dict]] = {}
        
        for record in self._buffer:
            partition_path = self._get_partition_path(record)
            partition_key = str(partition_path)
            
            if partition_key not in partitions:
                partitions[partition_key] = []
            
            # Удаляем поля партиционирования из записи
            clean_record = {
                k: v for k, v in record.items() 
                if k not in self.partition_by
            }
            partitions[partition_key].append(clean_record)
        
        # Запись в Parquet
        written_files = []
        
        for partition_path_str, records in partitions.items():
            partition_path = Path(partition_path_str)
            partition_path.mkdir(parents=True, exist_ok=True)
            
            # Генерация имени файла
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"data_{timestamp}.parquet"
            filepath = partition_path / filename
            
            # Конвертация в DataFrame
            df = pd.DataFrame(records)
            
            # Запись в Parquet
            table = pa.Table.from_pandas(df)
            pq.write_table(
                table,
                filepath,
                compression=self.compression,
                use_dictionary=True,
                write_statistics=True
            )
            
            logger.info(f"Written {len(records)} records to {filepath}")
            written_files.append(str(filepath))
        
        self._buffer.clear()
        
        return written_files
    
    def read_partition(
        self,
        filters: Optional[dict[str, Any]] = None,
        columns: Optional[list[str]] = None
    ) -> pd.DataFrame:
        """
        Чтение данных из партиций с фильтрацией.
        
        Args:
            filters: Фильтры вида {"date": "2024-01-01", "program_id": "abc"}
            columns: Список колонок для чтения
        
        Returns:
            DataFrame с данными
        """
        all_data = []
        
        # Поиск всех parquet файлов
        parquet_files = list(self.base_path.rglob("*.parquet"))
        
        for filepath in parquet_files:
            try:
                # Чтение с фильтрацией по пути (партиции)
                should_read = True
                
                if filters:
                    path_str = str(filepath)
                    for key, value in filters.items():
                        if f"{key}={value}" not in path_str:
                            should_read = False
                            break
                
                if not should_read:
                    continue
                
                # Чтение файла
                table = pq.read_table(filepath, columns=columns)
                df = table.to_pandas()
                all_data.append(df)
                
            except Exception as e:
                logger.error(f"Error reading {filepath}: {e}")
        
        if not all_data:
            return pd.DataFrame()
        
        return pd.concat(all_data, ignore_index=True)
    
    def aggregate(
        self,
        group_by: list[str],
        aggregations: dict[str, str],
        filters: Optional[dict[str, Any]] = None
    ) -> pd.DataFrame:
        """
        Агрегация данных.
        
        Args:
            group_by: Колонки для группировки
            aggregations: Агрегации вида {"signature": "count", "slot": "max"}
            filters: Фильтры
        
        Returns:
            DataFrame с агрегированными данными
        """
        df = self.read_partition(filters=filters)
        
        if df.empty:
            return pd.DataFrame()
        
        return df.groupby(group_by).agg(aggregations).reset_index()
    
    def get_stats(self) -> dict:
        """Статистика хранилища."""
        parquet_files = list(self.base_path.rglob("*.parquet"))
        
        total_size = sum(f.stat().st_size for f in parquet_files)
        total_records = 0
        
        for filepath in parquet_files:
            try:
                parquet_file = pq.ParquetFile(filepath)
                total_records += parquet_file.metadata.num_rows
            except Exception:
                pass
        
        return {
            "base_path": str(self.base_path),
            "file_count": len(parquet_files),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "total_records": total_records,
            "compression": self.compression,
            "partition_by": self.partition_by
        }
    
    def compact_partitions(
        self,
        max_file_size_mb: float = 100.0
    ) -> list[str]:
        """
        Компактификация мелких файлов в более крупные.
        
        Args:
            max_file_size_mb: Максимальный размер файла перед компактификацией
        
        Returns:
            Список новых файлов
        """
        parquet_files = list(self.base_path.rglob("*.parquet"))
        
        # Группировка по партициям
        partitions: dict[str, list[Path]] = {}
        
        for filepath in parquet_files:
            # Извлечение пути партиции (без имени файла)
            partition_path = filepath.parent
            partition_key = str(partition_path)
            
            if partition_key not in partitions:
                partitions[partition_key] = []
            partitions[partition_key].append(filepath)
        
        new_files = []
        
        for partition_key, files in partitions.items():
            # Проверка размера файлов
            small_files = []
            
            for filepath in files:
                size_mb = filepath.stat().st_size / (1024 * 1024)
                if size_mb < max_file_size_mb:
                    small_files.append(filepath)
            
            if len(small_files) <= 1:
                continue
            
            # Чтение всех мелких файлов
            all_data = []
            
            for filepath in small_files:
                try:
                    table = pq.read_table(filepath)
                    df = table.to_pandas()
                    all_data.append(df)
                except Exception as e:
                    logger.error(f"Error reading {filepath}: {e}")
            
            if not all_data:
                continue
            
            # Объединение и запись
            combined_df = pd.concat(all_data, ignore_index=True)
            
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"data_compacted_{timestamp}.parquet"
            filepath = Path(partition_key) / filename
            
            table = pa.Table.from_pandas(combined_df)
            pq.write_table(
                table,
                filepath,
                compression=self.compression
            )
            
            logger.info(f"Compacted {len(small_files)} files into {filepath}")
            new_files.append(str(filepath))
            
            # Удаление старых файлов (опционально)
            # for old_file in small_files:
            #     old_file.unlink()
        
        return new_files


def example_usage():
    """Пример использования хранилища."""
    store = ParquetDataStore(
        base_path="data/processed",
        partition_by=["date", "program_id"],
        compression="snappy"
    )
    
    # Добавление тестовых данных
    test_records = [
        {
            "signature": f"sig_{i}",
            "slot": 123456789 + i,
            "program_id": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
            "timestamp": datetime.utcnow().isoformat(),
            "data": ["test_data"]
        }
        for i in range(100)
    ]
    
    store.add_batch(test_records)
    store.flush()
    
    # Чтение данных
    df = store.read_partition(filters={"program_id": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"})
    print(f"Read {len(df)} records")
    
    # Агрегация
    agg = store.aggregate(
        group_by=["program_id"],
        aggregations={"signature": "count", "slot": "max"}
    )
    print(f"Aggregation: {agg}")
    
    # Статистика
    stats = store.get_stats()
    print(f"Stats: {stats}")


if __name__ == "__main__":
    example_usage()
