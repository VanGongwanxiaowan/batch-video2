# Topic API Documentation

## 1. Create Topic

- **Endpoint**: `POST /topics`
- **Summary**: 新增话题 (Add Topic)
- **Description**: 新增一个话题 (Add a new topic)

### Request Parameters

- **Body**: `CreateTopicRequest`
  - `name` (string, required): 话题名称 (Topic name)
  - `prompt_gen_image` (string, optional): 提示词L1 (Prompt L1)
  - `prompt_cover_image` (string, optional): 提示词L2 (Prompt L2)
  - `prompt_image_prefix` (string, optional): 提示词L3 (Prompt L3)
  - `prompt_l4` (string, optional): 提示词L4 (Prompt L4)

### Response Parameters

- **Body**: `CreateTopicResponse`
  - `id` (integer): 新增话题的ID (ID of the newly created topic)

## 2. Get Topic Details

- **Endpoint**: `GET /topics/{topic_id}`
- **Summary**: 获取指定话题的详细信息 (Get details of a specified topic)
- **Description**: 获取指定话题的详细信息 (Get detailed information for a specified topic)

### Request Parameters

- **Path**:
  - `topic_id` (integer, required, minimum: 1): 话题ID (Topic ID)

### Response Parameters

- **Body**: `GetTopicResponse` (inherits from `Topic`)
  - `id` (integer): 话题ID (Topic ID)
  - `name` (string): 话题名称 (Topic name)
  - `prompt_gen_image` (string, optional): 提示词L1 (Prompt L1)
  - `prompt_cover_image` (string, optional): 提示词L2 (Prompt L2)
  - `prompt_image_prefix` (string, optional): 提示词L3 (Prompt L3)
  - `prompt_l4` (string, optional): 提示词L4 (Prompt L4)
  - `created_at` (string): 创建时间 (Creation timestamp, ISO format)
  - `updated_at` (string): 更新时间 (Last update timestamp, ISO format)

## 3. List Topics

- **Endpoint**: `GET /topics/list`
- **Summary**: 话题列表 (Topic List)
- **Description**: 列出话题 (List topics)

### Request Parameters

- **Query**:
  - `page` (integer, optional, default: 1, minimum: 1): 页码 (Page number)
  - `page_size` (integer, optional, default: 10, minimum: 1): 每页大小 (Page size)

### Response Parameters

- **Body**: `ListTopicResponse`
  - `total` (integer): 总记录数 (Total number of records)
  - `items` (array of `Topic`): 话题列表 (List of topics)
    - `Topic`
      - `id` (integer): 话题ID (Topic ID)
      - `name` (string): 话题名称 (Topic name)
      - `prompt_gen_image` (string, optional): 提示词L1 (Prompt L1)
      - `prompt_cover_image` (string, optional): 提示词L2 (Prompt L2)
      - `prompt_image_prefix` (string, optional): 提示词L3 (Prompt L3)
      - `prompt_l4` (string, optional): 提示词L4 (Prompt L4)
      - `created_at` (string): 创建时间 (Creation timestamp, ISO format)
      - `updated_at` (string): 更新时间 (Last update timestamp, ISO format)

## 4. Update Topic

- **Endpoint**: `PUT /topics/{topic_id}`
- **Summary**: 更新话题信息 (Update Topic Information)
- **Description**: 更新指定话题的信息 (Update information for a specified topic)

### Request Parameters

- **Path**:
  - `topic_id` (integer, required, minimum: 1): 话题ID (Topic ID)
- **Body**: `UpdateTopicRequest`
  - `name` (string, optional): 话题名称 (Topic name)
  - `prompt_gen_image` (string, optional): 提示词L1 (Prompt L1)
  - `prompt_cover_image` (string, optional): 提示词L2 (Prompt L2)
  - `prompt_image_prefix` (string, optional): 提示词L3 (Prompt L3)
  - `prompt_l4` (string, optional): 提示词L4 (Prompt L4)

### Response Parameters

- **Body**: `UpdateTopicResponse`
  - `id` (integer): 更新话题的ID (ID of the updated topic)

## 5. Delete Topic

- **Endpoint**: `DELETE /topics/{topic_id}`
- **Summary**: 删除话题 (Delete Topic)
- **Description**: 删除指定话题 (Delete a specified topic)

### Request Parameters

- **Path**:
  - `topic_id` (integer, required, minimum: 1): 话题ID (Topic ID)

### Response Parameters

- **Body**: `DeleteTopicResponse`
  - `id` (integer): 被删除话题的ID (ID of the deleted topic)