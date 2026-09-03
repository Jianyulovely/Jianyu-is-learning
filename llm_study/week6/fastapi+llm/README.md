```markdown:README.md
# AI 教师助手

基于 FastAPI 和大语言模型的多学科问答系统，支持语文、数学、英语三个学科的专业问答。

## 项目结构

```
.
├── main.py              # FastAPI 主应用
├── llm.py              # 大语言模型调用函数
├── requirements.txt     # 依赖列表
└── README.md           # 项目说明
```

## 安装依赖

```bash
pip install fastapi uvicorn openai pydantic
```

## 配置

在 `main.py` 第 25 行修改你的 API Key：
```python
api_key: str = "your_api_key_here"
```

## 运行

```bash
python main.py
```

服务启动后访问：http://localhost:8010/docs

## API 接口

- `POST /chinese-teacher` - 语文问答
- `POST /math-teacher` - 数学问答  
- `POST /english-teacher` - 英语问答

请求格式：
```json
{
    "question": "你的问题"
}
```
```
