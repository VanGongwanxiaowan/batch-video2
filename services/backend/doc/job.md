# Job API Documentation

## 1. Create Job

- **Endpoint**: `POST /jobs`
- **Summary**: 创建任务 (Create Task)
- **Description**: 创建一个新的任务 (Create a new task)

### Request Parameters

- **Body**: `CreateJobRequest`
  - `title` (string, required): 任务标题 (Task title)
  - `content` (string, required): 任务内容 (Task content)
  - `language_id` (integer, optional): 语言ID (Language ID)
  - `voice` (string, required): 音色 (Voice)
  - `description` (string, required): 任务描述 (Task description)
  - `status` (string, optional, default: "待处理"): 任务状态 (Task status)
  - `status_detail` (string, required): 任务状态详情 (Task status detail)
  - `account_id` (integer, optional): 账号ID (Account ID)
  - `topic_id` (integer, optional): 话题ID (Topic ID)

### Response Parameters

- **Body**: `CreateJobResponse`
  - `id` (integer): 新增任务的ID (ID of the newly created task)

## 2. Get Job Details

- **Endpoint**: `GET /jobs/{job_id}`
- **Summary**: 获取指定任务的详细信息 (Get details of a specified task)
- **Description**: 获取指定任务的详细信息 (Get detailed information for a specified task)

### Request Parameters

- **Path**:
  - `job_id` (integer, required, minimum: 1): 任务ID (Task ID)

### Response Parameters

- **Body**: `Job`
  - `id` (integer): 任务ID (Task ID)
  - `title` (string): 任务标题 (Task title)
  - `content` (string): 任务内容 (Task content)
  - `language_id` (integer, optional): 语言ID (Language ID)
  - `language` (object, optional): 语言信息 (Language information)
    - `id` (integer)
    - `name` (string)
    - `platform` (string)
    - `language_name` (string)
    - `created_at` (string)
    - `updated_at` (string)
  - `voice` (string): 音色 (Voice)
  - `description` (string): 任务描述 (Task description)
  - `topic_id` (integer, optional): 话题ID (Topic ID)
  - `topic` (object, optional): 话题信息 (Topic information)
    - `id` (integer)
    - `name` (string)
    - `prompt_gen_image` (string)
    - `prompt_cover_image` (string)
    - `prompt_image_prefix` (string)
    - `prompt_l4` (string)
    - `created_at` (string)
    - `updated_at` (string)
  - `job_splits` (array of `JobSplit`): 任务分割信息 (Task split information)
    - `JobSplit`
      - `start` (integer): 开始时间 (Start time)
      - `end` (integer): 结束时间 (End time)
      - `text` (string): 文本内容 (Text content)
      - `prompt` (string, optional): 提示 (Prompt)
      - `image` (string, optional): 图片 (Image)
  - `status` (string): 任务状态 (Task status)
  - `status_detail` (string): 任务状态详情 (Task status detail)
  - `created_at` (string): 创建时间 (Creation timestamp, ISO format)
  - `updated_at` (string): 更新时间 (Last update timestamp, ISO format)
  - `account_id` (integer, optional): 账号ID (Account ID)

## 3. List Jobs

- **Endpoint**: `GET /jobs/list`
- **Summary**: 任务列表 (Task List)
- **Description**: 列出任务 (List tasks)

### Request Parameters

- **Query**:
  - `page` (integer, optional, default: 1, minimum: 1): 页码 (Page number)
  - `page_size` (integer, optional, default: 10, minimum: 1): 每页大小 (Page size)
  - `status` (string, optional, default: "待处理"): 任务状态 (Task status)
  - `account_id` (integer, optional): 账号ID (Filter by account ID)
  - `language_id` (integer, optional): 语言ID (Filter by language ID)

### Response Parameters

- **Body**: `ListJobResponse`
  - `total` (integer): 总记录数 (Total number of records)
  - `items` (array of `Job`): 任务列表 (List of tasks)
    - (See `Job` schema above for details)

## 4. Delete Job

- **Endpoint**: `DELETE /jobs/{job_id}`
- **Summary**: 删除指定任务 (Delete specified task)
- **Description**: 删除指定任务 (Delete a specified task)

### Request Parameters

- **Path**:
  - `job_id` (integer, required, minimum: 1): 任务ID (Task ID)

### Response Parameters

- **Body**: `CreateJobResponse` (Used for deletion confirmation)
  - `id` (integer): 被删除任务的ID (ID of the deleted task)

## 5. Update Job

- **Endpoint**: `PUT /jobs/{job_id}`
- **Summary**: 更新指定任务信息 (Update specified task information)
- **Description**: 更新指定任务 (Update a specified task)

### Request Parameters

- **Path**:
  - `job_id` (integer, required, minimum: 1): 任务ID (Task ID)
- **Body**: `Job`
  - (See `Job` schema above for details on request body)

### Response Parameters

- **Body**: `Job`
  - (See `Job` schema above for details on response body)

## 6. Export Job Video

- **Endpoint**: `POST /jobs/export/{job_id}`
- **Summary**: 导出任务视频 (Export task video)
- **Description**: 导出指定任务的视频 (Export video for a specified task)

### Request Parameters

- **Path**:
  - `job_id` (integer, required, minimum: 1): 任务ID (Task ID)

### Response Parameters

- **Body**: (Depends on the actual return type of `service.export_job`, typically a success message or a path to the exported video)
  - *Note: The exact structure of the response is not explicitly defined in the `api/jobs.py` file's `response_model` for this endpoint. It returns `result` directly from the service.*