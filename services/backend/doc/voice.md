# Voice API Documentation

## 1. Create Voice

- **Endpoint**: `POST /voice`
- **Summary**: 创建音色 (Create Voice)
- **Description**: 创建一个新的音色 (Create a new voice)

### Request Parameters

- **Body**: `CreateVoiceRequest`
  - `name` (string, required): 音色名称 (Voice name)
  - `path` (string, required): 音色路径 (Voice path)

### Response Parameters

- **Body**: `CreateVoiceResponse`
  - `id` (integer): 新增音色的ID (ID of the newly created voice)

## 2. Get Voice Details

- **Endpoint**: `GET /voice/{voice_id}`
- **Summary**: 获取指定音色的详细信息 (Get details of a specified voice)
- **Description**: 获取指定音色的详细信息 (Get detailed information for a specified voice)

### Request Parameters

- **Path**:
  - `voice_id` (integer, required, minimum: 1): 音色ID (Voice ID)

### Response Parameters

- **Body**: `Voice`
  - `id` (integer): 音色ID (Voice ID)
  - `name` (string): 音色名称 (Voice name)
  - `path` (string): 音色路径 (Voice path)
  - `created_at` (string): 创建时间 (Creation timestamp, ISO format)
  - `updated_at` (string): 更新时间 (Last update timestamp, ISO format)

## 3. List Voices

- **Endpoint**: `GET /voice/list`
- **Summary**: 音色列表 (Voice List)
- **Description**: 列出音色 (List voices)

### Request Parameters

- **Query**:
  - `page` (integer, optional, default: 1, minimum: 1): 页码 (Page number)
  - `page_size` (integer, optional, default: 10, minimum: 1): 每页大小 (Page size)

### Response Parameters

- **Body**: `ListVoiceResponse`
  - `total` (integer): 总记录��� (Total number of records)
  - `items` (array of `Voice`): 音色列表 (List of voices)
    - `Voice`
      - `id` (integer): 音色ID (Voice ID)
      - `name` (string): 音色名称 (Voice name)
      - `path` (string): 音色路径 (Voice path)
      - `created_at` (string): 创建时间 (Creation timestamp, ISO format)
      - `updated_at` (string): 更新时间 (Last update timestamp, ISO format)

## 4. Delete Voice

- **Endpoint**: `DELETE /voice/{voice_id}`
- **Summary**: 删除指定音色 (Delete specified voice)
- **Description**: 删除指定音色 (Delete a specified voice)

### Request Parameters

- **Path**:
  - `voice_id` (integer, required, minimum: 1): 音色ID (Voice ID)

### Response Parameters

- **Body**: `DeleteVoiceResponse`
  - `id` (integer): 被删除音色的ID (ID of the deleted voice)