import base64
import datetime
import hashlib
import hmac
import json
import os
import shutil
import urllib
import uuid
import warnings
from typing import Any, Dict, Iterator, List, Optional, Union

import oss2

__all__ = ["OssManager", "OssManagerError"]
IMAGE_FORMAT_SET = [
    "bmp",
    "jpg",
    "jpeg",
    "png",
    "tif",
    "gif",
    "pcx",
    "tga",
    "exif",
    "fpx",
    "svg",
    "psd",
    "cdr",
    "pcd",
    "dxf",
    "ufo",
    "eps",
    "ai",
    "raw",
    "WMF",
    "webp",
    "tiff",
]

OssManagerError = type("OssManagerError", (ValueError,), {})


warnings.warn(
    "The aliyun_oss module is deprecated", category=DeprecationWarning, stacklevel=2
)

from config import settings
from core.logging_config import setup_logging

logger = setup_logging("backend.ossutils", log_to_file=False)

class OssManager(object):
    acl_type = {
        "private": oss2.BUCKET_ACL_PRIVATE,
        "onlyread": oss2.BUCKET_ACL_PUBLIC_READ,
        "readwrite": oss2.BUCKET_ACL_PUBLIC_READ_WRITE,
    }
    # 存储类型
    storage_cls = {
        "standard": oss2.BUCKET_STORAGE_CLASS_STANDARD,  # 标准类型
        "ia": oss2.BUCKET_STORAGE_CLASS_IA,  # 低频访问类型
        "archive": oss2.BUCKET_STORAGE_CLASS_ARCHIVE,  # 归档类型
        "cold_archive": oss2.BUCKET_STORAGE_CLASS_COLD_ARCHIVE,  # 冷归档类型
    }
    # 冗余类型
    redundancy_type = {
        "lrs": oss2.BUCKET_DATA_REDUNDANCY_TYPE_LRS,  # 本地冗余
        "zrs": oss2.BUCKET_DATA_REDUNDANCY_TYPE_ZRS,  # 同城冗余（跨机房）
    }

    def __init__(self, **kwargs: Any) -> None:
        self.access_key_id = settings.OSS_ACCESS_KEY_ID
        self.access_key_secret = settings.OSS_ACCESS_KEY_SECRET
        self.bucket_name = settings.OSS_BUCKET_NAME
        # 安全：不再打印敏感信息，只记录bucket名称用于调试
        logger.debug(f"OssManager initialized with bucket: {self.bucket_name}")
        self.endpoint = settings.OSS_ENDPOINT
        # 初始化OSS客户端
        self.cache_path = "/data/_download_cache/"
        self.scheme = kwargs.get("scheme", "https")
        self.image_domain = kwargs.get("image_domain", "")
        self.asset_domain = kwargs.get("asset_domain", "")
        self.policy_expire_time = kwargs.get("policy_expire_time", 3600)

        self.cname = ""

        self.bucket = None
        self.__init()

    def __init(self, bucket_name: Optional[str] = None) -> None:
        """初始化对象
        
        Args:
            bucket_name: 存储桶名称，如果为None则使用配置中的名称
        """

        if oss2 is None:
            raise ImportError("'oss2' must be installed to use OssManager")
        if not any((self.endpoint, self.cname)):
            raise AttributeError("One of 'endpoint' and 'cname' must not be None.")

        self.auth = oss2.Auth(self.access_key_id, self.access_key_secret)

        # 如果cname存在，则使用自定义域名初始化
        self.endpoint = self.cname if self.cname else self.endpoint
        is_cname = True if self.cname else False
        self.bucket_name = bucket_name if bucket_name else self.bucket_name
        self.bucket = oss2.Bucket(
            self.auth, self.endpoint, self.bucket_name, is_cname=is_cname
        )

        if self.cache_path:
            try:
                os.makedirs(self.cache_path)
            except OSError:
                pass

    def delete_object(self, uploadkey: str) -> None:
        """删除OSS对象
        
        Args:
            uploadkey: 对象键
        """
        self.bucket.delete_object(uploadkey)

    def reload_oss(self, **kwargs: Any) -> None:
        """重新加载oss配置
        
        Args:
            **kwargs: OSS配置参数
        """
        self.access_key_id = kwargs.get("access_key_id")
        self.access_key_secret = kwargs.get("access_key_secret")
        self.bucket_name = kwargs.get("bucket_name")
        self.endpoint = kwargs.get("endpoint")
        self.__init()

    def create_bucket(
        self,
        bucket_name: Optional[str] = None,
        acl_type: str = "private",
        storage_type: str = "standard",
        redundancy_type: str = "zrs",
    ) -> Any:
        self.__init(bucket_name=bucket_name)
        permission = self.acl_type.get(acl_type)
        config = oss2.models.BucketCreateConfig(
            storage_class=self.storage_cls.get(storage_type),
            data_redundancy_type=self.redundancy_type.get(redundancy_type),
        )
        return self.bucket.create_bucket(permission, input=config)

    def iter_buckets(
        self, 
        prefix: str = "", 
        marker: str = "", 
        max_keys: int = 100, 
        max_retries: Optional[int] = None
    ) -> Iterator[Any]:
        """
        迭代列举Bucket
        
        Args:
            prefix: 只列举匹配该前缀的Bucket
            marker: 分页符。只列举Bucket名字典序在此之后的Bucket
            max_keys: 每次调用 `list_buckets` 时的max_keys参数。注意迭代器返回的数目可能会大于该值。
            max_retries: 最大重试次数
            
        Returns:
            Iterator: Bucket迭代器
        """
        if not hasattr(self, "service"):
            self.service = oss2.Service(self.auth, self.endpoint)

        return oss2.BucketIterator(
            self.service,
            prefix=prefix,
            marker=marker,
            max_keys=max_keys,
            max_retries=max_retries,
        )

    def list_buckets(
        self, 
        prefix: str = "", 
        marker: str = "", 
        max_keys: int = 100, 
        params: Optional[Dict[str, Any]] = None
    ) -> Any:
        """根据前缀罗列用户的Bucket。

        Args:
            prefix: 只罗列Bucket名为该前缀的Bucket，空串表示罗列所有的Bucket
            marker: 分页标志。首次调用传空串，后续使用返回值中的next_marker
            max_keys: 每次调用最多返回的Bucket数目
            params: list操作参数，传入'tag-key','tag-value'对结果进行过滤

        Returns:
            oss2.models.ListBucketsResult: 罗列的结果
        """
        if not hasattr(self, "service"):
            self.service = oss2.Service(self.auth, self.endpoint)
        return self.service.list_buckets(
            prefix=prefix, marker=marker, max_keys=max_keys, params=params
        )

    def is_exist_bucket(self) -> bool:
        """判断存储空间是否存在
        
        Returns:
            bool: 如果存在返回True，否则返回False
        """
        try:
            self.bucket.get_bucket_info()
        except oss2.exceptions.NoSuchBucket:
            return False
        except (SystemExit, KeyboardInterrupt):
            # 系统退出异常，不捕获，直接抛出
            raise
        except Exception:
            # 其他异常直接抛出
            raise
        return True

    def delete_bucket(self, bucket_name: Optional[str] = None) -> Any:
        """删除bucket
        
        Args:
            bucket_name: 存储桶名称，如果为None则使用当前bucket
            
        Returns:
            Any: 删除操作的响应结果
        """
        try:
            resp = self.bucket.delete_bucket()
            if resp.status < 300:
                return True
            elif resp.status == 404:
                return False
        except (SystemExit, KeyboardInterrupt):
            # 系统退出异常，不捕获，直接抛出
            raise
        except Exception as e:
            # 其他异常（OSS删除bucket错误等）
            import traceback

            # 记录异常但允许继续执行
            logger.error(f"[delete_bucket] Failed to delete bucket: {e}\n{traceback.format_exc()}")
            raise

    def encrypt_bucket(self) -> Any:
        """加密bucket
        
        Returns:
            Any: 加密操作的响应结果
        """
        # 创建Bucket加密配置，以AES256加密为例。
        rule = oss2.models.ServerSideEncryptionRule()
        rule.sse_algorithm = oss2.SERVER_SIDE_ENCRYPTION_AES256
        # 设置KMS密钥ID，加密方式为KMS可设置此项。
        # 如需使用指定的密钥加密，需输入指定的CMK ID；
        # 若使用OSS托管的CMK进行加密，此项为空。使用AES256进行加密时，此项必须为空。
        rule.kms_master_keyid = ""

        # 设置Bucket加密。
        result = self.bucket.put_bucket_encryption(rule)
        # 记录HTTP返回码
        logger.info(f"Bucket encryption set, HTTP response code: {result.status}")
        return result

    def delete_encrypt_bucket(self) -> Any:
        """删除Bucket加密配置
        
        Returns:
            Any: 删除操作的响应结果
        """
        result = self.bucket.delete_bucket_encryption()
        # 记录HTTP返回码
        logger.info(f"Bucket encryption deleted, HTTP status: {result.status}")
        return result

    def get_sign_url(self, key: str, expire: int = 7200) -> str:
        """获取GET签名URL
        
        Args:
            key: 对象键
            expire: 过期时间（秒）
            
        Returns:
            str: 签名URL
        """
        return self.bucket.sign_url("GET", key, expire)

    def post_sign_url(self, key: str, expire: int = 7200) -> str:
        """获取POST签名URL
        
        Args:
            key: 对象键
            expire: 过期时间（秒）
            
        Returns:
            str: 签名URL
        """
        return self.bucket.sign_url("POST", key, expire)

    def delete_cache_file(self, filename: str) -> None:
        """删除文件缓存
        
        Args:
            filename: 文件名
        """
        filepath = os.path.abspath(os.path.join(self.cache_path, filename))
        assert os.path.isfile(filepath), "非文件或文件不存在"
        os.remove(filepath)

    def search_cache_file(self, filename: str) -> Optional[str]:
        """文件缓存搜索
        
        Args:
            filename: 文件名
            
        Returns:
            Optional[str]: 如果文件存在返回文件路径，否则返回None
        """
        # 拼接绝对路径
        filepath = os.path.abspath(os.path.join(self.cache_path, filename))
        if os.path.isfile(filepath):
            return filepath
        else:
            return None

    def download(
        self, 
        key: str, 
        local_name: Optional[str] = None, 
        process: Optional[Any] = None, 
        is_stream: bool = False
    ) -> Union[str, Any]:
        """
        下载oss文件

        :param key:
        :param local_name:
        :param process:
        :param is_stream:
            is_stream = True:
                >>> result = self.download('readme.txt', is_stream=True)
                >>> print(result.read())
                'hello world'
            is_stream = False:
                >>> result = self.download('readme.txt', '/tmp/cache/readme.txt')
                >>> print(result)
                '/tmp/cache/readme.txt'
        :return:
        """
        if not local_name:
            local_name = os.path.abspath(os.path.join(self.cache_path, key))
        make_dir(os.path.dirname(local_name))
        if is_stream:
            return self.bucket.get_object(key, process=process)
        else:
            self.bucket.get_object_to_file(key, local_name, process=process)
            return local_name

    def upload(
        self, 
        filepath: str, 
        key: Optional[str] = None, 
        num_threads: int = 2
    ) -> str:
        """上传oss文件
        
        Args:
            filepath: 本地文件路径
            key: OSS对象键，如果为None则使用文件名
            num_threads: 上传线程数
            
        Returns:
            str: 文件URL
        """
        if key is None:
            key = filepath.split("/")[-1]
        headers = None
        if filepath.endswith(".dds"):
            headers = dict()
            headers["Content-Type"] = "application/octet-stream"

        result = oss2.resumable_upload(
            self.bucket,
            key,
            filepath,
            headers=headers,
            num_threads=num_threads,
        )
        # 返回下载链接
        if not any((self.image_domain, self.asset_domain)):
            return result.resp.response.url
        return self.get_file_url(filepath, key)
    
    def upload_data(
        self, 
        data: Union[bytes, bytearray], 
        key: str, 
        num_threads: int = 2
    ) -> str:
        """上传数据到OSS
        
        Args:
            data: 要上传的数据（字节）
            key: OSS对象键
            num_threads: 上传线程数
            
        Returns:
            str: 文件URL
        """
        import tempfile
        with tempfile.NamedTemporaryFile() as f:
            f.write(data)
            f.flush()
            headers = None
            result = oss2.resumable_upload(
                self.bucket,
                key,
                f.name,
                num_threads=num_threads,
                headers=headers,
            )
            # 返回下载链接
            if not any((self.image_domain, self.asset_domain)):
                return result.resp.response.url
            return self.get_file_url(f.name, key)
                
    def get_policy(
        self,
        filepath: str,
        callback_url: str,
        callback_data: Optional[Dict[str, Any]] = None,
        callback_content_type: str = "application/json",
    ) -> Dict[str, str]:
        """
        授权给第三方上传

        Args:
            filepath: 文件路径
            callback_url: 回调URL
            callback_data: 需要回传的参数
            callback_content_type: 回调时的Content-Type
                   "application/json"
                   "application/x-www-form-urlencoded"

        Returns:
            Dict[str, str]: 包含上传策略的字典
        """
        params = urllib.parse.urlencode(dict(data=json.dumps(callback_data)))
        policy_encode = self._get_policy_encode(filepath)
        sign = self.get_signature(policy_encode)

        callback_dict = dict()
        callback_dict["callbackUrl"] = callback_url
        callback_dict["callbackBody"] = (
            "filepath=${object}&size=${size}&mime_type=${mimeType}"
            "&img_height=${imageInfo.height}&img_width=${imageInfo.width}"
            "&img_format=${imageInfo.format}&" + params
        )
        callback_dict["callbackBodyType"] = callback_content_type

        callback_param = json.dumps(callback_dict).strip().encode()
        base64_callback_body = base64.b64encode(callback_param)

        return dict(
            accessid=self.access_key_id,
            host=f"{self.scheme}://{self.bucket_name}.{self.endpoint}",
            policy=policy_encode.decode(),
            signature=sign,
            dir=filepath,
            filename=uuid.uuid4().hex,
            callback=base64_callback_body.decode(),
        )

    def _get_policy_encode(self, filepath: str) -> bytes:
        """获取策略编码
        
        Args:
            filepath: 文件路径
            
        Returns:
            bytes: Base64编码的策略
        """
        expire_time = datetime.datetime.now() + datetime.timedelta(
            seconds=self.policy_expire_time
        )
        policy_dict = dict(
            expiration=expire_time.isoformat() + "Z",
            conditions=[
                ["starts-with", "$key", filepath],  # 指定值开始
                # ["eq", "$success_action_redirect", "public-read"],  # 精确匹配
                ["content-length-range", 1, 1024*1024*1024*5]         # 对象大小限制
            ],
        )
        policy = json.dumps(policy_dict).strip().encode()
        return base64.b64encode(policy)

    def get_signature(self, policy_encode: bytes) -> str:
        """
        获取签名

        Args:
            policy_encode: Base64编码的策略
            
        Returns:
            str: 签名字符串
        """
        h = hmac.new(
            self.access_key_secret.encode("utf-8"), policy_encode, hashlib.sha1
        )
        sign_result = base64.encodebytes(h.digest()).strip()
        return sign_result.decode()

    def get_file_url(self, filepath: str, key: str) -> str:
        """获取文件URL
        
        Args:
            filepath: 文件路径
            key: OSS对象键
            
        Returns:
            str: 文件URL
        """
        if filepath.split(".")[-1] in IMAGE_FORMAT_SET:
            resource_url = "//{domain}/{key}".format(domain=self.image_domain, key=key)
        else:
            resource_url = "//{domain}/{key}".format(domain=self.asset_domain, key=key)
        return resource_url

    def update_file_headers(self, key: str, headers: Dict[str, str]) -> None:
        """更新文件头信息
        
        Args:
            key: OSS对象键
            headers: 头信息字典
        """
        self.bucket.update_object_meta(key, headers)


    def list_objices(self, key: str) -> List[Any]:
        """列出文件
        
        Args:
            key: 对象键前缀
            
        Returns:
            List[Any]: 对象列表
        """
        return self.bucket.list_objects(key)

def make_dir(dir_path: str) -> None:
    """新建目录
    
    Args:
        dir_path: 目录路径
    """
    try:
        os.makedirs(dir_path)
    except OSError:
        pass


def copy_file(src: str, dst: str) -> None:
    """拷贝文件
    
    Args:
        src: 源文件路径
        dst: 目标文件路径
    """
    dst_dir = os.path.dirname(dst)
    make_dir(dst_dir)
    shutil.copy(src, dst)
