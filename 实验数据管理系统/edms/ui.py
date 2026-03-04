from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from edms.app import ExperimentDataSystem


class EDMSUI(tk.Tk):
    def __init__(self, db_path: str = "experiment_data.db") -> None:
        super().__init__()
        self.title("实验数据管理系统")
        self.geometry("980x700")
        self.system = ExperimentDataSystem(db_path)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True)

        self._build_category_tab()
        self._build_record_tab()
        self._build_data_entry_tab()
        self._build_query_tab()
        self._build_export_tab()

    def _build_category_tab(self) -> None:
        tab = ttk.Frame(self.tabs)
        self.tabs.add(tab, text="分类管理")

        form = ttk.LabelFrame(tab, text="新增分类")
        form.pack(fill="x", padx=10, pady=10)

        self.cat_name = tk.StringVar()
        self.cat_desc = tk.StringVar()
        ttk.Label(form, text="分类名").grid(row=0, column=0, padx=8, pady=8)
        ttk.Entry(form, textvariable=self.cat_name, width=30).grid(row=0, column=1, padx=8, pady=8)
        ttk.Label(form, text="描述").grid(row=0, column=2, padx=8, pady=8)
        ttk.Entry(form, textvariable=self.cat_desc, width=40).grid(row=0, column=3, padx=8, pady=8)
        ttk.Button(form, text="新增", command=self.add_category).grid(row=0, column=4, padx=8, pady=8)

        self.cat_text = tk.Text(tab, height=24)
        self.cat_text.pack(fill="both", expand=True, padx=10, pady=10)
        ttk.Button(tab, text="刷新分类列表", command=self.refresh_categories).pack(pady=(0, 10))

    def _build_record_tab(self) -> None:
        tab = ttk.Frame(self.tabs)
        self.tabs.add(tab, text="实验记录")

        form = ttk.LabelFrame(tab, text="新增实验记录")
        form.pack(fill="x", padx=10, pady=10)

        self.rec_title = tk.StringVar()
        self.rec_researcher = tk.StringVar()
        self.rec_date = tk.StringVar()
        self.rec_status = tk.StringVar(value="running")
        self.rec_notes = tk.StringVar()

        labels = ["标题", "负责人", "实验日期", "状态", "备注"]
        vars_ = [self.rec_title, self.rec_researcher, self.rec_date, self.rec_status, self.rec_notes]
        for i, (lab, var) in enumerate(zip(labels, vars_)):
            ttk.Label(form, text=lab).grid(row=0, column=i * 2, padx=6, pady=8)
            ttk.Entry(form, textvariable=var, width=16).grid(row=0, column=i * 2 + 1, padx=6, pady=8)
        ttk.Button(form, text="新增", command=self.add_record).grid(row=0, column=10, padx=6, pady=8)

        self.rec_text = tk.Text(tab, height=24)
        self.rec_text.pack(fill="both", expand=True, padx=10, pady=10)
        ttk.Button(tab, text="刷新实验记录", command=self.refresh_records).pack(pady=(0, 10))

    def _build_data_entry_tab(self) -> None:
        tab = ttk.Frame(self.tabs)
        self.tabs.add(tab, text="数据录入")

        form = ttk.LabelFrame(tab, text="新增实验数据")
        form.pack(fill="x", padx=10, pady=10)

        self.data_name = tk.StringVar()
        self.data_category_id = tk.StringVar()
        self.data_value = tk.StringVar()
        self.data_unit = tk.StringVar()
        self.data_time = tk.StringVar()
        self.data_operator = tk.StringVar()
        self.data_record_id = tk.StringVar()
        self.data_remarks = tk.StringVar()

        entries = [
            ("数据名", self.data_name),
            ("分类ID", self.data_category_id),
            ("数值", self.data_value),
            ("单位", self.data_unit),
            ("记录时间", self.data_time),
            ("操作人", self.data_operator),
            ("记录ID(可空)", self.data_record_id),
            ("备注", self.data_remarks),
        ]
        for idx, (lab, var) in enumerate(entries):
            row = idx // 4
            col = (idx % 4) * 2
            ttk.Label(form, text=lab).grid(row=row, column=col, padx=6, pady=8)
            ttk.Entry(form, textvariable=var, width=20).grid(row=row, column=col + 1, padx=6, pady=8)

        ttk.Button(form, text="录入", command=self.add_data).grid(row=2, column=7, padx=6, pady=8)

    def _build_query_tab(self) -> None:
        tab = ttk.Frame(self.tabs)
        self.tabs.add(tab, text="查询统计")

        box = ttk.LabelFrame(tab, text="查询条件")
        box.pack(fill="x", padx=10, pady=10)

        self.q_category = tk.StringVar()
        self.q_keyword = tk.StringVar()
        self.q_start = tk.StringVar()
        self.q_end = tk.StringVar()

        fields = [
            ("分类ID", self.q_category),
            ("关键字", self.q_keyword),
            ("开始时间", self.q_start),
            ("结束时间", self.q_end),
        ]
        for i, (lab, var) in enumerate(fields):
            ttk.Label(box, text=lab).grid(row=0, column=i * 2, padx=6, pady=8)
            ttk.Entry(box, textvariable=var, width=20).grid(row=0, column=i * 2 + 1, padx=6, pady=8)

        ttk.Button(box, text="查询", command=self.run_query).grid(row=0, column=8, padx=6, pady=8)
        ttk.Button(box, text="分类统计", command=self.run_stats).grid(row=0, column=9, padx=6, pady=8)

        self.query_text = tk.Text(tab, height=28)
        self.query_text.pack(fill="both", expand=True, padx=10, pady=10)

    def _build_export_tab(self) -> None:
        tab = ttk.Frame(self.tabs)
        self.tabs.add(tab, text="导出")

        frame = ttk.LabelFrame(tab, text="导出数据")
        frame.pack(fill="x", padx=10, pady=10)
        self.export_fmt = tk.StringVar(value="json")
        self.export_path = tk.StringVar(value="exports/all_data.json")

        ttk.Label(frame, text="格式").grid(row=0, column=0, padx=6, pady=8)
        ttk.Combobox(frame, textvariable=self.export_fmt, values=["json", "csv"], width=8).grid(
            row=0, column=1, padx=6, pady=8
        )
        ttk.Label(frame, text="路径").grid(row=0, column=2, padx=6, pady=8)
        ttk.Entry(frame, textvariable=self.export_path, width=50).grid(row=0, column=3, padx=6, pady=8)
        ttk.Button(frame, text="导出", command=self.export_data).grid(row=0, column=4, padx=6, pady=8)

    def add_category(self) -> None:
        try:
            category_id = self.system.categories.add_category(self.cat_name.get(), self.cat_desc.get())
            messagebox.showinfo("成功", f"分类新增成功，ID={category_id}")
            self.refresh_categories()
        except Exception as exc:
            messagebox.showerror("错误", str(exc))

    def refresh_categories(self) -> None:
        rows = self.system.categories.list_categories()
        self.cat_text.delete("1.0", tk.END)
        for row in rows:
            self.cat_text.insert(tk.END, f"{dict(row)}\n")

    def add_record(self) -> None:
        try:
            record_id = self.system.records.add_record(
                self.rec_title.get(),
                self.rec_researcher.get(),
                self.rec_date.get(),
                self.rec_status.get(),
                self.rec_notes.get(),
            )
            messagebox.showinfo("成功", f"实验记录新增成功，ID={record_id}")
            self.refresh_records()
        except Exception as exc:
            messagebox.showerror("错误", str(exc))

    def refresh_records(self) -> None:
        rows = self.system.records.list_records()
        self.rec_text.delete("1.0", tk.END)
        for row in rows:
            self.rec_text.insert(tk.END, f"{dict(row)}\n")

    def add_data(self) -> None:
        try:
            record_id = int(self.data_record_id.get()) if self.data_record_id.get().strip() else None
            data_id = self.system.data.add_data(
                self.data_name.get(),
                int(self.data_category_id.get()),
                float(self.data_value.get()),
                self.data_unit.get(),
                self.data_time.get(),
                self.data_operator.get(),
                record_id,
                self.data_remarks.get(),
            )
            messagebox.showinfo("成功", f"实验数据录入成功，ID={data_id}")
        except Exception as exc:
            messagebox.showerror("错误", str(exc))

    def run_query(self) -> None:
        try:
            category_id = int(self.q_category.get()) if self.q_category.get().strip() else None
            rows = self.system.data.query_data(
                category_id=category_id,
                keyword=self.q_keyword.get() or None,
                date_start=self.q_start.get() or None,
                date_end=self.q_end.get() or None,
            )
            self.query_text.delete("1.0", tk.END)
            for row in rows:
                self.query_text.insert(tk.END, f"{dict(row)}\n")
        except Exception as exc:
            messagebox.showerror("错误", str(exc))

    def run_stats(self) -> None:
        rows = self.system.data.stats_by_category()
        self.query_text.delete("1.0", tk.END)
        for row in rows:
            self.query_text.insert(tk.END, f"{dict(row)}\n")

    def export_data(self) -> None:
        try:
            out = self.system.data.export_data(self.export_fmt.get(), self.export_path.get())
            messagebox.showinfo("成功", f"导出完成：{out}")
        except Exception as exc:
            messagebox.showerror("错误", str(exc))

    def on_close(self) -> None:
        self.system.close()
        self.destroy()


def run_ui(db_path: str = "experiment_data.db") -> None:
    app = EDMSUI(db_path)
    app.mainloop()
