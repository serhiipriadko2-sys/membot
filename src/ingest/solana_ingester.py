"""
INGEST-01: Асинхронный коннектор Solana WebSocket для MEME token factories.
Получение логов в реальном времени, буферизация, базовая валидация.
"""
import asyncio
import json
import logging
from typing import Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime
import websockets
from solana.rpc.websocket_api import connect
from solana.rpc.types import TokenAccountOpts
from solders.pubkey import Pubkey

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class LogEvent:
    """Структура события лога."""
    signature: str
    slot: int
    program_id: str
    data: list[str]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        return {
            "signature": self.signature,
            "slot": self.slot,
            "program_id": self.program_id,
            "data": self.data,
            "timestamp": self.timestamp.isoformat()
        }


class SolanaLogIngester:
    """
    INGЕСТ-01: Асинхронный инжестор логов Solana.
    
    Поддерживает:
    - Подключение к WebSocket RPC
    - Подписку на логи по program_id
    - Буферизацию событий
    - Callback-обработку
    - Автоматический reconnect
    """
    
    def __init__(
        self,
        rpc_ws_url: str,
        program_ids: list[str],
        buffer_size: int = 1000,
        reconnect_delay: float = 5.0
    ):
        self.rpc_ws_url = rpc_ws_url
        self.program_ids = [Pubkey.from_string(pid) for pid in program_ids]
        self.buffer_size = buffer_size
        self.reconnect_delay = reconnect_delay
        
        self._buffer: list[LogEvent] = []
        self._running = False
        self._websocket: Optional[Any] = None
        self._subscription_id: Optional[int] = None
    
    async def _process_log(self, log_data: dict) -> None:
        """Обработка полученного лога."""
        try:
            event = LogEvent(
                signature=log_data.get("signature", ""),
                slot=log_data.get("slot", 0),
                program_id=log_data.get("programId", ""),
                data=log_data.get("data", [])
            )
            
            self._buffer.append(event)
            
            # Trim buffer if needed
            if len(self._buffer) > self.buffer_size:
                self._buffer = self._buffer[-self.buffer_size:]
            
            logger.info(f"Received event: {event.signature[:8]}... slot={event.slot}")
            
        except Exception as e:
            logger.error(f"Error processing log: {e}")
    
    async def _subscribe(self) -> None:
        """Подписка на логи."""
        if not self._websocket:
            return
            
        for program_id in self.program_ids:
            try:
                # Подписка на логи программы
                response = await self._websocket.logs_subscribe(
                    filter={"mentions": [str(program_id)]},
                    commitment="confirmed"
                )
                self._subscription_id = response.result
                logger.info(f"Subscribed to program: {program_id}")
            except Exception as e:
                logger.error(f"Subscription error for {program_id}: {e}")
    
    async def run(self, callback: Optional[Callable[[LogEvent], None]] = None) -> None:
        """
        Основной цикл инжестора.
        
        Args:
            callback: Функция для обработки каждого события
        """
        self._running = True
        
        while self._running:
            try:
                async with connect(self.rpc_ws_url) as ws:
                    self._websocket = ws
                    logger.info("Connected to Solana WebSocket")
                    
                    await self._subscribe()
                    
                    async for message in self._websocket:
                        if not self._running:
                            break
                            
                        try:
                            log_data = message.params.result.value
                            await self._process_log(log_data)
                            
                            if callback and self._buffer:
                                event = self._buffer.pop(0)
                                await asyncio.get_event_loop().run_in_executor(
                                    None, callback, event
                                )
                                
                        except Exception as e:
                            logger.error(f"Message processing error: {e}")
                            
            except Exception as e:
                logger.error(f"Connection error: {e}")
                if self._running:
                    logger.info(f"Reconnecting in {self.reconnect_delay}s...")
                    await asyncio.sleep(self.reconnect_delay)
    
    def stop(self) -> None:
        """Остановка инжестора."""
        self._running = False
        logger.info("Stopping ingester...")
    
    def get_buffer(self) -> list[LogEvent]:
        """Получение текущего буфера."""
        return self._buffer.copy()
    
    def clear_buffer(self) -> None:
        """Очистка буфера."""
        self._buffer.clear()


async def example_callback(event: LogEvent):
    """Пример callback-функции."""
    print(f"Callback received: {event.to_dict()}")


async def main():
    """Пример использования."""
    # Для тестирования используйте devnet или локальный узел
    ingester = SolanaLogIngester(
        rpc_ws_url="wss://api.devnet.solana.com",
        program_ids=["TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"],  # SPL Token Program
        buffer_size=100
    )
    
    try:
        await ingester.run(callback=example_callback)
    except KeyboardInterrupt:
        ingester.stop()


if __name__ == "__main__":
    asyncio.run(main())
