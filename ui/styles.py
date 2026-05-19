APP_STYLESHEET = """
QMainWindow#appWindow {
    background: #091013;
}
QWidget {
    color: #EAF1F4;
    font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
    font-size: 13px;
}
QWidget#appShell {
    background: #091013;
}
QDialog, QInputDialog {
    background: #10191B;
    color: #EAF1F4;
}
QDialog QLabel, QInputDialog QLabel {
    color: #EAF1F4;
    background: transparent;
}
QDialog QCheckBox, QInputDialog QCheckBox {
    color: #EAF1F4;
    background: transparent;
}
QDialogButtonBox {
    background: transparent;
}
QFrame#sidebar {
    background: #0D171A;
    border-right: 1px solid #1E3438;
}
QWidget#contentShell {
    background: #10191B;
}
QFrame#topBar, QFrame#panelCard, QGroupBox,
QFrame#panel, QWidget#panel, QWidget#missionSetting {
    background: #162225;
    border: 1px solid #263D42;
    border-radius: 8px;
}
QFrame#topBar {
    background: #142023;
}
QTabWidget#contentStack::pane {
    border: 0;
    background: transparent;
}
QGroupBox {
    margin-top: 12px;
    padding: 16px;
    font-weight: 700;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 8px;
    color: #F5D38A;
}
QWidget[role="taskRow"] {
    background: #101A1D;
    border: 1px solid #274045;
    border-radius: 8px;
}
QScrollArea, QTextEdit, QPlainTextEdit, QLineEdit, QComboBox {
    background: #0A1214;
    color: #F1F6F8;
    border: 1px solid #2A444A;
    border-radius: 7px;
    padding: 8px;
    selection-background-color: #D9A441;
    selection-color: #101315;
}
QTextEdit {
    font-family: "Cascadia Mono", "Consolas", monospace;
    line-height: 1.35;
}
QComboBox {
    padding-right: 28px;
    min-height: 22px;
}
QComboBox::drop-down {
    border: 0;
    width: 26px;
}
QComboBox QAbstractItemView {
    background: #0A1214;
    color: #F1F6F8;
    border: 1px solid #2A444A;
    outline: 0;
    selection-background-color: #F2C75E;
    selection-color: #071012;
}
QComboBox QAbstractItemView::item {
    min-height: 28px;
    padding: 6px 10px;
}
QPushButton {
    background: #203337;
    color: #F5FAFB;
    border: 1px solid #335056;
    border-radius: 7px;
    padding: 9px 13px;
    min-height: 18px;
}
QPushButton:hover {
    background: #294147;
    border-color: #4B737B;
}
QPushButton:pressed {
    background: #17272B;
}
QPushButton:disabled {
    background: #121A1C;
    color: #657579;
    border-color: #203033;
}
QPushButton#primaryButton {
    background: #F2C75E;
    border: 1px solid #FFE08C;
    color: #071012;
    font-weight: 800;
}
QPushButton#primaryButton:hover {
    background: #FFD978;
}
QPushButton#primaryButton:disabled {
    background: #4E4225;
    border-color: #7B6837;
    color: #D9C899;
}
QPushButton#dangerButton {
    background: #7D2E3A;
    border-color: #B44C5C;
    color: #FFF6F7;
    font-weight: 700;
}
QPushButton#dangerButton:hover {
    background: #963849;
}
QPushButton[role="navButton"] {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 8px;
    color: #AABABE;
    text-align: left;
    padding: 12px 16px;
    min-height: 28px;
    font-weight: 700;
    font-size: 15px;
}
QPushButton[role="navButton"]:hover {
    background: #142326;
    border-color: #263F44;
    color: #EAF1F4;
}
QPushButton[role="navButton"]:checked {
    background: #D9A441;
    border-color: #F1C76D;
    color: #101315;
}
QPushButton[list-button="true"] {
    min-width: 34px;
    max-width: 34px;
    padding: 8px;
}
QCheckBox {
    spacing: 9px;
    color: #EFF6F7;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 5px;
    border: 1px solid #4D666B;
    background: #091113;
}
QCheckBox::indicator:checked {
    background: #D9A441;
    border-color: #F1C76D;
}
QLabel[role="brand"] {
    color: #FFFFFF;
    font-size: 22px;
    font-weight: 900;
}
QLabel[role="sidebarCaption"], QLabel[role="sidebarFooter"],
QLabel[role="muted"], QLabel[role="statLabel"] {
    color: #8FA3A8;
}
QLabel[role="sidebarFooter"] {
    line-height: 1.4;
}
QLabel[role="topTitle"] {
    color: #EAF1F4;
    font-size: 16px;
    font-weight: 800;
}
QLabel[role="title"] {
    color: #FFFFFF;
    font-size: 18px;
    font-weight: 800;
}
QLabel#statusBadge {
    background: #0E2A25;
    border: 1px solid #2C7B67;
    border-radius: 7px;
    color: #90E4C9;
    padding: 6px 10px;
    font-weight: 800;
}
QFormLayout QLabel {
    color: #BFD0D4;
}
QScrollBar:vertical {
    background: #0C1416;
    width: 11px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background: #3C5960;
    border-radius: 5px;
    min-height: 26px;
}
QScrollBar::handle:vertical:hover {
    background: #51737A;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    height: 0;
}
"""

LIST_BUTTON_STYLE = (
    "QPushButton {background-color: #203337; color: #F5FAFB; "
    "border: 1px solid #335056; border-radius: 7px; padding: 8px;}"
    "QPushButton:hover {background-color: #294147; border-color: #4B737B;}"
)

SELECTED_BUTTON_STYLE = (
    "QPushButton {background-color: #D9A441; color: #101315; "
    "border: 1px solid #F1C76D; border-radius: 7px; padding: 8px; font-weight: 800;}"
)
