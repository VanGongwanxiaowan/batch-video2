import json
import logging
import sys
import time
from pathlib import Path

from kafka import TopicPartition
from kafka.structs import OffsetAndMetadata

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

# Add the parent directory to the sys.path to allow importing config
from config.kafka_config import create_kafka_consumer
from config.settings import get_settings
from core.logging_config import setup_logging

logger = setup_logging("ai_image_gen.consumer_all")

# Set logging level for kafka to WARNING to suppress INFO messages
logging.getLogger('kafka').setLevel(logging.WARNING)
logging.getLogger('kafka.coordinator.heartbeat').setLevel(logging.WARNING)
logging.getLogger('kafka.sasl.plain').setLevel(logging.ERROR)

class AllMessageConsumer:
    def __init__(self):
        settings = get_settings()
        # Combine all topics from settings
        self.topics = settings.KAFKA_TOPICS.split(',') + settings.PRIORITY_KAFKA_TOPICS.split(',')
        self.consumer_group_id = settings.KAFKA_CONSUMER_GROUP_ID + "_all_consumer" # Use a distinct group ID
        self.bootstrap_servers = settings.KAFKA_BOOTSTRAP_SERVERS
        self.consumer = None
        self._connect_kafka()

    def _connect_kafka(self):
        self.consumer = create_kafka_consumer(
            group_id=self.consumer_group_id,
            client_id="all_message_consumer_client",
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            api_version=(0, 10, 1),
            auto_offset_reset='earliest', # Start consuming from the earliest available message
            enable_auto_commit=False # Manual commit for better control
        ) 
        self.consumer.subscribe(self.topics)
        logger.info(f"AllMessageConsumer connected to Kafka at {self.bootstrap_servers}, topics: {self.topics}, group: {self.consumer_group_id}")

    def start(self):
        logger.info("Starting consumption of all Kafka messages (no processing logic)...")
        while True:
            messages = self.consumer.poll(timeout_ms=1000, max_records=500) # Poll multiple messages
            if messages:
                total_consumed = 0
                offsets_to_commit = {}
                for topic_partition, msgs in messages.items():
                    logger.debug(f"Consuming messages from topic {topic_partition.topic}, partition {topic_partition.partition}, offset {topic_partition.offset}")
                    for msg in msgs:
                        # No processing logic, just log and prepare for commit
                        logger.info(f"Consumed message from topic {msg.topic}, partition {msg.partition}, offset {msg.offset}")
                        # Store the offset to commit for this topic-partition
                        offsets_to_commit[topic_partition] = OffsetAndMetadata(msg.offset + 1, None, msg.leader_epoch)
                        total_consumed += 1
                
                if offsets_to_commit:
                    self.consumer.commit(offsets_to_commit)
                    logger.info(f"Processed and committed {total_consumed} messages.")
            else:
                logger.info("No new messages available, waiting...")
                time.sleep(5) # Wait longer if no messages to reduce CPU usage

if __name__ == "__main__":
    consumer = AllMessageConsumer()
    consumer.start()