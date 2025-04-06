import json
import os

from PyQt5.QtCore import Qt, QRectF, pyqtSignal, QRegExp
from PyQt5.QtGui import (
    QColor, QBrush, QPen, QFont, QLinearGradient, 
    QPixmap, QPainterPath, QRegExpValidator, QIntValidator
)
from PyQt5.QtWidgets import (
    QGraphicsScene, QGraphicsTextItem, QGraphicsRectItem, QGraphicsItemGroup, 
    QGraphicsPixmapItem, QGraphicsItem, QGraphicsEllipseItem, QLineEdit, 
    QGraphicsProxyWidget, QPushButton
)

import resources_rc
import config

class SwitchButton(QGraphicsItem):
    def __init__(self, width=60, height=30, parent=None):
        super().__init__(parent)
        self._state = False
        self.width = width
        self.height = height
        self.callback = None
        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(Qt.LeftButton)

    def boundingRect(self):
        return QRectF(0, 0, self.width, self.height)

    def shape(self):
        path = QPainterPath()
        path.addRoundedRect(self.boundingRect(), self.height/2, self.height/2)
        return path

    def paint(self, painter, option, widget):
        radius = self.height / 2
        bg_color = config.COLOR_SWITCH_OFF if not self._state else config.COLOR_SWITCH_ON
        painter.setPen(Qt.NoPen)
        painter.setBrush(bg_color)
        painter.drawRoundedRect(self.boundingRect(), radius, radius)
        circle_diameter = self.height - 4
        circle_rect = QRectF(2, 2, circle_diameter, circle_diameter)
        if self._state:
            circle_rect.moveLeft(self.width - circle_diameter - 2)
        painter.setBrush(Qt.white)
        painter.drawEllipse(circle_rect)

    def mousePressEvent(self, event):
        self._state = not self._state
        self.update()
        if self.callback:
            self.callback(self._state)
        event.accept()

class GameModeRadioButton(QGraphicsItemGroup):
    def __init__(self, mode_text, mode_value, x, y, selected=False, parent=None):
        super().__init__(parent)
        self.mode_text = mode_text
        self.mode_value = mode_value
        self.selected = selected
        self.setAcceptHoverEvents(True)
        self.circle_radius = 8
        self.circle = QGraphicsEllipseItem(0, 8, self.circle_radius*2, self.circle_radius*2)
        self.circle.setBrush(QBrush(config.COLOR_SWITCH_ON) if self.selected else QBrush(Qt.white))
        self.circle.setPen(QPen(Qt.white, 1))
        self.addToGroup(self.circle)
        self.text_item = QGraphicsTextItem(mode_text)
        self.text_item.setDefaultTextColor(Qt.white)
        self.text_item.setFont(QFont(config.FONT_FAMILY, config.MENU_SWITCH_LABEL_FONT_SIZE))
        self.text_item.setPos(self.circle_radius*2 + 5, 0)
        self.addToGroup(self.text_item)
        self.setPos(x, y)

    def mousePressEvent(self, event):
        if self.scene() and hasattr(self.scene(), 'update_game_mode'):
            self.scene().update_game_mode(self.mode_value)
        event.accept()

    def setSelected(self, selected):
        self.selected = selected
        self.circle.setBrush(QBrush(config.COLOR_SWITCH_ON) if self.selected else QBrush(Qt.white))
        self.update()

class MenuScene(QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = None
        self.setSceneRect(0, 0, config.WINDOW_WIDTH, config.WINDOW_HEIGHT)
        self.level_buttons = []
        self.levels_data = []
        self.turn_based = False
        self.game_mode = "2 graczy lokalnie"
        self.radio_buttons = []
        self.network_ip = ""
        self.network_port = ""
        self.ip_lineedit = None
        self.port_lineedit = None
        self._ip_proxy = None
        self._port_proxy = None
        self.load_levels()
        self.setup_menu()
        self.editor_selected = None
        if self.logger:
            self.logger.log("MenuScene: Scena menu utworzona.")

    def load_levels(self):
        try:
            levels_path = os.path.join(os.path.dirname(__file__), 'levels.json')
            with open(levels_path, 'r') as f:
                self.levels_data = json.load(f)
        except Exception as e:
            print(f"Błąd wczytywania poziomów: {e}")
            self.levels_data = [{"name": "Poziom 1"}]

    def setup_menu(self):
        title = QGraphicsTextItem("Cell Expansion Wars")
        title.setFont(QFont(config.FONT_FAMILY, config.MENU_TITLE_FONT_SIZE, QFont.Bold))
        title.setDefaultTextColor(Qt.white)
        title_width = title.boundingRect().width()
        title.setPos((self.width() - title_width) / 2, config.MENU_TITLE_Y_POSITION)
        self.addItem(title)

        switch_label = QGraphicsTextItem("Tryb turowy")
        switch_label.setFont(QFont(config.FONT_FAMILY, config.MENU_SWITCH_LABEL_FONT_SIZE))
        switch_label.setDefaultTextColor(Qt.white)
        switch_label_width = switch_label.boundingRect().width()
        switch_label.setPos((self.width() - switch_label_width) / 2, config.MENU_SWITCH_LABEL_Y_POSITION)
        self.addItem(switch_label)

        self.switch = SwitchButton(60, 30)
        self.switch.setPos((self.width() - self.switch.width) / 2, config.MENU_SWITCH_Y_POSITION)
        def switch_callback(state):
            self.turn_based = state
            if self.logger:
                self.logger.log(f"MenuScene: Tryb turowy {'włączony' if state else 'wyłączony'}.")
        self.switch.callback = switch_callback
        self.addItem(self.switch)

        level_title = QGraphicsTextItem("Wybierz poziom:")
        level_title.setFont(QFont(config.FONT_FAMILY, config.MENU_LEVEL_TITLE_FONT_SIZE))
        level_title.setDefaultTextColor(Qt.white)
        level_title_width = level_title.boundingRect().width()
        level_title.setPos((self.width() - level_title_width) / 2, config.MENU_LEVEL_TITLE_Y_POSITION)
        self.addItem(level_title)

        y_pos = config.MENU_LEVEL_START_Y_POSITION
        button_width = config.MENU_LEVEL_BUTTON_WIDTH

        for i, level in enumerate(self.levels_data):
            button_x = (self.width() - button_width) / 2
            level_name = level.get('name', f'Poziom {i+1}')
            button_text = f"Poziom {i+1}: {level_name}"

            button = self.create_button(button_text, button_x, y_pos, button_width)
            button.left_rect.level_id = i + 1
            button.right_rect.level_id = i + 1
            button.right_rect.is_edit_button = True
            self.level_buttons.append(button)
            y_pos += 60

        mode_title = QGraphicsTextItem("Wybierz tryb gry:")
        mode_title.setFont(QFont(config.FONT_FAMILY, config.MENU_LEVEL_TITLE_FONT_SIZE))
        mode_title.setDefaultTextColor(Qt.white)
        mode_title_width = mode_title.boundingRect().width()
        mode_title.setPos((self.width() - mode_title_width) / 2, y_pos + config.MENU_MODE_TITLE_Y_OFFSET)
        self.addItem(mode_title)

        radio_y = y_pos + config.MENU_RADIO_FIRST_Y_OFFSET
        first_group = [("1 gracz", "1 gracz"), ("2 graczy lokalnie", "2 graczy lokalnie")]
        spacing = 110
        group_width = len(first_group) * spacing + 60
        radio_start_x_1 = (self.width() - group_width) / 2
        for i, (text, value) in enumerate(first_group):
            selected = (value == self.game_mode)
            radio = GameModeRadioButton(text, value, radio_start_x_1 + i * spacing, radio_y, selected)
            self.radio_buttons.append(radio)
            self.addItem(radio)

        radio_y2 = radio_y + config.MENU_RADIO_SECOND_Y_OFFSET
        second_group = [("gra sieciowa", "gra sieciowa")]
        for text, value in second_group:
            selected = (value == self.game_mode)
            radio_x = (self.width() - 140) / 2
            radio = GameModeRadioButton(text, value, radio_x, radio_y2, selected)
            self.radio_buttons.append(radio)
            self.addItem(radio)

        self.ip_lineedit = QLineEdit()
        self.ip_lineedit.setPlaceholderText("Adres IP (np. 192.168.1.1)")
        ip_regex = QRegExp(r"^((25[0-5]|2[0-4]\d|[01]?\d?\d)\.){3}(25[0-5]|2[0-4]\d|[01]?\d?\d)$")
        ip_validator = QRegExpValidator(ip_regex)
        self.ip_lineedit.setValidator(ip_validator)
        ip_width = int(self.width() * 0.25)
        self.ip_lineedit.setFixedWidth(ip_width)
        self.ip_lineedit.setStyleSheet("font-size: {}px;".format(int(self.width()/75)))
        ip_proxy = QGraphicsProxyWidget()
        ip_proxy.setWidget(self.ip_lineedit)
        ip_proxy.setPos((self.width() - ip_width) / 2, radio_y2 + config.MENU_IP_Y_OFFSET)
        self.addItem(ip_proxy)

        self.port_lineedit = QLineEdit()
        self.port_lineedit.setPlaceholderText("Port (np. 12345)")
        port_validator = QIntValidator(0, 65535)
        self.port_lineedit.setValidator(port_validator)
        port_width = int(self.width() * 0.25)
        self.port_lineedit.setFixedWidth(port_width)
        self.port_lineedit.setStyleSheet("font-size: {}px;".format(int(self.width()/75)))
        port_proxy = QGraphicsProxyWidget()
        port_proxy.setWidget(self.port_lineedit)
        port_proxy.setPos((self.width() - port_width) / 2, radio_y2 + config.MENU_PORT_Y_OFFSET)
        self.addItem(port_proxy)

        if self.game_mode != "gra sieciowa":
            ip_proxy.setVisible(False)
            port_proxy.setVisible(False)
        self._ip_proxy = ip_proxy
        self._port_proxy = port_proxy

        replay_source_title = QGraphicsTextItem("Źródło replay:")
        replay_source_title.setFont(QFont(config.FONT_FAMILY, config.MENU_LEVEL_TITLE_FONT_SIZE))
        replay_source_title.setDefaultTextColor(Qt.white)
        replay_source_title_width = replay_source_title.boundingRect().width()
        replay_source_title.setPos((self.width() - replay_source_title_width) / 2, self.height() - config.MENU_REPLAY_TITLE_Y_OFFSET)
        self.addItem(replay_source_title)
        self.replay_source = "XML"
        replay_options = [("XML", "XML"), ("JSON", "JSON"), ("NoSQL", "NoSQL")]
        radio_y = self.height() - 80
        spacing = 100
        group_width = len(replay_options) * spacing
        radio_start_x = (self.width() - group_width) / 2
        self.replay_radio_buttons = []
        def create_radio_handler(radio):
            def handler(event):
                self.replay_source = radio.mode_value
                for rb in self.replay_radio_buttons:
                    rb.setSelected(rb.mode_value == radio.mode_value)
                if self.logger:
                    self.logger.log(f"MenuScene: Wybrane źródło replay: {radio.mode_value}")
                event.accept()
            return handler
        for i, (text, value) in enumerate(replay_options):
            selected = (value == self.replay_source)
            radio = GameModeRadioButton(text, value, radio_start_x + i * spacing, radio_y, selected)
            radio.mousePressEvent = create_radio_handler(radio)
            self.replay_radio_buttons.append(radio)
            self.addItem(radio)
        replay_button = QPushButton("Odtwórz replay")
        replay_button.setFixedSize(150, 40)
        replay_proxy = QGraphicsProxyWidget()
        replay_proxy.setWidget(replay_button)
        replay_proxy.setPos((self.width() - 150) / 2, self.height() - config.MENU_REPLAY_BUTTON_Y_OFFSET)
        self.addItem(replay_proxy)
        replay_button.clicked.connect(lambda: self.replay_selected() if hasattr(self, 'replay_selected') else None)

    def create_button(self, text, x, y, width=200):
        class Button(QGraphicsItemGroup):
            def __init__(self, text, x, y, width, parent=None):
                super().__init__(parent)
                self.setFiltersChildEvents(False)
                height = 50
                right_width = height
                left_width = width - right_width

                self.left_rect = QGraphicsRectItem(x, y, left_width, height)
                self.left_rect.setBrush(QBrush(config.COLOR_BUTTON_LEFT))
                self.left_rect.setPen(QPen(Qt.white, 2))
                self.left_rect.level_id = 0
                self.addToGroup(self.left_rect)

                self.text_item = QGraphicsTextItem(text, self.left_rect)
                self.text_item.setDefaultTextColor(Qt.white)
                self.text_item.setFont(QFont(config.FONT_FAMILY, config.BUTTON_FONT_SIZE))
                self.update_text_position(x, y, left_width, height)

                self.right_rect = QGraphicsRectItem(x + left_width, y, right_width, height)
                self.right_rect.setBrush(QBrush(config.COLOR_BUTTON_RIGHT))
                self.right_rect.setPen(QPen(Qt.white, 2))
                self.right_rect.level_id = 0
                self.right_rect.is_edit_button = False
                self.addToGroup(self.right_rect)

                self.icon_item = QGraphicsPixmapItem(QPixmap(":/olowek.png"), self.right_rect)
                self.update_icon_position(x + left_width, y, right_width, height)

                for item in [self.left_rect, self.right_rect]:
                    item.setCursor(Qt.PointingHandCursor)

            def update_text_position(self, x, y, width, height):
                text_rect = self.text_item.boundingRect()
                text_x = (width - text_rect.width()) / 2
                text_y = (height - text_rect.height()) / 2
                self.text_item.setPos(x + text_x, y + text_y)

            def update_icon_position(self, x, y, width, height):
                icon_rect = self.icon_item.boundingRect()
                icon_x = (width - icon_rect.width()) / 2
                icon_y = (height - icon_rect.height()) / 2
                self.icon_item.setPos(x + icon_x, y + icon_y)

        button = Button(text, x, y, width)
        self.addItem(button)
        return button

    def mousePressEvent(self, event):
        pos = event.scenePos()
        clicked_items = self.items(pos)

        for item in clicked_items:
            if isinstance(item, QGraphicsRectItem) and hasattr(item, 'level_id') and item.level_id > 0:
                if hasattr(item, 'is_edit_button') and item.is_edit_button:
                    if self.logger:
                        self.logger.log(f"MenuScene: Wybrano edycję poziomu {item.level_id}.")
                    if self.editor_selected:
                        self.editor_selected(item.level_id)
                else:
                    if self.logger:
                        self.logger.log(f"MenuScene: Wybrano poziom {item.level_id} do gry.")
                    self.level_selected(item.level_id)
                return

        super().mousePressEvent(event)

    def level_selected(self, level_id):
        pass

    def update_game_mode(self, selected_mode):
        self.game_mode = selected_mode
        for radio in self.radio_buttons:
            radio.setSelected(radio.mode_value == selected_mode)
        if self.logger:
            self.logger.log(f"MenuScene: Wybrano tryb gry: {self.game_mode}")
        if self.game_mode == "gra sieciowa":
            if self._ip_proxy:
                self._ip_proxy.setVisible(True)
            if self._port_proxy:
                self._port_proxy.setVisible(True)
        else:
            if self._ip_proxy:
                self._ip_proxy.setVisible(False)
            if self._port_proxy:
                self._port_proxy.setVisible(False)

    def drawBackground(self, painter, rect):
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor(230, 190, 255))
        gradient.setColorAt(1, QColor(100, 0, 150))
        painter.fillRect(rect, gradient)