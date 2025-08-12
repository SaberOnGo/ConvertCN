#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
编码统一工具 - 带预览和版本信息 (增强版)
支持文件类型过滤、编码预览、版本信息显示、多种输出编码选择
支持简繁体转换、多种文档格式
优化了预览窗口的交互体验
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import chardet
import codecs
import shutil
from pathlib import Path
from collections import Counter
import threading
import zipfile
import xml.etree.ElementTree as ET
import tempfile

# 版本信息
VERSION = "1.4.1"
BUILD_DATE = "2025-07"
AUTHOR = "SaberOnGo"

# 输出编码选项
OUTPUT_ENCODINGS = {
    "简体GB18030": {
        "encoding": "gb18030",
        "charset": "simplified",
        "name": "简体GB18030"
    },
    "简体GB2312": {
        "encoding": "gb2312", 
        "charset": "simplified",
        "name": "简体GB2312"
    },
    "简体UTF-8": {
        "encoding": "utf-8",
        "charset": "simplified", 
        "name": "简体UTF-8"
    },
    "繁体BIG5": {
        "encoding": "big5",
        "charset": "traditional",
        "name": "繁体BIG5"
    },
    "繁体UTF-8": {
        "encoding": "utf-8",
        "charset": "traditional",
        "name": "繁体UTF-8"
    },
    "简体GBK": {
        "encoding": "gbk",
        "charset": "simplified",
        "name": "简体GBK"
    },
    "UTF-8(无BOM)": {
        "encoding": "utf-8",
        "charset": "auto",
        "name": "UTF-8(无BOM)"
    },
    "UTF-8(带BOM)": {
        "encoding": "utf-8-sig",
        "charset": "auto", 
        "name": "UTF-8(带BOM)"
    }
}

class EncodingUnifierGUI:
    def __init__(self, root):
        self.root = root
        self.root.title(f"文件编码统一工具 v{VERSION}")
        self.root.geometry("1300x900")
        
        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.file_extensions_var = tk.StringVar(value=".c,.h,.cpp,.hpp,.cc,.cxx,.txt,.py,.java,.js,.html,.css,.xml,.json,.md,.sql,.ini,.cfg,.conf,.log,.csv,.tsv,.doc,.docx,.rtf,.odt")
        self.output_encoding_var = tk.StringVar(value="简体GB18030")
        
        self.encoding_results = {}
        self.copy_files = {}  # 存储需要直接复制的文件
        self.excluded_files = set()  # 存储用户排除的文件
        self.processed_files = []
        
        # 预览窗口相关
        self.preview_window = None
        self.preview_excluded_files = set()  # 预览窗口中排除的文件
        
        # 导入简繁转换模块（如果可用）
        self.has_opencc = False
        try:
            import opencc
            self.opencc = opencc
            self.has_opencc = True
        except ImportError:
            pass
        
        self.setup_ui()
        
    def setup_ui(self):
        """设置用户界面"""
        # 创建菜单
        self.create_menu()
        
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 路径和过滤设置框架
        settings_frame = ttk.LabelFrame(main_frame, text="设置", padding="5")
        settings_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 输入目录
        ttk.Label(settings_frame, text="输入目录 (A):").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        input_frame = ttk.Frame(settings_frame)
        input_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        ttk.Entry(input_frame, textvariable=self.input_path, width=80).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(input_frame, text="浏览", command=self.browse_input_directory).grid(row=0, column=1)
        
        # 输出目录
        ttk.Label(settings_frame, text="输出目录 (B):").grid(row=2, column=0, sticky=tk.W, pady=(0, 5))
        output_frame = ttk.Frame(settings_frame)
        output_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        ttk.Entry(output_frame, textvariable=self.output_path, width=80).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(output_frame, text="浏览", command=self.browse_output_directory).grid(row=0, column=1)
        ttk.Button(output_frame, text="自动设置", command=self.auto_set_output).grid(row=0, column=2, padx=(5, 0))
        
        # 文件类型过滤
        ttk.Label(settings_frame, text="要处理编码的文件类型 (用逗号分隔):").grid(row=4, column=0, sticky=tk.W, pady=(0, 5))
        filter_frame = ttk.Frame(settings_frame)
        filter_frame.grid(row=5, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        ttk.Entry(filter_frame, textvariable=self.file_extensions_var, width=80).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(filter_frame, text="重置默认", command=self.reset_extensions).grid(row=0, column=1)
        
        # 输出编码设置
        ttk.Label(settings_frame, text="输出编码:").grid(row=6, column=0, sticky=tk.W, pady=(5, 5))
        encoding_frame = ttk.Frame(settings_frame)
        encoding_frame.grid(row=7, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        encoding_combo = ttk.Combobox(encoding_frame, textvariable=self.output_encoding_var, 
                                     values=list(OUTPUT_ENCODINGS.keys()), 
                                     state="readonly", width=20)
        encoding_combo.grid(row=0, column=0, padx=(0, 10))
        
        # 简繁转换说明
        if self.has_opencc:
            encoding_info = ttk.Label(encoding_frame, text="支持简繁体转换", foreground="green", font=("", 9))
        else:
            encoding_info = ttk.Label(encoding_frame, text="简繁体转换不可用 (需要安装opencc-python-reimplemented)", foreground="orange", font=("", 9))
        encoding_info.grid(row=0, column=1, sticky=tk.W)
        
        # 说明文字
        info_text = "说明: 上述文件类型会进行编码检测和转换，其他所有文件将直接复制到输出目录\n支持的文档格式: .doc, .docx, .rtf, .odt 等"
        ttk.Label(settings_frame, text=info_text, foreground="blue", font=("", 9)).grid(row=8, column=0, sticky=tk.W, pady=(5, 0))
        
        # 配置列权重
        settings_frame.columnconfigure(0, weight=1)
        input_frame.columnconfigure(0, weight=1)
        output_frame.columnconfigure(0, weight=1)
        filter_frame.columnconfigure(0, weight=1)
        encoding_frame.columnconfigure(0, weight=1)
        
        # 控制按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Button(button_frame, text="扫描文件", command=self.scan_files).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(button_frame, text="预览转换", command=self.show_preview_window).grid(row=0, column=1, padx=(0, 5))
        ttk.Button(button_frame, text="开始处理", command=self.start_processing).grid(row=0, column=2, padx=(0, 5))
        ttk.Button(button_frame, text="清除结果", command=self.clear_results).grid(row=0, column=3, padx=(0, 5))
        ttk.Button(button_frame, text="打开输出目录", command=self.open_output_directory).grid(row=0, column=4)
        
        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 状态标签
        self.status_var = tk.StringVar(value="请选择输入和输出目录，配置文件类型过滤")
        ttk.Label(main_frame, textvariable=self.status_var).grid(row=3, column=0, columnspan=2, sticky=tk.W)
        
        # 结果显示区域
        result_frame = ttk.LabelFrame(main_frame, text="扫描结果", padding="5")
        result_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        
        # 创建Notebook来分类显示
        self.notebook = ttk.Notebook(result_frame)
        self.notebook.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 需要处理编码的文件标签页
        encoding_frame = ttk.Frame(self.notebook)
        self.notebook.add(encoding_frame, text="编码处理文件")
        
        # 直接复制的文件标签页
        copy_frame = ttk.Frame(self.notebook)
        self.notebook.add(copy_frame, text="直接复制文件")
        
        # 统计信息标签页
        summary_frame = ttk.Frame(self.notebook)
        self.notebook.add(summary_frame, text="统计信息")
        
        # 设置编码处理文件列表
        self.setup_encoding_tree(encoding_frame)
        
        # 设置直接复制文件列表
        self.setup_copy_tree(copy_frame)
        
        # 设置统计信息
        self.setup_summary_text(summary_frame)
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(4, weight=1)
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=1)
        
    def create_menu(self):
        """创建菜单栏"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="使用说明", command=self.show_help)
        help_menu.add_separator()
        help_menu.add_command(label="关于", command=self.show_about)
        
    def show_about(self):
        """显示关于对话框"""
        about_text = f"""文件编码统一工具

版本: {VERSION}
构建日期: {BUILD_DATE}
开发者: {AUTHOR}

功能特性:
• 智能检测文件编码
• 批量转换为统一编码
• 支持多种输出编码格式
• 支持简繁体转换
• 支持多种文档格式 (.doc, .docx, .rtf, .odt)
• 文件类型过滤
• 编码预览功能
• 完整目录结构保持
• 优化的预览交互体验

适用于处理混合编码的源代码项目和文档，
支持C/C++、Python、Java、文档等多种文件类型。

© 2024 保留所有权利"""
        
        messagebox.showinfo("关于", about_text)
        
    def show_help(self):
        """显示使用说明"""
        help_text = """使用说明

1. 设置目录
   • 选择输入目录(A): 包含源文件的目录
   • 选择输出目录(B): 处理后文件的保存位置

2. 配置文件类型和输出编码
   • 设置要处理编码的文件扩展名
   • 选择输出编码格式（支持简繁体转换）
   • 其他文件将直接复制，保持原样

3. 扫描和预览
   • 点击"扫描文件"分析所有文件
   • 点击"预览转换"查看转换效果
   • 在预览窗口中可以直接排除不需要转换的文件

4. 开始处理
   • 点击"开始处理"执行转换和复制
   • 查看详细的统计报告

支持的文档格式:
• 文本文件: .txt, .md, .log, .csv, .tsv, .ini, .cfg, .conf
• 源代码: .c, .h, .cpp, .hpp, .py, .java, .js, .html, .css, .xml, .json, .sql
• 文档格式: .doc, .docx, .rtf, .odt

简繁体转换:
• 需要安装 opencc-python-reimplemented 模块
• 支持简体↔繁体自动转换
• 根据输出编码自动判断转换方向

注意事项:
• 建议先预览确认转换效果
• 输出目录会保持原目录结构
• 所有操作都是安全的，不会修改原文件
• 预览窗口支持直接操作文件排除/包含
• 应用更改时会进行二次确认"""
        
        help_window = tk.Toplevel(self.root)
        help_window.title("使用说明")
        help_window.geometry("600x500")
        help_window.resizable(False, False)
        
        text_widget = scrolledtext.ScrolledText(help_window, wrap=tk.WORD, padx=10, pady=10)
        text_widget.pack(fill=tk.BOTH, expand=True)
        text_widget.insert(tk.END, help_text)
        text_widget.config(state=tk.DISABLED)
        
    def setup_encoding_tree(self, parent):
        """设置编码处理文件树"""
        # 文件列表
        list_frame = ttk.Frame(parent)
        list_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        
        # 标题和操作按钮
        title_frame = ttk.Frame(list_frame)
        title_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        ttk.Label(title_frame, text="需要编码处理的文件:").grid(row=0, column=0, sticky=tk.W)
        ttk.Button(title_frame, text="全选", command=self.select_all_encoding).grid(row=0, column=1, padx=(10, 5))
        ttk.Button(title_frame, text="全不选", command=self.deselect_all_encoding).grid(row=0, column=2, padx=(0, 5))
        ttk.Button(title_frame, text="删除选中", command=self.remove_selected_encoding).grid(row=0, column=3)
        
        title_frame.columnconfigure(0, weight=1)
        
        # 创建Treeview显示文件信息
        columns = ('select', 'file', 'encoding', 'confidence', 'status', 'action')
        self.encoding_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=12)
        
        # 设置列标题
        self.encoding_tree.heading('select', text='选择')
        self.encoding_tree.heading('file', text='文件路径')
        self.encoding_tree.heading('encoding', text='检测编码')
        self.encoding_tree.heading('confidence', text='置信度')
        self.encoding_tree.heading('status', text='状态')
        self.encoding_tree.heading('action', text='操作')
        
        # 设置列宽
        self.encoding_tree.column('select', width=50)
        self.encoding_tree.column('file', width=320)
        self.encoding_tree.column('encoding', width=80)
        self.encoding_tree.column('confidence', width=60)
        self.encoding_tree.column('status', width=80)
        self.encoding_tree.column('action', width=120)
        
        self.encoding_tree.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 滚动条
        encoding_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.encoding_tree.yview)
        encoding_scroll.grid(row=1, column=1, sticky=(tk.N, tk.S))
        self.encoding_tree.configure(yscrollcommand=encoding_scroll.set)
        
        # 绑定事件
        self.encoding_tree.bind('<Double-1>', self.on_encoding_file_double_click)
        self.encoding_tree.bind('<Button-1>', self.on_encoding_tree_click)
        
        # 详细信息显示
        detail_frame = ttk.Frame(parent)
        detail_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        ttk.Label(detail_frame, text="详细信息:").grid(row=0, column=0, sticky=tk.W)
        
        self.encoding_detail_text = scrolledtext.ScrolledText(detail_frame, width=45, height=15)
        self.encoding_detail_text.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置权重
        parent.columnconfigure(0, weight=2)
        parent.columnconfigure(1, weight=1)
        parent.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(1, weight=1)
        detail_frame.columnconfigure(0, weight=1)
        detail_frame.rowconfigure(1, weight=1)
        
    def setup_copy_tree(self, parent):
        """设置直接复制文件树"""
        ttk.Label(parent, text="直接复制的文件:").grid(row=0, column=0, sticky=tk.W)
        
        # 创建Treeview显示复制文件信息
        columns = ('file', 'size', 'status')
        self.copy_tree = ttk.Treeview(parent, columns=columns, show='headings', height=15)
        
        # 设置列标题
        self.copy_tree.heading('file', text='文件路径')
        self.copy_tree.heading('size', text='文件大小')
        self.copy_tree.heading('status', text='状态')
        
        # 设置列宽
        self.copy_tree.column('file', width=500)
        self.copy_tree.column('size', width=100)
        self.copy_tree.column('status', width=120)
        
        self.copy_tree.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 滚动条
        copy_scroll = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.copy_tree.yview)
        copy_scroll.grid(row=1, column=1, sticky=(tk.N, tk.S))
        self.copy_tree.configure(yscrollcommand=copy_scroll.set)
        
        # 配置权重
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)
        
    def setup_summary_text(self, parent):
        """设置统计信息文本"""
        ttk.Label(parent, text="统计信息:").grid(row=0, column=0, sticky=tk.W)
        
        self.summary_text = scrolledtext.ScrolledText(parent, width=80, height=20)
        self.summary_text.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置权重
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)
        
    def on_encoding_tree_click(self, event):
        """处理编码树点击事件"""
        item = self.encoding_tree.identify('item', event.x, event.y)
        column = self.encoding_tree.identify('column', event.x, event.y)
        
        # 如果点击的是选择列
        if item and column == '#1':  # 选择列
            file_path = self.encoding_tree.item(item)['tags'][0]
            
            # 切换选择状态
            if file_path in self.excluded_files:
                self.excluded_files.discard(file_path)
                select_text = "☑"
            else:
                self.excluded_files.add(file_path)
                select_text = "☐"
            
            # 更新显示
            values = list(self.encoding_tree.item(item)['values'])
            values[0] = select_text
            self.encoding_tree.item(item, values=values)
        
    def select_all_encoding(self):
        """全选编码文件"""
        for item in self.encoding_tree.get_children():
            file_path = self.encoding_tree.item(item)['tags'][0]
            self.excluded_files.discard(file_path)
            
            values = list(self.encoding_tree.item(item)['values'])
            values[0] = "☑"
            self.encoding_tree.item(item, values=values)
            
    def deselect_all_encoding(self):
        """全不选编码文件"""
        for item in self.encoding_tree.get_children():
            file_path = self.encoding_tree.item(item)['tags'][0]
            self.excluded_files.add(file_path)
            
            values = list(self.encoding_tree.item(item)['values'])
            values[0] = "☐"
            self.encoding_tree.item(item, values=values)
            
    def remove_selected_encoding(self):
        """删除未选中的编码文件"""
        if not self.excluded_files:
            messagebox.showinfo("提示", "所有文件都已选中，无需删除")
            return
            
        result = messagebox.askyesno(
            "确认删除", 
            f"确定要从处理列表中删除 {len(self.excluded_files)} 个未选中的文件吗？\n"
            "这些文件将被直接复制，不会进行编码转换。"
        )
        
        if result:
            # 移动到复制列表
            for file_path in self.excluded_files.copy():
                if file_path in self.encoding_results:
                    # 移动到复制文件列表
                    file_info = self.get_file_info(file_path)
                    self.copy_files[file_path] = file_info
                    
                    # 从编码结果中删除
                    del self.encoding_results[file_path]
            
            self.excluded_files.clear()
            
            # 重新构建界面
            self.rebuild_file_lists()
            
            messagebox.showinfo("完成", "已将未选中的文件移动到直接复制列表")
    
    def rebuild_file_lists(self):
        """重新构建文件列表"""
        # 清空现有列表
        self.encoding_tree.delete(*self.encoding_tree.get_children())
        self.copy_tree.delete(*self.copy_tree.get_children())
        
        # 重建编码文件列表
        for file_path, encoding_info in self.encoding_results.items():
            self.update_encoding_file_list(file_path, encoding_info)
            
        # 重建复制文件列表
        for file_path, file_info in self.copy_files.items():
            self.update_copy_file_list(file_path, file_info)
            
    def show_preview_window(self):
        """显示预览窗口"""
        if not self.encoding_results:
            messagebox.showerror("错误", "请先扫描文件")
            return
            
        # 获取目标编码信息
        target_encoding_info = OUTPUT_ENCODINGS[self.output_encoding_var.get()]
        
        # 筛选需要转换的文件
        convert_files = []
        for file_path, info in self.encoding_results.items():
            if (file_path not in self.excluded_files and 
                info.get('has_chinese', False)):
                convert_files.append((file_path, info))
        
        if not convert_files:
            messagebox.showinfo("提示", "没有需要编码转换的文件")
            return
            
        # 如果预览窗口已存在，先关闭
        if self.preview_window:
            self.preview_window.destroy()
            
        # 创建预览窗口
        self.preview_window = tk.Toplevel(self.root)
        self.preview_window.title(f"编码转换预览 - {len(convert_files)} 个文件 → {target_encoding_info['name']}")
        self.preview_window.geometry("1300x800")
        
        # 初始化预览排除列表
        self.preview_excluded_files = set()
        
        # 主容器
        main_container = ttk.Frame(self.preview_window)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 左侧文件列表框架 - 缩小宽度
        left_frame = ttk.Frame(main_container)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 10))
        
        # 文件列表标题和操作按钮
        file_header_frame = ttk.Frame(left_frame)
        file_header_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(file_header_frame, text="待转换文件:").pack(side=tk.LEFT)
        ttk.Button(file_header_frame, text="全选", command=lambda: self.preview_select_all(True)).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(file_header_frame, text="全不选", command=lambda: self.preview_select_all(False)).pack(side=tk.RIGHT, padx=(5, 0))
        
        # 文件列表框架 - 添加滚动条
        list_container = ttk.Frame(left_frame)
        list_container.pack(fill=tk.BOTH, expand=True)
        
        # 创建带滚动条的文件列表
        self.preview_file_listbox = tk.Listbox(list_container, width=50)  # 固定宽度
        
        # 垂直滚动条
        v_scrollbar = ttk.Scrollbar(list_container, orient=tk.VERTICAL, command=self.preview_file_listbox.yview)
        self.preview_file_listbox.configure(yscrollcommand=v_scrollbar.set)
        
        # 水平滚动条
        h_scrollbar = ttk.Scrollbar(list_container, orient=tk.HORIZONTAL, command=self.preview_file_listbox.xview)
        self.preview_file_listbox.configure(xscrollcommand=h_scrollbar.set)
        
        # 布局
        self.preview_file_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        v_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        h_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        list_container.columnconfigure(0, weight=1)
        list_container.rowconfigure(0, weight=1)
        
        # 填充文件列表
        self.preview_convert_files = convert_files
        for i, (file_path, info) in enumerate(convert_files):
            rel_path = os.path.relpath(file_path, self.input_path.get())
            source_encoding = info.get('best_encoding', 'unknown')
            display_text = f"☑ {rel_path} ({source_encoding})"
            self.preview_file_listbox.insert(tk.END, display_text)
        
        # 右侧预览区域
        right_frame = ttk.Frame(main_container)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # 预览标题
        preview_header_frame = ttk.Frame(right_frame)
        preview_header_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.preview_title = ttk.Label(preview_header_frame, text="选择文件查看预览", font=("", 12, "bold"))
        self.preview_title.pack(side=tk.LEFT)
        
        # 操作按钮
        ttk.Button(preview_header_frame, text="排除此文件", command=self.toggle_current_file_exclusion).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(preview_header_frame, text="应用更改", command=self.apply_preview_changes).pack(side=tk.RIGHT, padx=(5, 0))
        
        # 创建预览区域的容器 - 使用PanedWindow来分割转换前后
        preview_paned = ttk.PanedWindow(right_frame, orient=tk.HORIZONTAL)
        preview_paned.pack(fill=tk.BOTH, expand=True)
        
        # 转换前框架
        before_frame = ttk.LabelFrame(preview_paned, text="转换前")
        preview_paned.add(before_frame, weight=1)
        
        # 转换前文本区域 - 添加滚动条
        self.before_text = tk.Text(before_frame, wrap=tk.NONE, width=40, height=25)
        before_v_scroll = ttk.Scrollbar(before_frame, orient=tk.VERTICAL, command=self.before_text.yview)
        before_h_scroll = ttk.Scrollbar(before_frame, orient=tk.HORIZONTAL, command=self.before_text.xview)
        self.before_text.configure(yscrollcommand=before_v_scroll.set, xscrollcommand=before_h_scroll.set)
        
        self.before_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        before_v_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
        before_h_scroll.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        before_frame.columnconfigure(0, weight=1)
        before_frame.rowconfigure(0, weight=1)
        
        # 转换后框架
        after_frame = ttk.LabelFrame(preview_paned, text=f"转换后 ({target_encoding_info['name']})")
        preview_paned.add(after_frame, weight=1)
        
        # 转换后文本区域 - 添加滚动条
        self.after_text = tk.Text(after_frame, wrap=tk.NONE, width=40, height=25)
        after_v_scroll = ttk.Scrollbar(after_frame, orient=tk.VERTICAL, command=self.after_text.yview)
        after_h_scroll = ttk.Scrollbar(after_frame, orient=tk.HORIZONTAL, command=self.after_text.xview)
        self.after_text.configure(yscrollcommand=after_v_scroll.set, xscrollcommand=after_h_scroll.set)
        
        self.after_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        after_v_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
        after_h_scroll.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        after_frame.columnconfigure(0, weight=1)
        after_frame.rowconfigure(0, weight=1)
        
        # 底部按钮框架
        bottom_frame = ttk.Frame(self.preview_window)
        bottom_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # 状态标签
        self.preview_status_var = tk.StringVar(value=f"共 {len(convert_files)} 个文件待转换")
        ttk.Label(bottom_frame, textvariable=self.preview_status_var).pack(side=tk.LEFT)
        
        ttk.Button(bottom_frame, text="关闭预览", command=self.close_preview_window).pack(side=tk.RIGHT)
        
        # 绑定事件
        self.preview_file_listbox.bind('<<ListboxSelect>>', self.on_preview_file_select)
        self.preview_file_listbox.bind('<Double-Button-1>', self.on_preview_file_double_click)
        
        # 选择第一个文件
        if convert_files:
            self.preview_file_listbox.selection_set(0)
            self.on_preview_file_select(None)
    
    def preview_select_all(self, select):
        """预览窗口全选/全不选"""
        if select:
            self.preview_excluded_files.clear()
            prefix = "☑"
        else:
            self.preview_excluded_files = set(fp for fp, _ in self.preview_convert_files)
            prefix = "☐"
        
        # 更新列表显示
        for i, (file_path, info) in enumerate(self.preview_convert_files):
            rel_path = os.path.relpath(file_path, self.input_path.get())
            source_encoding = info.get('best_encoding', 'unknown')
            display_text = f"{prefix} {rel_path} ({source_encoding})"
            self.preview_file_listbox.delete(i)
            self.preview_file_listbox.insert(i, display_text)
        
        # 更新状态
        self.update_preview_status()
    
    def on_preview_file_select(self, event):
        """预览文件选择事件"""
        selection = self.preview_file_listbox.curselection()
        if not selection:
            return
            
        index = selection[0]
        file_path, info = self.preview_convert_files[index]
        source_encoding = info.get('best_encoding', 'utf-8')
        
        # 更新标题
        rel_path = os.path.relpath(file_path, self.input_path.get())
        self.preview_title.config(text=f"预览: {rel_path}")
        
        try:
            # 读取原文件内容
            content = self.read_file_content(file_path, source_encoding)
            
            # 显示转换前内容
            self.before_text.delete(1.0, tk.END)
            self.before_text.insert(tk.END, content)
            
            # 显示转换后内容
            converted_content = self.convert_text_encoding(content, self.output_encoding_var.get())
            self.after_text.delete(1.0, tk.END)
            self.after_text.insert(tk.END, converted_content)
            
        except Exception as e:
            error_msg = f"无法读取文件: {str(e)}"
            self.before_text.delete(1.0, tk.END)
            self.before_text.insert(tk.END, error_msg)
            self.after_text.delete(1.0, tk.END)
            self.after_text.insert(tk.END, "转换预览不可用")
    
    def on_preview_file_double_click(self, event):
        """预览文件双击事件 - 切换选择状态"""
        self.toggle_current_file_exclusion()
    
    def toggle_current_file_exclusion(self):
        """切换当前文件的排除状态"""
        selection = self.preview_file_listbox.curselection()
        if not selection:
            return
            
        index = selection[0]
        file_path, info = self.preview_convert_files[index]
        
        # 切换排除状态
        if file_path in self.preview_excluded_files:
            self.preview_excluded_files.discard(file_path)
            prefix = "☑"
        else:
            self.preview_excluded_files.add(file_path)
            prefix = "☐"
        
        # 更新列表显示
        rel_path = os.path.relpath(file_path, self.input_path.get())
        source_encoding = info.get('best_encoding', 'unknown')
        display_text = f"{prefix} {rel_path} ({source_encoding})"
        self.preview_file_listbox.delete(index)
        self.preview_file_listbox.insert(index, display_text)
        self.preview_file_listbox.selection_set(index)
        
        # 更新状态
        self.update_preview_status()
    
    def update_preview_status(self):
        """更新预览状态"""
        total_files = len(self.preview_convert_files)
        excluded_count = len(self.preview_excluded_files)
        selected_count = total_files - excluded_count
        
        status_text = f"共 {total_files} 个文件，已选中 {selected_count} 个，排除 {excluded_count} 个"
        self.preview_status_var.set(status_text)
    
    def apply_preview_changes(self):
        """应用预览中的更改到主窗口"""
        if not self.preview_excluded_files:
            messagebox.showinfo("提示", "没有需要应用的更改")
            return
        
        # 二次确认
        excluded_count = len(self.preview_excluded_files)
        result = messagebox.askyesno(
            "确认应用更改",
            f"确定要将 {excluded_count} 个文件标记为排除吗？\n\n"
            "这些文件将不会进行编码转换，而是直接复制到输出目录。\n\n"
            "此操作会影响主窗口的文件选择状态。"
        )
        
        if not result:
            return
            
        # 将预览中排除的文件添加到主窗口的排除列表
        for file_path in self.preview_excluded_files:
            self.excluded_files.add(file_path)
        
        # 更新主窗口的编码文件列表显示
        for item in self.encoding_tree.get_children():
            file_path = self.encoding_tree.item(item)['tags'][0]
            if file_path in self.excluded_files:
                values = list(self.encoding_tree.item(item)['values'])
                values[0] = "☐"  # 更新选择状态
                self.encoding_tree.item(item, values=values)
        
        messagebox.showinfo("应用成功", f"已将 {excluded_count} 个文件标记为排除，请在主窗口查看")
        
        # 清空预览排除列表
        self.preview_excluded_files.clear()
        
        # 重新选择当前文件以刷新显示
        selection = self.preview_file_listbox.curselection()
        if selection:
            self.on_preview_file_select(None)
    
    def close_preview_window(self):
        """关闭预览窗口"""
        if self.preview_window:
            self.preview_window.destroy()
            self.preview_window = None
            self.preview_excluded_files.clear()
    
    def get_file_extensions(self):
        """获取文件扩展名列表"""
        extensions_str = self.file_extensions_var.get().strip()
        if not extensions_str:
            return []
        
        extensions = []
        for ext in extensions_str.split(','):
            ext = ext.strip()
            if ext and not ext.startswith('.'):
                ext = '.' + ext
            if ext:
                extensions.append(ext.lower())
        
        return extensions
        
    def reset_extensions(self):
        """重置默认文件扩展名"""
        self.file_extensions_var.set(".c,.h,.cpp,.hpp,.cc,.cxx,.txt,.py,.java,.js,.html,.css,.xml,.json,.md,.sql,.ini,.cfg,.conf,.log,.csv,.tsv,.doc,.docx,.rtf,.odt")
        
    def browse_input_directory(self):
        """浏览选择输入目录"""
        directory = filedialog.askdirectory(title="选择输入目录 (A)")
        if directory:
            self.input_path.set(directory)
            # 如果输出目录为空，自动设置
            if not self.output_path.get():
                self.auto_set_output()
                
    def browse_output_directory(self):
        """浏览选择输出目录"""
        directory = filedialog.askdirectory(title="选择输出目录 (B)")
        if directory:
            self.output_path.set(directory)
            
    def auto_set_output(self):
        """自动设置输出目录"""
        if self.input_path.get():
            input_dir = self.input_path.get()
            parent_dir = os.path.dirname(input_dir)
            dir_name = os.path.basename(input_dir)
            output_dir = os.path.join(parent_dir, f"{dir_name}_encoded")
            self.output_path.set(output_dir)
    
    def open_output_directory(self):
        """打开输出目录"""
        if self.output_path.get() and os.path.exists(self.output_path.get()):
            try:
                if os.name == 'nt':  # Windows
                    os.startfile(self.output_path.get())
                else:  # Linux/Mac
                    import subprocess
                    subprocess.run(['xdg-open', self.output_path.get()])
            except Exception as e:
                messagebox.showerror("错误", f"无法打开目录: {str(e)}")
        else:
            messagebox.showwarning("警告", "输出目录不存在或未设置")
    
    def read_file_content(self, file_path, encoding):
        """读取文件内容，支持多种文件格式"""
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext == '.docx':
            return self.read_docx_content(file_path)
        elif file_ext == '.doc':
            return self.read_doc_content(file_path)
        elif file_ext == '.rtf':
            return self.read_rtf_content(file_path)
        elif file_ext == '.odt':
            return self.read_odt_content(file_path)
        else:
            # 普通文本文件
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
    
    def read_docx_content(self, file_path):
        """读取DOCX文件内容"""
        try:
            with zipfile.ZipFile(file_path, 'r') as docx_zip:
                document_xml = docx_zip.read('word/document.xml')
                root = ET.fromstring(document_xml)
                
                # 提取文本内容
                text_elements = root.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t')
                content = '\n'.join([elem.text or '' for elem in text_elements])
                
                return content if content else "无法提取文本内容"
        except Exception as e:
            return f"读取DOCX文件失败: {str(e)}"
    
    def read_doc_content(self, file_path):
        """读取DOC文件内容"""
        try:
            # 尝试使用python-docx2txt (如果可用)
            try:
                import docx2txt
                content = docx2txt.process(file_path)
                return content if content else "无法提取文本内容"
            except ImportError:
                pass
            
            # 简单的二进制读取和文本提取
            with open(file_path, 'rb') as f:
                raw_data = f.read()
                # 尝试查找文本内容
                content = raw_data.decode('utf-8', errors='ignore')
                # 简单清理
                content = ''.join(c for c in content if c.isprintable() or c.isspace())
                return content[:1000] + "..." if len(content) > 1000 else content
        except Exception as e:
            return f"读取DOC文件失败: {str(e)}"
    
    def read_rtf_content(self, file_path):
        """读取RTF文件内容"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                # 简单的RTF内容提取
                import re
                # 移除RTF控制字符
                content = re.sub(r'\\[a-z]+\d*\s?', '', content)
                content = re.sub(r'[{}]', '', content)
                
                return content if content else "无法提取文本内容"
        except Exception as e:
            return f"读取RTF文件失败: {str(e)}"
    
    def read_odt_content(self, file_path):
        """读取ODT文件内容"""
        try:
            with zipfile.ZipFile(file_path, 'r') as odt_zip:
                content_xml = odt_zip.read('content.xml')
                root = ET.fromstring(content_xml)
                
                # 提取文本内容
                text_elements = root.findall('.//{urn:oasis:names:tc:opendocument:xmlns:text:1.0}p')
                content = '\n'.join([elem.text or '' for elem in text_elements])
                
                return content if content else "无法提取文本内容"
        except Exception as e:
            return f"读取ODT文件失败: {str(e)}"
    
    def convert_text_encoding(self, text, target_encoding_option):
        """转换文本编码，支持简繁体转换"""
        target_info = OUTPUT_ENCODINGS[target_encoding_option]
        
        # 简繁体转换
        if self.has_opencc and target_info['charset'] != 'auto':
            try:
                if target_info['charset'] == 'traditional':
                    # 转换为繁体
                    converter = self.opencc.OpenCC('s2t')  # 简体到繁体
                    text = converter.convert(text)
                elif target_info['charset'] == 'simplified':
                    # 转换为简体
                    converter = self.opencc.OpenCC('t2s')  # 繁体到简体
                    text = converter.convert(text)
            except Exception as e:
                # 转换失败，使用原文
                pass
        
        return text
            
    def scan_files(self):
        """扫描文件"""
        if not self.input_path.get():
            messagebox.showerror("错误", "请先选择输入目录")
            return
            
        if not os.path.exists(self.input_path.get()):
            messagebox.showerror("错误", "输入目录不存在")
            return
            
        if not self.output_path.get():
            messagebox.showerror("错误", "请先选择输出目录")
            return
            
        extensions = self.get_file_extensions()
        if not extensions:
            messagebox.showerror("错误", "请设置要处理的文件类型")
            return
        
        # 清除排除列表
        self.excluded_files.clear()
        
        # 在后台线程中执行扫描
        self.status_var.set("正在扫描文件...")
        self.progress_var.set(0)
        
        thread = threading.Thread(target=self._scan_files_thread, args=(extensions,))
        thread.daemon = True
        thread.start()
        
    def _scan_files_thread(self, target_extensions):
        """后台扫描文件线程"""
        try:
            # 清除之前的结果
            self.encoding_results.clear()
            self.copy_files.clear()
            
            # 找到所有文件
            all_files = []
            encoding_files = []
            copy_files = []
            
            for root, dirs, filenames in os.walk(self.input_path.get()):
                for filename in filenames:
                    file_path = os.path.join(root, filename)
                    all_files.append(file_path)
                    
                    # 判断是否需要编码处理
                    file_ext = os.path.splitext(filename)[1].lower()
                    if file_ext in target_extensions:
                        encoding_files.append(file_path)
                    else:
                        copy_files.append(file_path)
            
            if not all_files:
                self.root.after(0, lambda: self.status_var.set("未找到任何文件"))
                return
                
            # 处理需要编码检测的文件
            total_encoding_files = len(encoding_files)
            for i, file_path in enumerate(encoding_files):
                # 更新进度
                progress = (i / len(all_files)) * 50  # 前50%用于编码检测
                self.root.after(0, lambda p=progress: self.progress_var.set(p))
                
                # 检测编码
                encoding_info = self.detect_file_encoding(file_path)
                self.encoding_results[file_path] = encoding_info
                
                # 更新界面
                self.root.after(0, lambda fp=file_path, ei=encoding_info: self.update_encoding_file_list(fp, ei))
            
            # 处理需要直接复制的文件
            for i, file_path in enumerate(copy_files):
                # 更新进度
                progress = 50 + (i / len(copy_files)) * 50  # 后50%用于复制文件信息
                self.root.after(0, lambda p=progress: self.progress_var.set(p))
                
                # 获取文件信息
                file_info = self.get_file_info(file_path)
                self.copy_files[file_path] = file_info
                
                # 更新界面
                self.root.after(0, lambda fp=file_path, fi=file_info: self.update_copy_file_list(fp, fi))
            
            # 完成扫描
            self.root.after(0, lambda: self.scan_complete(target_extensions))
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("扫描错误", f"扫描过程中出现错误: {str(e)}"))
            
    def get_file_info(self, file_path):
        """获取文件信息"""
        try:
            stat = os.stat(file_path)
            size = stat.st_size
            
            # 格式化文件大小
            if size < 1024:
                size_str = f"{size} B"
            elif size < 1024 * 1024:
                size_str = f"{size/1024:.1f} KB"
            else:
                size_str = f"{size/(1024*1024):.1f} MB"
                
            return {
                'size': size,
                'size_str': size_str,
                'exists': True
            }
        except Exception:
            return {
                'size': 0,
                'size_str': 'Unknown',
                'exists': False
            }
            
    def detect_file_encoding(self, file_path):
        """检测文件编码"""
        result = {
            'chardet_encoding': 'unknown',
            'chardet_confidence': 0,
            'best_encoding': 'unknown',
            'encodings_test': {},
            'has_chinese': False,
            'file_type': 'text'
        }
        
        try:
            file_ext = os.path.splitext(file_path)[1].lower()
            
            # 检测文档类型文件
            if file_ext in ['.doc', '.docx', '.rtf', '.odt']:
                result['file_type'] = 'document'
                try:
                    content = self.read_file_content(file_path, 'utf-8')
                    result['has_chinese'] = any('\u4e00' <= char <= '\u9fff' for char in content)
                    result['best_encoding'] = 'utf-8'  # 文档类型默认使用UTF-8
                    result['encodings_test']['utf-8'] = {
                        'success': True,
                        'has_chinese': result['has_chinese'],
                        'has_mojibake': False,
                        'score': 10
                    }
                except Exception as e:
                    result['error'] = str(e)
                return result
            
            # 普通文本文件编码检测
            # 使用chardet检测
            with open(file_path, 'rb') as f:
                raw_data = f.read()
                if len(raw_data) > 0:
                    chardet_result = chardet.detect(raw_data)
                    result['chardet_encoding'] = chardet_result['encoding'] or 'unknown'
                    result['chardet_confidence'] = chardet_result['confidence'] or 0
            
            # 尝试用不同编码读取
            test_encodings = ['utf-8', 'gb18030', 'gbk', 'gb2312', 'big5', 'utf-8-sig', 'ascii']
            best_score = -1
            best_encoding = 'unknown'
            
            for encoding in test_encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read()
                        
                    # 评分系统
                    score = 0
                    has_chinese = any('\u4e00' <= char <= '\u9fff' for char in content)
                    has_mojibake = any(char in content for char in ['锟', '烫', '屯', '�'])
                    
                    if not has_mojibake:
                        score += 10
                    if has_chinese:
                        score += 5
                        result['has_chinese'] = True
                    
                    result['encodings_test'][encoding] = {
                        'success': True,
                        'has_chinese': has_chinese,
                        'has_mojibake': has_mojibake,
                        'score': score
                    }
                    
                    if score > best_score:
                        best_score = score
                        best_encoding = encoding
                        
                except Exception:
                    result['encodings_test'][encoding] = {
                        'success': False,
                        'error': True
                    }
            
            result['best_encoding'] = best_encoding
            
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def update_encoding_file_list(self, file_path, encoding_info):
        """更新编码文件列表显示"""
        rel_path = os.path.relpath(file_path, self.input_path.get())
        
        # 确定显示的编码和状态
        best_encoding = encoding_info.get('best_encoding', 'unknown')
        confidence = encoding_info.get('chardet_confidence', 0)
        target_encoding_info = OUTPUT_ENCODINGS[self.output_encoding_var.get()]
        
        # 确定状态和操作
        if encoding_info.get('file_type') == 'document':
            if encoding_info.get('has_chinese', False):
                status = "需要转换"
                action = f"文档→{target_encoding_info['name']}"
            else:
                status = "无中文"
                action = "直接复制"
        elif best_encoding == target_encoding_info['encoding'] and target_encoding_info['charset'] == 'auto':
            status = "✓ 目标编码"
            action = "直接复制"
        elif encoding_info.get('has_chinese', False):
            status = "需要转换"
            action = f"{best_encoding}→{target_encoding_info['name']}"
        else:
            status = "无中文"
            action = "直接复制"
        
        # 默认选中状态
        select_text = "☑"
        
        # 插入到树形视图
        self.encoding_tree.insert('', 'end', values=(
            select_text,
            rel_path,
            best_encoding,
            f"{confidence:.2f}",
            status,
            action
        ), tags=(file_path,))
        
    def update_copy_file_list(self, file_path, file_info):
        """更新复制文件列表显示"""
        rel_path = os.path.relpath(file_path, self.input_path.get())
        
        # 插入到树形视图
        self.copy_tree.insert('', 'end', values=(
            rel_path,
            file_info.get('size_str', 'Unknown'),
            "待复制"
        ), tags=(file_path,))
    
    def scan_complete(self, target_extensions):
        """扫描完成"""
        self.progress_var.set(100)
        
        # 统计编码分布
        encodings = []
        for file_path, info in self.encoding_results.items():
            if info.get('has_chinese', False):
                encodings.append(info.get('best_encoding', 'unknown'))
        
        encoding_counter = Counter(encodings) if encodings else Counter()
        
        # 计算文件总数和大小
        total_encoding_files = len(self.encoding_results)
        total_copy_files = len(self.copy_files)
        total_files = total_encoding_files + total_copy_files
        
        total_copy_size = sum(info.get('size', 0) for info in self.copy_files.values())
        if total_copy_size < 1024:
            copy_size_str = f"{total_copy_size} B"
        elif total_copy_size < 1024 * 1024:
            copy_size_str = f"{total_copy_size/1024:.1f} KB"
        else:
            copy_size_str = f"{total_copy_size/(1024*1024):.1f} MB"
        
        # 生成统计报告
        summary = f"扫描完成!\n\n"
        summary += f"输入目录: {self.input_path.get()}\n"
        summary += f"输出目录: {self.output_path.get()}\n"
        summary += f"文件类型过滤: {self.file_extensions_var.get()}\n"
        summary += f"输出编码: {self.output_encoding_var.get()}\n\n"
        
        summary += f"文件统计:\n"
        summary += f"  总文件数: {total_files}\n"
        summary += f"  需要编码处理: {total_encoding_files} 个\n"
        summary += f"  直接复制: {total_copy_files} 个 ({copy_size_str})\n\n"
        
        if encodings:
            summary += f"编码分布 (需要处理的文件):\n"
            for encoding, count in encoding_counter.most_common():
                summary += f"  {encoding}: {count} 个文件\n"
        else:
            summary += "需要编码处理的文件中未发现中文内容\n"
        
        # 显示扫描结果
        self.status_var.set(f"扫描完成 - 总计 {total_files} 个文件")
        self.summary_text.delete(1.0, tk.END)
        self.summary_text.insert(tk.END, summary)
        
        # 切换到统计信息标签页
        self.notebook.select(2)
    
    def on_encoding_file_double_click(self, event):
        """编码文件双击事件"""
        selection = self.encoding_tree.selection()
        if not selection:
            return
            
        item = self.encoding_tree.item(selection[0])
        file_path = item['tags'][0]
        
        # 显示文件详细信息
        self.show_encoding_file_details(file_path)
    
    def show_encoding_file_details(self, file_path):
        """显示编码文件详细信息"""
        if file_path not in self.encoding_results:
            return
            
        info = self.encoding_results[file_path]
        target_encoding_info = OUTPUT_ENCODINGS[self.output_encoding_var.get()]
        
        details = f"文件: {os.path.relpath(file_path, self.input_path.get())}\n"
        details += "="*50 + "\n\n"
        
        details += f"输入路径: {file_path}\n"
        output_file_path = self.get_output_file_path(file_path)
        details += f"输出路径: {output_file_path}\n"
        details += f"目标编码: {target_encoding_info['name']}\n\n"
        
        details += f"Chardet检测: {info.get('chardet_encoding', 'unknown')} "
        details += f"(置信度: {info.get('chardet_confidence', 0):.2f})\n"
        details += f"推荐编码: {info.get('best_encoding', 'unknown')}\n"
        details += f"文件类型: {info.get('file_type', 'text')}\n"
        details += f"包含中文: {'是' if info.get('has_chinese', False) else '否'}\n\n"
        
        details += "各编码测试结果:\n"
        details += "-"*30 + "\n"
        
        for encoding, result in info.get('encodings_test', {}).items():
            if result.get('success', False):
                status = "✓"
                if result.get('has_mojibake', False):
                    status += " (乱码)"
                elif result.get('has_chinese', False):
                    status += " (含中文)"
                details += f"{encoding:12}: {status}\n"
            else:
                details += f"{encoding:12}: ✗ 读取失败\n"
        
        self.encoding_detail_text.delete(1.0, tk.END)
        self.encoding_detail_text.insert(tk.END, details)
    
    def get_output_file_path(self, input_file_path):
        """获取输出文件路径"""
        rel_path = os.path.relpath(input_file_path, self.input_path.get())
        return os.path.join(self.output_path.get(), rel_path)
    
    def start_processing(self):
        """开始处理文件"""
        if not self.encoding_results and not self.copy_files:
            messagebox.showerror("错误", "请先扫描文件")
            return
            
        if not self.output_path.get():
            messagebox.showerror("错误", "请先选择输出目录")
            return
        
        # 检查输出目录
        if os.path.exists(self.output_path.get()):
            if os.listdir(self.output_path.get()):
                response = messagebox.askyesno(
                    "输出目录不为空",
                    f"输出目录不为空:\n{self.output_path.get()}\n\n"
                    "继续处理将覆盖同名文件，是否继续?"
                )
                if not response:
                    return
        
        # 统计处理计划（排除被用户取消选择的文件）
        selected_encoding_files = [fp for fp in self.encoding_results.keys() if fp not in self.excluded_files]
        target_encoding_info = OUTPUT_ENCODINGS[self.output_encoding_var.get()]
        
        total_files = len(selected_encoding_files) + len(self.copy_files)
        convert_files = sum(1 for fp in selected_encoding_files 
                          if self.encoding_results[fp].get('has_chinese', False))
        encoding_copy_files = len(selected_encoding_files) - convert_files
        direct_copy_files = len(self.copy_files)
        excluded_count = len(self.excluded_files)
        
        # 计算复制文件总大小
        total_copy_size = sum(info.get('size', 0) for info in self.copy_files.values())
        if total_copy_size < 1024 * 1024:
            copy_size_str = f"{total_copy_size/1024:.1f} KB"
        else:
            copy_size_str = f"{total_copy_size/(1024*1024):.1f} MB"
        
        message = (f"处理计划:\n\n"
                  f"总文件数: {total_files}\n"
                  f"编码转换: {convert_files} 个 (转换为{target_encoding_info['name']})\n"
                  f"编码文件直接复制: {encoding_copy_files} 个\n"
                  f"其他文件直接复制: {direct_copy_files} 个 ({copy_size_str})\n")
        
        if excluded_count > 0:
            message += f"用户排除: {excluded_count} 个 (将直接复制)\n"
            
        message += (f"\n输入目录: {self.input_path.get()}\n"
                   f"输出目录: {self.output_path.get()}\n"
                   f"输出编码: {target_encoding_info['name']}\n\n"
                   f"开始处理?")
        
        response = messagebox.askyesno("确认处理", message)
        
        if not response:
            return
        
        # 在后台线程中执行处理
        self.status_var.set("正在处理文件...")
        self.progress_var.set(0)
        
        thread = threading.Thread(target=self._process_files_thread)
        thread.daemon = True
        thread.start()
    
    def _process_files_thread(self):
        """后台处理文件线程"""
        try:
            target_encoding_info = OUTPUT_ENCODINGS[self.output_encoding_var.get()]
            target_encoding = target_encoding_info['encoding']
            
            # 创建输出目录
            if not os.path.exists(self.output_path.get()):
                os.makedirs(self.output_path.get())
            
            success_count = 0
            fail_count = 0
            convert_count = 0
            encoding_copy_count = 0
            direct_copy_count = 0
            excluded_copy_count = 0
            
            # 将排除的编码文件移到复制列表处理
            excluded_encoding_files = {}
            for file_path in self.excluded_files:
                if file_path in self.encoding_results:
                    excluded_encoding_files[file_path] = self.get_file_info(file_path)
            
            selected_encoding_files = {fp: info for fp, info in self.encoding_results.items() 
                                     if fp not in self.excluded_files}
            
            total_files = len(selected_encoding_files) + len(self.copy_files) + len(excluded_encoding_files)
            processed_count = 0
            
            # 处理选中的编码文件
            for file_path, info in selected_encoding_files.items():
                # 更新进度
                progress = (processed_count / total_files) * 100
                self.root.after(0, lambda p=progress: self.progress_var.set(p))
                
                # 获取输出路径
                output_file_path = self.get_output_file_path(file_path)
                
                # 确保输出目录存在
                output_dir = os.path.dirname(output_file_path)
                if not os.path.exists(output_dir):
                    os.makedirs(output_dir)
                
                # 判断是否需要转换
                source_encoding = info.get('best_encoding', 'utf-8')
                has_chinese = info.get('has_chinese', False)
                
                if has_chinese:
                    # 需要转换编码
                    if self.convert_and_save_file(file_path, output_file_path, source_encoding, target_encoding_info):
                        success_count += 1
                        convert_count += 1
                        action_text = f"✓ 已转换 ({source_encoding}→{target_encoding_info['name']})"
                    else:
                        fail_count += 1
                        action_text = "✗ 转换失败"
                else:
                    # 直接复制文件
                    if self.copy_file(file_path, output_file_path):
                        success_count += 1
                        encoding_copy_count += 1
                        action_text = "✓ 已复制"
                    else:
                        fail_count += 1
                        action_text = "✗ 复制失败"
                
                # 更新文件状态
                self.root.after(0, lambda fp=file_path, at=action_text: self.update_encoding_file_action(fp, at))
                processed_count += 1
            
            # 处理排除的编码文件（直接复制）
            for file_path, file_info in excluded_encoding_files.items():
                # 更新进度
                progress = (processed_count / total_files) * 100
                self.root.after(0, lambda p=progress: self.progress_var.set(p))
                
                # 获取输出路径
                output_file_path = self.get_output_file_path(file_path)
                
                # 确保输出目录存在
                output_dir = os.path.dirname(output_file_path)
                if not os.path.exists(output_dir):
                    os.makedirs(output_dir)
                
                # 直接复制文件
                if self.copy_file(file_path, output_file_path):
                    success_count += 1
                    excluded_copy_count += 1
                    action_text = "✓ 已复制(排除)"
                else:
                    fail_count += 1
                    action_text = "✗ 复制失败"
                
                # 更新文件状态
                self.root.after(0, lambda fp=file_path, at=action_text: self.update_encoding_file_action(fp, at))
                processed_count += 1
            
            # 处理需要直接复制的文件
            for file_path, file_info in self.copy_files.items():
                # 更新进度
                progress = (processed_count / total_files) * 100
                self.root.after(0, lambda p=progress: self.progress_var.set(p))
                
                # 获取输出路径
                output_file_path = self.get_output_file_path(file_path)
                
                # 确保输出目录存在
                output_dir = os.path.dirname(output_file_path)
                if not os.path.exists(output_dir):
                    os.makedirs(output_dir)
                
                # 直接复制文件
                if self.copy_file(file_path, output_file_path):
                    success_count += 1
                    direct_copy_count += 1
                    status_text = "✓ 已复制"
                else:
                    fail_count += 1
                    status_text = "✗ 复制失败"
                
                # 更新文件状态
                self.root.after(0, lambda fp=file_path, st=status_text: self.update_copy_file_status(fp, st))
                processed_count += 1
            
            # 处理完成
            self.root.after(0, lambda: self.processing_complete(
                total_files, success_count, fail_count, convert_count, 
                encoding_copy_count, direct_copy_count, excluded_copy_count, target_encoding_info))
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("处理错误", f"处理过程中出现错误: {str(e)}"))
    
    def convert_and_save_file(self, input_path, output_path, source_encoding, target_encoding_info):
        """转换编码并保存文件"""
        try:
            # 读取原文件内容
            content = self.read_file_content(input_path, source_encoding)
            
            # 进行简繁体转换
            converted_content = self.convert_text_encoding(content, self.output_encoding_var.get())
            
            # 写入新编码到输出文件
            target_encoding = target_encoding_info['encoding']
            
            # 处理文档类型文件
            file_ext = os.path.splitext(input_path)[1].lower()
            if file_ext in ['.doc', '.docx', '.rtf', '.odt']:
                # 文档类型转换为文本文件
                output_path = os.path.splitext(output_path)[0] + '.txt'
            
            with open(output_path, 'w', encoding=target_encoding) as f:
                f.write(converted_content)
            
            return True
            
        except Exception as e:
            return False
    
    def copy_file(self, input_path, output_path):
        """复制文件"""
        try:
            shutil.copy2(input_path, output_path)
            return True
        except Exception as e:
            return False
    
    def update_encoding_file_action(self, file_path, new_action):
        """更新编码文件操作状态显示"""
        for item in self.encoding_tree.get_children():
            if self.encoding_tree.item(item)['tags'][0] == file_path:
                values = list(self.encoding_tree.item(item)['values'])
                values[5] = new_action  # 操作列
                self.encoding_tree.item(item, values=values)
                break
                
    def update_copy_file_status(self, file_path, new_status):
        """更新复制文件状态显示"""
        for item in self.copy_tree.get_children():
            if self.copy_tree.item(item)['tags'][0] == file_path:
                values = list(self.copy_tree.item(item)['values'])
                values[2] = new_status  # 状态列
                self.copy_tree.item(item, values=values)
                break
    
    def processing_complete(self, total, success, fail, convert_count, encoding_copy_count, 
                          direct_copy_count, excluded_copy_count, target_encoding_info):
        """处理完成"""
        self.progress_var.set(100)
        
        # 构建完成消息
        message = f"处理完成!\n\n"
        message += f"输入目录: {self.input_path.get()}\n"
        message += f"输出目录: {self.output_path.get()}\n"
        message += f"文件类型过滤: {self.file_extensions_var.get()}\n"
        message += f"输出编码: {target_encoding_info['name']}\n\n"
        message += f"处理统计:\n"
        message += f"  总文件数: {total}\n"
        message += f"  成功处理: {success}\n"
        message += f"  处理失败: {fail}\n"
        message += f"  编码转换: {convert_count}\n"
        message += f"  编码文件复制: {encoding_copy_count}\n"
        message += f"  其他文件复制: {direct_copy_count}\n"
        
        if excluded_copy_count > 0:
            message += f"  用户排除复制: {excluded_copy_count}\n"
        
        if self.has_opencc and target_encoding_info['charset'] != 'auto':
            message += f"\n简繁体转换: {'已启用' if convert_count > 0 else '无需转换'}\n"
        
        message += f"\n所有文件已保存到输出目录:\n{self.output_path.get()}"
        
        self.status_var.set(f"处理完成 - 成功: {success}, 失败: {fail}")
        
        # 显示详细结果
        self.summary_text.delete(1.0, tk.END)
        self.summary_text.insert(tk.END, message)
        
        # 切换到统计信息标签页
        self.notebook.select(2)
        
        # 弹出完成对话框
        result = messagebox.askquestion(
            "处理完成", 
            message + "\n\n是否打开输出目录?",
            type=messagebox.YESNO
        )
        
        if result == 'yes':
            self.open_output_directory()
    
    def clear_results(self):
        """清除结果"""
        self.encoding_results.clear()
        self.copy_files.clear()
        self.excluded_files.clear()
        self.encoding_tree.delete(*self.encoding_tree.get_children())
        self.copy_tree.delete(*self.copy_tree.get_children())
        self.encoding_detail_text.delete(1.0, tk.END)
        self.summary_text.delete(1.0, tk.END)
        self.progress_var.set(0)
        self.status_var.set("已清除结果")
        
        # 关闭预览窗口
        self.close_preview_window()

def main():
    root = tk.Tk()
    app = EncodingUnifierGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()