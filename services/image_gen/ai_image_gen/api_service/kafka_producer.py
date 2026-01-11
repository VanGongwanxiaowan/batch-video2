# Kafka producer for sending image generation tasks
import json
import logging
import os

from config.kafka_config import (
    create_kafka_producer as _create_kafka_producer,  # Import the helper function
)
from config.settings import get_settings
from core.logging_config import setup_logging

logger = setup_logging("ai_image_gen.kafka_producer")

class KafkaProducer:
    def __init__(self):
        settings = get_settings()
        self.bootstrap_servers = settings.KAFKA_BOOTSTRAP_SERVERS
        self.producer = None
        self._connect_kafka()

    def _connect_kafka(self):
        try:
            self.producer = _create_kafka_producer(
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
            logger.info(f"Successfully connected to Kafka at {self.bootstrap_servers}")
        except (SystemExit, KeyboardInterrupt):
            # 系统退出异常，不捕获，直接抛出
            raise
        except Exception as e:
            # 其他异常（Kafka连接错误等）
            logger.error(f"[_connect_kafka] Failed to connect to Kafka: {e}", exc_info=True)
            self.producer = None # Ensure producer is None on failure

    async def send_message(self, topic: str, message: dict):
        """
        异步发送消息到 Kafka topic。
        
        Args:
            topic: Kafka topic 名称
            message: 要发送的消息字典
            
        Raises:
            ServiceUnavailableException: 当 Kafka producer 不可用时
            ServiceException: 当发送消息失败时
        """
        if not self.producer:
            logger.warning("Kafka producer not initialized. Attempting to reconnect...")
            self._connect_kafka()
            if not self.producer:
                error_msg = "Kafka producer not available. Message will not be sent."
                logger.error(error_msg)
                raise ServiceUnavailableException(
                    service_name="kafka_producer",
                    message=error_msg
                )

        try:
            # 使用异步方式发送，避免阻塞事件循环
            import asyncio
            loop = asyncio.get_event_loop()
            future = self.producer.send(topic, message)
            # 在线程池中执行同步操作
            record_metadata = await loop.run_in_executor(
                None, 
                lambda: future.get(timeout=10)
            )
            logger.info(
                f"Message sent to topic '{record_metadata.topic}' "
                f"partition {record_metadata.partition} "
                f"offset {record_metadata.offset}"
            )
        except (SystemExit, KeyboardInterrupt):
            # 系统退出异常，不捕获，直接抛出
            raise
        except Exception as e:
            # 其他异常（Kafka发送错误等）
            logger.error(f"[send_message] Failed to send message to Kafka topic {topic}: {e}", exc_info=True)
            raise ServiceException(
                f"Failed to send message to Kafka topic {topic}: {e}",
                service_name="kafka_producer"
            )

    def close(self):
        if self.producer:
            self.producer.close()
            logger.info("Kafka producer closed.")