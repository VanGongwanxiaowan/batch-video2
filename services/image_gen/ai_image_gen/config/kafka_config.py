from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError

from config.settings import get_settings
from core.logging_config import setup_logging

logger = setup_logging("ai_image_gen.kafka_config")

def get_kafka_config():
    """
    Retrieves Kafka configuration from settings.
    
    Returns:
        dict: Kafka 配置字典
    """
    settings = get_settings()
    
    config = {
        'bootstrap_servers': settings.KAFKA_BOOTSTRAP_SERVERS,
        'security_protocol': settings.KAFKA_SECURITY_PROTOCOL,
    }
    logger.debug(f"Kafka config (without credentials): bootstrap_servers={config['bootstrap_servers']}, security_protocol={config['security_protocol']}")

    if settings.KAFKA_USERNAME and settings.KAFKA_PASSWORD:
        config['sasl_mechanism'] = settings.KAFKA_SASL_MECHANISM
        config['sasl_plain_username'] = settings.KAFKA_USERNAME
        config['sasl_plain_password'] = settings.KAFKA_PASSWORD
    
    return config

def create_kafka_consumer(topic_name=None, group_id=None, **kwargs):
    """
    Creates and returns a KafkaConsumer instance with configured connection details.
    """
    config = get_kafka_config()
    
    consumer_config = {
        'bootstrap_servers': config['bootstrap_servers'],
        'security_protocol': config['security_protocol'],
        # 'session_timeout_ms': 180000,          # 2 分钟，给予一些处理裕度
        # 'heartbeat_interval_ms': 30000,         # 30 秒，确保在 session_timeout_ms 内有足够心跳
        # 'max_poll_interval_ms': 360000,         # 6 分钟，必须大于消息处理最长时间，且大于 session_timeout_ms
        # 'request_timeout_ms': 365000,        
        **kwargs
    }

    if 'sasl_mechanism' in config:
        consumer_config['sasl_mechanism'] = config['sasl_mechanism']
        consumer_config['sasl_plain_username'] = config['sasl_plain_username']
        consumer_config['sasl_plain_password'] = config['sasl_plain_password']

    if group_id:
        consumer_config['group_id'] = group_id
    logger.debug(f"Creating Kafka consumer with topic={topic_name}, group_id={group_id}")
    logger.debug(f"Consumer config (without credentials): { {k: v for k, v in consumer_config.items() if 'password' not in k.lower()} }")
    consumer = KafkaConsumer(**consumer_config)
    # Removed consumer.subscribe(topic_name) as the caller (kafka_monitor) will handle subscription/assignment
    return consumer

def create_kafka_producer(**kwargs):
    """
    Creates and returns a KafkaProducer instance with configured connection details.
    """
    config = get_kafka_config()

    producer_config = {
        'bootstrap_servers': config['bootstrap_servers'],
        'security_protocol': config['security_protocol'],
        **kwargs
    }

    if 'sasl_mechanism' in config:
        producer_config['sasl_mechanism'] = config['sasl_mechanism']
        producer_config['sasl_plain_username'] = config['sasl_plain_username']
        producer_config['sasl_plain_password'] = config['sasl_plain_password']

    try:
        producer = KafkaProducer(**producer_config)
        logger.debug("Kafka producer created successfully")
        return producer
    except KafkaError as e:
        logger.error(f"Error creating Kafka producer: {e}", exc_info=True)
        raise
