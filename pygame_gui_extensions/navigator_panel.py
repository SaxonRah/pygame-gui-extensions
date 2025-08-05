import pygame
import pygame_gui
from pygame_gui.core import UIElement, ObjectID
from pygame_gui.core.interfaces import IContainerLikeInterface
from typing import List, Optional, Dict, Any, Union, Callable, Tuple, Protocol
from dataclasses import dataclass, field
from enum import Enum
import copy

try:
    from pygame_gui.core.interfaces.gui_font_interface import IGUIFontInterface
except ImportError:
    IGUIFontInterface = None

NAVIGATOR_DEBUG = False

# Define custom pygame-gui events
UI_NAVIGATOR_VIEWPORT_CHANGED = pygame.USEREVENT + 100
UI_NAVIGATOR_ZOOM_CHANGED = pygame.USEREVENT + 101
UI_NAVIGATOR_NAVIGATION_CLICKED = pygame.USEREVENT + 102
UI_NAVIGATOR_FIT_REQUESTED = pygame.USEREVENT + 103
UI_NAVIGATOR_ZOOM_TO_SELECTION = pygame.USEREVENT + 104
UI_NAVIGATOR_CONTENT_CHANGED = pygame.USEREVENT + 105


class NavigatorMode(Enum):
    """Display modes for the navigator"""
    THUMBNAIL = "thumbnail"  # Show scaled-down content
    WIREFRAME = "wireframe"  # Show outline/structure only
    CUSTOM = "custom"  # Use custom drawing function


class ZoomMode(Enum):
    """Zoom behavior modes"""
    FIT_WIDTH = "fit_width"
    FIT_HEIGHT = "fit_height"
    FIT_ALL = "fit_all"
    ACTUAL_SIZE = "actual_size"
    CUSTOM = "custom"


@dataclass
class NavigatorLayoutConfig:
    """Layout and spacing configuration for navigator panel"""
    # Thumbnail area
    thumbnail_padding: int = 4
    thumbnail_border_width: int = 1

    # Viewport visualization
    viewport_border_width: int = 2
    viewport_fill_alpha: int = 60
    selection_border_width: int = 2
    selection_fill_alpha: int = 40

    # Zoom controls
    zoom_control_height: int = 30
    zoom_button_size: int = 24
    zoom_button_spacing: int = 3
    zoom_text_size: int = 16
    zoom_percentage_size: int = 10

    # Coordinate display
    coordinate_font_size: int = 10
    coordinate_padding: int = 4
    coordinate_background_alpha: int = 180

    # Error display
    error_font_size: int = 14
    error_icon_size: int = 16

    # Minimum sizes
    min_thumbnail_size: Tuple[int, int] = (50, 50)
    min_viewport_indicator_size: int = 2


@dataclass
class NavigatorInteractionConfig:
    """Interaction and timing configuration"""
    # Mouse interaction
    click_to_navigate: bool = True
    drag_to_pan: bool = True
    pan_sensitivity: float = 1.0
    drag_threshold: int = 3

    # Zoom behavior
    zoom_wheel_enabled: bool = True
    zoom_wheel_factor: float = 1.1
    zoom_animation_enabled: bool = False
    zoom_animation_duration: float = 0.2

    # Keyboard navigation
    keyboard_navigation: bool = True
    keyboard_pan_speed: float = 10.0
    keyboard_zoom_step: float = 0.1

    # Performance
    update_throttle_ms: int = 16  # ~60fps
    thumbnail_update_on_change: bool = True


@dataclass
class NavigatorBehaviorConfig:
    """Behavior configuration for navigator panel"""
    # Display options
    show_viewport_outline: bool = True
    show_zoom_controls: bool = True
    show_coordinates: bool = False
    show_selection_highlight: bool = True
    show_content_bounds: bool = False

    # Zoom settings
    zoom_levels: List[float] = field(default_factory=lambda: [0.1, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0, 4.0, 5.0])
    min_zoom: float = 0.05
    max_zoom: float = 20.0
    default_zoom: float = 1.0

    # Viewport behavior
    clamp_viewport_to_content: bool = True
    center_content_when_smaller: bool = True
    maintain_aspect_ratio: bool = True

    # Performance options
    thumbnail_cache_enabled: bool = True
    max_thumbnail_cache_size: int = 10
    lazy_thumbnail_updates: bool = True

    # Error handling
    show_error_details: bool = True
    fallback_to_wireframe: bool = True


@dataclass
class NavigatorConfig:
    """Complete configuration for the navigator panel"""
    # Sub-configurations
    layout: NavigatorLayoutConfig = field(default_factory=NavigatorLayoutConfig)
    interaction: NavigatorInteractionConfig = field(default_factory=NavigatorInteractionConfig)
    behavior: NavigatorBehaviorConfig = field(default_factory=NavigatorBehaviorConfig)

    # Display mode
    mode: NavigatorMode = NavigatorMode.THUMBNAIL

    # Colors (with proper defaults)
    viewport_color: pygame.Color = field(default_factory=lambda: pygame.Color(255, 255, 255, 60))
    viewport_border_color: pygame.Color = field(default_factory=lambda: pygame.Color(255, 255, 255))
    selection_color: pygame.Color = field(default_factory=lambda: pygame.Color(255, 255, 0, 100))
    selection_border_color: pygame.Color = field(default_factory=lambda: pygame.Color(255, 255, 0))

    # Custom drawing function
    custom_draw_function: Optional[Callable[[pygame.Surface, pygame.Rect, Any], None]] = None

    # Convenience properties for backward compatibility
    @property
    def show_viewport_outline(self) -> bool:
        return self.behavior.show_viewport_outline

    @property
    def show_zoom_controls(self) -> bool:
        return self.behavior.show_zoom_controls

    @property
    def show_coordinates(self) -> bool:
        return self.behavior.show_coordinates

    @property
    def click_to_navigate(self) -> bool:
        return self.interaction.click_to_navigate

    @property
    def drag_to_pan(self) -> bool:
        return self.interaction.drag_to_pan

    @property
    def zoom_wheel_enabled(self) -> bool:
        return self.interaction.zoom_wheel_enabled


class NavigatorViewport:
    """Information about the current viewport with improved functionality"""

    def __init__(self,
                 content_x: float = 0.0, content_y: float = 0.0,
                 content_width: float = 100.0, content_height: float = 100.0,
                 zoom: float = 1.0,
                 total_content_width: float = 100.0, total_content_height: float = 100.0):

        self.content_x: float = content_x
        self.content_y: float = content_y
        self.content_width: float = content_width
        self.content_height: float = content_height
        self.zoom: float = zoom
        self.total_content_width: float = total_content_width
        self.total_content_height: float = total_content_height

    def get_center(self) -> Tuple[float, float]:
        """Get viewport center in content coordinates"""
        return (
            self.content_x + self.content_width / 2,
            self.content_y + self.content_height / 2
        )

    def set_center(self, x: float, y: float):
        """Set viewport center in content coordinates"""
        self.content_x = x - self.content_width / 2
        self.content_y = y - self.content_height / 2

    def clamp_to_content(self):
        """Ensure viewport stays within content bounds"""
        # Handle case where viewport is larger than content
        if self.content_width >= self.total_content_width:
            self.content_x = -(self.content_width - self.total_content_width) / 2
        else:
            self.content_x = max(0, min(self.content_x, self.total_content_width - self.content_width))

        if self.content_height >= self.total_content_height:
            self.content_y = -(self.content_height - self.total_content_height) / 2
        else:
            self.content_y = max(0, min(self.content_y, self.total_content_height - self.content_height))

    def contains_point(self, x: float, y: float) -> bool:
        """Check if a point is within the viewport"""
        return (self.content_x <= x <= self.content_x + self.content_width and
                self.content_y <= y <= self.content_y + self.content_height)

    def get_bounds_rect(self) -> pygame.Rect:
        """Get viewport as pygame Rect"""
        return pygame.Rect(int(self.content_x), int(self.content_y),
                           int(self.content_width), int(self.content_height))

    def copy(self) -> 'NavigatorViewport':
        """Create a copy of this viewport"""
        return NavigatorViewport(
            self.content_x, self.content_y,
            self.content_width, self.content_height,
            self.zoom,
            self.total_content_width, self.total_content_height
        )


class ContentProvider(Protocol):
    """Protocol for content providers - implement this to provide content to the navigator"""

    def get_content_size(self) -> Tuple[float, float]:
        """Return the total size of the content"""
        ...

    def render_thumbnail(self, surface: pygame.Surface, thumbnail_rect: pygame.Rect,
                         viewport: NavigatorViewport, mode: NavigatorMode) -> None:
        """Render content thumbnail to the given surface and rect"""
        ...

    def get_selection_bounds(self) -> Optional[pygame.Rect]:
        """Return bounds of current selection, if any"""
        ...


class NavigatorThemeManager:
    """Manages theming for the navigator panel with proper pygame-gui integration"""

    def __init__(self, ui_element: UIElement):
        self.ui_element = ui_element
        self.ui_manager = ui_element.ui_manager
        self.themed_colors = {}
        self.themed_font = None
        self._update_theme_data()

    def _get_element_ids(self) -> List[str]:
        """Get element IDs for theme lookup - matches PropertyPanel approach"""
        # Create element_ids and add the base element type
        element_ids = ['navigator_panel']

        # Add object_id and class_id from the UIElement
        if hasattr(self.ui_element, 'object_ids') and self.ui_element.object_ids:
            element_ids.extend(self.ui_element.object_ids)

        # Try to get IDs from the ObjectID directly
        if hasattr(self.ui_element, '_object_id') and self.ui_element._object_id:
            if self.ui_element._object_id.object_id:
                element_ids.append(self.ui_element._object_id.object_id)
            if self.ui_element._object_id.class_id:
                element_ids.append(self.ui_element._object_id.class_id)

        return element_ids

    def _update_theme_data(self):
        """Update theme-dependent data with proper pygame-gui integration"""

        # Default color mappings
        color_mappings = {
            'dark_bg': pygame.Color(30, 30, 30),
            'thumbnail_bg': pygame.Color(45, 45, 45),
            'normal_border': pygame.Color(100, 100, 100),
            'focused_border': pygame.Color(120, 160, 255),
            'control_bg': pygame.Color(60, 60, 60),
            'control_border': pygame.Color(80, 80, 80),
            'control_text': pygame.Color(255, 255, 255),
            'hovered_bg': pygame.Color(80, 80, 80),
            'pressed_bg': pygame.Color(100, 100, 100),
            'disabled_bg': pygame.Color(40, 40, 40),
            'disabled_text': pygame.Color(120, 120, 120),
            'viewport_outline': pygame.Color(255, 255, 255),
            'viewport_fill': pygame.Color(255, 255, 255, 60),
            'selection_highlight': pygame.Color(255, 255, 0, 100),
            'selection_border': pygame.Color(255, 255, 0),
            'error_bg': pygame.Color(80, 40, 40),
            'error_text': pygame.Color(255, 150, 150),
            'coordinate_bg': pygame.Color(0, 0, 0, 180),
            'coordinate_text': pygame.Color(255, 255, 255),
        }

        try:
            self.themed_colors = {}
            theme = self.ui_manager.get_theme()
            element_ids = self._get_element_ids()

            # Use UIElement's theme access methods if available
            for color_id, default_color in color_mappings.items():
                try:
                    # Try to get themed color using pygame-gui's theme system
                    if hasattr(theme, 'get_colour_or_gradient'):
                        color = theme.get_colour_or_gradient(color_id, element_ids)
                        self.themed_colors[color_id] = color if color else default_color
                    else:
                        self.themed_colors[color_id] = default_color
                except Exception:
                    self.themed_colors[color_id] = default_color

            # Get themed font using pygame-gui's font system
            try:
                if hasattr(theme, 'get_font'):
                    self.themed_font = theme.get_font(element_ids)
                else:
                    raise Exception("No font method")
            except Exception:
                try:
                    self.themed_font = pygame.font.SysFont('Arial', 12)
                except:
                    self.themed_font = pygame.font.Font(None, 12)

        except Exception as e:
            if NAVIGATOR_DEBUG:
                print(f"Error getting theme data: {e}")
            # Complete fallback
            self.themed_colors = color_mappings
            try:
                self.themed_font = pygame.font.SysFont('Arial', 12)
            except:
                self.themed_font = pygame.font.Font(None, 12)

    def rebuild_from_changed_theme_data(self):
        """Called when theme data changes"""
        self._update_theme_data()

    def get_color(self, color_id: str, fallback: pygame.Color = None) -> pygame.Color:
        """Get a themed color with fallback"""
        return self.themed_colors.get(color_id, fallback or pygame.Color(255, 255, 255))

    def get_font(self, size: Optional[int] = None):
        """Get the themed font, optionally scaled"""
        if size:
            try:
                # Try to create a font with the desired size
                font = pygame.font.SysFont('Arial', size)
                if font:
                    return font
            except:
                pass
            try:
                return pygame.font.Font(None, size)
            except:
                pass

        # Fallback to themed font
        return self.themed_font


class ImageContentProvider:
    """Content provider for pygame surfaces/images with proper error handling"""

    def __init__(self, image: pygame.Surface):
        self.image = image.convert_alpha() if image else None
        self.selection_rect: Optional[pygame.Rect] = None
        self._cached_thumbnail: Optional[pygame.Surface] = None
        self._cache_size: Optional[Tuple[int, int]] = None

    def get_content_size(self) -> Tuple[float, float]:
        if self.image:
            return float(self.image.get_width()), float(self.image.get_height())
        return 0.0, 0.0

    def render_thumbnail(self, surface: pygame.Surface, thumbnail_rect: pygame.Rect,
                         viewport: NavigatorViewport, mode: NavigatorMode) -> None:
        """Render thumbnail with proper error handling and caching"""
        if not self.image:
            # Draw error indicator
            error_color = pygame.Color(100, 50, 50)
            pygame.draw.rect(surface, error_color, thumbnail_rect)
            return

        try:
            # Check if we can use cached thumbnail
            current_size = (thumbnail_rect.width, thumbnail_rect.height)
            if (self._cached_thumbnail is None or
                    self._cache_size != current_size or
                    current_size[0] <= 0 or current_size[1] <= 0):

                # Create new cached thumbnail
                img_w, img_h = self.image.get_size()
                if img_w <= 0 or img_h <= 0:
                    return

                scale_x = thumbnail_rect.width / img_w
                scale_y = thumbnail_rect.height / img_h
                scale = min(scale_x, scale_y)

                scaled_w = max(1, int(img_w * scale))
                scaled_h = max(1, int(img_h * scale))

                if scaled_w > 0 and scaled_h > 0:
                    self._cached_thumbnail = pygame.transform.scale(self.image, (scaled_w, scaled_h))
                    self._cache_size = current_size
                else:
                    return

            if self._cached_thumbnail:
                # Center the scaled image in the thumbnail rect
                thumb_w, thumb_h = self._cached_thumbnail.get_size()
                x = thumbnail_rect.x + (thumbnail_rect.width - thumb_w) // 2
                y = thumbnail_rect.y + (thumbnail_rect.height - thumb_h) // 2
                surface.blit(self._cached_thumbnail, (x, y))

        except Exception as e:
            if NAVIGATOR_DEBUG:
                print(f"Error rendering image thumbnail: {e}")
            # Draw error indicator
            error_color = pygame.Color(100, 50, 50)
            pygame.draw.rect(surface, error_color, thumbnail_rect)

    def get_selection_bounds(self) -> Optional[pygame.Rect]:
        return self.selection_rect

    def set_selection(self, rect: Optional[pygame.Rect]):
        self.selection_rect = rect


class NodeGraphContentProvider:
    """Content provider for node graphs with comprehensive rendering"""

    def __init__(self, content_size: Tuple[float, float]):
        self.content_size = content_size
        self.nodes: List[Dict[str, Any]] = []
        self.connections: List[Tuple[int, int]] = []
        self.selection: List[int] = []
        self._render_cache: Dict[str, Any] = {}

    def get_content_size(self) -> Tuple[float, float]:
        return self.content_size

    def add_node(self, x: float, y: float, width: float = 100, height: float = 50,
                 label: str = "", color: pygame.Color = pygame.Color(100, 150, 200)):
        """Add a node to the graph"""
        node = {
            'x': x, 'y': y, 'width': width, 'height': height,
            'label': label, 'color': color
        }
        self.nodes.append(node)
        self._render_cache.clear()  # Clear cache when nodes change
        return len(self.nodes) - 1

    def add_connection(self, from_node: int, to_node: int):
        """Add a connection between nodes"""
        if 0 <= from_node < len(self.nodes) and 0 <= to_node < len(self.nodes):
            self.connections.append((from_node, to_node))
            self._render_cache.clear()  # Clear cache when connections change

    def render_thumbnail(self, surface: pygame.Surface, thumbnail_rect: pygame.Rect,
                         viewport: NavigatorViewport, mode: NavigatorMode) -> None:
        """Render node graph thumbnail with mode support"""
        if not self.nodes:
            return

        try:
            # Calculate scale to fit content in thumbnail
            content_w, content_h = self.content_size
            if content_w <= 0 or content_h <= 0:
                return

            scale_x = thumbnail_rect.width / content_w
            scale_y = thumbnail_rect.height / content_h
            scale = min(scale_x, scale_y)

            # Calculate scaled content size and offset for centering
            scaled_content_w = content_w * scale
            scaled_content_h = content_h * scale
            offset_x = (thumbnail_rect.width - scaled_content_w) / 2
            offset_y = (thumbnail_rect.height - scaled_content_h) / 2

            # Determine rendering style based on mode
            wireframe_mode = mode == NavigatorMode.WIREFRAME

            # Draw connections first (so they appear behind nodes)
            for from_idx, to_idx in self.connections:
                if from_idx < len(self.nodes) and to_idx < len(self.nodes):
                    from_node = self.nodes[from_idx]
                    to_node = self.nodes[to_idx]

                    # Calculate scaled positions
                    from_x = thumbnail_rect.x + offset_x + (from_node['x'] + from_node['width'] / 2) * scale
                    from_y = thumbnail_rect.y + offset_y + (from_node['y'] + from_node['height'] / 2) * scale
                    to_x = thumbnail_rect.x + offset_x + (to_node['x'] + to_node['width'] / 2) * scale
                    to_y = thumbnail_rect.y + offset_y + (to_node['y'] + to_node['height'] / 2) * scale

                    line_color = pygame.Color(120, 120, 120) if not wireframe_mode else pygame.Color(100, 100, 100)
                    line_width = max(1, int(2 * scale))
                    pygame.draw.line(surface, line_color,
                                     (int(from_x), int(from_y)), (int(to_x), int(to_y)), line_width)

            # Draw nodes
            for i, node in enumerate(self.nodes):
                # Calculate scaled position and size
                x = thumbnail_rect.x + offset_x + node['x'] * scale
                y = thumbnail_rect.y + offset_y + node['y'] * scale
                w = max(2, node['width'] * scale)
                h = max(2, node['height'] * scale)

                node_rect = pygame.Rect(int(x), int(y), int(w), int(h))

                if wireframe_mode:
                    # Wireframe mode: just draw outlines
                    border_color = pygame.Color(150, 150, 150)
                    if i in self.selection:
                        border_color = pygame.Color(255, 255, 100)
                    border_width = max(1, int(2 * scale))
                    pygame.draw.rect(surface, border_color, node_rect, border_width)
                else:
                    # Normal mode: draw filled rectangles
                    color = node['color']
                    if i in self.selection:
                        color = pygame.Color(255, 255, 100)

                    pygame.draw.rect(surface, color, node_rect)
                    border_width = max(1, int(1 * scale))
                    pygame.draw.rect(surface, pygame.Color(80, 80, 80), node_rect, border_width)

                    # Draw label if node is large enough
                    if w > 20 and h > 10 and node['label']:
                        try:
                            font_size = max(8, int(12 * scale))
                            font = pygame.font.Font(None, font_size)
                            text_surface = font.render(node['label'][:8], True, pygame.Color(255, 255, 255))
                            text_rect = text_surface.get_rect()
                            text_rect.center = node_rect.center

                            # Only draw if text fits in node
                            if (text_rect.width <= node_rect.width - 4 and
                                    text_rect.height <= node_rect.height - 2):
                                surface.blit(text_surface, text_rect)
                        except Exception:
                            pass  # Skip text if any error

        except Exception as e:
            if NAVIGATOR_DEBUG:
                print(f"Error rendering node graph thumbnail: {e}")

    def get_selection_bounds(self) -> Optional[pygame.Rect]:
        if not self.selection:
            return None

        # Calculate bounding box of selected nodes
        min_x = min_y = float('inf')
        max_x = max_y = float('-inf')

        for node_idx in self.selection:
            if 0 <= node_idx < len(self.nodes):
                node = self.nodes[node_idx]
                min_x = min(min_x, node['x'])
                min_y = min(min_y, node['y'])
                max_x = max(max_x, node['x'] + node['width'])
                max_y = max(max_y, node['y'] + node['height'])

        if min_x != float('inf'):
            return pygame.Rect(int(min_x), int(min_y),
                               int(max_x - min_x), int(max_y - min_y))
        return None

    def set_selection(self, node_indices: List[int]):
        self.selection = [i for i in node_indices if 0 <= i < len(self.nodes)]
        self._render_cache.clear()  # Clear cache when selection changes


class FunctionContentProvider:
    """Content provider using custom drawing function with error handling"""

    def __init__(self, content_size: Tuple[float, float],
                 draw_function: Callable[[pygame.Surface, pygame.Rect, NavigatorViewport, NavigatorMode], None]):
        self.content_size = content_size
        self.draw_function = draw_function
        self.selection_bounds: Optional[pygame.Rect] = None

    def get_content_size(self) -> Tuple[float, float]:
        return self.content_size

    def render_thumbnail(self, surface: pygame.Surface, thumbnail_rect: pygame.Rect,
                         viewport: NavigatorViewport, mode: NavigatorMode) -> None:
        try:
            self.draw_function(surface, thumbnail_rect, viewport, mode)
        except Exception as e:
            if NAVIGATOR_DEBUG:
                print(f"Error in custom draw function: {e}")

    def get_selection_bounds(self) -> Optional[pygame.Rect]:
        return self.selection_bounds

    def set_selection_bounds(self, rect: Optional[pygame.Rect]):
        self.selection_bounds = rect


class ZoomControl:
    """Zoom control overlay with comprehensive configuration support"""

    def __init__(self, rect: pygame.Rect, config: NavigatorConfig):
        self.rect = rect
        self.config = config
        self.layout = config.layout

        # Calculate button layout
        button_size = self.layout.zoom_button_size
        button_spacing = self.layout.zoom_button_spacing
        total_button_width = button_size * 4 + button_spacing * 3

        start_x = rect.x + (rect.width - total_button_width) // 2
        y = rect.y + (rect.height - button_size) // 2

        self.zoom_in_rect = pygame.Rect(start_x, y, button_size, button_size)
        self.zoom_out_rect = pygame.Rect(start_x + button_size + button_spacing, y, button_size, button_size)
        self.fit_rect = pygame.Rect(start_x + (button_size + button_spacing) * 2, y, button_size, button_size)
        self.actual_size_rect = pygame.Rect(start_x + (button_size + button_spacing) * 3, y, button_size, button_size)

        # State
        self.hovered_button = None
        self.pressed_button = None

    def draw(self, surface: pygame.Surface, current_zoom: float, theme_manager: NavigatorThemeManager):
        """Draw zoom controls with comprehensive theming"""
        # Background
        bg_color = theme_manager.get_color('control_bg')
        border_color = theme_manager.get_color('control_border')

        pygame.draw.rect(surface, bg_color, self.rect)
        pygame.draw.rect(surface, border_color, self.rect, 1)

        # Buttons
        buttons = [
            (self.zoom_in_rect, "+", "zoom_in"),
            (self.zoom_out_rect, "-", "zoom_out"),
            (self.fit_rect, "F", "fit"),
            (self.actual_size_rect, "1", "actual")
        ]

        text_color = theme_manager.get_color('control_text')
        hover_color = theme_manager.get_color('hovered_bg')
        pressed_color = theme_manager.get_color('pressed_bg')

        for button_rect, text, button_id in buttons:
            # Button state colors
            button_bg = bg_color
            if self.pressed_button == button_id:
                button_bg = pressed_color
            elif self.hovered_button == button_id:
                button_bg = hover_color

            # Button background
            if button_bg != bg_color:
                pygame.draw.rect(surface, button_bg, button_rect)

            # Button border
            pygame.draw.rect(surface, border_color, button_rect, 1)

            # Button text
            try:
                font = theme_manager.get_font(self.layout.zoom_text_size)
                text_surface = font.render(text, True, text_color)
                text_rect = text_surface.get_rect(center=button_rect.center)
                surface.blit(text_surface, text_rect)
            except Exception as e:
                if NAVIGATOR_DEBUG:
                    print(f"Error rendering zoom button text: {e}")

        # Zoom level display
        zoom_text = f"{current_zoom * 100:.0f}%"
        try:
            font = theme_manager.get_font(self.layout.zoom_percentage_size)
            zoom_surface = font.render(zoom_text, True, text_color)
            zoom_rect = zoom_surface.get_rect()
            zoom_rect.centerx = self.rect.centerx
            zoom_rect.bottom = self.rect.bottom - 2
            surface.blit(zoom_surface, zoom_rect)
        except Exception as e:
            if NAVIGATOR_DEBUG:
                print(f"Error rendering zoom percentage: {e}")

    def handle_click(self, pos: Tuple[int, int], button: int) -> Optional[str]:
        """Handle click on zoom controls"""
        if button == 1:  # Left click only
            if self.zoom_in_rect.collidepoint(pos):
                self.pressed_button = "zoom_in"
                return "zoom_in"
            elif self.zoom_out_rect.collidepoint(pos):
                self.pressed_button = "zoom_out"
                return "zoom_out"
            elif self.fit_rect.collidepoint(pos):
                self.pressed_button = "fit"
                return "fit"
            elif self.actual_size_rect.collidepoint(pos):
                self.pressed_button = "actual_size"
                return "actual_size"
        return None

    def handle_mouse_up(self, pos: Tuple[int, int]) -> bool:
        """Handle mouse up event"""
        if self.pressed_button:
            self.pressed_button = None
            return True
        return False

    def handle_hover(self, pos: Tuple[int, int]) -> bool:
        """Handle hover over zoom controls"""
        old_hovered = self.hovered_button

        if self.zoom_in_rect.collidepoint(pos):
            self.hovered_button = "zoom_in"
        elif self.zoom_out_rect.collidepoint(pos):
            self.hovered_button = "zoom_out"
        elif self.fit_rect.collidepoint(pos):
            self.hovered_button = "fit"
        elif self.actual_size_rect.collidepoint(pos):
            self.hovered_button = "actual"
        else:
            self.hovered_button = None

        return old_hovered != self.hovered_button


class NavigatorPanel(UIElement):
    """Main navigator panel widget with comprehensive configuration and error handling"""

    def __init__(self, relative_rect: pygame.Rect,
                 manager: pygame_gui.UIManager,
                 content_provider: ContentProvider,
                 viewport: NavigatorViewport = None,
                 config: NavigatorConfig = None,
                 container: IContainerLikeInterface = None,
                 object_id: Union[ObjectID, str, None] = None,
                 anchors: Dict[str, str] = None):

        # Handle object_id properly
        if isinstance(object_id, ObjectID):
            self._object_id = object_id
        elif isinstance(object_id, str):
            self._object_id = ObjectID(object_id=object_id, class_id=None)
        else:
            self._object_id = ObjectID(object_id='#navigator_panel', class_id=None)

        super().__init__(relative_rect, manager, container,
                         starting_height=1, layer_thickness=1,
                         anchors=anchors, object_id=self._object_id)

        self.content_provider = content_provider
        self.viewport = viewport or NavigatorViewport()
        self.config = config or NavigatorConfig()

        # Initialize viewport size based on content
        try:
            content_w, content_h = self.content_provider.get_content_size()
            self.viewport.total_content_width = content_w
            self.viewport.total_content_height = content_h
        except Exception as e:
            if NAVIGATOR_DEBUG:
                print(f"Error getting content size: {e}")
            self.viewport.total_content_width = 100.0
            self.viewport.total_content_height = 100.0

        # Create theme manager
        element_ids = ['navigator_panel']
        if hasattr(self, 'object_ids') and self.object_ids:
            element_ids.extend(self.object_ids)
        self.theme_manager = NavigatorThemeManager(self)

        # UI state
        self.is_dragging = False
        self.drag_start_pos = (0, 0)
        self.drag_start_viewport = None
        self.is_focused = False
        self.thumbnail_cache: Optional[pygame.Surface] = None
        self.cache_invalid = True
        self._last_update_time = 0
        self.needs_rebuild = True

        # Layout state
        self._last_rebuild_state = None

        # Calculate layout
        self._calculate_layout()

        # Zoom control
        self.zoom_control = None
        if self.config.behavior.show_zoom_controls:
            self._create_zoom_control()

        # Create image surface
        self.image = pygame.Surface(self.rect.size).convert()

        # Initial render
        self.rebuild_image()

    def _needs_layout_rebuild(self) -> bool:
        """Check if layout needs rebuilding"""
        current_state = {
            'rect_size': (self.rect.width, self.rect.height),
            'show_zoom_controls': self.config.behavior.show_zoom_controls,
            'zoom_control_height': self.config.layout.zoom_control_height,
            'thumbnail_padding': self.config.layout.thumbnail_padding,
        }

        if current_state != self._last_rebuild_state:
            self._last_rebuild_state = current_state
            return True
        return False

    def _calculate_layout(self):
        """Calculate layout rectangles with comprehensive configuration support"""
        padding = self.config.layout.thumbnail_padding

        # Available area
        available_width = self.rect.width - 2 * padding
        available_height = self.rect.height - 2 * padding

        # Subtract zoom control height if needed
        if self.config.behavior.show_zoom_controls:
            available_height -= self.config.layout.zoom_control_height + padding

        # Ensure minimum size
        min_w, min_h = self.config.layout.min_thumbnail_size
        available_width = max(min_w, available_width)
        available_height = max(min_h, available_height)

        # Thumbnail area
        self.thumbnail_rect = pygame.Rect(
            padding, padding,
            available_width,
            available_height
        )

        if NAVIGATOR_DEBUG:
            print(f"Layout calculated: thumbnail_rect={self.thumbnail_rect}")

    def _create_zoom_control(self):
        """Create zoom control with proper layout"""
        if self.config.behavior.show_zoom_controls:
            zoom_y = self.thumbnail_rect.bottom + self.config.layout.thumbnail_padding
            zoom_rect = pygame.Rect(
                0, zoom_y,
                self.rect.width, self.config.layout.zoom_control_height
            )
            self.zoom_control = ZoomControl(zoom_rect, self.config)

    def rebuild_from_changed_theme_data(self):
        """Called by pygame-gui when theme data changes"""
        if NAVIGATOR_DEBUG:
            print("NavigatorPanel: rebuilding from changed theme data")

        self.theme_manager.rebuild_from_changed_theme_data()
        self.cache_invalid = True
        self.needs_rebuild = True
        self._last_rebuild_state = None  # Force layout recalculation
        self.rebuild_image()

    def _setup_element_object_ids(self):
        """Setup object IDs for theme lookup - called by UIElement"""
        # This is called by the parent UIElement during initialization
        # to set up proper theme ID chains
        pass

    def rebuild_image(self):
        """Rebuild the image surface with comprehensive error handling"""
        if not self.needs_rebuild:
            return

        try:
            # Recalculate layout if needed
            if self._needs_layout_rebuild():
                self._calculate_layout()
                if self.zoom_control:
                    self._create_zoom_control()

            # Fill background
            bg_color = self.theme_manager.get_color('dark_bg')
            self.image.fill(bg_color)

            # Draw thumbnail
            self._draw_thumbnail()

            # Draw viewport indicator
            if self.config.behavior.show_viewport_outline:
                self._draw_viewport_indicator()

            # Draw selection highlight
            if self.config.behavior.show_selection_highlight:
                self._draw_selection_highlight()

            # Draw content bounds if enabled
            if self.config.behavior.show_content_bounds:
                self._draw_content_bounds()

            # Draw zoom controls
            if self.zoom_control:
                self.zoom_control.draw(self.image, self.viewport.zoom, self.theme_manager)

            # Draw coordinates if enabled
            if self.config.behavior.show_coordinates:
                self._draw_coordinates()

            # Draw border
            border_color = self.theme_manager.get_color('focused_border' if self.is_focused else 'normal_border')
            border_width = 2 if self.is_focused else 1
            pygame.draw.rect(self.image, border_color, self.image.get_rect(), border_width)

            self.needs_rebuild = False

        except Exception as e:
            if NAVIGATOR_DEBUG:
                print(f"Error rebuilding navigator image: {e}")
            # Draw error state
            self._draw_error_state(str(e))

    def _draw_thumbnail(self):
        """Draw the content thumbnail with comprehensive error handling"""
        # Fill thumbnail background
        thumbnail_bg = self.theme_manager.get_color('thumbnail_bg')
        pygame.draw.rect(self.image, thumbnail_bg, self.thumbnail_rect)

        # Draw content using provider
        try:
            if self.config.mode == NavigatorMode.CUSTOM and self.config.custom_draw_function:
                self.config.custom_draw_function(self.image, self.thumbnail_rect, self.viewport)
            else:
                # Call content provider with proper parameters
                self.content_provider.render_thumbnail(
                    self.image, self.thumbnail_rect, self.viewport, self.config.mode
                )
        except Exception as e:
            if NAVIGATOR_DEBUG:
                print(f"Error drawing thumbnail: {e}")

            # Try fallback to wireframe mode if enabled
            if (self.config.behavior.fallback_to_wireframe and
                    self.config.mode != NavigatorMode.WIREFRAME):
                try:
                    self.content_provider.render_thumbnail(
                        self.image, self.thumbnail_rect, self.viewport, NavigatorMode.WIREFRAME
                    )
                except Exception as e2:
                    if NAVIGATOR_DEBUG:
                        print(f"Error in wireframe fallback: {e2}")
                    self._draw_thumbnail_error(str(e))
            else:
                self._draw_thumbnail_error(str(e))

        # Draw thumbnail border
        border_color = self.theme_manager.get_color('control_border')
        pygame.draw.rect(self.image, border_color, self.thumbnail_rect,
                         self.config.layout.thumbnail_border_width)

    def _draw_thumbnail_error(self, error_msg: str):
        """Draw error indicator in thumbnail area"""
        error_bg = self.theme_manager.get_color('error_bg')
        error_text_color = self.theme_manager.get_color('error_text')

        pygame.draw.rect(self.image, error_bg, self.thumbnail_rect)

        # Draw error icon (simple X)
        icon_size = self.config.layout.error_icon_size
        center_x = self.thumbnail_rect.centerx
        center_y = self.thumbnail_rect.centery - 10

        pygame.draw.line(self.image, error_text_color,
                         (center_x - icon_size // 2, center_y - icon_size // 2),
                         (center_x + icon_size // 2, center_y + icon_size // 2), 3)
        pygame.draw.line(self.image, error_text_color,
                         (center_x + icon_size // 2, center_y - icon_size // 2),
                         (center_x - icon_size // 2, center_y + icon_size // 2), 3)

        # Draw error text if enabled
        if self.config.behavior.show_error_details:
            try:
                font = self.theme_manager.get_font(self.config.layout.error_font_size)
                lines = ["Render Error", error_msg[:20] + "..." if len(error_msg) > 20 else error_msg]

                y_offset = center_y + icon_size
                for line in lines:
                    if line:
                        text_surface = font.render(line, True, error_text_color)
                        text_rect = text_surface.get_rect()
                        text_rect.centerx = center_x
                        text_rect.y = y_offset

                        # Only draw if it fits
                        if text_rect.bottom < self.thumbnail_rect.bottom - 5:
                            self.image.blit(text_surface, text_rect)
                            y_offset += text_rect.height + 2
            except Exception:
                pass  # Don't fail on error text rendering

    def _draw_viewport_indicator(self):
        """Draw the viewport rectangle overlay with configuration support"""
        try:
            viewport_rect = self._content_to_thumbnail_rect(
                self.viewport.content_x, self.viewport.content_y,
                self.viewport.content_width, self.viewport.content_height
            )

            min_size = self.config.layout.min_viewport_indicator_size
            if viewport_rect.width >= min_size and viewport_rect.height >= min_size:
                # Clip to thumbnail area
                clipped_rect = viewport_rect.clip(self.thumbnail_rect)

                if clipped_rect.width > 0 and clipped_rect.height > 0:
                    # FIXED: Use theme colors instead of config colors
                    viewport_fill_color = self.theme_manager.get_color('viewport_fill')
                    viewport_border_color = self.theme_manager.get_color('viewport_outline')

                    # Draw semi-transparent fill
                    if viewport_fill_color.a > 0:
                        try:
                            temp_surface = pygame.Surface((clipped_rect.width, clipped_rect.height), pygame.SRCALPHA)
                            temp_surface.fill(viewport_fill_color)
                            self.image.blit(temp_surface, clipped_rect)
                        except Exception as e:
                            if NAVIGATOR_DEBUG:
                                print(f"Error drawing viewport fill: {e}")

                    # Draw border
                    border_width = self.config.layout.viewport_border_width
                    if border_width > 0:
                        pygame.draw.rect(self.image, viewport_border_color,
                                         clipped_rect, border_width)
        except Exception as e:
            if NAVIGATOR_DEBUG:
                print(f"Error drawing viewport indicator: {e}")

    def _draw_selection_highlight(self):
        """Draw selection highlight with configuration support"""
        try:
            selection_bounds = self.content_provider.get_selection_bounds()
            if selection_bounds:
                selection_rect = self._content_to_thumbnail_rect(
                    selection_bounds.x, selection_bounds.y,
                    selection_bounds.width, selection_bounds.height
                )

                # Clip to thumbnail area
                clipped_rect = selection_rect.clip(self.thumbnail_rect)

                if clipped_rect.width > 0 and clipped_rect.height > 0:
                    # FIXED: Use theme colors instead of config colors
                    selection_fill_color = self.theme_manager.get_color('selection_highlight')
                    selection_border_color = self.theme_manager.get_color('selection_border')

                    # Draw selection highlight
                    if selection_fill_color.a > 0:
                        try:
                            temp_surface = pygame.Surface((clipped_rect.width, clipped_rect.height), pygame.SRCALPHA)
                            temp_surface.fill(selection_fill_color)
                            self.image.blit(temp_surface, clipped_rect)
                        except Exception as e:
                            if NAVIGATOR_DEBUG:
                                print(f"Error drawing selection fill: {e}")

                    # Draw selection border
                    border_width = self.config.layout.selection_border_width
                    pygame.draw.rect(self.image, selection_border_color,
                                     clipped_rect, border_width)
        except Exception as e:
            if NAVIGATOR_DEBUG:
                print(f"Error drawing selection highlight: {e}")

    def _draw_content_bounds(self):
        """Draw content boundaries"""
        try:
            content_w, content_h = self.content_provider.get_content_size()
            bounds_rect = self._content_to_thumbnail_rect(0, 0, content_w, content_h)

            # Clip to thumbnail area
            clipped_rect = bounds_rect.clip(self.thumbnail_rect)

            if clipped_rect.width > 0 and clipped_rect.height > 0:
                bounds_color = self.theme_manager.get_color('control_border')
                pygame.draw.rect(self.image, bounds_color, clipped_rect, 1)
        except Exception as e:
            if NAVIGATOR_DEBUG:
                print(f"Error drawing content bounds: {e}")

    def _draw_coordinates(self):
        """Draw coordinate information with configuration support"""
        try:
            coord_text = f"({self.viewport.content_x:.0f}, {self.viewport.content_y:.0f}) {self.viewport.zoom * 100:.0f}%"

            font = self.theme_manager.get_font(self.config.layout.coordinate_font_size)
            text_color = self.theme_manager.get_color('coordinate_text')
            text_surface = font.render(coord_text, True, text_color)

            # Position at bottom-left of thumbnail
            text_rect = text_surface.get_rect()
            padding = self.config.layout.coordinate_padding
            text_rect.bottomleft = (self.thumbnail_rect.x + padding, self.thumbnail_rect.bottom - padding)

            # Draw background
            bg_color = self.theme_manager.get_color('coordinate_bg')
            bg_rect = text_rect.copy()
            bg_rect.inflate(padding * 2, padding)

            temp_surface = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
            temp_surface.fill(bg_color)
            self.image.blit(temp_surface, bg_rect)

            self.image.blit(text_surface, text_rect)
        except Exception as e:
            if NAVIGATOR_DEBUG:
                print(f"Error drawing coordinates: {e}")

    def _draw_error_state(self, error_msg: str):
        """Draw error state for the entire panel"""
        error_bg = self.theme_manager.get_color('error_bg')
        error_text_color = self.theme_manager.get_color('error_text')

        self.image.fill(error_bg)

        try:
            font = self.theme_manager.get_font(self.config.layout.error_font_size)
            text_lines = ["Navigator Error", error_msg[:30] + "..." if len(error_msg) > 30 else error_msg]

            y_offset = self.rect.height // 2 - len(text_lines) * 12
            for line in text_lines:
                if line:
                    text_surface = font.render(line, True, error_text_color)
                    text_rect = text_surface.get_rect()
                    text_rect.centerx = self.rect.width // 2
                    text_rect.y = y_offset
                    self.image.blit(text_surface, text_rect)
                    y_offset += text_rect.height + 4
        except Exception:
            pass  # Don't fail on error rendering

    def _content_to_thumbnail_rect(self, content_x: float, content_y: float,
                                   content_width: float, content_height: float) -> pygame.Rect:
        """Convert content coordinates to thumbnail rect with proper error handling"""
        try:
            # Get content size
            content_w, content_h = self.content_provider.get_content_size()
            if content_w <= 0 or content_h <= 0:
                return pygame.Rect(0, 0, 0, 0)

            # Calculate scale to maintain aspect ratio
            scale_x = self.thumbnail_rect.width / content_w
            scale_y = self.thumbnail_rect.height / content_h
            scale = min(scale_x, scale_y)

            # Calculate scaled content size and offset for centering
            scaled_content_w = content_w * scale
            scaled_content_h = content_h * scale

            offset_x = (self.thumbnail_rect.width - scaled_content_w) / 2
            offset_y = (self.thumbnail_rect.height - scaled_content_h) / 2

            # Convert coordinates
            thumb_x = self.thumbnail_rect.x + offset_x + (content_x * scale)
            thumb_y = self.thumbnail_rect.y + offset_y + (content_y * scale)
            thumb_w = content_width * scale
            thumb_h = content_height * scale

            return pygame.Rect(int(thumb_x), int(thumb_y), int(thumb_w), int(thumb_h))
        except Exception as e:
            if NAVIGATOR_DEBUG:
                print(f"Error converting content to thumbnail coordinates: {e}")
            return pygame.Rect(0, 0, 0, 0)

    def _thumbnail_to_content_point(self, thumb_x: int, thumb_y: int) -> Tuple[float, float]:
        """Convert thumbnail coordinates to content coordinates with error handling"""
        try:
            content_w, content_h = self.content_provider.get_content_size()
            if content_w <= 0 or content_h <= 0:
                return 0.0, 0.0

            # Calculate scale and offset (same as in _content_to_thumbnail_rect)
            scale_x = self.thumbnail_rect.width / content_w
            scale_y = self.thumbnail_rect.height / content_h
            scale = min(scale_x, scale_y)

            scaled_content_w = content_w * scale
            scaled_content_h = content_h * scale

            offset_x = (self.thumbnail_rect.width - scaled_content_w) / 2
            offset_y = (self.thumbnail_rect.height - scaled_content_h) / 2

            # Convert back to content coordinates
            relative_x = thumb_x - self.thumbnail_rect.x - offset_x
            relative_y = thumb_y - self.thumbnail_rect.y - offset_y

            if scale <= 0:
                return 0.0, 0.0

            content_x = relative_x / scale
            content_y = relative_y / scale

            return content_x, content_y
        except Exception as e:
            if NAVIGATOR_DEBUG:
                print(f"Error converting thumbnail to content coordinates: {e}")
            return 0.0, 0.0

    def process_event(self, event: pygame.event.Event) -> bool:
        """Process pygame events with comprehensive handling"""
        consumed = False

        try:
            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.rect.collidepoint(event.pos):
                    self.is_focused = True
                    relative_pos = (event.pos[0] - self.rect.x, event.pos[1] - self.rect.y)

                    if event.button == 1:  # Left click
                        consumed = self._handle_left_click(relative_pos, event.button)
                    elif event.button == 3:  # Right click
                        consumed = self._handle_right_click(relative_pos)
                else:
                    self.is_focused = False

            elif event.type == pygame.MOUSEBUTTONUP:
                relative_pos = (event.pos[0] - self.rect.x, event.pos[1] - self.rect.y)
                consumed = self._handle_mouse_up(relative_pos, event.button)

            elif event.type == pygame.MOUSEMOTION:
                if self.rect.collidepoint(event.pos):
                    relative_pos = (event.pos[0] - self.rect.x, event.pos[1] - self.rect.y)
                    consumed = self._handle_mouse_motion(relative_pos)

            elif event.type == pygame.MOUSEWHEEL:
                if self.rect.collidepoint(pygame.mouse.get_pos()):
                    consumed = self._handle_scroll(event.y)

            elif event.type == pygame.KEYDOWN and self.is_focused:
                if self.config.interaction.keyboard_navigation:
                    consumed = self._handle_key_event(event)

        except Exception as e:
            if NAVIGATOR_DEBUG:
                print(f"Error processing event: {e}")

        return consumed

    def _handle_left_click(self, pos: Tuple[int, int], button: int) -> bool:
        """Handle left mouse click with comprehensive logic"""
        try:
            # Check zoom controls first
            if self.zoom_control and self.zoom_control.rect.collidepoint(pos):
                action = self.zoom_control.handle_click(pos, button)
                if action:
                    self._handle_zoom_action(action)
                    return True

            # Check thumbnail area
            if self.thumbnail_rect.collidepoint(pos):
                if self.config.interaction.click_to_navigate:
                    # Convert click position to content coordinates
                    content_x, content_y = self._thumbnail_to_content_point(pos[0], pos[1])

                    # Center viewport on clicked position
                    self.viewport.set_center(content_x, content_y)
                    if self.config.behavior.clamp_viewport_to_content:
                        self.viewport.clamp_to_content()

                    self._fire_viewport_changed_event()
                    self.needs_rebuild = True
                    self.rebuild_image()

                    # Start dragging if enabled
                    if self.config.interaction.drag_to_pan:
                        self.is_dragging = True
                        self.drag_start_pos = pos
                        self.drag_start_viewport = self.viewport.copy()

                    return True
        except Exception as e:
            if NAVIGATOR_DEBUG:
                print(f"Error handling left click: {e}")

        return False

    def _handle_right_click(self, pos: Tuple[int, int]) -> bool:
        """Handle right mouse click"""
        try:
            if self.thumbnail_rect.collidepoint(pos):
                # Fire navigation clicked event
                content_x, content_y = self._thumbnail_to_content_point(pos[0], pos[1])

                event_data = {
                    'content_position': (content_x, content_y),
                    'thumbnail_position': pos,
                    'ui_element': self
                }
                pygame.event.post(pygame.event.Event(UI_NAVIGATOR_NAVIGATION_CLICKED, event_data))
                return True
        except Exception as e:
            if NAVIGATOR_DEBUG:
                print(f"Error handling right click: {e}")

        return False

    def _handle_mouse_up(self, pos: Tuple[int, int], button: int) -> bool:
        """Handle mouse up events"""
        consumed = False

        try:
            # Handle zoom control mouse up
            if self.zoom_control:
                if self.zoom_control.handle_mouse_up(pos):
                    consumed = True
                    self.needs_rebuild = True
                    self.rebuild_image()

            # Handle drag end
            if button == 1 and self.is_dragging:
                self._handle_drag_end()
                consumed = True
        except Exception as e:
            if NAVIGATOR_DEBUG:
                print(f"Error handling mouse up: {e}")

        return consumed

    def _handle_mouse_motion(self, pos: Tuple[int, int]) -> bool:
        """Handle mouse motion with comprehensive drag support"""
        hover_changed = False

        try:
            # Update zoom control hover
            if self.zoom_control:
                if self.zoom_control.handle_hover(pos):
                    hover_changed = True

            # Handle dragging
            if self.is_dragging and self.drag_start_viewport:
                dx = pos[0] - self.drag_start_pos[0]
                dy = pos[1] - self.drag_start_pos[1]

                # Check drag threshold
                drag_distance = (dx * dx + dy * dy) ** 0.5
                if drag_distance >= self.config.interaction.drag_threshold:
                    # Convert pixel movement to content movement
                    content_w, content_h = self.content_provider.get_content_size()
                    if content_w > 0 and content_h > 0:
                        scale_x = self.thumbnail_rect.width / content_w
                        scale_y = self.thumbnail_rect.height / content_h
                        scale = min(scale_x, scale_y)

                        if scale > 0:
                            content_dx = dx / scale * self.config.interaction.pan_sensitivity
                            content_dy = dy / scale * self.config.interaction.pan_sensitivity

                            self.viewport.content_x = self.drag_start_viewport.content_x + content_dx
                            self.viewport.content_y = self.drag_start_viewport.content_y + content_dy

                            if self.config.behavior.clamp_viewport_to_content:
                                self.viewport.clamp_to_content()

                            self._fire_viewport_changed_event()
                            hover_changed = True
        except Exception as e:
            if NAVIGATOR_DEBUG:
                print(f"Error handling mouse motion: {e}")

        if hover_changed:
            self.needs_rebuild = True
            self.rebuild_image()

        return hover_changed

    def _handle_drag_end(self):
        """Handle end of drag operation"""
        self.is_dragging = False
        self.drag_start_viewport = None

    def _handle_scroll(self, delta: int) -> bool:
        """Handle mouse wheel scroll with configuration support"""
        try:
            if self.config.interaction.zoom_wheel_enabled:
                zoom_factor = self.config.interaction.zoom_wheel_factor

                if delta > 0:
                    new_zoom = self.viewport.zoom * zoom_factor
                else:
                    new_zoom = self.viewport.zoom / zoom_factor

                self.set_zoom(new_zoom)
                return True
        except Exception as e:
            if NAVIGATOR_DEBUG:
                print(f"Error handling scroll: {e}")

        return False

    def _handle_key_event(self, event: pygame.event.Event) -> bool:
        """Handle keyboard events with configuration support"""
        try:
            pan_speed = self.config.interaction.keyboard_pan_speed

            if event.key == pygame.K_f:
                self._fit_content()
                return True
            elif event.key == pygame.K_1:
                self._actual_size()
                return True
            elif event.key == pygame.K_PLUS or event.key == pygame.K_EQUALS:
                self._zoom_in()
                return True
            elif event.key == pygame.K_MINUS:
                self._zoom_out()
                return True
            elif event.key == pygame.K_LEFT:
                self._pan(-pan_speed, 0)
                return True
            elif event.key == pygame.K_RIGHT:
                self._pan(pan_speed, 0)
                return True
            elif event.key == pygame.K_UP:
                self._pan(0, -pan_speed)
                return True
            elif event.key == pygame.K_DOWN:
                self._pan(0, pan_speed)
                return True
            elif event.key == pygame.K_s:
                self.fit_to_selection()
                return True
        except Exception as e:
            if NAVIGATOR_DEBUG:
                print(f"Error handling key event: {e}")

        return False

    def _handle_zoom_action(self, action: str):
        """Handle zoom control actions"""
        try:
            if action == "zoom_in":
                self._zoom_in()
            elif action == "zoom_out":
                self._zoom_out()
            elif action == "fit":
                self._fit_content()
            elif action == "actual_size":
                self._actual_size()
        except Exception as e:
            if NAVIGATOR_DEBUG:
                print(f"Error handling zoom action: {e}")

    def _zoom_in(self):
        """Zoom in to next level with configuration support"""
        try:
            current_zoom = self.viewport.zoom
            zoom_levels = self.config.behavior.zoom_levels

            for zoom_level in zoom_levels:
                if zoom_level > current_zoom:
                    self.set_zoom(zoom_level)
                    return

            # No higher zoom level found, use factor
            max_zoom = min(self.config.behavior.max_zoom, max(zoom_levels) if zoom_levels else 5.0)
            if current_zoom < max_zoom:
                zoom_factor = self.config.interaction.zoom_wheel_factor
                self.set_zoom(min(current_zoom * zoom_factor, max_zoom))
        except Exception as e:
            if NAVIGATOR_DEBUG:
                print(f"Error zooming in: {e}")

    def _zoom_out(self):
        """Zoom out to previous level with configuration support"""
        try:
            current_zoom = self.viewport.zoom
            zoom_levels = self.config.behavior.zoom_levels

            for zoom_level in reversed(zoom_levels):
                if zoom_level < current_zoom:
                    self.set_zoom(zoom_level)
                    return

            # No lower zoom level found, use factor
            min_zoom = max(self.config.behavior.min_zoom, min(zoom_levels) if zoom_levels else 0.1)
            if current_zoom > min_zoom:
                zoom_factor = self.config.interaction.zoom_wheel_factor
                self.set_zoom(max(current_zoom / zoom_factor, min_zoom))
        except Exception as e:
            if NAVIGATOR_DEBUG:
                print(f"Error zooming out: {e}")

    def _fit_content(self):
        """Fit all content in view with configuration support"""
        try:
            content_w, content_h = self.content_provider.get_content_size()
            if content_w <= 0 or content_h <= 0:
                return

            # Calculate zoom to fit content in viewport
            # Use a reasonable base viewport size
            base_viewport_w = 400
            base_viewport_h = 300

            zoom_x = base_viewport_w / content_w
            zoom_y = base_viewport_h / content_h
            zoom = min(zoom_x, zoom_y)

            # Clamp to configured limits
            zoom = max(self.config.behavior.min_zoom, min(self.config.behavior.max_zoom, zoom))

            self.set_zoom(zoom)

            # Center content
            self.viewport.set_center(content_w / 2, content_h / 2)
            if self.config.behavior.clamp_viewport_to_content:
                self.viewport.clamp_to_content()

            self._fire_viewport_changed_event()

            # Fire fit event
            event_data = {'ui_element': self}
            pygame.event.post(pygame.event.Event(UI_NAVIGATOR_FIT_REQUESTED, event_data))
        except Exception as e:
            if NAVIGATOR_DEBUG:
                print(f"Error fitting content: {e}")

    def _actual_size(self):
        """Set zoom to 100% (actual size)"""
        try:
            self.set_zoom(1.0)
        except Exception as e:
            if NAVIGATOR_DEBUG:
                print(f"Error setting actual size: {e}")

    def _pan(self, dx: float, dy: float):
        """Pan the viewport by pixel amounts"""
        try:
            # Convert pixels to content units
            if self.viewport.zoom > 0:
                content_dx = dx / self.viewport.zoom
                content_dy = dy / self.viewport.zoom

                self.viewport.content_x += content_dx
                self.viewport.content_y += content_dy

                if self.config.behavior.clamp_viewport_to_content:
                    self.viewport.clamp_to_content()

                self._fire_viewport_changed_event()
                self.needs_rebuild = True
                self.rebuild_image()
        except Exception as e:
            if NAVIGATOR_DEBUG:
                print(f"Error panning: {e}")

    def _fire_viewport_changed_event(self):
        """Fire viewport changed event"""
        try:
            event_data = {
                'viewport': self.viewport,
                'ui_element': self
            }
            pygame.event.post(pygame.event.Event(UI_NAVIGATOR_VIEWPORT_CHANGED, event_data))
        except Exception as e:
            if NAVIGATOR_DEBUG:
                print(f"Error firing viewport changed event: {e}")

    def _fire_zoom_changed_event(self):
        """Fire zoom changed event"""
        try:
            event_data = {
                'zoom': self.viewport.zoom,
                'ui_element': self
            }
            pygame.event.post(pygame.event.Event(UI_NAVIGATOR_ZOOM_CHANGED, event_data))
        except Exception as e:
            if NAVIGATOR_DEBUG:
                print(f"Error firing zoom changed event: {e}")

    def update(self, time_delta: float):
        """Update the panel with performance considerations"""
        super().update(time_delta)

        try:
            # Throttle updates for performance
            current_time = pygame.time.get_ticks()
            if current_time - self._last_update_time >= self.config.interaction.update_throttle_ms:
                self._last_update_time = current_time

                # Check if we need to rebuild
                if (self.cache_invalid or
                        (self.config.interaction.thumbnail_update_on_change and self.needs_rebuild)):
                    self.cache_invalid = False
                    self.rebuild_image()
        except Exception as e:
            if NAVIGATOR_DEBUG:
                print(f"Error in update: {e}")

    # Public API methods with error handling
    def set_content_provider(self, provider: ContentProvider):
        """Set a new content provider with error handling"""
        try:
            self.content_provider = provider

            # Update viewport size
            content_w, content_h = provider.get_content_size()
            self.viewport.total_content_width = content_w
            self.viewport.total_content_height = content_h

            self.cache_invalid = True
            self.needs_rebuild = True
            self.rebuild_image()

            # Fire content changed event
            event_data = {
                'content_provider': provider,
                'ui_element': self
            }
            pygame.event.post(pygame.event.Event(UI_NAVIGATOR_CONTENT_CHANGED, event_data))
        except Exception as e:
            if NAVIGATOR_DEBUG:
                print(f"Error setting content provider: {e}")

    def set_viewport(self, viewport: NavigatorViewport):
        """Set viewport information with validation"""
        try:
            self.viewport = viewport
            if self.config.behavior.clamp_viewport_to_content:
                self.viewport.clamp_to_content()
            self._fire_viewport_changed_event()
            self.needs_rebuild = True
            self.rebuild_image()
        except Exception as e:
            if NAVIGATOR_DEBUG:
                print(f"Error setting viewport: {e}")

    def get_viewport(self) -> NavigatorViewport:
        """Get current viewport information"""
        return self.viewport

    def set_zoom(self, zoom: float):
        """Set zoom level with comprehensive validation"""
        try:
            old_zoom = self.viewport.zoom

            # Clamp zoom to configured limits
            zoom = max(self.config.behavior.min_zoom,
                       min(self.config.behavior.max_zoom, zoom))

            self.viewport.zoom = zoom

            if old_zoom != self.viewport.zoom:
                # Keep the viewport center the same
                center_x, center_y = self.viewport.get_center()

                # Calculate new viewport size based on zoom
                # Use reasonable base screen dimensions
                base_screen_width = 400
                base_screen_height = 300

                # Convert screen area to content units at current zoom
                self.viewport.content_width = base_screen_width / self.viewport.zoom
                self.viewport.content_height = base_screen_height / self.viewport.zoom

                # Restore center position
                self.viewport.set_center(center_x, center_y)

                if self.config.behavior.clamp_viewport_to_content:
                    self.viewport.clamp_to_content()

                self._fire_zoom_changed_event()
                self.needs_rebuild = True
                self.rebuild_image()
        except Exception as e:
            if NAVIGATOR_DEBUG:
                print(f"Error setting zoom: {e}")

    def fit_to_selection(self):
        """Fit viewport to current selection with error handling"""
        try:
            selection_bounds = self.content_provider.get_selection_bounds()
            if selection_bounds and selection_bounds.width > 0 and selection_bounds.height > 0:
                # Calculate zoom to fit selection
                zoom_x = self.viewport.content_width / selection_bounds.width
                zoom_y = self.viewport.content_height / selection_bounds.height
                zoom = min(zoom_x, zoom_y) * 0.8  # Leave some margin

                # Clamp zoom
                zoom = max(self.config.behavior.min_zoom,
                           min(self.config.behavior.max_zoom, zoom))

                self.set_zoom(zoom)

                # Center on selection
                center_x = selection_bounds.centerx
                center_y = selection_bounds.centery
                self.viewport.set_center(center_x, center_y)

                if self.config.behavior.clamp_viewport_to_content:
                    self.viewport.clamp_to_content()

                self._fire_viewport_changed_event()

                # Fire zoom to selection event
                event_data = {
                    'selection_bounds': selection_bounds,
                    'ui_element': self
                }
                pygame.event.post(pygame.event.Event(UI_NAVIGATOR_ZOOM_TO_SELECTION, event_data))
        except Exception as e:
            if NAVIGATOR_DEBUG:
                print(f"Error fitting to selection: {e}")

    def refresh(self):
        """Force refresh of the navigator"""
        try:
            self.cache_invalid = True
            self.needs_rebuild = True
            self.rebuild_image()
        except Exception as e:
            if NAVIGATOR_DEBUG:
                print(f"Error refreshing navigator: {e}")

    # Configuration update methods
    def update_config(self, config: NavigatorConfig):
        """Update configuration and rebuild if necessary"""
        try:
            old_config = self.config
            self.config = copy.deepcopy(config)

            # Check if layout changed
            layout_changed = (
                    old_config.layout.thumbnail_padding != config.layout.thumbnail_padding or
                    old_config.layout.zoom_control_height != config.layout.zoom_control_height or
                    old_config.behavior.show_zoom_controls != config.behavior.show_zoom_controls
            )

            if layout_changed:
                self._calculate_layout()
                if self.config.behavior.show_zoom_controls:
                    self._create_zoom_control()
                else:
                    self.zoom_control = None

            # Force complete rebuild
            self.cache_invalid = True
            self.needs_rebuild = True
            self._last_rebuild_state = None
            self.rebuild_image()

            if NAVIGATOR_DEBUG:
                print("Navigator configuration updated")
        except Exception as e:
            if NAVIGATOR_DEBUG:
                print(f"Error updating config: {e}")


# Example theme for navigator panel with comprehensive styling
NAVIGATOR_THEME = {
    "navigator_panel": {
        "colours": {
            "dark_bg": "#1e1e1e",
            "thumbnail_bg": "#2d2d2d",
            "normal_border": "#646464",
            "focused_border": "#78a0ff",
            "control_bg": "#3c3c3c",
            "control_border": "#505050",
            "control_text": "#ffffff",
            "hovered_bg": "#505050",
            "pressed_bg": "#646464",
            "disabled_bg": "#282828",
            "disabled_text": "#787878",
            "viewport_outline": "#ffffff",
            "viewport_fill": "#ffffff3c",
            "selection_highlight": "#ffff0064",
            "selection_border": "#ffff00",
            "error_bg": "#503c3c",
            "error_text": "#ff9696",
            "coordinate_bg": "#000000b4",
            "coordinate_text": "#ffffff"
        },
        "font": {
            "name": "arial",
            "size": "12",
            "bold": "0",
            "italic": "0"
        }
    },
    "@navigator": {
        "colours": {
            "dark_bg": "#252525",
            "thumbnail_bg": "#353535"
        }
    },
    "#main_navigator": {
        "colours": {
            "focused_border": "#ff6600"
        }
    },
    "#secondary_navigator": {
        "colours": {
            "dark_bg": "#1a1a1a",
            "normal_border": "#888888"
        }
    }
}


def create_sample_image_content() -> ImageContentProvider:
    """Create sample image content with proper error handling"""
    try:
        # Create a sample image with some patterns
        image = pygame.Surface((800, 600))

        # Fill with gradient
        for y in range(600):
            color_value = int(255 * y / 600)
            color = pygame.Color(color_value // 3, color_value // 2, color_value)
            pygame.draw.line(image, color, (0, y), (800, y))

        # Add some shapes
        for i in range(20):
            x = (i % 5) * 160 + 80
            y = (i // 5) * 120 + 60
            color = pygame.Color(255, 255 - i * 10, i * 10)
            pygame.draw.circle(image, color, (x, y), 30)
            pygame.draw.rect(image, pygame.Color(255, 255, 255),
                             pygame.Rect(x - 40, y - 40, 80, 80), 2)

        provider = ImageContentProvider(image)

        # Set a sample selection
        provider.set_selection(pygame.Rect(200, 150, 200, 150))

        return provider
    except Exception as e:
        if NAVIGATOR_DEBUG:
            print(f"Error creating sample image content: {e}")
        # Return empty provider
        empty_image = pygame.Surface((100, 100))
        empty_image.fill((50, 50, 50))
        return ImageContentProvider(empty_image)


def create_sample_node_graph() -> NodeGraphContentProvider:
    """Create sample node graph content with comprehensive setup"""
    try:
        provider = NodeGraphContentProvider((1200, 800))

        # Add nodes in a hierarchical layout
        root = provider.add_node(100, 100, 120, 60, "Root", pygame.Color(100, 150, 255))

        # Level 1 nodes
        node1 = provider.add_node(50, 250, 100, 50, "Node 1", pygame.Color(150, 200, 100))
        node2 = provider.add_node(200, 250, 100, 50, "Node 2", pygame.Color(150, 200, 100))
        node3 = provider.add_node(350, 250, 100, 50, "Node 3", pygame.Color(150, 200, 100))

        # Level 2 nodes
        node4 = provider.add_node(25, 400, 80, 40, "Child 1", pygame.Color(255, 200, 100))
        node5 = provider.add_node(125, 400, 80, 40, "Child 2", pygame.Color(255, 200, 100))
        node6 = provider.add_node(275, 400, 80, 40, "Child 3", pygame.Color(255, 200, 100))
        node7 = provider.add_node(375, 400, 80, 40, "Child 4", pygame.Color(255, 200, 100))

        # Some distant nodes
        node8 = provider.add_node(600, 200, 100, 50, "Remote", pygame.Color(200, 100, 255))
        node9 = provider.add_node(800, 350, 90, 45, "Isolated", pygame.Color(255, 150, 150))

        # Add connections
        provider.add_connection(root, node1)
        provider.add_connection(root, node2)
        provider.add_connection(root, node3)
        provider.add_connection(node1, node4)
        provider.add_connection(node1, node5)
        provider.add_connection(node2, node6)
        provider.add_connection(node3, node7)
        provider.add_connection(node2, node8)
        provider.add_connection(node8, node9)

        # Set selection
        provider.set_selection([node1, node4, node5])

        return provider
    except Exception as e:
        if NAVIGATOR_DEBUG:
            print(f"Error creating sample node graph: {e}")
        # Return minimal provider
        return NodeGraphContentProvider((100, 100))


def main():
    """Example demonstration of the Navigator Panel with comprehensive configuration"""
    pygame.init()
    screen = pygame.display.set_mode((1200, 800))
    pygame.display.set_caption("Comprehensive Navigator Panel Demo")
    clock = pygame.time.Clock()

    # Create manager with theme
    manager = pygame_gui.UIManager((1200, 800), NAVIGATOR_THEME)

    # Create content providers
    image_provider = create_sample_image_content()
    node_provider = create_sample_node_graph()
    current_provider = node_provider

    # Create viewport with proper initial configuration
    content_w, content_h = current_provider.get_content_size()
    main_content_width = 450
    main_content_height = 350
    initial_zoom = 1.0

    viewport = NavigatorViewport(
        content_x=100, content_y=100,
        content_width=main_content_width / initial_zoom,
        content_height=main_content_height / initial_zoom,
        zoom=initial_zoom,
        total_content_width=content_w, total_content_height=content_h
    )

    # Create comprehensive configuration
    config = NavigatorConfig()
    config.behavior.show_zoom_controls = True
    config.behavior.show_coordinates = True
    config.behavior.show_selection_highlight = True
    config.interaction.click_to_navigate = True
    config.interaction.drag_to_pan = True
    config.interaction.zoom_wheel_enabled = True

    # Create navigator panel
    navigator = NavigatorPanel(
        pygame.Rect(50, 50, 300, 400),
        manager,
        current_provider,
        viewport,
        config,
        object_id=ObjectID(object_id='#main_navigator', class_id='@navigator')
    )

    # Create a second navigator with different configuration
    viewport2 = NavigatorViewport(
        content_x=0, content_y=0,
        content_width=content_w * 0.5, content_height=content_h * 0.5,
        zoom=1.0,
        total_content_width=content_w, total_content_height=content_h
    )

    config2 = NavigatorConfig()
    config2.mode = NavigatorMode.WIREFRAME
    config2.behavior.show_zoom_controls = False
    config2.behavior.show_coordinates = False
    config2.behavior.show_selection_highlight = True

    navigator2 = NavigatorPanel(
        pygame.Rect(400, 50, 250, 300),
        manager,
        node_provider,
        viewport2,
        config2,
        object_id=ObjectID(object_id='#secondary_navigator', class_id='@navigator_two')
    )

    # Instructions
    print("\nComprehensive Navigator Panel Demo")
    print("\nFeatures:")
    print("- Fixed image rendering bug")
    print("- Comprehensive configuration system")
    print("- Improved error handling and debugging")
    print("- Theme management system")
    print("- Performance optimizations")
    print("- Enhanced event handling")

    print("\nControls:")
    print("- Click in navigator to center viewport")
    print("- Drag to pan viewport")
    print("- Mouse wheel to zoom")
    print("- Zoom buttons: +, -, F(it), 1(00%)")
    print("- Arrow keys to pan (when focused)")
    print("- F to fit content, 1 for actual size")
    print("- S to zoom to selection")

    print("\nConfiguration Controls:")
    print("Press T to toggle content type")
    print("Press R to reset viewport")
    print("Press I to toggle info display")
    print("Press M to change navigator mode")
    print("Press C to toggle coordinates")
    print("Press Z to toggle zoom controls")
    print("Press D to toggle debug mode\n")

    # State variables
    using_node_content = True
    info_visible = True
    debug_mode = NAVIGATOR_DEBUG

    running = True
    while running:
        time_delta = clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_t:
                    # Toggle content type
                    using_node_content = not using_node_content
                    new_provider = node_provider if using_node_content else image_provider
                    navigator.set_content_provider(new_provider)
                    print(f"Switched to {'node graph' if using_node_content else 'image'} content")

                elif event.key == pygame.K_r:
                    # Reset viewport
                    if using_node_content:
                        new_viewport = NavigatorViewport(0, 0, 600, 400, 1.0, 1200, 800)
                    else:
                        new_viewport = NavigatorViewport(100, 100, 400, 300, 1.0, 800, 600)
                    navigator.set_viewport(new_viewport)
                    print("Reset viewport")

                elif event.key == pygame.K_i:
                    # Toggle info display
                    info_visible = not info_visible
                    print(f"Info display: {'on' if info_visible else 'off'}")

                elif event.key == pygame.K_m:
                    # Cycle navigator mode
                    modes = list(NavigatorMode)
                    current_mode_index = modes.index(navigator.config.mode)
                    next_mode_index = (current_mode_index + 1) % len(modes)
                    navigator.config.mode = modes[next_mode_index]
                    navigator.refresh()
                    print(f"Navigator mode: {navigator.config.mode.value}")

                elif event.key == pygame.K_c:
                    # Toggle coordinates
                    navigator.config.behavior.show_coordinates = not navigator.config.behavior.show_coordinates
                    navigator.refresh()
                    print(f"Coordinates: {'on' if navigator.config.behavior.show_coordinates else 'off'}")

                elif event.key == pygame.K_z:
                    # Toggle zoom controls
                    navigator.config.behavior.show_zoom_controls = not navigator.config.behavior.show_zoom_controls
                    navigator.update_config(navigator.config)
                    print(f"Zoom controls: {'on' if navigator.config.behavior.show_zoom_controls else 'off'}")

                elif event.key == pygame.K_y:
                    # Toggle theme between light and dark - FIXED VERSION
                    if not hasattr(navigator, 'is_light_theme'):
                        navigator.is_light_theme = False

                    if not navigator.is_light_theme:
                        # Switch to light theme by updating the UIManager's theme
                        light_theme = {
                            "navigator_panel": {
                                "colours": {
                                    "dark_bg": "#f0f0f0",
                                    "thumbnail_bg": "#fafafa",
                                    "normal_border": "#a0a0a0",
                                    "focused_border": "#4682b4",
                                    "control_bg": "#dcdcdc",
                                    "control_border": "#b4b4b4",
                                    "control_text": "#323232",
                                    "hovered_bg": "#c8c8c8",
                                    "pressed_bg": "#b4b4b4",
                                    "viewport_outline": "#2066cc",
                                    "viewport_fill": "#2066cc40",
                                    "selection_highlight": "#ff8c0080",
                                    "selection_border": "#ff6600",
                                    "coordinate_bg": "#ffffffc8",
                                    "coordinate_text": "#323232"
                                }
                            }
                        }

                        # Load the light theme
                        manager.get_theme().load_theme(light_theme)
                        navigator.is_light_theme = True
                        navigator2.is_light_theme = True
                        print("Switched to light theme")
                    else:
                        # Switch back to dark theme
                        manager.get_theme().load_theme(NAVIGATOR_THEME)
                        navigator.is_light_theme = False
                        navigator2.is_light_theme = False
                        print("Switched to dark theme")

                    # Rebuild both navigators
                    navigator.rebuild_from_changed_theme_data()
                    navigator2.rebuild_from_changed_theme_data()

                elif event.key == pygame.K_d:
                #     # Toggle debug mode
                #     global NAVIGATOR_DEBUG
                    if debug_mode:
                        debug_mode = NAVIGATOR_DEBUG
                    else:
                        debug_mode = not NAVIGATOR_DEBUG
                    print(f"Debug mode: {'on' if debug_mode else 'off'}")

                elif event.key == pygame.K_s:
                    # Zoom to selection
                    navigator.fit_to_selection()
                    print("Zoomed to selection")

            # Handle navigator events
            elif event.type == UI_NAVIGATOR_VIEWPORT_CHANGED:
                if debug_mode:
                    vp = event.viewport
                    print(f"Viewport changed: ({vp.content_x:.1f}, {vp.content_y:.1f}) "
                          f"{vp.content_width:.1f}x{vp.content_height:.1f} @ {vp.zoom:.2f}x")

            elif event.type == UI_NAVIGATOR_ZOOM_CHANGED:
                if debug_mode:
                    print(f"Zoom changed: {event.zoom:.2f}x")

            elif event.type == UI_NAVIGATOR_NAVIGATION_CLICKED:
                if debug_mode:
                    pos = event.content_position
                    print(f"Navigation clicked at content position: ({pos[0]:.1f}, {pos[1]:.1f})")

            elif event.type == UI_NAVIGATOR_FIT_REQUESTED:
                if debug_mode:
                    print("Fit to content requested")

            elif event.type == UI_NAVIGATOR_ZOOM_TO_SELECTION:
                if debug_mode:
                    bounds = event.selection_bounds
                    print(f"Zoomed to selection: {bounds}")

            elif event.type == UI_NAVIGATOR_CONTENT_CHANGED:
                if debug_mode:
                    print("Content provider changed")

            # Forward events to manager
            manager.process_events(event)

        # Update
        manager.update(time_delta)

        # Draw
        screen.fill((25, 25, 25))

        # Draw main content area simulation (same as before but with error handling)
        main_content_rect = pygame.Rect(700, 50, 450, 350)
        pygame.draw.rect(screen, pygame.Color(40, 40, 40), main_content_rect)
        pygame.draw.rect(screen, pygame.Color(100, 100, 100), main_content_rect, 2)

        # Simulate content in main area based on viewport
        try:
            vp = navigator.get_viewport()
            if using_node_content:
                # Calculate the scale factor to convert from content coordinates to screen coordinates
                content_to_screen_scale_x = main_content_rect.width / vp.content_width
                content_to_screen_scale_y = main_content_rect.height / vp.content_height

                # FIXED: Draw connections first (so they appear behind nodes)
                for from_idx, to_idx in node_provider.connections:
                    if from_idx < len(node_provider.nodes) and to_idx < len(node_provider.nodes):
                        from_node = node_provider.nodes[from_idx]
                        to_node = node_provider.nodes[to_idx]

                        # Check if both nodes are at least partially visible in viewport
                        from_center_x = from_node['x'] + from_node['width'] / 2
                        from_center_y = from_node['y'] + from_node['height'] / 2
                        to_center_x = to_node['x'] + to_node['width'] / 2
                        to_center_y = to_node['y'] + to_node['height'] / 2

                        viewport_left = vp.content_x
                        viewport_top = vp.content_y
                        viewport_right = vp.content_x + vp.content_width
                        viewport_bottom = vp.content_y + vp.content_height

                        # Check if connection line intersects with viewport (simplified check)
                        connection_left = min(from_center_x, to_center_x)
                        connection_right = max(from_center_x, to_center_x)
                        connection_top = min(from_center_y, to_center_y)
                        connection_bottom = max(from_center_y, to_center_y)

                        if (connection_right > viewport_left and connection_left < viewport_right and
                                connection_bottom > viewport_top and connection_top < viewport_bottom):

                            # Convert to screen coordinates
                            screen_from_x = main_content_rect.x + (
                                        from_center_x - viewport_left) * content_to_screen_scale_x
                            screen_from_y = main_content_rect.y + (
                                        from_center_y - viewport_top) * content_to_screen_scale_y
                            screen_to_x = main_content_rect.x + (
                                        to_center_x - viewport_left) * content_to_screen_scale_x
                            screen_to_y = main_content_rect.y + (to_center_y - viewport_top) * content_to_screen_scale_y

                            # Only draw if both points are reasonable
                            if (main_content_rect.left - 50 <= screen_from_x <= main_content_rect.right + 50 and
                                    main_content_rect.top - 50 <= screen_from_y <= main_content_rect.bottom + 50 and
                                    main_content_rect.left - 50 <= screen_to_x <= main_content_rect.right + 50 and
                                    main_content_rect.top - 50 <= screen_to_y <= main_content_rect.bottom + 50):
                                # Draw connection line
                                line_color = pygame.Color(120, 120, 120)
                                line_width = max(1, int(2 * min(content_to_screen_scale_x, content_to_screen_scale_y)))
                                pygame.draw.line(screen, line_color,
                                                 (int(screen_from_x), int(screen_from_y)),
                                                 (int(screen_to_x), int(screen_to_y)),
                                                 line_width)

                # FIXED: Draw nodes with text labels
                for i, node in enumerate(node_provider.nodes):
                    # Node bounds in content coordinates
                    node_left = node['x']
                    node_top = node['y']
                    node_right = node['x'] + node['width']
                    node_bottom = node['y'] + node['height']

                    # Viewport bounds in content coordinates
                    viewport_left = vp.content_x
                    viewport_top = vp.content_y
                    viewport_right = vp.content_x + vp.content_width
                    viewport_bottom = vp.content_y + vp.content_height

                    # Check if node intersects with viewport
                    if (node_right > viewport_left and node_left < viewport_right and
                            node_bottom > viewport_top and node_top < viewport_bottom):

                        # Calculate the portion of the node that's visible in the viewport
                        visible_left = max(node_left, viewport_left)
                        visible_top = max(node_top, viewport_top)
                        visible_right = min(node_right, viewport_right)
                        visible_bottom = min(node_bottom, viewport_bottom)

                        # Convert to screen coordinates relative to main content rect
                        screen_left = main_content_rect.x + (visible_left - viewport_left) * content_to_screen_scale_x
                        screen_top = main_content_rect.y + (visible_top - viewport_top) * content_to_screen_scale_y
                        screen_right = main_content_rect.x + (visible_right - viewport_left) * content_to_screen_scale_x
                        screen_bottom = main_content_rect.y + (
                                    visible_bottom - viewport_top) * content_to_screen_scale_y

                        # Create screen rectangle
                        screen_rect = pygame.Rect(
                            int(screen_left),
                            int(screen_top),
                            max(1, int(screen_right - screen_left)),
                            max(1, int(screen_bottom - screen_top))
                        )

                        # Only draw if rectangle is valid and within main content area
                        if screen_rect.width > 0 and screen_rect.height > 0:
                            clipped_rect = screen_rect.clip(main_content_rect)
                            if clipped_rect.width > 0 and clipped_rect.height > 0:
                                # Choose node color
                                color = node['color']
                                if i in node_provider.selection:
                                    color = pygame.Color(255, 255, 100)

                                # Draw node rectangle
                                pygame.draw.rect(screen, color, clipped_rect)
                                pygame.draw.rect(screen, pygame.Color(200, 200, 200), clipped_rect, 1)

                                # FIXED: Draw text label if node is large enough and has a label
                                if (clipped_rect.width > 30 and clipped_rect.height > 15 and
                                        node['label'] and len(node['label']) > 0):

                                    try:
                                        # Calculate appropriate font size based on node size
                                        font_size = max(10, min(24, int(clipped_rect.height * 0.6)))
                                        text_font = pygame.font.Font(None, font_size)

                                        # Truncate text if too long
                                        display_text = node['label']
                                        if len(display_text) > 12:
                                            display_text = display_text[:12] + "..."

                                        # Render text
                                        text_surface = text_font.render(display_text, True, pygame.Color(255, 255, 255))
                                        text_rect = text_surface.get_rect()
                                        text_rect.center = clipped_rect.center

                                        # Only draw if text fits within the node
                                        if (text_rect.width <= clipped_rect.width - 4 and
                                                text_rect.height <= clipped_rect.height - 2):
                                            # Draw text background for better readability
                                            bg_rect = text_rect.copy()
                                            bg_rect.inflate(4, 2)
                                            bg_surface = pygame.Surface((bg_rect.width, bg_rect.height),
                                                                        pygame.SRCALPHA)
                                            bg_surface.fill(pygame.Color(0, 0, 0, 128))  # Semi-transparent black
                                            screen.blit(bg_surface, bg_rect)

                                            # Draw the text
                                            screen.blit(text_surface, text_rect)

                                    except Exception as text_error:
                                        if debug_mode:
                                            print(f"Error drawing node text: {text_error}")
                                        # Skip text rendering if there's an error
                                        pass
            else:
                # Image content rendering (unchanged)
                viewport_left = max(0, int(vp.content_x))
                viewport_top = max(0, int(vp.content_y))
                viewport_right = min(image_provider.image.get_width(), int(vp.content_x + vp.content_width))
                viewport_bottom = min(image_provider.image.get_height(), int(vp.content_y + vp.content_height))

                if viewport_right > viewport_left and viewport_bottom > viewport_top:
                    visible_width = viewport_right - viewport_left
                    visible_height = viewport_bottom - viewport_top

                    if visible_width > 0 and visible_height > 0:
                        img_rect = pygame.Rect(int(viewport_left), int(viewport_top),
                                               int(visible_width), int(visible_height))

                        img_rect = img_rect.clip(pygame.Rect(0, 0, image_provider.image.get_width(),
                                                             image_provider.image.get_height()))

                        if img_rect.width > 0 and img_rect.height > 0:
                            cropped = image_provider.image.subsurface(img_rect)

                            scale_x = main_content_rect.width / visible_width
                            scale_y = main_content_rect.height / visible_height
                            scale = min(scale_x, scale_y)

                            scaled_width = int(visible_width * scale)
                            scaled_height = int(visible_height * scale)

                            if scaled_width > 0 and scaled_height > 0:
                                scaled_img = pygame.transform.scale(cropped, (scaled_width, scaled_height))

                                draw_x = main_content_rect.x + (main_content_rect.width - scaled_width) // 2
                                draw_y = main_content_rect.y + (main_content_rect.height - scaled_height) // 2

                                screen.blit(scaled_img, (draw_x, draw_y))

        except Exception as e:
            # Draw error indicator in main content area
            if debug_mode:
                print(f"Error drawing main content: {e}")

            label_font = pygame.font.Font(None, 24)
            error_text = label_font.render("Content Error", True, pygame.Color(255, 100, 100))
            error_rect = error_text.get_rect(center=main_content_rect.center)
            screen.blit(error_text, error_rect)

        # Draw info panel with comprehensive information
        if info_visible:
            info_rect = pygame.Rect(700, 450, 450, 300)
            pygame.draw.rect(screen, pygame.Color(35, 35, 35), info_rect)
            pygame.draw.rect(screen, pygame.Color(80, 80, 80), info_rect, 1)

            font = pygame.font.Font(None, 20)
            small_font = pygame.font.Font(None, 16)

            y_offset = info_rect.y + 10

            # Title
            title = font.render("Navigator Demo Info", True, pygame.Color(255, 255, 255))
            screen.blit(title, (info_rect.x + 10, y_offset))
            y_offset += 30

            # Viewport info
            try:
                vp = navigator.get_viewport()
                config_info = navigator.config

                info_lines = [
                    f"Content Type: {'Node Graph' if using_node_content else 'Image'}",
                    f"Display Mode: {config_info.mode.value.title()}",
                    f"Viewport Position: ({vp.content_x:.1f}, {vp.content_y:.1f})",
                    f"Viewport Size: {vp.content_width:.1f} x {vp.content_height:.1f}",
                    f"Zoom Level: {vp.zoom:.2f}x ({vp.zoom * 100:.0f}%)",
                    f"Total Content: {vp.total_content_width:.0f} x {vp.total_content_height:.0f}",
                    "",
                    "Configuration Status:",
                    f"  Zoom Controls: {'On' if config_info.behavior.show_zoom_controls else 'Off'}",
                    f"  Coordinates: {'On' if config_info.behavior.show_coordinates else 'Off'}",
                    f"  Click Navigation: {'On' if config_info.interaction.click_to_navigate else 'Off'}",
                    f"  Drag Panning: {'On' if config_info.interaction.drag_to_pan else 'Off'}",
                    f"  Zoom Wheel: {'On' if config_info.interaction.zoom_wheel_enabled else 'Off'}",
                    f"  Debug Mode: {'On' if debug_mode else 'Off'}",
                    "",
                    "Navigator 1 (left): Full-featured with configuration",
                    "Navigator 2 (right): Wireframe mode, minimal UI",
                ]

                for line in info_lines:
                    if line and y_offset + 18 < info_rect.bottom - 10:
                        text_color = pygame.Color(200, 200, 200)
                        if line.startswith("  "):
                            text_color = pygame.Color(150, 200, 150)

                        text = small_font.render(line, True, text_color)
                        screen.blit(text, (info_rect.x + 10, y_offset))
                        y_offset += 18

                # Selection info
                if using_node_content and node_provider.selection:
                    if y_offset + 18 < info_rect.bottom - 10:
                        selection_text = small_font.render(f"Selected Nodes: {len(node_provider.selection)}",
                                                           True, pygame.Color(255, 255, 100))
                        screen.blit(selection_text, (info_rect.x + 10, y_offset))
                        y_offset += 18
                elif not using_node_content and image_provider.selection_rect:
                    if y_offset + 18 < info_rect.bottom - 10:
                        sel_rect = image_provider.selection_rect
                        selection_text = small_font.render(
                            f"Selection: {sel_rect.width}x{sel_rect.height} at ({sel_rect.x}, {sel_rect.y})",
                            True, pygame.Color(255, 255, 100))
                        screen.blit(selection_text, (info_rect.x + 10, y_offset))

                # Performance info if debug mode
                if debug_mode and y_offset + 36 < info_rect.bottom - 10:
                    y_offset += 10
                    perf_lines = [
                        "Debug Information:",
                        f"  Cache Invalid: {navigator.cache_invalid}",
                        f"  Needs Rebuild: {navigator.needs_rebuild}",
                        f"  Is Dragging: {navigator.is_dragging}",
                        f"  Is Focused: {navigator.is_focused}",
                    ]

                    for line in perf_lines:
                        if y_offset + 18 < info_rect.bottom - 10:
                            debug_color = pygame.Color(100, 150, 255)
                            if line.startswith("  "):
                                debug_color = pygame.Color(150, 150, 200)

                            text = small_font.render(line, True, debug_color)
                            screen.blit(text, (info_rect.x + 10, y_offset))
                            y_offset += 18

            except Exception as e:
                error_text = small_font.render(f"Info Error: {str(e)[:40]}", True, pygame.Color(255, 100, 100))
                screen.blit(error_text, (info_rect.x + 10, y_offset))

        # Draw labels and status
        try:
            label_font = pygame.font.Font(None, 18)

            # Navigator labels
            nav1_label = label_font.render("Navigator 1 (Full Configuration)", True, pygame.Color(255, 255, 255))
            screen.blit(nav1_label, (50, 30))

            nav2_label = label_font.render("Navigator 2 (Wireframe)", True, pygame.Color(255, 255, 255))
            screen.blit(nav2_label, (400, 30))

            main_label = label_font.render("Main Content View", True, pygame.Color(255, 255, 255))
            screen.blit(main_label, (700, 30))

            # Status indicators
            status_font = pygame.font.Font(None, 14)
            status_y = 10

            # Current mode
            mode_text = f"Mode: {navigator.config.mode.value.title()}"
            mode_surface = status_font.render(mode_text, True, pygame.Color(200, 255, 200))
            screen.blit(mode_surface, (50, status_y))

            # Debug status
            if debug_mode:
                debug_surface = status_font.render("DEBUG", True, pygame.Color(255, 200, 100))
                screen.blit(debug_surface, (200, status_y))

            # Content type
            content_text = f"Content: {'Nodes' if using_node_content else 'Image'}"
            content_surface = status_font.render(content_text, True, pygame.Color(200, 200, 255))
            screen.blit(content_surface, (300, status_y))

        except Exception as e:
            if debug_mode:
                print(f"Error drawing labels: {e}")

        # Draw UI
        manager.draw_ui(screen)
        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()