# ConvertCN-中文编码自动识别转换工具

> **对标 ConvertZ / ConvertZZ + 自动中文编码识别 + 简繁体转换 + 预览 GUI**  
> 全新开源替代方案，支持 **GBK / GB2312 / GB18030 / BIG5 / UTF-8** 等常见中文编码，  
> 可选 **简繁体转换**，并提供 **所见即所得的预览界面**，兼容 Windows / macOS / Linux。

---

## ✨ 为什么选择 ConvertCN

- 🆚 **对标 ConvertZ / ConvertZZ**，功能覆盖 + 体验升级
- 🔎 **自动检测编码**：基于 `chardet` 多编码检测算法
- 🈶 **中文感知**：只处理含中文的文件，避免无关文件被改
- 🔁 **批量转换**：保留原目录结构，输出到独立目录
- 🈳 **简繁体转换**（可选）：OpenCC 驱动，编码转换同时完成简繁切换
- 👀 **所见即所得预览**：左右对比原文与转换结果，支持排除文件
- 🧰 **多格式支持**：文本类 + 办公文档（自动提取文本）
- 📊 **统计功能**：转换前后编码分布、文件数量、处理结果一目了然

  <img width="869" height="568" alt="image" src="https://github.com/user-attachments/assets/00f21fda-db5f-417a-a91a-acc89f7dd173" />


---

## 📥 下载与运行

### 方式一：直接运行打包版本（推荐）
1. 前往 [Releases](../../releases)，下载最新的 **Windows `.exe` 版本**。
2. 解压（如有压缩包），直接双击运行，无需安装 Python。

> 如果被杀毒软件拦截，请添加到信任列表。

### 方式二：运行源码
```bash
git clone https://github.com/你的用户名/ConvertCN.git
cd ConvertCN
pip install -r requirements.txt
python encoding_gui_4.py
```

---

## 🚀 快速上手

1. **选择输入目录**（要扫描的文件夹）
2. **选择输出目录**（转换后的文件保存位置）
3. **选择目标编码**（如 UTF-8、GBK 等）
4. （可选）**简繁体转换**（简→繁 或 繁→简）
5. 点击 **扫描文件** → **预览转换**（可排除不需要的文件）
6. 点击 **开始处理** → 查看 **统计结果**

<img width="869" height="635" alt="image" src="https://github.com/user-attachments/assets/e2b8594c-d253-4f84-879d-2f228c72c9bd" />

---

## 🖼️ 界面预览


- 主界面：输入/输出目录选择
- 预览界面：左右对比
- 统计界面：编码分布 & 文件数量

软件主界面：
<img width="869" height="635" alt="image" src="https://github.com/user-attachments/assets/899c8bbf-f561-41b3-a6ba-017b5294b9a7" />


预览对比
<img width="1279" height="538" alt="image" src="https://github.com/user-attachments/assets/190c7f26-a559-4fbe-b76c-1765a19480ac" />

---

## 📦 支持的文件类型

- **文本类**：`.txt` `.md` `.csv` `.html` `.xml` `.py` `.java` `.c` `.cpp` `.json` ...
- **文档类**：`.doc` `.docx` `.rtf` `.odt`（自动提取为 `.txt` 输出）
- 扩展名可自定义
<img width="869" height="69" alt="image" src="https://github.com/user-attachments/assets/8c6d3678-ce75-4bf0-b43c-6d080d8bfcd7" />

---

## ⚙️ 环境要求

- **打包版**：Windows 7/10/11（64 位）
- **源码运行**：Python 3.8+  
  依赖：`chardet`、`opencc-python-reimplemented`（简繁体转换可选）、`docx2txt`（文档解析可选）

---

## 📄 许可

本项目基于 [MIT License](LICENSE) 开源，你可以自由使用、修改、分发。

---

## ⭐ 支持项目

如果这个工具帮到了你，请点一个 **Star** ⭐，让更多人看到它！  
在搜索 **ConvertZ** / **ConvertZZ** 时，也能发现 **ConvertCN**！

---
