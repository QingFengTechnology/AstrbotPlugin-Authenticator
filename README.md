![AstrbotPlugin-Authenticator](https://socialify.git.ci/QingFengTechnology/AstrbotPlugin-Authenticator/image?description=1&font=KoHo&language=1&logo=data%3Aimage%2Fsvg%2Bxml%3Bbase64%2CPHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0Ij48ZyBmaWxsPSJub25lIiBzdHJva2U9IiNmZmYiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCIgc3Ryb2tlLXdpZHRoPSIxIj48cGF0aCBkPSJNMjAuNzI1IDYuMTY2YTIuNDIgMi40MiAwIDAgMC0xLjc3MS43ODZjLS4yMTYtMS4wMjMtLjg1OS0xLjMyNC0xLjU5My0xLjY2NWMtLjQ2NS0uMjE2LS42NTktLjY5Ni0uNzIyLTEuMDQzYy0uMDI0LS4xMzMtLjEzMy0uMjQtLjI2OC0uMjRjLS4xMzQgMC0uMjYyLjA1NS0uMzI2LjE3M2MtLjE0LjI1LS4zNTQuOC0uMzczIDEuODFjLS4wMjkgMS41MDMgMS4yMSAyLjY2MiAxLjgzNCAzLjA1M2MtLjA2NC4zNy0uMjkuOTQyLS4zOTUgMS4xODJhNC45IDQuOSAwIDAgMS0xLjg3LTEuMjM0Yy0uOTU4LTEuMDQzLTEuNzM4LTEuNzgxLTIuNzU2LTIuNTAzcy0uMzM3LTEuNTgzLjA5LTEuNzg4cy4xMDMtLjQxNS0uOTYyLS4zNzljLS44NTMuMDI5LTIuMDY3LjUzLTIuNTY3Ljc3N2MtLjUxLS4xNjItMS41NzItLjE5NC0yLjAzOC0uMTlDMi40MjUgNC45MDUgMSA4Ljk4IDEgMTFjMCA2LjA4NiA0Ljg3MyA5IDguMzczIDljMy45NTggMCA1LjM0NS0xLjYxNCA1LjM0NS0xLjYxNGMuMTY0LjEwMS43Ni4zMTYgMS44MzguMzYyYzEuMzQ5LjA1NyAxLjg1MS0uMzI0IDEuODktLjYxN3MtLjE3OS0uNC0uMzctLjQ5Yy0uMTktLjA4OS0uNDktLjI2LTEuMDU1LS40NDVjLS40NTMtLjE0Ny0uNjU3LS4zMDgtLjcwMi0uMzdjMi43My0yLjQ3MiAzLjIzLTUuOTM1IDMuMTUzLTcuNDA3YzIuMTEyLS4wODIgMi45NDMtMS40ODggMy4yMTctMi4yYy4yOC0uNzI2LjQ1NC0xLjcxNi4xNjQtMS45NGMtLjIzMi0uMTgtLjQyNi4wMzYtLjQ5NC4xNjdjLS4zNzIuMzk2LS42NDQuNzE5LTEuNjM1LjcxOSIvPjxwYXRoIGQ9Ik0xMiAxMC41NjhzLjg3Ni0uMjcgMS42NDUuMjU1YzEuMDQxLjcxIDEuMzU1IDEuNjc2IDEuMzU1IDEuNjc2bS0xLjUgNHMtMS4wNDEtLjUwNy0yLjYwNC0yLjUzOWMtMS44NzgtMi40NC0zLjY0Ny01LjA3NC03LjM2Ny00LjIxM2MwIDAtLjAyOSA1LjI1IDQuOTcxIDYuNzUyIi8%2BPC9nPjwvc3ZnPg%3D%3D&name=1&pattern=Solid&theme=Auto)

这是一个强大的身份验证插件，旨在提供一个完整的身份验证流程系统以实现全自动筛选人机~~和部分智力低下的类人~~。

## 功能

- **详细的插件配置，可自定义绝大部分内容**
- 支持群聊白名单，避免在意外群聊中触发验证
- 模块化设计，可自由开关各个功能
- 基于关键词的加群请求审核
  - 也同样支持不验证自动通过/拒绝所有请求
  - 支持设定延迟，降低风控风险
- 通过简易验证判断入群者是否为人机

## 安装

在 Astrbot WebUI 插件页面点击`安装`按钮，选择`从链接安装`，复制粘贴本仓库 URL 并点击安装即可。

## 使用

插件安装后默认不启用任何功能，在插件配置中开启你需要的功能即可开始使用。

## 配置

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
      "AutomaticReview_AutoReviewConfig": {
        "type": "object",
        "description": "自动审核相关配置",
        "items": {
          "AutoReviewConfig_Enable": {
            "type": "string",
            "description": "是否启用该功能",
            "hint": "配置为`None`时不启用该功能；`False`表示自动拒绝所有请求；`True`表示自动同意所有请求。",
            "options": [
              "None",
              "True",
              "False"
            ],
            "default": "None"
          },
          "AutoReviewConfig_RejectReason": {
            "type": "string",
            "description": "自动拒绝理由",
            "hint": "自动拒绝申请时所使用的理由。",
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