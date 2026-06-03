from __future__ import annotations

import json
import os
import re
import sys
import tkinter as tk
import webbrowser
from datetime import date
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, Dict, List

from generate_gpt_input import generate_gpt_input, gpt_input_path, gpt_output_path
from import_gpt_minutes import import_gpt_minutes
from meeting_workflow_state import (
    WorkflowState,
    next_meeting_id,
    parse_frontmatter,
    repo_root_from,
    source_meeting_date,
    validate_meeting_id,
)
from register_source import register_source
from render_meeting_repo import render_repo, validate_repo
from update_dashboards import update_dashboards


TXT = {
    "title": "09_Meeting \uc218\ub3d9 GPT \ud68c\uc758 \uc6cc\ud06c\ud50c\ub85c",
    "meeting_id": "\ud68c\uc758 ID",
    "title_label": "\uc81c\ubaa9",
    "date": "\uc77c\uc790",
    "source_file": "\uc6d0\ubcf8 \ud30c\uc77c",
    "gpt_input_file": "GPT 입력 파일",
    "gpt_output_file": "GPT \uacb0\uacfc \ud30c\uc77c",
    "copy_raw": "\uba85\uc2dc\uc801\uc73c\ub85c \ud655\uc778\ud55c \ub4a4 \uc6d0\ubcf8 \ud30c\uc77c\uc744 20_Sources/00_Originals\ub85c \ubcf5\uc0ac",
    "preview_register": "\ub4f1\ub85d \ubbf8\ub9ac\ubcf4\uae30",
    "apply_register": "\ub4f1\ub85d \uc801\uc6a9",
    "new_meeting": "새 회의 만들기",
    "register_source": "원본/STT 등록",
    "generate_gpt_input": "GPT 입력 파일 생성",
    "open_gpt_input": "GPT 입력 파일 열기",
    "select_gpt_output": "GPT 결과 파일 선택",
    "preview_import": "\uac00\uc838\uc624\uae30 \ubbf8\ub9ac\ubcf4\uae30",
    "apply_import": "\uac00\uc838\uc624\uae30 \uc801\uc6a9",
    "open_review": "Review 열기",
    "refresh_dashboard": "Dashboard 갱신",
    "run_validation": "Validation 실행",
    "validate": "\uac80\uc99d",
    "render_dashboards": "\ub80c\ub354+\ub300\uc2dc\ubcf4\ub4dc \uc801\uc6a9",
    "new_id": "\uc0c8 ID \uc0dd\uc131",
    "refresh": "\ubaa9\ub85d \uc0c8\ub85c\uace0\uce68",
    "browse": "\ucc3e\uae30",
    "select_source": "\uc6d0\ubcf8 \ud30c\uc77c \uc120\ud0dd",
    "select_gpt": "\ubd99\uc5ec\ub123\uc740 GPT \uacb0\uacfc \uc120\ud0dd",
    "source_required": "\uc6d0\ubcf8/STT \ud30c\uc77c\uc744 \uc120\ud0dd\ud558\uc138\uc694.",
    "gpt_input_required": "GPT 입력 파일을 먼저 생성하세요.",
    "gpt_required": "GPT \uacb0\uacfc \ud30c\uc77c\uc744 \uc120\ud0dd\ud558\uc138\uc694. STT/\uc6d0\ubcf8 \ud30c\uc77c\uc740 '\ub4f1\ub85d \uc801\uc6a9'\uc5d0\uc11c \uc0ac\uc6a9\ud558\uace0, '\uac00\uc838\uc624\uae30 \uc801\uc6a9'\uc740 ChatGPT \uacb0\uacfc JSON/Markdown \ud30c\uc77c\uc744 \uc0ac\uc6a9\ud569\ub2c8\ub2e4.",
    "file_missing": "\ud30c\uc77c\uc774 \uc5c6\uc2b5\ub2c8\ub2e4: ",
    "file_is_dir": "\ud30c\uc77c\uc774 \uc544\ub2c8\ub77c \ud3f4\ub354\uac00 \uc120\ud0dd\ub418\uc5c8\uc2b5\ub2c8\ub2e4: ",
    "open_failed": "파일 열기 실패",
    "refresh_done": "\uae30\uc874 \ud68c\uc758 ID \ubaa9\ub85d\uc744 \uc0c8\ub85c\uace0\uce68\ud588\uc2b5\ub2c8\ub2e4.",
    "proposed_id": "\uc0c8 \ud68c\uc758 ID\ub97c \uc81c\uc548\ud588\uc2b5\ub2c8\ub2e4: ",
    "id_failed": "\ud68c\uc758 ID \uc0dd\uc131 \uc2e4\ud328",
    "confirm_raw_title": "\uc6d0\ubcf8 \ubcf5\uc0ac \ud655\uc778",
    "confirm_raw_body": "\uc120\ud0dd\ud55c \uc6d0\ubcf8 \ud30c\uc77c\uc744 20_Sources/00_Originals\ub85c \uc9c0\uae08 \ubcf5\uc0ac\ud560\uae4c\uc694?",
    "raw_cancelled": "\uc6d0\ubcf8 \ubcf5\uc0ac\uac00 \ud655\uc778\ub418\uc9c0 \uc54a\uc544 \ub4f1\ub85d\uc744 \ucde8\uc18c\ud588\uc2b5\ub2c8\ub2e4.",
    "confirm_register_title": "\ub4f1\ub85d \uc801\uc6a9",
    "confirm_register_body": "\uc18c\uc2a4 \ub178\ud2b8\uc640 \uba54\uc778 \ud68c\uc758 \ub178\ud2b8\ub97c \uc0dd\uc131\ud558\uac70\ub098 \uc5c5\ub370\uc774\ud2b8\ud560\uae4c\uc694?",
    "source_id_mismatch_title": "\uc6d0\ubcf8 \uacbd\ub85c ID \ud655\uc778",
    "source_id_mismatch_body": "\uc120\ud0dd\ud55c \uc6d0\ubcf8/STT \uacbd\ub85c\uc5d0 \ub2e4\ub978 \ud68c\uc758 ID\uac00 \ubcf4\uc785\ub2c8\ub2e4.\n\n\ud604\uc7ac \ud68c\uc758 ID: {current}\n\uc6d0\ubcf8 \uacbd\ub85c ID: {source}\n\n\ud68c\uc758 ID\uac00 \uc77c\uce58\ud558\ub294 \ud30c\uc77c\uc744 \uc120\ud0dd\ud558\uc138\uc694.",
    "register_failed": "\ub4f1\ub85d \uc2e4\ud328",
    "confirm_import_title": "\uac00\uc838\uc624\uae30 \uc801\uc6a9",
    "confirm_import_body": "\ubd99\uc5ec\ub123\uc740 GPT \uacb0\uacfc\ub85c \uc0dd\uc131 \uc601\uc5ed\uc744 \uc5c5\ub370\uc774\ud2b8\ud560\uae4c\uc694?",
    "import_failed": "\uac00\uc838\uc624\uae30 \uc2e4\ud328",
    "validation_failed": "\uac80\uc99d \uc2e4\ud328",
    "validation_passed": "\uac80\uc99d \ud1b5\uacfc",
    "confirm_render_title": "\ub80c\ub354 \uc801\uc6a9",
    "confirm_render_body": "\uc0dd\uc131 \ub178\ud2b8\uc640 \ub300\uc2dc\ubcf4\ub4dc\ub97c \ub2e4\uc2dc \ub80c\ub354\ub9c1\ud560\uae4c\uc694?",
    "apply": "\uc801\uc6a9",
    "preview": "\ubbf8\ub9ac\ubcf4\uae30",
}


def discover_meetings(root: Path) -> List[Dict[str, Any]]:
    root = root.resolve()
    found: Dict[str, Dict[str, Any]] = {}

    def add(meeting_id: str, title: Any = "", meeting_date: Any = "", source: Any = "", mtime: float = 0.0) -> None:
        meeting_id = str(meeting_id or "").strip()
        if not meeting_id:
            return
        item = found.setdefault(
            meeting_id,
            {"meeting_id": meeting_id, "title": "", "meeting_date": "", "source": "", "mtime": 0.0},
        )
        if title and not item["title"]:
            item["title"] = str(title)
        if meeting_date and not item["meeting_date"]:
            item["meeting_date"] = str(meeting_date)
        if source and not item["source"]:
            item["source"] = str(source)
        item["mtime"] = max(float(item["mtime"]), float(mtime or 0.0))

    meetings_dir = root / "25_Meetings"
    if meetings_dir.exists():
        for meeting_dir in sorted(path for path in meetings_dir.iterdir() if path.is_dir()):
            meeting_id = meeting_dir.name
            main_note = meeting_dir / f"{meeting_id}.md"
            if main_note.exists():
                frontmatter = parse_frontmatter(main_note.read_text(encoding="utf-8"))
                add(
                    frontmatter.get("meeting_id") or meeting_id,
                    title=frontmatter.get("title"),
                    meeting_date=frontmatter.get("meeting_date"),
                    source=frontmatter.get("source_note"),
                    mtime=main_note.stat().st_mtime,
                )
            data_path = meeting_dir / "_data" / "gpt_minutes.json"
            if data_path.exists():
                try:
                    data = json.loads(data_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    data = {}
                add(
                    data.get("meeting_id") or meeting_id,
                    title=data.get("title"),
                    meeting_date=data.get("meeting_date"),
                    mtime=data_path.stat().st_mtime,
                )

    source_dir = root / "20_Sources"
    if source_dir.exists():
        for source_note in sorted(source_dir.glob("*.md")):
            frontmatter = parse_frontmatter(source_note.read_text(encoding="utf-8"))
            if frontmatter.get("type") != "source":
                continue
            add(
                frontmatter.get("meeting_id"),
                title=frontmatter.get("title"),
                meeting_date=frontmatter.get("meeting_date"),
                source=source_note.as_posix(),
                mtime=source_note.stat().st_mtime,
            )

    return sorted(found.values(), key=lambda item: (-float(item["mtime"]), str(item["meeting_id"])))


def canonical_meeting_options(meetings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [item for item in meetings if validate_meeting_id(str(item["meeting_id"]))]


def suggest_meeting_id(meetings: List[Dict[str, Any]]) -> str:
    canonical = canonical_meeting_options(meetings)
    return str(canonical[0]["meeting_id"]) if canonical else ""


def choose_initial_meeting_id(saved_id: str, meetings: List[Dict[str, Any]]) -> str:
    saved_id = saved_id.strip()
    if validate_meeting_id(saved_id):
        return saved_id
    return suggest_meeting_id(meetings)


def korean_action_text(action: Any) -> str:
    text = str(action)
    replacements = (
        ("would copy raw source to ", "\uc6d0\ubcf8 \ubcf5\uc0ac \uc608\uc815: "),
        ("copied raw source to ", "\uc6d0\ubcf8 \ubcf5\uc0ac \uc644\ub8cc: "),
        ("would register meeting ID ", "\ud68c\uc758 ID \ub4f1\ub85d \uc608\uc815: "),
        ("registered meeting ID ", "\ud68c\uc758 ID \ub4f1\ub85d \uc644\ub8cc: "),
        ("unchanged meeting ID registry ", "\ud68c\uc758 ID \ub4f1\ub85d \uc720\uc9c0: "),
        ("would create ", "\uc0dd\uc131 \uc608\uc815: "),
        ("would update ", "\uc5c5\ub370\uc774\ud2b8 \uc608\uc815: "),
        ("wrote ", "\uc791\uc131 \uc644\ub8cc: "),
        ("unchanged existing GPT output file ", "기존 GPT 결과 파일 유지: "),
        ("unchanged existing source note ", "\uae30\uc874 \uc18c\uc2a4 \ub178\ud2b8 \uc720\uc9c0: "),
        ("unchanged existing main note ", "\uae30\uc874 \uba54\uc778 \ud68c\uc758 \ub178\ud2b8 \uc720\uc9c0: "),
        ("unchanged ", "\ubcc0\uacbd \uc5c6\uc74c: "),
    )
    for old, new in replacements:
        if text.startswith(old):
            return new + text[len(old):]
    return text


def selected_existing_file(path_text: str, empty_message: str) -> Path:
    text = str(path_text or "").strip()
    if not text:
        raise ValueError(empty_message)
    path = Path(text).expanduser()
    if not path.exists():
        raise FileNotFoundError(TXT["file_missing"] + str(path))
    if not path.is_file():
        raise ValueError(TXT["file_is_dir"] + str(path))
    return path


def meeting_id_in_path(path_text: str) -> str:
    match = re.search(r"MTG-\d{8}-\d{3}", str(path_text or ""))
    return match.group(0) if match else ""


class MeetingWorkflowApp(tk.Tk):
    def __init__(self, root_path: Path) -> None:
        super().__init__()
        self.root_path = root_path.resolve()
        self.state_model = WorkflowState.load(self.root_path)
        self.meeting_options = discover_meetings(self.root_path)
        self.title(TXT["title"])
        self.geometry("920x680")
        self._build()
        self._load_state_to_form()

    def _build(self) -> None:
        self.columnconfigure(1, weight=1)
        row = 0
        self.meeting_id = self._meeting_id_entry(row, TXT["meeting_id"])
        row += 1
        self.meeting_title = self._entry(row, TXT["title_label"])
        row += 1
        self.meeting_date = self._entry(row, TXT["date"])
        row += 1
        self.source_file = self._file_entry(row, TXT["source_file"], self._browse_source)
        row += 1
        self.gpt_input_file = self._file_entry(row, TXT["gpt_input_file"], None)
        row += 1
        self.gpt_output_file = self._file_entry(row, TXT["gpt_output_file"], None)
        row += 1
        self.copy_raw = tk.BooleanVar(value=False)
        ttk.Checkbutton(self, text=TXT["copy_raw"], variable=self.copy_raw).grid(
            row=row, column=0, columnspan=3, sticky="w", padx=12, pady=6
        )
        row += 1

        buttons = ttk.Frame(self)
        buttons.grid(row=row, column=0, columnspan=3, sticky="ew", padx=12, pady=8)
        for index in range(5):
            buttons.columnconfigure(index, weight=1)
        flow_buttons = [
            (TXT["new_meeting"], self._generate_new_meeting_id),
            (TXT["register_source"], lambda: self._register_source(True)),
            (TXT["generate_gpt_input"], self._generate_gpt_input),
            (TXT["open_gpt_input"], self._open_gpt_input),
            (TXT["select_gpt_output"], self._browse_gpt),
            (TXT["preview_import"], lambda: self._import(False)),
            (TXT["apply_import"], lambda: self._import(True)),
            (TXT["open_review"], self._open_review),
            (TXT["refresh_dashboard"], self._render_apply),
            (TXT["run_validation"], self._validate),
        ]
        for index, (label, command) in enumerate(flow_buttons):
            ttk.Button(buttons, text=label, command=command).grid(
                row=index // 5, column=index % 5, padx=4, pady=3, sticky="ew"
            )
        row += 1

        self.log = tk.Text(self, height=24, wrap="word")
        self.log.grid(row=row, column=0, columnspan=3, sticky="nsew", padx=12, pady=8)
        self.rowconfigure(row, weight=1)

    def _entry(self, row: int, label: str) -> tk.StringVar:
        var = tk.StringVar()
        ttk.Label(self, text=label).grid(row=row, column=0, sticky="w", padx=12, pady=4)
        ttk.Entry(self, textvariable=var).grid(row=row, column=1, columnspan=2, sticky="ew", padx=12, pady=4)
        return var

    def _meeting_id_entry(self, row: int, label: str) -> tk.StringVar:
        var = tk.StringVar()
        ttk.Label(self, text=label).grid(row=row, column=0, sticky="w", padx=12, pady=4)
        self.meeting_id_combo = ttk.Combobox(
            self,
            textvariable=var,
            values=[item["meeting_id"] for item in canonical_meeting_options(self.meeting_options)],
            state="normal",
        )
        self.meeting_id_combo.grid(row=row, column=1, sticky="ew", padx=12, pady=4)
        self.meeting_id_combo.bind("<<ComboboxSelected>>", lambda _event: self._autofill_from_meeting_id(force=True))
        id_buttons = ttk.Frame(self)
        id_buttons.grid(row=row, column=2, sticky="ew", padx=12, pady=4)
        id_buttons.columnconfigure(0, weight=1)
        ttk.Button(id_buttons, text=TXT["refresh"], command=self._refresh_meeting_options).grid(row=0, column=0, sticky="ew")
        return var

    def _file_entry(self, row: int, label: str, browse_command) -> tk.StringVar:
        var = tk.StringVar()
        ttk.Label(self, text=label).grid(row=row, column=0, sticky="w", padx=12, pady=4)
        columnspan = 1 if browse_command else 2
        ttk.Entry(self, textvariable=var).grid(row=row, column=1, columnspan=columnspan, sticky="ew", padx=12, pady=4)
        if browse_command:
            ttk.Button(self, text=TXT["browse"], command=browse_command).grid(row=row, column=2, sticky="ew", padx=12, pady=4)
        return var

    def _load_state_to_form(self) -> None:
        self.meeting_title.set(self.state_model.title)
        self.source_file.set(self.state_model.source_file)
        source_date = source_meeting_date(self.state_model.source_file)
        self.meeting_date.set(self.state_model.meeting_date or source_date or date.today().isoformat())
        initial_id = choose_initial_meeting_id(self.state_model.meeting_id, self.meeting_options)
        self.meeting_id.set(initial_id or next_meeting_id(self.root_path, self.meeting_date.get()))
        self.gpt_input_file.set(self.state_model.gpt_input_file)
        self.gpt_output_file.set(self.state_model.gpt_output_file)
        self.copy_raw.set(self.state_model.copy_raw)
        self._autofill_from_meeting_id(force=False)

    def _save_form_state(self) -> None:
        self.state_model.meeting_id = self.meeting_id.get().strip()
        self.state_model.title = self.meeting_title.get().strip()
        self.state_model.meeting_date = self.meeting_date.get().strip()
        self.state_model.source_file = self.source_file.get().strip()
        self.state_model.gpt_input_file = self.gpt_input_file.get().strip()
        self.state_model.gpt_output_file = self.gpt_output_file.get().strip()
        self.state_model.copy_raw = self.copy_raw.get()
        self.state_model.save(self.root_path)

    def _browse_source(self) -> None:
        value = filedialog.askopenfilename(title=TXT["select_source"])
        if value:
            self.source_file.set(value)
            self._apply_source_date_to_new_meeting()

    def _browse_gpt(self) -> None:
        value = filedialog.askopenfilename(title=TXT["select_gpt"])
        if value:
            self.gpt_output_file.set(value)

    def _optional_source_file(self) -> Path | None:
        if not self.source_file.get().strip():
            return None
        return selected_existing_file(self.source_file.get(), TXT["source_required"])

    def _refresh_meeting_options(self) -> None:
        self.meeting_options = discover_meetings(self.root_path)
        self.meeting_id_combo["values"] = [item["meeting_id"] for item in canonical_meeting_options(self.meeting_options)]
        if not self.meeting_id.get().strip():
            self._generate_new_meeting_id()
        self._autofill_from_meeting_id(force=False)
        self._write_log(TXT["refresh_done"])

    def _generate_new_meeting_id(self) -> None:
        try:
            source_date = source_meeting_date(self.source_file.get())
            meeting_date = source_date or self.meeting_date.get().strip()
            if source_date:
                self.meeting_date.set(source_date)
            self.meeting_id.set(next_meeting_id(self.root_path, meeting_date))
            self._write_log(TXT["proposed_id"] + self.meeting_id.get())
        except Exception as exc:
            messagebox.showerror(TXT["id_failed"], str(exc))

    def _apply_source_date_to_new_meeting(self, log: bool = True) -> None:
        source_date = source_meeting_date(self.source_file.get())
        if not source_date:
            return
        current_id = self.meeting_id.get().strip()
        if any(item["meeting_id"] == current_id for item in canonical_meeting_options(self.meeting_options)):
            return
        self.meeting_date.set(source_date)
        self.meeting_id.set(next_meeting_id(self.root_path, source_date))
        if log:
            self._write_log(TXT["proposed_id"] + self.meeting_id.get())

    def _autofill_from_meeting_id(self, force: bool = False) -> None:
        meeting_id = self.meeting_id.get().strip()
        option = next((item for item in self.meeting_options if item["meeting_id"] == meeting_id), None)
        if not option:
            return
        if option.get("title") and (force or not self.meeting_title.get().strip()):
            self.meeting_title.set(str(option["title"]))
        if option.get("meeting_date") and (force or not self.meeting_date.get().strip()):
            self.meeting_date.set(str(option["meeting_date"]))

    def _register_source(self, apply: bool) -> None:
        try:
            self._apply_source_date_to_new_meeting(log=False)
            self._save_form_state()
            confirmed_copy = False
            if apply:
                source_hint = meeting_id_in_path(self.source_file.get())
                current_id = self.meeting_id.get().strip()
                if source_hint and source_hint != current_id:
                    body = TXT["source_id_mismatch_body"].format(current=current_id, source=source_hint)
                    messagebox.showerror(TXT["source_id_mismatch_title"], body)
                    return
                if self.copy_raw.get():
                    selected_existing_file(self.source_file.get(), TXT["source_required"])
                    confirmed_copy = messagebox.askyesno(TXT["confirm_raw_title"], TXT["confirm_raw_body"])
                    if not confirmed_copy:
                        self._write_log(TXT["raw_cancelled"])
                        return
                elif not messagebox.askyesno(TXT["confirm_register_title"], TXT["confirm_register_body"]):
                    return
            actions = register_source(
                root=self.root_path,
                meeting_id=self.meeting_id.get().strip(),
                title=self.meeting_title.get().strip(),
                meeting_date=self.meeting_date.get().strip(),
                source_file=selected_existing_file(self.source_file.get(), TXT["source_required"]) if self.source_file.get().strip() else None,
                copy_raw=self.copy_raw.get(),
                confirm_copy=confirmed_copy,
                apply=apply,
            )
            self._write_actions(TXT["apply"] if apply else TXT["preview"], actions)
        except Exception as exc:
            messagebox.showerror(TXT["register_failed"], str(exc))

    def _import(self, apply: bool) -> None:
        self._save_form_state()
        try:
            if apply and not messagebox.askyesno(TXT["confirm_import_title"], TXT["confirm_import_body"]):
                return
            actions = import_gpt_minutes(
                root=self.root_path,
                meeting_id=self.meeting_id.get().strip(),
                gpt_output=selected_existing_file(self.gpt_output_file.get(), TXT["gpt_required"]),
                apply=apply,
            )
            self._write_actions(TXT["apply"] if apply else TXT["preview"], actions)
        except Exception as exc:
            messagebox.showerror(TXT["import_failed"], str(exc))

    def _generate_gpt_input(self) -> None:
        self._save_form_state()
        try:
            actions = generate_gpt_input(
                root=self.root_path,
                meeting_id=self.meeting_id.get().strip(),
                title=self.meeting_title.get().strip(),
                meeting_date=self.meeting_date.get().strip(),
                source_file=self._optional_source_file(),
                apply=True,
            )
            input_path = gpt_input_path(self.root_path, self.meeting_id.get().strip())
            output_path = gpt_output_path(self.root_path, self.meeting_id.get().strip())
            self.gpt_input_file.set(str(input_path))
            self.gpt_output_file.set(str(output_path))
            self._save_form_state()
            self._write_actions(TXT["apply"], actions)
        except Exception as exc:
            messagebox.showerror(TXT["import_failed"], str(exc))

    def _open_gpt_input(self) -> None:
        path_text = self.gpt_input_file.get().strip()
        if not path_text and self.meeting_id.get().strip():
            path_text = str(gpt_input_path(self.root_path, self.meeting_id.get().strip()))
        try:
            self._open_existing_file(selected_existing_file(path_text, TXT["gpt_input_required"]))
        except Exception as exc:
            messagebox.showerror(TXT["open_failed"], str(exc))

    def _open_review(self) -> None:
        review_path = self.root_path / "00_Dashboard" / "Action_Queue.md"
        if not review_path.exists() and self.meeting_id.get().strip():
            meeting_id = self.meeting_id.get().strip()
            review_path = self.root_path / "25_Meetings" / meeting_id / f"{meeting_id}.md"
        try:
            self._open_existing_file(selected_existing_file(str(review_path), TXT["file_missing"] + str(review_path)))
        except Exception as exc:
            messagebox.showerror(TXT["open_failed"], str(exc))

    def _open_existing_file(self, path: Path) -> None:
        if hasattr(os, "startfile"):
            os.startfile(str(path))
        else:
            webbrowser.open(path.resolve().as_uri())

    def _validate(self) -> None:
        errors = validate_repo(self.root_path)
        if errors:
            self._write_actions(TXT["validation_failed"], errors)
        else:
            self._write_log(TXT["validation_passed"])

    def _render_apply(self) -> None:
        if not messagebox.askyesno(TXT["confirm_render_title"], TXT["confirm_render_body"]):
            return
        actions = render_repo(self.root_path, apply=True)
        actions.extend(update_dashboards(self.root_path, apply=True))
        self._write_actions(TXT["apply"], actions)

    def _write_actions(self, heading: str, actions) -> None:
        self._write_log(heading)
        for action in actions:
            self._write_log(f"- {korean_action_text(action)}")

    def _write_log(self, text: str) -> None:
        self.log.insert("end", text + "\n")
        self.log.see("end")


def main() -> int:
    root = repo_root_from()
    app = MeetingWorkflowApp(root)
    if "--check" in sys.argv:
        print(app.title())
        app.destroy()
        return 0
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
