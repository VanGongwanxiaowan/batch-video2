# API Documentation

This document provides an overview of the available API endpoints.

## Account API

### 1. Create Account
- **Endpoint**: `POST /account`
- **Summary**: 新增账号 (Add Account)
- **Description**: 新增一个账号 (Add a new account)

### 2. List Accounts
- **Endpoint**: `GET /account/list`
- **Summary**: 账号列表 (Account List)
- **Description**: 列出账号 (List accounts)

### 3. Get Account Details
- **Endpoint**: `GET /account/{account_id}`
- **Summary**: 获取指定账号的详细信息 (Get details of a specified account)
- **Description**: 获取指定账号的详细信息 (Get detailed information for a specified account)

### 4. Update Account
- **Endpoint**: `PUT /account/{account_id}`
- **Summary**: 更新账号信息 (Update Account Information)
- **Description**: 更新指定账号的信息 (Update information for a specified account)

### 5. Delete Account
- **Endpoint**: `DELETE /account/{account_id}`
- **Summary**: 删除账号 (Delete Account)
- **Description**: 删除指定账号 (Delete a specified account)

## Job API

### 1. Create Job
- **Endpoint**: `POST /job`
- **Summary**: 创建任务 (Create Task)
- **Description**: 创建一个新的任务 (Create a new task)

### 2. Get Job Details
- **Endpoint**: `GET /job/{job_id}`
- **Summary**: 获取指定任务的详细信息 (Get details of a specified task)
- **Description**: 获取指定任务的详细信息 (Get detailed information for a specified task)

### 3. List Jobs
- **Endpoint**: `GET /job/list`
- **Summary**: 任务列表 (Task List)
- **Description**: 列出任务 (List tasks)

### 4. Delete Job
- **Endpoint**: `DELETE /job/{job_id}`
- **Summary**: 删除指定任务 (Delete specified task)
- **Description**: 删除指定任务 (Delete a specified task)

### 5. Update Job
- **Endpoint**: `PUT /job/{job_id}`
- **Summary**: 更新指定任务信息 (Update specified task information)
- **Description**: 更新指定任务 (Update a specified task)

### 6. Export Job Video
- **Endpoint**: `POST /job/export/{job_id}`
- **Summary**: 导出任务视频 (Export task video)
- **Description**: 导出指定任务的视频 (Export video for a specified task)

## Language API

### 1. Create Language
- **Endpoint**: `POST /language`
- **Summary**: 新增语种 (Add Language)
- **Description**: 新增一个语种 (Add a new language)

### 2. List Languages
- **Endpoint**: `GET /language/list`
- **Summary**: 语种列表 (Language List)
- **Description**: 列出语种 (List languages)

### 3. Get Language Details
- **Endpoint**: `GET /language/{language_id}`
- **Summary**: 获取指定语种的详细信息 (Get details of a specified language)
- **Description**: 获取指定语种的详细信息 (Get detailed information for a specified language)

### 4. Update Language
- **Endpoint**: `PUT /language/{language_id}`
- **Summary**: 更新语种信息 (Update Language Information)
- **Description**: 更新指定语种的信息 (Update information for a specified language)

### 5. Delete Language
- **Endpoint**: `DELETE /language/{language_id}`
- **Summary**: 删除语种 (Delete Language)
- **Description**: 删除指定语种 (Delete a specified language)

## Topic API

### 1. Create Topic
- **Endpoint**: `POST /topic`
- **Summary**: 新增话题 (Add Topic)
- **Description**: 新增一个话题 (Add a new topic)

### 2. Get Topic Details
- **Endpoint**: `GET /topic/{topic_id}`
- **Summary**: 获取指定话题的详细信息 (Get details of a specified topic)
- **Description**: 获取指定话题的详细信息 (Get detailed information for a specified topic)

### 3. List Topics
- **Endpoint**: `GET /topic/list`
- **Summary**: 话题列表 (Topic List)
- **Description**: 列出话题 (List topics)

### 4. Update Topic
- **Endpoint**: `PUT /topic/{topic_id}`
- **Summary**: 更新话题信息 (Update Topic Information)
- **Description**: 更新指定话题的信息 (Update information for a specified topic)

### 5. Delete Topic
- **Endpoint**: `DELETE /topic/{topic_id}`
- **Summary**: 删除话题 (Delete Topic)
- **Description**: 删除指定话题 (Delete a specified topic)

## Voice API

### 1. Create Voice
- **Endpoint**: `POST /voice`
- **Summary**: 创建音色 (Create Voice)
- **Description**: 创建一个新的音色 (Create a new voice)

### 2. Get Voice Details
- **Endpoint**: `GET /voice/{voice_id}`
- **Summary**: 获取指定音色的详细信息 (Get details of a specified voice)
- **Description**: 获取指定音色的详细信息 (Get detailed information for a specified voice)

### 3. List Voices
- **Endpoint**: `GET /voice/list`
- **Summary**: 音色列表 (Voice List)
- **Description**: 列出音色 (List voices)

### 4. Delete Voice
- **Endpoint**: `DELETE /voice/{voice_id}`
- **Summary**: 删除指定音色 (Delete specified voice)
- **Description**: 删除指定音色 (Delete a specified voice)