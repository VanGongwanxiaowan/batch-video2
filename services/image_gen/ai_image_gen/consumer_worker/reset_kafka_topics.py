import sys
import time
from pathlib import Path

from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import NoBrokersAvailable, TopicAlreadyExistsError, UnknownTopicOrPartitionError

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

# 添加项目根目录到Python路径
_project_root = Path(__file__).parent.parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from config.kafka_config import get_kafka_config
from config.settings import get_settings
from core.logging_config import setup_logging

# 配置日志
logger = setup_logging("image_gen.ai_image_gen.consumer_worker.reset_kafka_topics", log_to_file=False)

# Configuration
settings = get_settings()
kafka_config = get_kafka_config()
KAFKA_BOOTSTRAP_SERVERS = kafka_config['bootstrap_servers']
KAFKA_TOPICS = settings.KAFKA_TOPICS.split(',')  + [settings.PRIORITY_KAFKA_TOPICS]
NUM_PARTITIONS = 6
REPLICATION_FACTOR = 1 # For local development, 1 is usually fine

def create_admin_client(max_attempts=5, delay=5):
    """Creates and returns a KafkaAdminClient instance with retry logic."""
    for attempt in range(1, max_attempts + 1):
        admin_client = KafkaAdminClient(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            client_id='kafka-topic-resetter',
            security_protocol=kafka_config.get('security_protocol', 'PLAINTEXT'),
            sasl_mechanism=kafka_config.get('sasl_mechanism'),
            sasl_plain_username=kafka_config.get('sasl_plain_username'),
            sasl_plain_password=kafka_config.get('sasl_plain_password')
        )
        logger.info(f"KafkaAdminClient connected to {KAFKA_BOOTSTRAP_SERVERS} on attempt {attempt}")
        return admin_client

    logger.error(f"Failed to connect to Kafka after {max_attempts} attempts.")
    return None

def reset_topics():
    """Deletes and recreates specified Kafka topics."""
    admin_client = create_admin_client()
    if not admin_client:
        return

    logger.info(f"Attempting to reset Kafka topics: {KAFKA_TOPICS}")

    # 1. Delete topics
    logger.info("Deleting existing topics...")
    try:
        for topic in KAFKA_TOPICS:
            topics = [topic]
            result = admin_client.delete_topics(topics)
            logger.debug(f"Deletion initiated for topics: {result}")
            logger.info(f"Successfully initiated deletion for topics: {topics}")
        # Give Kafka some time to delete topics
        time.sleep(5) 
    except UnknownTopicOrPartitionError as e:
        logger.warning(f"Some topics did not exist, skipping deletion for those. {e}")
    except (SystemExit, KeyboardInterrupt):
        # 系统退出异常，不捕获，直接抛出
        raise
    except Exception as e:
        # 其他异常（Kafka删除topic错误等）
        logger.exception(f"[reset_kafka_topics] Error deleting topics: {e}")
        # If deletion fails, we might still try to create them if they don't exist

   

    # 2. Create topics
    logger.info("Creating new topics...")
    new_topics = [NewTopic(name=topic, num_partitions=NUM_PARTITIONS, replication_factor=REPLICATION_FACTOR)
                  for topic in KAFKA_TOPICS]
    try:
        admin_client.create_topics(new_topics, validate_only=False)
        logger.info(f"Successfully created topics with {NUM_PARTITIONS} partitions: {KAFKA_TOPICS}")
    except TopicAlreadyExistsError:
        logger.warning("Some topics already exist, skipping creation for those.")
    except (SystemExit, KeyboardInterrupt):
        # 系统退出异常，不捕获，直接抛出
        raise
    except Exception as e:
        # 其他异常（Kafka创建topic错误等）
        logger.exception(f"[reset_kafka_topics] Error creating topics: {e}")

    admin_client.close()

if __name__ == "__main__":
    reset_topics()