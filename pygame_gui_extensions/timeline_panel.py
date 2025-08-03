import pygame
import pygame_gui
from pygame_gui.core import UIElement, ObjectID
from pygame_gui.core.interfaces import IContainerLikeInterface
from typing import List, Optional, Dict, Any, Union, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
import math
import time as time_module
import copy

try:
    from pygame_gui.core.interfaces.gui_font_interface import IGUIFontInterface
except ImportError:
    IGUIFontInterface = None

TIMELINE_DEBUG = False

# Define custom pygame-gui events
UI_TIMELINE_FRAME_CHANGED = pygame.USEREVENT + 100
UI_TIMELINE_KEYFRAME_ADDED = pygame.USEREVENT + 101
UI_TIMELINE_KEYFRAME_REMOVED = pygame.USEREVENT + 102
UI_TIMELINE_KEYFRAME_MOVED = pygame.USEREVENT + 103
UI_TIMELINE_KEYFRAME_SELECTED = pygame.USEREVENT + 104
UI_TIMELINE_LAYER_VISIBILITY_CHANGED = pygame.USEREVENT + 105
UI_TIMELINE_LAYER_LOCK_CHANGED = pygame.USEREVENT + 106
UI_TIMELINE_PLAYBACK_STARTED = pygame.USEREVENT + 107
UI_TIMELINE_PLAYBACK_STOPPED = pygame.USEREVENT + 108
UI_TIMELINE_PLAYBACK_PAUSED = pygame.USEREVENT + 109
UI_TIMELINE_ZOOM_CHANGED = pygame.USEREVENT + 110
UI_TIMELINE_SELECTION_CHANGED = pygame.USEREVENT + 111


class InterpolationType(Enum):
    """Animation interpolation types"""
    LINEAR = "linear"
    EASE_IN = "ease_in"
    EASE_OUT = "ease_out"
    EASE_IN_OUT = "ease_in_out"
    STEP = "step"
    BEZIER = "bezier"
    SMOOTH = "smooth"


class LayerType(Enum):
    """Animation layer types"""
    TRANSFORM = "transform"
    PROPERTY = "property"
    EVENT = "event"
    SOUND = "sound"
    CUSTOM = "custom"


class PlaybackState(Enum):
    """Timeline playback states"""
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"
    SCRUBBING = "scrubbing"


class KeyframeFlags(Enum):
    """Keyframe behavior flags"""
    LOCKED = "locked"
    SELECTED = "selected"
    TANGENT_BROKEN = "tangent_broken"
    AUTO_TANGENT = "auto_tangent"


@dataclass
class TimelineLayoutConfig:
    """Layout and spacing configuration for timeline panel"""
    # Panel dimensions
    frame_height: int = 20
    layer_height: int = 40
    scrubber_height: int = 30
    controls_height: int = 35
    layer_label_width: int = 150

    # Timeline elements
    keyframe_size: int = 8
    playhead_width: int = 2
    major_tick_height: int = 15
    minor_tick_height: int = 8

    # Visual spacing
    layer_padding: int = 2
    control_button_spacing: int = 4
    timeline_margin: int = 5

    # Tick marks
    major_tick_interval: int = 10
    minor_tick_interval: int = 5

    # Borders and lines
    border_width: int = 1
    focus_border_width: int = 2
    grid_line_width: int = 1

    # Fallback settings
    fallback_font_size: int = 10


@dataclass
class TimelineInteractionConfig:
    """Interaction and timing configuration"""
    # Zoom settings
    zoom_sensitivity: float = 0.1
    min_zoom: float = 0.1
    max_zoom: float = 10.0

    # Scroll settings
    scroll_speed: int = 20
    auto_scroll_margin: float = 0.1  # Percentage of visible area

    # Drag settings
    drag_threshold: int = 5
    keyframe_click_tolerance: int = 12

    # Timing
    double_click_time: int = 500  # milliseconds
    cursor_blink_time: float = 0.5  # seconds

    # Playback
    default_fps: float = 30.0
    min_fps: float = 1.0
    max_fps: float = 120.0


@dataclass
class TimelineBehaviorConfig:
    """Behavior configuration for timeline panel"""
    # Display options
    show_frame_numbers: bool = True
    show_time_code: bool = True
    show_layer_names: bool = True
    show_interpolation_curves: bool = False
    show_grid: bool = True

    # Interaction behavior
    snap_to_frames: bool = True
    auto_scroll_on_playback: bool = True
    zoom_to_fit_on_clip_change: bool = True
    multi_select_keyframes: bool = True

    # Playback behavior
    loop_by_default: bool = False
    scrub_while_dragging: bool = True
    preview_while_scrubbing: bool = True

    # Keyframe behavior
    auto_tangents: bool = True
    keyframe_shape: str = "diamond"  # diamond, circle, square
    color_keyframes_by_interpolation: bool = True

    # Performance
    cache_rendered_elements: bool = True
    lazy_redraw: bool = True
    max_visible_keyframes: int = 1000

    # Integration
    sync_with_property_panel: bool = True
    sync_with_hierarchy_panel: bool = True


@dataclass
class TimelineConfig:
    """Complete configuration for the timeline panel"""
    # Sub-configurations
    layout: TimelineLayoutConfig = field(default_factory=TimelineLayoutConfig)
    interaction: TimelineInteractionConfig = field(default_factory=TimelineInteractionConfig)
    behavior: TimelineBehaviorConfig = field(default_factory=TimelineBehaviorConfig)

    # Convenience properties for backward compatibility
    @property
    def frame_height(self) -> int:
        return self.layout.frame_height

    @property
    def layer_height(self) -> int:
        return self.layout.layer_height

    @property
    def scrubber_height(self) -> int:
        return self.layout.scrubber_height

    @property
    def controls_height(self) -> int:
        return self.layout.controls_height

    @property
    def keyframe_size(self) -> int:
        return self.layout.keyframe_size

    @property
    def show_frame_numbers(self) -> bool:
        return self.behavior.show_frame_numbers

    @property
    def show_time_code(self) -> bool:
        return self.behavior.show_time_code

    @property
    def snap_to_frames(self) -> bool:
        return self.behavior.snap_to_frames

    @property
    def auto_scroll_on_playback(self) -> bool:
        return self.behavior.auto_scroll_on_playback

    @property
    def default_fps(self) -> float:
        return self.interaction.default_fps


@dataclass
class Keyframe:
    """Individual keyframe in an animation"""
    frame: int
    value: Any
    interpolation: InterpolationType = InterpolationType.LINEAR
    flags: List[KeyframeFlags] = field(default_factory=list)

    # Bezier curve control points (relative to keyframe position)
    in_tangent: Tuple[float, float] = (0.0, 0.0)
    out_tangent: Tuple[float, float] = (0.0, 0.0)

    # Custom data
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_locked(self) -> bool:
        return KeyframeFlags.LOCKED in self.flags

    def is_selected(self) -> bool:
        return KeyframeFlags.SELECTED in self.flags

    def set_selected(self, selected: bool):
        if selected and KeyframeFlags.SELECTED not in self.flags:
            self.flags.append(KeyframeFlags.SELECTED)
        elif not selected and KeyframeFlags.SELECTED in self.flags:
            self.flags.remove(KeyframeFlags.SELECTED)


@dataclass
class AnimationCurve:
    """Animation curve containing keyframes for a specific property"""
    property_name: str
    keyframes: List[Keyframe] = field(default_factory=list)
    default_value: Any = None
    enabled: bool = True

    def add_keyframe(self, keyframe: Keyframe):
        """Add keyframe maintaining frame order"""
        # Remove existing keyframe at same frame
        self.keyframes = [kf for kf in self.keyframes if kf.frame != keyframe.frame]

        # Insert in correct position
        inserted = False
        for i, kf in enumerate(self.keyframes):
            if kf.frame > keyframe.frame:
                self.keyframes.insert(i, keyframe)
                inserted = True
                break

        if not inserted:
            self.keyframes.append(keyframe)

    def remove_keyframe(self, frame: int) -> bool:
        """Remove keyframe at specified frame"""
        original_count = len(self.keyframes)
        self.keyframes = [kf for kf in self.keyframes if kf.frame != frame]
        return len(self.keyframes) < original_count

    def get_keyframe(self, frame: int) -> Optional[Keyframe]:
        """Get keyframe at specific frame"""
        for kf in self.keyframes:
            if kf.frame == frame:
                return kf
        return None

    def get_value_at_frame(self, frame: float) -> Any:
        """Interpolate value at given frame"""
        if not self.keyframes:
            return self.default_value

        # Find surrounding keyframes
        before_kf = None
        after_kf = None

        for kf in self.keyframes:
            if kf.frame <= frame:
                before_kf = kf
            elif kf.frame > frame and after_kf is None:
                after_kf = kf
                break

        # No keyframes or only one
        if before_kf is None:
            return after_kf.value if after_kf else self.default_value
        if after_kf is None:
            return before_kf.value

        # Same frame
        if before_kf.frame == after_kf.frame:
            return before_kf.value

        # Interpolate between keyframes
        return self._interpolate(before_kf, after_kf, frame)

    def _interpolate(self, kf1: Keyframe, kf2: Keyframe, frame: float) -> Any:
        """Interpolate between two keyframes"""
        if kf1.frame == kf2.frame:
            return kf1.value

        t = (frame - kf1.frame) / (kf2.frame - kf1.frame)
        t = max(0.0, min(1.0, t))

        # Handle different value types
        if isinstance(kf1.value, (int, float)) and isinstance(kf2.value, (int, float)):
            return self._interpolate_numeric(kf1, kf2, t)
        elif isinstance(kf1.value, (list, tuple)) and isinstance(kf2.value, (list, tuple)):
            return self._interpolate_vector(kf1, kf2, t)
        elif isinstance(kf1.value, pygame.Color) and isinstance(kf2.value, pygame.Color):
            return self._interpolate_color(kf1, kf2, t)
        else:
            # Default to step interpolation for unsupported types
            return kf1.value if t < 0.5 else kf2.value

    @staticmethod
    def _interpolate_numeric(kf1: Keyframe, kf2: Keyframe, t: float) -> float:
        """Interpolate numeric values"""
        if kf1.interpolation == InterpolationType.STEP:
            return kf1.value
        elif kf1.interpolation == InterpolationType.LINEAR:
            return kf1.value + (kf2.value - kf1.value) * t
        elif kf1.interpolation == InterpolationType.EASE_IN:
            t = t * t
            return kf1.value + (kf2.value - kf1.value) * t
        elif kf1.interpolation == InterpolationType.EASE_OUT:
            t = 1 - (1 - t) * (1 - t)
            return kf1.value + (kf2.value - kf1.value) * t
        elif kf1.interpolation == InterpolationType.EASE_IN_OUT:
            t = 0.5 * (1 - math.cos(math.pi * t))
            return kf1.value + (kf2.value - kf1.value) * t
        elif kf1.interpolation == InterpolationType.SMOOTH:
            t = t * t * (3 - 2 * t)  # Smoothstep
            return kf1.value + (kf2.value - kf1.value) * t
        else:
            return kf1.value + (kf2.value - kf1.value) * t

    def _interpolate_vector(self, kf1: Keyframe, kf2: Keyframe, t: float) -> List[float]:
        """Interpolate vector values"""
        if kf1.interpolation == InterpolationType.STEP:
            return list(kf1.value)

        result = []
        for i in range(min(len(kf1.value), len(kf2.value))):
            if isinstance(kf1.value[i], (int, float)) and isinstance(kf2.value[i], (int, float)):
                # Create temporary keyframes for numeric interpolation
                temp_kf1 = Keyframe(kf1.frame, kf1.value[i], kf1.interpolation)
                temp_kf2 = Keyframe(kf2.frame, kf2.value[i], kf1.interpolation)
                result.append(self._interpolate_numeric(temp_kf1, temp_kf2, t))
            else:
                result.append(kf1.value[i] if t < 0.5 else kf2.value[i])
        return result

    @staticmethod
    def _interpolate_color(kf1: Keyframe, kf2: Keyframe, t: float) -> pygame.Color:
        """Interpolate color values"""
        if kf1.interpolation == InterpolationType.STEP:
            return pygame.Color(kf1.value)

        r = int(kf1.value.r + (kf2.value.r - kf1.value.r) * t)
        g = int(kf1.value.g + (kf2.value.g - kf1.value.g) * t)
        b = int(kf1.value.b + (kf2.value.b - kf1.value.b) * t)
        a = int(kf1.value.a + (kf2.value.a - kf1.value.a) * t)

        return pygame.Color(max(0, min(255, r)), max(0, min(255, g)),
                            max(0, min(255, b)), max(0, min(255, a)))


@dataclass
class AnimationLayer:
    """Layer containing multiple animation curves"""
    id: str
    name: str
    layer_type: LayerType = LayerType.PROPERTY
    curves: List[AnimationCurve] = field(default_factory=list)

    # Layer properties
    visible: bool = True
    locked: bool = False
    muted: bool = False
    solo: bool = False

    # Visual properties
    color: pygame.Color = field(default_factory=lambda: pygame.Color(150, 150, 150))
    height: int = 40

    # Target object reference (optional)
    target_object: Any = None
    target_property_path: Optional[str] = None

    # Custom data
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_curve(self, curve: AnimationCurve):
        """Add animation curve to layer"""
        # Remove existing curve with same property name
        self.curves = [c for c in self.curves if c.property_name != curve.property_name]
        self.curves.append(curve)

    def remove_curve(self, property_name: str) -> bool:
        """Remove animation curve by property name"""
        original_count = len(self.curves)
        self.curves = [c for c in self.curves if c.property_name != property_name]
        return len(self.curves) < original_count

    def get_curve(self, property_name: str) -> Optional[AnimationCurve]:
        """Get animation curve by property name"""
        for curve in self.curves:
            if curve.property_name == property_name:
                return curve
        return None

    def get_all_keyframes(self) -> List[Tuple[AnimationCurve, Keyframe]]:
        """Get all keyframes from all curves"""
        keyframes = []
        for curve in self.curves:
            for kf in curve.keyframes:
                keyframes.append((curve, kf))
        return sorted(keyframes, key=lambda x: x[1].frame)

    def get_keyframes_at_frame(self, frame: int) -> List[Tuple[AnimationCurve, Keyframe]]:
        """Get all keyframes at specific frame"""
        keyframes = []
        for curve in self.curves:
            kf = curve.get_keyframe(frame)
            if kf:
                keyframes.append((curve, kf))
        return keyframes


@dataclass
class AnimationClip:
    """Animation clip containing layers and global settings"""
    name: str
    layers: List[AnimationLayer] = field(default_factory=list)

    # Timeline settings
    length: int = 300  # frames
    fps: float = 30.0
    start_frame: int = 0

    # Playback settings
    loop: bool = False
    ping_pong: bool = False

    # Custom data
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_layer(self, layer: AnimationLayer):
        """Add animation layer"""
        self.layers.append(layer)

    def remove_layer(self, layer_id: str) -> bool:
        """Remove layer by ID"""
        original_count = len(self.layers)
        self.layers = [layer for layer in self.layers if layer.id != layer_id]
        return len(self.layers) < original_count

    def get_layer(self, layer_id: str) -> Optional[AnimationLayer]:
        """Get layer by ID"""
        for layer in self.layers:
            if layer.id == layer_id:
                return layer
        return None

    def get_duration_seconds(self) -> float:
        """Get clip duration in seconds"""
        return self.length / self.fps if self.fps > 0 else 0.0

    def frame_to_time(self, frame: float) -> float:
        """Convert frame to time in seconds"""
        return frame / self.fps if self.fps > 0 else 0.0

    def time_to_frame(self, time_seconds: float) -> float:
        """Convert time to frame"""
        return time_seconds * self.fps


class TimelineThemeManager:
    """Manages theming for the timeline panel"""

    def __init__(self, ui_manager: pygame_gui.UIManager, element_ids: List[str]):
        self.ui_manager = ui_manager
        self.element_ids = element_ids
        self.themed_colors = {}
        self.themed_font = None
        self._update_theme_data()

    def _update_theme_data(self):
        """Update theme-dependent data with comprehensive fallbacks"""
        # Default color mappings with fallbacks
        color_mappings = {
            'timeline_bg': pygame.Color(40, 40, 40),
            'controls_bg': pygame.Color(35, 35, 35),
            'scrubber_bg': pygame.Color(45, 45, 45),
            'layer_bg': pygame.Color(50, 50, 50),
            'layer_bg_alt': pygame.Color(45, 45, 45),
            'layer_label_bg': pygame.Color(55, 55, 55),
            'normal_text': pygame.Color(255, 255, 255),
            'disabled_text': pygame.Color(150, 150, 150),
            'layer_text': pygame.Color(220, 220, 220),
            'grid_line': pygame.Color(60, 60, 60),
            'major_tick': pygame.Color(200, 200, 200),
            'minor_tick': pygame.Color(150, 150, 150),
            'playhead': pygame.Color(255, 80, 80),
            'playhead_handle': pygame.Color(255, 100, 100),
            'selection': pygame.Color(100, 150, 255),
            'selection_bg': pygame.Color(70, 130, 180),
            'hover_bg': pygame.Color(60, 60, 60),
            'focused_bg': pygame.Color(80, 120, 160),
            'keyframe_linear': pygame.Color(100, 150, 255),
            'keyframe_ease_in': pygame.Color(100, 255, 100),
            'keyframe_ease_out': pygame.Color(255, 100, 100),
            'keyframe_ease_in_out': pygame.Color(255, 150, 100),
            'keyframe_step': pygame.Color(200, 200, 200),
            'keyframe_bezier': pygame.Color(255, 100, 255),
            'keyframe_smooth': pygame.Color(100, 255, 255),
            'keyframe_selected': pygame.Color(255, 255, 100),
            'keyframe_locked': pygame.Color(120, 120, 120),
            'keyframe_outline': pygame.Color(20, 20, 20),
            'button_bg': pygame.Color(60, 60, 60),
            'button_hover': pygame.Color(80, 80, 80),
            'button_pressed': pygame.Color(40, 40, 40),
            'button_text': pygame.Color(255, 255, 255),
            'border': pygame.Color(100, 100, 100),
            'focus_border': pygame.Color(120, 160, 255),
            'layer_border': pygame.Color(80, 80, 80),
            'time_cursor': pygame.Color(255, 255, 255),
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

            # Get themed font
            try:
                if hasattr(theme, 'get_font'):
                    self.themed_font = theme.get_font(self.element_ids)
                else:
                    raise Exception("No font method")
            except Exception:
                try:
                    self.themed_font = pygame.font.SysFont('Arial', 10)
                except:
                    self.themed_font = pygame.font.Font(None, 10)

        except Exception as e:
            if TIMELINE_DEBUG:
                print(f"Error getting theme data: {e}")
            # Complete fallback
            self.themed_colors = color_mappings
            try:
                self.themed_font = pygame.font.SysFont('Arial', 10)
            except:
                self.themed_font = pygame.font.Font(None, 10)

    def rebuild_from_changed_theme_data(self):
        """Called when theme data changes"""
        self._update_theme_data()

    def get_color(self, color_id: str, fallback: pygame.Color = None) -> pygame.Color:
        """Get a themed color with fallback"""
        return self.themed_colors.get(color_id, fallback or pygame.Color(255, 255, 255))

    def get_font(self):
        """Get the themed font"""
        return self.themed_font


class TimelineRenderer:
    """Handles rendering of timeline elements with configuration support"""

    def __init__(self, config: TimelineConfig, theme_manager: TimelineThemeManager):
        self.config = config
        self.theme_manager = theme_manager

    def draw_timeline_background(self, surface: pygame.Surface, rect: pygame.Rect):
        """Draw timeline background with grid"""
        bg_color = self.theme_manager.get_color('timeline_bg')
        surface.fill(bg_color)

        if self.config.behavior.show_grid:
            self._draw_grid(surface, rect)

    def _draw_grid(self, surface: pygame.Surface, rect: pygame.Rect):
        """Draw timeline grid lines"""
        grid_color = self.theme_manager.get_color('grid_line')

        # Simplified grid drawing - in a real implementation, this would be more sophisticated
        spacing = 50  # pixels between grid lines
        for x in range(0, rect.width, spacing):
            pygame.draw.line(surface, grid_color, (x, 0), (x, rect.height),
                             self.config.layout.grid_line_width)

    def draw_keyframe(self, surface: pygame.Surface, pos: Tuple[int, int],
                      keyframe: Keyframe) -> pygame.Rect:
        """Draw a keyframe at specified position"""
        size = self.config.layout.keyframe_size
        x, y = pos

        # Choose color based on keyframe state and configuration
        if keyframe.is_selected():
            color = self.theme_manager.get_color('keyframe_selected')
        elif keyframe.is_locked():
            color = self.theme_manager.get_color('keyframe_locked')
        elif self.config.behavior.color_keyframes_by_interpolation:
            # Color by interpolation type
            color_map = {
                InterpolationType.LINEAR: 'keyframe_linear',
                InterpolationType.EASE_IN: 'keyframe_ease_in',
                InterpolationType.EASE_OUT: 'keyframe_ease_out',
                InterpolationType.EASE_IN_OUT: 'keyframe_ease_in_out',
                InterpolationType.STEP: 'keyframe_step',
                InterpolationType.BEZIER: 'keyframe_bezier',
                InterpolationType.SMOOTH: 'keyframe_smooth',
            }
            color_key = color_map.get(keyframe.interpolation, 'keyframe_linear')
            color = self.theme_manager.get_color(color_key)
        else:
            color = self.theme_manager.get_color('keyframe_linear')

        # Draw keyframe shape based on configuration
        shape = self.config.behavior.keyframe_shape
        keyframe_rect = pygame.Rect(x - size // 2, y - size // 2, size, size)

        if shape == "diamond":
            points = [
                (x, y - size // 2),
                (x + size // 2, y),
                (x, y + size // 2),
                (x - size // 2, y)
            ]
            pygame.draw.polygon(surface, color, points)
            # Draw outline
            outline_color = self.theme_manager.get_color('keyframe_outline')
            pygame.draw.polygon(surface, outline_color, points, 1)
        elif shape == "circle":
            pygame.draw.circle(surface, color, (x, y), size // 2)
            # Draw outline
            outline_color = self.theme_manager.get_color('keyframe_outline')
            pygame.draw.circle(surface, outline_color, (x, y), size // 2, 1)
        else:  # square
            pygame.draw.rect(surface, color, keyframe_rect)
            # Draw outline
            outline_color = self.theme_manager.get_color('keyframe_outline')
            pygame.draw.rect(surface, outline_color, keyframe_rect, 1)

        return keyframe_rect

    def draw_playhead(self, surface: pygame.Surface, x: int, rect: pygame.Rect):
        """Draw playhead at specified x position"""
        playhead_color = self.theme_manager.get_color('playhead')
        pygame.draw.line(surface, playhead_color, (x, rect.top), (x, rect.bottom),
                         self.config.layout.playhead_width)

        # Draw playhead handle
        handle_color = self.theme_manager.get_color('playhead_handle')
        handle_size = 8
        handle_rect = pygame.Rect(x - handle_size // 2, rect.top, handle_size, handle_size)
        pygame.draw.rect(surface, handle_color, handle_rect)

    def draw_layer_background(self, surface: pygame.Surface, rect: pygame.Rect,
                              layer: AnimationLayer, is_alternate: bool = False):
        """Draw layer background"""
        if is_alternate:
            bg_color = self.theme_manager.get_color('layer_bg_alt')
        else:
            bg_color = self.theme_manager.get_color('layer_bg')

        surface.fill(bg_color)

        # Draw layer border if configured
        if hasattr(self.config.layout, 'show_layer_borders') and self.config.layout.show_layer_borders:
            border_color = self.theme_manager.get_color('layer_border')
            pygame.draw.rect(surface, border_color, rect, self.config.layout.border_width)


class TimelinePanel(UIElement):
    """Main timeline/animation panel widget with comprehensive configuration"""

    def __init__(self, relative_rect: pygame.Rect,
                 manager: pygame_gui.UIManager,
                 config: TimelineConfig = None,
                 container: IContainerLikeInterface = None,
                 object_id: Union[ObjectID, str, None] = None,
                 anchors: Dict[str, str] = None):

        # Handle object_id properly
        if isinstance(object_id, ObjectID):
            self._object_id = object_id
        elif isinstance(object_id, str):
            self._object_id = ObjectID(object_id=object_id, class_id=None)
        else:
            self._object_id = ObjectID(object_id='#timeline_panel', class_id=None)

        super().__init__(relative_rect, manager, container,
                         starting_height=1, layer_thickness=1,
                         anchors=anchors, object_id=self._object_id)

        self.config = config or TimelineConfig()

        # Create theme manager
        element_ids = ['timeline_panel']
        if hasattr(self, 'object_ids') and self.object_ids:
            element_ids.extend(self.object_ids)
        self.theme_manager = TimelineThemeManager(manager, element_ids)

        # Animation data
        self.clip: Optional[AnimationClip] = None
        self.current_frame: float = 0.0
        self.playback_state = PlaybackState.STOPPED
        self.selection: List[Tuple[str, str, int]] = []  # [(layer_id, curve_name, frame)]

        # Playback timing
        # self.last_playback_time = 0.0
        # self.playback_start_frame = 0.0

        # View settings
        self.zoom = 1.0
        self.scroll_x = 0.0
        self.scroll_y = 0.0

        # UI state
        self.is_scrubbing = False
        self.is_dragging_keyframe = False
        self.drag_start_pos = (0, 0)
        self.drag_start_frame = 0.0
        self.hovered_keyframe: Optional[Tuple[str, str, int]] = None
        self.focused_layer: Optional[str] = None
        self.is_panel_focused = False

        # Layout rects
        self.controls_rect = pygame.Rect(0, 0, 0, 0)
        self.scrubber_rect = pygame.Rect(0, 0, 0, 0)
        self.timeline_rect = pygame.Rect(0, 0, 0, 0)
        self.layers_rect = pygame.Rect(0, 0, 0, 0)
        self.layer_labels_rect = pygame.Rect(0, 0, 0, 0)

        # Renderer
        self.renderer = TimelineRenderer(self.config, self.theme_manager)

        # Integration callbacks
        self.frame_change_callback: Optional[Callable[[float], None]] = None
        self.keyframe_change_callback: Optional[Callable[[str, str, int, Any], None]] = None

        # Performance tracking
        self._last_rebuild_state = None

        # Create the image surface
        self.image = pygame.Surface(self.rect.size).convert()

        # Initialize
        self.setup_layout()
        self.rebuild_image()

    def _needs_rebuild(self) -> bool:
        """Check if UI needs rebuilding with better performance tracking"""
        current_state = {
            'current_frame': self.current_frame,
            'zoom': self.zoom,
            'scroll_x': self.scroll_x,
            'scroll_y': self.scroll_y,
            'playback_state': self.playback_state,
            'clip_id': id(self.clip) if self.clip else None,
            'selection_count': len(self.selection),
            'rect_size': (self.rect.width, self.rect.height),
            'layer_count': len(self.clip.layers) if self.clip else 0,
            'hovered_keyframe': self.hovered_keyframe,
            'panel_focused': self.is_panel_focused,
        }

        if current_state != self._last_rebuild_state:
            self._last_rebuild_state = current_state
            return True

        return False

    def rebuild_from_changed_theme_data(self):
        """Called when theme data changes"""
        self.theme_manager.rebuild_from_changed_theme_data()
        self.renderer = TimelineRenderer(self.config, self.theme_manager)
        self._last_rebuild_state = None  # Force rebuild
        self.rebuild_image()

    def setup_layout(self):
        """Setup layout rectangles based on configuration"""
        layout = self.config.layout

        self.controls_rect = pygame.Rect(
            0, 0, self.rect.width, layout.controls_height
        )

        self.scrubber_rect = pygame.Rect(
            layout.layer_label_width, layout.controls_height,
            self.rect.width - layout.layer_label_width, layout.scrubber_height
        )

        timeline_y = layout.controls_height + layout.scrubber_height
        timeline_height = self.rect.height - timeline_y

        # Layer labels area
        self.layer_labels_rect = pygame.Rect(
            0, timeline_y,
            layout.layer_label_width, timeline_height
        )

        # Main timeline area
        self.timeline_rect = pygame.Rect(
            layout.layer_label_width, timeline_y,
            self.rect.width - layout.layer_label_width, timeline_height
        )

        # Layers area within timeline
        self.layers_rect = self.timeline_rect.copy()

    def rebuild_image(self):
        """Rebuild the image surface with performance optimizations"""
        if not self.config.behavior.lazy_redraw or self._needs_rebuild():
            # Fill background
            bg_color = self.theme_manager.get_color('timeline_bg')
            self.image.fill(bg_color)

            # Draw components
            self._draw_controls()
            self._draw_scrubber()
            self._draw_layer_labels()
            self._draw_timeline()

            # Draw border
            border_color = self.theme_manager.get_color('border')
            pygame.draw.rect(self.image, border_color, self.image.get_rect(),
                             self.config.layout.border_width)

            # Draw focus indicator
            if self.is_panel_focused:
                focus_color = self.theme_manager.get_color('focus_border')
                pygame.draw.rect(self.image, focus_color, self.image.get_rect(),
                                 self.config.layout.focus_border_width)

    def _draw_controls(self):
        """Draw playback controls with improved configuration support"""
        if self.controls_rect.height <= 0:
            return

        try:
            controls_surface = self.image.subsurface(self.controls_rect)
        except (ValueError, pygame.error):
            return

        # Background
        bg_color = self.theme_manager.get_color('controls_bg')
        controls_surface.fill(bg_color)

        # Draw playback buttons
        layout = self.config.layout
        button_size = min(24, self.controls_rect.height - 6)
        button_y = (self.controls_rect.height - button_size) // 2
        button_spacing = button_size + layout.control_button_spacing

        buttons = [
            ("<<", self._rewind_to_start),
            ("|<", self._step_backward),
            (">" if self.playback_state != PlaybackState.PLAYING else "||", self._toggle_playback),
            (">|", self._step_forward),
            (">>", self._fast_forward_to_end),
        ]

        button_x = 10
        for button_text, button_action in buttons:
            button_rect = pygame.Rect(button_x, button_y, button_size, button_size)

            # Button background
            button_color = self.theme_manager.get_color('button_bg')
            pygame.draw.rect(controls_surface, button_color, button_rect)

            # Button border
            border_color = self.theme_manager.get_color('border')
            pygame.draw.rect(controls_surface, border_color, button_rect, layout.border_width)

            # Button text
            try:
                text_color = self.theme_manager.get_color('button_text')
                font = self.theme_manager.get_font()

                if hasattr(font, 'render_premul'):
                    text_surface = font.render_premul(button_text, text_color)
                else:
                    text_surface = font.render(button_text, True, text_color)

                text_rect = text_surface.get_rect(center=button_rect.center)
                controls_surface.blit(text_surface, text_rect)
            except Exception:
                pass

            button_x += button_spacing

        # Draw frame/time display
        self._draw_time_display(controls_surface, button_x + 20)

    def _draw_time_display(self, surface: pygame.Surface, x_offset: int):
        """Draw frame and time information"""
        frame_text = f"Frame: {int(self.current_frame)}"

        if self.clip:
            time_text = f"Time: {self.clip.frame_to_time(self.current_frame):.2f}s"
            fps_text = f"FPS: {self.clip.fps:.1f}"
            length_text = f"Length: {self.clip.length}"
        else:
            time_text = "Time: 0.00s"
            fps_text = f"FPS: {self.config.interaction.default_fps:.1f}"
            length_text = "Length: 0"

        text_info = []
        if self.config.behavior.show_frame_numbers:
            text_info.append(frame_text)
        if self.config.behavior.show_time_code:
            text_info.append(time_text)
            text_info.append(fps_text)
        text_info.append(length_text)

        try:
            text_color = self.theme_manager.get_color('normal_text')
            font = self.theme_manager.get_font()

            text_x = x_offset
            text_y = (self.controls_rect.height - 12) // 2

            for text in text_info:
                if hasattr(font, 'render_premul'):
                    text_surface = font.render_premul(text, text_color)
                else:
                    text_surface = font.render(text, True, text_color)

                surface.blit(text_surface, (text_x, text_y))
                text_x += text_surface.get_width() + 15

        except Exception:
            pass

    def _draw_scrubber(self):
        """Draw timeline scrubber with frame markers"""
        if self.scrubber_rect.height <= 0:
            return

        try:
            scrubber_surface = self.image.subsurface(self.scrubber_rect)
        except (ValueError, pygame.error):
            return

        # Background
        bg_color = self.theme_manager.get_color('scrubber_bg')
        scrubber_surface.fill(bg_color)

        if not self.clip:
            return

        # Calculate frame positions
        frames_per_pixel = 1.0 / self.zoom
        start_frame = self.scroll_x * frames_per_pixel
        end_frame = start_frame + self.scrubber_rect.width * frames_per_pixel

        # Draw frame markers with configuration
        layout = self.config.layout
        behavior = self.config.behavior

        major_color = self.theme_manager.get_color('major_tick')
        minor_color = self.theme_manager.get_color('minor_tick')

        for frame in range(int(start_frame), int(end_frame) + 1):
            if frame < 0 or frame > self.clip.length:
                continue

            x = int((frame - start_frame) / frames_per_pixel)
            if x < 0 or x >= self.scrubber_rect.width:
                continue

            # Major or minor tick
            if frame % layout.major_tick_interval == 0:
                color = major_color
                height = layout.major_tick_height

                # Draw frame number if configured
                if behavior.show_frame_numbers:
                    self._draw_frame_number(scrubber_surface, x, frame)

            elif frame % layout.minor_tick_interval == 0:
                color = minor_color
                height = layout.minor_tick_height
            else:
                continue

            pygame.draw.line(scrubber_surface, color, (x, 0), (x, height))

        # Draw playhead in scrubber
        playhead_x = int((self.current_frame - start_frame) / frames_per_pixel)
        if 0 <= playhead_x < self.scrubber_rect.width:
            self.renderer.draw_playhead(scrubber_surface, playhead_x,
                                        pygame.Rect(0, 0, self.scrubber_rect.width,
                                                    self.scrubber_rect.height))

    def _draw_frame_number(self, surface: pygame.Surface, x: int, frame: int):
        """Draw frame number at position"""
        try:
            text_color = self.theme_manager.get_color('normal_text')
            font = self.theme_manager.get_font()

            if hasattr(font, 'render_premul'):
                text_surface = font.render_premul(str(frame), text_color)
            else:
                text_surface = font.render(str(frame), True, text_color)

            text_rect = text_surface.get_rect()
            text_rect.centerx = x
            text_rect.bottom = self.scrubber_rect.height - 2

            if text_rect.left >= 0 and text_rect.right < self.scrubber_rect.width:
                surface.blit(text_surface, text_rect)
        except Exception:
            pass

    def _draw_layer_labels(self):
        """Draw layer labels area with configuration support"""
        if self.layer_labels_rect.width <= 0 or not self.clip:
            return

        try:
            labels_surface = self.image.subsurface(self.layer_labels_rect)
        except (ValueError, pygame.error):
            return

        # Background
        bg_color = self.theme_manager.get_color('layer_label_bg')
        labels_surface.fill(bg_color)

        if not self.config.behavior.show_layer_names:
            return

        # Draw layer names
        layer_y = -self.scroll_y
        for i, layer in enumerate(self.clip.layers):
            if layer_y + layer.height < 0:
                layer_y += layer.height
                continue
            if layer_y > self.layer_labels_rect.height:
                break

            layer_rect = pygame.Rect(0, int(layer_y), self.layer_labels_rect.width, layer.height)

            # Layer background
            if layer_rect.bottom > 0 and layer_rect.top < self.layer_labels_rect.height:
                clipped_rect = layer_rect.clip(pygame.Rect(0, 0, self.layer_labels_rect.width,
                                                           self.layer_labels_rect.height))
                if clipped_rect.width > 0 and clipped_rect.height > 0:
                    try:
                        layer_surface = labels_surface.subsurface(clipped_rect)
                        bg_color = self.theme_manager.get_color('layer_bg_alt' if i % 2 else 'layer_bg')
                        layer_surface.fill(bg_color)
                    except (ValueError, pygame.error):
                        pass

                # Layer name text
                if layer_rect.height > 15:  # Only draw text if layer is tall enough
                    try:
                        text_color = (self.theme_manager.get_color('disabled_text') if not layer.visible
                                      else self.theme_manager.get_color('layer_text'))
                        font = self.theme_manager.get_font()

                        if hasattr(font, 'render_premul'):
                            text_surface = font.render_premul(layer.name, text_color)
                        else:
                            text_surface = font.render(layer.name, True, text_color)

                        text_rect = text_surface.get_rect()
                        text_rect.left = 5
                        text_rect.centery = layer_y + layer.height // 2

                        if (text_rect.bottom <= self.layer_labels_rect.height and
                                text_rect.top >= 0):
                            labels_surface.blit(text_surface, text_rect)
                    except Exception:
                        pass

            layer_y += layer.height

    def _draw_timeline(self):
        """Draw timeline with layers and keyframes"""
        if self.timeline_rect.height <= 0 or not self.clip:
            return

        try:
            timeline_surface = self.image.subsurface(self.timeline_rect)
        except (ValueError, pygame.error):
            return

        # Draw timeline background with grid
        self.renderer.draw_timeline_background(timeline_surface, self.timeline_rect)

        # Calculate visible area
        frames_per_pixel = 1.0 / self.zoom
        start_frame = self.scroll_x * frames_per_pixel
        end_frame = start_frame + self.timeline_rect.width * frames_per_pixel

        # Performance optimization: limit visible keyframes
        total_keyframes = 0

        # Draw layers
        layer_y = -self.scroll_y
        for i, layer in enumerate(self.clip.layers):
            if layer_y + layer.height < 0:
                layer_y += layer.height
                continue
            if layer_y > self.timeline_rect.height:
                break

            # Draw layer background
            layer_rect = pygame.Rect(0, int(layer_y), self.timeline_rect.width, layer.height)
            if layer_rect.bottom > 0 and layer_rect.top < self.timeline_rect.height:
                clipped_rect = layer_rect.clip(pygame.Rect(0, 0, self.timeline_rect.width,
                                                           self.timeline_rect.height))
                if clipped_rect.width > 0 and clipped_rect.height > 0:
                    try:
                        layer_surface = timeline_surface.subsurface(clipped_rect)
                        self.renderer.draw_layer_background(layer_surface, clipped_rect, layer, i % 2 == 1)
                    except (ValueError, pygame.error):
                        pass

                # Draw keyframes for this layer
                if total_keyframes < self.config.behavior.max_visible_keyframes:
                    drawn = self._draw_layer_keyframes(timeline_surface, layer, layer_y,
                                                       start_frame, end_frame, frames_per_pixel)
                    total_keyframes += drawn

            layer_y += layer.height

        # Draw playhead in timeline
        playhead_x = int((self.current_frame - start_frame) / frames_per_pixel)
        if 0 <= playhead_x < self.timeline_rect.width:
            self.renderer.draw_playhead(timeline_surface, playhead_x,
                                        pygame.Rect(0, 0, self.timeline_rect.width,
                                                    self.timeline_rect.height))

    def _draw_layer_keyframes(self, surface: pygame.Surface, layer: AnimationLayer,
                              layer_y: float, start_frame: float, end_frame: float,
                              frames_per_pixel: float) -> int:
        """Draw keyframes for a specific layer with performance tracking"""
        if not layer.visible:
            return 0

        keyframes_drawn = 0

        # Get all keyframes in visible range
        for curve in layer.curves:
            for kf in curve.keyframes:
                if start_frame <= kf.frame <= end_frame:
                    x = int((kf.frame - start_frame) / frames_per_pixel)
                    y = int(layer_y + layer.height // 2)

                    if 0 <= x < self.timeline_rect.width and 0 <= y < self.timeline_rect.height:
                        # Check if this keyframe is selected
                        is_selected = (layer.id, curve.property_name, kf.frame) in self.selection
                        if is_selected:
                            kf.set_selected(True)
                        else:
                            kf.set_selected(False)

                        self.renderer.draw_keyframe(surface, (x, y), kf)
                        keyframes_drawn += 1

        return keyframes_drawn

    def process_event(self, event: pygame.event.Event) -> bool:
        """Process pygame events with comprehensive handling"""
        consumed = False

        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.is_panel_focused = True
                relative_pos = (event.pos[0] - self.rect.x, event.pos[1] - self.rect.y)
                if event.button == 1:  # Left click
                    consumed = self._handle_left_click(relative_pos)
                elif event.button == 3:  # Right click
                    consumed = self._handle_right_click(relative_pos)
            else:
                self.is_panel_focused = False

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                self._handle_mouse_up()
                consumed = True

        elif event.type == pygame.MOUSEMOTION:
            relative_pos = (event.pos[0] - self.rect.x, event.pos[1] - self.rect.y)
            consumed = self._handle_mouse_motion(relative_pos)

        elif event.type == pygame.MOUSEWHEEL:
            if self.rect.collidepoint(pygame.mouse.get_pos()):
                consumed = self._handle_scroll(event.x, event.y)

        elif event.type == pygame.KEYDOWN and self.is_panel_focused:
            consumed = self._handle_key_event(event)

        return consumed

    def _handle_left_click(self, pos: Tuple[int, int]) -> bool:
        """Handle left mouse click with improved area detection"""
        x, y = pos

        # Check controls area
        if self.controls_rect.collidepoint(pos):
            return self._handle_controls_click(pos)

        # Check scrubber area
        elif self.scrubber_rect.collidepoint(pos):
            # Start scrubbing
            self.is_scrubbing = True
            self._set_frame_from_scrubber_pos(x - self.scrubber_rect.x)
            return True

        # Check layer labels area
        elif self.layer_labels_rect.collidepoint(pos):
            return self._handle_layer_label_click(pos)

        # Check timeline area
        elif self.timeline_rect.collidepoint(pos):
            timeline_pos = (x - self.timeline_rect.x, y - self.timeline_rect.y)
            return self._handle_timeline_click(timeline_pos)

        return False

    def _handle_layer_label_click(self, pos: Tuple[int, int]) -> bool:
        """Handle click in layer labels area"""
        if not self.clip:
            return False

        y = pos[1] - self.layer_labels_rect.y
        layer_y = -self.scroll_y

        for layer in self.clip.layers:
            if layer_y <= y < layer_y + layer.height:
                # Toggle layer visibility or select layer
                self.focused_layer = layer.id

                # Could add layer visibility toggle here
                # layer.visible = not layer.visible

                self.rebuild_image()
                return True
            layer_y += layer.height

        return False

    def _handle_controls_click(self, pos: Tuple[int, int]) -> bool:
        """Handle click in controls area with configuration support"""
        layout = self.config.layout
        button_size = min(24, self.controls_rect.height - 6)
        button_y = (self.controls_rect.height - button_size) // 2
        button_spacing = button_size + layout.control_button_spacing

        button_x = 10
        buttons = [
            self._rewind_to_start,
            self._step_backward,
            self._toggle_playback,
            self._step_forward,
            self._fast_forward_to_end,
        ]

        for button_action in buttons:
            button_rect = pygame.Rect(button_x, button_y, button_size, button_size)
            if button_rect.collidepoint(pos):
                button_action()
                return True
            button_x += button_spacing

        return False

    def _handle_timeline_click(self, pos: Tuple[int, int]) -> bool:
        """Handle click in timeline area with improved keyframe detection"""
        if not self.clip:
            return False

        x, y = pos

        # Calculate frame from x position
        frames_per_pixel = 1.0 / self.zoom
        start_frame = self.scroll_x * frames_per_pixel
        clicked_frame = int(start_frame + x * frames_per_pixel)

        # Find clicked layer
        layer_y = -self.scroll_y
        clicked_layer = None

        for layer in self.clip.layers:
            if layer_y <= y < layer_y + layer.height:
                clicked_layer = layer
                break
            layer_y += layer.height

        if not clicked_layer:
            return False

        # Check for keyframe click with configurable tolerance
        tolerance = self.config.interaction.keyframe_click_tolerance
        keyframe_clicked = False

        for curve in clicked_layer.curves:
            for kf in curve.keyframes:
                kf_x = int((kf.frame - start_frame) / frames_per_pixel)
                kf_y = layer_y + clicked_layer.height // 2

                # Check if click is near keyframe
                if abs(x - kf_x) <= tolerance and abs(y - kf_y) <= tolerance:
                    self._select_keyframe(clicked_layer.id, curve.property_name, kf.frame)
                    keyframe_clicked = True
                    break

            if keyframe_clicked:
                break

        if not keyframe_clicked:
            # Clear selection and set current frame
            if not self.config.behavior.multi_select_keyframes:
                self.selection.clear()
            self.set_current_frame(clicked_frame)

        self.rebuild_image()
        return True

    @staticmethod
    def _handle_right_click(pos: Tuple[int, int]) -> bool:
        """Handle right mouse click - context menu would be implemented here"""
        return False

    def _handle_mouse_up(self):
        """Handle mouse button release"""
        self.is_scrubbing = False
        self.is_dragging_keyframe = False

    def _handle_mouse_motion(self, pos: Tuple[int, int]) -> bool:
        """Handle mouse motion with improved hover detection"""
        if self.is_scrubbing and self.scrubber_rect.collidepoint(pos):
            self._set_frame_from_scrubber_pos(pos[0] - self.scrubber_rect.x)
            return True

        # Update hover state
        old_hovered = self.hovered_keyframe
        self.hovered_keyframe = self._get_keyframe_at_pos(pos)

        if old_hovered != self.hovered_keyframe:
            self.rebuild_image()
            return True

        return False

    def _handle_scroll(self, x_delta: int, y_delta: int) -> bool:
        """Handle scroll wheel with configuration support"""
        keys = pygame.key.get_pressed()
        interaction = self.config.interaction

        if keys[pygame.K_LCTRL] or keys[pygame.K_RCTRL]:
            # Zoom
            zoom_factor = 1.0 + (y_delta * interaction.zoom_sensitivity)
            old_zoom = self.zoom
            self.zoom = max(interaction.min_zoom, min(interaction.max_zoom, self.zoom * zoom_factor))

            if self.zoom != old_zoom:
                # Adjust scroll to zoom around mouse position
                mouse_x = pygame.mouse.get_pos()[0] - self.rect.x
                if self.scrubber_rect.collidepoint((mouse_x, 0)):
                    frames_per_pixel = 1.0 / old_zoom
                    mouse_frame = self.scroll_x * frames_per_pixel + mouse_x * frames_per_pixel

                    new_frames_per_pixel = 1.0 / self.zoom
                    self.scroll_x = (mouse_frame - mouse_x * new_frames_per_pixel) / new_frames_per_pixel

                self.rebuild_image()

                event_data = {'zoom': self.zoom, 'ui_element': self}
                pygame.event.post(pygame.event.Event(UI_TIMELINE_ZOOM_CHANGED, event_data))
                return True
        else:
            # Scroll
            if abs(x_delta) > abs(y_delta):
                # Horizontal scroll
                self.scroll_x = max(0, int(self.scroll_x + x_delta * interaction.scroll_speed))
            else:
                # Vertical scroll
                self.scroll_y = max(0, int(self.scroll_y + y_delta * interaction.scroll_speed))

            self.rebuild_image()
            return True

        return False

    def _handle_key_event(self, event: pygame.event.Event) -> bool:
        """Handle keyboard events"""
        if event.key == pygame.K_SPACE:
            self._toggle_playback()
            return True
        elif event.key == pygame.K_LEFT:
            self._step_backward()
            return True
        elif event.key == pygame.K_RIGHT:
            self._step_forward()
            return True
        elif event.key == pygame.K_HOME:
            self._rewind_to_start()
            return True
        elif event.key == pygame.K_END:
            self._fast_forward_to_end()
            return True
        elif event.key == pygame.K_DELETE:
            self._delete_selected_keyframes()
            return True

        return False

    def _set_frame_from_scrubber_pos(self, x: int):
        """Set current frame from scrubber x position"""
        frames_per_pixel = 1.0 / self.zoom
        start_frame = self.scroll_x * frames_per_pixel
        frame = start_frame + x * frames_per_pixel

        if self.config.behavior.snap_to_frames:
            frame = round(frame)

        self.set_current_frame(frame)

    def _get_keyframe_at_pos(self, pos: Tuple[int, int]) -> Optional[Tuple[str, str, int]]:
        """Get keyframe at mouse position with configuration support"""
        if not self.clip or not self.timeline_rect.collidepoint(pos):
            return None

        x, y = pos[0] - self.timeline_rect.x, pos[1] - self.timeline_rect.y

        # Calculate frame and layer
        frames_per_pixel = 1.0 / self.zoom
        start_frame = self.scroll_x * frames_per_pixel
        tolerance = self.config.interaction.keyframe_click_tolerance

        layer_y = -self.scroll_y
        for layer in self.clip.layers:
            if layer_y <= y < layer_y + layer.height:
                # Check keyframes in this layer
                for curve in layer.curves:
                    for kf in curve.keyframes:
                        kf_x = int((kf.frame - start_frame) / frames_per_pixel)
                        kf_y = layer_y + layer.height // 2

                        if (abs(x - kf_x) <= tolerance and
                                abs(y - kf_y) <= tolerance):
                            return layer.id, curve.property_name, kf.frame
                break
            layer_y += layer.height

        return None

    def _select_keyframe(self, layer_id: str, property_name: str, frame: int):
        """Select a keyframe with multi-selection support"""
        keyframe_id = (layer_id, property_name, frame)

        if self.config.behavior.multi_select_keyframes:
            # Toggle selection
            if keyframe_id in self.selection:
                self.selection.remove(keyframe_id)
            else:
                self.selection.append(keyframe_id)
        else:
            # Single selection
            if keyframe_id in self.selection:
                self.selection.clear()
            else:
                self.selection.clear()
                self.selection.append(keyframe_id)

        event_data = {
            'selection': self.selection.copy(),
            'ui_element': self
        }
        pygame.event.post(pygame.event.Event(UI_TIMELINE_SELECTION_CHANGED, event_data))

    def _delete_selected_keyframes(self):
        """Delete selected keyframes"""
        if not self.clip or not self.selection:
            return

        for layer_id, property_name, frame in self.selection:
            layer = self.clip.get_layer(layer_id)
            if layer:
                curve = layer.get_curve(property_name)
                if curve:
                    curve.remove_keyframe(frame)

                    event_data = {
                        'layer_id': layer_id,
                        'property_name': property_name,
                        'frame': frame,
                        'ui_element': self
                    }
                    pygame.event.post(pygame.event.Event(UI_TIMELINE_KEYFRAME_REMOVED, event_data))

        self.selection.clear()
        self.rebuild_image()

    def _auto_scroll_to_frame(self, frame: float):
        """Auto-scroll timeline to keep frame visible with configuration support"""
        frames_per_pixel = 1.0 / self.zoom
        start_frame = self.scroll_x * frames_per_pixel
        end_frame = start_frame + self.scrubber_rect.width * frames_per_pixel

        margin = (end_frame - start_frame) * self.config.interaction.auto_scroll_margin

        if frame < start_frame + margin:
            self.scroll_x = max(0, int((frame - margin) / frames_per_pixel))
            self.rebuild_image()
        elif frame > end_frame - margin:
            self.scroll_x = max(0,
                                int((frame - self.scrubber_rect.width * frames_per_pixel + margin) / frames_per_pixel))
            self.rebuild_image()

    # Playback control methods
    def _toggle_playback(self):
        """Toggle playback state"""
        if self.playback_state == PlaybackState.PLAYING:
            self.pause()
        elif self.playback_state == PlaybackState.PAUSED:
            self.play()
        else:
            self.play()

    def _step_backward(self):
        """Step one frame backward"""
        self.set_current_frame(self.current_frame - 1)

    def _step_forward(self):
        """Step one frame forward"""
        self.set_current_frame(self.current_frame + 1)

    def _rewind_to_start(self):
        """Rewind to start"""
        self.set_current_frame(0)

    def _fast_forward_to_end(self):
        """Fast forward to end"""
        if self.clip:
            self.set_current_frame(self.clip.length)
        else:
            self.set_current_frame(100)  # Default length

    def update(self, time_delta: float):
        """Update the panel with playback handling"""
        super().update(time_delta)

        # Handle playback
        if self.playback_state == PlaybackState.PLAYING and self.clip:
            # Use time_delta directly (already in seconds) - this is the key fix
            frame_delta = time_delta * self.clip.fps
            new_frame = self.current_frame + frame_delta

            if new_frame >= self.clip.length:
                if self.clip.loop:
                    new_frame = self.clip.start_frame
                else:
                    new_frame = self.clip.length
                    self.stop()

            self.set_current_frame(new_frame)

            # Auto-scroll during playback
            if self.config.behavior.auto_scroll_on_playback:
                self._auto_scroll_to_frame(self.current_frame)

    # Public API methods
    def set_clip(self, clip: AnimationClip):
        """Set the animation clip to display"""
        self.clip = clip
        self.current_frame = 0.0
        self.selection.clear()

        if self.config.behavior.zoom_to_fit_on_clip_change and clip:
            self.zoom_to_fit()

        self._last_rebuild_state = None  # Force rebuild
        self.rebuild_image()

    def get_clip(self) -> Optional[AnimationClip]:
        """Get the current animation clip"""
        return self.clip

    def set_current_frame(self, frame: float):
        """Set the current frame"""
        if self.clip:
            frame = max(0, min(self.clip.length, frame))  # Keep as float for smooth playback
        else:
            frame = max(0, frame)

        old_frame = self.current_frame
        self.current_frame = frame

        # Use small threshold for float comparison to avoid excessive updates
        if abs(old_frame - frame) > 0.001:
            # Fire frame change event
            event_data = {
                'frame': frame,
                'old_frame': old_frame,
                'ui_element': self
            }
            pygame.event.post(pygame.event.Event(UI_TIMELINE_FRAME_CHANGED, event_data))

            # Call callback
            if self.frame_change_callback:
                self.frame_change_callback(frame)

            self.rebuild_image()

    def get_current_frame(self) -> float:
        """Get the current frame"""
        return self.current_frame

    def play(self):
        """Start playback"""
        if self.playback_state != PlaybackState.PLAYING:
            self.playback_state = PlaybackState.PLAYING

            event_data = {'ui_element': self}
            pygame.event.post(pygame.event.Event(UI_TIMELINE_PLAYBACK_STARTED, event_data))
            # Removed rebuild_image() call - set_current_frame handles this

    def pause(self):
        """Pause playback"""
        if self.playback_state == PlaybackState.PLAYING:
            self.playback_state = PlaybackState.PAUSED

            event_data = {'ui_element': self}
            pygame.event.post(pygame.event.Event(UI_TIMELINE_PLAYBACK_PAUSED, event_data))

            self.rebuild_image()

    def stop(self):
        """Stop playback"""
        self.playback_state = PlaybackState.STOPPED

        event_data = {'ui_element': self}
        pygame.event.post(pygame.event.Event(UI_TIMELINE_PLAYBACK_STOPPED, event_data))

        self.rebuild_image()

    def add_keyframe(self, layer_id: str, property_name: str, frame: int, value: Any,
                     interpolation: InterpolationType = InterpolationType.LINEAR):
        """Add a keyframe"""
        if not self.clip:
            return False

        layer = self.clip.get_layer(layer_id)
        if not layer:
            return False

        curve = layer.get_curve(property_name)
        if not curve:
            curve = AnimationCurve(property_name, default_value=value)
            layer.add_curve(curve)

        keyframe = Keyframe(frame, value, interpolation)
        curve.add_keyframe(keyframe)

        event_data = {
            'layer_id': layer_id,
            'property_name': property_name,
            'frame': frame,
            'value': value,
            'keyframe': keyframe,
            'ui_element': self
        }
        pygame.event.post(pygame.event.Event(UI_TIMELINE_KEYFRAME_ADDED, event_data))

        if self.keyframe_change_callback:
            self.keyframe_change_callback(layer_id, property_name, frame, value)

        self.rebuild_image()
        return True

    def remove_keyframe(self, layer_id: str, property_name: str, frame: int):
        """Remove a keyframe"""
        if not self.clip:
            return False

        layer = self.clip.get_layer(layer_id)
        if not layer:
            return False

        curve = layer.get_curve(property_name)
        if not curve:
            return False

        if curve.remove_keyframe(frame):
            event_data = {
                'layer_id': layer_id,
                'property_name': property_name,
                'frame': frame,
                'ui_element': self
            }
            pygame.event.post(pygame.event.Event(UI_TIMELINE_KEYFRAME_REMOVED, event_data))

            self.rebuild_image()
            return True

        return False

    def get_value_at_frame(self, layer_id: str, property_name: str, frame: float) -> Any:
        """Get interpolated value at specific frame"""
        if not self.clip:
            return None

        layer = self.clip.get_layer(layer_id)
        if not layer:
            return None

        curve = layer.get_curve(property_name)
        if not curve:
            return None

        return curve.get_value_at_frame(frame)

    def zoom_to_fit(self):
        """Zoom timeline to fit entire clip"""
        if not self.clip or self.clip.length <= 0:
            return

        available_width = self.scrubber_rect.width - 20  # Some margin
        self.zoom = available_width / self.clip.length
        self.zoom = max(self.config.interaction.min_zoom,
                        min(self.config.interaction.max_zoom, self.zoom))
        self.scroll_x = 0

        self.rebuild_image()

    def set_zoom(self, zoom: float):
        """Set timeline zoom level"""
        old_zoom = self.zoom
        self.zoom = max(self.config.interaction.min_zoom,
                        min(self.config.interaction.max_zoom, zoom))

        if old_zoom != self.zoom:
            event_data = {'zoom': self.zoom, 'ui_element': self}
            pygame.event.post(pygame.event.Event(UI_TIMELINE_ZOOM_CHANGED, event_data))
            self.rebuild_image()

    def set_frame_change_callback(self, callback: Callable[[float], None]):
        """Set callback for frame changes"""
        self.frame_change_callback = callback

    def set_keyframe_change_callback(self, callback: Callable[[str, str, int, Any], None]):
        """Set callback for keyframe changes"""
        self.keyframe_change_callback = callback

    def get_selected_keyframes(self) -> List[Tuple[str, str, int]]:
        """Get currently selected keyframes"""
        return self.selection.copy()

    def clear_selection(self):
        """Clear keyframe selection"""
        self.selection.clear()
        self.rebuild_image()

    def refresh(self):
        """Refresh the timeline display"""
        self._last_rebuild_state = None  # Force rebuild
        self.rebuild_image()

    # Configuration update methods
    def update_layout_config(self, layout_config: TimelineLayoutConfig):
        """Update layout configuration and rebuild"""
        self.config.layout = copy.deepcopy(layout_config)
        self.setup_layout()
        self._last_rebuild_state = None
        self.rebuild_image()

    def update_behavior_config(self, behavior_config: TimelineBehaviorConfig):
        """Update behavior configuration"""
        self.config.behavior = copy.deepcopy(behavior_config)
        self._last_rebuild_state = None
        self.rebuild_image()

    def update_interaction_config(self, interaction_config: TimelineInteractionConfig):
        """Update interaction configuration"""
        self.config.interaction = copy.deepcopy(interaction_config)


# Example themes for timeline panel
TIMELINE_DARK_THEME = {
    "timeline_panel": {
        "colours": {
            "timeline_bg": "#282828",
            "controls_bg": "#232323",
            "scrubber_bg": "#2d2d2d",
            "layer_bg": "#323232",
            "layer_bg_alt": "#2d2d2d",
            "layer_label_bg": "#373737",
            "normal_text": "#ffffff",
            "disabled_text": "#969696",
            "layer_text": "#dcdcdc",
            "grid_line": "#3c3c3c",
            "major_tick": "#c8c8c8",
            "minor_tick": "#969696",
            "playhead": "#ff5050",
            "playhead_handle": "#ff6464",
            "selection": "#6496ff",
            "selection_bg": "#4682b4",
            "hover_bg": "#3c3c3c",
            "focused_bg": "#5078a0",
            "keyframe_linear": "#64a0ff",
            "keyframe_ease_in": "#64ff64",
            "keyframe_ease_out": "#ff6464",
            "keyframe_ease_in_out": "#ff9664",
            "keyframe_step": "#c8c8c8",
            "keyframe_bezier": "#ff64ff",
            "keyframe_smooth": "#64ffff",
            "keyframe_selected": "#ffff64",
            "keyframe_locked": "#787878",
            "keyframe_outline": "#141414",
            "button_bg": "#3c3c3c",
            "button_hover": "#505050",
            "button_pressed": "#282828",
            "button_text": "#ffffff",
            "border": "#646464",
            "focus_border": "#78a0ff",
            "layer_border": "#505050",
            "time_cursor": "#ffffff"
        },
        "font": {
            "name": "arial",
            "size": "10",
            "bold": "0",
            "italic": "0"
        }
    }
}

TIMELINE_LIGHT_THEME = {
    "timeline_panel": {
        "colours": {
            "timeline_bg": "#f5f5f5",
            "controls_bg": "#e8e8e8",
            "scrubber_bg": "#f0f0f0",
            "layer_bg": "#ffffff",
            "layer_bg_alt": "#f8f8f8",
            "layer_label_bg": "#e0e0e0",
            "normal_text": "#2b2b2b",
            "disabled_text": "#969696",
            "layer_text": "#333333",
            "grid_line": "#d0d0d0",
            "major_tick": "#333333",
            "minor_tick": "#666666",
            "playhead": "#dc143c",
            "playhead_handle": "#ff6b6b",
            "selection": "#4a90e2",
            "selection_bg": "#cce4f6",
            "hover_bg": "#e6e6e6",
            "focused_bg": "#b3d9ff",
            "keyframe_linear": "#4a90e2",
            "keyframe_ease_in": "#27ae60",
            "keyframe_ease_out": "#e74c3c",
            "keyframe_ease_in_out": "#f39c12",
            "keyframe_step": "#95a5a6",
            "keyframe_bezier": "#9b59b6",
            "keyframe_smooth": "#1abc9c",
            "keyframe_selected": "#f1c40f",
            "keyframe_locked": "#bdc3c7",
            "keyframe_outline": "#2c3e50",
            "button_bg": "#d3d3d3",
            "button_hover": "#c0c0c0",
            "button_pressed": "#a8a8a8",
            "button_text": "#2b2b2b",
            "border": "#a0a0a0",
            "focus_border": "#4a90e2",
            "layer_border": "#c0c0c0",
            "time_cursor": "#2b2b2b"
        },
        "font": {
            "name": "arial",
            "size": "10",
            "bold": "0",
            "italic": "0"
        }
    }
}


def create_sample_animation_clip() -> AnimationClip:
    """Create a sample animation clip for testing"""
    clip = AnimationClip("Sample Animation", length=120, fps=30.0)

    # Transform layer
    transform_layer = AnimationLayer("transform", "Transform", LayerType.TRANSFORM)

    # Position X animation
    pos_x_curve = AnimationCurve("position_x", default_value=0.0)
    pos_x_curve.add_keyframe(Keyframe(0, 0.0, InterpolationType.LINEAR))
    pos_x_curve.add_keyframe(Keyframe(30, 100.0, InterpolationType.EASE_OUT))
    pos_x_curve.add_keyframe(Keyframe(60, 0.0, InterpolationType.EASE_IN_OUT))
    pos_x_curve.add_keyframe(Keyframe(90, -50.0, InterpolationType.EASE_IN))
    pos_x_curve.add_keyframe(Keyframe(120, 0.0, InterpolationType.LINEAR))
    transform_layer.add_curve(pos_x_curve)

    # Position Y animation
    pos_y_curve = AnimationCurve("position_y", default_value=0.0)
    pos_y_curve.add_keyframe(Keyframe(0, 0.0, InterpolationType.LINEAR))
    pos_y_curve.add_keyframe(Keyframe(15, -30.0, InterpolationType.EASE_OUT))
    pos_y_curve.add_keyframe(Keyframe(45, 50.0, InterpolationType.EASE_IN_OUT))
    pos_y_curve.add_keyframe(Keyframe(75, -20.0, InterpolationType.SMOOTH))
    pos_y_curve.add_keyframe(Keyframe(120, 0.0, InterpolationType.LINEAR))
    transform_layer.add_curve(pos_y_curve)

    # Rotation animation
    rotation_curve = AnimationCurve("rotation", default_value=0.0)
    rotation_curve.add_keyframe(Keyframe(0, 0.0, InterpolationType.LINEAR))
    rotation_curve.add_keyframe(Keyframe(60, 180.0, InterpolationType.EASE_IN_OUT))
    rotation_curve.add_keyframe(Keyframe(120, 360.0, InterpolationType.LINEAR))
    transform_layer.add_curve(rotation_curve)

    clip.add_layer(transform_layer)

    # Color layer
    color_layer = AnimationLayer("color", "Color", LayerType.PROPERTY)

    # Color animation
    color_curve = AnimationCurve("color", default_value=pygame.Color(255, 255, 255))
    color_curve.add_keyframe(Keyframe(0, pygame.Color(255, 0, 0), InterpolationType.LINEAR))
    color_curve.add_keyframe(Keyframe(30, pygame.Color(0, 255, 0), InterpolationType.LINEAR))
    color_curve.add_keyframe(Keyframe(60, pygame.Color(0, 0, 255), InterpolationType.LINEAR))
    color_curve.add_keyframe(Keyframe(90, pygame.Color(255, 255, 0), InterpolationType.LINEAR))
    color_curve.add_keyframe(Keyframe(120, pygame.Color(255, 0, 0), InterpolationType.LINEAR))
    color_layer.add_curve(color_curve)

    # Opacity animation
    opacity_curve = AnimationCurve("opacity", default_value=1.0)
    opacity_curve.add_keyframe(Keyframe(0, 1.0, InterpolationType.LINEAR))
    opacity_curve.add_keyframe(Keyframe(20, 0.2, InterpolationType.EASE_OUT))
    opacity_curve.add_keyframe(Keyframe(40, 1.0, InterpolationType.EASE_IN))
    opacity_curve.add_keyframe(Keyframe(80, 0.5, InterpolationType.STEP))
    opacity_curve.add_keyframe(Keyframe(120, 1.0, InterpolationType.LINEAR))
    color_layer.add_curve(opacity_curve)

    clip.add_layer(color_layer)

    # Scale layer
    scale_layer = AnimationLayer("scale", "Scale", LayerType.PROPERTY)

    # Scale animation
    scale_curve = AnimationCurve("scale", default_value=1.0)
    scale_curve.add_keyframe(Keyframe(0, 1.0, InterpolationType.LINEAR))
    scale_curve.add_keyframe(Keyframe(25, 1.5, InterpolationType.EASE_OUT))
    scale_curve.add_keyframe(Keyframe(50, 0.8, InterpolationType.EASE_IN_OUT))
    scale_curve.add_keyframe(Keyframe(75, 2.0, InterpolationType.BEZIER))
    scale_curve.add_keyframe(Keyframe(100, 0.5, InterpolationType.SMOOTH))
    scale_curve.add_keyframe(Keyframe(120, 1.0, InterpolationType.LINEAR))
    scale_layer.add_curve(scale_curve)

    clip.add_layer(scale_layer)

    return clip


class SampleAnimatedObject:
    """Sample object that can be animated"""

    def __init__(self):
        self.position_x = 0.0
        self.position_y = 0.0
        self.rotation = 0.0
        self.color = pygame.Color(255, 255, 255)
        self.opacity = 1.0
        self.scale = 1.0

    def apply_frame_values(self, clip: AnimationClip, frame: float):
        """Apply animation values from specified frame"""
        for layer in clip.layers:
            for curve in layer.curves:
                value = curve.get_value_at_frame(frame)
                if hasattr(self, curve.property_name):
                    setattr(self, curve.property_name, value)


def main():
    """Example demonstration of the fully configurable Timeline Panel"""
    pygame.init()
    screen = pygame.display.set_mode((1200, 800))
    pygame.display.set_caption("Fully Configurable Timeline Panel Demo")
    clock = pygame.time.Clock()

    # Start with dark theme
    manager = pygame_gui.UIManager((1200, 800), TIMELINE_DARK_THEME)
    current_theme = "dark"

    # Create different configurations for demonstration
    compact_config = TimelineConfig()
    compact_config.layout.layer_height = 25
    compact_config.layout.controls_height = 25
    compact_config.layout.scrubber_height = 20
    compact_config.layout.keyframe_size = 6
    compact_config.behavior.show_frame_numbers = False
    compact_config.behavior.show_layer_names = True

    large_config = TimelineConfig()
    large_config.layout.layer_height = 60
    large_config.layout.controls_height = 45
    large_config.layout.scrubber_height = 40
    large_config.layout.keyframe_size = 12
    large_config.layout.layer_label_width = 200
    large_config.behavior.show_frame_numbers = True
    large_config.behavior.show_layer_names = True
    large_config.behavior.show_interpolation_curves = True

    performance_config = TimelineConfig()
    performance_config.behavior.cache_rendered_elements = True
    performance_config.behavior.lazy_redraw = True
    performance_config.behavior.max_visible_keyframes = 500
    performance_config.layout.keyframe_size = 8

    # Create timeline panel with default config
    timeline_panel = TimelinePanel(
        pygame.Rect(50, 50, 1100, 350),
        manager,
        compact_config,
        object_id=ObjectID(object_id='#main_timeline', class_id='@timeline_panel')
    )

    # Create sample animation
    sample_clip = create_sample_animation_clip()
    timeline_panel.set_clip(sample_clip)

    # Create animated object for demonstration
    animated_object = SampleAnimatedObject()

    # Set up frame change callback to update object
    def on_frame_changed(given_frame: float):
        if TIMELINE_DEBUG:
            print(f"Frame changed to: {given_frame}")
        animated_object.apply_frame_values(sample_clip, given_frame)

    timeline_panel.set_frame_change_callback(on_frame_changed)

    # Instructions
    print("\nFully Configurable Timeline Panel Demo")
    print("\nNew Configuration Features:")
    print("- Comprehensive layout configuration")
    print("- Behavior and interaction settings")
    print("- Theme management with light/dark themes")
    print("- Performance optimizations")
    print("- Layer label area with configurable width")
    print("- Configurable keyframe appearance and behavior")

    print("\nControls:")
    print("- Click controls to play/pause/stop")
    print("- Click and drag in scrubber to scrub timeline")
    print("- Click keyframes to select them")
    print("- Click layer labels to focus layers")
    print("- Space bar to toggle playback")
    print("- Left/Right arrows to step frames")
    print("- Home/End to go to start/end")
    print("- Ctrl+Mouse wheel to zoom")
    print("- Mouse wheel to scroll")
    print("- Delete to remove selected keyframes")

    print("\nConfiguration Controls:")
    print("Press '1' for compact layout")
    print("Press '2' for large layout")
    print("Press '3' for performance layout")
    print("Press 'T' to toggle light/dark theme")
    print("Press 'G' to toggle grid display")
    print("Press 'N' to toggle frame numbers")
    print("Press 'L' to toggle layer names")
    print("Press 'M' to toggle multi-select")
    print("Press 'S' to toggle snap to frames")
    print("Press 'A' to toggle auto-scroll")
    print("Press 'Z' to zoom to fit")
    print("Press 'K' to add keyframe at current frame")
    print("Press 'C' to clear selection\n")

    running = True
    while running:
        time_delta = clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1:
                    # Apply compact configuration
                    timeline_panel.update_layout_config(compact_config.layout)
                    timeline_panel.update_behavior_config(compact_config.behavior)
                    print("Applied compact layout configuration")

                elif event.key == pygame.K_2:
                    # Apply large configuration
                    timeline_panel.update_layout_config(large_config.layout)
                    timeline_panel.update_behavior_config(large_config.behavior)
                    print("Applied large layout configuration")

                elif event.key == pygame.K_3:
                    # Apply performance configuration
                    timeline_panel.update_layout_config(performance_config.layout)
                    timeline_panel.update_behavior_config(performance_config.behavior)
                    print("Applied performance configuration")

                elif event.key == pygame.K_t:
                    # Toggle theme
                    if current_theme == "dark":
                        manager.get_theme().load_theme(TIMELINE_LIGHT_THEME)
                        current_theme = "light"
                    else:
                        manager.get_theme().load_theme(TIMELINE_DARK_THEME)
                        current_theme = "dark"

                    timeline_panel.rebuild_from_changed_theme_data()
                    print(f"Switched to {current_theme} theme")

                elif event.key == pygame.K_g:
                    # Toggle grid display
                    timeline_panel.config.behavior.show_grid = not timeline_panel.config.behavior.show_grid
                    timeline_panel.refresh()
                    print(f"Grid display: {'ON' if timeline_panel.config.behavior.show_grid else 'OFF'}")

                elif event.key == pygame.K_n:
                    # Toggle frame numbers
                    timeline_panel.config.behavior.show_frame_numbers = not timeline_panel.config.behavior.show_frame_numbers
                    timeline_panel.refresh()
                    print(f"Frame numbers: {'ON' if timeline_panel.config.behavior.show_frame_numbers else 'OFF'}")

                elif event.key == pygame.K_l:
                    # Toggle layer names
                    timeline_panel.config.behavior.show_layer_names = not timeline_panel.config.behavior.show_layer_names
                    timeline_panel.refresh()
                    print(f"Layer names: {'ON' if timeline_panel.config.behavior.show_layer_names else 'OFF'}")

                elif event.key == pygame.K_m:
                    # Toggle multi-select
                    timeline_panel.config.behavior.multi_select_keyframes = not timeline_panel.config.behavior.multi_select_keyframes
                    print(
                        f"Multi-select keyframes: {'ON' if timeline_panel.config.behavior.multi_select_keyframes else 'OFF'}")

                elif event.key == pygame.K_s:
                    # Toggle snap to frames
                    timeline_panel.config.behavior.snap_to_frames = not timeline_panel.config.behavior.snap_to_frames
                    print(f"Snap to frames: {'ON' if timeline_panel.config.behavior.snap_to_frames else 'OFF'}")

                elif event.key == pygame.K_a:
                    # Toggle auto-scroll
                    timeline_panel.config.behavior.auto_scroll_on_playback = not timeline_panel.config.behavior.auto_scroll_on_playback
                    print(f"Auto-scroll: {'ON' if timeline_panel.config.behavior.auto_scroll_on_playback else 'OFF'}")

                elif event.key == pygame.K_z:
                    # Zoom to fit
                    timeline_panel.zoom_to_fit()
                    print("Zoomed to fit")

                elif event.key == pygame.K_k:
                    # Add keyframe at current frame
                    frame = int(timeline_panel.get_current_frame())
                    timeline_panel.add_keyframe("transform", "position_x", frame,
                                                animated_object.position_x, InterpolationType.LINEAR)
                    print(f"Added keyframe at frame {frame}")

                elif event.key == pygame.K_c:
                    # Clear selection
                    timeline_panel.clear_selection()
                    print("Cleared selection")

            # Handle timeline events
            elif event.type == UI_TIMELINE_FRAME_CHANGED:
                if TIMELINE_DEBUG:
                    print(f"Frame changed: {event.frame}")

            elif event.type == UI_TIMELINE_KEYFRAME_ADDED:
                if TIMELINE_DEBUG:
                    print(f"Keyframe added: {event.layer_id}.{event.property_name} @ {event.frame}")

            elif event.type == UI_TIMELINE_KEYFRAME_REMOVED:
                if TIMELINE_DEBUG:
                    print(f"Keyframe removed: {event.layer_id}.{event.property_name} @ {event.frame}")

            elif event.type == UI_TIMELINE_PLAYBACK_STARTED:
                if TIMELINE_DEBUG:
                    print("Playback started")

            elif event.type == UI_TIMELINE_PLAYBACK_STOPPED:
                if TIMELINE_DEBUG:
                    print("Playback stopped")

            elif event.type == UI_TIMELINE_PLAYBACK_PAUSED:
                if TIMELINE_DEBUG:
                    print("Playback paused")

            elif event.type == UI_TIMELINE_SELECTION_CHANGED:
                if TIMELINE_DEBUG:
                    print(f"Selection changed: {len(event.selection)} keyframes selected")

            elif event.type == UI_TIMELINE_ZOOM_CHANGED:
                if TIMELINE_DEBUG:
                    print(f"Zoom changed: {event.zoom:.2f}")

            # Forward to manager
            manager.process_events(event)

        # Update
        manager.update(time_delta)

        # Draw
        screen.fill((20, 20, 20))

        # Draw animated object visualization
        center_x = 600
        center_y = 550

        # Calculate position based on animation
        draw_x = center_x + animated_object.position_x
        draw_y = center_y + animated_object.position_y

        # Calculate size based on scale
        base_size = 30
        size = int(base_size * animated_object.scale)

        # Calculate color with opacity
        color = pygame.Color(animated_object.color)
        color.a = int(255 * animated_object.opacity)

        # Draw object (simple circle)
        if size > 0:
            pygame.draw.circle(screen, color, (int(draw_x), int(draw_y)), size)

            # Draw rotation indicator (line from center)
            import math
            line_length = size * 0.8
            angle_rad = math.radians(animated_object.rotation)
            end_x = draw_x + math.cos(angle_rad) * line_length
            end_y = draw_y + math.sin(angle_rad) * line_length
            pygame.draw.line(screen, pygame.Color(255, 255, 255),
                             (draw_x, draw_y), (end_x, end_y), 2)

        # Draw comprehensive info text
        font = pygame.font.Font(None, 20)
        small_font = pygame.font.Font(None, 16)

        info_lines = [
            f"Configurable Timeline Demo - Frame: {timeline_panel.get_current_frame():.1f}",
            f"Position: ({animated_object.position_x:.1f}, {animated_object.position_y:.1f})",
            f"Rotation: {animated_object.rotation:.1f}",
            f"Scale: {animated_object.scale:.2f}",
            f"Opacity: {animated_object.opacity:.2f}",
            f"Playback: {timeline_panel.playback_state.value}",
            f"Theme: {current_theme}",
            f"Zoom: {timeline_panel.zoom:.2f}x"
        ]

        y_offset = 420
        for line in info_lines:
            text_surface = font.render(line, True, pygame.Color(255, 255, 255))
            screen.blit(text_surface, (50, y_offset))
            y_offset += 22

        # Draw configuration status
        config_lines = [
            "Configuration Status:",
            f"Layer Height: {timeline_panel.config.layout.layer_height}px",
            f"Keyframe Size: {timeline_panel.config.layout.keyframe_size}px",
            f"Grid: {'ON' if timeline_panel.config.behavior.show_grid else 'OFF'}",
            f"Frame Numbers: {'ON' if timeline_panel.config.behavior.show_frame_numbers else 'OFF'}",
            f"Layer Names: {'ON' if timeline_panel.config.behavior.show_layer_names else 'OFF'}",
            f"Multi-Select: {'ON' if timeline_panel.config.behavior.multi_select_keyframes else 'OFF'}",
            f"Snap to Frames: {'ON' if timeline_panel.config.behavior.snap_to_frames else 'OFF'}",
            f"Auto-Scroll: {'ON' if timeline_panel.config.behavior.auto_scroll_on_playback else 'OFF'}",
            f"Max Visible Keyframes: {timeline_panel.config.behavior.max_visible_keyframes}",
        ]

        y_offset = 420
        for i, line in enumerate(config_lines):
            if i == 0:
                text_surface = font.render(line, True, pygame.Color(200, 255, 200))
            else:
                text_surface = small_font.render(line, True, pygame.Color(180, 180, 180))
            screen.blit(text_surface, (400, y_offset))
            y_offset += 18

        # Draw keyframe info
        selection_info = []
        if timeline_panel.get_selected_keyframes():
            selection_info.append(f"Selected: {len(timeline_panel.get_selected_keyframes())} keyframes")

            # Show details of first selected keyframe
            if timeline_panel.get_selected_keyframes():
                layer_id, prop_name, frame = timeline_panel.get_selected_keyframes()[0]
                value = timeline_panel.get_value_at_frame(layer_id, prop_name, frame)
                selection_info.append(f"Layer: {layer_id}")
                selection_info.append(f"Property: {prop_name}")
                selection_info.append(f"Frame: {frame}")
                selection_info.append(f"Value: {value}")

        if timeline_panel.hovered_keyframe:
            layer_id, prop_name, frame = timeline_panel.hovered_keyframe
            selection_info.append(f"Hovered: {layer_id}.{prop_name} @ {frame}")

        y_offset = 420
        for line in selection_info:
            text_surface = small_font.render(line, True, pygame.Color(255, 255, 100))
            screen.blit(text_surface, (700, y_offset))
            y_offset += 18

        # Draw performance info
        performance_info = [
            "Performance:",
            f"Layers: {len(sample_clip.layers)}",
            f"Total Keyframes: {sum(len(curve.keyframes) for layer in sample_clip.layers for curve in layer.curves)}",
            f"Clip Length: {sample_clip.length} frames",
            f"FPS: {sample_clip.fps}",
            f"Duration: {sample_clip.get_duration_seconds():.2f}s",
        ]

        y_offset = 420
        for i, line in enumerate(performance_info):
            if i == 0:
                text_surface = font.render(line, True, pygame.Color(255, 200, 200))
            else:
                text_surface = small_font.render(line, True, pygame.Color(180, 180, 180))
            screen.blit(text_surface, (900, y_offset))
            y_offset += 18

        # Draw layer information
        if timeline_panel.clip:
            layer_info = ["Layers:"]
            for layer in timeline_panel.clip.layers:
                status = "visible" if layer.visible else "hidden"
                if layer.locked:
                    status += ", locked"
                if timeline_panel.focused_layer == layer.id:
                    status += ", focused"

                curve_count = len(layer.curves)
                keyframe_count = sum(len(curve.keyframes) for curve in layer.curves)

                layer_info.append(f"{layer.name}: {curve_count} curves, {keyframe_count} keyframes ({status})")

            y_offset = 600
            for i, line in enumerate(layer_info):
                if i == 0:
                    text_surface = font.render(line, True, pygame.Color(200, 200, 255))
                else:
                    text_surface = small_font.render(line, True, pygame.Color(180, 180, 180))
                screen.blit(text_surface, (50, y_offset))
                y_offset += 18

        # Draw controls help
        help_info = [
            "Quick Controls:",
            "1/2/3 - Layout configs",
            "T - Toggle theme",
            "G - Toggle grid",
            "N - Frame numbers",
            "L - Layer names",
            "M - Multi-select",
            "S - Snap frames",
            "A - Auto-scroll",
            "Z - Zoom to fit",
            "K - Add keyframe",
            "C - Clear selection"
        ]

        y_offset = 520
        for i, line in enumerate(help_info):
            if i == 0:
                text_surface = font.render(line, True, pygame.Color(255, 255, 200))
            else:
                text_surface = small_font.render(line, True, pygame.Color(180, 180, 180))
            screen.blit(text_surface, (700, y_offset))
            y_offset += 18

        manager.draw_ui(screen)
        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()