import requests
from requests.auth import HTTPBasicAuth
import time
import random
import functools
from datetime import datetime
import argparse
import os
import pandas as pd

#  版本说明：增加打标签，方便平台查找并手动提交
# 创建命令行参数解析器，根据需要可调整日期
parser = argparse.ArgumentParser(description='Check Submission')
parser.add_argument('--credentials_file', type=str, default="brain_credentials.txt", help='账号文件')
parser.add_argument('--start_date', type=str, default="06-01", help='开始日期 (MM-DD格式)')
parser.add_argument('--end_date', type=str, default="12-31", help='结束日期 (MM-DD格式)')
parser.add_argument('--alpha_num', type=int, default=10000, help='要检查的Alpha数量')
parser.add_argument('--sharpe_th', type=float, default=1.25, help='Sharpe阈值')
parser.add_argument('--fitness_th', type=float, default=1.0, help='Fitness阈值')
parser.add_argument('--turnover_th', type=float, default=0.3, help='Turnover阈值')
parser.add_argument('--region', type=str, default="USA", help='地区')
parser.add_argument('--blacklist_file', type=str, default="blacklist.txt", help='黑名单文件路径')
# 新增配置：是否将检查通过的Alpha加入黑名单，默认False（不加入）
parser.add_argument('--add_passed_to_blacklist', type=bool, default=False, help='是否将检查通过的Alpha加入黑名单 (默认: False)')

args = parser.parse_args()

# 从文件读取凭据
def read_credentials(file_path):
    username = ""
    password = ""
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r') as file:
                content = file.read().strip()
                # 解析JSON格式
                import json
                credentials = json.loads(content)
                if len(credentials) >= 1:
                    username = credentials[0]
                if len(credentials) >= 2:
                    password = credentials[1]
            return username, password
        else:
            print(f"凭据文件 {file_path} 不存在")
            return "", ""
    except json.JSONDecodeError as e:
        print(f"凭据文件格式错误，请确保格式为 [\"your email\",\"password\"]: {e}")
        return "", ""
    except Exception as e:
        print(f"读取凭据文件时出错: {e}")
        return "", ""


# 读取黑名单（文件不存在时创建）
def read_blacklist(file_path):
    blacklist = set()
    try:
        if not os.path.exists(file_path):
            with open(file_path, 'w') as file:
                pass
            print(f"黑名单文件 {file_path} 不存在，已创建新文件")
        else:
            with open(file_path, 'r') as file:
                for line in file:
                    blacklist.add(line.strip())
            print(f"已从黑名单文件中读取 {len(blacklist)} 个Alpha ID")
    except Exception as e:
        print(f"读取或创建黑名单文件时出错: {e}")
    return blacklist


# 更新黑名单（实时写入）
def update_blacklist(file_path, alpha_id):
    try:
        with open(file_path, 'a') as file:
            file.write(f"{alpha_id}\n")
            print(f"已实时将通过的Alpha ID {alpha_id} 添加到黑名单")
        return True
    except Exception as e:
        print(f"实时更新黑名单文件时出错: {e}")
        return False

def sign_in():
    username = ""
    password = ""
    credentials_path = "brain_credentials.txt"
    # Open the credentials file and read the username and password
    try:
        with open(credentials_path, "r") as file:
            content = file.read().strip()
            # 解析JSON格式
            import json
            credentials = json.loads(content)
            username = credentials[0] if len(credentials) >= 1 else ""
            password = credentials[1] if len(credentials) >= 2 else ""
    except FileNotFoundError:
        print(f"Error: The file '{credentials_path}' was not found.")
        return None
    except json.JSONDecodeError as e:
        print(f"Error: 凭据文件格式错误，请确保格式为 [\"your email\",\"password\"]: {e}")
        return None
    except Exception as e:
        print(f"An error occurred while reading the credentials file: {e}")
        return None

    s = requests.Session()
    s.auth = (username, password)
    while True:
        try:
            response = s.post('https://api.worldquantbrain.com/authentication')
            response.raise_for_status()  # Raises a HTTPError if the status is 4xx, 5xx
            print(f"{response.json()['user']['id']},Authentication successful.")
            break  # Exit the loop on success
        except requests.HTTPError as e:
            print(f"HTTP error occurred: {e}. Retrying...")  # Provide more specific error message
            time.sleep(10)
        except Exception as e:
            print(f"Error during authentication: {e}. Trying to login again.")
            time.sleep(10)
    return s

def session_close(session):
    session.close()

def requests_wq(s,type='get',url='',json=None,t=15):
    session = s
    while True:
        try:
            if type == 'get':
                ret = session.get(url)
            if type == 'post':
                if json == None:
                    ret = session.post(url)
                else:
                    ret = session.post(url, json=json)
            if type == 'patch':
                ret = session.patch(url, json=json)
            if ret.status_code == 429:
                print(f"状态={ret.status_code},延时{t}秒")
                time.sleep(t)
                continue
            if ret.status_code in (200,201):
                return ret, session
            if ret.status_code == 401:
                session = sign_in()
                continue
            else:
                print(f"\033[31m状态={ret.status_code}，continue\033[0m")
                continue
        except requests.RequestException as e:
            print(f"Error during method execution: {e}. Retrying...")
            time.sleep(10)
            session = sign_in()
            print(f"延时10秒，重新连接")
    return None, None
# 检查Alpha提交状态（带超时）
def get_check_submission(s, alpha_id):
    sess = s
    while True:
        #result = s.get(f"https://api.worldquantbrain.com/alphas/{alpha_id}/check", timeout=30)
        result,sess = requests_wq(sess,'get',f"https://api.worldquantbrain.com/alphas/{alpha_id}/check")
        if "retry-after" in result.headers:
            time.sleep(float(result.headers["Retry-After"]))
        else:
            break
    if result.json().get("is", 0) == 0:
        print(f"Alpha {alpha_id}: logged out，返回 'sleep'")
        return "sleep",sess
    checks_df = pd.DataFrame(result.json()["is"]["checks"])
    # 检查 SELF_CORRELATION 是否为 "nan"
    self_correlation_value = checks_df[checks_df["name"] == "SELF_CORRELATION"]["value"].values[0]
    pc = self_correlation_value
    if any(checks_df["result"] == "ERROR"):
        print(f"Alpha {alpha_id}: \033[31m ERROR \033[0m，检查失败")
        return "ERROR",sess
    if any(checks_df["result"] == "FAIL"):
        print(f"Alpha {alpha_id}: \033[31m FAIL \033[0m，检查失败")
        return "FAIL",sess
    if pd.isna(self_correlation_value) or str(self_correlation_value).lower() == "nan":
        print(f"Alpha {alpha_id}: SELF_CORRELATION 为 \033[31m nan \033[0m，检查失败")
        return "nan",sess
    return pc,sess
def set_alpha_properties(
        s,
        alpha_id,
        name: str = None,
        color: str = None,
        selection_desc: str = "None",
        combo_desc: str = "None",
        tags: str = "ace_tag",
        regular_desc: str = "None"
):
    """
    Function changes alpha's description parameters
    """
    sess = s
    params = {
        "color": color,
        "name": name,
        "tags": [tags],
        "category": None,
        "regular": {"description": regular_desc},
        "combo": {"description": combo_desc},
        "selection": {"description": selection_desc},
    }
    response,sess = requests_wq(sess,'patch',"https://api.worldquantbrain.com/alphas/" + alpha_id,params)
    return response,sess

# 读取凭据
username, password = read_credentials(args.credentials_file)
if not username or not password:
    print("未能获取有效的用户名或密码，请检查凭据文件，如无请创建credentials.txt，文件首行邮箱账号，第二行平台密码,不需要其他符号")
    exit()

# 读取黑名单
blacklist = read_blacklist(args.blacklist_file)

# 设置其他参数
sharpe_th = args.sharpe_th
fitness_th = args.fitness_th
turnover_th = args.turnover_th

start_date = args.start_date
end_date = args.end_date
alpha_num = args.alpha_num
region = args.region


# 获取特定状态的Alpha数量
def get_alpha_count(s,status):
    sess = s
    try:
        url = f"https://api.worldquantbrain.com/users/self/alphas?limit=1&status={status}"
        response,sess = requests_wq(sess,'get',url)
        if response.status_code < 300:
            count = response.json().get('count', 0)
            return count,sess
        else:
            print(f"获取状态为 '{status}' 的Alpha数量失败: {response.status_code}")
            return None,sess
    except Exception as e:
        print(f"获取状态为 '{status}' 的Alpha数量时出错: {e}")
        return None,sess
# 获取有效Alpha
def get_alphas(s,start_date, end_date, sharpe_th, fitness_th, turnover_th, region, alpha_num):
    sess = s
    output = []
    count = 0
    current_year = datetime.now().strftime('%Y')
    for i in range(0, alpha_num, 100):
        print(i)
        url = f"https://api.worldquantbrain.com/users/self/alphas?limit=100&offset={i}" \
              f"&status=UNSUBMITTED%1FIS_FAIL&dateCreated%3E={current_year}-{start_date}" \
              f"T00:00:00-04:00&dateCreated%3C{current_year}-{end_date}" \
              f"T00:00:00-04:00&is.fitness%3E{fitness_th}&is.sharpe%3E{sharpe_th}" \
              f"&settings.region={region}&order=is.sharpe&hidden=false&type!=SUPER" \
              f"&is.turnover%3C{turnover_th}"

        #response = s.get(url)
        response,sess = requests_wq(sess,'get',url)
        alpha_list = response.json()["results"]
        if len(alpha_list) == 0: break
        for j in range(len(alpha_list)):
            alpha_id = alpha_list[j]["id"]
            if alpha_id in blacklist:
                print(f"跳过ID为 {alpha_id} 的Alpha，因为它在黑名单中")
                continue
            name = alpha_list[j]["name"]
            dateCreated = alpha_list[j]["dateCreated"]
            sharpe = alpha_list[j]["is"]["sharpe"]
            fitness = alpha_list[j]["is"]["fitness"]
            turnover = alpha_list[j]["is"]["turnover"]
            margin = alpha_list[j]["is"]["margin"]
            longCount = alpha_list[j]["is"]["longCount"]
            shortCount = alpha_list[j]["is"]["shortCount"]
            decay = alpha_list[j]["settings"]["decay"]
            exp = alpha_list[j]['regular']['code']
            count += 1
            checks = alpha_list[j].get("is", {}).get("checks", [])
            has_failed_checks = any(check.get('result') == 'FAIL' for check in checks if check)
            if has_failed_checks:
                print(f"跳过ID为 {alpha_id} 的Alpha，因为它有失败的检查项")
                continue
            if (longCount + shortCount) > 100 and turnover < turnover_th:
                if sharpe < -sharpe_th:
                    exp = "-%s" % exp
                rec = [alpha_id, exp, sharpe, turnover, fitness, margin, dateCreated, decay]
                print(rec)
                output.append(rec)
    print("count: %d" % count)
    return output,sess


# 主程序
def main():
    print("=== Check Submission ===")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"凭据文件: {args.credentials_file}")
    print(f"黑名单文件: {args.blacklist_file}")
    print(f"日期范围: {start_date} 至 {end_date}")
    print(f"检查的Alpha数量: {alpha_num}")
    print(f"地区: {region}")
    print(f"Sharpe阈值: {sharpe_th}")
    print(f"Fitness阈值: {fitness_th}")
    print(f"Turnover阈值: {turnover_th}")
    print(f"检查通过的Alpha是否加入黑名单: {args.add_passed_to_blacklist}")  # 新增显示

    if not username or not password:
        print("未能获取有效的用户名或密码，请检查凭据文件格式。")
        print("凭据文件应为JSON格式：[\"your_email@example.com\",\"your_password\"]")
        print("如无brain_credentials.txt文件请创建，文件内容示例：[\"user@example.com\",\"password123\"]")
        exit()
    s = sign_in()
    if not s:
        print("登录失败，程序退出")
        return

    initial_submitted_count,s = get_alpha_count(s,"ACTIVE")
    if initial_submitted_count is not None:
        print(f"平台上已提交的Alpha数量: {initial_submitted_count}")
    else:
        print("无法计算ACTIVE，请检查登录凭据或网络连接")
    print("\n正在获取Alpha列表...")
    print(f"\n搜索符合条件的有效alpha (Sharpe >= {sharpe_th}, Fitness >= {fitness_th}, Turnover < {turnover_th})...")
    valid_alphas_data,s = get_alphas(s,start_date, end_date, sharpe_th, fitness_th, turnover_th, region, alpha_num)
    valid_alphas = [alpha[0] for alpha in valid_alphas_data]
    alpha_metrics = {
        alpha[0]: {"exp": alpha[1], "sharpe": alpha[2], "turnover": alpha[3], "fitness": alpha[4], "margin": alpha[5]}
        for alpha in valid_alphas_data}

    print(f"找到 {len(valid_alphas)} 个有效Alpha（不包含失败检查项和黑名单中的Alpha）")

    if not valid_alphas:
        print("没有发现符合条件的有效Alpha，无需提交。")
        return

    print(f"\n准备检测 {len(valid_alphas)} 个有效Alpha")
    failed = 0
    for i, alpha_id in enumerate(valid_alphas):
        print(
            f"检查 {i + 1}/{len(valid_alphas)}: {alpha_id}  [Sharpe: {alpha_metrics[alpha_id]['sharpe']},turnover: {alpha_metrics[alpha_id]['turnover']}, Fitness: {alpha_metrics[alpha_id]['fitness']}, margin: {alpha_metrics[alpha_id]['margin']}]")
        if alpha_metrics[alpha_id]['exp'].startswith("para_") or alpha_metrics[alpha_id]['exp'].startswith("var_") or alpha_metrics[alpha_id]['exp'].startswith("trade_when"):
            print(f"[exp: {alpha_metrics[alpha_id]['exp']}")
        else:
            print(f"[exp: {alpha_metrics[alpha_id]['exp']}")
        # 先检查Alpha状态，处理 "sleep" 和超时逻辑
        for count_i in range(3):  #3次机会
            check_result,s = get_check_submission(s, alpha_id)
            if check_result != "sleep" or check_result != "timeout":
                break
            if check_result == "sleep":
                #延时40S
                time.sleep(40)
                continue
        print(f"alphaId={alpha_id},check_result={check_result}")
        if check_result in ("timeout","nan","ERROR","error"):
            print(f"Alpha={alpha_id}: \033[33m 检查结果:timeout,打上标签timeout,，到平台查看Tag-timeout,并手动检查 \033[0m")
            set_alpha_properties(s, alpha_id, name=datetime.now().strftime("%Y.%m.%d"), color=None, selection_desc="None", combo_desc="None",
                                 tags="timeout", )
            continue
        elif check_result == "FAIL":
            print(f"检查结果: 错误 (FAIL)，列入黑名单")
            set_alpha_properties(s, alpha_id, name=datetime.now().strftime("%Y.%m.%d"), color=None, selection_desc="None", combo_desc="None",
                                 tags="Blacklist", )
            failed += 1
            if update_blacklist(args.blacklist_file, alpha_id):
                blacklist.add(alpha_id)
                continue
        else:
            print(f"Alpha {alpha_id}: \033[32m 检查通过,打上OKOK标签,到平台查看Tag-OKOK,并手动提交 \033[0m")
            set_alpha_properties(s, alpha_id, name=datetime.now().strftime("%Y.%m.%d"), color=None, selection_desc="None", combo_desc="None",
                                 tags="OKOK", )
            # 根据配置决定是否将检查通过的Alpha加入黑名单
            if args.add_passed_to_blacklist:
                if update_blacklist(args.blacklist_file, alpha_id):
                    blacklist.add(alpha_id)
                    print(f"Alpha {alpha_id}: 已加入黑名单")
            else:
                print(f"Alpha {alpha_id}: 检查通过，未加入黑名单")

    print(f"\n通过检查:")
    print(f"总共: {len(valid_alphas)} 个Alpha")
    print(f"失败: {failed} 个")

if __name__ == "__main__":
    main()