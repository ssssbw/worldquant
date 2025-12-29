# IND Region Alpha 生成器 (快速版)
# 🎉 IND Region Theme: 29 Dec'25 - 4 Jan'26 (1周)
# Multiplier: 2X for regular alphas

import random
import csv
import os
import json  # 添加json模块用于正确序列化

# IND Region 配置
IND_CONFIG = {
    'region': 'IND',
    'universe': 'TOP2000',
    'delay': 1,
    'multiplier': '2X',
    'duration': '29 Dec\'25 - 4 Jan\'26',
    'allowed_pv1_group_fields': ['country', 'exchange', 'market', 'sector', 'industry', 'subindustry']
}

# Macro 和 Model 字段列表
MACRO_FIELDS = [
    'gdp', 'inflation', 'interest_rate', 'exchange_rate', 'cpi', 'ppi',
    'unemployment_rate', 'industrial_production', 'retail_sales', 'consumer_confidence',
    'housing_starts', 'trade_balance', 'current_account', 'government_debt',
    'money_supply', 'current_gdp', 'gdp_growth', 'core_inflation'
]

MODEL_FIELDS = [
    f'model{i}' for i in range(1, 51)
] + [f'model{i}' for i in range(60, 71)]

# 允许的分组字段
groups = IND_CONFIG['allowed_pv1_group_fields']

# 时间窗口
time_windows = {
    'very_short': [3, 5, 7],
    'short': [10, 15, 20],
    'medium': [30, 40, 60],
    'long': [90, 120, 180]
}

# 快速Alpha模板
quick_templates = [
    # Model因子模板
    "ts_rank({field}, {window})",
    "group_neutralize(rank({field}), {group})",
    "ts_zscore({field}, {window})",
    "group_rank(rank({field}), {group})",
    "ts_rank(ts_delta({field}, {delay}), {window})",
    "zscore({field})",
    "ts_delta({field}, {delay})",
    "ts_mean({field}, {window})",
    # Macro因子模板
    "ts_rank(ts_delta({macro_field}, 1), {window})",
    "ts_decay_linear(rank({macro_field}), {window})",
    "ts_delta(ts_mean({macro_field}, {window}), 1)",
    "group_neutralize(ts_delta({macro_field}, {delay}) - ts_mean(ts_delta({macro_field}, 1), {window}), {group})",
    "-1 * ts_zscore({macro_field}, {window})",
    "ts_rank({macro_field} / ts_mean({macro_field}, {window}) - 1, {window}) * -1",
    "rank({macro_field} - ts_mean({macro_field}, {window})) / ts_std_dev({macro_field}, {window})",
    "ts_std_dev({macro_field}, {window})",
    "ts_scale({macro_field}, {window}) * ts_rank({macro_field}, {window})",
    # 跨资产因子
    "ts_corr({field1}, {field2}, {window})",
    "ts_cov({field1}, {field2}, {window})",
    "group_neutralize({field1} / {field2}, {group})",
    # 复合因子
    "group_neutralize({factor1} + {factor2}, {group})",
    "ts_mean(rank({field1}) * ts_rank({field2}, {window}), {window})",
]

def generate_quick_alphas(target_count=5000):
    """快速生成Alpha因子"""
    alpha_expressions = []
    seen = set()
    
    all_fields = MACRO_FIELDS + MODEL_FIELDS
    delays = [1, 2, 3, 5]
    
    while len(alpha_expressions) < target_count:
        template = random.choice(quick_templates)
        
        # 随机选择参数
        field = random.choice(all_fields)
        macro_field = random.choice(MACRO_FIELDS)
        field1 = random.choice(MODEL_FIELDS)
        field2 = random.choice(MACRO_FIELDS)
        window = random.choice(time_windows['medium'])
        delay = random.choice(delays)
        group = random.choice(groups)
        
        # 随机选择因子组件
        factor1 = f"ts_rank({random.choice(MODEL_FIELDS)}, 30)"
        factor2 = f"ts_rank({random.choice(MACRO_FIELDS)}, 30)"
        
        try:
            alpha_expr = template.format(
                field=field,
                macro_field=macro_field,
                field1=field1,
                field2=field2,
                window=window,
                delay=delay,
                group=group,
                factor1=factor1,
                factor2=factor2
            )
            
            # 简单去重
            if alpha_expr not in seen:
                seen.add(alpha_expr)
                alpha_expressions.append(alpha_expr)
                
        except (KeyError, ValueError):
            continue
        
        # 每500个输出一次进度
        if len(alpha_expressions) % 500 == 0:
            print(f"已生成 {len(alpha_expressions)} / {target_count} 个因子")
    
    return alpha_expressions

# 生成Alpha列表
print("="*60)
print("🎉 IND Region Alpha 生成器 (快速版)")
print("="*60)
print(f"📅 时间周期: {IND_CONFIG['duration']}")
print(f"💰 乘数: {IND_CONFIG['multiplier']}")
print(f"🌍 区域: {IND_CONFIG['region']}")
print(f"📊 目标因子数: 5000")
print("="*60)

alpha_expressions = generate_quick_alphas(5000)
print(f"\n✅ 成功生成 {len(alpha_expressions)} 个Alpha因子")

# 封装Alpha表达式
alpha_list = []
for alpha_expression in alpha_expressions:
    simulation_data = {
        "type": "REGULAR",
        "settings": {
            "instrumentType": "EQUITY",
            "region": IND_CONFIG['region'],
            "universe": IND_CONFIG['universe'],
            "delay": IND_CONFIG['delay'],
            "decay": random.choice([4, 5, 6, 7, 8]),
            "neutralization": random.choice(IND_CONFIG['allowed_pv1_group_fields']),
            "truncation": 0.01,
            "pasteurization": "ON",
            "unitHandling": "VERIFY",
            "nanHandling": "ON",
            "language": "FASTEXPR",
            "visualization": False,
        },
        "regular": alpha_expression
    }
    alpha_list.append(simulation_data)

print(f"✅ 已封装 {len(alpha_list)} 个待回测的Alpha")

# 显示示例
if alpha_list:
    print("\n📝 Alpha示例（前3个）：")
    for i, alpha in enumerate(alpha_list[:3], start=1):
        print(f"\n{i}. 类型: {alpha['type']}")
        print(f"   区域: {alpha['settings']['region']}")
        print(f"   Universe: {alpha['settings']['universe']}")
        print(f"   分组中性化: {alpha['settings']['neutralization']}")
        print(f"   表达式: {alpha['regular'][:100]}...")

# 保存到CSV文件 - 使用JSON格式保存settings
alpha_list_file_path = 'alpha_list_ind_region.csv'

# 将settings转换为JSON字符串
alpha_list_for_csv = []
for alpha in alpha_list:
    alpha_copy = alpha.copy()
    alpha_copy['settings'] = json.dumps(alpha['settings'])  # 转换为JSON字符串
    alpha_list_for_csv.append(alpha_copy)

with open(alpha_list_file_path, 'w', newline='') as output_file:
    dict_writer = csv.DictWriter(output_file, fieldnames=['type', 'settings', 'regular'])
    dict_writer.writeheader()
    dict_writer.writerows(alpha_list_for_csv)

print(f"\n✅ Alpha列表已保存到 {alpha_list_file_path}")
print(f"📊 总计: {len(alpha_list)} 个Alpha因子")

# 统计报告
print("\n" + "="*60)
print("📈 IND Region Alpha 生成统计报告")
print("="*60)

model_count = sum(1 for a in alpha_list if any(f'model{i}' in a['regular'] for i in range(1, 71)))
macro_count = len(alpha_list) - model_count

print(f"\nModel类别因子: {model_count} 个 ({model_count/len(alpha_list)*100:.1f}%)")
print(f"Macro类别因子: {macro_count} 个 ({macro_count/len(alpha_list)*100:.1f}%)")

group_neutral_count = sum(1 for a in alpha_list if 'group_neutralize' in a['regular'] or 'group_rank' in a['regular'])
print(f"\n使用分组中性化的因子: {group_neutral_count} 个 ({group_neutral_count/len(alpha_list)*100:.1f}%)")

print("\n" + "="*60)
print("🎯 IND Region Alpha 生成完成！")
print("="*60)


