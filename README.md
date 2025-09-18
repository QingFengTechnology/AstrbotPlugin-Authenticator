![AstrbotPlugin-Authenticator](https://socialify.git.ci/QingFengTechnology/AstrbotPlugin-Authenticator/image?description=1&font=KoHo&language=1&logo=data%3Aimage%2Fsvg%2Bxml%3Bbase64%2CPHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0Ij4KCTxnIGZpbGw9Im5vbmUiIHN0cm9rZT0iIzRFNkNGRSIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIiBzdHJva2Utd2lkdGg9IjEuNSI%2BCgkJPHBhdGggZD0iTTIwLjcyNSA2LjE2NmEyLjQyIDIuNDIgMCAwIDAtMS43NzEuNzg2Yy0uMjE2LTEuMDIzLS44NTktMS4zMjQtMS41OTMtMS42NjVjLS40NjUtLjIxNi0uNjU5LS42OTYtLjcyMi0xLjA0M2MtLjAyNC0uMTMzLS4xMzMtLjI0LS4yNjgtLjI0Yy0uMTM0IDAtLjI2Mi4wNTUtLjMyNi4xNzNjLS4xNC4yNS0uMzU0LjgtLjM3MyAxLjgxYy0uMDI5IDEuNTAzIDEuMjEgMi42NjIgMS44MzQgMy4wNTNjLS4wNjQuMzctLjI5Ljk0Mi0uMzk1IDEuMTgyYTQuOSA0LjkgMCAwIDEtMS44Ny0xLjIzNGMtLjk1OC0xLjA0My0xLjczOC0xLjc4MS0yLjc1Ni0yLjUwM3MtLjMzNy0xLjU4My4wOS0xLjc4OHMuMTAzLS40MTUtLjk2Mi0uMzc5Yy0uODUzLjAyOS0yLjA2Ny41My0yLjU2Ny43NzdjLS41MS0uMTYyLTEuNTcyLS4xOTQtMi4wMzgtLjE5QzIuNDI1IDQuOTA1IDEgOC45OCAxIDExYzAgNi4wODYgNC44NzMgOSA4LjM3MyA5YzMuOTU4IDAgNS4zNDUtMS42MTQgNS4zNDUtMS42MTRjLjE2NC4xMDEuNzYuMzE2IDEuODM4LjM2MmMxLjM0OS4wNTcgMS44NTEtLjMyNCAxLjg5LS42MTdzLS4xNzktLjQtLjM3LS40OWMtLjE5LS4wODktLjQ5LS4yNi0xLjA1NS0uNDQ1Yy0uNDUzLS4xNDctLjY1Ny0uMzA4LS43MDItLjM3YzIuNzMtMi40NzIgMy4yMy01LjkzNSAzLjE1My03LjQwN2MyLjExMi0uMDgyIDIuOTQzLTEuNDg4IDMuMjE3LTIuMmMuMjgtLjcyNi40NTQtMS43MTYuMTY0LTEuOTRjLS4yMzItLjE4LS40MjYuMDM2LS40OTQuMTY3Yy0uMzcyLjM5Ni0uNjQ0LjcxOS0xLjYzNS43MTkiIC8%2BCgkJPHBhdGggZD0iTTEyIDEwLjU2OHMuODc2LS4yNyAxLjY0NS4yNTVjMS4wNDEuNzEgMS4zNTUgMS42NzYgMS4zNTUgMS42NzZtLTEuNSA0cy0xLjA0MS0uNTA3LTIuNjA0LTIuNTM5Yy0xLjg3OC0yLjQ0LTMuNjQ3LTUuMDc0LTcuMzY3LTQuMjEzYzAgMC0uMDI5IDUuMjUgNC45NzEgNi43NTIiIC8%2BCgk8L2c%2BCjwvc3ZnPg%3D%3D&name=1&pattern=Circuit+Board&theme=Auto)

这是一个强大的身份验证插件，旨在提供一个完整的身份验证流程系统以实现全自动筛选人机~~和部分智力低下的类人~~。

## 功能

- **详细的插件配置，可自定义绝大部分内容**
- 支持群聊白名单，避免在意外群聊中触发验证
- 模块化设计，可自由开关各个功能
- 基于关键词的加群请求审核
  - 支持等级限制，仅允许指定等级以上的用户申请入群
  - 支持设定延迟，降低风控风险
- 通过简易验证判断入群者是否为人机
- 黑名单功能
  - 支持自动拒绝黑名单用户的加群请求
  - 支持忽略黑名单用户的消息
  - 支持自动踢出黑名单用户

## 安装

在 Astrbot WebUI 插件页面点击`安装`按钮，选择`从链接安装`，复制粘贴本仓库 URL 并点击安装即可。

## 使用

插件安装后默认不启用任何功能，在插件配置中开启你需要的功能即可开始使用。

> [!Note]
> 使用此插件的机器人账号需要为你指定群聊的管理员。\
> 插件不会检测当前账号在触发操作的群聊是否为管理员。

## 配置

### 黑名单功能配置

黑名单功能提供以下配置选项：

- **Ban_Enable**: 是否启用黑名单功能
- **BanConfig_IgnoreUser**: 是否忽略黑名单用户的消息
- **BanConfig_RejectInvitationConfig**: 拒绝加群请求配置
  - **Enable**: 是否拒绝黑名单用户的加群请求
  - **Reason**: 拒绝理由
- **BanConfig_AutoKickConfig**: 自动踢出配置
  - **Enable**: 是否自动踢出黑名单用户
  - **Interval**: 检查间隔（秒）
  - **Reason**: 踢出理由

### 黑名单命令

- `ban add <QQ号>` - 将用户添加到黑名单
- `ban remove <QQ号>` - 从黑名单中移除用户
- `ban list` - 查看当前黑名单列表
- `ban check <QQ号>` - 检查用户是否在黑名单中

> [!Note]
> 黑名单命令需要管理员或群主权限才能执行。

<details>
<summary>插件原始配置文件(<code>_conf_schema.json</code>)</summary>

```json
{
  "WhitelistGroups": {
    "description": "群聊白名单",
    "type": "list",
    "default": [],
    "hint": "仅在这些群聊中使用本插件，留空则在所有群聊中启用。"
  },
  "AutomaticReview": {
    "type": "object",
    "description": "加群请求审核相关配置",
    "items": {
      "AutomaticReview_Enable": {
        "type": "bool",
        "description": "是否启用请求审核功能",
        "default": false
      },
      "AutomaticReview_KeywordsConfig": {
        "type": "object",
        "description": "关键词相关配置",
        "items": {
          "KeywordsConfig_AcceptKeywords": {
            "type": "list",
            "description": "自动同意关键词",
            "hint": "当申请消息中包含这些关键词时，将自动同意加群请求。",
            "default": []
          },
          "KeywordsConfig_RejectKeywords": {
            "type": "list",
            "description": "自动拒绝关键词",
            "hint": "当申请消息中包含这些关键词时，将自动拒绝加群请求。",
            "default": []
          },
          "KeywordsConfig_RejectReason": {
            "type": "string",
            "description": "拒绝申请时使用的理由",
            "default": "申请被拒绝。"
          }
        }
      },
      "AutomaticReview_DelaySeconds": {
        "type": "int",
        "description": "延迟处理时间",
        "hint": "处理入群申请前等待的秒数，设为0以禁用该功能。",
        "default": 0
      }
    }
  },
  "SimpleReCAPTCHA": {
    "type": "object",
    "description": "人机验证相关配置",
    "items": {
      "SimpleReCAPTCHA_Enable": {
        "type": "bool",
        "description": "是否启用人机验证功能",
        "default": false
      },
      "SimpleReCAPTCHA_VerificationTimeout": {
        "description": "验证超时时间",
        "type": "int",
        "default": 180,
        "hint": "成员须在此时间内完成验证，否则将被踢出，单位为秒。"
      },
      "SimpleReCAPTCHA_KickDelay": {
        "description": "验证超时后踢出延迟",
        "type": "int",
        "default": 3,
        "hint": "发送验证超时消息后，等待多少秒再执行踢出操作。"
      },
      "SimpleReCAPTCHA_MessageConfig": {
        "type": "object",
        "description": "验证消息配置",
        "hint": "如你不了解部分占位符指代的内容，请参阅插件README中的说明。",
        "obvious_hint": true,
        "items": {
          "MessageConfig_Join": {
            "description": "成员入群提示",
            "type": "string",
            "default": "{at_user} 欢迎加入本群！请在 {timeout} 分钟内 @我 并回答下面的问题以完成验证：\n{question}",
            "hint": "成员入群时发送的验证信息，可用变量: {at_user}, {member_name}, {question}, {timeout}。"
          },
          "MessageConfig_Success": {
            "description": "验证成功提示",
            "type": "string",
            "default": "{at_user} 验证成功，欢迎你的加入！",
            "hint": "成员回答正确后发送的消息，可用变量: {at_user}, {member_name}。"
          },
          "MessageConfig_Wrong": {
            "description": "答案错误提示",
            "type": "string",
            "default": "{at_user} 答案错误，请重新回答验证。这是你的新问题：\n{question}",
            "hint": "成员回答错误后发送的消息，之后会自动生成新问题。可用变量: {at_user}, {question}。"
          },
          "MessageConfig_CountdownWarningConfig": {
            "type": "object",
            "description": "超时警告配置",
            "items": {
              "CountdownWarningConfig_Time": {
                "description": "警告倒计时",
                "type": "int",
                "default": 60,
                "hint": "在验证超时前多少秒提示成员尽快进行验证，设为0以禁用该功能。"
              },
              "CountdownWarningConfig_Message": {
                "description": "超时警告提示",
                "type": "string",
                "default": "{at_user} 验证即将超时，请尽快查看我的验证消息并进行人机验证！",
                "hint": "在验证即将超时前发送的警告消息，可用变量: {at_user}, {member_name}。"
              }
            }
          },
          "MessageConfig_FailureConfig": {
            "type": "object",
            "description": "验证超时配置",
            "items": {
              "FailureConfig_Enable": {
                "description": "是否启用验证超时提示",
                "type": "bool",
                "default": false
              },
              "FailureConfig_Message": {
                "description": "验证超时提示",
                "type": "string",
                "default": "{at_user} 验证超时，请重新申请加入本群。",
                "hint": "成员验证超时后发送的消息，可用变量: {at_user}, {member_name}。"
              }
            }
          },
          "MessageConfig_KickConfig": {
            "type": "object",
            "description": "最终踢出配置",
            "items": {
              "KickConfig_Enable": {
                "description": "是否启用最终踢出提示",
                "type": "bool",
                "default": false
              },
              "KickConfig_Message": {
                "description": "最终踢出提示",
                "type": "string",
                "default": "{at_user} 因未在规定时间内完成验证，已被请出本群。",
                "hint": "成员被踢出后发送的公开消息，可用变量: {at_user}, {member_name}。"
              }
            }
          }
        }
      }
    }
  }
}
```

</details>

### 配置占位符定义

- **{at_user}**：@目标用户。
- **{member_name}**：目标用户的昵称。
- **{question}**：当前验证问题。
- **{timeout}**：*仅部分配置可用*，验证超时时间，这将自动转为分钟。

## 鸣谢

- **[DeepSeek](https://chat.deepseek.com)** 本项目大部分的代码都是 AI 编写，后续维护也交由 AI 维护。
- **[qiqi55488](https://github.com/qiqi55488)** 本项目主要功能模块之一参考自[这位开发者的插件](https://github.com/qiqi55488/astrbot_plugin_appreview)。
- **[huntuo146](https://github.com/huntuo146)** 本项目主要功能模块之一参考自[这位开发者的插件](https://github.com/huntuo146/astrbot_plugin_Group-Verification_PRO)。