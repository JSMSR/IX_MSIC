#!/usr/bin/python3
import subprocess
import re
import json
import os
from datetime import datetime, timezone

# --- 配置区 ---
OUTPUT_DIR = "/opt/bird_ixf"
JSON_FILENAME = "ixf.json"
BIRD_CTL_PATH = "/run/bird/bird.ctl"

IXP_CONFIG = {
    "ixp_id": 4499,                 # PeeringDB 中的 IX ID
    "shortname": "MSR IX",
    "switch_name": "MSR-Core-SW",    # 建议填一个，方便识别
    "colo_name": "JSMSR Networks MSR Internet Exchange",
    "city": "Shibuya",
    "country": "JP",
    "manufacturer": "Juniper",
    "model": "MX204"
}
# --------------

def parse_bird_to_ixf():
    try:
        # 使用你确认的路径执行 BIRD 命令
        raw_output = subprocess.check_output(["birdc", "-s", BIRD_CTL_PATH, "s", "p", "a"], text=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running birdc: {e}")
        return None

    blocks = re.split(r'\n(?=\S+\s+BGP\s+)', raw_output)
    member_list = []
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    
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
            
            # 状态逻辑：
            # 在专业版格式中，connection 层的 state 通常指物理连接是否 active
            # 我们可以根据 BGP 状态灵活定义
            ixf_conn_state = "active" if state == "Established" else "inactive"
            
            # 构造符合 Euro-IX 标准的嵌套条目
            member_entry = {
                "as_number": asn_val,        # 兼容性字段
                "asnum": asn_val,           # 核心字段
                "connection_list": [
                    {
                        "ixp_id": IXP_CONFIG["ixp_id"],
                        "state": ixf_conn_state,
                        "if_list": [
                            {
                                "if_speed": 1000,
                                "switch_id": 1
                            }
                        ],
                        "vlan_list": [
                            {
                                "vlan_id": 0,
                                "ipv6": {
                                    "address": ip,
                                    "routeserver": True
                                }
                            }
                        ]
                    }
                ],
                "last_updated": now_utc
            }
            member_list.append(member_entry)

    # 构建最终的全量 JSON
    return {
        "version": "1.0",
        "timestamp": now_utc,
        "ixp_list": [
            {
                "ixp_id": IXP_CONFIG["ixp_id"],
                "shortname": IXP_CONFIG["shortname"],
                "vlan": [{"id": 0}],
                "switch": [
                    {
                        "id": 1,
                        "name": IXP_CONFIG["switch_name"],
                        "colo": IXP_CONFIG["colo_name"],
                        "city": IXP_CONFIG["city"],
                        "country": IXP_CONFIG["country"],
                        "manufacturer": IXP_CONFIG["manufacturer"],
                        "model": IXP_CONFIG["model"]
                    }
                ]
            }
        ],
        "member_list": member_list
    }

if __name__ == "__main__":
    data = parse_bird_to_ixf()
    if data:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        file_path = os.path.join(OUTPUT_DIR, JSON_FILENAME)
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)
        print(f"Success: Professional IX-F JSON with BIRD logic generated at {file_path}")
