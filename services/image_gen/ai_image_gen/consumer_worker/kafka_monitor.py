import json
import os
import sys
from pathlib import Path

from kafka import TopicPartition

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

# 添加项目根目录到Python路径
_project_root = Path(__file__).parent.parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import pickle

from config.kafka_config import create_kafka_consumer, get_kafka_config
from config.settings import get_settings
from core.logging_config import setup_logging

settings = get_settings()

# 配置日志
logger = setup_logging("image_gen.ai_image_gen.consumer_worker.kafka_monitor", log_to_file=False)
def get_kafka_topic_metrics():
    """
    Connects to Kafka, retrieves topic and partition information,
    and calculates total, processed, and unprocessed messages for each topic.
    """
    # Hardcoded topics and consumer group as per user's request
    kafka_topics = settings.KAFKA_TOPICS.split(',') + [settings.PRIORITY_KAFKA_TOPICS]#['common',"dall_e","open_ai","webpilot"]
    consumer_group_id =settings.KAFKA_CONSUMER_GROUP_ID# 'huace_group'

    logger.info(f"Connecting to Kafka using configured settings")
    logger.info(f"Monitoring topics: {kafka_topics}")
    logger.info(f"Using consumer group for lag calculation: {consumer_group_id}")

    metrics = {}

    # Create a consumer to get topic metadata and offsets
    # client_id is optional, but good practice
    consumer = create_kafka_consumer(
        topic_name=None, # Use assign() later
        group_id=consumer_group_id,
        client_id="kafka_monitor_client", # client_id is optional, but good practice
        enable_auto_commit=False, # We don't want this monitor to commit offsets
        auto_offset_reset='earliest', # Start from earliest if no committed offset
        consumer_timeout_ms=1000, # Timeout for consumer operations
        value_deserializer = lambda m: json.loads(m.decode('utf-8')) # Changed from pickle to json deserializer
    )

    # Ensure consumer is connected and has metadata
    consumer.topics()
    # Add a small poll to help the consumer instance initialize and synchronize
    consumer.poll(timeout_ms=100)

    for topic_name in kafka_topics:
        partitions = consumer.partitions_for_topic(topic_name)
        if not partitions:
            logger.warning(f"Topic '{topic_name}' not found.")
            metrics[topic_name] = {
                "total_messages": 0,
                "processed_messages": 0,
                "unprocessed_messages": 0,
                "details": "No partitions found"
            }
            continue

        logger.info(f"Topic '{topic_name}' has {len(partitions)} partitions.")
        topic_partitions = [TopicPartition(topic_name, p) for p in partitions]

        # Explicitly assign partitions to the consumer to ensure committed offsets are fetched
        consumer.assign(topic_partitions)
        # Poll briefly to allow the consumer to fetch committed offsets after assignment
        consumer.poll(timeout_ms=100)

        end_offsets = consumer.end_offsets(topic_partitions)

        for tp in topic_partitions:
            consumer_offset = consumer.committed(tp)
            end_offset = end_offsets.get(tp, 0) # Use .get with default 0

            # If no offset is committed, assume it's at the earliest for calculation
            earliest_offset = consumer.beginning_offsets([tp]).get(tp, 0)
            current_group_offset = consumer_offset if consumer_offset is not None else earliest_offset

            unconsumed_messages = end_offset - current_group_offset

            # Ensure non-negative count
            unconsumed_messages = max(0, unconsumed_messages)

            logger.debug(f"Partition: {tp.partition}, Consumer Offset: {consumer_offset}, End Offset: {end_offset}, Unconsumed Messages: {unconsumed_messages}")

        # No summary section as in the original snippet
        metrics[topic_name] = {
            "unconsumed_messages_total": sum(max(0, end_offsets.get(tp, 0) - (consumer.committed(tp) if consumer.committed(tp) is not None else consumer.beginning_offsets([tp]).get(tp, 0))) for tp in topic_partitions)
        }


    consumer.close()

    return metrics

if __name__ == "__main__":
    # The original snippet did not have a summary printout in the __main__ block,
    # so we remove the summary printout here to match the requested behavior.
    get_kafka_topic_metrics()