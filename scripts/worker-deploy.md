# 用 Cloudflare Worker 给 GitHub Actions 装一个可靠的闹钟

GitHub 自带的 `schedule` 对低活跃仓库不可靠（实测：延迟 6 小时，甚至整天不触发）。
本方案用一个 Cloudflare Worker 每天准点调用 GitHub 的「手动触发」接口，
执行仍然在 GitHub Actions 里，代码和数据不用迁移。

做完之后你会得到：

- **定时**：工作日北京时间 16:30 自动刷新
- **一键**：手机书签点一下立即刷新
- **成本**：0 元（Workers 免费版每天 10 万次请求，我们用 1 次）

---

## 第 1 步：创建受限 Token

1. 打开 <https://github.com/settings/personal-access-tokens/new>
   （注意是 **Fine-grained**，不是 Classic）
2. 填写：
   - **Token name**：`futures-basis-trigger`
   - **Expiration**：1 year（一年后重做一次）
   - **Repository access**：选 `Only select repositories` → 勾选 `futures-basis`
3. 展开 **Permissions** → **Repository permissions**，只改一项：
   - **Actions** → `Read and write`
   - 其余全部保持 `No access`
4. 点 **Generate token**，复制 `github_pat_xxxxx`

> 这把钥匙**只能按「Run workflow」按钮**，读不到代码、改不了代码、看不到你的设置。
> 即使泄露，最坏结果是别人能触发你的任务、消耗几十秒 Actions 额度。

---

## 第 2 步：创建 Worker

1. 打开 <https://dash.cloudflare.com>，注册或登录（免费，邮箱即可，不需要信用卡）
2. 左侧 **Workers & Pages** → **Create**（或 Create application）
3. 选 **Workers** → **Start with Hello World**（模板不限，之后会整个替换）
4. 名称填 `futures-basis-cron` → **Deploy**
5. 点 **Edit code**（编辑代码），把编辑器里的示例代码**全部删掉**，
   粘贴 `scripts/worker.js` 的完整内容
6. 右上角 **Deploy**（部署）

> Cloudflare 的界面偶尔改版，核心就是找到「创建 Worker → 编辑代码 → 部署」这条路径。

---

## 第 3 步：配置变量

Worker 页面 → **Settings**（设置）→ **Variables and Secrets**（变量和密钥）→ **Add**

| 变量名 | 值 | 类型 |
|---|---|---|
| `GH_TOKEN` | 第 1 步复制的 `github_pat_...` | **Secret**（加密） |
| `REPO` | `SummerNT/futures-basis` | Text（明文） |
| `TRIGGER_KEY` | 自己编一串随机字符，如 `fb-7k2m9x` | **Secret**（加密） |
| `WORKFLOW` | `daily.yml` | Text（可省略，默认就是它） |
| `BRANCH` | `main` | Text（可省略，默认就是它） |

保存后**再点一次 Deploy**，变量才生效。

---

## 第 4 步：设置定时

Worker 页面 → **Settings** → **Triggers**（触发器）→ **Cron Triggers** → **Add Cron Trigger**

填入：

```
30 8 * * 1-5
```

这是 UTC 时间，对应**北京时间 16:30，周一到周五**。

> Cloudflare 的 cron 用的是 UTC，别填成 `30 16`，那会是北京时间第二天 00:30。

---

## 第 5 步：验证

**先测手动触发**，浏览器打开：

```
https://futures-basis-cron.<你的workers子域>.workers.dev/trigger?key=你设的TRIGGER_KEY
```

子域名在 Worker 页面顶部能看到，形如 `futures-basis-cron.yourname.workers.dev`。

预期返回：

```
2026-10-27 16:30 (Beijing) OK triggered SummerNT/futures-basis/daily.yml@main
```

然后去 <https://github.com/SummerNT/futures-basis/actions> 看一眼，
应该有一条 `event=workflow_dispatch` 的运行，几十秒后变绿。

**如果返回 FAIL：**

| 返回 | 原因 |
|---|---|
| `401` | token 没填对，或已过期 |
| `403` | token 权限不够（要 Actions: Read and write），或没勾选这个仓库 |
| `404` | `REPO` 变量写错，或者 `WORKFLOW` 文件名不对 |
| `ERR missing REPO or GH_TOKEN` | 变量没生效，回第 3 步重新 Deploy |

---

## 第 6 步：手机存一键书签

把第 5 步那个 URL 存进手机浏览器书签，或者「添加到主屏幕」。

以后每天想手动刷新，点一下就行。

> **定时触发不依赖你访问这个 URL。** 即使 `workers.dev` 在你手机上打不开，
> Cloudflare 的服务器照样会在 16:30 调它 —— 那是两回事。

---

## 顺带要做的事

Worker 生效后，**把 GitHub 里不可靠的定时关掉**，避免两边同时提交产生冲突：

编辑 `.github/workflows/daily.yml`，把 `schedule:` 那三行注释掉，只保留 `push` 和 `workflow_dispatch`：

```yaml
on:
  # schedule:              # GitHub 自带定时不可靠，改由 Cloudflare Worker 触发
  #   - cron: "13 8 * * 1-5"
  #   - cron: "43 8 * * 1-5"
  #   - cron: "13 10 * * 1-5"
  push:
    branches: [main]
    paths:
      - "src/**"
      - "run.py"
      - ".github/workflows/daily.yml"
  workflow_dispatch:
```

---

## 为什么不用 cron-job.org

| | Cloudflare Worker | cron-job.org |
|---|---|---|
| token 存放 | 你自己的账号，加密 Secret | 第三方服务器，明文保存 |
| 手动触发端点 | 自带 | 没有 |
| 定制能力 | 可以随便改代码 | 只能填表单 |
| 成本 | 免费 | 免费 |

两者都能用，Worker 只是把钥匙留在自己手里。
