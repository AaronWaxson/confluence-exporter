# Confluence Page Exporter

使用 Python + `uv` 虚拟环境创建的 CLI 工具，用于递归导出 Confluence 页面及其所有子页面。支持 HTML 和 Markdown 两种导出格式，并自动下载内嵌的附件/图片。

## 环境要求

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) 包管理器

## 安装与配置

进入项目目录，复制配置模板：

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入你的 Confluence 凭证（适用于 Server / Data Center，使用用户名和密码）：

```env
CONFLUENCE_URL=http://172.16.2.225:8090
CONFLUENCE_USERNAME=your_username
CONFLUENCE_PASSWORD=your_password
```

## 使用方法

你可以通过提供完整的页面 URL（推荐）或直接提供 `page-id` 来导出页面：

### 方式 1：提供页面 URL（自动解析）

```bash
uv run confluence-export \
  --page-url "http://172.16.2.225:8090/pages/viewpage.action?pageId=162180277" \
  --format markdown \
  --output ./export \
  --recursive
```

### 方式 2：提供 Page ID

```bash
uv run confluence-export \
  --page-id 162180277 \
  --format markdown \
  --output ./export \
  --recursive
```

### 参数说明

- `--url`: Confluence Base URL。如果使用了 `.env` 或 `--page-url` 则可以省略。
- `--username`: 用户名（也可在 `.env` 中配置）。
- `--password`: 密码（也可在 `.env` 中配置）。
- `--page-id`: 要导出的页面 ID。
- `--page-url`: 完整的页面 URL。
- `--format`: 导出格式，可选 `html` 或 `markdown`（默认：`markdown`）。
- `--output`: 导出文件保存的目录（默认：`./export`）。
- `--recursive` / `--no-recursive`: 是否递归导出子页面（默认：递归）。

## 特性

- **支持直接传 URL**：免去了手动寻找 page ID 的麻烦。
- **自动处理图片**：页面内的图片附件会被下载到同级 `attachments` 目录下，并且无论导出 Markdown 还是 HTML，图片链接都会被自动替换为本地相对路径。
- **美观的终端显示**：使用 `rich` 库展示漂亮的树形结构和下载进度。
