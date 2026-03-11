from app import app
from models import db

with app.app_context():
    print("正在删除旧表...")
    db.drop_all()
    print("正在创建新表...")
    db.create_all()
    
    # 顺便把分类初始化了，防止首页没分类
    from models import Category, User
    from werkzeug.security import generate_password_hash
    
    cats = ["头条", "国际", "国内", "军事", "财经", "科技", "体育"]
    for c in cats:
        db.session.add(Category(name=c))
    
    # 初始化管理员
    db.session.add(User(username="admin", password=generate_password_hash("0910"), role="admin"))
    
    db.session.commit()
    print("数据库重置成功！分类和管理员账号已就绪。")