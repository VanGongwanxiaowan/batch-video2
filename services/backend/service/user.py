"""用户服务模块。

提供用户的创建、查询、认证等业务逻辑。
遵循单一职责原则，只负责用户相关的业务逻辑。
"""
import sys
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

# 添加项目根目录到Python路径
_project_root = Path(__file__).parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from db.models import User, get_beijing_time  # noqa: E402
from schema.account import UserCreate, UserLogin, UserSync  # noqa: E402

from core.db.dao.user_dao import UserDAO  # noqa: E402
from core.exceptions import ValidationException  # noqa: E402
from core.utils.password import hash_password, verify_password  # noqa: E402


class UserService:
    """用户服务类，负责处理用户相关的业务逻辑。
    
    提供用户的创建、查询、认证等功能。
    遵循单一职责原则，只负责用户相关的业务逻辑。
    
    Attributes:
        db: 数据库会话对象
        user_dao: 用户数据访问对象
    """
    
    def __init__(self, db: Session) -> None:
        """初始化用户服务。
        
        Args:
            db: 数据库会话对象
        """
        self.db = db
        self.user_dao = UserDAO(db)
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户。
        
        Args:
            username: 用户名
            
        Returns:
            Optional[User]: 用户对象，如果不存在返回None
        """
        return self.user_dao.get_by_username(username)
    
    def create_user(self, user: UserCreate) -> User:
        """创建新用户。
        
        Args:
            user: 用户创建请求对象
            
        Returns:
            User: 创建的用户对象
            
        Raises:
            ValidationException: 如果用户名已存在
            
        Note:
            密码会自动使用bcrypt进行哈希处理
        """
        # 检查用户名是否已存在
        existing_user = self.get_user_by_username(user.username)
        if existing_user:
            raise ValidationException(
                f"Username already exists: {user.username}",
                field="username"
            )
        
        hashed_password = hash_password(user.password)
        db_user = User(username=user.username, password=hashed_password)
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user
    
    def sync_user(self, user: UserSync) -> User:
        """同步用户（创建或更新用户）。
        
        Args:
            user: 用户同步请求对象，包含user_id
            
        Returns:
            User: 同步后的用户对象
            
        Note:
            密码会自动使用bcrypt进行哈希处理
            如果用户已存在（通过user_id），则更新；否则创建新用户
        """
        hashed_password = hash_password(user.password)
        
        # 检查是否已存在（通过user_id）
        existing_user = self.user_dao.get(user.id) if user.id else None
        
        if existing_user:
            # 更新现有用户
            existing_user.username = user.username
            existing_user.password = hashed_password
            self.db.commit()
            self.db.refresh(existing_user)
            return existing_user
        else:
            # 创建新用户
            db_user = User(
                username=user.username,
                password=hashed_password,
                user_id=user.id
            )
            self.db.add(db_user)
            self.db.commit()
            self.db.refresh(db_user)
            return db_user
    
    def authenticate_user(self, user: UserLogin) -> User:
        """验证用户身份。
        
        Args:
            user: 用户登录请求对象，包含用户名和密码
            
        Returns:
            User: 认证成功的用户对象，并更新last_login_at字段
            
        Raises:
            ValidationException: 如果用户名或密码不正确
        """
        db_user = self.get_user_by_username(user.username)
        if not db_user or not verify_password(user.password, db_user.password):
            raise ValidationException(
                "Incorrect username or password",
                field="username"
            )
        
        # 更新最后登录时间
        db_user.last_login_at = get_beijing_time()
        self.db.commit()
        self.db.refresh(db_user)
        
        return db_user

