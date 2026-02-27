#!/usr/bin/python3
import subprocess
import re
import json
import os
from datetime import datetime, timezone

# --- 配置区 ---
OUTPUT_DIR = "/opt/bird_ixf"
JSON_FILENAME = "ixf.json"
# 使用你确认的路径
BIRD_CTL_PATH = "/run/bird/bird.ctl"
# --------------

def parse_bird_to_ixf():
    try:
        # 显式使用你找到的 /run/bird/bird.ctl 路径
        raw_output = subprocess.check_output(["birdc", "-s", BIRD_CTL_PATH, "s", "p", "a"], text=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running birdc: {e}")
        return None

    # 按照 BGP 协议块切分内容
    blocks = re.split(r'\n(?=\S+\s+BGP\s+)', raw_output)
    member_list = []
    now_utc = datetime.now(timezone.utc)
    
    for block in blocks:
        if "BGP" not in block:
            continue
            
        asn_match = re.search(r"Neighbor AS:\s+(\d+)", block)
        ip_match = re.search(r"Neighbor address:\s+([0-9a-fA-F:]+)", block)
        state_match = re.search(r"BGP state:\s+(\w+)", block)

        if asn_match and ip_match:
            asn_val = int(asn_match.group(1))
            ip = ip_match.group(1)
            state = state_match.group(1) if state_match else "down"
            
            # 状态映射逻辑
            ixf_state = "up" if state == "Established" else "down"
            
            # 构造 PeeringDB 兼容字典
            member_entry = {
                "as_number": asn_val,
                "asnum": asn_val,               
                "ip_addresses": [ip],           
                "session_state": ixf_state,     
                "last_updated": now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "is_rs_peer": True,             
                "if_speed": 1000                
            }
            member_list.append(member_entry)

    return {
        "version": "1.0",
        "timestamp": now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "member_list": member_list
    }

if __name__ == "__main__":
    data = parse_bird_to_ixf()
    if data:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        file_path = os.path.join(OUTPUT_DIR, JSON_FILENAME)
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)
        print(f"Success: IX-F JSON has been generated at {file_path}")
