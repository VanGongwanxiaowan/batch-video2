"""Kafka消费者Worker主逻辑"""
import asyncio
import json
import logging
import os
import threading
import time
from multiprocessing import Process, Queue

import httpx
from data_management.models import Task
from image_generator import ImageGenerator
from kafka import TopicPartition
from kafka.structs import OffsetAndMetadata
from model_manager import ModelManager

from config.kafka_config import create_kafka_consumer, get_kafka_config
from config.settings import get_settings
from core.config.constants import (
    ImageGenConfig,
    RetryConfig,
    TimeoutConfig,
    WorkerConfig,
)
from core.logging_config import setup_logging

logger = setup_logging("ai_image_gen.consumer_worker")

# Set logging level for kafka to WARNING to suppress INFO messages
logging.getLogger('kafka').setLevel(logging.WARNING)
logging.getLogger('kafka.coordinator.heartbeat').setLevel(logging.WARNING)
logging.getLogger('kafka.sasl.plain').setLevel(logging.ERROR)

class ConsumerWorker:
    def __init__(self):
        settings = get_settings()
        self.topics = settings.KAFKA_TOPICS.split(',') +  settings.PRIORITY_KAFKA_TOPICS.split(',')
        self.priority_topics = settings.PRIORITY_KAFKA_TOPICS.split(',')
        self.consumer_group_id = settings.KAFKA_CONSUMER_GROUP_ID
        self.bootstrap_servers = get_kafka_config()['bootstrap_servers']
        self.consumer = None
        self.que_dic = {k:Queue() for k in self.topics }
        self.commit_que = Queue()
        self.priority_consumer = None
        self.model_manager = ModelManager()
        self.image_generator = ImageGenerator(self.model_manager)
        self._connect_kafka()
        
        self.settings = get_settings()

    def _connect_kafka(self):

        self.consumer = create_kafka_consumer(
            group_id=self.consumer_group_id,
            client_id="gpu_worker_client",
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            api_version=(0, 10, 1),
            auto_offset_reset='earliest', # Start consuming from the earliest available message
            enable_auto_commit=False # Manual commit for better control
        ) 
        self.consumer.subscribe(self.topics)

        logger.info(f"Consumer connected to Kafka at {self.bootstrap_servers}, topics: {self.topics}, group: {self.consumer_group_id}")


    def start(self):
        """
        持续消费 Kafka 消息并将其添加到内部任务调度器。
        """
        logger.info("Starting Kafka message consumption...")

        # 启动任务处理进程
        task_process = Process(
            target=self._process_tasks_loop,
            args=(self.que_dic, self.commit_que, self.model_manager, self.image_generator, self.priority_topics)
        )
        task_process.start()
        logger.info("Task processing process started.")

        try:
            while True:
                # 主进程只负责 poll 消息
                try:
                    message = self.consumer.poll(timeout_ms=200, max_records=1)  # Poll one message at a time
                    if message:
                        self._handle_message(message)
                    else:
                        time.sleep(WorkerConfig.DEFAULT_POLL_SLEEP_SECONDS)  # 减少 CPU 占用
                except (SystemExit, KeyboardInterrupt):
                    # 系统退出异常，不捕获，直接抛出
                    raise
                except Exception as e:
                    # 其他异常（Kafka轮询错误等）
                    logger.error(f"[run] Error polling Kafka messages: {e}", exc_info=True)
                    time.sleep(WorkerConfig.DEFAULT_ERROR_SLEEP_SECONDS)  # 出错后等待更长时间

                # 主进程负责 commit 消息
                try:
                    while not self.commit_que.empty():
                        commit_info = self.commit_que.get()
                        topic_partition = commit_info['topic_partition']
                        offset_and_metadata = commit_info['offset_and_metadata']
                        self.consumer.commit({topic_partition: offset_and_metadata})
                        logger.debug(
                            f"Committed offset {offset_and_metadata.offset} "
                            f"for {topic_partition.topic}-{topic_partition.partition}"
                        )
                except (SystemExit, KeyboardInterrupt):
                    # 系统退出异常，不捕获，直接抛出
                    raise
                except Exception as e:
                    # 其他异常（Kafka提交错误等）
                    logger.error(f"[run] Error committing Kafka offset: {e}", exc_info=True)
        except (SystemExit, KeyboardInterrupt):
            logger.info("Received shutdown signal, stopping worker...")
            raise
        except Exception as e:
            # 其他异常（worker主循环错误等）
            logger.error(f"[run] Fatal error in worker main loop: {e}", exc_info=True)
            raise
        finally:
            # 清理资源
            logger.info("Cleaning up worker resources...")
            if task_process.is_alive():
                task_process.terminate()
                task_process.join(timeout=WorkerConfig.DEFAULT_PROCESS_JOIN_TIMEOUT_SECONDS)
                if task_process.is_alive():
                    logger.warning("Task process did not terminate gracefully, forcing kill...")
                    task_process.kill()
            if self.consumer:
                try:
                    self.consumer.close()
                except (SystemExit, KeyboardInterrupt):
                    # 系统退出异常，不捕获，直接抛出
                    raise
                except Exception as e:
                    # 其他异常（Kafka关闭错误等）
                    logger.error(f"[run] Error closing Kafka consumer: {e}", exc_info=True)
            logger.info("Worker shutdown complete.")

    def _handle_message(self, message):
        # import pdb
        # pdb.set_trace()
        for key, msgs in message.items():
            for msg in msgs:
                task_data = msg.value
                task_id = task_data.get("task_id")
                logger.info(f"Received task {task_id} from topic {msg.topic}, partition {msg.partition}, offset {msg.offset}")
                # 将消息放入对应的队列
                self.que_dic[msg.topic].put(msg)
                #logger.info(f"Task {task_id} added to queue for topic {msg.topic}")

        #


    def _process_tasks_loop(self, que_dic, commit_que, model_manager, image_generator, priority_topics):
        """
        在新进程中持续从任务队列中获取任务并进行处理。
        """
        # 在新进程中重新初始化数据库会话，因为SessionLocal不是线程安全的
        # 重新初始化 image_generator，确保模型加载在新进程中进行
        # 并且只加载一次
        local_image_generator = ImageGenerator(model_manager)
        logger.info("Task processing loop started in new process.")

        # 用于轮询非优先级队列的索引
        non_priority_topics = [t for t in que_dic.keys() if t not in priority_topics]
        current_non_priority_topic_idx = 0

        while True:
            task_processed_in_this_loop = False

            # 1. 优先处理优先级队列
            for topic in priority_topics:
                if not que_dic[topic].empty():
                    msg = que_dic[topic].get()
                    self._process_single_task(msg, commit_que, local_image_generator)
                    task_processed_in_this_loop = True
                    # 优先级队列有消息就一直处理，直到清空或没有更多优先级队列有消息
                    # 这里不break，继续检查下一个优先级队列

            # 2. 如果优先级队列没有消息，或者处理完所有优先级队列后，轮流处理非优先级队列
            if non_priority_topics:
                # 轮询非优先级队列
                topic_to_process = non_priority_topics[current_non_priority_topic_idx]
                
                processed_count = 0
                while not que_dic[topic_to_process].empty() and processed_count < 100:
                    # 在处理非优先级任务前，再次检查优先级队列
                    priority_task_found = False
                    for p_topic in priority_topics:
                        if not que_dic[p_topic].empty():
                            msg = que_dic[p_topic].get()
                            self._process_single_task(msg, commit_que, local_image_generator)
                            task_processed_in_this_loop = True
                            priority_task_found = True
                            break # 优先处理完一个优先级任务后，重新开始循环检查优先级队列
                    
                    if priority_task_found:
                        continue # 如果处理了优先级任务，跳过当前非优先级任务的处理，重新开始外层循环

                    # 如果没有优先级任务，则处理非优先级任务
                    msg = que_dic[topic_to_process].get()
                    self._process_single_task(msg, commit_que, local_image_generator)
                    processed_count += 1
                    task_processed_in_this_loop = True
                
                # 移动到下一个非优先级队列
                current_non_priority_topic_idx = (current_non_priority_topic_idx + 1) % len(non_priority_topics)

            if not task_processed_in_this_loop:
                time.sleep(WorkerConfig.DEFAULT_BUSY_WAIT_SLEEP_SECONDS)  # 短暂休眠以避免忙等待

    def _process_single_task(self, message, commit_que, image_generator):
        """
        处理单个任务，支持重试机制。
        """
        if not message:
            return

        topic = message.topic
        partition = message.partition
        offset = message.offset
        task_data = message.value
        task_id = task_data.get("task_id")
        model_name = task_data.get("model_name")
        loras = task_data.get("loras")
        prompt = task_data.get("prompt")
        negative_prompt = task_data.get("negative_prompt")
        image_params = task_data.get("image_params")

        logger.info(f"Processing task {task_id} with model {model_name} (Kafka: {topic}-{partition}-{offset})")

        image_path = None  # Initialize image_path to None
        error_message = None
        status = "failed"  # Default to failed, update to completed on success
        max_retries = RetryConfig.MAX_RETRIES
        retries = 0

        while retries < max_retries:
            try:
                image_path = image_generator.generate(
                    model_name, prompt, negative_prompt, image_params, loras
                )
                logger.info(f"Task {task_id} completed. Image path: {image_path}")
                status = "completed"
                break  # Exit retry loop on success
            except (SystemExit, KeyboardInterrupt):
                # 系统退出异常，不捕获，直接抛出
                raise
            except Exception as e:
                # 其他异常（图像生成错误等）
                retries += 1
                error_message = str(e)
                logger.error(f"[_process_task] Error generating image for task {task_id} (Attempt {retries}/{max_retries}): {e}",exc_info=True)
                if retries < max_retries:
                    # 指数退避，使用配置常量
                    delay = min(RetryConfig.BASE_DELAY_SECONDS ** retries, RetryConfig.MAX_DELAY_SECONDS)
                    time.sleep(delay)

        # Upload image to the API service or mark as failed
        api_base_url = self.settings.API_BASE_URL
        upload_success = False
        
        # 使用 httpx 客户端，设置超时和连接池
        timeout = httpx.Timeout(
            ImageGenConfig.DEFAULT_HTTP_TIMEOUT_SECONDS,
            connect=TimeoutConfig.DEFAULT_DATABASE_CONNECT_TIMEOUT
        )
        try:
            with httpx.Client(
                timeout=timeout,
                limits=httpx.Limits(
                    max_keepalive_connections=ImageGenConfig.DEFAULT_MAX_KEEPALIVE_CONNECTIONS,
                    max_connections=ImageGenConfig.DEFAULT_MAX_CONNECTIONS
                )
            ) as client:
                if status == "completed" and image_path:
                    upload_url = f"{api_base_url}/upload_image?task_id={task_id}"
                    try:
                        with open(image_path, "rb") as f:
                            files = {"image": (os.path.basename(image_path), f.read(), "image/png")}
                            response = client.post(upload_url, files=files)
                            response.raise_for_status()
                            logger.info(f"Image for task {task_id} successfully uploaded to API service.")
                            upload_success = True
                    except FileNotFoundError:
                        logger.error(f"Image file not found for task {task_id}: {image_path}")
                        error_message = f"Image file not found: {image_path}"
                        status = "failed"
                    except (SystemExit, KeyboardInterrupt):
                        # 系统退出异常，不捕获，直接抛出
                        raise
                    except (OSError, PermissionError, IOError) as file_error:
                        # 文件IO错误
                        logger.error(f"[_process_task] 文件IO错误 task_id={task_id}: {file_error}", exc_info=True)
                        error_message = f"Error reading image file: {file_error}"
                        status = "failed"
                    except Exception as file_error:
                        # 其他异常
                        logger.error(f"[_process_task] Error reading image file for task {task_id}: {file_error}", exc_info=True)
                        error_message = f"Error reading image file: {file_error}"
                        status = "failed"
                else:
                    # If generation failed or image_path is None, mark as failed in API service
                    upload_url = f"{api_base_url}/upload_image?task_id={task_id}"
                    if error_message:
                        # URL encode error message
                        import urllib.parse
                        upload_url += f"&error_message={urllib.parse.quote(error_message)}"
                    response = client.post(upload_url)  # No file to upload
                    response.raise_for_status()
                    logger.info(f"Task {task_id} marked as failed in API service with error: {error_message}")
                    upload_success = True
        except httpx.HTTPStatusError as e:
            logger.error(
                f"Failed to upload image for task {task_id} to API service: "
                f"{e.response.status_code} - {e.response.text}"
            )
            status = "failed"
            error_message = f"API upload failed: {e.response.status_code} - {e.response.text}"
        except httpx.TimeoutException as e:
            logger.error(f"Timeout uploading image for task {task_id} to API service: {e}")
            status = "failed"
            error_message = f"Upload timeout: {str(e)}"
        except httpx.RequestError as e:
            logger.error(f"Network error uploading image for task {task_id} to API service: {e}", exc_info=True)
            status = "failed"
            error_message = f"Network error: {str(e)}"
        except (SystemExit, KeyboardInterrupt):
            # 系统退出异常，不捕获，直接抛出
            raise
        except Exception as e:
            # 其他未预期的异常
            logger.error(f"[_process_task] Unexpected error uploading for task {task_id}: {e}", exc_info=True)
            status = "failed"
            error_message = f"Unexpected upload error: {str(e)}"
        
        # 清理临时文件（可选，根据需求决定是否保留）
        if image_path and os.path.exists(image_path):
            if upload_success:
                # 如果上传成功，可以选择删除临时文件
                # 注意：这里注释掉了删除操作，因为可能需要保留文件用于调试或后续处理
                # os.remove(image_path)
                logger.debug(f"Temporary image file {image_path} can be removed after successful upload.")
            else:
                logger.warning(f"Image file {image_path} not removed due to upload failure. Manual cleanup may be needed.")
        
        # Always commit the Kafka offset, even if upload failed
        # This ensures we don't reprocess the same message indefinitely
        try:
            commit_que.put({
                'topic_partition': TopicPartition(topic, partition),
                'offset_and_metadata': OffsetAndMetadata(offset + 1, None, message.leader_epoch)
            })
            logger.debug(f"Kafka offset commit queued for task {task_id}")
        except (SystemExit, KeyboardInterrupt):
            # 系统退出异常，不捕获，直接抛出
            raise
        except Exception as e:
            # 其他异常（Kafka offset提交错误等）
            logger.error(f"[_process_task] Failed to queue Kafka offset commit for task {task_id}: {e}", exc_info=True)

if __name__ == "__main__":
    # Example of how to run the worker
    # In a real deployment, this would be managed by Docker/Kubernetes
    worker = ConsumerWorker()
    worker.start()
