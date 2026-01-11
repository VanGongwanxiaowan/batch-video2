# Account API Documentation

## 1. Create Account

- **Endpoint**: `POST /accounts`
- **Summary**: 新增账号 (Add Account)
- **Description**: 新增一个账号 (Add a new account)

### Request Parameters

- **Body**: `CreateAccountRequest`
  - `username` (string, required): 账号名称 (Account name)
  - `logo` (string, optional, default: ""): 账号Logo (Account logo)
  - `area` (string, optional, default: ""): 区域 (Area)
  - `platform` (string, optional, default: "youtube"): 平台 (Platform)

### Response Parameters

- **Body**: `CreateAccountResponse`
  - `id` (integer): 新增账号的ID (ID of the newly created account)

## 2. List Accounts

- **Endpoint**: `GET /accounts/list`
- **Summary**: 账号列表 (Account List)
- **Description**: 列出账号 (List accounts)

### Request Parameters

- **Query**:
  - `page` (integer, optional, default: 1, minimum: 1): 页码 (Page number)
  - `page_size` (integer, optional, default: 10, minimum: 1): 每页大小 (Page size)

### Response Parameters

- **Body**: `ListAccountResponse`
  - `total` (integer): 总记录数 (Total number of records)
  - `items` (array of `Account`): 账号列表 (List of accounts)
    - `Account`
      - `id` (integer): 账号ID (Account ID)
      - `username` (string): 账号名称 (Account name)
      - `logo` (string): 账号Logo (Account logo)
      - `platform` (string): 平台 (Platform)
      - `area` (string): 区域 (Area)

## 3. Get Account Details

- **Endpoint**: `GET /accounts/{account_id}`
- **Summary**: 获取指定账号的详细信息 (Get details of a specified account)
- **Description**: ���取指定账号的详细信息 (Get detailed information for a specified account)

### Request Parameters

- **Path**:
  - `account_id` (integer, required, minimum: 1): 账号ID (Account ID)

### Response Parameters

- **Body**: `GetAccountResponse`
  - `id` (integer): 账号ID (Account ID)
  - `username` (string): 账号名称 (Account name)
  - `logo` (string): 账号Logo (Account logo)
  - `area` (string): 区域 (Area)
  - `created_at` (string): 创建时间 (Creation timestamp, ISO format)
  - `updated_at` (string): 更新时间 (Last update timestamp, ISO format)

## 4. Update Account

- **Endpoint**: `PUT /accounts/{account_id}`
- **Summary**: 更新账号信息 (Update Account Information)
- **Description**: 更新指定账号的信息 (Update information for a specified account)

### Request Parameters

- **Path**:
  - `account_id` (integer, required): 账号ID (Account ID)
- **Body**: `UpdateAccountRequest`
  - `username` (string, required): 账号名称 (Account name)
  - `logo` (string, optional, default: ""): 账号Logo (Account logo)
  - `area` (string, optional, default: ""): 区域 (Area)

### Response Parameters

- **Body**: `UpdateAccountResponse`
  - `id` (integer): 更新账号的ID (ID of the updated account)

## 5. Delete Account

- **Endpoint**: `DELETE /accounts/{account_id}`
- **Summary**: 删除账号 (Delete Account)
- **Description**: 删除指定账号 (Delete a specified account)

### Request Parameters

- **Path**:
  - `account_id` (integer, required): 账号ID (Account ID)

### Response Parameters

- **Body**: `DeleteAccountResponse`
  - `id` (integer): 被删除账号的ID (ID of the deleted account)