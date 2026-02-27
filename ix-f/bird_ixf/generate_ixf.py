import subprocess
import re
import json
import os
from datetime import datetime

# --- 配置区 ---
# 脚本将生成的 JSON 文件存放在此路径
OUTPUT_DIR = "/opt/bird_ixf"
JSON_FILENAME = "ixf.json"
# --------------

def parse_bird_to_ixf():
    # 运行 BIRD 命令并获取输出
    try:
        raw_output = subprocess.check_output(["birdc", "s", "p", "a"], text=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running birdc: {e}")
        return None

    # 按照 BGP 协议块切分内容
    blocks = re.split(r'\n(?=\S+\s+BGP\s+)', raw_output)

    member_list = []
    for block in blocks:
        if "BGP" not in block:
            continue
            
        # 使用正则提取关键信息
        asn_match = re.search(r"Neighbor AS:\s+(\d+)", block)
        ip_match = re.search(r"Neighbor address:\s+([0-9a-fA-F:]+)", block)
        state_match = re.search(r"BGP state:\s+(\w+)", block)

        if asn_match and ip_match:
            asn = asn_match.group(1)
            ip = ip_match.group(1)
            state = state_match.group(1) if state_match else "down"
            
            # 状态映射：只要配置了都输出，但只有 Established 标记为 up
            ixf_state = "up" if state == "Established" else "down"
            
            member_list.append({
                "as_number": int(asn),
                "ip_addresses": [ip],
                "session_state": ixf_state,
                "last_updated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            })

    # 返回符合 Euro-IX IX-F Schema 的结构
    return {
        "version": "1.0",
        "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "member_list": member_list
    }

if __name__ == "__main__":
    data = parse_bird_to_ixf()
    
    if data:
        # 确保输出目录存在
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        file_path = os.path.join(OUTPUT_DIR, JSON_FILENAME)
        
        # 写入文件
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)
        
        print(f"Success: IX-F JSON has been generated at {file_path}")
