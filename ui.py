import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog
from tkcalendar import Calendar
import calendar as pycalendar
from datetime import date, datetime
import os, sys

import database
import settings as app_settings

class TaskPlannerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🗓️ Планировщик задач")
        self.root.geometry("1200x800")

        # Инициализация базы и настроек
        database.init_db()
        self.settings = app_settings.load_settings()

        # Проверка пароля (если задан)
        if self.settings.get("app_password"):
            if not self._prompt_password():
                self.root.destroy()
                return

        # Установка темы
        self._apply_theme(self.settings.get("theme", "light"))

        # Инициализация текущей даты ДО построения интерфейса
        today = date.today()
        self.current_year = today.year
        self.current_month = today.month

        # Построение интерфейса
        self._setup_window()
        self._build_ui()

        # Отрисовка календаря и списка задач
        self._render_month(self.current_year, self.current_month)
        self.refresh_task_list()

        # Предложение автозапуска при первом запуске
        if self.settings.get("autostart_enabled") is False:
            self._ask_autostart_once()

    # ====== Окно ======
    def _setup_window(self):
        self.canvas = tk.Canvas(self.root, highlightthickness=0, bg=self.bg)
        self.canvas.pack(fill="both", expand=True)
        self.inner = tk.Frame(self.canvas, bg=self.bg)
        self.inner.place(relx=0.5, rely=0.5, anchor="center", width=1180, height=780)
        self.root.bind("<Configure>", self._redraw_bg)

    def _redraw_bg(self, event=None):
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        self.canvas.delete("all")
        self.canvas.create_rectangle(0, 0, w, h, fill=self.bg, outline=self.bg)

    # ====== Тема ======
    def _apply_theme(self, theme):
        style = ttk.Style()
        if theme == "dark":
            style.theme_use("clam")
            self.bg = "#2c3e50"
            self.panel_bg = "#34495e"
            self.fg = "white"
            self.accent = "#3b82f6"
            style.configure("Treeview", background="#1f2937", fieldbackground="#1f2937",
                            foreground="white")
            style.map("Treeview", background=[("selected", "#3b82f6")], foreground=[("selected", "white")])
        else:
            style.theme_use("default")
            self.bg = "#eef2f7"
            self.panel_bg = "#f7f9fc"
            self.fg = "#1f2937"
            self.accent = "#2563eb"
            style.configure("Treeview", background="white", fieldbackground="white",
                            foreground="black")
            style.map("Treeview", background=[("selected", "#cfe3ff")], foreground=[("selected", "black")])

        # Перерисовать уже созданные элементы, если есть
        if hasattr(self, "inner"):
            self.inner.configure(bg=self.bg)
            for child in self.inner.winfo_children():
                self._try_set_colors(child)
        if hasattr(self, "canvas"):
            self._redraw_bg()
        if hasattr(self, "month_grid") and hasattr(self, "current_year"):
            self._render_month(self.current_year, self.current_month)
        if hasattr(self, "list_tab"):
            self.refresh_task_list()

    def _try_set_colors(self, widget):
        # Рекурсивно обновляем bg/fg, где возможно
        try:
            widget.configure(bg=self.bg, fg=self.fg)
        except Exception:
            try:
                widget.configure(bg=self.bg)
            except Exception:
                pass
        for ch in widget.winfo_children():
            self._try_set_colors(ch)

    # ====== UI ======
    def _build_ui(self):
        # Верхнее меню (только нужные)
        menubar = tk.Frame(self.inner, bg=self.panel_bg)
        menubar.pack(fill="x", padx=10, pady=(10, 4))
        tk.Button(menubar, text="Настройки", bg=self.panel_bg, fg=self.fg,
                  relief="flat", command=self.open_settings_window).pack(side="left", padx=6)
        tk.Button(menubar, text="Справка", bg=self.panel_bg, fg=self.fg,
                  relief="flat", command=self.show_about).pack(side="left", padx=6)

        # Тело
        body = tk.Frame(self.inner, bg=self.bg)
        body.pack(fill="both", expand=True, padx=16, pady=8)

        # Левая панель
        left = tk.Frame(body, bg=self.panel_bg, bd=1, relief="solid")
        left.pack(side="left", fill="y", padx=(0, 8))

        tk.Label(left, text="Календарь", bg=self.panel_bg, fg=self.fg,
                 font=("Arial", 11, "bold")).pack(pady=(8, 0))
        self.mini_cal = Calendar(left, selectmode='day', date_pattern='yyyy-mm-dd')
        self.mini_cal.pack(padx=8, pady=8)

        tk.Label(left, text="Категории", bg=self.panel_bg, fg=self.fg,
                 font=("Arial", 11, "bold")).pack(anchor="w", padx=8, pady=(8, 4))
        self.cal_list = tk.Listbox(left, height=6)
        self._refresh_categories_listbox()
        self.cal_list.pack(fill="x", padx=8, pady=(0, 8))

        tk.Button(left, text="Создать задачу", command=self.open_create_task_window,
                  bg=self.accent, fg="white").pack(fill="x", padx=8, pady=(4, 12))

        # Правая часть: вкладки
        right = tk.Frame(body, bg=self.bg)
        right.pack(side="right", fill="both", expand=True)

        self.tabs = ttk.Notebook(right)
        self.tabs.pack(fill="both", expand=True)

        # Вкладка Месяц
        self.month_tab = tk.Frame(self.tabs, bg=self.bg)
        self.tabs.add(self.month_tab, text="Месяц")

        nav = tk.Frame(self.month_tab, bg=self.bg)
        nav.pack(fill="x", padx=8, pady=6)
        tk.Button(nav, text="◀", command=lambda: self._change_month(-1)).pack(side="left")
        self.month_label = tk.Label(nav, text=self._month_title(), bg=self.bg,
                                    fg=self.fg, font=("Arial", 12, "bold"))
        self.month_label.pack(side="left", padx=8)
        tk.Button(nav, text="▶", command=lambda: self._change_month(1)).pack(side="left")

        self.month_grid = tk.Frame(self.month_tab, bg=self.bg)
        self.month_grid.pack(fill="both", expand=True, padx=8, pady=8)

        self.status_bar = tk.Label(self.month_tab, text="", bg=self.panel_bg,
                                   fg=self.fg, anchor="w")
        self.status_bar.pack(fill="x", padx=8, pady=(0, 8))

        # Вкладка Задачи
        self.list_tab = tk.Frame(self.tabs, bg=self.bg)
        self.tabs.add(self.list_tab, text="Задачи")
        self._build_list_tab(self.list_tab)

    # ====== Месячный календарь ======
    def _month_title(self):
        month_names = ["Январь","Февраль","Март","Апрель","Май","Июнь",
                       "Июль","Август","Сентябрь","Октябрь","Ноябрь","Декабрь"]
        return f"{month_names[self.current_month-1]} {self.current_year}"

    def _change_month(self, delta):
        m = self.current_month + delta
        y = self.current_year
        if m < 1:
            m = 12; y -= 1
        elif m > 12:
            m = 1; y += 1
        self.current_month, self.current_year = m, y
        self.month_label.config(text=self._month_title())
        self._render_month(y, m)

    def _render_month(self, year, month):
        for w in self.month_grid.winfo_children():
            w.destroy()

        days = ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"]
        for i, d in enumerate(days):
            tk.Label(self.month_grid, text=d, bg=self.bg, fg=self.fg,
                     font=("Arial", 10, "bold")).grid(row=0, column=i, padx=4, pady=4)

        cal = pycalendar.Calendar(firstweekday=0)
        month_days = cal.monthdayscalendar(year, month)

        tasks = database.get_all_tasks()
        tasks_by_date = {}
        for t in tasks:
            dl = t[4]
            if dl:
                tasks_by_date.setdefault(dl, []).append(t)

        for r, week in enumerate(month_days, start=1):
            for c, day in enumerate(week):
                cell = tk.Frame(self.month_grid, bg="white", bd=1, relief="solid")
                cell.grid(row=r, column=c, padx=2, pady=2, sticky="nsew")
                self.month_grid.grid_columnconfigure(c, weight=1)
                self.month_grid.grid_rowconfigure(r, weight=1)

                if day == 0:
                    continue

                d_str = f"{year:04d}-{month:02d}-{day:02d}"

                # Заголовок дня
                hdr = tk.Frame(cell, bg="#e5e7eb")
                hdr.pack(fill="x")
                tk.Label(hdr, text=str(day), bg="#e5e7eb", fg="#111827").pack(side="left", padx=4)

                # Список задач
                body = tk.Frame(cell, bg="white")
                body.pack(fill="both", expand=True)

                for task in tasks_by_date.get(d_str, []):
                    title = task[1]
                    status = task[7]
                    color = {
                        "completed": "#d1fae5",   # зелёный
                        "in progress": "#fde68a", # оранжевый
                        "postponed": "#fecaca",   # красный
                        "pending": "#f3f4f6"      # серый
                    }.get(status, "#f3f4f6")
                    lbl = tk.Label(body, text=title, bg=color, anchor="w")
                    lbl.pack(fill="x", padx=4, pady=2)

                    # ЛКМ — показать инфо
                    lbl.bind("<Button-1>", lambda e, t=task, yy=year, mm=month, dd=day: self._select_day(yy, mm, dd, t))

                    # ПКМ — контекстное меню статуса
                    def _show_status_menu(ev, t=task):
                        menu = tk.Menu(self.root, tearoff=0)
                        menu.add_command(label="В процессе", command=lambda: self._set_task_status(t[0], "in progress"))
                        menu.add_command(label="Завершено", command=lambda: self._set_task_status(t[0], "completed"))
                        menu.add_command(label="Отложено", command=lambda: self._set_task_status(t[0], "postponed"))
                        menu.add_command(label="В ожидании", command=lambda: self._set_task_status(t[0], "pending"))
                        menu.tk_popup(ev.x_root, ev.y_root)
                    lbl.bind("<Button-3>", _show_status_menu)

                # Выделение сегодняшнего дня
                today = date.today()
                if today.year == year and today.month == month and today.day == day:
                    cell.config(bg=self.accent)
                    hdr.config(bg=self.accent)
                    for ch in hdr.winfo_children():
                        ch.config(bg=self.accent, fg="white")

                # Клик по пустой области — выбрать день
                cell.bind("<Button-1>", lambda e, dd=d_str: self._select_day_str(dd))

    def _set_task_status(self, task_id, new_status):
        database.update_task_status(task_id, new_status)
        self._render_month(self.current_year, self.current_month)
        self.refresh_task_list()

    def _select_day(self, y, m, d, task=None):
        dt = datetime(y, m, d)
        months_ru = ["января","февраля","марта","апреля","мая","июня","июля","августа","сентября","октября","ноября","декабря"]
        weekdays_ru = ["Понедельник","Вторник","Среда","Четверг","Пятница","Суббота","Воскресенье"]
        weekday = weekdays_ru[dt.weekday()]
        text = f"{weekday}, {dt.day} {months_ru[dt.month-1]} {dt.year}"
        self.status_bar.config(text=text)
        if task:
            self._show_task_info_popup(task)

    def _select_day_str(self, dstr):
        try:
            y, m, d = map(int, dstr.split("-"))
            self._select_day(y, m, d)
        except Exception:
            pass

    # ====== Вкладка «Задачи» ======
    def _build_list_tab(self, parent):
        # Панель фильтров
        pnl = tk.Frame(parent, bg=self.bg)
        pnl.pack(fill="x", padx=8, pady=6)

        tk.Label(pnl, text="Статус:", bg=self.bg, fg=self.fg).pack(side="left")
        self.filter_status = tk.StringVar(value="all")
        for label, status in [("Все","all"), ("В ожидании","pending"), ("В процессе","in progress"),
                              ("Завершено","completed"), ("Отложено","postponed")]:
            tk.Radiobutton(pnl, text=label, variable=self.filter_status, value=status,
                           command=self.refresh_task_list, bg=self.bg, fg=self.fg,
                           selectcolor=self.panel_bg).pack(side="left", padx=3)

        tk.Label(pnl, text="Категория:", bg=self.bg, fg=self.fg).pack(side="left", padx=(10, 2))
        self.filter_category = tk.StringVar(value="all")
        self.cat_menu = ttk.Combobox(pnl, values=["all"] + self.settings.get("categories", []), width=18)
        self.cat_menu.bind("<<ComboboxSelected>>", lambda e: self.filter_category.set(self.cat_menu.get()) or self.refresh_task_list())
        self.cat_menu.set("all")
        self.cat_menu.pack(side="left", padx=3)

        tk.Label(pnl, text="Поиск:", bg=self.bg, fg=self.fg).pack(side="left", padx=(10, 2))
        self.filter_search = tk.Entry(pnl, width=24)
        self.filter_search.pack(side="left")
        self.filter_search.bind("<KeyRelease>", lambda e: self.refresh_task_list())

        # Обёртка для Treeview, чтобы прокрутки были внутри вкладки
        tree_wrap = tk.Frame(parent, bg=self.bg)
        tree_wrap.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        columns = ("ID","Название","Категория","Приоритет","Статус","Создано","Дедлайн")
        self.tree = ttk.Treeview(tree_wrap, columns=columns, show="headings", height=18, selectmode="extended")

        # Ширины для горизонтальной прокрутки
        self.tree.column("ID", width=80, anchor="center")
        self.tree.column("Название", width=320, anchor="w")
        self.tree.column("Категория", width=180, anchor="center")
        self.tree.column("Приоритет", width=140, anchor="center")
        self.tree.column("Статус", width=160, anchor="center")
        self.tree.column("Создано", width=160, anchor="center")
        self.tree.column("Дедлайн", width=160, anchor="center")

        for col in columns:
            self.tree.heading(col, text=col, command=lambda c=col: self._sort_tree_by_column(c))

        # Прокрутки в обе стороны
        sb_y = ttk.Scrollbar(tree_wrap, orient="vertical", command=self.tree.yview)
        sb_x = ttk.Scrollbar(tree_wrap, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=sb_y.set, xscrollcommand=sb_x.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        sb_y.grid(row=0, column=1, sticky="ns")
        sb_x.grid(row=1, column=0, sticky="ew")
        tree_wrap.grid_rowconfigure(0, weight=1)
        tree_wrap.grid_columnconfigure(0, weight=1)

        # Панель действий
        actions = tk.Frame(parent, bg=self.bg)
        actions.pack(fill="x", padx=8, pady=6)
        tk.Button(actions, text="✅ Выполнено", command=lambda: self._bulk_status('completed'),
                  bg="#22c55e", fg="white").pack(side="left", padx=4)
        tk.Button(actions, text="🔄 В процессе", command=lambda: self._bulk_status('in progress'),
                  bg="#f59e0b", fg="white").pack(side="left", padx=4)
        tk.Button(actions, text="⏸️ Отложено", command=lambda: self._bulk_status('postponed'),
                  bg="#ef4444", fg="white").pack(side="left", padx=4)
        tk.Button(actions, text="🗑️ Удалить", command=self._bulk_delete,
                  bg="#dc2626", fg="white").pack(side="left", padx=4)

        # Двойной клик — детали
        self.tree.bind("<Double-1>", self._show_task_details)

        # Горячие клавиши: копировать/вставить
        self.tree.bind("<Control-c>", self._copy_selected_to_clipboard)
        self.tree.bind("<Control-C>", self._copy_selected_to_clipboard)
        self.tree.bind("<Control-v>", self._paste_tasks)
        self.tree.bind("<Control-V>", self._paste_tasks)

        # Контекстное меню статуса в списке (ПКМ)
        self.tree.bind("<Button-3>", self._tree_context_menu)

    def _tree_context_menu(self, event):
        iid = self.tree.identify_row(event.y)
        if not iid:
            return
        self.tree.selection_set(iid)
        tid = self.tree.item(iid)['values'][0]
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="В процессе", command=lambda: self._set_task_status(tid, "in progress"))
        menu.add_command(label="Завершено", command=lambda: self._set_task_status(tid, "completed"))
        menu.add_command(label="Отложено", command=lambda: self._set_task_status(tid, "postponed"))
        menu.add_command(label="В ожидании", command=lambda: self._set_task_status(tid, "pending"))
        menu.tk_popup(event.x_root, event.y_root)

    # ====== Копирование/вставка ======
    def _copy_selected_to_clipboard(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        headers = ["ID","Название","Категория","Приоритет","Статус","Создано","Дедлайн"]
        lines = ["\t".join(headers)]
        for iid in sel:
            values = self.tree.item(iid)["values"]
            str_vals = [str(v if v is not None else "") for v in values]
            lines.append("\t".join(str_vals))
        text = "\n".join(lines)
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.root.update()
        except Exception:
            pass

    def _paste_tasks(self, event=None):
        try:
            data = self.root.clipboard_get()
        except Exception:
            data = ""

        def _priority_from_ru(s):
            return {"Низкий":"low","Средний":"medium","Высокий":"high"}.get(s, "medium")

        def _status_from_ru(s):
            return {"В ожидании":"pending","В процессе":"in progress","Завершено":"completed","Отложено":"postponed"}.get(s, "pending")

        inserted = 0

        # Импорт из TSV
        if data and "\t" in data:
            lines = [ln for ln in data.strip().splitlines() if ln.strip()]
            start_idx = 1 if lines and lines[0].lower().startswith("id\t") else 0
            for ln in lines[start_idx:]:
                cols = ln.split("\t")
                if len(cols) >= 7:
                    title = cols[1].strip() or "Без названия"
                    category = cols[2].strip()
                    priority = _priority_from_ru(cols[3].strip())
                    status = _status_from_ru(cols[4].strip())
                    deadline = cols[6].strip() or None
                    task_data = {
                        'title': title,
                        'description': '',
                        'deadline': deadline,
                        'priority': priority,
                        'category': category,
                        'status': status,
                        'tags': '',
                        'recurrence': None,
                        'reminder': None
                    }
                    database.add_task(task_data)
                    inserted += 1

        # Если из буфера не получилось — дублируем выделенные
        if inserted == 0:
            sel = self.tree.selection()
            if not sel:
                return
            ids = [self.tree.item(i)['values'][0] for i in sel]
            all_tasks = {t[0]: t for t in database.get_all_tasks()}
            for tid in ids:
                t = all_tasks.get(tid)
                if not t:
                    continue
                copy_data = {
                    'title': f"{t[1]} (копия)",
                    'description': t[2] or '',
                    'deadline': t[4],
                    'priority': t[5] or 'medium',
                    'category': t[6] or '',
                    'status': t[7] or 'pending',
                    'tags': t[8] or '',
                    'recurrence': t[9],
                    'reminder': t[10]
                }
                database.add_task(copy_data)
                inserted += 1

        if inserted > 0:
            self._render_month(self.current_year, self.current_month)
            self.refresh_task_list()
            messagebox.showinfo("Вставка", f"Добавлено задач: {inserted}")

    # ====== Хелперы списка ======
    def refresh_task_list(self):
        status = self.filter_status.get() if hasattr(self, "filter_status") else "all"
        category = self.filter_category.get() if hasattr(self, "filter_category") else "all"
        keyword = self.filter_search.get().strip() if hasattr(self, "filter_search") else ""

        tasks = database.get_all_tasks_ordered()
        if status != "all":
            tasks = [t for t in tasks if t[7] == status]
        if category != "all":
            tasks = [t for t in tasks if (t[6] or "") == category]
        if keyword:
            kw = keyword.lower()
            tasks = [t for t in tasks if kw in (t[1] or "").lower() or kw in (t[2] or "").lower()]

        if hasattr(self, "tree"):
            for item in self.tree.get_children():
                self.tree.delete(item)
            priority_display = {"low":"Низкий","medium":"Средний","high":"Высокий"}
            status_display = {"pending":"В ожидании","in progress":"В процессе","completed":"Завершено","postponed":"Отложено"}
            for t in tasks:
                created_date = (t[3].split()[0] if isinstance(t[3], str) else str(t[3])[:10]) if t[3] else ""
                deadline_date = t[4] or ""
                self.tree.insert("", "end", values=(t[0], t[1], t[6] or "",
                                                    priority_display.get(t[5], t[5]),
                                                    status_display.get(t[7], t[7]),
                                                    created_date, deadline_date))

    def _sort_tree_by_column(self, col):
        items = [(self.tree.set(i, col), i) for i in self.tree.get_children("")]
        try:
            def keyfunc(x):
                val = x[0]
                if col == "ID":
                    try:
                        return int(val)
                    except Exception:
                        return 0
                return val
            items.sort(key=keyfunc)
        except Exception:
            pass
        for idx, (_, iid) in enumerate(items):
            self.tree.move(iid, "", idx)

    def _bulk_status(self, new_status):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Статус", "Выберите задачи.")
            return
        for iid in sel:
            tid = self.tree.item(iid)['values'][0]
            database.update_task_status(tid, new_status)
        self._render_month(self.current_year, self.current_month)
        self.refresh_task_list()

    def _bulk_delete(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Удаление", "Выберите задачи.")
            return
        if not messagebox.askyesno("Удаление", f"Удалить выбранные задачи ({len(sel)})?"):
            return
        for iid in sel:
            tid = self.tree.item(iid)['values'][0]
            database.delete_task(tid)
        self._render_month(self.current_year, self.current_month)
        self.refresh_task_list()

    def _show_task_details(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        tid = self.tree.item(sel[0])['values'][0]
        for t in database.get_all_tasks():
            if t[0] == tid:
                self._show_task_info_popup(t)
                break

    def _show_task_info_popup(self, task):
        status_display = {"pending":"В ожидании","in progress":"В процессе","completed":"Завершено","postponed":"Отложено"}
        priority_display = {"low":"Низкий","medium":"Средний","high":"Высокий"}
        txt = (f"Название: {task[1]}\nКатегория: {task[6] or ''}\n"
               f"Приоритет: {priority_display.get(task[5], task[5])}\n"
               f"Дедлайн: {task[4] or ''}\nСтатус: {status_display.get(task[7], task[7])}\n\nОписание:\n{task[2] or 'Нет описания'}")
        messagebox.showinfo("Задача", txt)

    # ====== Создание задачи ======
    def open_create_task_window(self):
        win = tk.Toplevel(self.root)
        win.title("Создать задачу")
        win.geometry("480x560")
        win.configure(bg=self.panel_bg)
        win.transient(self.root)
        win.grab_set()

        tk.Label(win, text="Название:*", bg=self.panel_bg, fg=self.fg).pack(anchor="w", padx=12, pady=(12,4))
        title_entry = tk.Entry(win)
        title_entry.pack(fill="x", padx=12)

        tk.Label(win, text="Описание:", bg=self.panel_bg, fg=self.fg).pack(anchor="w", padx=12, pady=(12,4))
        desc_entry = scrolledtext.ScrolledText(win, height=8)
        desc_entry.pack(fill="both", padx=12)

        tk.Label(win, text="Категория:", bg=self.panel_bg, fg=self.fg).pack(anchor="w", padx=12, pady=(12,4))
        cat_frame = tk.Frame(win, bg=self.panel_bg)
        cat_frame.pack(fill="x", padx=12)
        cat_combo = ttk.Combobox(cat_frame, values=self.settings.get("categories", []), width=24)
        cat_combo.pack(side="left", padx=(0,6))
        new_cat_entry = tk.Entry(cat_frame)
        new_cat_entry.pack(side="left", fill="x", expand=True)
        tk.Button(cat_frame, text="➕ Добавить категорию",
                  command=lambda: self._add_category_from_entry(new_cat_entry, cat_combo)).pack(side="left", padx=6)

        tk.Label(win, text="Приоритет:", bg=self.panel_bg, fg=self.fg).pack(anchor="w", padx=12, pady=(12,4))
        pr_combo = ttk.Combobox(win, values=["Низкий","Средний","Высокий"])
        pr_combo.set("Средний")
        pr_combo.pack(fill="x", padx=12)

        tk.Label(win, text="Дедлайн:", bg=self.panel_bg, fg=self.fg).pack(anchor="w", padx=12, pady=(12,4))
        cal = Calendar(win, selectmode='day', date_pattern='yyyy-mm-dd')
        cal.pack(padx=12, pady=6)

        btns = tk.Frame(win, bg=self.panel_bg)
        btns.pack(fill="x", padx=12, pady=12)
        tk.Button(btns, text="Создать", bg=self.accent, fg="white",
                  command=lambda: self._create_task_action(win, title_entry, desc_entry, cat_combo, new_cat_entry, pr_combo, cal)).pack(side="left")
        tk.Button(btns, text="Отмена", command=win.destroy).pack(side="right")

    def _add_category_from_entry(self, entry, combo):
        name = entry.get().strip()
        if not name:
            messagebox.showwarning("Категория", "Введите название категории.")
            return
        app_settings.add_category(name)
        self.settings = app_settings.load_settings()
        combo['values'] = self.settings['categories']
        entry.delete(0, tk.END)
        self._refresh_categories_listbox()
        messagebox.showinfo("Категория", f"Категория «{name}» добавлена.")

    def _create_task_action(self, win, title_entry, desc_entry, cat_combo, new_cat_entry, pr_combo, cal):
        title = title_entry.get().strip()
        if not title:
            messagebox.showerror("Ошибка", "Введите название задачи!")
            return
        new_cat = new_cat_entry.get().strip()
        category = new_cat if new_cat else cat_combo.get().strip()
        priority_map = {"Низкий":"low","Средний":"medium","Высокий":"high"}
        priority = priority_map.get(pr_combo.get().strip(), "medium")
        deadline = cal.get_date()

        task_data = {
            'title': title,
            'description': desc_entry.get("1.0", tk.END).strip(),
            'deadline': deadline,
            'priority': priority,
            'category': category,
            'status': 'pending',
            'tags': '',
            'recurrence': None,
            'reminder': None
        }
        database.add_task(task_data)
        win.destroy()
        self._render_month(self.current_year, self.current_month)
        self.refresh_task_list()

    # ====== Настройки/категории ======
    def open_settings_window(self):
        win = tk.Toplevel(self.root)
        win.title("Настройки")
        win.geometry("420x380")
        win.configure(bg=self.panel_bg)

        tk.Label(win, text="Пароль на приложение:", bg=self.panel_bg, fg=self.fg).pack(anchor="w", padx=10, pady=(10,4))
        pwd_entry = tk.Entry(win, show="*")
        pwd_entry.insert(0, self.settings.get("app_password", ""))
        pwd_entry.pack(fill="x", padx=10)

        tk.Label(win, text="Тема:", bg=self.panel_bg, fg=self.fg).pack(anchor="w", padx=10, pady=(10,4))
        theme_var = tk.StringVar(value=self.settings.get("theme", "light"))
        ttk.Radiobutton(win, text="Светлая", variable=theme_var, value="light").pack(anchor="w", padx=10)
        ttk.Radiobutton(win, text="Тёмная", variable=theme_var, value="dark").pack(anchor="w", padx=10)

        autostart_var = tk.BooleanVar(value=self.settings.get("autostart_enabled", False))
        ttk.Checkbutton(win, text="Запускать при старте Windows", variable=autostart_var).pack(anchor="w", padx=10, pady=(10,4))

        tk.Label(win, text="Категории:", bg=self.panel_bg, fg=self.fg).pack(anchor="w", padx=10, pady=(10,4))
        cats_frame = tk.Frame(win, bg=self.panel_bg)
        cats_frame.pack(fill="x", padx=10)
        cats_list = tk.Listbox(cats_frame, height=6)
        for c in self.settings['categories']:
            cats_list.insert("end", c)
        cats_list.pack(side="left", fill="both", expand=True)
        ctrl = tk.Frame(cats_frame, bg=self.panel_bg)
        ctrl.pack(side="right", fill="y")
        cat_new = tk.Entry(ctrl)
        cat_new.pack(pady=4)
        tk.Button(ctrl, text="➕", command=lambda: self._add_category_from_settings(cat_new, cats_list)).pack(pady=2)
        tk.Button(ctrl, text="➖", command=lambda: self._remove_category_from_settings(cats_list)).pack(pady=2)

        def save_settings_action():
            app_settings.set_password(pwd_entry.get())
            app_settings.set_theme(theme_var.get())
            app_settings.set_autostart(autostart_var.get())
            self.settings = app_settings.load_settings()
            self._apply_theme(self.settings['theme'])
            if autostart_var.get():
                self._enable_autostart()
            else:
                self._disable_autostart()
            self._refresh_categories_listbox()
            messagebox.showinfo("Настройки", "Сохранено.")

        tk.Button(win, text="Сохранить", command=save_settings_action, bg=self.accent, fg="white").pack(pady=12)

    def _add_category_from_settings(self, entry, listbox):
        name = entry.get().strip()
        if not name:
            return
        app_settings.add_category(name)
        self.settings = app_settings.load_settings()
        listbox.delete(0, "end")
        for c in self.settings['categories']:
            listbox.insert("end", c)
        entry.delete(0, tk.END)

    def _remove_category_from_settings(self, listbox):
        sel = listbox.curselection()
        if not sel:
            return
        name = listbox.get(sel[0])
        app_settings.remove_category(name)
        self.settings = app_settings.load_settings()
        listbox.delete(sel[0])

    def _refresh_categories_listbox(self):
        if hasattr(self, "cal_list"):
            self.cal_list.delete(0, "end")
            for c in self.settings.get("categories", []):
                self.cal_list.insert("end", c)

    # ====== Пароль и автозапуск ======
    def _prompt_password(self):
        pwd = simpledialog.askstring("Пароль", "Введите пароль для входа:", show="*")
        return pwd == self.settings.get("app_password")

    def _ask_autostart_once(self):
        if messagebox.askyesno("Автозапуск", "Включить запуск приложения при старте ПК?"):
            self._enable_autostart()
            self.settings['autostart_enabled'] = True
            app_settings.set_autostart(True)

    def _enable_autostart(self):
        try:
            startup_dir = os.path.join(os.environ.get('APPDATA'), r"Microsoft\Windows\Start Menu\Programs\Startup")
            exe_path = sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(sys.argv[0])
            link_path = os.path.join(startup_dir, "TaskPlanner_start.bat")
            with open(link_path, "w", encoding="utf-8") as f:
                f.write(f'@echo off\nstart "" "{exe_path}"\n')
        except Exception as e:
            messagebox.showerror("Автозапуск", f"Не удалось настроить автозапуск: {e}")

    def _disable_autostart(self):
        try:
            startup_dir = os.path.join(os.environ.get('APPDATA'), r"Microsoft\Windows\Start Menu\Programs\Startup")
            link_path = os.path.join(startup_dir, "TaskPlanner_start.bat")
            if os.path.exists(link_path):
                os.remove(link_path)
        except Exception:
            pass

    # ====== Справка ======
    def show_about(self):
        messagebox.showinfo("О приложении", "TaskPlanner\nМесячный календарь + Список задач\nTkinter + SQLite + tkcalendar")
