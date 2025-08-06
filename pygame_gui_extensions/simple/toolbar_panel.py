import pygame
import pygame_gui
from pygame_gui.core import UIElement, ObjectID
from pygame_gui.core.interfaces import IContainerLikeInterface
from typing import List, Optional, Dict, Any, Union, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
import copy

try:
    from pygame_gui.core.interfaces.gui_font_interface import IGUIFontInterface
except ImportError:
    IGUIFontInterface = None

TOOLBAR_DEBUG = False

# Define custom pygame-gui events
UI_TOOLBAR_BUTTON_CLICKED = pygame.USEREVENT + 330
UI_TOOLBAR_BUTTON_HOVERED = pygame.USEREVENT + 331
UI_TOOLBAR_SEPARATOR_ADDED = pygame.USEREVENT + 332
UI_TOOLBAR_OVERFLOW_ACTIVATED = pygame.USEREVENT + 333
UI_TOOLBAR_GROUP_TOGGLED = pygame.USEREVENT + 334


class ToolbarOrientation(Enum):
    """Toolbar orientation"""
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"


class ToolbarButtonState(Enum):
    """Toolbar button states"""
    NORMAL = "normal"
    HOVERED = "hovered"
    PRESSED = "pressed"
    DISABLED = "disabled"
    ACTIVE = "active"  # Toggle state


class ToolbarOverflowMode(Enum):
    """Overflow handling modes"""
    NONE = "none"  # No overflow handling
    HIDE = "hide"  # Hide overflowing buttons
    SCROLL = "scroll"  # Add scroll buttons
    MENU = "menu"  # Show overflow menu


@dataclass
class ToolbarButton:
    """Represents a toolbar button"""
    id: str
    text: str = ""
    tooltip: str = ""
    icon: Optional[pygame.Surface] = None
    icon_path: Optional[str] = None
    callback: Optional[Callable] = None
    shortcut: Optional[str] = None
    enabled: bool = True
    visible: bool = True
    checkable: bool = False
    checked: bool = False
    group_id: Optional[str] = None  # For radio button groups
    width: Optional[int] = None  # Custom width
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolbarSeparator:
    """Represents a toolbar separator"""
    id: str
    width: int = 1
    visible: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolbarGroup:
    """Represents a group of related toolbar items"""
    id: str
    items: List[Union[ToolbarButton, ToolbarSeparator]] = field(default_factory=list)
    label: str = ""
    collapsible: bool = False
    collapsed: bool = False
    visible: bool = True
    exclusive: bool = False  # Only one button can be active at a time
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolbarLayoutConfig:
    """Layout and spacing configuration for toolbar panel"""
    # Orientation and sizing
    orientation: ToolbarOrientation = ToolbarOrientation.HORIZONTAL
    button_size: Tuple[int, int] = (32, 32)
    auto_size_buttons: bool = True

    # Spacing
    button_spacing: int = 2
    group_spacing: int = 8
    padding: int = 4

    # Icons and text
    icon_size: Tuple[int, int] = (16, 16)
    show_text: bool = False
    text_position: str = "bottom"  # bottom, right, left, top
    font_size: int = 10

    # Separators
    separator_width: int = 1
    separator_margin: int = 4
    separator_height_ratio: float = 0.6  # Fraction of button height

    # Border and background
    border_width: int = 1
    corner_radius: int = 2

    # Overflow
    overflow_button_size: int = 16
    overflow_indicator_size: int = 8

    # Group headers
    group_header_height: int = 20
    group_header_font_size: int = 10


@dataclass
class ToolbarInteractionConfig:
    """Interaction and timing configuration"""
    # Click behavior
    click_sound: Optional[str] = None
    double_click_time: int = 500

    # Hover behavior
    hover_delay: int = 100
    hover_sound: Optional[str] = None
    show_tooltips: bool = True
    tooltip_delay: int = 1000

    # Keyboard navigation
    keyboard_navigation: bool = True
    tab_navigation: bool = True
    arrow_key_navigation: bool = True

    # Animation
    animate_hover: bool = True
    animate_press: bool = True
    animation_duration: float = 0.1


@dataclass
class ToolbarBehaviorConfig:
    """Behavior configuration for toolbar panel"""
    # Button behavior
    auto_repeat_enabled: bool = False
    auto_repeat_delay: float = 0.5
    auto_repeat_rate: float = 0.1

    # Visual behavior
    show_button_backgrounds: bool = True
    show_button_borders: bool = False
    highlight_active_buttons: bool = True
    show_shortcuts_in_tooltips: bool = True

    # Group behavior
    remember_group_states: bool = True
    animate_group_collapse: bool = True

    # Overflow behavior
    overflow_mode: ToolbarOverflowMode = ToolbarOverflowMode.HIDE
    show_overflow_indicator: bool = True

    # Performance
    cache_button_images: bool = True
    lazy_icon_loading: bool = False


@dataclass
class ToolbarConfig:
    """Complete configuration for the toolbar panel"""
    # Sub-configurations
    layout: ToolbarLayoutConfig = field(default_factory=ToolbarLayoutConfig)
    interaction: ToolbarInteractionConfig = field(default_factory=ToolbarInteractionConfig)
    behavior: ToolbarBehaviorConfig = field(default_factory=ToolbarBehaviorConfig)

    # Convenience properties
    @property
    def orientation(self) -> ToolbarOrientation:
        return self.layout.orientation

    @property
    def button_size(self) -> Tuple[int, int]:
        return self.layout.button_size

    @property
    def show_tooltips(self) -> bool:
        return self.interaction.show_tooltips


class ToolbarThemeManager:
    """Manages theming for the toolbar panel"""

    def __init__(self, ui_manager: pygame_gui.UIManager, element_ids: List[str]):
        self.ui_manager = ui_manager
        self.element_ids = element_ids
        self.themed_colors = {}
        self.themed_fonts = {}
        self._update_theme_data()

    def _update_theme_data(self):
        """Update theme-dependent data with comprehensive fallbacks"""

        # Default color mappings
        color_mappings = {
            # Panel colors
            'panel_bg': pygame.Color(50, 50, 50),
            'panel_border': pygame.Color(100, 100, 100),

            # Button colors by state
            'button_normal_bg': pygame.Color(0, 0, 0, 0),  # Transparent
            'button_hovered_bg': pygame.Color(70, 70, 70, 180),
            'button_pressed_bg': pygame.Color(90, 90, 90, 180),
            'button_disabled_bg': pygame.Color(40, 40, 40, 100),
            'button_active_bg': pygame.Color(70, 130, 180, 180),

            'button_normal_border': pygame.Color(0, 0, 0, 0),  # Transparent
            'button_hovered_border': pygame.Color(100, 100, 100),
            'button_pressed_border': pygame.Color(120, 120, 120),
            'button_disabled_border': pygame.Color(60, 60, 60),
            'button_active_border': pygame.Color(100, 150, 200),

            'button_normal_text': pygame.Color(255, 255, 255),
            'button_hovered_text': pygame.Color(255, 255, 255),
            'button_pressed_text': pygame.Color(220, 220, 220),
            'button_disabled_text': pygame.Color(120, 120, 120),
            'button_active_text': pygame.Color(255, 255, 255),

            # Separator colors
            'separator': pygame.Color(100, 100, 100),
            'separator_shadow': pygame.Color(30, 30, 30),

            # Group colors
            'group_header_bg': pygame.Color(60, 60, 60),
            'group_header_text': pygame.Color(200, 200, 200),
            'group_border': pygame.Color(80, 80, 80),

            # Overflow colors
            'overflow_button_bg': pygame.Color(60, 60, 60),
            'overflow_indicator': pygame.Color(255, 255, 100),

            # Shadow and highlights
            'shadow': pygame.Color(0, 0, 0, 80),
            'highlight': pygame.Color(255, 255, 255, 60),
        }

        try:
            self.themed_colors = {}
            theme = self.ui_manager.get_theme()

            for color_id, default_color in color_mappings.items():
                try:
                    if hasattr(theme, 'get_colour_or_gradient'):
                        color = theme.get_colour_or_gradient(color_id, self.element_ids)
                        self.themed_colors[color_id] = color if color else default_color
                    else:
                        self.themed_colors[color_id] = default_color
                except Exception:
                    self.themed_colors[color_id] = default_color

            # Get themed fonts
            try:
                if hasattr(theme, 'get_font'):
                    self.themed_fonts['default'] = theme.get_font(self.element_ids)
                else:
                    raise Exception("No font method")
            except Exception:
                try:
                    self.themed_fonts['default'] = pygame.font.SysFont('Arial', 10)
                except:
                    self.themed_fonts['default'] = pygame.font.Font(None, 10)

        except Exception as e:
            if TOOLBAR_DEBUG:
                print(f"Error updating toolbar theme: {e}")
            # Use all defaults
            self.themed_colors = color_mappings
            self.themed_fonts['default'] = pygame.font.Font(None, 10)

    def get_color(self, color_id: str, state: ToolbarButtonState = ToolbarButtonState.NORMAL) -> pygame.Color:
        """Get color for specific button state"""
        if state != ToolbarButtonState.NORMAL:
            state_color_id = f"{color_id}_{state.value}"
            if state_color_id in self.themed_colors:
                return self.themed_colors[state_color_id]

        return self.themed_colors.get(color_id, pygame.Color(255, 255, 255))

    def get_font(self, font_size: int = 10) -> pygame.font.Font:
        """Get font with specified size"""
        font_key = f"font_{font_size}"

        if font_key not in self.themed_fonts:
            try:
                self.themed_fonts[font_key] = pygame.font.SysFont('Arial', font_size)
            except:
                self.themed_fonts[font_key] = pygame.font.Font(None, font_size)

        return self.themed_fonts[font_key]


class ToolbarButtonRenderer:
    """Renders individual toolbar buttons"""

    def __init__(self, button: ToolbarButton, config: ToolbarConfig, theme_manager: ToolbarThemeManager):
        self.button = button
        self.config = config
        self.theme_manager = theme_manager
        self.rect = pygame.Rect(0, 0, 0, 0)
        self.state = ToolbarButtonState.NORMAL
        self.cached_image = None
        self.last_render_state = None

    def set_rect(self, rect: pygame.Rect):
        """Set the button rectangle"""
        if rect != self.rect:
            self.rect = rect
            self.cached_image = None

    def set_state(self, state: ToolbarButtonState):
        """Set the button state"""
        if state != self.state:
            self.state = state
            self.cached_image = None

    def render(self, surface: pygame.Surface):
        """Render the button to the surface"""
        if not self.button.visible or self.rect.width == 0:
            return

        # Check if we need to re-render
        current_state = (self.state, self.button.checked, self.button.enabled)
        if (self.config.behavior.cache_button_images and
                self.cached_image and
                current_state == self.last_render_state):
            surface.blit(self.cached_image, self.rect)
            return

        # Create button surface
        button_surface = pygame.Surface(self.rect.size, pygame.SRCALPHA).convert_alpha()

        # Determine effective state
        effective_state = self.state
        if not self.button.enabled:
            effective_state = ToolbarButtonState.DISABLED
        elif self.button.checked:
            effective_state = ToolbarButtonState.ACTIVE

        # Draw background
        if self.config.behavior.show_button_backgrounds:
            bg_color = self.theme_manager.get_color('button_bg', effective_state)
            if bg_color.a > 0:
                if self.config.layout.corner_radius > 0:
                    pygame.draw.rect(button_surface, bg_color, button_surface.get_rect(),
                                     border_radius=self.config.layout.corner_radius)
                else:
                    pygame.draw.rect(button_surface, bg_color, button_surface.get_rect())

        # Draw border
        if self.config.behavior.show_button_borders or effective_state != ToolbarButtonState.NORMAL:
            border_color = self.theme_manager.get_color('button_border', effective_state)
            if border_color.a > 0:
                if self.config.layout.corner_radius > 0:
                    pygame.draw.rect(button_surface, border_color, button_surface.get_rect(),
                                     self.config.layout.border_width,
                                     border_radius=self.config.layout.corner_radius)
                else:
                    pygame.draw.rect(button_surface, border_color, button_surface.get_rect(),
                                     self.config.layout.border_width)

        # Calculate content area
        content_rect = button_surface.get_rect()
        content_rect.inflate_ip(-4, -4)  # Small padding

        # Draw icon
        icon_rect = None
        if self.button.icon:
            icon = self.button.icon
            icon_size = self.config.layout.icon_size

            # Scale icon if needed
            if icon.get_size() != icon_size:
                icon = pygame.transform.scale(icon, icon_size)

            # Position icon
            if self.config.layout.show_text:
                if self.config.layout.text_position == "bottom":
                    icon_rect = pygame.Rect(
                        content_rect.centerx - icon_size[0] // 2,
                        content_rect.y,
                        icon_size[0], icon_size[1]
                    )
                elif self.config.layout.text_position == "right":
                    icon_rect = pygame.Rect(
                        content_rect.x,
                        content_rect.centery - icon_size[1] // 2,
                        icon_size[0], icon_size[1]
                    )
                elif self.config.layout.text_position == "left":
                    icon_rect = pygame.Rect(
                        content_rect.right - icon_size[0],
                        content_rect.centery - icon_size[1] // 2,
                        icon_size[0], icon_size[1]
                    )
                else:  # top
                    icon_rect = pygame.Rect(
                        content_rect.centerx - icon_size[0] // 2,
                        content_rect.bottom - icon_size[1],
                        icon_size[0], icon_size[1]
                    )
            else:
                # Center icon
                icon_rect = pygame.Rect(
                    content_rect.centerx - icon_size[0] // 2,
                    content_rect.centery - icon_size[1] // 2,
                    icon_size[0], icon_size[1]
                )

            # Apply disabled effect
            if not self.button.enabled:
                icon = icon.copy()
                icon.set_alpha(100)

            button_surface.blit(icon, icon_rect)

        # Draw text
        if self.config.layout.show_text and self.button.text:
            text_color = self.theme_manager.get_color('button_text', effective_state)
            font = self.theme_manager.get_font(self.config.layout.font_size)

            text_surface = font.render(self.button.text, True, text_color)

            # Position text
            if icon_rect:
                if self.config.layout.text_position == "bottom":
                    text_pos = (
                        content_rect.centerx - text_surface.get_width() // 2,
                        icon_rect.bottom + 2
                    )
                elif self.config.layout.text_position == "right":
                    text_pos = (
                        icon_rect.right + 2,
                        content_rect.centery - text_surface.get_height() // 2
                    )
                elif self.config.layout.text_position == "left":
                    text_pos = (
                        icon_rect.left - text_surface.get_width() - 2,
                        content_rect.centery - text_surface.get_height() // 2
                    )
                else:  # top
                    text_pos = (
                        content_rect.centerx - text_surface.get_width() // 2,
                        icon_rect.top - text_surface.get_height() - 2
                    )
            else:
                # Center text
                text_pos = (
                    content_rect.centerx - text_surface.get_width() // 2,
                    content_rect.centery - text_surface.get_height() // 2
                )

            button_surface.blit(text_surface, text_pos)

        # Cache the rendered button
        if self.config.behavior.cache_button_images:
            self.cached_image = button_surface.copy()
            self.last_render_state = current_state

        # Blit to main surface
        surface.blit(button_surface, self.rect)


class ToolbarPanel(UIElement):
    """Horizontal or vertical button strip with groups and overflow handling"""

    def __init__(self, relative_rect: pygame.Rect,
                 manager: pygame_gui.UIManager,
                 config: ToolbarConfig = None,
                 container: IContainerLikeInterface = None,
                 object_id: Union[ObjectID, str, None] = None,
                 anchors: Dict[str, str] = None):

        # Handle object_id properly
        if isinstance(object_id, ObjectID):
            self._object_id = object_id
        elif isinstance(object_id, str):
            self._object_id = ObjectID(object_id=object_id, class_id=None)
        else:
            self._object_id = ObjectID(object_id='#toolbar_panel', class_id=None)

        super().__init__(relative_rect, manager, container,
                         starting_height=1, layer_thickness=1,
                         anchors=anchors, object_id=self._object_id)

        self.config = config or ToolbarConfig()

        # Create theme manager
        element_ids = ['toolbar_panel']
        if hasattr(self, 'object_ids') and self.object_ids:
            element_ids.extend(self.object_ids)
        self.theme_manager = ToolbarThemeManager(manager, element_ids)

        # Toolbar data
        self.toolbar_groups: List[ToolbarGroup] = []
        self.buttons: Dict[str, ToolbarButton] = {}
        self.separators: Dict[str, ToolbarSeparator] = {}

        # Button renderers
        self.button_renderers: Dict[str, ToolbarButtonRenderer] = {}

        # State
        self.hovered_button: Optional[str] = None
        self.pressed_button: Optional[str] = None
        self.focused_button: Optional[str] = None

        # Layout state
        self.visible_buttons: List[str] = []
        self.overflowing_buttons: List[str] = []
        self.button_rects: Dict[str, pygame.Rect] = {}
        self.separator_rects: Dict[str, pygame.Rect] = {}

        # Overflow state
        self.overflow_button_rect = pygame.Rect(0, 0, 0, 0)
        self.show_overflow_menu = False

        # Timing
        self.last_click_time = 0
        self.last_clicked_button: Optional[str] = None

        # Create the image surface
        #self.image = pygame.Surface(self.rect.size).convert()
        self.image = pygame.Surface(self.rect.size, pygame.SRCALPHA).convert_alpha()

        # Initialize
        self._calculate_layout()
        self.rebuild_image()

    # Public API
    def add_button(self, button: ToolbarButton, group_id: Optional[str] = None) -> ToolbarButton:
        """Add a button to the toolbar"""
        self.buttons[button.id] = button

        # Create renderer
        self.button_renderers[button.id] = ToolbarButtonRenderer(
            button, self.config, self.theme_manager
        )

        # Add to group
        if group_id:
            group = self.get_group(group_id)
            if group:
                group.items.append(button)
            else:
                # Create new group
                group = ToolbarGroup(group_id, [button])
                self.toolbar_groups.append(group)
        elif not self.toolbar_groups:
            # Create default group
            group = ToolbarGroup("default", [button])
            self.toolbar_groups.append(group)
        else:
            # Add to last group
            self.toolbar_groups[-1].items.append(button)

        self._calculate_layout()
        self.rebuild_image()
        return button

    def add_separator(self, separator_id: str = None, group_id: Optional[str] = None) -> ToolbarSeparator:
        """Add a separator to the toolbar"""
        if separator_id is None:
            separator_id = f"sep_{len(self.separators)}"

        separator = ToolbarSeparator(separator_id)
        self.separators[separator_id] = separator

        # Add to group
        if group_id:
            group = self.get_group(group_id)
            if group:
                group.items.append(separator)
        elif self.toolbar_groups:
            self.toolbar_groups[-1].items.append(separator)

        self._calculate_layout()
        self.rebuild_image()
        return separator

    def add_group(self, group: ToolbarGroup) -> ToolbarGroup:
        """Add a button group to the toolbar"""
        self.toolbar_groups.append(group)

        # Register all buttons and separators
        for item in group.items:
            if isinstance(item, ToolbarButton):
                self.buttons[item.id] = item
                self.button_renderers[item.id] = ToolbarButtonRenderer(
                    item, self.config, self.theme_manager
                )
            elif isinstance(item, ToolbarSeparator):
                self.separators[item.id] = item

        self._calculate_layout()
        self.rebuild_image()
        return group

    def get_button(self, button_id: str) -> Optional[ToolbarButton]:
        """Get button by ID"""
        return self.buttons.get(button_id)

    def get_group(self, group_id: str) -> Optional[ToolbarGroup]:
        """Get group by ID"""
        for group in self.toolbar_groups:
            if group.id == group_id:
                return group
        return None

    def set_button_state(self, button_id: str, checked: bool = None, enabled: bool = None):
        """Set button state"""
        button = self.get_button(button_id)
        if not button:
            return

        if checked is not None:
            button.checked = checked

            # Handle exclusive groups
            if checked and button.group_id:
                group = self.get_group(button.group_id)
                if group and group.exclusive:
                    # Uncheck other buttons in group
                    for item in group.items:
                        if isinstance(item, ToolbarButton) and item.id != button_id:
                            item.checked = False

        if enabled is not None:
            button.enabled = enabled

        self.rebuild_image()

    def remove_button(self, button_id: str):
        """Remove a button"""
        if button_id in self.buttons:
            del self.buttons[button_id]

        if button_id in self.button_renderers:
            del self.button_renderers[button_id]

        # Remove from groups
        for group in self.toolbar_groups:
            group.items = [item for item in group.items
                           if not (isinstance(item, ToolbarButton) and item.id == button_id)]

        self._calculate_layout()
        self.rebuild_image()

    def clear(self):
        """Clear all buttons and groups"""
        self.toolbar_groups.clear()
        self.buttons.clear()
        self.separators.clear()
        self.button_renderers.clear()
        self._calculate_layout()
        self.rebuild_image()

    # Internal methods
    def _calculate_layout(self):
        """Calculate button positions and handle overflow"""
        self.visible_buttons.clear()
        self.overflowing_buttons.clear()
        self.button_rects.clear()
        self.separator_rects.clear()

        if not self.toolbar_groups:
            return

        is_horizontal = self.config.layout.orientation == ToolbarOrientation.HORIZONTAL
        padding = self.config.layout.padding

        # Available space
        if is_horizontal:
            available_space = self.rect.width - 2 * padding
            current_pos = padding
        else:
            available_space = self.rect.height - 2 * padding
            current_pos = padding

        # Reserve space for overflow button if needed
        overflow_space = 0
        if self.config.behavior.overflow_mode != ToolbarOverflowMode.NONE:
            overflow_space = self.config.layout.overflow_button_size + self.config.layout.button_spacing

        effective_space = available_space - overflow_space

        # Calculate required space first
        total_required = 0
        for group in self.toolbar_groups:
            if not group.visible:
                continue

            group_size = 0
            for item in group.items:
                if isinstance(item, ToolbarButton) and item.visible:
                    button_size = self._calculate_button_size(item)
                    group_size += button_size[0 if is_horizontal else 1]
                    group_size += self.config.layout.button_spacing
                elif isinstance(item, ToolbarSeparator) and item.visible:
                    group_size += item.width + 2 * self.config.layout.separator_margin

            if group_size > 0:
                total_required += group_size + self.config.layout.group_spacing

        # Layout items
        has_overflow = total_required > effective_space
        used_space = 0

        for group in self.toolbar_groups:
            if not group.visible:
                continue

            # Add group spacing
            if current_pos > padding:
                current_pos += self.config.layout.group_spacing

            for item in group.items:
                if isinstance(item, ToolbarButton) and item.visible:
                    button_size = self._calculate_button_size(item)

                    # Check if button fits
                    if (used_space + button_size[0 if is_horizontal else 1] <= effective_space or
                            not has_overflow):

                        # Position button
                        if is_horizontal:
                            rect = pygame.Rect(current_pos, padding,
                                               button_size[0], self.rect.height - 2 * padding)
                            current_pos += button_size[0] + self.config.layout.button_spacing
                        else:
                            rect = pygame.Rect(padding, current_pos,
                                               self.rect.width - 2 * padding, button_size[1])
                            current_pos += button_size[1] + self.config.layout.button_spacing

                        self.button_rects[item.id] = rect
                        self.button_renderers[item.id].set_rect(rect)
                        self.visible_buttons.append(item.id)
                        used_space += button_size[0 if is_horizontal else 1]
                    else:
                        # Button overflows
                        self.overflowing_buttons.append(item.id)

                elif isinstance(item, ToolbarSeparator) and item.visible:
                    # Position separator
                    sep_width = item.width
                    sep_margin = self.config.layout.separator_margin

                    if is_horizontal:
                        sep_height = int(self.rect.height * self.config.layout.separator_height_ratio)
                        sep_y = (self.rect.height - sep_height) // 2
                        rect = pygame.Rect(current_pos + sep_margin, sep_y, sep_width, sep_height)
                        current_pos += sep_width + 2 * sep_margin
                    else:
                        sep_width_actual = int(self.rect.width * self.config.layout.separator_height_ratio)
                        sep_x = (self.rect.width - sep_width_actual) // 2
                        rect = pygame.Rect(sep_x, current_pos + sep_margin, sep_width_actual, sep_width)
                        current_pos += sep_width + 2 * sep_margin

                    self.separator_rects[item.id] = rect

        # Position overflow button
        if has_overflow and self.overflowing_buttons:
            overflow_size = self.config.layout.overflow_button_size
            if is_horizontal:
                self.overflow_button_rect = pygame.Rect(
                    self.rect.width - overflow_size - padding,
                    (self.rect.height - overflow_size) // 2,
                    overflow_size, overflow_size
                )
            else:
                self.overflow_button_rect = pygame.Rect(
                    (self.rect.width - overflow_size) // 2,
                    self.rect.height - overflow_size - padding,
                    overflow_size, overflow_size
                )
        else:
            self.overflow_button_rect = pygame.Rect(0, 0, 0, 0)

    def _calculate_button_size(self, button: ToolbarButton) -> Tuple[int, int]:
        """Calculate button size"""
        if button.width:
            if self.config.layout.orientation == ToolbarOrientation.HORIZONTAL:
                return (button.width, self.config.layout.button_size[1])
            else:
                return (self.config.layout.button_size[0], button.width)

        if self.config.layout.auto_size_buttons and self.config.layout.show_text and button.text:
            font = self.theme_manager.get_font(self.config.layout.font_size)
            text_size = font.size(button.text)

            # Add padding for icon and spacing
            extra_w = 8  # Basic padding
            extra_h = 8

            if button.icon:
                if self.config.layout.text_position in ["left", "right"]:
                    extra_w += self.config.layout.icon_size[0] + 4
                    extra_h = max(extra_h, self.config.layout.icon_size[1] + 8)
                else:  # top/bottom
                    extra_w = max(extra_w, self.config.layout.icon_size[0] + 8)
                    extra_h += self.config.layout.icon_size[1] + 4

            return (text_size[0] + extra_w, text_size[1] + extra_h)

        return self.config.layout.button_size

    def _get_button_at_position(self, pos: Tuple[int, int]) -> Optional[str]:
        """Get button at the given position"""
        for button_id, rect in self.button_rects.items():
            if rect.collidepoint(pos):
                return button_id
        return None

    def rebuild_image(self):
        """Rebuild the toolbar image"""
        self.image.fill(self.theme_manager.get_color('panel_bg'))

        # Use element's coordinate space
        element_rect = pygame.Rect(0, 0, self.rect.width, self.rect.height)

        # Draw panel border
        if self.config.layout.border_width > 0:
            border_color = self.theme_manager.get_color('panel_border')
            pygame.draw.rect(self.image, border_color, element_rect,
                             self.config.layout.border_width)

        # Draw separators (coordinates should already be relative)
        for sep_id, rect in self.separator_rects.items():
            sep_color = self.theme_manager.get_color('separator')
            shadow_color = self.theme_manager.get_color('separator_shadow')

            # Draw separator with shadow effect
            pygame.draw.rect(self.image, shadow_color,
                             (rect.x + 1, rect.y + 1, rect.width, rect.height))
            pygame.draw.rect(self.image, sep_color, rect)

        # Draw buttons (renderers should handle relative coordinates)
        for button_id in self.visible_buttons:
            renderer = self.button_renderers[button_id]
            renderer.render(self.image)

        # Draw overflow button
        if self.overflow_button_rect.width > 0:
            overflow_bg = self.theme_manager.get_color('overflow_button_bg')
            pygame.draw.rect(self.image, overflow_bg, self.overflow_button_rect)

            # Draw overflow indicator (three dots)
            if self.config.behavior.show_overflow_indicator:
                indicator_color = self.theme_manager.get_color('overflow_indicator')
                center = self.overflow_button_rect.center
                dot_size = 2
                spacing = 4

                for i in range(3):
                    if self.config.layout.orientation == ToolbarOrientation.HORIZONTAL:
                        dot_pos = (center[0] - spacing + i * spacing, center[1])
                    else:
                        dot_pos = (center[0], center[1] - spacing + i * spacing)

                    pygame.draw.circle(self.image, indicator_color, dot_pos, dot_size)

    def process_event(self, event: pygame.event.Event) -> bool:
        """Process events"""
        consumed = False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            clicked_button = self._get_button_at_position(event.pos)

            if clicked_button:
                button = self.buttons[clicked_button]
                if button.enabled:
                    self.pressed_button = clicked_button
                    self.button_renderers[clicked_button].set_state(ToolbarButtonState.PRESSED)
                    self.rebuild_image()
                    consumed = True

            elif self.overflow_button_rect.collidepoint(event.pos):
                # Handle overflow button click
                self.show_overflow_menu = not self.show_overflow_menu
                event_data = {'ui_element': self, 'overflowing_buttons': self.overflowing_buttons}
                pygame.event.post(pygame.event.Event(UI_TOOLBAR_OVERFLOW_ACTIVATED, event_data))
                consumed = True

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.pressed_button:
                clicked_button = self._get_button_at_position(event.pos)

                if clicked_button == self.pressed_button:
                    button = self.buttons[clicked_button]

                    # Handle checkable buttons
                    if button.checkable:
                        button.checked = not button.checked

                        # Handle exclusive groups
                        if button.checked and button.group_id:
                            group = self.get_group(button.group_id)
                            if group and group.exclusive:
                                for item in group.items:
                                    if isinstance(item, ToolbarButton) and item.id != clicked_button:
                                        item.checked = False

                    # Call callback
                    if button.callback:
                        try:
                            button.callback(button)
                        except Exception as e:
                            if TOOLBAR_DEBUG:
                                print(f"Error calling button callback: {e}")

                    # Fire event
                    event_data = {
                        'button': button,
                        'button_id': clicked_button,
                        'ui_element': self
                    }
                    pygame.event.post(pygame.event.Event(UI_TOOLBAR_BUTTON_CLICKED, event_data))

                # Reset pressed state
                if self.pressed_button in self.button_renderers:
                    self.button_renderers[self.pressed_button].set_state(
                        ToolbarButtonState.HOVERED if clicked_button == self.pressed_button
                        else ToolbarButtonState.NORMAL
                    )

                self.pressed_button = None
                self.rebuild_image()
                consumed = True

        elif event.type == pygame.MOUSEMOTION:
            hovered_button = self._get_button_at_position(event.pos)

            if hovered_button != self.hovered_button:
                # Update old hovered button
                if self.hovered_button and self.hovered_button in self.button_renderers:
                    self.button_renderers[self.hovered_button].set_state(ToolbarButtonState.NORMAL)

                # Update new hovered button
                if hovered_button and hovered_button in self.button_renderers:
                    button = self.buttons[hovered_button]
                    if button.enabled:
                        self.button_renderers[hovered_button].set_state(ToolbarButtonState.HOVERED)

                        # Fire hover event
                        event_data = {
                            'button': button,
                            'button_id': hovered_button,
                            'ui_element': self
                        }
                        pygame.event.post(pygame.event.Event(UI_TOOLBAR_BUTTON_HOVERED, event_data))

                self.hovered_button = hovered_button
                self.rebuild_image()

        return consumed

    def update(self, time_delta: float):
        """Update the toolbar"""
        super().update(time_delta)


# Example usage and theme
TOOLBAR_THEME = {
    'toolbar_panel': {
        'colours': {
            'panel_bg': '#323232',
            'panel_border': '#646464',

            'button_normal_bg': '#00000000',
            'button_hovered_bg': '#464646B4',
            'button_pressed_bg': '#5A5A5AB4',
            'button_disabled_bg': '#28282864',
            'button_active_bg': '#4682B4B4',

            'button_normal_border': '#00000000',
            'button_hovered_border': '#646464',
            'button_pressed_border': '#787878',
            'button_disabled_border': '#3C3C3C',
            'button_active_border': '#6496C8',

            'button_normal_text': '#FFFFFF',
            'button_hovered_text': '#FFFFFF',
            'button_pressed_text': '#DCDCDC',
            'button_disabled_text': '#787878',
            'button_active_text': '#FFFFFF',

            'separator': '#646464',
            'separator_shadow': '#1E1E1E',

            'group_header_bg': '#3C3C3C',
            'group_header_text': '#C8C8C8',
            'group_border': '#505050',

            'overflow_button_bg': '#3C3C3C',
            'overflow_indicator': '#FFFF64',

            'shadow': '#00000050',
            'highlight': '#FFFFFF3C',
        }
    }
}


def main():
    """Example demonstration of the Toolbar Panel"""
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("Toolbar Panel Demo")
    clock = pygame.time.Clock()

    # Create manager with theme
    manager = pygame_gui.UIManager((800, 600), TOOLBAR_THEME)

    # Create toolbar configurations
    horizontal_config = ToolbarConfig()
    horizontal_config.layout.show_text = True
    horizontal_config.layout.text_position = "bottom"

    vertical_config = ToolbarConfig()
    vertical_config.layout.orientation = ToolbarOrientation.VERTICAL
    vertical_config.layout.button_size = (48, 48)

    # Create some sample icons
    def create_icon(color, shape="circle"):
        icon = pygame.Surface((16, 16), pygame.SRCALPHA)
        if shape == "circle":
            pygame.draw.circle(icon, color, (8, 8), 6)
        elif shape == "rect":
            pygame.draw.rect(icon, color, (2, 2, 12, 12))
        elif shape == "triangle":
            pygame.draw.polygon(icon, color, [(8, 2), (14, 14), (2, 14)])
        return icon

    # Create horizontal toolbar
    horizontal_toolbar = ToolbarPanel(
        pygame.Rect(50, 50, 500, 60),
        manager,
        horizontal_config
    )

    # Add buttons to horizontal toolbar
    file_group = ToolbarGroup("file", label="File")

    new_button = ToolbarButton("new", "New", "Create new file", create_icon((100, 255, 100)))
    new_button.callback = lambda btn: print(f"New file clicked")

    open_button = ToolbarButton("open", "Open", "Open file", create_icon((100, 150, 255)))
    open_button.callback = lambda btn: print(f"Open file clicked")

    save_button = ToolbarButton("save", "Save", "Save file", create_icon((255, 200, 100)))
    save_button.callback = lambda btn: print(f"Save file clicked")

    file_group.items = [new_button, open_button, save_button]
    horizontal_toolbar.add_group(file_group)

    # Add separator
    horizontal_toolbar.add_separator()

    # Edit group
    edit_group = ToolbarGroup("edit", label="Edit")

    cut_button = ToolbarButton("cut", "Cut", "Cut selection", create_icon((255, 100, 100), "rect"))
    copy_button = ToolbarButton("copy", "Copy", "Copy selection", create_icon((255, 255, 100), "rect"))
    paste_button = ToolbarButton("paste", "Paste", "Paste from clipboard", create_icon((150, 255, 150), "rect"))

    edit_group.items = [cut_button, copy_button, paste_button]
    horizontal_toolbar.add_group(edit_group)

    # Create vertical toolbar
    vertical_toolbar = ToolbarPanel(
        pygame.Rect(50, 150, 60, 300),
        manager,
        vertical_config
    )

    # Add tool buttons (checkable/exclusive group)
    tools_group = ToolbarGroup("tools", label="Tools", exclusive=True)

    select_tool = ToolbarButton("select", "", "Select tool", create_icon((255, 255, 255)), checkable=True, checked=True)
    brush_tool = ToolbarButton("brush", "", "Brush tool", create_icon((255, 100, 100)), checkable=True)
    eraser_tool = ToolbarButton("eraser", "", "Eraser tool", create_icon((200, 200, 200)), checkable=True)

    # Set group for exclusive behavior
    select_tool.group_id = "tools"
    brush_tool.group_id = "tools"
    eraser_tool.group_id = "tools"

    tools_group.items = [select_tool, brush_tool, eraser_tool]
    vertical_toolbar.add_group(tools_group)

    print("Toolbar Panel Demo")
    print("- Horizontal toolbar with file and edit groups")
    print("- Vertical toolbar with exclusive tool selection")
    print("- Hover effects and click callbacks")
    print("- Separators and grouping")

    running = True
    while running:
        time_delta = clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == UI_TOOLBAR_BUTTON_CLICKED:
                print(f"Toolbar button clicked: {event.button.text or event.button.id}")
            elif event.type == UI_TOOLBAR_BUTTON_HOVERED:
                print(f"Toolbar button hovered: {event.button.text or event.button.id}")
            elif event.type == UI_TOOLBAR_OVERFLOW_ACTIVATED:
                print(f"Overflow menu activated: {len(event.overflowing_buttons)} hidden buttons")

            manager.process_events(event)

        manager.update(time_delta)

        screen.fill((30, 30, 30))
        manager.draw_ui(screen)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()