import random
from app import app
from models import db, News, Category, User
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

def seed_data():
    # ✨ 核心修复：确保所有数据库操作都在这个 with 块的缩进内
    with app.app_context():
        print("🚀 开始生成全品类测试数据...")

        # 1. 确保管理员账号存在
        admin = User.query.filter_by(username="admin").first()
        if not admin:
            admin = User(username="admin", password=generate_password_hash("0910"), role="admin")
            db.session.add(admin)
            db.session.commit()

        # 2. 定义分类及对应的模拟标题
        news_data = {
            "科技": [
                "国产大模型发布，AI领域再添强劲竞争者",
                "折叠屏手机市场爆发，多家厂商发布年度旗舰",
                "量子计算取得重大突破，计算效率提升千倍",
                "自动驾驶技术在部分城市开启全天候商业化运营"
            ],
            "财经": [
                "全球股市波动加剧，投资者避险情绪升温",
                "创业板指单日大涨3%，科技股领涨市场",
                "央行发布最新货币政策，释放流动性支持实体经济",
                "互联网大厂发布财报，利润增长超出市场预期"
            ],
            "体育": [
                "2024巴黎奥运会场馆建设进入最后验收阶段",
                "NBA常规赛：卫冕冠军豪取十连胜领跑全联盟",
                "世界乒联公开赛：国乒包揽男女单打冠军",
                "足协杯决赛定档，南北双雄争夺年度最高荣誉"
            ],
            "娱乐": [
                "年度史诗级大片定档暑期，首支预告片引发全网关注",
                "知名歌手巡回演唱会门票秒罄，粉丝呼吁增加场次",
                "电影金像奖入围名单揭晓，多部现实主义题材受青睐",
                "新款国民综艺开录，多位重磅嘉宾首度加盟"
            ],
            "头条": [
                "十四届全国人大常委会举行会议，审议多项法律草案",
                "我国深海探测器成功完成万米深潜任务",
                "全球气候峰会达成共识，共同推动绿色能源转型"
            ]
        }

        # 3. 开始循环插入 (注意这里的缩进，必须在 with 块内)
        total_count = 0
        for cat_name, titles in news_data.items():
            # 获取或创建分类
            cat = Category.query.filter_by(name=cat_name).first()
            if not cat:
                cat = Category(name=cat_name)
                db.session.add(cat)
                db.session.commit()
                print(f"- 已创建分类: {cat_name}")
            
            for t in titles:
                if not News.query.filter_by(title=t).first():
                    # 随机生成阅读数、点赞数，让排行和图表更好看
                    random_likes = random.randint(10, 100)
                    
                    # 随机生成过去一周内的发布时间
                    random_days = random.randint(0, 7)
                    random_time = datetime.now() - timedelta(days=random_days)

                    n = News(
                        title=t,
                        content=f"【{cat_name}深度报道】{t}。据本报记者实地采访了解到，该事件在行业内引发了广泛讨论。专家指出，这一动态不仅展示了我国在{cat_name}领域的快速发展，也为未来的产业升级提供了重要参考。更多详细内容请持续关注我们的后续报道。",
                        category_id=cat.id,
                        author_id=admin.id,
                        status="published",
                        likes=random_likes,
                        dislikes=random.randint(0, 10),
                        publish_time=random_time,
                        created_at=random_time
                    )
                    db.session.add(n)
                    total_count += 1
        
        db.session.commit()
        print(f"✅ 成功生成 {total_count} 条全品类新闻数据！")

if __name__ == "__main__":
    seed_data()