import uvicorn
import os
import sys
from pathlib import Path

# 获取当前文件所在目录
current_dir = Path(__file__).parent.absolute()

# 设置工作目录
os.chdir(current_dir)

if __name__ == "__main__":
    print(f"Current directory: {os.getcwd()}")
    print("Starting FastAPI application...")
    
    try:
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except ImportError as e:
        print(f"Import error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1) 