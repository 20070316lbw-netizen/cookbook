"""
yaml.dump 整体覆盖,冲掉手写配置块 —— 正确写法

场景:config.yaml 由两部分组成
  - data  : generate_config.py 自动生成
  - model : 手写的 lightgbm 超参
脚本只该更新 data,不能动 model。

核心模式:读 -> 只改自己负责的 key -> 写回。
"""
import yaml
from pathlib import Path


# ----------------------------------------------------------------------
# ❌ 错:直接 yaml.dump 一个只含 data 的 dict,会清空整个文件
# ----------------------------------------------------------------------
def wrong(output_path: Path, data_block: dict) -> None:
    config = {"data": data_block}
    with open(output_path, "w") as f:
        yaml.dump(config, f)
    # 结果:文件里只剩 data,手写的 model 块没了


# ----------------------------------------------------------------------
# ✅ 对:先读出已有内容,只替换 data,其他 key 原样保留
# ----------------------------------------------------------------------
def right(output_path: Path, data_block: dict) -> dict:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. 文件已存在就先读出来;不存在就从空 dict 开始
    if output_path.exists():
        with open(output_path, "r", encoding="utf-8") as f:
            existing = yaml.safe_load(f) or {}   # 空文件 safe_load 返回 None
    else:
        existing = {}

    # 2. 只替换自己负责的 key,model 等其他 key 不受影响
    existing["data"] = data_block

    # 3. 写回
    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(
            existing, f,
            default_flow_style=False,   # 块状格式,不挤成一行
            allow_unicode=True,         # 中文不转义成 \uXXXX
            sort_keys=False,            # 保持原顺序,不按字母重排
        )
    return existing


if __name__ == "__main__":
    import tempfile

    # 造一个已有 model 块的 config 文件
    tmp = Path(tempfile.gettempdir()) / "demo_config.yaml"
    tmp.write_text(
        "data:\n  start: old\nmodel:\n  num_leaves: 31\n",
        encoding="utf-8",
    )
    print("原始文件:")
    print(tmp.read_text(encoding="utf-8"))

    # 用正确写法更新 data
    new_data = {"start": "2024-05-12", "end": "2025-05-12"}
    right(tmp, new_data)

    print("更新 data 之后(model 块应该还在):")
    print(tmp.read_text(encoding="utf-8"))

    result = yaml.safe_load(tmp.read_text(encoding="utf-8"))
    assert "model" in result, "model 块不该丢"
    assert result["data"]["start"] == "2024-05-12", "data 应该被更新"
    print("✅ data 已更新,model 块完整保留")

    tmp.unlink()
