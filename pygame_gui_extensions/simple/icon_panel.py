import pygame
import pygame_gui
from pygame_gui.core import UIElement, ObjectID
from pygame_gui.core.interfaces import IContainerLikeInterface
from typing import List, Optional, Dict, Any, Union, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
import copy
from pathlib import Path

try:
    from pygame_gui.core.interfaces.gui_font_interface import IGUIFontInterface
except ImportError:
    IGUIFontInterface = None

ICON_DEBUG = False

# Define custom pygame-gui events
UI_ICON_CLICKED = pygame.USEREVENT + 310
UI_ICON_DOUBLE_CLICKED = pygame.USEREVENT + 311
UI_ICON_HOVERED = pygame.USEREVENT + 312
UI_ICON_LOADED = pygame.USEREVENT + 313
UI_ICON_LOAD_FAILED = pygame.USEREVENT + 314


class IconState(Enum):
    """Icon visual states"""
    NORMAL = "normal"
    HOVERED = "hovered"
    PRESSED = "pressed"
    DISABLED = "disabled"
    SELECTED = "selected"
    LOADING = "loading"


class IconScaleMode(Enum):
    """Icon scaling modes"""
    STRETCH = "stretch"  # Stretch to fit exactly
    SCALE_KEEP_ASPECT = "scale_keep_aspect"  # Scale maintaining aspect ratio
    CENTER = "center"  # Center without scaling
    TILE = "tile"  # Tile the icon


class IconFallbackMode(Enum):
    """Fallback icon generation modes"""
    GEOMETRIC = "geometric"  # Simple geometric shapes
    INITIALS = "initials"  # Text initials
    PLACEHOLDER = "placeholder"  # Standard placeholder
    NONE = "none"  # No fallback


@dataclass
class IconLayoutConfig:
    """Layout and spacing configuration for icon panel"""
    # Icon sizing
    icon_size: Tuple[int, int] = (32, 32)
    padding: int = 4

    # Border and background
    border_width: int = 1
    corner_radius: int = 2
    background_alpha: int = 255

    # Loading indicator
    loading_indicator_size: int = 16
    loading_ring_width: int = 2

    # Fallback icon settings
    fallback_icon_size: int = 16
    fallback_text_size: int = 12
    fallback_shape_size: int = 8

    # Shadow and highlight
    shadow_offset: Tuple[int, int] = (1, 1)
    shadow_alpha: int = 80
    highlight_width: int = 1


@dataclass
class IconInteractionConfig:
    """Interaction and timing configuration"""
    # Click behavior
    clickable: bool = True
    double_click_time: int = 500  # milliseconds
    click_sound: Optional[str] = None

    # Hover behavior
    hoverable: bool = True
    hover_delay: int = 100  # milliseconds
    hover_sound: Optional[str] = None
    hover_scale: float = 1.1  # Scale factor on hover

    # Selection behavior
    selectable: bool = False
    toggle_selection: bool = False

    # Animation timing
    animation_duration: float = 0.2  # seconds
    animation_easing: str = "ease_out"


@dataclass
class IconBehaviorConfig:
    """Behavior configuration for icon panel"""
    # Loading behavior
    show_loading_indicator: bool = True
    animate_loading: bool = True
    loading_timeout: float = 10.0  # seconds

    # Fallback behavior
    fallback_mode: IconFallbackMode = IconFallbackMode.GEOMETRIC
    show_fallback_on_error: bool = True
    cache_fallback_icons: bool = True

    # Visual behavior
    show_background: bool = False
    show_border: bool = False
    show_shadow: bool = False
    show_highlight_on_hover: bool = True
    animate_state_changes: bool = True

    # Performance
    cache_scaled_icons: bool = True
    lazy_load: bool = False
    preload_hover_state: bool = False


@dataclass
class IconConfig:
    """Complete configuration for the icon panel"""
    # Sub-configurations
    layout: IconLayoutConfig = field(default_factory=IconLayoutConfig)
    interaction: IconInteractionConfig = field(default_factory=IconInteractionConfig)
    behavior: IconBehaviorConfig = field(default_factory=IconBehaviorConfig)

    # Default settings
    default_scale_mode: IconScaleMode = IconScaleMode.SCALE_KEEP_ASPECT
    default_fallback_text: str = "?"

    # Convenience properties
    @property
    def icon_size(self) -> Tuple[int, int]:
        return self.layout.icon_size

    @property
    def clickable(self) -> bool:
        return self.interaction.clickable

    @property
    def cache_icons(self) -> bool:
        return self.behavior.cache_scaled_icons


class IconCache:
    """Icon caching system"""

    def __init__(self, max_size: int = 100):
        self.cache: Dict[str, pygame.Surface] = {}
        self.max_size = max_size
        self.access_order: List[str] = []

    def get(self, key: str) -> Optional[pygame.Surface]:
        """Get cached icon"""
        if key in self.cache:
            # Move to end (most recently used)
            self.access_order.remove(key)
            self.access_order.append(key)
            return self.cache[key]
        return None

    def put(self, key: str, surface: pygame.Surface):
        """Cache an icon surface"""
        if key in self.cache:
            # Update existing
            self.cache[key] = surface
            self.access_order.remove(key)
            self.access_order.append(key)
        else:
            # Add new
            if len(self.cache) >= self.max_size:
                # Remove least recently used
                lru_key = self.access_order.pop(0)
                del self.cache[lru_key]

            self.cache[key] = surface
            self.access_order.append(key)

    def clear(self):
        """Clear the cache"""
        self.cache.clear()
        self.access_order.clear()


class IconThemeManager:
    """Manages theming for the icon panel"""

    def __init__(self, ui_manager: pygame_gui.UIManager, element_ids: List[str]):
        self.ui_manager = ui_manager
        self.element_ids = element_ids
        self.themed_colors = {}
        self._update_theme_data()

    def _update_theme_data(self):
        """Update theme-dependent data with comprehensive fallbacks"""

        # Default color mappings
        color_mappings = {
            'normal_bg': pygame.Color(0, 0, 0, 0),  # Transparent
            'hovered_bg': pygame.Color(60, 60, 60, 128),
            'pressed_bg': pygame.Color(80, 80, 80, 128),
            'disabled_bg': pygame.Color(40, 40, 40, 128),
            'selected_bg': pygame.Color(70, 130, 180, 128),
            'loading_bg': pygame.Color(50, 50, 50, 128),
            'normal_border': pygame.Color(100, 100, 100),
            'hovered_border': pygame.Color(120, 120, 120),
            'pressed_border': pygame.Color(140, 140, 140),
            'disabled_border': pygame.Color(80, 80, 80),
            'selected_border': pygame.Color(120, 160, 255),
            'loading_border': pygame.Color(100, 200, 100),
            'shadow': pygame.Color(0, 0, 0, 60),
            'highlight': pygame.Color(255, 255, 255, 100),
            'loading_indicator': pygame.Color(100, 200, 100),
            'fallback_bg': pygame.Color(60, 60, 60),
            'fallback_fg': pygame.Color(200, 200, 200),
            'error_bg': pygame.Color(80, 40, 40),
            'error_fg': pygame.Color(255, 150, 150),
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

        except Exception as e:
            if ICON_DEBUG:
                print(f"Error updating icon theme: {e}")
            # Use all defaults
            self.themed_colors = color_mappings

    def get_color(self, color_id: str, state: IconState = IconState.NORMAL) -> pygame.Color:
        """Get color for specific state"""
        state_suffix = f"_{state.value}" if state != IconState.NORMAL else ""
        full_color_id = f"{color_id}{state_suffix}"

        return self.themed_colors.get(full_color_id,
                                      self.themed_colors.get(color_id,
                                                             pygame.Color(255, 255, 255)))


class IconPanel(UIElement):
    """Icon display panel with comprehensive state management and configuration"""

    # Global icon cache
    _global_cache = IconCache(200)

    def __init__(self, relative_rect: pygame.Rect,
                 manager: pygame_gui.UIManager,
                 icon_path: Union[str, Path, None] = None,
                 icon_surface: Optional[pygame.Surface] = None,
                 config: IconConfig = None,
                 container: IContainerLikeInterface = None,
                 object_id: Union[ObjectID, str, None] = None,
                 anchors: Dict[str, str] = None):

        # Handle object_id properly
        if isinstance(object_id, ObjectID):
            self._object_id = object_id
        elif isinstance(object_id, str):
            self._object_id = ObjectID(object_id=object_id, class_id=None)
        else:
            self._object_id = ObjectID(object_id='#icon_panel', class_id=None)

        super().__init__(relative_rect, manager, container,
                         starting_height=1, layer_thickness=1,
                         anchors=anchors, object_id=self._object_id)

        self.config = config or IconConfig()

        # Create theme manager
        element_ids = ['icon_panel']
        if hasattr(self, 'object_ids') and self.object_ids:
            element_ids.extend(self.object_ids)
        self.theme_manager = IconThemeManager(manager, element_ids)

        # Icon data
        self.icon_path = Path(icon_path) if icon_path else None
        self._original_icon = icon_surface
        self._scaled_icon = None
        self._fallback_icon = None

        # State
        self.state = IconState.NORMAL
        self.scale_mode = self.config.default_scale_mode

        # Interaction state
        self.is_hovered = False
        self.is_pressed = False
        self.is_selected = False
        self.is_loading = False
        self.load_failed = False

        # Animation state
        self.animation_time = 0.0
        self.animation_start_time = 0.0
        self.animation_from_scale = 1.0
        self.animation_to_scale = 1.0

        # Loading state
        self.loading_start_time = 0.0
        self.loading_angle = 0.0

        # Timing
        self.last_click_time = 0

        # Create the image surface
        self.image = pygame.Surface(self.rect.size, pygame.SRCALPHA).convert_alpha()

        # Initialize
        self._load_icon()
        self.rebuild_image()

    # Public API
    def set_icon(self, icon_path: Union[str, Path, None] = None,
                 icon_surface: Optional[pygame.Surface] = None):
        """Set a new icon"""
        self.icon_path = Path(icon_path) if icon_path else None
        self._original_icon = icon_surface
        self._scaled_icon = None
        self.load_failed = False
        self._load_icon()
        self.rebuild_image()

    def set_state(self, state: IconState):
        """Set the icon state"""
        if state != self.state:
            old_state = self.state
            self.state = state

            # Handle animations
            if self.config.behavior.animate_state_changes:
                if state == IconState.HOVERED and self.config.interaction.hover_scale != 1.0:
                    self._start_scale_animation(1.0, self.config.interaction.hover_scale)
                elif old_state == IconState.HOVERED and state == IconState.NORMAL:
                    self._start_scale_animation(self.config.interaction.hover_scale, 1.0)

            self.rebuild_image()

    def set_scale_mode(self, scale_mode: IconScaleMode):
        """Set the icon scaling mode"""
        if scale_mode != self.scale_mode:
            self.scale_mode = scale_mode
            self._scaled_icon = None  # Force rescale
            self.rebuild_image()

    # Internal methods
    def _load_icon(self):
        """Load the icon from path or use provided surface"""
        self.is_loading = True
        self.loading_start_time = pygame.time.get_ticks() / 1000.0

        try:
            if self._original_icon:
                # Use provided surface
                self.is_loading = False
                self._scale_icon()
            elif self.icon_path and self.icon_path.exists():
                # Load from file
                try:
                    self._original_icon = pygame.image.load(str(self.icon_path)).convert_alpha()
                    self.is_loading = False
                    self._scale_icon()

                    # Fire loaded event
                    event_data = {
                        'icon_path': str(self.icon_path),
                        'ui_element': self
                    }
                    pygame.event.post(pygame.event.Event(UI_ICON_LOADED, event_data))

                except Exception as e:
                    if ICON_DEBUG:
                        print(f"Error loading icon {self.icon_path}: {e}")
                    self._handle_load_failure()
            else:
                # No valid icon source
                self.is_loading = False
                self._create_fallback_icon()

        except Exception as e:
            if ICON_DEBUG:
                print(f"Error in icon loading: {e}")
            self._handle_load_failure()

    def _handle_load_failure(self):
        """Handle icon loading failure"""
        self.is_loading = False
        self.load_failed = True

        if self.config.behavior.show_fallback_on_error:
            self._create_fallback_icon()

        # Fire load failed event
        event_data = {
            'icon_path': str(self.icon_path) if self.icon_path else None,
            'ui_element': self
        }
        pygame.event.post(pygame.event.Event(UI_ICON_LOAD_FAILED, event_data))

    def _scale_icon(self):
        """Scale the icon according to current settings"""
        if not self._original_icon:
            return

        # Generate cache key
        cache_key = f"{id(self._original_icon)}_{self.config.layout.icon_size}_{self.scale_mode.value}"

        # Check cache
        if self.config.behavior.cache_scaled_icons:
            cached = self._global_cache.get(cache_key)
            if cached:
                self._scaled_icon = cached
                return

        target_w, target_h = self.config.layout.icon_size
        original_w, original_h = self._original_icon.get_size()

        if self.scale_mode == IconScaleMode.STRETCH:
            # Stretch to exact size
            scaled = pygame.transform.scale(self._original_icon, (target_w, target_h))

        elif self.scale_mode == IconScaleMode.SCALE_KEEP_ASPECT:
            # Scale maintaining aspect ratio
            scale_x = target_w / original_w
            scale_y = target_h / original_h
            scale = min(scale_x, scale_y)

            new_w = int(original_w * scale)
            new_h = int(original_h * scale)

            scaled = pygame.transform.scale(self._original_icon, (new_w, new_h))

        elif self.scale_mode == IconScaleMode.CENTER:
            # Center without scaling (crop if needed)
            scaled = pygame.Surface((target_w, target_h), pygame.SRCALPHA).convert_alpha()
            x = (target_w - original_w) // 2
            y = (target_h - original_h) // 2
            scaled.blit(self._original_icon, (x, y))

        else:  # TILE
            # Tile the icon
            scaled = pygame.Surface((target_w, target_h), pygame.SRCALPHA).convert_alpha()
            for x in range(0, target_w, original_w):
                for y in range(0, target_h, original_h):
                    scaled.blit(self._original_icon, (x, y))

        self._scaled_icon = scaled

        # Cache the result
        if self.config.behavior.cache_scaled_icons:
            self._global_cache.put(cache_key, scaled)

    def _create_fallback_icon(self):
        """Create fallback icon"""
        cache_key = f"fallback_{self.config.behavior.fallback_mode.value}_{self.config.layout.icon_size}"

        # Check cache
        if self.config.behavior.cache_fallback_icons:
            cached = self._global_cache.get(cache_key)
            if cached:
                self._fallback_icon = cached
                return

        w, h = self.config.layout.icon_size
        surface = pygame.Surface((w, h), pygame.SRCALPHA).convert_alpha()

        bg_color = self.theme_manager.get_color('error_bg' if self.load_failed else 'fallback_bg')
        fg_color = self.theme_manager.get_color('error_fg' if self.load_failed else 'fallback_fg')

        if self.config.behavior.fallback_mode == IconFallbackMode.GEOMETRIC:
            # Draw simple geometric shape
            center = (w // 2, h // 2)
            radius = min(w, h) // 3

            pygame.draw.circle(surface, bg_color, center, radius + 2)
            pygame.draw.circle(surface, fg_color, center, radius, 2)

            # Draw X for error
            if self.load_failed:
                pygame.draw.line(surface, fg_color,
                                 (center[0] - radius // 2, center[1] - radius // 2),
                                 (center[0] + radius // 2, center[1] + radius // 2), 2)
                pygame.draw.line(surface, fg_color,
                                 (center[0] + radius // 2, center[1] - radius // 2),
                                 (center[0] - radius // 2, center[1] + radius // 2), 2)

        elif self.config.behavior.fallback_mode == IconFallbackMode.INITIALS:
            # Draw text initials
            font_size = self.config.layout.fallback_text_size
            font = pygame.font.Font(None, font_size)
            text = self.config.default_fallback_text

            pygame.draw.rect(surface, bg_color, (0, 0, w, h))

            text_surface = font.render(text, True, fg_color)
            text_rect = text_surface.get_rect(center=(w // 2, h // 2))
            surface.blit(text_surface, text_rect)

        elif self.config.behavior.fallback_mode == IconFallbackMode.PLACEHOLDER:
            # Standard placeholder pattern
            pygame.draw.rect(surface, bg_color, (0, 0, w, h))
            pygame.draw.rect(surface, fg_color, (0, 0, w, h), 2)

            # Draw diagonal lines
            pygame.draw.line(surface, fg_color, (0, 0), (w, h), 1)
            pygame.draw.line(surface, fg_color, (w, 0), (0, h), 1)

        self._fallback_icon = surface

        # Cache the result
        if self.config.behavior.cache_fallback_icons:
            self._global_cache.put(cache_key, surface)

    def _start_scale_animation(self, from_scale: float, to_scale: float):
        """Start scale animation"""
        self.animation_start_time = pygame.time.get_ticks() / 1000.0
        self.animation_from_scale = from_scale
        self.animation_to_scale = to_scale
        self.animation_time = 0.0

    def _get_current_scale(self) -> float:
        """Get current scale factor for animations"""
        if self.animation_time >= self.config.interaction.animation_duration:
            return self.animation_to_scale

        # Simple linear interpolation (could be enhanced with easing)
        progress = self.animation_time / self.config.interaction.animation_duration
        return self.animation_from_scale + (self.animation_to_scale - self.animation_from_scale) * progress

    def rebuild_image(self):
        """Rebuild the panel image"""
        self.image.fill(pygame.Color(0, 0, 0, 0))  # Transparent

        # Use element's own coordinate space
        element_rect = pygame.Rect(0, 0, self.rect.width, self.rect.height)

        # Get current state colors
        bg_color = self.theme_manager.get_color('normal_bg', self.state)
        border_color = self.theme_manager.get_color('normal_border', self.state)

        # Draw background
        if self.config.behavior.show_background:
            if self.config.layout.corner_radius > 0:
                pygame.draw.rect(self.image, bg_color, element_rect,
                                 border_radius=self.config.layout.corner_radius)
            else:
                pygame.draw.rect(self.image, bg_color, element_rect)

        # Calculate icon position (centered in element)
        current_scale = self._get_current_scale()
        icon_w, icon_h = self.config.layout.icon_size

        if current_scale != 1.0:
            icon_w = int(icon_w * current_scale)
            icon_h = int(icon_h * current_scale)

        # Center in element (relative coordinates)
        icon_x = (self.rect.width - icon_w) // 2
        icon_y = (self.rect.height - icon_h) // 2
        icon_rect = pygame.Rect(icon_x, icon_y, icon_w, icon_h)

        # Draw icon
        if self.is_loading and self.config.behavior.show_loading_indicator:
            self._draw_loading_indicator(icon_rect)
        elif self._scaled_icon:
            # Scale if needed for animation
            if current_scale != 1.0:
                scaled_icon = pygame.transform.scale(self._scaled_icon, (icon_w, icon_h))
                self.image.blit(scaled_icon, icon_rect)
            else:
                # Center the scaled icon
                icon_pos = (
                    (self.rect.width - self._scaled_icon.get_width()) // 2,
                    (self.rect.height - self._scaled_icon.get_height()) // 2
                )
                self.image.blit(self._scaled_icon, icon_pos)
        elif self._fallback_icon:
            # Center the fallback icon
            icon_pos = (
                (self.rect.width - self._fallback_icon.get_width()) // 2,
                (self.rect.height - self._fallback_icon.get_height()) // 2
            )
            self.image.blit(self._fallback_icon, icon_pos)

        # Draw border
        if self.config.behavior.show_border and self.config.layout.border_width > 0:
            if self.config.layout.corner_radius > 0:
                pygame.draw.rect(self.image, border_color, element_rect,
                                 self.config.layout.border_width,
                                 border_radius=self.config.layout.corner_radius)
            else:
                pygame.draw.rect(self.image, border_color, element_rect,
                                 self.config.layout.border_width)

    def _draw_loading_indicator(self, icon_rect: pygame.Rect):
        """Draw loading indicator"""
        center = icon_rect.center
        radius = self.config.layout.loading_indicator_size // 2
        width = self.config.layout.loading_ring_width

        loading_color = self.theme_manager.get_color('loading_indicator')

        if self.config.behavior.animate_loading:
            # Animated spinner
            start_angle = self.loading_angle
            end_angle = start_angle + 90  # 90 degree arc

            # Convert to radians and draw arc
            import math
            start_rad = math.radians(start_angle)
            end_rad = math.radians(end_angle)

            # Draw arc (simplified - could use more sophisticated arc drawing)
            for angle in range(int(start_angle), int(end_angle), 5):
                rad = math.radians(angle)
                x = center[0] + radius * math.cos(rad)
                y = center[1] + radius * math.sin(rad)
                pygame.draw.circle(self.image, loading_color, (int(x), int(y)), width // 2)
        else:
            # Static loading ring
            pygame.draw.circle(self.image, loading_color, center, radius, width)

    def process_event(self, event: pygame.event.Event) -> bool:
        """Process events"""
        consumed = False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos) and self.config.interaction.clickable:
                self.is_pressed = True
                self.set_state(IconState.PRESSED)
                consumed = True

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.is_pressed:
                self.is_pressed = False
                if self.rect.collidepoint(event.pos):
                    # Handle selection
                    if self.config.interaction.selectable:
                        if self.config.interaction.toggle_selection:
                            self.is_selected = not self.is_selected
                        else:
                            self.is_selected = True

                    # Check for double click
                    current_time = pygame.time.get_ticks()
                    if (current_time - self.last_click_time) < self.config.interaction.double_click_time:
                        event_data = {'ui_element': self}
                        pygame.event.post(pygame.event.Event(UI_ICON_DOUBLE_CLICKED, event_data))
                    else:
                        event_data = {'ui_element': self}
                        pygame.event.post(pygame.event.Event(UI_ICON_CLICKED, event_data))

                    self.last_click_time = current_time

                next_state = IconState.NORMAL
                if self.is_selected:
                    next_state = IconState.SELECTED
                elif self.is_hovered:
                    next_state = IconState.HOVERED

                self.set_state(next_state)
                consumed = True

        elif event.type == pygame.MOUSEMOTION:
            if self.config.interaction.hoverable:
                was_hovered = self.is_hovered
                self.is_hovered = self.rect.collidepoint(event.pos)

                if self.is_hovered != was_hovered:
                    if self.is_hovered:
                        event_data = {'ui_element': self}
                        pygame.event.post(pygame.event.Event(UI_ICON_HOVERED, event_data))

                    if not self.is_pressed:
                        if self.is_selected:
                            self.set_state(IconState.SELECTED)
                        else:
                            self.set_state(IconState.HOVERED if self.is_hovered else IconState.NORMAL)

        return consumed

    def update(self, time_delta: float):
        """Update the panel"""
        super().update(time_delta)

        # Update animations
        if self.config.behavior.animate_state_changes:
            if self.animation_time < self.config.interaction.animation_duration:
                self.animation_time += time_delta
                self.rebuild_image()

        # Update loading animation
        if self.is_loading and self.config.behavior.animate_loading:
            self.loading_angle += 180 * time_delta  # 180 degrees per second
            if self.loading_angle >= 360:
                self.loading_angle -= 360
            self.rebuild_image()

        # Check loading timeout
        if self.is_loading:
            current_time = pygame.time.get_ticks() / 1000.0
            if current_time - self.loading_start_time > self.config.behavior.loading_timeout:
                self._handle_load_failure()


# Example usage and theme
ICON_THEME = {
    'icon_panel': {
        'colours': {
            'normal_bg': '#00000000',  # Transparent
            'hovered_bg': '#3C3C3C80',
            'pressed_bg': '#50505080',
            'disabled_bg': '#28282880',
            'selected_bg': '#4682B480',
            'loading_bg': '#32323280',
            'normal_border': '#646464',
            'hovered_border': '#787878',
            'pressed_border': '#8C8C8C',
            'disabled_border': '#505050',
            'selected_border': '#78A0FF',
            'loading_border': '#64C864',
            'shadow': '#0000003C',
            'highlight': '#FFFFFF64',
            'loading_indicator': '#64C864',
            'fallback_bg': '#3C3C3C',
            'fallback_fg': '#C8C8C8',
            'error_bg': '#503C3C',
            'error_fg': '#FF9696',
        }
    }
}


def main():
    """Example demonstration of the Icon Panel"""
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("Icon Panel Demo")
    clock = pygame.time.Clock()

    # Create manager with theme
    manager = pygame_gui.UIManager((800, 600), ICON_THEME)

    # Create different icon configurations
    basic_config = IconConfig()
    basic_config.behavior.show_background = True
    basic_config.behavior.show_border = True

    hover_config = IconConfig()
    hover_config.behavior.show_background = True
    hover_config.behavior.show_border = True
    hover_config.interaction.hover_scale = 1.2
    hover_config.behavior.animate_state_changes = True

    selectable_config = IconConfig()
    selectable_config.behavior.show_background = True
    selectable_config.behavior.show_border = True
    selectable_config.interaction.selectable = True
    selectable_config.interaction.toggle_selection = True

    # Create some sample icons
    icon_size = (32, 32)

    # Create a simple colored icon
    red_icon = pygame.Surface(icon_size, pygame.SRCALPHA)
    pygame.draw.circle(red_icon, (255, 100, 100), (16, 16), 12)

    blue_icon = pygame.Surface(icon_size, pygame.SRCALPHA)
    pygame.draw.rect(blue_icon, (100, 100, 255), (4, 4, 24, 24))

    green_icon = pygame.Surface(icon_size, pygame.SRCALPHA)
    points = [(16, 4), (28, 28), (4, 28)]
    pygame.draw.polygon(green_icon, (100, 255, 100), points)

    # Create icon panels
    icon1 = IconPanel(
        pygame.Rect(50, 50, 64, 64),
        manager,
        icon_surface=red_icon,
        config=basic_config
    )

    icon2 = IconPanel(
        pygame.Rect(150, 50, 64, 64),
        manager,
        icon_surface=blue_icon,
        config=hover_config
    )

    icon3 = IconPanel(
        pygame.Rect(250, 50, 64, 64),
        manager,
        icon_surface=green_icon,
        config=selectable_config
    )

    # Fallback icon (no source)
    fallback_config = IconConfig()
    fallback_config.behavior.show_background = True
    fallback_config.behavior.show_border = True
    fallback_config.behavior.fallback_mode = IconFallbackMode.GEOMETRIC

    fallback_icon = IconPanel(
        pygame.Rect(350, 50, 64, 64),
        manager,
        config=fallback_config
    )

    # Loading icon simulation
    loading_config = IconConfig()
    loading_config.behavior.show_background = True
    loading_config.behavior.show_border = True
    loading_config.behavior.show_loading_indicator = True
    loading_config.behavior.animate_loading = True

    loading_icon = IconPanel(
        pygame.Rect(450, 50, 64, 64),
        manager,
        config=loading_config
    )
    loading_icon.is_loading = True
    loading_icon.loading_start_time = pygame.time.get_ticks() / 1000.0

    print("Icon Panel Demo")
    print("- Basic icon display")
    print("- Hover effects with scaling")
    print("- Selectable icons")
    print("- Fallback icon generation")
    print("- Loading indicators")

    running = True
    while running:
        time_delta = clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == UI_ICON_CLICKED:
                print(f"Icon clicked: {event.ui_element}")
            elif event.type == UI_ICON_HOVERED:
                print(f"Icon hovered: {event.ui_element}")

            manager.process_events(event)

        manager.update(time_delta)

        screen.fill((30, 30, 30))
        manager.draw_ui(screen)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()