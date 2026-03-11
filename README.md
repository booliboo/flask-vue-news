本项目采用前后端分离架构，具体技术栈如下：
1. 系统架构
开发模式：前后端分离架构（B/S 架构）
通信协议 ：HTTP / RESTful API
认证方式：JWT (JSON Web Token)
2. 前端技术栈
核心框架：Vue.js 3 (Composition API)
网络请求：Axios
数据可视化：ECharts 5.x
页面开发：HTML5、CSS3 (Flexbox / Grid)
3. 后端技术栈
编程语言：Python 3.x
核心框架：Flask
跨域处理：Flask-CORS
安全加密：Werkzeug (Password Hashing)
身份验证：PyJWT
文件上传：Werkzeug.utils
4. 数据库技术
数据库系统：MySQL 8.0
ORM框架：Flask-SQLAlchemy
数据库驱动：PyMySQL
5. 核心功能实现
内容安全：关键词过滤算法（Sensitive Words Filtering）
交互功能：点赞/点踩幂等记录、实时评论、新闻收藏
用户体验：阅读进度记忆（Scroll Position Tracking）
资源管理：多格式附件（PDF/Docx/Image）上传与动态图标识别转换
