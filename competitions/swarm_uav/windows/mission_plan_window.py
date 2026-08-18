"""Mission plan editor, loaded from designer/mission_plan_window.ui.

The window opened by UPLOAD MISSION: build the plan step by step, reorder or
drop steps, and save. It only edits the list — publishing is the controller's
job, and the main window decides when the saved plan goes out.
"""

import logging
from pathlib import Path

from PyQt6 import uic
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QListWidgetItem, QMessageBox

from config import WINDOW_TITLE
from competitions.swarm_uav.config import PLAN_MAX_STEPS, PLAN_TEXT
from competitions.swarm_uav.controller.mission_plan import PlanStep
from competitions.swarm_uav.widgets.mission_step_editor import MissionStepEditor
from theme import fade_in, flush_layout, space_layout
from theme.tokens import SPACE_LG, SPACE_XL

logger = logging.getLogger(__name__)

FORM_PATH = Path(__file__).resolve().parents[1] / "designer" / "mission_plan_window.ui"


class MissionPlanWindow(QDialog):
    """Edits one mission plan; the steps are only read after it is accepted."""

    def __init__(self, plan_steps: list[PlanStep], parent=None) -> None:
        """plan_steps is the plan currently held, shown for further editing."""
        super().__init__(parent)
        uic.loadUi(FORM_PATH, self)
        self.setWindowTitle(f"{WINDOW_TITLE} - {PLAN_TEXT['window_title']}")

        space_layout(self.planlayout, SPACE_XL, SPACE_LG)
        flush_layout(self.listbuttonlayout)
        flush_layout(self.dialogbuttonlayout)

        # Edited on a copy, so cancelling really keeps the previous plan.
        self.plan_steps = list(plan_steps)

        self.step_editor = MissionStepEditor(self)
        self.step_editor.step_requested.connect(self.add_step)
        self.editorlayout.addWidget(self.step_editor)

        self.upbtn.clicked.connect(lambda: self.move_selected_step(-1))
        self.downbtn.clicked.connect(lambda: self.move_selected_step(1))
        self.removebtn.clicked.connect(self.remove_selected_step)
        self.clearbtn.clicked.connect(self.clear_steps)
        self.cancelbtn.clicked.connect(self.reject)
        self.savebtn.clicked.connect(self.accept)

        self.refresh_list()

    # Editing

    def add_step(self, step: PlanStep) -> None:
        if len(self.plan_steps) >= PLAN_MAX_STEPS:
            QMessageBox.warning(
                self,
                "Plan full",
                f"A mission plan holds at most {PLAN_MAX_STEPS} steps.",
            )
            return
        self.plan_steps.append(step)
        self.refresh_list()
        self.planlist.setCurrentRow(len(self.plan_steps) - 1)

    def remove_selected_step(self) -> None:
        selected_row = self.planlist.currentRow()
        if selected_row < 0:
            return
        self.plan_steps.pop(selected_row)
        self.refresh_list()
        self.planlist.setCurrentRow(min(selected_row, len(self.plan_steps) - 1))

    def move_selected_step(self, offset: int) -> None:
        """Move the selected step one place up or down the plan."""
        selected_row = self.planlist.currentRow()
        target_row = selected_row + offset
        if selected_row < 0 or not 0 <= target_row < len(self.plan_steps):
            return
        self.plan_steps[selected_row], self.plan_steps[target_row] = (
            self.plan_steps[target_row], self.plan_steps[selected_row]
        )
        self.refresh_list()
        self.planlist.setCurrentRow(target_row)

    def clear_steps(self) -> None:
        self.plan_steps = []
        self.refresh_list()

    # Display

    def refresh_list(self) -> None:
        """Redraw the numbered plan; an empty plan shows why it is empty."""
        self.planlist.clear()
        if not self.plan_steps:
            empty_item = QListWidgetItem(PLAN_TEXT["empty_plan"])
            empty_item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.planlist.addItem(empty_item)
        else:
            for step_number, step in enumerate(self.plan_steps, start=1):
                self.planlist.addItem(f"{step_number:>2}. {step.description()}")

        has_steps = bool(self.plan_steps)
        for list_button in (self.upbtn, self.downbtn, self.removebtn, self.clearbtn):
            list_button.setEnabled(has_steps)
        self.savebtn.setEnabled(has_steps)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        fade_in(self)
