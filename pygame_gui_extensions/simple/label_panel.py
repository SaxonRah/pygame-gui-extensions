import pygame
import pygame_gui
from pygame_gui.core import UIElement, ObjectID
from pygame_gui.core.interfaces import IContainerLikeInterface
from typing import List, Optional, Dict, Any, Union, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum

LABEL_DEBUG = True

# Events
UI_LABEL_CLICKED = pygame.USEREVENT + 300
UI_LABEL_TEXT_CHANGED = pygame.USEREVENT + 303


class LabelAlignment(Enum):
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


@dataclass
class LabelLayoutConfig:
    padding_left: int = 4
    padding_right: int = 4
    padding_top: int = 2
    padding_bottom: int = 2
    border_width: int = 0
    corner_radius: int = 0
    font_size: int = 12
    bold: bool = False
    italic: bool = False
    line_spacing: int = 2


@dataclass
class LabelInteractionConfig:
    clickable: bool = False
    hoverable: bool = False
    double_click_time: int = 500


@dataclass
class LabelBehaviorConfig:
    auto_size: bool = False
    word_wrap: bool = False
    show_background: bool = False
    show_border: bool = False
    strip_whitespace: bool = True
    convert_tabs_to_spaces: bool = True
    tab_width: int = 4


@dataclass
class LabelConfig:
    layout: LabelLayoutConfig = field(default_factory=LabelLayoutConfig)
    interaction: LabelInteractionConfig = field(default_factory=LabelInteractionConfig)
    behavior: LabelBehaviorConfig = field(default_factory=LabelBehaviorConfig)
    default_alignment: LabelAlignment = LabelAlignment.LEFT


class LabelPanel(UIElement):
    """Always draws some background to avoid transparent text issues"""

    def __init__(self, relative_rect: pygame.Rect,
                 manager: pygame_gui.UIManager,
                 text: str = "",
                 config: LabelConfig = None,
                 container: IContainerLikeInterface = None,
                 object_id: Union[ObjectID, str, None] = None,
                 anchors: Dict[str, str] = None):

        # Handle object_id
        if isinstance(object_id, ObjectID):
            self._object_id = object_id
        elif isinstance(object_id, str):
            self._object_id = ObjectID(object_id=object_id, class_id=None)
        else:
            self._object_id = ObjectID(object_id='#label_panel', class_id=None)

        super().__init__(relative_rect, manager, container,
                         starting_height=1, layer_thickness=1,
                         anchors=anchors, object_id=self._object_id)

        # Store config
        self.config = config or LabelConfig()
        self._text = text or "Label"

        # Simple state tracking
        self.is_hovered = False
        self.is_pressed = False
        self.alignment = self.config.default_alignment

        # Timing
        self.last_click_time = 0

        # Create the image surface
        self.image = pygame.Surface(self.rect.size, pygame.SRCALPHA).convert_alpha()

        if LABEL_DEBUG:
            print(f"LabelPanel created: text='{self._text}', size={self.rect.size}")

        # Initialize
        self.rebuild_image()

    @property
    def text(self) -> str:
        return self._text

    @text.setter
    def text(self, value: str):
        if value != self._text:
            self._text = value or "Empty"
            self.rebuild_image()

            event_data = {'text': self._text, 'ui_element': self}
            pygame.event.post(pygame.event.Event(UI_LABEL_TEXT_CHANGED, event_data))

    def rebuild_image(self):
        """Always draws SOME background to avoid text rendering issues"""
        if LABEL_DEBUG:
            print(f"Rebuilding label image: {self.rect.size}, text: '{self._text}'")

        # Clear surface
        self.image.fill(pygame.Color(0, 0, 0, 0))  # Transparent

        # Always draw some kind of background
        bg_rect = pygame.Rect(2, 2, self.rect.width - 4, self.rect.height - 4)

        if self.config.behavior.show_background:
            # Visible background
            if LABEL_DEBUG:
                print("Drawing visible background...")
            bg_color = pygame.Color(60, 60, 60) if self.is_hovered else pygame.Color(50, 50, 50)
        else:
            # Invisible but present background - this prevents text rendering issues
            if LABEL_DEBUG:
                print("Drawing invisible background for text rendering...")
            bg_color = pygame.Color(0, 0, 0, 1)  # Almost transparent but not fully

        if self.config.layout.corner_radius > 0:
            pygame.draw.rect(self.image, bg_color, bg_rect, border_radius=self.config.layout.corner_radius)
        else:
            pygame.draw.rect(self.image, bg_color, bg_rect)

        # Create font - EXACT same methods as debug
        font = None
        font_size = self.config.layout.font_size
        font_bold = self.config.layout.bold
        font_italic = self.config.layout.italic

        font_methods = [
            lambda: pygame.font.SysFont('Arial', font_size, font_bold, font_italic),
            lambda: pygame.font.SysFont('Segoe UI', font_size),
            lambda: pygame.font.SysFont('Tahoma', font_size),
            lambda: pygame.font.Font(None, font_size),
        ]

        for i, font_method in enumerate(font_methods):
            try:
                font = font_method()
                if LABEL_DEBUG:
                    print(f"Font method {i} succeeded: {font}")
                break
            except Exception as e:
                if LABEL_DEBUG:
                    print(f"Font method {i} failed: {e}")

        if not font:
            if LABEL_DEBUG:
                print("ERROR: Could not create any font!")
            return

        # Process text
        text_to_render = self._text
        if self.config.behavior.strip_whitespace:
            text_to_render = text_to_render.strip()
        if self.config.behavior.convert_tabs_to_spaces:
            text_to_render = text_to_render.expandtabs(self.config.behavior.tab_width)

        # Handle word wrapping
        if self.config.behavior.word_wrap:
            content_w = (self.rect.width -
                         self.config.layout.padding_left -
                         self.config.layout.padding_right)

            lines = []
            for paragraph in text_to_render.split('\n'):
                if not paragraph:
                    lines.append("")
                    continue

                words = paragraph.split(' ')
                current_line = ""

                for word in words:
                    test_line = f"{current_line} {word}".strip()
                    if font.size(test_line)[0] <= content_w:
                        current_line = test_line
                    else:
                        if current_line:
                            lines.append(current_line)
                            current_line = word
                        else:
                            lines.append(word)

                if current_line:
                    lines.append(current_line)
        else:
            lines = [text_to_render]

        # Render text with STRONG color contrast
        if self.config.behavior.show_background:
            # For visible backgrounds, use normal colors
            text_color = pygame.Color(255, 255, 0) if self.is_hovered else pygame.Color(255, 255, 255)
        else:
            # For "invisible" backgrounds, use high contrast colors
            text_color = pygame.Color(255, 255, 255)  # Always white for max contrast

        # Calculate positioning
        content_x = self.config.layout.padding_left
        content_y = self.config.layout.padding_top
        content_w = (self.rect.width -
                     self.config.layout.padding_left -
                     self.config.layout.padding_right)
        content_h = (self.rect.height -
                     self.config.layout.padding_top -
                     self.config.layout.padding_bottom)

        # Render each line
        line_height = font.get_height() + self.config.layout.line_spacing
        total_height = len(lines) * line_height - self.config.layout.line_spacing

        start_y = content_y + (content_h - total_height) // 2  # Center vertically

        for i, line in enumerate(lines):
            if not line.strip():
                continue

            try:
                if LABEL_DEBUG and i == 0:
                    print(f"Trying to render text: '{line}' with color {text_color}")

                if hasattr(font, 'render_premul'):
                    text_surface = font.render_premul(line, text_color)
                else:
                    text_surface = font.render(line, True, text_color)

                if LABEL_DEBUG and i == 0:
                    print(f"Text surface created: size={text_surface.get_size()}")
                    print(f"Text surface bitsize={text_surface.get_bitsize()}")

                # Position text with alignment
                if self.alignment == LabelAlignment.LEFT:
                    text_x = content_x
                elif self.alignment == LabelAlignment.CENTER:
                    text_x = content_x + (content_w - text_surface.get_width()) // 2
                else:  # RIGHT
                    text_x = content_x + content_w - text_surface.get_width()

                text_y = start_y + i * line_height

                # EXACT same blit call as debug
                self.image.blit(text_surface, (text_x, text_y))

                if LABEL_DEBUG and i == 0:
                    print(f"Text blitted at ({text_x}, {text_y})")

            except Exception as e:
                if LABEL_DEBUG:
                    print(f"Error rendering text: {e}")

        # Draw border if enabled
        if self.config.behavior.show_border and self.config.layout.border_width > 0:
            border_color = pygame.Color(100, 100, 100)
            border_rect = pygame.Rect(0, 0, self.rect.width, self.rect.height)

            if self.config.layout.corner_radius > 0:
                pygame.draw.rect(self.image, border_color, border_rect,
                                 self.config.layout.border_width,
                                 border_radius=self.config.layout.corner_radius)
            else:
                pygame.draw.rect(self.image, border_color, border_rect,
                                 self.config.layout.border_width)

        if LABEL_DEBUG:
            print("Image rebuild complete")

    def process_event(self, event: pygame.event.Event) -> bool:
        consumed = False

        # Hover handling
        if self.config.interaction.hoverable and event.type == pygame.MOUSEMOTION:
            was_hovered = self.is_hovered
            self.is_hovered = self.rect.collidepoint(event.pos)
            if was_hovered != self.is_hovered:
                self.rebuild_image()

        # Click handling
        elif self.config.interaction.clickable and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                current_time = pygame.time.get_ticks()
                if (current_time - self.last_click_time) < self.config.interaction.double_click_time:
                    print("Double click detected")
                else:
                    event_data = {'ui_element': self}
                    pygame.event.post(pygame.event.Event(UI_LABEL_CLICKED, event_data))
                self.last_click_time = current_time
                consumed = True

        return consumed

    def update(self, time_delta: float):
        super().update(time_delta)

        # Auto-sizing
        if self.config.behavior.auto_size and self._text:
            # Create font for measuring
            font_methods = [
                lambda: pygame.font.SysFont('Arial', self.config.layout.font_size,
                                            self.config.layout.bold, self.config.layout.italic),
                lambda: pygame.font.Font(None, self.config.layout.font_size),
            ]

            font = None
            for font_method in font_methods:
                try:
                    font = font_method()
                    break
                except:
                    continue

            if font:
                text_size = font.size(self._text)
                new_width = (text_size[0] +
                             self.config.layout.padding_left +
                             self.config.layout.padding_right)
                new_height = (text_size[1] +
                              self.config.layout.padding_top +
                              self.config.layout.padding_bottom)

                if new_width != self.rect.width or new_height != self.rect.height:
                    self.rect.width = new_width
                    self.rect.height = new_height
                    self.image = pygame.Surface(self.rect.size, pygame.SRCALPHA).convert_alpha()
                    self.rebuild_image()


def main():
    """Test"""
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("Label Panel")
    clock = pygame.time.Clock()

    print("Starting label test...")

    manager = pygame_gui.UIManager((800, 600))

    # Test 1: Basic (should now work!)
    config1 = LabelConfig()
    label1 = LabelPanel(
        pygame.Rect(50, 50, 200, 30),
        manager,
        "Basic Label",
        config1
    )

    # Test 2: With background and hover
    config2 = LabelConfig()
    config2.behavior.show_background = True
    config2.interaction.hoverable = True
    label2 = LabelPanel(
        pygame.Rect(50, 100, 200, 30),
        manager,
        "Hover Label",
        config2
    )

    # Test 3: Centered with border
    config3 = LabelConfig()
    config3.behavior.show_background = True
    config3.behavior.show_border = True
    config3.default_alignment = LabelAlignment.CENTER
    config3.layout.border_width = 1
    label3 = LabelPanel(
        pygame.Rect(50, 150, 200, 30),
        manager,
        "Centered Border",
        config3
    )

    # Test 4: Auto-size
    config4 = LabelConfig()
    config4.behavior.auto_size = True
    config4.behavior.show_background = True
    config4.layout.padding_left = 10
    config4.layout.padding_right = 10
    label4 = LabelPanel(
        pygame.Rect(50, 200, 0, 0),  # Will auto-size
        manager,
        "Auto Size",
        config4
    )

    # Test 5: Word wrap
    config5 = LabelConfig()
    config5.behavior.word_wrap = True
    config5.behavior.show_background = True
    config5.layout.padding_left = 8
    config5.layout.padding_right = 8
    label5 = LabelPanel(
        pygame.Rect(300, 50, 200, 80),
        manager,
        "This text should wrap to multiple lines",
        config5
    )

    # Test 6: Another basic one to be sure
    config6 = LabelConfig()
    label6 = LabelPanel(
        pygame.Rect(50, 250, 200, 30),
        manager,
        "Another Basic",
        config6
    )

    print("Starting main loop...")

    running = True
    while running:
        time_delta = clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == UI_LABEL_CLICKED:
                print(f"Label clicked: {event.ui_element.text}")
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    label1.text = f"Updated {pygame.time.get_ticks()}"

            manager.process_events(event)

        manager.update(time_delta)

        screen.fill((30, 30, 30))
        manager.draw_ui(screen)

        # Reference squares
        pygame.draw.rect(screen, (100, 0, 0), (10, 10, 20, 20))
        pygame.draw.rect(screen, (0, 100, 0), (10, 40, 20, 20))

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()