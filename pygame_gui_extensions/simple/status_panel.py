import pygame
import pygame_gui
from pygame_gui.core import UIElement, ObjectID
from pygame_gui.core.interfaces import IContainerLikeInterface
from typing import List, Optional, Dict, Any, Union, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
import copy
import time

try:
    from pygame_gui.core.interfaces.gui_font_interface import IGUIFontInterface
except ImportError:
    IGUIFontInterface = None

STATUS_DEBUG = False

# Define custom pygame-gui events
UI_STATUS_CLICKED = pygame.USEREVENT + 320
UI_STATUS_DISMISSED = pygame.USEREVENT + 321
UI_STATUS_TIMEOUT = pygame.USEREVENT + 322
UI_STATUS_LEVEL_CHANGED = pygame.USEREVENT + 323
UI_STATUS_MESSAGE_CHANGED = pygame.USEREVENT + 324


class StatusLevel(Enum):
    """Status level/severity"""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    DEBUG = "debug"
    CUSTOM = "custom"


class StatusAnimationType(Enum):
    """Status animation types"""
    NONE = "none"
    FADE_IN = "fade_in"
    SLIDE_IN = "slide_in"
    BOUNCE = "bounce"
    PULSE = "pulse"


@dataclass
class StatusLayoutConfig:
    """Layout and spacing configuration for status panel"""
    # Content layout
    padding_left: int = 8
    padding_right: int = 8
    padding_top: int = 6
    padding_bottom: int = 6

    # Icon settings
    icon_size: Tuple[int, int] = (16, 16)
    icon_spacing: int = 6
    show_icon: bool = True

    # Text settings
    font_size: int = 12
    line_height: int = 16
    max_lines: int = 3

    # Border and background
    border_width: int = 1
    corner_radius: int = 4

    # Close/dismiss button
    close_button_size: int = 14
    close_button_margin: int = 4
    show_close_button: bool = True

    # Progress bar (for loading states)
    progress_bar_height: int = 3
    progress_bar_margin: int = 2
    show_progress_bar: bool = False

    # Shadow
    shadow_offset: Tuple[int, int] = (2, 2)
    shadow_blur: int = 4


@dataclass
class StatusInteractionConfig:
    """Interaction and timing configuration"""
    # Click behavior
    clickable: bool = True
    click_to_dismiss: bool = True
    click_sound: Optional[str] = None

    # Auto-dismiss behavior
    auto_dismiss: bool = True
    dismiss_timeout: Dict[StatusLevel, float] = field(default_factory=lambda: {
        StatusLevel.INFO: 3.0,
        StatusLevel.SUCCESS: 2.0,
        StatusLevel.WARNING: 5.0,
        StatusLevel.ERROR: 0.0,  # Don't auto-dismiss errors
        StatusLevel.DEBUG: 1.5,
        StatusLevel.CUSTOM: 3.0
    })

    # Animation timing
    animation_duration: float = 0.3
    animation_easing: str = "ease_out"

    # Hover behavior
    pause_on_hover: bool = True
    hover_highlight: bool = True


@dataclass
class StatusBehaviorConfig:
    """Behavior configuration for status panel"""
    # Visual behavior
    show_timestamp: bool = False
    show_level_indicator: bool = True
    animate_in: bool = True
    animate_out: bool = True

    # Text behavior
    word_wrap: bool = True
    truncate_long_text: bool = True
    show_full_text_on_hover: bool = True

    # Stacking behavior (for multiple status messages)
    stack_similar_messages: bool = True
    max_stack_count: int = 99

    # Persistence
    persist_errors: bool = True
    persist_warnings: bool = False
    log_all_messages: bool = True

    # Accessibility
    screen_reader_announce: bool = True
    high_contrast_mode: bool = False


@dataclass
class StatusConfig:
    """Complete configuration for the status panel"""
    # Sub-configurations
    layout: StatusLayoutConfig = field(default_factory=StatusLayoutConfig)
    interaction: StatusInteractionConfig = field(default_factory=StatusInteractionConfig)
    behavior: StatusBehaviorConfig = field(default_factory=StatusBehaviorConfig)

    # Default settings
    default_level: StatusLevel = StatusLevel.INFO
    default_animation: StatusAnimationType = StatusAnimationType.FADE_IN

    # Convenience properties
    @property
    def auto_dismiss(self) -> bool:
        return self.interaction.auto_dismiss

    @property
    def show_icon(self) -> bool:
        return self.layout.show_icon

    @property
    def clickable(self) -> bool:
        return self.interaction.clickable


@dataclass
class StatusMessage:
    """Represents a status message"""
    text: str
    level: StatusLevel = StatusLevel.INFO
    timestamp: float = field(default_factory=time.time)
    icon: Optional[pygame.Surface] = None
    progress: Optional[float] = None  # 0.0 to 1.0 for progress bar
    count: int = 1  # For stacked messages
    persistent: bool = False
    custom_timeout: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class StatusThemeManager:
    """Manages theming for the status panel"""

    def __init__(self, ui_manager: pygame_gui.UIManager, element_ids: List[str]):
        self.ui_manager = ui_manager
        self.element_ids = element_ids
        self.themed_colors = {}
        self.themed_fonts = {}
        self._update_theme_data()

    def _update_theme_data(self):
        """Update theme-dependent data with comprehensive fallbacks"""

        # Default color mappings by status level
        color_mappings = {
            # Info colors
            'info_bg': pygame.Color(45, 85, 125, 240),
            'info_border': pygame.Color(70, 110, 150),
            'info_text': pygame.Color(255, 255, 255),
            'info_icon': pygame.Color(100, 150, 255),

            # Success colors
            'success_bg': pygame.Color(45, 125, 85, 240),
            'success_border': pygame.Color(70, 150, 110),
            'success_text': pygame.Color(255, 255, 255),
            'success_icon': pygame.Color(100, 255, 150),

            # Warning colors
            'warning_bg': pygame.Color(125, 105, 45, 240),
            'warning_border': pygame.Color(150, 130, 70),
            'warning_text': pygame.Color(255, 255, 255),
            'warning_icon': pygame.Color(255, 200, 100),

            # Error colors
            'error_bg': pygame.Color(125, 45, 45, 240),
            'error_border': pygame.Color(150, 70, 70),
            'error_text': pygame.Color(255, 255, 255),
            'error_icon': pygame.Color(255, 100, 100),

            # Debug colors
            'debug_bg': pygame.Color(85, 45, 125, 240),
            'debug_border': pygame.Color(110, 70, 150),
            'debug_text': pygame.Color(255, 255, 255),
            'debug_icon': pygame.Color(200, 100, 255),

            # Custom/default colors
            'custom_bg': pygame.Color(60, 60, 60, 240),
            'custom_border': pygame.Color(100, 100, 100),
            'custom_text': pygame.Color(255, 255, 255),
            'custom_icon': pygame.Color(200, 200, 200),

            # Common colors
            'shadow': pygame.Color(0, 0, 0, 100),
            'close_button': pygame.Color(200, 200, 200),
            'close_button_hover': pygame.Color(255, 100, 100),
            'progress_bg': pygame.Color(100, 100, 100, 100),
            'progress_fg': pygame.Color(255, 255, 255, 200),
            'timestamp_text': pygame.Color(200, 200, 200),
            'stack_indicator': pygame.Color(255, 255, 100),
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
                    self.themed_fonts['default'] = pygame.font.SysFont('Arial', 12)
                except:
                    self.themed_fonts['default'] = pygame.font.Font(None, 12)

        except Exception as e:
            if STATUS_DEBUG:
                print(f"Error updating status theme: {e}")
            # Use all defaults
            self.themed_colors = color_mappings
            self.themed_fonts['default'] = pygame.font.Font(None, 12)

    def get_color(self, color_id: str, level: StatusLevel = StatusLevel.INFO) -> pygame.Color:
        """Get color for specific status level"""
        level_color_id = f"{level.value}_{color_id}"

        return self.themed_colors.get(level_color_id,
                                      self.themed_colors.get(color_id,
                                                             pygame.Color(255, 255, 255)))

    def get_font(self, font_size: int = 12) -> pygame.font.Font:
        """Get font with specified size"""
        font_key = f"font_{font_size}"

        if font_key not in self.themed_fonts:
            try:
                self.themed_fonts[font_key] = pygame.font.SysFont('Arial', font_size)
            except:
                self.themed_fonts[font_key] = pygame.font.Font(None, font_size)

        return self.themed_fonts[font_key]


class StatusPanel(UIElement):
    """Status display panel with comprehensive configuration and auto-dismiss"""

    def __init__(self, relative_rect: pygame.Rect,
                 manager: pygame_gui.UIManager,
                 message: Union[str, StatusMessage, None] = None,
                 level: StatusLevel = StatusLevel.INFO,
                 config: StatusConfig = None,
                 container: IContainerLikeInterface = None,
                 object_id: Union[ObjectID, str, None] = None,
                 anchors: Dict[str, str] = None):

        # Handle object_id properly
        if isinstance(object_id, ObjectID):
            self._object_id = object_id
        elif isinstance(object_id, str):
            self._object_id = ObjectID(object_id=object_id, class_id=None)
        else:
            self._object_id = ObjectID(object_id='#status_panel', class_id=None)

        super().__init__(relative_rect, manager, container,
                         starting_height=1, layer_thickness=1,
                         anchors=anchors, object_id=self._object_id)

        self.config = config or StatusConfig()

        # Create theme manager
        element_ids = ['status_panel']
        if hasattr(self, 'object_ids') and self.object_ids:
            element_ids.extend(self.object_ids)
        self.theme_manager = StatusThemeManager(manager, element_ids)

        # Status message
        if isinstance(message, StatusMessage):
            self.message = message
        elif message:
            self.message = StatusMessage(text=message, level=level)
        else:
            self.message = StatusMessage(text="", level=level)

        # State
        self.is_hovered = False
        self.is_dismissing = False
        self.is_dismissed = False

        # Timing
        self.creation_time = time.time()
        self.last_update_time = time.time()
        self.dismiss_time = 0.0
        self.animation_time = 0.0

        # Animation state
        self.animation_type = self.config.default_animation
        self.animation_progress = 0.0
        self.target_alpha = 255

        # Layout cache
        self._text_lines: List[str] = []
        self._icon_rect = pygame.Rect(0, 0, 0, 0)
        self._text_rect = pygame.Rect(0, 0, 0, 0)
        self._close_button_rect = pygame.Rect(0, 0, 0, 0)
        self._progress_bar_rect = pygame.Rect(0, 0, 0, 0)

        # Message log (for debugging/persistence)
        self.message_log: List[StatusMessage] = []

        # Create the image surface
        self.image = pygame.Surface(self.rect.size, pygame.SRCALPHA).convert_alpha()

        # Initialize
        self._calculate_layout()
        self._start_animation()
        self.rebuild_image()

        # Start auto-dismiss timer if enabled
        self._schedule_auto_dismiss()

    # Public API
    def set_message(self, message: Union[str, StatusMessage], level: StatusLevel = None):
        """Set a new status message"""
        if isinstance(message, StatusMessage):
            self.message = message
        else:
            self.message = StatusMessage(
                text=message,
                level=level or self.message.level
            )

        # Log message if enabled
        if self.config.behavior.log_all_messages:
            self.message_log.append(copy.deepcopy(self.message))

        # Reset timing
        self.creation_time = time.time()
        self.is_dismissing = False

        # Recalculate layout and restart animation
        self._calculate_layout()
        self._start_animation()
        self.rebuild_image()

        # Reschedule auto-dismiss
        self._schedule_auto_dismiss()

        # Fire event
        event_data = {
            'message': self.message.text,
            'level': self.message.level,
            'ui_element': self
        }
        pygame.event.post(pygame.event.Event(UI_STATUS_MESSAGE_CHANGED, event_data))

    def set_level(self, level: StatusLevel):
        """Set the status level"""
        if level != self.message.level:
            self.message.level = level
            self.rebuild_image()

            # Reschedule auto-dismiss with new level
            self._schedule_auto_dismiss()

            # Fire event
            event_data = {
                'level': level,
                'ui_element': self
            }
            pygame.event.post(pygame.event.Event(UI_STATUS_LEVEL_CHANGED, event_data))

    def set_progress(self, progress: Optional[float]):
        """Set progress value (0.0 to 1.0) or None to hide"""
        self.message.progress = progress
        if progress is not None:
            self.config.layout.show_progress_bar = True
        self.rebuild_image()

    def dismiss(self, animate: bool = True):
        """Manually dismiss the status"""
        if self.is_dismissed:
            return

        self.is_dismissing = True

        if animate and self.config.behavior.animate_out:
            self._start_dismiss_animation()
        else:
            self._complete_dismiss()

    def add_to_stack(self, count: int = 1):
        """Add to the stack count for similar messages"""
        self.message.count += count
        self.rebuild_image()

    # Internal methods
    def _calculate_layout(self):
        """Calculate layout rectangles"""
        # Available content area
        content_x = self.config.layout.padding_left
        content_y = self.config.layout.padding_top
        content_w = (self.rect.width -
                     self.config.layout.padding_left -
                     self.config.layout.padding_right)
        content_h = (self.rect.height -
                     self.config.layout.padding_top -
                     self.config.layout.padding_bottom)

        # Close button
        if self.config.layout.show_close_button:
            close_size = self.config.layout.close_button_size
            close_margin = self.config.layout.close_button_margin
            self._close_button_rect = pygame.Rect(
                self.rect.width - close_size - close_margin,
                close_margin,
                close_size,
                close_size
            )
            content_w -= close_size + close_margin
        else:
            self._close_button_rect = pygame.Rect(0, 0, 0, 0)

        # Icon
        if self.config.layout.show_icon:
            icon_w, icon_h = self.config.layout.icon_size
            self._icon_rect = pygame.Rect(
                content_x,
                content_y + (content_h - icon_h) // 2,
                icon_w,
                icon_h
            )
            text_x = content_x + icon_w + self.config.layout.icon_spacing
            text_w = content_w - icon_w - self.config.layout.icon_spacing
        else:
            self._icon_rect = pygame.Rect(0, 0, 0, 0)
            text_x = content_x
            text_w = content_w

        # Progress bar
        if self.config.layout.show_progress_bar:
            progress_h = self.config.layout.progress_bar_height
            progress_margin = self.config.layout.progress_bar_margin
            self._progress_bar_rect = pygame.Rect(
                content_x,
                self.rect.height - progress_h - progress_margin,
                content_w,
                progress_h
            )
            content_h -= progress_h + progress_margin
        else:
            self._progress_bar_rect = pygame.Rect(0, 0, 0, 0)

        # Text area
        self._text_rect = pygame.Rect(text_x, content_y, text_w, content_h)

        # Process text into lines
        self._process_text()

    def _process_text(self):
        """Process text into lines for display"""
        if not self.message.text:
            self._text_lines = []
            return

        font = self.theme_manager.get_font(self.config.layout.font_size)

        # Split into paragraphs first
        paragraphs = self.message.text.split('\n')
        self._text_lines = []

        for paragraph in paragraphs:
            if not paragraph.strip():
                self._text_lines.append("")
                continue

            if self.config.behavior.word_wrap:
                # Word wrap within available width
                words = paragraph.split(' ')
                current_line = ""

                for word in words:
                    test_line = f"{current_line} {word}".strip()
                    if font.size(test_line)[0] <= self._text_rect.width:
                        current_line = test_line
                    else:
                        if current_line:
                            self._text_lines.append(current_line)
                            current_line = word
                        else:
                            # Word too long, force break
                            self._text_lines.append(word)

                if current_line:
                    self._text_lines.append(current_line)
            else:
                # No wrapping, just add the line
                if self.config.behavior.truncate_long_text:
                    # Truncate with ellipsis if too long
                    if font.size(paragraph)[0] > self._text_rect.width:
                        # Binary search for fitting text
                        left, right = 0, len(paragraph)
                        ellipsis = "..."
                        ellipsis_width = font.size(ellipsis)[0]
                        available_width = self._text_rect.width - ellipsis_width

                        while left < right:
                            mid = (left + right + 1) // 2
                            if font.size(paragraph[:mid])[0] <= available_width:
                                left = mid
                            else:
                                right = mid - 1

                        paragraph = paragraph[:left] + ellipsis

                self._text_lines.append(paragraph)

        # Limit to max lines
        if len(self._text_lines) > self.config.layout.max_lines:
            self._text_lines = self._text_lines[:self.config.layout.max_lines]
            if self._text_lines:
                self._text_lines[-1] += "..."

    def _start_animation(self):
        """Start entrance animation"""
        if not self.config.behavior.animate_in:
            self.animation_progress = 1.0
            return

        self.animation_time = 0.0
        self.animation_progress = 0.0
        self.target_alpha = 255

    def _start_dismiss_animation(self):
        """Start dismiss animation"""
        self.animation_time = 0.0
        self.animation_progress = 1.0
        self.target_alpha = 0

    def _schedule_auto_dismiss(self):
        """Schedule auto-dismiss based on level and configuration"""
        if not self.config.interaction.auto_dismiss:
            return

        # Check if this level should persist
        if (self.message.level == StatusLevel.ERROR and self.config.behavior.persist_errors):
            return
        if (self.message.level == StatusLevel.WARNING and self.config.behavior.persist_warnings):
            return
        if self.message.persistent:
            return

        # Get timeout for this level
        timeout = self.message.custom_timeout
        if timeout is None:
            timeout = self.config.interaction.dismiss_timeout.get(self.message.level, 3.0)

        if timeout > 0:
            self.dismiss_time = self.creation_time + timeout

    def _complete_dismiss(self):
        """Complete the dismiss process"""
        self.is_dismissed = True

        # Fire dismiss event
        event_data = {
            'message': self.message.text,
            'level': self.message.level,
            'ui_element': self
        }
        pygame.event.post(pygame.event.Event(UI_STATUS_DISMISSED, event_data))

        # Kill the element
        self.kill()

    def _create_default_icon(self) -> pygame.Surface:
        """Create default icon for the current status level"""
        icon_w, icon_h = self.config.layout.icon_size
        icon_surface = pygame.Surface((icon_w, icon_h), pygame.SRCALPHA).convert_alpha()

        icon_color = self.theme_manager.get_color('icon', self.message.level)
        center = (icon_w // 2, icon_h // 2)
        radius = min(icon_w, icon_h) // 3

        if self.message.level == StatusLevel.INFO:
            # Info icon - circle with 'i'
            pygame.draw.circle(icon_surface, icon_color, center, radius, 2)
            font = pygame.font.Font(None, max(12, icon_h // 2))
            text = font.render('i', True, icon_color)
            text_rect = text.get_rect(center=center)
            icon_surface.blit(text, text_rect)

        elif self.message.level == StatusLevel.SUCCESS:
            # Success icon - checkmark
            pygame.draw.circle(icon_surface, icon_color, center, radius, 2)
            # Simple checkmark
            check_points = [
                (center[0] - radius // 2, center[1]),
                (center[0] - radius // 4, center[1] + radius // 2),
                (center[0] + radius // 2, center[1] - radius // 2)
            ]
            pygame.draw.lines(icon_surface, icon_color, False, check_points, 2)

        elif self.message.level == StatusLevel.WARNING:
            # Warning icon - triangle with exclamation
            points = [
                (center[0], center[1] - radius),
                (center[0] - radius, center[1] + radius),
                (center[0] + radius, center[1] + radius)
            ]
            pygame.draw.polygon(icon_surface, icon_color, points, 2)
            font = pygame.font.Font(None, max(12, icon_h // 2))
            text = font.render('!', True, icon_color)
            text_rect = text.get_rect(center=center)
            icon_surface.blit(text, text_rect)

        elif self.message.level == StatusLevel.ERROR:
            # Error icon - circle with X
            pygame.draw.circle(icon_surface, icon_color, center, radius, 2)
            pygame.draw.line(icon_surface, icon_color,
                             (center[0] - radius // 2, center[1] - radius // 2),
                             (center[0] + radius // 2, center[1] + radius // 2), 2)
            pygame.draw.line(icon_surface, icon_color,
                             (center[0] + radius // 2, center[1] - radius // 2),
                             (center[0] - radius // 2, center[1] + radius // 2), 2)

        elif self.message.level == StatusLevel.DEBUG:
            # Debug icon - gear/cog
            pygame.draw.circle(icon_surface, icon_color, center, radius, 2)
            # Simple gear teeth
            for angle in range(0, 360, 45):
                import math
                x = center[0] + (radius + 2) * math.cos(math.radians(angle))
                y = center[1] + (radius + 2) * math.sin(math.radians(angle))
                pygame.draw.circle(icon_surface, icon_color, (int(x), int(y)), 1)

        else:  # CUSTOM
            # Custom icon - simple circle
            pygame.draw.circle(icon_surface, icon_color, center, radius, 2)

        return icon_surface

    def rebuild_image(self):
        """Rebuild the panel image"""
        self.image.fill(pygame.Color(0, 0, 0, 0))  # Transparent

        # Calculate current alpha based on animation
        current_alpha = int(self.target_alpha * self.animation_progress)
        if current_alpha <= 0:
            return

        # Get colors for current level
        bg_color = self.theme_manager.get_color('bg', self.message.level)
        border_color = self.theme_manager.get_color('border', self.message.level)
        text_color = self.theme_manager.get_color('text', self.message.level)

        # Apply alpha
        bg_color = pygame.Color(bg_color.r, bg_color.g, bg_color.b,
                                min(bg_color.a, current_alpha))
        border_color = pygame.Color(border_color.r, border_color.g, border_color.b,
                                    min(border_color.a, current_alpha))
        text_color = pygame.Color(text_color.r, text_color.g, text_color.b,
                                  min(text_color.a, current_alpha))

        # Draw shadow
        shadow_color = self.theme_manager.get_color('shadow')
        shadow_alpha = min(shadow_color.a, current_alpha // 2)
        shadow_color = pygame.Color(shadow_color.r, shadow_color.g, shadow_color.b, shadow_alpha)

        shadow_rect = self.rect.copy()
        shadow_rect.x += self.config.layout.shadow_offset[0]
        shadow_rect.y += self.config.layout.shadow_offset[1]

        if self.config.layout.corner_radius > 0:
            pygame.draw.rect(self.image, shadow_color, shadow_rect,
                             border_radius=self.config.layout.corner_radius)
        else:
            pygame.draw.rect(self.image, shadow_color, shadow_rect)

        # Draw background
        if self.config.layout.corner_radius > 0:
            pygame.draw.rect(self.image, bg_color, self.rect,
                             border_radius=self.config.layout.corner_radius)
        else:
            pygame.draw.rect(self.image, bg_color, self.rect)

        # Draw border
        if self.config.layout.border_width > 0:
            if self.config.layout.corner_radius > 0:
                pygame.draw.rect(self.image, border_color, self.rect,
                                 self.config.layout.border_width,
                                 border_radius=self.config.layout.corner_radius)
            else:
                pygame.draw.rect(self.image, border_color, self.rect,
                                 self.config.layout.border_width)

        # Draw icon
        if self.config.layout.show_icon and not self._icon_rect.width == 0:
            icon = self.message.icon or self._create_default_icon()
            if icon:
                # Scale icon if needed
                if icon.get_size() != self.config.layout.icon_size:
                    icon = pygame.transform.scale(icon, self.config.layout.icon_size)

                # Apply alpha to icon
                if current_alpha < 255:
                    icon = icon.copy()
                    icon.set_alpha(current_alpha)

                self.image.blit(icon, self._icon_rect)

        # Draw text
        if self._text_lines:
            font = self.theme_manager.get_font(self.config.layout.font_size)
            line_height = self.config.layout.line_height

            for i, line in enumerate(self._text_lines):
                if not line:
                    continue

                y = self._text_rect.y + i * line_height
                if y + line_height > self._text_rect.bottom:
                    break

                try:
                    text_surface = font.render(line, True, text_color)
                    if current_alpha < 255:
                        text_surface.set_alpha(current_alpha)
                    self.image.blit(text_surface, (self._text_rect.x, y))
                except:
                    continue

        # Draw stack count indicator
        if self.message.count > 1:
            stack_color = self.theme_manager.get_color('stack_indicator')
            stack_alpha = min(stack_color.a, current_alpha)
            stack_color = pygame.Color(stack_color.r, stack_color.g, stack_color.b, stack_alpha)

            # Draw small circle with count
            stack_radius = 8
            stack_center = (self.rect.width - stack_radius - 2, stack_radius + 2)

            pygame.draw.circle(self.image, stack_color, stack_center, stack_radius)

            # Draw count text
            font = pygame.font.Font(None, 14)
            count_text = str(min(self.message.count, 99))
            text_surface = font.render(count_text, True, pygame.Color(0, 0, 0))
            if current_alpha < 255:
                text_surface.set_alpha(current_alpha)

            text_rect = text_surface.get_rect(center=stack_center)
            self.image.blit(text_surface, text_rect)

        # Draw close button
        if (self.config.layout.show_close_button and
                not self._close_button_rect.width == 0):
            close_color = self.theme_manager.get_color('close_button_hover' if self.is_hovered
                                                       else 'close_button')
            close_alpha = min(close_color.a, current_alpha)
            close_color = pygame.Color(close_color.r, close_color.g, close_color.b, close_alpha)

            # Draw X
            center = self._close_button_rect.center
            size = self._close_button_rect.width // 3
            pygame.draw.line(self.image, close_color,
                             (center[0] - size, center[1] - size),
                             (center[0] + size, center[1] + size), 2)
            pygame.draw.line(self.image, close_color,
                             (center[0] + size, center[1] - size),
                             (center[0] - size, center[1] + size), 2)

        # Draw progress bar
        if (self.config.layout.show_progress_bar and
                self.message.progress is not None and
                not self._progress_bar_rect.width == 0):

            progress_bg = self.theme_manager.get_color('progress_bg')
            progress_fg = self.theme_manager.get_color('progress_fg')

            # Background
            pygame.draw.rect(self.image, progress_bg, self._progress_bar_rect)

            # Progress
            if self.message.progress > 0:
                progress_width = int(self._progress_bar_rect.width * self.message.progress)
                progress_rect = pygame.Rect(
                    self._progress_bar_rect.x,
                    self._progress_bar_rect.y,
                    progress_width,
                    self._progress_bar_rect.height
                )
                pygame.draw.rect(self.image, progress_fg, progress_rect)

        # Draw timestamp if enabled
        if self.config.behavior.show_timestamp:
            timestamp_color = self.theme_manager.get_color('timestamp_text')
            timestamp_alpha = min(timestamp_color.a, current_alpha)
            timestamp_color = pygame.Color(timestamp_color.r, timestamp_color.g, timestamp_color.b,
                                           timestamp_alpha)

            import datetime
            timestamp_str = datetime.datetime.fromtimestamp(self.message.timestamp).strftime("%H:%M:%S")
            font = pygame.font.Font(None, 10)

            text_surface = font.render(timestamp_str, True, timestamp_color)
            if current_alpha < 255:
                text_surface.set_alpha(current_alpha)

            # Position in bottom right
            text_pos = (
                self.rect.width - text_surface.get_width() - 4,
                self.rect.height - text_surface.get_height() - 2
            )
            self.image.blit(text_surface, text_pos)

    def process_event(self, event: pygame.event.Event) -> bool:
        """Process events"""
        consumed = False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos) and self.config.interaction.clickable:
                # Check close button first
                if (self.config.layout.show_close_button and
                        self._close_button_rect.collidepoint(event.pos)):
                    self.dismiss()
                    consumed = True
                elif self.config.interaction.click_to_dismiss:
                    self.dismiss()
                    consumed = True
                else:
                    # Fire click event
                    event_data = {'ui_element': self}
                    pygame.event.post(pygame.event.Event(UI_STATUS_CLICKED, event_data))
                    consumed = True

        elif event.type == pygame.MOUSEMOTION:
            was_hovered = self.is_hovered
            self.is_hovered = self.rect.collidepoint(event.pos)

            if was_hovered != self.is_hovered:
                if self.config.interaction.hover_highlight:
                    self.rebuild_image()

        return consumed

    def update(self, time_delta: float):
        """Update the panel"""
        super().update(time_delta)

        current_time = time.time()

        # Update animation
        if self.animation_progress < 1.0 and not self.is_dismissing:
            self.animation_time += time_delta
            progress = min(1.0, self.animation_time / self.config.interaction.animation_duration)

            # Apply easing (simple ease-out)
            if self.config.interaction.animation_easing == "ease_out":
                progress = 1 - (1 - progress) ** 2

            self.animation_progress = progress
            self.rebuild_image()

        elif self.animation_progress > 0.0 and self.is_dismissing:
            self.animation_time += time_delta
            progress = max(0.0, 1.0 - (self.animation_time / self.config.interaction.animation_duration))

            # Apply easing
            if self.config.interaction.animation_easing == "ease_out":
                progress = 1 - (1 - progress) ** 2

            self.animation_progress = progress
            self.rebuild_image()

            if progress <= 0.0:
                self._complete_dismiss()

        # Check auto-dismiss
        if (not self.is_dismissing and
                not self.is_dismissed and
                self.dismiss_time > 0 and
                current_time >= self.dismiss_time):

            # Don't dismiss if hovered and pause_on_hover is enabled
            if not (self.is_hovered and self.config.interaction.pause_on_hover):
                # Fire timeout event
                event_data = {'ui_element': self}
                pygame.event.post(pygame.event.Event(UI_STATUS_TIMEOUT, event_data))

                self.dismiss()

# Example usage and theme
STATUS_THEME = {
    'status_panel': {
        'colours': {
            # Info colors
            'info_bg': '#2D557D',
            'info_border': '#466E96',
            'info_text': '#FFFFFF',
            'info_icon': '#64C8FF',

            # Success colors
            'success_bg': '#2D7D55',
            'success_border': '#469655',
            'success_text': '#FFFFFF',
            'success_icon': '#64FF96',

            # Warning colors
            'warning_bg': '#7D692D',
            'warning_border': '#968246',
            'warning_text': '#FFFFFF',
            'warning_icon': '#FFC864',

            # Error colors
            'error_bg': '#7D2D2D',
            'error_border': '#964646',
            'error_text': '#FFFFFF',
            'error_icon': '#FF6464',

            # Debug colors
            'debug_bg': '#552D7D',
            'debug_border': '#6E4696',
            'debug_text': '#FFFFFF',
            'debug_icon': '#C864FF',

            # Custom colors
            'custom_bg': '#3C3C3C',
            'custom_border': '#646464',
            'custom_text': '#FFFFFF',
            'custom_icon': '#C8C8C8',

            # Common colors
            'shadow': '#00000064',
            'close_button': '#C8C8C8',
            'close_button_hover': '#FF6464',
            'progress_bg': '#64646464',
            'progress_fg': '#FFFFFFC8',
            'timestamp_text': '#C8C8C8',
            'stack_indicator': '#FFFF64',
        }
    }
}

def main():
    """Example demonstration of the Status Panel"""
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("Status Panel Demo")
    clock = pygame.time.Clock()

    # Create manager with theme
    manager = pygame_gui.UIManager((800, 600), STATUS_THEME)

    # Create different status configurations
    basic_config = StatusConfig()

    persistent_config = StatusConfig()
    persistent_config.interaction.auto_dismiss = False
    persistent_config.layout.show_close_button = True

    progress_config = StatusConfig()
    progress_config.layout.show_progress_bar = True
    progress_config.interaction.auto_dismiss = False

    # Example status panels
    statuses = []

    # Info status
    info_status = StatusPanel(
        pygame.Rect(50, 50, 300, 60),
        manager,
        "This is an information message",
        StatusLevel.INFO,
        basic_config
    )
    statuses.append(info_status)

    # Success status
    success_status = StatusPanel(
        pygame.Rect(50, 120, 300, 60),
        manager,
        "Operation completed successfully!",
        StatusLevel.SUCCESS,
        basic_config
    )
    statuses.append(success_status)

    # Warning status
    warning_status = StatusPanel(
        pygame.Rect(50, 190, 300, 60),
        manager,
        "This is a warning message that you should pay attention to",
        StatusLevel.WARNING,
        basic_config
    )
    statuses.append(warning_status)

    # Error status (persistent)
    error_status = StatusPanel(
        pygame.Rect(50, 260, 300, 60),
        manager,
        "An error occurred and needs your attention",
        StatusLevel.ERROR,
        persistent_config
    )
    statuses.append(error_status)

    # Progress status
    progress_status = StatusPanel(
        pygame.Rect(50, 330, 300, 80),
        manager,
        "Loading... Please wait",
        StatusLevel.INFO,
        progress_config
    )
    progress_status.set_progress(0.0)
    statuses.append(progress_status)

    print("Status Panel Demo")
    print("- Different status levels with auto-dismiss")
    print("- Progress indicators")
    print("- Persistent error messages")
    print("- Click to dismiss or use close button")

    progress_value = 0.0
    running = True

    while running:
        time_delta = clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == UI_STATUS_CLICKED:
                print(f"Status clicked: {event.ui_element.message.text}")
            elif event.type == UI_STATUS_DISMISSED:
                print(f"Status dismissed: {event.ui_element.message.text}")
            elif event.type == UI_STATUS_TIMEOUT:
                print(f"Status timed out: {event.ui_element.message.text}")
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    # Add a new random status
                    import random
                    messages = [
                        ("New message received", StatusLevel.INFO),
                        ("File saved successfully", StatusLevel.SUCCESS),
                        ("Low disk space warning", StatusLevel.WARNING),
                        ("Connection failed", StatusLevel.ERROR),
                        ("Debug: Variable updated", StatusLevel.DEBUG)
                    ]
                    msg, level = random.choice(messages)

                    new_status = StatusPanel(
                        pygame.Rect(400, 50 + len(statuses) * 70, 300, 60),
                        manager,
                        msg,
                        level,
                        basic_config
                    )
                    statuses.append(new_status)

            manager.process_events(event)

        # Update progress
        if progress_status.alive():
            progress_value += time_delta * 0.3  # 30% per second
            if progress_value >= 1.0:
                progress_value = 0.0
            progress_status.set_progress(progress_value)

        manager.update(time_delta)

        screen.fill((30, 30, 30))
        manager.draw_ui(screen)

        # Instructions
        font = pygame.font.Font(None, 24)
        text = font.render("Press SPACE to add random status messages", True, (255, 255, 255))
        screen.blit(text, (50, 500))

        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()