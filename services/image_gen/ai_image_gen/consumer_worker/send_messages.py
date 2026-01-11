import json
import os
import random
import time
import uuid

from config.kafka_config import create_kafka_producer, get_kafka_config

# Configuration
KAFKA_TOPICS = os.getenv("KAFKA_TOPICS", "sd15_tasks,flux_tasks,online_task").split(',')

def create_producer():
    """Creates and returns a KafkaProducer instance."""
    return create_kafka_producer(
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        api_version=(0, 10, 1)
    )

def generate_task_data(topic_name, loras = []):
    """Generates a sample task dictionary."""
    task_id = str(uuid.uuid4())
    
    # Default values
    model_name = "sdxl-turbo"
    prompt = f"A futuristic city at sunset, highly detailed, {task_id}"
    negative_prompt = "blurry, low quality"
    image_params = {"width": 512, "height": 512, "steps": 10, "cfg_scale": 2.0, "seed": -1, "batch_size": 1}
    # loras = []

    if "sdxl_tasks" in topic_name:
        model_name = "sdxl-turbo"
        prompt = f"A futuristic city at sunset, highly detailed, {task_id}"
        negative_prompt = "blurry, low quality"
        image_params = {"width": 512, "height": 512, "steps": 5, "cfg_scale": 2.0, "seed": -1, "batch_size": 1}
        loras = []
    elif "sd15_tasks" in topic_name:
        model_name = "sd15"
        prompt = f"A fantasy landscape, {task_id}"
        negative_prompt = "ugly, deformed"
        image_params = {"width": 512, "height": 512, "steps": 5, "cfg_scale": 7.0, "seed": -1, "batch_size": 1}
        loras = [{"name": "KoalaEngineV2a", "weight": 0.8}
]
    elif "flux_tasks" in topic_name:
        model_name = "flux"
        prompt = "A cyberpunk street scene with neon lights and rain, intricate details"
        negative_prompt = "cartoon, anime, low resolution"
        image_params = {
            "width": 512,
            "height": 512,
            "steps": 5,
            "cfg_scale": 6.0,
            "seed": -1, # Random seed
            "batch_size": 1
        }
        lora_name = random.choice(["中国老人人像-realistic,full view", "替嫁王妃"])
        #lora_name = random.choice(["替嫁王妃"])
        if lora_name == "中国老人人像-realistic,full view":
            prompt = f"realistic,full view there is an old chinese person standing on the right side of the screen. "
            negative_prompt=''
        elif lora_name == "替嫁王妃":  
            prompt = f"tijiawangfei, there is an person standing on the right side of the screen. "
            negative_prompt = ''
        # if not loras:
        #     loras = [
        #         {"name": lora_name, "weight": 1.2}
        #     ]

    elif "online_task" in topic_name:
        model_name = "flux" # Assuming online tasks use flux for this example
        prompt = f"An online request image,chinese woman  {task_id}"
        negative_prompt = "low quality"
        image_params = {"width": 768, "height": 768, "steps": 5, "cfg_scale": 5.0, "seed": -1, "batch_size": 1}
        #lora_name = random.choice(["擦边北岸纯欲性感脸模黛雅.beiansafetensors"])
        lora_name = random.choice([  "中国老人人像-realistic,full view"])
        # loras = [
        #     {"name": lora_name, "weight": 0.9}
        # ]

    # Assign a random priority (0 is highest, 10 is lowest for example)
    # The lower the number, the higher the priority
    priority = 0

    return {
        "task_id": task_id,
        "model_name": model_name,
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "image_params": image_params,
        "loras": loras,
        "priority": priority # Add priority to the task data
    }

def send_messages(num_messages=10):
    """Sends a specified number of messages to Kafka topics."""
    producer = create_producer()
    # if not producer:
    #     print("Failed to create Kafka producer. Exiting.")
    #     return

    # print(f"Sending {num_messages} messages to topics: {KAFKA_TOPICS}")
    # for i in range(num_messages):
    #     topic = random.choice(["sd15_tasks","flux_tasks"])
    #     task_data = generate_task_data(topic)
        
    #     future = producer.send(topic, task_data)
    #     record_metadata = future.get(timeout=10)
    #     print(f"Sent message {i+1}/{num_messages} to topic {record_metadata.topic} "
    #             f"partition {record_metadata.partition} offset {record_metadata.offset} "
    #             f"with task_id {task_data['task_id']} and priority {task_data['priority']}")

    #     #time.sleep(0.1) # Small delay between messages
    loras1 = [{"name": "国风绘本插图画风加强-guofeng", "weight": 1.0}]
    loras3 = [{"name": "国风绘本插图画风加强-guofeng", "weight": 1.2}]
    loras4 = [{"name": "国风绘本插图画风加强-guofeng", "weight": 0.8}]

    loras2 = [{"name": "中国老人人像-realistic,full view", "weight": 1.0}]
    loras5 = [{"name": "中国老人人像-realistic,full view", "weight": 1.2}]

    lora6 = []
    index = 1
    loralist = [loras4, loras5]
    for i in range(100):
        # loras = random.choice([lora6,loras2,loras5])
        topic = "flux_tasks"
        idx = index % 2
        loras = loralist[idx]
        index += 1
        task_data = generate_task_data(topic, loras)
        future = producer.send(topic, task_data)
        record_metadata = future.get(timeout=10)

        # 使用标准logging，因为这个模块可能被其他地方导入
        import logging
        logging.info(f"Sent message {i+1}/{num_messages} to topic {record_metadata.topic} "
                f"partition {record_metadata.partition} offset {record_metadata.offset} "
                f"with task_id {task_data['task_id']} and priority {task_data['priority']} loras {str(task_data['loras'])}")

        time.sleep(0.1) # Small delay between messages

    producer.flush()
    producer.close()
    import logging
    logging.info("Finished sending messages.")

if __name__ == "__main__":
    send_messages(num_messages=5) # Send 20 messages by default