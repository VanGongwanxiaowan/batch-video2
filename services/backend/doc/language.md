# Language API Documentation

## 1. Create Language

- **Endpoint**: `POST /language`
- **Summary**: 新增语种 (Add Language)
- **Description**: 新增一个语种 (Add a new language)

### Request Parameters

- **Body**: `CreateLanguageRequest`
  - `name` (string, required): 语种名称 (Language name)
  - `platform` (string, optional): 平台 (Platform)
  - `language_name` (string, optional): 语言名称 (e.g., "zh-CN", "en-US") (Language name)

### Response Parameters

- **Body**: `CreateLanguageResponse`
  - `id` (integer): 新增语种的ID (ID of the newly created language)

## 2. List Languages

- **Endpoint**: `GET /language/list`
- **Summary**: 语种列表 (Language List)
- **Description**: 列出语种 (List languages)

### Request Parameters

- **Query**:
  - `page` (integer, optional, default: 1, minimum: 1): 页码 (Page number)
  - `page_size` (integer, optional, default: 10, minimum: 1): 每页大小 (Page size)

### Response Parameters

- **Body**: `ListLanguageResponse`
  - `total` (integer): 总记录数 (Total number of records)
  - `items` (array of `Language`): 语种列表 (List of languages)
    - `Language`
      - `id` (integer): 语种ID (Language ID)
      - `name` (string): 语种名称 (Language name)
      - `platform` (string, optional): 平台 (Platform)
      - `language_name` (string, optional): 语言名称 (e.g., "zh-CN", "en-US") (Language name)
      - `created_at` (string): 创建时间 (Creation timestamp, ISO format)
      - `updated_at` (string): 更新时间 (Last update timestamp, ISO format)

## 3. Get Language Details

- **Endpoint**: `GET /language/{language_id}`
- **Summary**: 获取指定语种的详细信息 (Get details of a specified language)
- **Description**: 获取指定语种的详细信息 (Get detailed information for a specified language)

### Request Parameters

- **Path**:
  - `language_id` (integer, required, minimum: 1): 语种ID (Language ID)

### Response Parameters

- **Body**: `GetLanguageResponse` (inherits from `Language`)
  - `id` (integer): 语种ID (Language ID)
  - `name` (string): 语种名称 (Language name)
  - `platform` (string, optional): 平台 (Platform)
  - `language_name` (string, optional): 语言名称 (e.g., "zh-CN", "en-US") (Language name)
  - `created_at` (string): 创建时间 (Creation timestamp, ISO format)
  - `updated_at` (string): 更新时间 (Last update timestamp, ISO format)

## 4. Update Language

- **Endpoint**: `PUT /language/{language_id}`
- **Summary**: 更新语种信息 (Update Language Information)
- **Description**: 更新指定语种的信息 (Update information for a specified language)

### Request Parameters

- **Path**:
  - `language_id` (integer, required, minimum: 1): 语种ID (Language ID)
- **Body**: `UpdateLanguageRequest`
  - `name` (string, optional): 语种名称 (Language name)
  - `platform` (string, optional): 平台 (Platform)
  - `language_name` (string, optional): 语言名称 (e.g., "zh-CN", "en-US") (Language name)

### Response Parameters

- **Body**: `UpdateLanguageResponse`
  - `id` (integer): 更新语种的ID (ID of the updated language)

## 5. Delete Language

- **Endpoint**: `DELETE /language/{language_id}`
- **Summary**: 删除语种 (Delete Language)
- **Description**: 删除指定语种 (Delete a specified language)

### Request Parameters

- **Path**:
  - `language_id` (integer, required, minimum: 1): 语种ID (Language ID)

### Response Parameters

- **Body**: `DeleteLanguageResponse`
  - `id` (integer): 被删除语种的ID (ID of the deleted language)