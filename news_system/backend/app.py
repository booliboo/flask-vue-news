import os
import jwt
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, request, jsonify, g, send_from_directory, make_response
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import func

from config import Config
from models import db, User, Category, News, Comment, ReadRecord, Favorite, ActionRecord 
app = Flask(__name__)
app.config.from_object(Config)

# 1. 强化跨域配置
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

db.init_app(app)

UPLOAD_FOLDER = app.config["UPLOAD_FOLDER"]
SERVER_URL = app.config["SERVER_URL"]

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# --- ✨ 修改部分：增加具体词汇提示逻辑 ✨ ---
SENSITIVE_WORDS_FILE = "sensitive_words.txt"

def load_sensitive_words():
    """从文件加载敏感词，如果文件不存在则创建默认值"""
    if not os.path.exists(SENSITIVE_WORDS_FILE):
        with open(SENSITIVE_WORDS_FILE, "w", encoding="utf-8") as f:
            f.write("广告,色情,暴力,代考,刷单,赌博")
    with open(SENSITIVE_WORDS_FILE, "r", encoding="utf-8") as f:
        content = f.read().strip()
        return content.split(",") if content else []

def get_hit_sensitive_words(title, content):
    """检测内容，返回触发的所有违规词列表"""
    words = load_sensitive_words()
    text = f"{title}{content}"
    # 找出所有包含在内容里的敏感词
    hits = [w.strip() for w in words if w.strip() and w.strip() in text]
    return hits

def format_image(img):
    if not img: return ""
    if img.startswith("http"): return img
    return f"{SERVER_URL}{img if img.startswith('/') else '/'+img}"

# --- 装饰器逻辑 ---
def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            auth = request.headers.get("Authorization")
            if not auth: return jsonify({"msg": "未登录"}), 401
            try:
                token = auth.split()[1]
                data = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
                g.user = data
                if role and data.get("role") != role:
                    return jsonify({"msg": "权限不足"}), 403
            except Exception as e:
                return jsonify({"msg": "登录失效", "error": str(e)}), 401
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# --- 管理员管理接口 ---
@app.route("/api/admin/sensitive_words", methods=["GET", "POST"])
@login_required("admin")
def manage_sensitive_words():
    """获取或更新敏感词库"""
    if request.method == "GET":
        return jsonify({"words": load_sensitive_words()})
    
    data = request.json
    new_words = data.get("words", [])
    with open(SENSITIVE_WORDS_FILE, "w", encoding="utf-8") as f:
        f.write(",".join(new_words))
    return jsonify({"msg": "词库更新成功"})

@app.route("/api/admin/audit_list", methods=["GET"])
@login_required("admin")
def get_audit_list():
    """获取待审核（已拦截）的新闻列表"""
    blocked_news = News.query.filter_by(status="blocked").order_by(News.created_at.desc()).all()
    result = []
    for n in blocked_news:
        cat = db.session.get(Category, n.category_id)
        result.append({
            "id": n.id,
            "title": n.title,
            "content": n.content,
            "category_name": cat.name if cat else "未分类",
            "created_at": n.created_at.strftime("%Y-%m-%d %H:%M")
        })
    return jsonify(result)

# --- 文件下载逻辑 ---
@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    response = make_response(send_from_directory(UPLOAD_FOLDER, filename))
    ext = os.path.splitext(filename)[1].lower()
    if ext in ['.ppt', '.pptx', '.doc', '.docx', '.xls', '.xlsx', '.pdf']:
        response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response

# --- 获取新闻 ---
@app.route("/api/news", methods=["GET"])
def get_news():
    try:
        show_all = request.args.get("all", "0") == "1"
        keyword = request.args.get("keyword", "")
        category_id = request.args.get("category_id")
        page = int(request.args.get("page", 1))
        size = int(request.args.get("size", 8))

        query = News.query
        if not show_all:
            query = query.filter_by(status="published")
            # ✨ 核心改动：普通用户只能看到发布时间 <= 现在的新闻
            query = query.filter(News.publish_time <= datetime.now())
        if keyword:
            query = query.filter(News.title.like(f"%{keyword}%"))
        if category_id and category_id not in ['null', 'undefined', '']:
            query = query.filter_by(category_id=int(category_id))
        
        pagination = query.order_by(News.created_at.desc()).paginate(page=page, per_page=size, error_out=False)
        
        result = []
        for n in pagination.items:
            cat = db.session.get(Category, n.category_id)
            views = ReadRecord.query.filter_by(news_id=n.id).count()
            result.append({
                "id": n.id,
                "title": n.title,
                "content": (n.content[:80] + "...") if n.content else "",
                "image_url": format_image(n.image_url),
                "views": views,
                "status": n.status,
                "category_id": n.category_id,
                "category_name": cat.name if cat else "未分类",
                "created_at": n.created_at.strftime("%Y-%m-%d %H:%M") if n.created_at else ""
            })
        return jsonify({"list": result, "total": pagination.total})
    except Exception as e:
        return jsonify({"msg": "服务器查询错误", "error": str(e)}), 500

# --- ✨ 修改部分：发布新闻增加违规词具体提示 ✨ ---
# --- 优化后的发布新闻接口 ---
# --- ✨ 优化后的发布新闻接口：强制频道校验 + 违规词强提示 ✨ ---
@app.route("/api/news", methods=["POST"])
@login_required()
def add_news():
    try:
        title = request.form.get("title")
        content = request.form.get("content")
        cat_id = request.form.get("category_id")
        
        # 1. 【核心改动】强制校验：不选频道直接返回 400 提示，不再默认分配
        if not cat_id or cat_id in ['undefined', 'null', '', 'None']:
            return jsonify({"msg": "发布失败：请选择所属频道（类别）！"}), 400
        
        if not title or not content:
            return jsonify({"msg": "标题和内容不能为空"}), 400

        # 2. 敏感词判定逻辑
        hit_words = get_hit_sensitive_words(title, content)
        
        # 3. 处理分类 ID 转换
        try:
            cat_id = int(cat_id)
        except (ValueError, TypeError):
            return jsonify({"msg": "频道 ID 格式错误"}), 400

        # 4. 文件上传逻辑（保持原样）
        img_file = request.files.get("image_file")
        img_path = ""
        if img_file and img_file.filename != '':
            img_name = "img_" + datetime.now().strftime("%Y%m%d%H%M%S_") + secure_filename(img_file.filename)
            img_file.save(os.path.join(UPLOAD_FOLDER, img_name))
            img_path = f"/uploads/{img_name}"

        att_file = request.files.get("attachment_file")
        file_path = ""
        if att_file and att_file.filename != '':
            att_name = "file_" + datetime.now().strftime("%Y%m%d%H%M%S_") + secure_filename(att_file.filename)
            att_file.save(os.path.join(UPLOAD_FOLDER, att_name))
            file_path = f"/uploads/{att_name}"

        # 5. 根据是否有违规词决定存入状态
        if hit_words:
            status = "blocked"
            res_msg = f"发布失败！内容包含违规词：【{','.join(hit_words)}】。已提交后台人工审核。"
            return_code = 400  # 使用 400 强行触发前端的 catch/错误提示
        else:
            status = "published"
            res_msg = "恭喜你，新闻已成功发布！"
            return_code = 200

       
            # 在 add_news 函数内部，存入数据库之前处理一下时间
        pub_time_str = request.form.get("publish_time")
        # 如果前端传了时间就用前端的，没传就用现在
        publish_time = datetime.strptime(pub_time_str, '%Y-%m-%dT%H:%M') if pub_time_str else datetime.now()

        # 6. 存入数据库
        new_news = News(
            title=title,
            content=content,
            category_id=cat_id,
            image_url=img_path,
            file_url=file_path, 
            status=status,
            author_id=g.user.get('user_id'), # ✨ 补上作者ID
            publish_time=publish_time,       # ✨ 补上定时发布时间
            created_at=datetime.now()
        )
        
        
        db.session.add(new_news)
        db.session.commit()
        
        return jsonify({
            "msg": res_msg, 
            "id": new_news.id, 
            "status": status
        }), return_code

    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": "系统繁忙，发布失败", "error": str(e)}), 500

@app.route("/api/news/rank")
def rank():
    result = db.session.query(News.id, News.title, func.count(ReadRecord.id).label('v'))\
        .outerjoin(ReadRecord, News.id == ReadRecord.news_id)\
        .group_by(News.id).order_by(func.count(ReadRecord.id).desc()).limit(10).all()
    return jsonify([{"id": r[0], "title": r[1], "views": r[2]} for r in result])

@app.route("/api/stats/category")
def stats_category():
    stats = db.session.query(Category.name, func.count(News.id))\
        .join(News, Category.id == News.category_id)\
        .group_by(Category.name).all()
    return jsonify([{"name": s[0], "value": s[1]} for s in stats])

@app.route("/api/news/<int:id>/audit", methods=["POST"])
@login_required("admin")
def audit_news(id):
    news = db.session.get(News, id)
    if not news: return jsonify({"msg": "新闻不存在"}), 404
    news.status = "published"
    db.session.commit()
    return jsonify({"msg": "审核成功"})

@app.route("/api/news/<int:id>/action", methods=["POST"])
@login_required() # ✨ 必须登录才能点赞，这样我们才能拿到 user_id
def news_action(id):
    news = db.session.get(News, id)
    if not news: return jsonify({"msg": "新闻不存在"}), 404
    
    user_id = g.user['user_id']
    data = request.json
    new_action = data.get("action") # 'like' 或 'dislike'
    
    # 1. 查找该用户对该新闻的现有操作记录
    existing_record = ActionRecord.query.filter_by(user_id=user_id, news_id=id).first()
    
    if existing_record:
        if existing_record.action_type == new_action:
            # ✨ 情况A：用户点击了相同的按钮 -> 取消操作（点赞减一，删除记录）
            if new_action == 'like': news.likes = max(0, news.likes - 1)
            else: news.dislikes = max(0, news.dislikes - 1)
            db.session.delete(existing_record)
            current_state = None
        else:
            # ✨ 情况B：用户切换了操作（比如从点赞换成点踩）
            if new_action == 'like':
                news.likes += 1
                news.dislikes = max(0, news.dislikes - 1)
            else:
                news.dislikes += 1
                news.likes = max(0, news.likes - 1)
            existing_record.action_type = new_action
            current_state = new_action
    else:
        # ✨ 情况C：第一次操作
        if new_action == 'like': news.likes += 1
        else: news.dislikes += 1
        db.session.add(ActionRecord(user_id=user_id, news_id=id, action_type=new_action))
        current_state = new_action

    db.session.commit()
    return jsonify({
        "likes": news.likes, 
        "dislikes": news.dislikes, 
        "currentState": current_state
    })

@app.route("/api/news/<int:id>/comment", methods=["POST"])
def add_comment_detail(id):
    data = request.json
    c = Comment(news_id=id, username=data.get('username','匿名'), content=data.get('content'))
    db.session.add(c)
    db.session.commit()
    return jsonify({"msg": "评论成功"})

@app.route("/api/register", methods=["POST"])
def register():
    data = request.json
    if User.query.filter_by(username=data["username"]).first():
        return jsonify({"msg": "用户名已存在"}), 400
    user = User(username=data["username"], password=generate_password_hash(data["password"]), role="user")
    db.session.add(user)
    db.session.commit()
    return jsonify({"msg": "注册成功"})

@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    user = User.query.filter_by(username=data["username"]).first()
    if not user or not check_password_hash(user.password, data["password"]):
        return jsonify({"msg": "账号或密码错误"}), 401
    
    payload = {
        "user_id": user.id, 
        "role": user.role, 
        "username": user.username, 
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    token = jwt.encode(payload, app.config["SECRET_KEY"], algorithm="HS256")
    
    return jsonify({
        "token": token, 
        "role": user.role, 
        "username": user.username,
        "nickname": user.nickname or user.username # ✨ 补上这一行，方便前端显示
    })

@app.route("/api/categories")
def categories():
    cats = Category.query.all()
    return jsonify([{"id": c.id, "name": c.name} for c in cats])

@app.route("/api/news/<int:id>", methods=["DELETE"])
@login_required("admin")
def delete_news(id):
    news = db.session.get(News, id)
    if not news: return jsonify({"msg": "不存在"}), 404
    Comment.query.filter_by(news_id=id).delete()
    ReadRecord.query.filter_by(news_id=id).delete()
    db.session.delete(news)
    db.session.commit()
    return jsonify({"msg": "删除成功"})

@app.route("/api/news/<int:id>")
def news_detail(id):
    news = db.session.get(News, id)
    if not news: return jsonify({"msg": "新闻不存在"}), 404
    
    # --- ✨ 逻辑增强：识别当前用户（如果登录了） ---
    current_user_id = None
    is_fav = False
    last_pos = 0
    
    auth = request.headers.get("Authorization")
    if auth and len(auth.split()) > 1:
        try:
            token = auth.split()[1]
            data = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
            current_user_id = data.get("user_id")
            # 1. 检查是否收藏
            is_fav = Favorite.query.filter_by(user_id=current_user_id, news_id=id).first() is not None
            # 2. 获取上次阅读进度
            last_record = ReadRecord.query.filter_by(news_id=id, user_id=current_user_id).order_by(ReadRecord.read_at.desc()).first()
            if last_record: last_pos = last_record.scroll_pos
        except: pass

    # --- ✨ 逻辑增强：创建带 user_id 的阅读记录 ---
    db.session.add(ReadRecord(news_id=id, user_id=current_user_id, read_at=datetime.now()))
    db.session.commit()
    
    comments = Comment.query.filter_by(news_id=id).order_by(Comment.created_at.desc()).all()
    return jsonify({
        "id": news.id,
        "title": news.title,
        "content": news.content,
        "image_url": format_image(news.image_url),
        "file_url": format_image(news.file_url), 
        "likes": news.likes or 0,
        "dislikes": news.dislikes or 0,
        "views": ReadRecord.query.filter_by(news_id=id).count(),
        "created_at": news.created_at.strftime("%Y-%m-%d %H:%M"),
        "is_favorite": is_fav,   # ✨ 返回收藏状态
        "last_pos": last_pos,     # ✨ 返回上次阅读位置
        "comments": [{"username": c.username, "content": c.content, "created_at": c.created_at.strftime("%Y-%m-%d %H:%M")} for c in comments]
    })
@app.route("/api/news/<int:id>/favorite", methods=["POST"])
@login_required()
def toggle_favorite(id):
    user_id = g.user['user_id']
    fav = Favorite.query.filter_by(user_id=user_id, news_id=id).first()
    if fav:
        db.session.delete(fav)
        msg = "取消收藏"
    else:
        db.session.add(Favorite(user_id=user_id, news_id=id))
        msg = "收藏成功"
    db.session.commit()
    return jsonify({"msg": msg})

@app.route("/api/user/favorites", methods=["GET"])
@login_required()
def get_user_favorites():
    """获取当前用户收藏的所有新闻列表"""
    user_id = g.user['user_id']
    # 通过关联查询，找到该用户收藏的所有新闻对象
    fav_news = db.session.query(News).join(Favorite, News.id == Favorite.news_id).filter(Favorite.user_id == user_id).all()
    
    result = []
    for n in fav_news:
        result.append({
            "id": n.id,
            "title": n.title,
            "created_at": n.created_at.strftime("%Y-%m-%d %H:%M")
        })
    return jsonify(result)

@app.route("/api/news/<int:id>/progress", methods=["POST"])
@login_required()
def save_progress(id):
    """保存用户的阅读进度"""
    data = request.json
    pos = data.get("scroll_pos", 0)
    # 找到该用户最后一次阅读该新闻的记录
    record = ReadRecord.query.filter_by(news_id=id, user_id=g.user['user_id']).order_by(ReadRecord.read_at.desc()).first()
    if record:
        record.scroll_pos = pos
        db.session.commit()
    return jsonify({"msg": "进度已保存"})

@app.route("/api/user/profile", methods=["GET", "POST"])
@login_required()
def profile_api():
    # 从 g.user 获取当前登录的用户 ID（装饰器里存进去的）
    user = db.session.get(User, g.user['user_id'])
    
    if request.method == "POST":
        data = request.json
        user.nickname = data.get('nickname')
        user.bio = data.get('bio')
        db.session.commit()
        return jsonify({"msg": "个人资料更新成功"})
    
    # GET 请求返回当前资料
    return jsonify({
        "nickname": user.nickname or user.username,
        "bio": user.bio or "",
        "role": user.role
    })

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        target_categories = ["头条", "国际", "国内", "军事", "财经", "科技", "体育", "娱乐", "社会", "生活"]
        for cat_name in target_categories:
            if not Category.query.filter_by(name=cat_name).first():
                db.session.add(Category(name=cat_name))
        
        admin_user = User.query.filter_by(username="admin").first()
        if not admin_user:
            db.session.add(User(username="admin", password=generate_password_hash("0910"), role="admin"))
        else:
            admin_user.password = generate_password_hash("0910")
        
        db.session.commit()
    app.run(debug=True)