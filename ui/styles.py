APP_STYLESHEET = """
QMainWindow, QWidget {
    background: #111418;
    color: #E7EAF0;
    font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
    font-size: 13px;
}
QTabWidget::pane {
    border: 1px solid #252B33;
    border-radius: 8px;
    background: #171B21;
}
QTabBar::tab {
    background: #171B21;
    color: #AAB2C0;
    padding: 10px 18px;
    border: 1px solid #252B33;
    border-bottom: none;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    margin-right: 4px;
}
QTabBar::tab:selected {
    background: #20262E;
    color: #FFFFFF;
}
QGroupBox, QFrame#panel, QWidget#panel, QWidget#missionSetting {
    background: #171B21;
    border: 1px solid #28303A;
    border-radius: 8px;
}
QGroupBox {
    margin-top: 10px;
    padding: 14px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #C9D1DD;
}
QScrollArea, QTextEdit, QPlainTextEdit, QLineEdit, QComboBox {
    background: #0D1014;
    color: #F0F3F7;
    border: 1px solid #2B3440;
    border-radius: 6px;
    padding: 7px;
    selection-background-color: #3F7B68;
}
QComboBox {
    padding-right: 24px;
}
QPushButton {
    background: #25313C;
    color: #F5F7FA;
    border: 1px solid #334252;
    border-radius: 6px;
    padding: 8px 12px;
}
QPushButton:hover {
    background: #2D3B48;
    border-color: #436071;
}
QPushButton:pressed {
    background: #1E2933;
}
QPushButton:disabled {
    background: #191D23;
    color: #65707D;
    border-color: #242A31;
}
QPushButton#primaryButton {
    background: #34785F;
    border-color: #45A17F;
    font-weight: 600;
}
QPushButton#primaryButton:hover {
    background: #3D8B70;
}
QPushButton#dangerButton {
    background: #76363A;
    border-color: #A34B51;
}
QPushButton#dangerButton:hover {
    background: #8A4045;
}
QPushButton[list-button="true"] {
    min-width: 32px;
    max-width: 32px;
    padding: 7px;
}
QCheckBox {
    spacing: 8px;
}
QCheckBox::indicator {
    width: 17px;
    height: 17px;
    border-radius: 4px;
    border: 1px solid #435060;
    background: #0D1014;
}
QCheckBox::indicator:checked {
    background: #3F8F72;
    border-color: #65C29D;
}
QLabel[role="title"] {
    color: #FFFFFF;
    font-size: 18px;
    font-weight: 700;
}
QLabel[role="muted"] {
    color: #93A0AF;
}
QScrollBar:vertical {
    background: #111418;
    width: 10px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background: #394653;
    border-radius: 5px;
    min-height: 24px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
"""

LIST_BUTTON_STYLE = "QPushButton {background-color: #26323D; border: 1px solid #334252; border-radius: 6px;}"
SELECTED_BUTTON_STYLE = "QPushButton {background-color: #3F7B68; border: 1px solid #67C59F; border-radius: 6px;}"
