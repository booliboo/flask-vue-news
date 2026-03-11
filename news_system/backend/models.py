from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# 1. 用户模型
class User(db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    nickname = db.Column(db.String(50)) 
    bio = db.Column(db.String(255))      
    role = db.Column(db.String(20), default="user") 

# 2. 分类模型
class Category(db.Model):
    __tablename__ = "category"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    news_list = db.relationship('News', backref='category', lazy=True)

# 3. 新闻模型
class News(db.Model):
    __tablename__ = "news"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text)
    image_url = db.Column(db.String(500)) 
    file_url = db.Column(db.String(500))  
    status = db.Column(db.String(20), default="published") 
    likes = db.Column(db.Integer, default=0)
    dislikes = db.Column(db.Integer, default=0)
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"))
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    publish_time = db.Column(db.DateTime, default=datetime.now) 
    created_at = db.Column(db.DateTime, default=datetime.now)

# 4. 评论模型
class Comment(db.Model):
    __tablename__ = "comment"
    id = db.Column(db.Integer, primary_key=True)
    news_id = db.Column(db.Integer, db.ForeignKey("news.id"))
    username = db.Column(db.String(50), default="游客")
    content = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)

# 5. 阅读记录模型 (用于阅读进度记忆)
class ReadRecord(db.Model):
    __tablename__ = "read_record"
    id = db.Column(db.Integer, primary_key=True)
    news_id = db.Column(db.Integer, db.ForeignKey("news.id"))
    user_id = db.Column(db.Integer, nullable=True)
    scroll_pos = db.Column(db.Integer, default=0) 
    read_at = db.Column(db.DateTime, default=datetime.now)

# 6. 收藏模型 
class Favorite(db.Model):
    __tablename__ = "favorite"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    news_id = db.Column(db.Integer, db.ForeignKey("news.id"))
    created_at = db.Column(db.DateTime, default=datetime.now)

# 7. 点赞/点踩记录模型 (用于防止刷票)
class ActionRecord(db.Model):
    __tablename__ = "action_record"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    news_id = db.Column(db.Integer, db.ForeignKey("news.id"), nullable=False)
    action_type = db.Column(db.String(10)) # 'like' 或 'dislike'
    created_at = db.Column(db.DateTime, default=datetime.now)