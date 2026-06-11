# .gitignore 通用模板

```python
# Python
__pycache__/
*.pyc
*.pyo
.venv/
venv/
*.egg-info/

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db

# 数据/敏感
*.duckdb
*.db
*.sqlite
.env
secrets.*

# 日志 (loguru 等运行产物)
*.log
logs/
```