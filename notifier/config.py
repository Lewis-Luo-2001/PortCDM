import os
from typing import Dict, List

##########################################
# LINE Notify tokens                     #
##########################################
# LINE Notify tokens
original_token = os.getenv('LINE_NOTIFY_TOKEN')

line_notify_tokens = {
    'Pilot': os.getenv('LINE_NOTIFY_TOKEN_PILOT'),
    'CIQS': os.getenv('LINE_NOTIFY_TOKEN_CIQS'),
    'Unmooring': os.getenv('LINE_NOTIFY_TOKEN_UNMOORING'),
    'Tugboat': os.getenv('LINE_NOTIFY_TOKEN_TUGBOAT'),
    'ShippingAgentWanHai': os.getenv('LINE_NOTIFY_TOKEN_SHIPPINGAGENT_WAN_HAI'),
    'ShippingCompanyYangMing': os.getenv('LINE_NOTIFY_TOKEN_SHIPPINGCOMPANY_YANG_MING'),
    'LoadingUnloading': os.getenv('LINE_NOTIFY_TOKEN_LOADINGUNLOADING_LIEN_HAI'),
    'PierLienHai': os.getenv('LINE_NOTIFY_TOKEN_PIER_LIEN_HAI'),
    'PierSelfOperated': os.getenv('LINE_NOTIFY_TOKEN_PIER_SELF_OPERATED')
}
berth_message_type_for_pier=["新增引水申請 (進港)","更新引水時間 (進港)","船長報告ETA", "引水人出發 (進港)","實際靠妥時間","新增引水申請 (出港)","更新引水時間 (出港)", "引水人出發 (出港)"]
##########################################
# Event mapping                          #
##########################################
# Events: ["進港預報申請", "修改進港預報", "新增引水申請 (進港)", "更新引水時間 (進港)", "船席異動", "船長報告ETA", 
# "引水人排班 (進港)", "引水人出發 (進港)", "引水人上船時間 (進港)", "申請進港", "經過信號台 (進港)", "實際靠妥時間", 
# "海巡署審核 (進港)", "移民署審核 (進港)", "出港預報申請", "修改出港預報", "海巡署審核 (出港)", "移民署審核 (出港)", 
# "新增引水申請 (出港)", "更新引水時間 (出港)", "引水人上船時間 (出港)", "引水人排班 (出港)", "引水人出發 (出港)",
# "離開泊地時間", "通過15浬時間", "通過10浬時間", "通過5浬時間"]
# Recipients: ["Pilot", "CIQS", "Unmooring", "Tugboat", "ShippingAgentWanHai", "ShippingCompanyYangMing", "LoadingUnloading", "PierLienHai", "PierSelfOperated"]
INOUT_PILOTAGE_EVENTS = ["新增引水申請", "更新引水時間", "引水人上船時間", "引水人出發", "引水人排班", "海巡署審核", "移民署審核"]
BERTH_ORDER_EVENTS = ["通過10浬時間", "通過5浬時間"]

notification_mapping: Dict[str, List[str]] = {
    "進港預報申請": ["Pilot", "CIQS", "ShippingAgentWanHai"],
    "修改進港預報": ["Pilot", "CIQS", "ShippingAgentWanHai", "Unmooring"],
    "新增引水申請 (進港)": ["Pilot", "CIQS", "ShippingAgentWanHai", "Tugboat"],
    "更新引水時間 (進港)": ["Pilot", "CIQS", "ShippingAgentWanHai", "Unmooring", "Tugboat"],
    "船席異動": ["Pilot", "CIQS", "ShippingAgentWanHai", "Unmooring"],
    "船長報告ETA": ["Pilot", "CIQS", "ShippingAgentWanHai", "Tugboat"],
    "引水人排班 (進港)": ["Pilot", "CIQS", "ShippingAgentWanHai"],
    "引水人出發 (進港)": ["Pilot", "CIQS", "ShippingAgentWanHai", "UNMOORING", "LoadingUnloading", "Tugboat"],
    "引水人上船時間 (進港)": ["Pilot", "CIQS", "PierLienHai", "PierSelfOperated", "ShippingCompanyYangMing", "ShippingAgentWanHai"],
    "申請進港": ["Pilot", "CIQS", "ShippingAgentWanHai"],
    "經過信號台 (進港)": ["Pilot", "CIQS", "ShippingAgentWanHai", "Unmooring"],
    "實際靠妥時間": ["Pilot", "CIQS", "ShippingAgentWanHai"],
    "海巡署審核 (進港)": ["Pilot", "CIQS", "ShippingAgentWanHai"],
    "移民署審核 (進港)": ["Pilot", "CIQS", "ShippingAgentWanHai"],
    "出港預報申請": ["Pilot", "CIQS", "ShippingAgentWanHai"],
    "修改出港預報": ["Pilot", "CIQS", "ShippingAgentWanHai", "Unmooring"],
    "海巡署審核 (出港)": ["Pilot", "CIQS", "ShippingAgentWanHai"],
    "移民署審核 (出港)": ["Pilot", "CIQS", "ShippingAgentWanHai"],
    "新增引水申請 (出港)": ["Pilot", "CIQS", "ShippingAgentWanHai", "Tugboat"],
    "更新引水時間 (出港)": ["Pilot", "CIQS", "ShippingAgentWanHai", "Unmooring", "Tugboat"],
    "引水人排班 (出港)": ["Pilot", "CIQS", "ShippingAgentWanHai"],
    "引水人出發 (出港)": ["Pilot", "CIQS", "ShippingCompanyYangMing", "ShippingAgentWanHai", "Unmooring", "Tugboat"],
    "引水人上船時間 (出港)": ["Pilot", "CIQS", "ShippingAgentWanHai"],
    "離開泊地時間": ["ShippingAgent", "ShippingCompany", "Pilot", "Tugboat"],
    "通過15浬時間": ["ShippingAgent", "ShippingCompany", "Pilot", "Tugboat"],
    "通過10浬時間": ["Pilot", "Unmooring", "Tugboat", "ShippingAgentWanHai", "ShippingCompanyYangMing", "LoadingUnloading"],
    "通過5浬時間": ["Pilot", "Unmooring", "Tugboat", "ShippingAgentWanHai", "ShippingCompanyYangMing", "LoadingUnloading"]
}
