import pygame
import pygame_gui
from pygame_gui.core import UIElement, ObjectID
from pygame_gui.core.interfaces import IContainerLikeInterface
from typing import List, Optional, Dict, Any, Union, Callable, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
import time
import copy

try:
    from pygame_gui.core.interfaces.gui_font_interface import IGUIFontInterface
except ImportError:
    IGUIFontInterface = None

TOOL_DEBUG = True

# Define custom pygame-gui events
UI_TOOL_SELECTED = pygame.USEREVENT + 200
UI_TOOL_DOUBLE_CLICKED = pygame.USEREVENT + 201
UI_TOOL_RIGHT_CLICKED = pygame.USEREVENT + 202
UI_TOOL_FAVORITED = pygame.USEREVENT + 203
UI_TOOL_UNFAVORITED = pygame.USEREVENT + 204
UI_TOOL_GROUP_EXPANDED = pygame.USEREVENT + 205
UI_TOOL_GROUP_COLLAPSED = pygame.USEREVENT + 206
UI_TOOL_SEARCH_CHANGED = pygame.USEREVENT + 207
UI_TOOL_VIEW_MODE_CHANGED = pygame.USEREVENT + 208


class ToolType(Enum):
    """Tool types for categorization"""
    ACTION = "action"
    CREATION = "creation"
    MODIFICATION = "modification"
    ANALYSIS = "analysis"
    NAVIGATION = "navigation"
    UTILITY = "utility"
    DEBUG = "debug"
    CUSTOM = "custom"


class ToolViewMode(Enum):
    """Tool palette view modes"""
    GRID = "grid"
    LIST = "list"
    DETAIL = "detail"


@dataclass
class Tool:
    """Individual tool data"""
    id: str
    name: str
    description: str = ""
    tool_type: ToolType = ToolType.UTILITY
    category: str = "General"
    icon_name: Optional[str] = None
    shortcut: str = ""
    callback: Optional[Callable] = None
    enabled: bool = True
    visible: bool = True
    use_count: int = 0
    last_used: float = 0.0
    is_favorite: bool = False
    is_loading: bool = False
    custom_data: Dict[str, Any] = field(default_factory=dict)

    def use_tool(self):
        """Mark tool as used"""
        self.use_count += 1
        self.last_used = time.time()


@dataclass
class ToolGroup:
    """Tool group/category container"""
    id: str
    name: str
    description: str = ""
    tools: List[Tool] = field(default_factory=list)
    expanded: bool = True
    icon_name: Optional[str] = None
    color: Optional[pygame.Color] = None
    order: int = 0

    def add_tool(self, tool: Tool):
        """Add tool to group"""
        if tool not in self.tools:
            self.tools.append(tool)

    def remove_tool(self, tool_id: str) -> bool:
        """Remove tool by ID"""
        original_count = len(self.tools)
        self.tools = [tool for tool in self.tools if tool.id != tool_id]
        return len(self.tools) < original_count

    def get_tool(self, tool_id: str) -> Optional[Tool]:
        """Get tool by ID"""
        for tool in self.tools:
            if tool.id == tool_id:
                return tool
        return None


@dataclass
class ToolPaletteLayoutConfig:
    """Layout configuration following property panel pattern"""
    # Grid layout settings
    grid_item_width: int = 120
    grid_item_height: int = 100
    grid_padding: int = 8
    grid_icon_size: Tuple[int, int] = (32, 32)

    # List layout settings
    list_item_height: int = 28
    list_icon_size: int = 20
    list_text_padding: int = 8

    # Detail layout settings
    detail_item_height: int = 60
    detail_icon_size: int = 40

    # Group headers (like section headers in property panel)
    group_header_height: int = 32
    group_expand_triangle_size: int = 4
    group_icon_size: int = 16
    group_text_padding: int = 8

    # Search and toolbar
    search_bar_height: int = 30
    toolbar_height: int = 28
    toolbar_button_size: int = 24
    toolbar_button_spacing: int = 4

    # Visual elements (following property panel)
    border_width: int = 1
    focus_border_width: int = 2
    corner_radius: int = 3
    control_spacing: int = 4
    control_padding: int = 4

    # Text and favorites
    favorite_star_size: int = 12
    favorite_star_offset: Tuple[int, int] = (4, 4)
    loading_indicator_size: int = 16


@dataclass
class ToolPaletteBehaviorConfig:
    """Behavior configuration"""
    show_descriptions: bool = True
    show_shortcuts: bool = True
    show_tooltips: bool = True
    show_categories: bool = True
    show_favorites_section: bool = True
    show_usage_stats: bool = False
    search_in_descriptions: bool = True
    group_by_category: bool = True
    track_usage_statistics: bool = True
    auto_expand_on_search: bool = True
    animate_hover_effects: bool = True
    show_loading_indicators: bool = True


@dataclass
class ToolPaletteConfig:
    """Complete configuration for tool palette panel"""
    layout: ToolPaletteLayoutConfig = field(default_factory=ToolPaletteLayoutConfig)
    behavior: ToolPaletteBehaviorConfig = field(default_factory=ToolPaletteBehaviorConfig)
    default_view_mode: ToolViewMode = ToolViewMode.GRID


class ToolThemeManager:
    """theme manager matching property panel capabilities"""

    def __init__(self, ui_manager: pygame_gui.UIManager, element_ids: List[str]):
        self.ui_manager = ui_manager
        self.element_ids = element_ids
        self.themed_colors = {}
        self.themed_font = None
        self.update_theme_data()

    def update_theme_data(self):
        """Update theme-dependent data with comprehensive fallbacks matching property panel"""

        # Comprehensive color mappings with tool-specific additions
        color_mappings = {
            # Basic panel colors (matching property panel)
            'dark_bg': pygame.Color(45, 45, 45),
            'normal_text': pygame.Color(255, 255, 255),
            'secondary_text': pygame.Color(180, 180, 180),
            'readonly_text': pygame.Color(150, 150, 150),

            # Section/group colors (matching property panel)
            'section_bg': pygame.Color(35, 35, 35),
            'section_text': pygame.Color(200, 200, 200),

            # Tool-specific colors (from basic control colors)
            'tool_bg': pygame.Color(60, 60, 60),
            'tool_text': pygame.Color(255, 255, 255),
            'tool_border': pygame.Color(100, 100, 100),

            # State colors (matching property panel states)
            'focused_bg': pygame.Color(50, 80, 120),
            'focused_border': pygame.Color(120, 160, 255),
            'hovered_bg': pygame.Color(50, 50, 50),
            'selected_bg': pygame.Color(70, 130, 180),

            # Tool-specific state colors
            'disabled_bg': pygame.Color(40, 40, 40),
            'disabled_text': pygame.Color(120, 120, 120),
            'active_bg': pygame.Color(90, 150, 210),
            'active_border': pygame.Color(140, 180, 255),
            'loading_bg': pygame.Color(80, 60, 40),
            'loading_text': pygame.Color(255, 200, 100),

            # Status colors (matching property panel validation colors)
            'error_bg': pygame.Color(60, 20, 20),
            'error_text': pygame.Color(255, 100, 100),
            'warning_bg': pygame.Color(80, 60, 20),
            'warning_text': pygame.Color(255, 200, 100),
            'success_bg': pygame.Color(20, 60, 20),
            'success_text': pygame.Color(100, 255, 100),

            # Tool-specific UI elements
            'favorite_star': pygame.Color(255, 215, 0),
            'favorite_star_outline': pygame.Color(200, 150, 0),
            'usage_indicator': pygame.Color(100, 200, 100),
            'search_highlight': pygame.Color(255, 255, 0, 100),

            # Borders and accents (matching property panel)
            'normal_border': pygame.Color(80, 80, 80),
            'accent': pygame.Color(100, 200, 100),

            # Toolbar specific colors
            'toolbar_bg': pygame.Color(30, 30, 30),
            'toolbar_button_bg': pygame.Color(50, 50, 50),
            'toolbar_button_text': pygame.Color(255, 255, 255),
            'toolbar_button_active': pygame.Color(70, 130, 180),

            # Search specific colors
            'search_bg': pygame.Color(40, 40, 40),
            'search_text': pygame.Color(255, 255, 255),
            'search_placeholder': pygame.Color(150, 150, 150),
            'search_border': pygame.Color(100, 100, 100),
        }

        try:
            self.themed_colors = {}
            theme = self.ui_manager.get_theme()

            for color_id, default_color in color_mappings.items():
                try:
                    if hasattr(theme, 'get_colour_or_gradient'):
                        color = theme.get_colour_or_gradient(color_id, self.element_ids)
                        # Handle gradients properly - if it's a gradient, we might want to extract a solid color
                        if color:
                            if hasattr(color, 'colour_1'):  # It's a gradient
                                # Use the first color of the gradient as fallback
                                self.themed_colors[color_id] = color.colour_1
                            else:
                                self.themed_colors[color_id] = color
                        else:
                            self.themed_colors[color_id] = default_color
                    else:
                        self.themed_colors[color_id] = default_color
                except Exception as e:
                    if TOOL_DEBUG:
                        print(f"Warning: Could not get themed color '{color_id}': {e}")
                    self.themed_colors[color_id] = default_color

            # Get themed font with comprehensive fallbacks
            try:
                if hasattr(theme, 'get_font'):
                    font = theme.get_font(self.element_ids)
                    if hasattr(font, 'get_font_size'):
                        # It's a pygame_gui font interface
                        self.themed_font = font
                    else:
                        # Fallback to pygame font
                        raise Exception("No valid font interface")
                else:
                    raise Exception("No font method")
            except Exception as e:
                if TOOL_DEBUG:
                    print(f"Warning: Could not get themed font: {e}, using fallback")
                try:
                    self.themed_font = pygame.font.SysFont('Arial', 12)
                except Exception as e2:
                    if TOOL_DEBUG:
                        print(f"Warning: Could not get system font: {e2}, using default")
                    self.themed_font = pygame.font.Font(None, 12)

        except Exception as e:
            if TOOL_DEBUG:
                print(f"Error getting theme data: {e}")
            # Complete fallback - use all default colors
            self.themed_colors = color_mappings
            try:
                self.themed_font = pygame.font.SysFont('Arial', 12)
            except:
                self.themed_font = pygame.font.Font(None, 12)

    def rebuild_from_changed_theme_data(self):
        """Called when theme data changes (matching property panel)"""
        if TOOL_DEBUG:
            print("Rebuilding tool palette theme data from changed theme")
        self.update_theme_data()

    def get_color(self, color_id: str, fallback: pygame.Color = None) -> pygame.Color:
        """Get a themed color with fallback (matching property panel)"""
        color = self.themed_colors.get(color_id, fallback or pygame.Color(255, 255, 255))
        if TOOL_DEBUG and color_id not in self.themed_colors:
            print(f"Warning: Color '{color_id}' not found in theme, using fallback")
        return color

    def get_font(self):
        """Get the themed font (matching property panel)"""
        return self.themed_font

    def get_all_colors(self) -> Dict[str, pygame.Color]:
        """Get all themed colors for debugging"""
        return self.themed_colors.copy()

    def apply_color_scheme(self, scheme_colors: Dict[str, pygame.Color]):
        """Apply a color scheme override"""
        for color_id, color in scheme_colors.items():
            if color_id in self.themed_colors:
                self.themed_colors[color_id] = color
                if TOOL_DEBUG:
                    print(f"Applied color scheme override: {color_id} = {color}")


class ToolRenderer:
    """tool renderer with better state management"""

    def __init__(self, tool: Tool, config: ToolPaletteConfig):
        self.tool = tool
        self.config = config
        self.is_selected = False
        self.is_focused = False
        self.is_hovered = False
        self.is_pressed = False
        self.rect = pygame.Rect(0, 0, 0, 0)

        # Animation state
        self.hover_time = 0.0
        self.press_time = 0.0

    def set_geometry(self, rect: pygame.Rect):
        """Set the geometry for this tool renderer"""
        self.rect = rect

    def update(self, time_delta: float):
        """Update renderer animations"""
        if self.is_hovered and self.config.behavior.animate_hover_effects:
            self.hover_time = min(1.0, self.hover_time + time_delta * 4)
        else:
            self.hover_time = max(0.0, self.hover_time - time_delta * 4)

        if self.is_pressed:
            self.press_time = min(1.0, self.press_time + time_delta * 8)
        else:
            self.press_time = max(0.0, self.press_time - time_delta * 8)

    def draw(self, surface: pygame.Surface, theme_manager: ToolThemeManager):
        """Draw the tool renderer with theming"""
        self._draw_background(surface, theme_manager)
        self._draw_content(surface, theme_manager)
        self._draw_status_indicators(surface, theme_manager)

    def _draw_background(self, surface: pygame.Surface, theme_manager: ToolThemeManager):
        """Draw background with state handling"""
        # Determine background color based on state priority
        if not self.tool.enabled:
            bg_color = theme_manager.get_color('disabled_bg')
        elif self.tool.is_loading:
            bg_color = theme_manager.get_color('loading_bg')
        elif self.is_pressed:
            bg_color = theme_manager.get_color('active_bg')
        elif self.is_selected:
            bg_color = theme_manager.get_color('selected_bg')
        elif self.is_hovered:
            # Animate hover background
            base_color = theme_manager.get_color('tool_bg')
            hover_color = theme_manager.get_color('hovered_bg')
            if self.config.behavior.animate_hover_effects and self.hover_time > 0:
                # Blend colors based on hover time
                r = int(base_color.r + (hover_color.r - base_color.r) * self.hover_time)
                g = int(base_color.g + (hover_color.g - base_color.g) * self.hover_time)
                b = int(base_color.b + (hover_color.b - base_color.b) * self.hover_time)
                bg_color = pygame.Color(r, g, b)
            else:
                bg_color = hover_color
        else:
            bg_color = theme_manager.get_color('tool_bg')

        pygame.draw.rect(surface, bg_color, self.rect,
                         border_radius=self.config.layout.corner_radius)

        # border handling
        if self.is_focused:
            border_color = theme_manager.get_color('focused_border')
            border_width = self.config.layout.focus_border_width
        elif self.is_pressed:
            border_color = theme_manager.get_color('active_border')
            border_width = self.config.layout.border_width
        elif not self.tool.enabled:
            border_color = theme_manager.get_color('disabled_text')
            border_width = self.config.layout.border_width
        else:
            border_color = theme_manager.get_color('tool_border')
            border_width = self.config.layout.border_width

        pygame.draw.rect(surface, border_color, self.rect,
                         border_width,
                         border_radius=self.config.layout.corner_radius)

    def _draw_content(self, surface: pygame.Surface, theme_manager: ToolThemeManager):
        """Draw tool content - override in subclasses"""
        pass

    def _draw_status_indicators(self, surface: pygame.Surface, theme_manager: ToolThemeManager):
        """Draw status indicators"""
        layout = self.config.layout
        behavior = self.config.behavior

        # Favorite star indicator (enhanced)
        if self.tool.is_favorite and behavior.show_favorites_section:
            star_color = theme_manager.get_color('favorite_star')
            outline_color = theme_manager.get_color('favorite_star_outline')
            star_x = self.rect.right - layout.favorite_star_offset[0]
            star_y = self.rect.y + layout.favorite_star_offset[1]
            star_size = layout.favorite_star_size

            # Draw star outline
            pygame.draw.circle(surface, outline_color, (star_x, star_y), star_size // 2 + 1)
            # Draw star fill
            pygame.draw.circle(surface, star_color, (star_x, star_y), star_size // 2)

        # Loading indicator
        if self.tool.is_loading and behavior.show_loading_indicators:
            loading_color = theme_manager.get_color('loading_text')
            loading_x = self.rect.x + layout.control_padding
            loading_y = self.rect.y + layout.control_padding
            loading_size = layout.loading_indicator_size

            # Simple loading indicator (could be animated)
            pygame.draw.circle(surface, loading_color,
                               (loading_x + loading_size // 2, loading_y + loading_size // 2),
                               loading_size // 4)

        # Usage statistics indicator
        if behavior.show_usage_stats and self.tool.use_count > 0:
            usage_color = theme_manager.get_color('usage_indicator')
            usage_text = str(self.tool.use_count)

            try:
                font = theme_manager.get_font()
                if hasattr(font, 'render_premul'):
                    usage_surface = font.render_premul(usage_text, usage_color)
                else:
                    usage_surface = font.render(usage_text, True, usage_color)

                usage_x = self.rect.x + layout.control_padding
                usage_y = self.rect.bottom - layout.control_padding - usage_surface.get_height()
                surface.blit(usage_surface, (usage_x, usage_y))
            except Exception:
                pass

    def handle_event(self, event: pygame.event.Event, relative_pos: Tuple[int, int]) -> bool:
        """Handle input events with state tracking"""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(relative_pos):
                self.is_pressed = True
                return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.is_pressed = False

        return False


class GridToolRenderer(ToolRenderer):
    """grid view tool renderer"""

    def _draw_content(self, surface: pygame.Surface, theme_manager: ToolThemeManager):
        layout = self.config.layout

        # Icon area with theming
        icon_size = layout.grid_icon_size
        icon_rect = pygame.Rect(
            self.rect.centerx - icon_size[0] // 2,
            self.rect.y + layout.grid_padding,
            icon_size[0],
            icon_size[1]
        )

        # Determine icon color based on tool state
        if not self.tool.enabled:
            icon_color = theme_manager.get_color('disabled_text')
        elif self.tool.is_loading:
            icon_color = theme_manager.get_color('loading_text')
        else:
            icon_color = theme_manager.get_color('tool_text')

        # Draw icon placeholder with styling
        pygame.draw.rect(surface, icon_color, icon_rect, 2,
                         border_radius=layout.corner_radius)

        # Tool name with text rendering
        name_y = icon_rect.bottom + layout.grid_padding
        text_color = icon_color  # Use same color as icon

        try:
            font = theme_manager.get_font()
            text = self.tool.name

            # Truncate text if too long for grid cell
            max_width = self.rect.width - 2 * layout.grid_padding
            if hasattr(font, 'size'):
                text_width = font.size(text)[0]
                if text_width > max_width:
                    # Simple truncation - could be enhanced
                    while text and font.size(text + "...")[0] > max_width:
                        text = text[:-1]
                    if text:
                        text += "..."

            if hasattr(font, 'render_premul'):
                text_surface = font.render_premul(text, text_color)
            else:
                text_surface = font.render(text, True, text_color)

            text_x = self.rect.x + (self.rect.width - text_surface.get_width()) // 2
            text_y = name_y + (self.rect.bottom - name_y - text_surface.get_height()) // 2
            surface.blit(text_surface, (text_x, text_y))
        except Exception as e:
            if TOOL_DEBUG:
                print(f"Error rendering grid tool text: {e}")


class ListToolRenderer(ToolRenderer):
    """list view tool renderer"""

    def _draw_content(self, surface: pygame.Surface, theme_manager: ToolThemeManager):
        layout = self.config.layout

        # Icon with theming
        icon_size = layout.list_icon_size
        icon_rect = pygame.Rect(
            self.rect.x + layout.list_text_padding,
            self.rect.y + (self.rect.height - icon_size) // 2,
            icon_size,
            icon_size
        )

        # Determine colors based on tool state
        if not self.tool.enabled:
            icon_color = theme_manager.get_color('disabled_text')
            text_color = theme_manager.get_color('disabled_text')
        elif self.tool.is_loading:
            icon_color = theme_manager.get_color('loading_text')
            text_color = theme_manager.get_color('loading_text')
        else:
            icon_color = theme_manager.get_color('tool_text')
            text_color = theme_manager.get_color('tool_text')

        # Draw icon placeholder
        pygame.draw.rect(surface, icon_color, icon_rect, 1,
                         border_radius=layout.corner_radius)

        # Tool name
        name_x = icon_rect.right + layout.list_text_padding

        try:
            font = theme_manager.get_font()
            if hasattr(font, 'render_premul'):
                text_surface = font.render_premul(self.tool.name, text_color)
            else:
                text_surface = font.render(self.tool.name, True, text_color)

            text_y = self.rect.y + (self.rect.height - text_surface.get_height()) // 2
            surface.blit(text_surface, (name_x, text_y))

            # shortcut display
            if self.tool.shortcut and self.config.behavior.show_shortcuts:
                shortcut_color = theme_manager.get_color('secondary_text')
                if hasattr(font, 'render_premul'):
                    shortcut_surface = font.render_premul(self.tool.shortcut, shortcut_color)
                else:
                    shortcut_surface = font.render(self.tool.shortcut, True, shortcut_color)

                shortcut_x = self.rect.right - layout.list_text_padding - shortcut_surface.get_width()
                # Account for favorite star
                if self.tool.is_favorite:
                    shortcut_x -= layout.favorite_star_size + layout.control_padding

                surface.blit(shortcut_surface, (shortcut_x, text_y))
        except Exception as e:
            if TOOL_DEBUG:
                print(f"Error rendering list tool text: {e}")


class DetailToolRenderer(ToolRenderer):
    """detail view tool renderer"""

    def _draw_content(self, surface: pygame.Surface, theme_manager: ToolThemeManager):
        layout = self.config.layout

        # Icon with theming
        icon_size = layout.detail_icon_size
        icon_rect = pygame.Rect(
            self.rect.x + layout.list_text_padding,
            self.rect.y + layout.list_text_padding,
            icon_size,
            icon_size
        )

        # Determine colors based on tool state
        if not self.tool.enabled:
            icon_color = theme_manager.get_color('disabled_text')
            text_color = theme_manager.get_color('disabled_text')
            desc_color = theme_manager.get_color('disabled_text')
        elif self.tool.is_loading:
            icon_color = theme_manager.get_color('loading_text')
            text_color = theme_manager.get_color('loading_text')
            desc_color = theme_manager.get_color('secondary_text')
        else:
            icon_color = theme_manager.get_color('tool_text')
            text_color = theme_manager.get_color('tool_text')
            desc_color = theme_manager.get_color('secondary_text')

        # Draw icon placeholder
        pygame.draw.rect(surface, icon_color, icon_rect, 2,
                         border_radius=layout.corner_radius)

        # Text area
        text_x = icon_rect.right + layout.list_text_padding

        try:
            font = theme_manager.get_font()

            # Tool name
            if hasattr(font, 'render_premul'):
                name_surface = font.render_premul(self.tool.name, text_color)
            else:
                name_surface = font.render(self.tool.name, True, text_color)

            name_y = self.rect.y + layout.list_text_padding
            surface.blit(name_surface, (text_x, name_y))

            # tool description
            if self.tool.description and self.config.behavior.show_descriptions:
                desc_y = name_y + name_surface.get_height() + 2

                # Smart text wrapping and truncation
                max_desc_width = self.rect.right - text_x - layout.list_text_padding
                if self.tool.is_favorite:
                    max_desc_width -= layout.favorite_star_size + layout.control_padding

                display_desc = self.tool.description
                max_desc_length = 80  # Increased for detail view

                if len(display_desc) > max_desc_length:
                    display_desc = display_desc[:max_desc_length] + "..."

                if hasattr(font, 'render_premul'):
                    desc_surface = font.render_premul(display_desc, desc_color)
                else:
                    desc_surface = font.render(display_desc, True, desc_color)

                surface.blit(desc_surface, (text_x, desc_y))

            # shortcut display
            if self.tool.shortcut and self.config.behavior.show_shortcuts:
                shortcut_color = theme_manager.get_color('secondary_text')
                if hasattr(font, 'render_premul'):
                    shortcut_surface = font.render_premul(self.tool.shortcut, shortcut_color)
                else:
                    shortcut_surface = font.render(self.tool.shortcut, True, shortcut_color)

                shortcut_x = self.rect.right - layout.list_text_padding - shortcut_surface.get_width()
                shortcut_y = self.rect.bottom - layout.list_text_padding - shortcut_surface.get_height()

                # Account for favorite star
                if self.tool.is_favorite:
                    shortcut_x -= layout.favorite_star_size + layout.control_padding

                surface.blit(shortcut_surface, (shortcut_x, shortcut_y))
        except Exception as e:
            if TOOL_DEBUG:
                print(f"Error rendering detail tool text: {e}")


class ToolPalettePanel(UIElement):
    """tool palette panel with comprehensive theming"""

    def __init__(self, relative_rect: pygame.Rect,
                 manager: pygame_gui.UIManager,
                 config: ToolPaletteConfig = None,
                 container: IContainerLikeInterface = None,
                 object_id: Union[ObjectID, str, None] = None,
                 anchors: Dict[str, str] = None):

        # Handle object_id properly
        if isinstance(object_id, ObjectID):
            self._object_id = object_id
        elif isinstance(object_id, str):
            self._object_id = ObjectID(object_id=object_id, class_id=None)
        else:
            self._object_id = ObjectID(object_id='#tool_palette_panel', class_id=None)

        super().__init__(relative_rect, manager, container,
                         starting_height=1, layer_thickness=1,
                         anchors=anchors, object_id=self._object_id)

        self.config = config or ToolPaletteConfig()

        # Create theme manager
        element_ids = ['tool_palette_panel']
        if hasattr(self, 'object_ids') and self.object_ids:
            element_ids.extend(self.object_ids)
        self.theme_manager = ToolThemeManager(manager, element_ids)

        # Tool data (following property panel pattern)
        self.tool_groups: Dict[str, ToolGroup] = {}
        self.tools: Dict[str, Tool] = {}
        self.favorites: Set[str] = set()

        # Current state
        self.view_mode = self.config.default_view_mode
        self.search_query = ""
        self.selected_tool: Optional[str] = None
        self.focused_tool: Optional[str] = None

        # UI state (following property panel pattern)
        self.scroll_y = 0
        self.max_scroll = 0
        self.content_height = 0
        self.is_panel_focused = False

        # Layout state (following property panel pattern)
        self._last_rebuild_state = None

        # Visible items cache
        self.visible_groups: List[ToolGroup] = []
        self.visible_tools: List[Tool] = []
        self.renderers: Dict[str, ToolRenderer] = {}
        self.group_rects: Dict[str, pygame.Rect] = {}

        # Layout rects
        self.toolbar_rect = pygame.Rect(0, 0, 0, 0)
        self.search_rect = pygame.Rect(0, 0, 0, 0)
        self.content_rect = pygame.Rect(0, 0, 0, 0)

        # Interaction state
        self.last_click_time = 0.0
        self.last_clicked_tool: Optional[str] = None

        # Create the image surface
        self.image = pygame.Surface(self.rect.size).convert()

        # Initialize
        self.rebuild_ui()
        self.rebuild_image()

    def _needs_rebuild(self) -> bool:
        """Check if UI needs rebuilding (following property panel pattern)"""
        current_state = {
            'scroll_y': self.scroll_y,
            'rect_size': (self.rect.width, self.rect.height),
            'group_states': {g.id: g.expanded for g in self.tool_groups.values()},
            'focused_tool': self.focused_tool,
            'selected_tool': self.selected_tool,
            'tool_count': len(self.tools),
            'view_mode': self.view_mode,
            'search_query': self.search_query,
            'grid_item_width': self.config.layout.grid_item_width,
            'grid_item_height': self.config.layout.grid_item_height,
            'list_item_height': self.config.layout.list_item_height,
        }

        if current_state != self._last_rebuild_state:
            self._last_rebuild_state = current_state
            return True

        return False

    def rebuild_from_changed_theme_data(self):
        """Called when theme data changes (matching property panel)"""
        if TOOL_DEBUG:
            print("Rebuilding tool palette from changed theme data")
        self.theme_manager.rebuild_from_changed_theme_data()
        self.rebuild_ui()
        self.rebuild_image()

    def update_layout_config(self, layout_config: ToolPaletteLayoutConfig):
        """Update layout configuration and rebuild (matching property panel)"""
        self.config.layout = copy.deepcopy(layout_config)
        self._last_rebuild_state = None
        self.rebuild_ui()
        self.rebuild_image()
        if TOOL_DEBUG:
            print(
                f"Layout updated - grid item size: {self.config.layout.grid_item_width}x{self.config.layout.grid_item_height}")

    def update_behavior_config(self, behavior_config: ToolPaletteBehaviorConfig):
        """Update behavior configuration (matching property panel)"""
        self.config.behavior = copy.deepcopy(behavior_config)
        self._last_rebuild_state = None
        self.rebuild_ui()
        self.rebuild_image()
        if TOOL_DEBUG:
            print(f"Behavior updated - show descriptions: {self.config.behavior.show_descriptions}")

    def apply_color_scheme(self, scheme_colors: Dict[str, pygame.Color]):
        """Apply a color scheme to the theme manager"""
        self.theme_manager.apply_color_scheme(scheme_colors)
        self.rebuild_image()

    def draw(self, surface: pygame.Surface):
        """Draw the panel image to the screen."""
        surface.blit(self.image, self.rect)

    def debug_print_complete_state(self):
        """Print complete debug information"""
        print(f"\n=== COMPLETE DEBUG STATE ===")
        print(f"View mode: {self.view_mode}")
        print(f"Scroll Y: {self.scroll_y}/{self.max_scroll}")
        print(f"Content rect: {self.content_rect}")

        print(f"\nTool groups ({len(self.tool_groups)}):")
        for group_id, group in self.tool_groups.items():
            print(f"  {group_id} ({group.name}): expanded={group.expanded}, {len(group.tools)} tools")
            for tool in group.tools:
                print(f"    - {tool.name} (id={tool.id})")

        print(f"\nVisible groups ({len(self.visible_groups)}):")
        for group in self.visible_groups:
            print(f"  {group.name}: expanded={group.expanded}")

        print(f"\nVisible tools ({len(self.visible_tools)}):")
        for tool in self.visible_tools:
            print(f"  {tool.name} (group: {tool.category})")

        print(f"\nRenderers ({len(self.renderers)}):")
        for tool_id, renderer in self.renderers.items():
            print(f"  {tool_id}: {renderer.rect}")

        print(f"\nGroup rects:")
        for group_id, rect in self.group_rects.items():
            print(f"  {group_id}: {rect}")

    def get_tool_by_id(self, tool_id: str) -> Optional[Tool]:
        """Get a tool by its ID"""
        return self.tools.get(tool_id)

    def get_group_by_id(self, group_id: str) -> Optional[ToolGroup]:
        """Get a group by its ID"""
        return self.tool_groups.get(group_id)

    def get_tools_by_type(self, tool_type: ToolType) -> List[Tool]:
        """Get all tools of a specific type"""
        return [tool for tool in self.tools.values() if tool.tool_type == tool_type]

    def get_favorite_tools(self) -> List[Tool]:
        """Get all favorite tools"""
        return [tool for tool in self.tools.values() if tool.is_favorite]

    def clear_all_tools(self):
        """Clear all tools and groups"""
        self.tools.clear()
        self.tool_groups.clear()
        self.favorites.clear()
        self.visible_tools.clear()
        self.visible_groups.clear()
        self.renderers.clear()
        self.group_rects.clear()
        self.selected_tool = None
        self.focused_tool = None
        self.rebuild_ui()
        self.rebuild_image()

    def expand_all_groups(self):
        """Expand all groups"""
        changed = False
        for group in self.tool_groups.values():
            if not group.expanded:
                group.expanded = True
                changed = True

        if changed:
            self.rebuild_ui()
            self.rebuild_image()

    def collapse_all_groups(self):
        """Collapse all groups"""
        changed = False
        for group in self.tool_groups.values():
            if group.expanded:
                group.expanded = False
                changed = True

        if changed:
            self.rebuild_ui()
            self.rebuild_image()

    def set_tool_enabled(self, tool_id: str, enabled: bool):
        """Enable or disable a tool"""
        if tool_id in self.tools:
            self.tools[tool_id].enabled = enabled
            self.rebuild_image()

    def set_tool_loading(self, tool_id: str, loading: bool):
        """Set a tool's loading state"""
        if tool_id in self.tools:
            self.tools[tool_id].is_loading = loading
            self.rebuild_image()

    def get_usage_statistics(self) -> Dict[str, int]:
        """Get usage statistics for all tools"""
        return {tool_id: tool.use_count for tool_id, tool in self.tools.items()}

    def sort_tools_by_usage(self, group_id: Optional[str] = None):
        """Sort tools by usage count"""
        if group_id and group_id in self.tool_groups:
            # Sort tools in specific group
            group = self.tool_groups[group_id]
            group.tools.sort(key=lambda t: t.use_count, reverse=True)
        else:
            # Sort tools in all groups
            for group in self.tool_groups.values():
                group.tools.sort(key=lambda t: t.use_count, reverse=True)

        self.rebuild_ui()
        self.rebuild_image()

    def filter_tools_by_enabled(self, enabled_only: bool = True):
        """Filter to show only enabled or disabled tools"""
        # This would require adding a filter state to the class
        # For now, we'll modify the _should_show_tool method
        pass

    def export_tool_configuration(self) -> Dict[str, Any]:
        """Export current tool configuration"""
        config_data = {
            'groups': [],
            'view_mode': self.view_mode.value,
            'search_query': self.search_query,
            'layout_config': {
                'grid_item_width': self.config.layout.grid_item_width,
                'grid_item_height': self.config.layout.grid_item_height,
                'list_item_height': self.config.layout.list_item_height,
            },
            'behavior_config': {
                'show_descriptions': self.config.behavior.show_descriptions,
                'show_shortcuts': self.config.behavior.show_shortcuts,
                'show_favorites_section': self.config.behavior.show_favorites_section,
            }
        }

        for group in self.tool_groups.values():
            group_data = {
                'id': group.id,
                'name': group.name,
                'description': group.description,
                'expanded': group.expanded,
                'order': group.order,
                'tools': []
            }

            for tool in group.tools:
                tool_data = {
                    'id': tool.id,
                    'name': tool.name,
                    'description': tool.description,
                    'tool_type': tool.tool_type.value,
                    'category': tool.category,
                    'shortcut': tool.shortcut,
                    'enabled': tool.enabled,
                    'visible': tool.visible,
                    'is_favorite': tool.is_favorite,
                    'use_count': tool.use_count,
                }
                group_data['tools'].append(tool_data)

            config_data['groups'].append(group_data)

        return config_data

    def import_tool_configuration(self, config_data: Dict[str, Any]):
        """Import tool configuration"""
        # Clear existing tools
        self.clear_all_tools()

        # Import layout config
        if 'layout_config' in config_data:
            layout_data = config_data['layout_config']
            self.config.layout.grid_item_width = layout_data.get('grid_item_width', 120)
            self.config.layout.grid_item_height = layout_data.get('grid_item_height', 100)
            self.config.layout.list_item_height = layout_data.get('list_item_height', 28)

        # Import behavior config
        if 'behavior_config' in config_data:
            behavior_data = config_data['behavior_config']
            self.config.behavior.show_descriptions = behavior_data.get('show_descriptions', True)
            self.config.behavior.show_shortcuts = behavior_data.get('show_shortcuts', True)
            self.config.behavior.show_favorites_section = behavior_data.get('show_favorites_section', True)

        # Import groups and tools
        for group_data in config_data.get('groups', []):
            group = ToolGroup(
                id=group_data['id'],
                name=group_data['name'],
                description=group_data.get('description', ''),
                expanded=group_data.get('expanded', True),
                order=group_data.get('order', 0)
            )

            for tool_data in group_data.get('tools', []):
                tool = Tool(
                    id=tool_data['id'],
                    name=tool_data['name'],
                    description=tool_data.get('description', ''),
                    tool_type=ToolType(tool_data.get('tool_type', 'utility')),
                    category=tool_data.get('category', 'General'),
                    shortcut=tool_data.get('shortcut', ''),
                    enabled=tool_data.get('enabled', True),
                    visible=tool_data.get('visible', True),
                    is_favorite=tool_data.get('is_favorite', False),
                    use_count=tool_data.get('use_count', 0),
                )
                group.add_tool(tool)

            self.add_group(group)

        # Set view mode and search
        if 'view_mode' in config_data:
            try:
                self.set_view_mode(ToolViewMode(config_data['view_mode']))
            except ValueError:
                pass  # Invalid view mode, keep current

        if 'search_query' in config_data:
            self.set_search_query(config_data['search_query'])

    def refresh(self):
        """Refresh the tool palette display"""
        self.rebuild_ui()
        self.rebuild_image()

    def rebuild_ui(self, force=False):
        """Rebuild the UI layout (following property panel pattern)"""
        if not force and not self._needs_rebuild():
            return

        if TOOL_DEBUG:
            print("Rebuilding tool palette UI...")

        self.visible_groups.clear()
        self.visible_tools.clear()
        self.group_rects.clear()
        self.renderers.clear()

        # Update visible items
        self._update_visible_items()

        # Calculate layout
        self._calculate_layout()

        # Create renderers
        self._create_renderers()

        # Calculate tool positions
        self._calculate_tool_positions()

        if TOOL_DEBUG:
            print(f"UI rebuilt: {len(self.visible_tools)} visible tools, "
                  f"content_height: {self.content_height}, max_scroll: {self.max_scroll}")

    def _update_visible_items(self):
        """Update visible groups and tools based on search and filters"""
        self.visible_groups = []
        self.visible_tools = []

        # Get all groups sorted by order
        all_groups = sorted(self.tool_groups.values(), key=lambda g: g.order)

        for group in all_groups:
            group_tools = []

            # Check all tools in this group
            for tool in group.tools:
                if self._should_show_tool(tool):
                    group_tools.append(tool)

            # Only show group if it has visible tools or no search is active
            if group_tools or not self.search_query:
                self.visible_groups.append(group)

                # Only add tools to visible_tools if group is expanded
                if group.expanded:
                    self.visible_tools.extend(group_tools)

    def _should_show_tool(self, tool: Tool) -> bool:
        """Check if tool should be visible based on filters"""
        if not tool.visible:
            return False

        # Search filter
        if self.search_query:
            search_targets = [tool.name.lower()]
            if self.config.behavior.search_in_descriptions:
                search_targets.append(tool.description.lower())

            found = any(self.search_query.lower() in target for target in search_targets)
            if not found:
                return False

        return True

    def _calculate_layout(self):
        """Calculate layout rectangles (following property panel pattern)"""
        layout = self.config.layout

        # Toolbar
        self.toolbar_rect = pygame.Rect(0, 0, self.rect.width, layout.toolbar_height)

        # Search bar
        search_y = layout.toolbar_height
        self.search_rect = pygame.Rect(0, search_y, self.rect.width, layout.search_bar_height)

        # Content area
        content_y = search_y + layout.search_bar_height
        self.content_rect = pygame.Rect(0, content_y, self.rect.width, self.rect.height - content_y)

    def _create_renderers(self):
        """Create tool renderers based on view mode"""
        self.renderers.clear()

        for tool in self.visible_tools:
            if self.view_mode == ToolViewMode.GRID:
                renderer = GridToolRenderer(tool, self.config)
            elif self.view_mode == ToolViewMode.LIST:
                renderer = ListToolRenderer(tool, self.config)
            else:  # DETAIL
                renderer = DetailToolRenderer(tool, self.config)

            renderer.is_selected = (tool.id == self.selected_tool)
            renderer.is_focused = (tool.id == self.focused_tool)
            self.renderers[tool.id] = renderer

    def _calculate_tool_positions(self):
        """Calculate tool positions"""
        layout = self.config.layout
        current_y = layout.grid_padding

        if self.view_mode == ToolViewMode.GRID:
            # Calculate grid parameters
            available_width = self.content_rect.width - 2 * layout.grid_padding
            columns = max(1, available_width // (layout.grid_item_width + layout.grid_padding))

            # Process each group separately
            for group in self.visible_groups:
                # Group header
                if self.config.behavior.show_categories:
                    group_rect = pygame.Rect(0, current_y, self.content_rect.width, layout.group_header_height)
                    self.group_rects[group.id] = group_rect
                    current_y += layout.group_header_height

                # Tools in group (only if expanded)
                if group.expanded:
                    group_tools = [tool for tool in group.tools if self._should_show_tool(tool)]

                    # Layout tools in grid within this group
                    group_start_y = current_y
                    for i, tool in enumerate(group_tools):
                        row = i // columns
                        col = i % columns

                        tool_x = layout.grid_padding + col * (layout.grid_item_width + layout.grid_padding)
                        tool_y = group_start_y + row * (layout.grid_item_height + layout.grid_padding)

                        tool_rect = pygame.Rect(tool_x, tool_y, layout.grid_item_width, layout.grid_item_height)

                        if tool.id in self.renderers:
                            self.renderers[tool.id].set_geometry(tool_rect)

                    # Calculate how much vertical space this group's tools took
                    if group_tools:
                        rows = (len(group_tools) + columns - 1) // columns
                        group_height = rows * (layout.grid_item_height + layout.grid_padding)
                        current_y += group_height

        else:
            # List/detail layout
            item_height = layout.list_item_height if self.view_mode == ToolViewMode.LIST else layout.detail_item_height

            for group in self.visible_groups:
                if self.config.behavior.show_categories:
                    group_rect = pygame.Rect(0, current_y, self.content_rect.width, layout.group_header_height)
                    self.group_rects[group.id] = group_rect
                    current_y += layout.group_header_height

                if group.expanded:
                    group_tools = [tool for tool in group.tools if self._should_show_tool(tool)]

                    for tool in group_tools:
                        tool_rect = pygame.Rect(0, current_y, self.content_rect.width, item_height)
                        if tool.id in self.renderers:
                            self.renderers[tool.id].set_geometry(tool_rect)
                        current_y += item_height

        # Update content height and max scroll
        self.content_height = current_y + layout.grid_padding
        self.max_scroll = max(0, self.content_height - self.content_rect.height)

    def rebuild_image(self):
        """Rebuild the image surface with enhanced theming"""
        # Fill background
        bg_color = self.theme_manager.get_color('dark_bg')
        self.image.fill(bg_color)

        # Draw components
        self._draw_toolbar()
        self._draw_search_bar()
        self._draw_content()

        # Draw border
        border_color = self.theme_manager.get_color('normal_border')
        pygame.draw.rect(self.image, border_color, self.image.get_rect(),
                         self.config.layout.border_width)

        # Draw focus indicator
        if self.is_panel_focused:
            focus_color = self.theme_manager.get_color('focused_border')
            pygame.draw.rect(self.image, focus_color, self.image.get_rect(),
                             self.config.layout.focus_border_width)

    def _draw_toolbar(self):
        """Draw the enhanced toolbar"""
        if self.toolbar_rect.height <= 0:
            return

        try:
            toolbar_surface = self.image.subsurface(self.toolbar_rect)
        except (ValueError, pygame.error):
            return

        # Background with enhanced theming
        bg_color = self.theme_manager.get_color('toolbar_bg')
        toolbar_surface.fill(bg_color)

        # View mode buttons with enhanced styling
        layout = self.config.layout
        button_size = layout.toolbar_button_size
        button_y = (self.toolbar_rect.height - button_size) // 2
        x_offset = layout.toolbar_button_spacing

        # Grid button
        grid_rect = pygame.Rect(x_offset, button_y, button_size, button_size)
        self._draw_toolbar_button(toolbar_surface, grid_rect, "G", self.view_mode == ToolViewMode.GRID)
        x_offset += button_size + layout.toolbar_button_spacing

        # List button
        list_rect = pygame.Rect(x_offset, button_y, button_size, button_size)
        self._draw_toolbar_button(toolbar_surface, list_rect, "L", self.view_mode == ToolViewMode.LIST)
        x_offset += button_size + layout.toolbar_button_spacing

        # Detail button
        detail_rect = pygame.Rect(x_offset, button_y, button_size, button_size)
        self._draw_toolbar_button(toolbar_surface, detail_rect, "D", self.view_mode == ToolViewMode.DETAIL)

    def _draw_toolbar_button(self, surface: pygame.Surface, rect: pygame.Rect, text: str, active: bool):
        """Draw enhanced toolbar button"""
        if active:
            bg_color = self.theme_manager.get_color('toolbar_button_active')
            text_color = self.theme_manager.get_color('normal_text')
        else:
            bg_color = self.theme_manager.get_color('toolbar_button_bg')
            text_color = self.theme_manager.get_color('toolbar_button_text')

        pygame.draw.rect(surface, bg_color, rect, border_radius=self.config.layout.corner_radius)

        # Enhanced border
        border_color = self.theme_manager.get_color('tool_border')
        pygame.draw.rect(surface, border_color, rect, self.config.layout.border_width,
                         border_radius=self.config.layout.corner_radius)

        # Text
        try:
            font = self.theme_manager.get_font()
            if hasattr(font, 'render_premul'):
                text_surface = font.render_premul(text, text_color)
            else:
                text_surface = font.render(text, True, text_color)

            text_rect = text_surface.get_rect(center=rect.center)
            surface.blit(text_surface, text_rect)
        except Exception as e:
            if TOOL_DEBUG:
                print(f"Error rendering toolbar button text: {e}")

    def _draw_search_bar(self):
        """Draw the enhanced search bar"""
        if self.search_rect.height <= 0:
            return

        try:
            search_surface = self.image.subsurface(self.search_rect)
        except (ValueError, pygame.error):
            return

        # Background with enhanced theming
        bg_color = self.theme_manager.get_color('section_bg')
        search_surface.fill(bg_color)

        # Search input area
        layout = self.config.layout
        input_rect = pygame.Rect(
            layout.control_padding,
            layout.control_padding,
            self.search_rect.width - 2 * layout.control_padding,
            self.search_rect.height - 2 * layout.control_padding
        )

        # Input background with enhanced theming
        input_bg_color = self.theme_manager.get_color('search_bg')
        pygame.draw.rect(search_surface, input_bg_color, input_rect,
                         border_radius=self.config.layout.corner_radius)

        # Enhanced input border
        border_color = self.theme_manager.get_color('search_border')
        pygame.draw.rect(search_surface, border_color, input_rect,
                         self.config.layout.border_width,
                         border_radius=self.config.layout.corner_radius)

        # Enhanced search text
        if self.search_query:
            display_text = self.search_query
            text_color = self.theme_manager.get_color('search_text')
        else:
            display_text = "Search tools..."
            text_color = self.theme_manager.get_color('search_placeholder')

        try:
            font = self.theme_manager.get_font()
            if hasattr(font, 'render_premul'):
                text_surface = font.render_premul(display_text, text_color)
            else:
                text_surface = font.render(display_text, True, text_color)

            text_rect = pygame.Rect(
                input_rect.x + layout.control_padding,
                input_rect.y + (input_rect.height - text_surface.get_height()) // 2,
                text_surface.get_width(),
                text_surface.get_height()
            )

            search_surface.blit(text_surface, text_rect)
        except Exception as e:
            if TOOL_DEBUG:
                print(f"Error rendering search text: {e}")

    def _draw_content(self):
        """Draw the content area with enhanced clipping"""
        if self.content_rect.height <= 0:
            return

        try:
            content_surface = self.image.subsurface(self.content_rect)
        except (ValueError, pygame.error):
            return

        # Background
        bg_color = self.theme_manager.get_color('dark_bg')
        content_surface.fill(bg_color)

        # Draw group headers
        for group_id, group in self.tool_groups.items():
            if group_id in self.group_rects:
                stored_rect = self.group_rects[group_id]
                display_rect = pygame.Rect(
                    stored_rect.x,
                    stored_rect.y - self.scroll_y,
                    stored_rect.width,
                    stored_rect.height
                )

                # Only draw if visible
                if display_rect.bottom >= 0 and display_rect.y < content_surface.get_height():
                    self._draw_group_header(content_surface, group, display_rect)

        # Draw tools
        for tool_id, renderer in self.renderers.items():
            display_rect = pygame.Rect(
                renderer.rect.x,
                renderer.rect.y - self.scroll_y,
                renderer.rect.width,
                renderer.rect.height
            )

            # Only draw if visible
            if display_rect.bottom >= 0 and display_rect.y < content_surface.get_height():
                self._draw_tool_at_position(content_surface, renderer, display_rect)

    def _draw_tool_at_position(self, surface: pygame.Surface, renderer: ToolRenderer, display_rect: pygame.Rect):
        """Draw a tool at a specific display position without modifying the renderer's stored rect"""
        if display_rect.bottom < 0 or display_rect.y >= surface.get_height():
            return

        # Calculate visible portion
        visible_rect = display_rect.clip(pygame.Rect(0, 0, surface.get_width(), surface.get_height()))

        if visible_rect.width > 0 and visible_rect.height > 0:
            try:
                # Create subsurface for the visible portion
                tool_surface = surface.subsurface(visible_rect)

                # Create a temporary renderer with the display position
                original_rect = renderer.rect

                # Set temporary rect for drawing (relative to the subsurface)
                renderer.rect = pygame.Rect(
                    display_rect.x - visible_rect.x,
                    display_rect.y - visible_rect.y,
                    display_rect.width,
                    display_rect.height
                )

                # Draw the tool
                renderer.draw(tool_surface, self.theme_manager)

                # Restore original rect immediately
                renderer.rect = original_rect

            except (ValueError, pygame.error) as e:
                if TOOL_DEBUG:
                    print(f"Error drawing tool {renderer.tool.id}: {e}")

                # Fallback: draw directly with temporary rect change
                original_rect = renderer.rect
                renderer.rect = display_rect
                renderer.draw(surface, self.theme_manager)
                renderer.rect = original_rect

    def _draw_group_header(self, surface: pygame.Surface, group: ToolGroup, rect: pygame.Rect):
        """Draw enhanced group header"""
        if rect.bottom < 0 or rect.y >= surface.get_height():
            return

        visible_rect = rect.clip(pygame.Rect(0, 0, surface.get_width(), surface.get_height()))
        if visible_rect.width <= 0 or visible_rect.height <= 0:
            return

        # Enhanced background
        section_bg = self.theme_manager.get_color('section_bg')
        try:
            section_surface = surface.subsurface(visible_rect)
            section_surface.fill(section_bg)
        except (ValueError, pygame.error):
            return

        # Only draw content if header is mostly visible
        if rect.y >= 0 and rect.bottom <= surface.get_height():
            self._draw_group_header_content(surface, group, rect)

    def _draw_group_header_content(self, surface: pygame.Surface, group: ToolGroup, rect: pygame.Rect):
        """Draw enhanced group header content"""
        layout = self.config.layout

        # Enhanced expand/collapse triangle
        triangle_x = 8
        triangle_y = rect.y + rect.height // 2
        triangle_color = self.theme_manager.get_color('section_text')
        triangle_size = layout.group_expand_triangle_size

        if group.expanded:
            # Down triangle (expanded)
            points = [
                (triangle_x, triangle_y - triangle_size),
                (triangle_x + triangle_size * 2, triangle_y - triangle_size),
                (triangle_x + triangle_size, triangle_y + triangle_size)
            ]
        else:
            # Right triangle (collapsed)
            points = [
                (triangle_x, triangle_y - triangle_size),
                (triangle_x, triangle_y + triangle_size),
                (triangle_x + triangle_size + 2, triangle_y)
            ]

        pygame.draw.polygon(surface, triangle_color, points)

        # Enhanced group name
        text_x = triangle_x + triangle_size * 3 + layout.group_text_padding
        text_color = self.theme_manager.get_color('section_text')

        try:
            font = self.theme_manager.get_font()
            group_text = f"{group.name} ({len([t for t in group.tools if self._should_show_tool(t)])})"

            if hasattr(font, 'render_premul'):
                text_surface = font.render_premul(group_text, text_color)
            else:
                text_surface = font.render(group_text, True, text_color)

            text_y = rect.y + (rect.height - text_surface.get_height()) // 2
            surface.blit(text_surface, (text_x, text_y))
        except Exception as e:
            if TOOL_DEBUG:
                print(f"Error rendering group header: {e}")

    # ... [include all the remaining methods from the original class but with enhanced error handling]

    def process_event(self, event: pygame.event.Event) -> bool:
        """Process pygame events with enhanced handling"""
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

        elif event.type == pygame.MOUSEMOTION:
            if self.rect.collidepoint(event.pos):
                relative_pos = (event.pos[0] - self.rect.x, event.pos[1] - self.rect.y)
                consumed = self._handle_mouse_motion(relative_pos)

        elif event.type == pygame.MOUSEWHEEL:
            if self.rect.collidepoint(pygame.mouse.get_pos()):
                consumed = self._handle_scroll(event.y)

        elif event.type == pygame.KEYDOWN and self.is_panel_focused:
            consumed = self._handle_key_event(event)

        return consumed

    def _handle_left_click(self, pos: Tuple[int, int]) -> bool:
        """Handle left mouse click with enhanced logic"""
        current_time = time.time() * 1000

        # Check toolbar clicks
        if self.toolbar_rect.collidepoint(pos):
            return self._handle_toolbar_click(pos)

        # Check search bar clicks
        if self.search_rect.collidepoint(pos):
            return True

        # Check content area clicks
        if self.content_rect.collidepoint(pos):
            # Check group header clicks
            group_id = self._get_group_header_at_position(pos)
            if group_id:
                group = self.tool_groups[group_id]
                group.expanded = not group.expanded

                self._last_rebuild_state = None
                self.rebuild_ui(force=True)
                self.rebuild_image()

                # Send enhanced event
                event_type = UI_TOOL_GROUP_EXPANDED if group.expanded else UI_TOOL_GROUP_COLLAPSED
                event_data = {'ui_element': self, 'group_id': group_id, 'group': group}
                pygame.event.post(pygame.event.Event(event_type, event_data))
                return True

            # Check tool clicks
            tool_id = self._get_tool_at_position(pos)
            if tool_id:
                # Enhanced double click detection
                is_double_click = (tool_id == self.last_clicked_tool and
                                   current_time - self.last_click_time < 500)

                self.last_clicked_tool = tool_id
                self.last_click_time = current_time

                if is_double_click:
                    # Double click event
                    tool = self.tools.get(tool_id)
                    event_data = {'ui_element': self, 'tool_id': tool_id, 'tool': tool}
                    pygame.event.post(pygame.event.Event(UI_TOOL_DOUBLE_CLICKED, event_data))

                    # Execute tool callback with enhanced error handling
                    if tool and tool.callback and tool.enabled:
                        try:
                            if TOOL_DEBUG:
                                print(f"Executing tool: {tool.name}")
                            tool.callback()
                        except Exception as e:
                            if TOOL_DEBUG:
                                print(f"Error executing tool callback for {tool.name}: {e}")
                else:
                    # Single click - select tool
                    self.select_tool(tool_id)

                return True

        return False

    def _handle_right_click(self, pos: Tuple[int, int]) -> bool:
        """Handle right mouse click with enhanced context"""
        if self.content_rect.collidepoint(pos):
            tool_id = self._get_tool_at_position(pos)
            if tool_id:
                tool = self.tools.get(tool_id)
                event_data = {
                    'ui_element': self,
                    'tool_id': tool_id,
                    'tool': tool,
                    'mouse_pos': pos,
                    'can_favorite': tool.enabled if tool else False
                }
                pygame.event.post(pygame.event.Event(UI_TOOL_RIGHT_CLICKED, event_data))
                return True
        return False

    def _handle_mouse_motion(self, pos: Tuple[int, int]) -> bool:
        """Handle mouse motion with enhanced hover effects"""
        tool_id = self._get_tool_at_position(pos) if self.content_rect.collidepoint(pos) else None

        hover_changed = False
        for renderer in self.renderers.values():
            new_hovered = (renderer.tool.id == tool_id)
            if renderer.is_hovered != new_hovered:
                renderer.is_hovered = new_hovered
                hover_changed = True

        if hover_changed:
            self.rebuild_image()

        return hover_changed

    def _handle_scroll(self, delta: int) -> bool:
        """Handle scroll wheel with enhanced scrolling"""
        scroll_speed = self.config.layout.grid_padding * 3  # Enhanced scroll speed
        old_scroll = self.scroll_y
        self.scroll_y = max(0, min(self.max_scroll, self.scroll_y - delta * scroll_speed))

        if old_scroll != self.scroll_y:
            self.rebuild_ui()
            self.rebuild_image()
            return True

        return False

    def _handle_key_event(self, event: pygame.event.Event) -> bool:
        """Handle keyboard events with enhanced navigation"""
        # TODO: Implement enhanced keyboard navigation
        return False

    def _handle_toolbar_click(self, pos: Tuple[int, int]) -> bool:
        """Handle toolbar button clicks with enhanced feedback"""
        layout = self.config.layout
        button_size = layout.toolbar_button_size
        button_y = (self.toolbar_rect.height - button_size) // 2
        x_offset = layout.toolbar_button_spacing

        # Grid button
        grid_rect = pygame.Rect(x_offset, button_y, button_size, button_size)
        if grid_rect.collidepoint(pos):
            self.set_view_mode(ToolViewMode.GRID)
            return True

        x_offset += button_size + layout.toolbar_button_spacing

        # List button
        list_rect = pygame.Rect(x_offset, button_y, button_size, button_size)
        if list_rect.collidepoint(pos):
            self.set_view_mode(ToolViewMode.LIST)
            return True

        x_offset += button_size + layout.toolbar_button_spacing

        # Detail button
        detail_rect = pygame.Rect(x_offset, button_y, button_size, button_size)
        if detail_rect.collidepoint(pos):
            self.set_view_mode(ToolViewMode.DETAIL)
            return True

        return False

    def _get_group_header_at_position(self, pos: Tuple[int, int]) -> Optional[str]:
        """Get group ID of header at position with enhanced accuracy"""
        if not self.config.behavior.show_categories:
            return None

        if not self.content_rect.collidepoint(pos):
            return None

        # Convert to content-relative coordinates
        content_relative_pos = (pos[0] - self.content_rect.x, pos[1] - self.content_rect.y)

        # Check against stored group rects
        for group_id, stored_rect in self.group_rects.items():
            display_rect = pygame.Rect(
                stored_rect.x,
                stored_rect.y - self.scroll_y,
                stored_rect.width,
                stored_rect.height
            )

            if display_rect.collidepoint(content_relative_pos):
                return group_id

        return None

    def _get_tool_at_position(self, pos: Tuple[int, int]) -> Optional[str]:
        """Get tool ID at position with enhanced accuracy"""
        # Convert to content-relative coordinates
        relative_pos = (pos[0] - self.content_rect.x, pos[1] - self.content_rect.y)

        # Check against tool renderer rects
        for tool_id, renderer in self.renderers.items():
            display_rect = pygame.Rect(
                renderer.rect.x,
                renderer.rect.y - self.scroll_y,
                renderer.rect.width,
                renderer.rect.height
            )

            if display_rect.collidepoint(relative_pos):
                return tool_id
        return None

    def select_tool(self, tool_id: Optional[str]):
        """Select a tool with enhanced feedback"""
        if self.selected_tool != tool_id:
            old_selection = self.selected_tool
            self.selected_tool = tool_id

            # Update renderer states
            for renderer in self.renderers.values():
                renderer.is_selected = (renderer.tool.id == tool_id)

            self.rebuild_image()

            # Enhanced usage tracking
            if tool_id and tool_id in self.tools:
                self.tools[tool_id].use_tool()
                if TOOL_DEBUG:
                    print(f"Tool selected: {self.tools[tool_id].name} (used {self.tools[tool_id].use_count} times)")

            # Send enhanced event
            event_data = {
                'ui_element': self,
                'tool_id': tool_id,
                'tool': self.tools.get(tool_id) if tool_id else None,
                'previous_selection': old_selection
            }
            pygame.event.post(pygame.event.Event(UI_TOOL_SELECTED, event_data))

    def set_view_mode(self, mode: ToolViewMode):
        """Set the view mode with enhanced feedback"""
        if self.view_mode != mode:
            old_mode = self.view_mode
            self.view_mode = mode
            self.scroll_y = 0  # Reset scroll
            self.rebuild_ui()
            self.rebuild_image()

            if TOOL_DEBUG:
                print(f"View mode changed: {old_mode.value} -> {mode.value}")

            # Send enhanced event
            event_data = {
                'ui_element': self,
                'view_mode': mode,
                'previous_mode': old_mode
            }
            pygame.event.post(pygame.event.Event(UI_TOOL_VIEW_MODE_CHANGED, event_data))

    def set_search_query(self, query: str):
        """Set search query with enhanced filtering"""
        if self.search_query != query:
            old_query = self.search_query
            self.search_query = query
            self.scroll_y = 0  # Reset scroll
            self.rebuild_ui()
            self.rebuild_image()

            if TOOL_DEBUG:
                visible_count = len(self.visible_tools)
                print(f"Search changed: '{old_query}' -> '{query}' ({visible_count} tools visible)")

            # Send enhanced event
            event_data = {
                'ui_element': self,
                'search_query': query,
                'previous_query': old_query,
                'results_count': len(self.visible_tools)
            }
            pygame.event.post(pygame.event.Event(UI_TOOL_SEARCH_CHANGED, event_data))

    # ... [include remaining public API methods with enhanced error handling]

    def add_group(self, group: ToolGroup):
        """Add a tool group with enhanced feedback"""
        self.tool_groups[group.id] = group
        for tool in group.tools:
            self.tools[tool.id] = tool
            if tool.is_favorite:
                self.favorites.add(tool.id)

        if TOOL_DEBUG:
            print(f"Added group '{group.name}' with {len(group.tools)} tools")

        self.rebuild_ui()
        self.rebuild_image()

    def add_tool(self, tool: Tool, group_id: str = "default"):
        """Add a tool to a group with enhanced feedback"""
        if group_id not in self.tool_groups:
            self.tool_groups[group_id] = ToolGroup(
                id=group_id,
                name=group_id.replace("_", " ").title()
            )

        self.tool_groups[group_id].add_tool(tool)
        self.tools[tool.id] = tool

        if tool.is_favorite:
            self.favorites.add(tool.id)

        if TOOL_DEBUG:
            print(f"Added tool '{tool.name}' to group '{group_id}'")

        self.rebuild_ui()
        self.rebuild_image()

    def remove_tool(self, tool_id: str) -> bool:
        """Remove a tool with enhanced feedback"""
        if tool_id in self.tools:
            tool_name = self.tools[tool_id].name

            # Remove from all groups
            for group in self.tool_groups.values():
                group.remove_tool(tool_id)

            # Remove from main dict and favorites
            del self.tools[tool_id]
            self.favorites.discard(tool_id)

            # Clear selection if this tool was selected
            if self.selected_tool == tool_id:
                self.selected_tool = None

            if TOOL_DEBUG:
                print(f"Removed tool '{tool_name}'")

            self.rebuild_ui()
            self.rebuild_image()
            return True
        return False

    def toggle_favorite(self, tool_id: str):
        """Toggle favorite status of a tool with enhanced feedback"""
        if tool_id in self.tools:
            tool = self.tools[tool_id]
            tool.is_favorite = not tool.is_favorite

            if tool.is_favorite:
                self.favorites.add(tool_id)
            else:
                self.favorites.discard(tool_id)

            if TOOL_DEBUG:
                status = "favorited" if tool.is_favorite else "unfavorited"
                print(f"Tool '{tool.name}' {status}")

            self.rebuild_image()

            # Send enhanced event
            event_type = UI_TOOL_FAVORITED if tool.is_favorite else UI_TOOL_UNFAVORITED
            event_data = {
                'ui_element': self,
                'tool_id': tool_id,
                'tool': tool,
                'favorites_count': len(self.favorites)
            }
            pygame.event.post(pygame.event.Event(event_type, event_data))

    def update(self, time_delta: float):
        """Update the panel with enhanced animations"""
        super().update(time_delta)

        # Update renderer animations
        needs_rebuild = False
        for renderer in self.renderers.values():
            old_hover_time = renderer.hover_time
            old_press_time = renderer.press_time
            renderer.update(time_delta)

            if (old_hover_time != renderer.hover_time or
                    old_press_time != renderer.press_time):
                needs_rebuild = True

        if needs_rebuild:
            self.rebuild_image()

    def get_debug_info(self) -> Dict[str, Any]:
        """Get comprehensive debug information"""
        return {
            'total_tools': len(self.tools),
            'visible_tools': len(self.visible_tools),
            'total_groups': len(self.tool_groups),
            'visible_groups': len(self.visible_groups),
            'favorites': len(self.favorites),
            'selected_tool': self.selected_tool,
            'focused_tool': self.focused_tool,
            'view_mode': self.view_mode.value,
            'search_query': self.search_query,
            'scroll_position': f"{self.scroll_y}/{self.max_scroll}",
            'content_height': self.content_height,
            'theme_colors': len(self.theme_manager.get_all_colors()),
            'panel_focused': self.is_panel_focused,
        }


# Theme definition with comprehensive color support
TOOL_PALETTE_THEME = {
    "tool_palette_panel": {
        "colours": {
            # Basic panel colors (matching property panel)
            "dark_bg": "#2d2d2d",
            "normal_text": "#ffffff",
            "secondary_text": "#b4b4b4",
            "readonly_text": "#969696",

            # Section/group colors
            "section_bg": "#232323",
            "section_text": "#c8c8c8",

            # Tool-specific colors
            "tool_bg": "#3c3c3c",
            "tool_text": "#ffffff",
            "tool_border": "#646464",

            # State colors
            "focused_bg": "#325078",
            "focused_border": "#78a0ff",
            "hovered_bg": "#323232",
            "selected_bg": "#4682b4",

            # Tool-specific state colors
            "disabled_bg": "#1e1e1e",
            "disabled_text": "#646464",
            "active_bg": "#5a96d2",
            "active_border": "#8cb4ff",
            "loading_bg": "#504032",
            "loading_text": "#ffc864",

            # Status colors
            "error_bg": "#3c1414",
            "error_text": "#ff6464",
            "warning_bg": "#503c14",
            "warning_text": "#ffc864",
            "success_bg": "#143c14",
            "success_text": "#64ff64",

            # Tool-specific UI elements
            "favorite_star": "#ffd700",
            "favorite_star_outline": "#b8960c",
            "usage_indicator": "#64c864",
            "search_highlight": "#ffff00",

            # Borders and accents
            "normal_border": "#505050",
            "accent": "#64c864",

            # Toolbar specific colors
            "toolbar_bg": "#1e1e1e",
            "toolbar_button_bg": "#323232",
            "toolbar_button_text": "#ffffff",
            "toolbar_button_active": "#4682b4",

            # Search specific colors
            "search_bg": "#282828",
            "search_text": "#ffffff",
            "search_placeholder": "#969696",
            "search_border": "#646464",
        },
        "font": {
            "name": "arial",
            "size": "12",
            "bold": "0",
            "italic": "0"
        }
    }
}


def create_sample_tools() -> List[ToolGroup]:
    """Create sample tools for demonstration"""
    groups = []

    # Creation Tools with properties
    creation_group = ToolGroup("creation", "Creation Tools", "Tools for creating new content")
    creation_group.add_tool(
        Tool("new_file", "New File", "Create a new file", ToolType.CREATION, "File", shortcut="Ctrl+N"))
    creation_group.add_tool(
        Tool("new_folder", "New Folder", "Create a new folder", ToolType.CREATION, "File", shortcut="Ctrl+Shift+N"))
    creation_group.add_tool(Tool("new_project", "New Project", "Create a new project", ToolType.CREATION, "Project"))
    creation_group.add_tool(
        Tool("add_sprite", "Add Sprite", "Add a sprite to the scene", ToolType.CREATION, "Game", is_favorite=True))
    groups.append(creation_group)

    # Edit Tools with properties
    edit_group = ToolGroup("modification", "Edit Tools", "Tools for modifying content")
    edit_group.add_tool(Tool("cut", "Cut", "Cut selected items", ToolType.MODIFICATION, "Edit", shortcut="Ctrl+X"))
    edit_group.add_tool(Tool("copy", "Copy", "Copy selected items", ToolType.MODIFICATION, "Edit", shortcut="Ctrl+C"))
    edit_group.add_tool(
        Tool("paste", "Paste", "Paste from clipboard", ToolType.MODIFICATION, "Edit", shortcut="Ctrl+V"))
    edit_group.add_tool(
        Tool("delete", "Delete", "Delete selected items", ToolType.MODIFICATION, "Edit", shortcut="Delete"))
    edit_group.add_tool(
        Tool("undo", "Undo", "Undo last action", ToolType.MODIFICATION, "Edit", shortcut="Ctrl+Z", is_favorite=True))
    edit_group.add_tool(
        Tool("redo", "Redo", "Redo last undone action", ToolType.MODIFICATION, "Edit", shortcut="Ctrl+Y"))
    edit_group.add_tool(Tool("find", "Find", "Find and replace text", ToolType.UTILITY, "Edit", shortcut="Ctrl+F"))
    groups.append(edit_group)

    # Navigation Tools with properties
    nav_group = ToolGroup("navigation", "Navigation", "Tools for navigation and view control")
    nav_group.add_tool(Tool("zoom_in", "Zoom In", "Zoom in on content", ToolType.NAVIGATION, "View", shortcut="Ctrl++"))
    nav_group.add_tool(
        Tool("zoom_out", "Zoom Out", "Zoom out from content", ToolType.NAVIGATION, "View", shortcut="Ctrl+-"))
    nav_group.add_tool(
        Tool("fit_view", "Fit to View", "Fit content to view", ToolType.NAVIGATION, "View", shortcut="Ctrl+0"))
    nav_group.add_tool(
        Tool("pan_tool", "Pan Tool", "Pan around content", ToolType.NAVIGATION, "View", shortcut="Space"))
    nav_group.add_tool(
        Tool("fullscreen", "Fullscreen", "Toggle fullscreen mode", ToolType.NAVIGATION, "View", shortcut="F11"))
    groups.append(nav_group)

    # Analysis Tools (new group)
    analysis_group = ToolGroup("analysis", "Analysis Tools", "Tools for analyzing and debugging")
    analysis_group.add_tool(
        Tool("profiler", "Profiler", "Profile application performance", ToolType.ANALYSIS, "Debug", is_loading=True))
    analysis_group.add_tool(
        Tool("inspector", "Inspector", "Inspect object properties", ToolType.ANALYSIS, "Debug", is_favorite=True))
    analysis_group.add_tool(Tool("console", "Console", "Open debug console", ToolType.DEBUG, "Debug", shortcut="F12"))
    analysis_group.add_tool(Tool("memory", "Memory Usage", "View memory consumption", ToolType.ANALYSIS, "Debug"))
    groups.append(analysis_group)

    return groups


def main():
    """demonstration with comprehensive theming features"""
    pygame.init()
    screen = pygame.display.set_mode((1400, 900))
    pygame.display.set_caption("Tool Palette Panel Demo")
    clock = pygame.time.Clock()

    # Create manager with theme
    manager = pygame_gui.UIManager((1400, 900), TOOL_PALETTE_THEME)

    # Create tool palette with configuration
    enhanced_config = ToolPaletteConfig()
    enhanced_config.behavior.show_usage_stats = True
    enhanced_config.behavior.animate_hover_effects = True
    enhanced_config.behavior.show_loading_indicators = True

    tool_palette = ToolPalettePanel(
        pygame.Rect(50, 50, 450, 700),
        manager,
        enhanced_config,
        object_id=ObjectID(object_id='#main_palette', class_id='@enhanced_tool_palette')
    )

    # Add sample tools
    sample_groups = create_sample_tools()
    for group in sample_groups:
        tool_palette.add_group(group)

    print("\nTool Palette Panel Demo")
    print("\nControls:")
    print("- Press 'G/L/D' to change view mode")
    print("- Press 'S' to toggle search")
    print("- Press 'T' to toggle theme (dark/light)")
    print("- Press 'F' to toggle favorites for selected tool")
    print("- Press 'U' to toggle usage statistics")
    print("- Press 'A' to toggle animations")
    print("- Press 'R' to reset view")
    print("- Press 'I' to show debug info")

    # demo state
    current_theme = "dark"
    show_debug_info = False

    running = True
    while running:
        time_delta = clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_g:
                    tool_palette.set_view_mode(ToolViewMode.GRID)
                    print("Switched to Grid view")
                elif event.key == pygame.K_l:
                    tool_palette.set_view_mode(ToolViewMode.LIST)
                    print("Switched to List view")
                elif event.key == pygame.K_d:
                    tool_palette.set_view_mode(ToolViewMode.DETAIL)
                    print("Switched to Detail view")
                elif event.key == pygame.K_s:
                    # Toggle search
                    query = "new" if not tool_palette.search_query else ""
                    tool_palette.set_search_query(query)
                    print(f"Search set to: '{query}'")
                elif event.key == pygame.K_t:
                    # Toggle theme
                    if current_theme == "dark":
                        # Switch to light theme with proper hover colors
                        light_colors = {
                            'dark_bg': pygame.Color(240, 240, 240),
                            'tool_bg': pygame.Color(255, 255, 255),
                            'section_bg': pygame.Color(230, 230, 230),
                            'normal_text': pygame.Color(0, 0, 0),
                            'tool_text': pygame.Color(0, 0, 0),
                            'section_text': pygame.Color(50, 50, 50),
                            'secondary_text': pygame.Color(100, 100, 100),
                            'tool_border': pygame.Color(180, 180, 180),
                            'normal_border': pygame.Color(200, 200, 200),
                            # Fixed hover colors for light theme
                            'hovered_bg': pygame.Color(230, 240, 255),  # Light blue hover
                            'hovered_text': pygame.Color(0, 0, 0),  # Keep text dark
                            'selected_bg': pygame.Color(180, 210, 255),  # Darker blue for selection
                            'focused_border': pygame.Color(100, 150, 255),
                            # Toolbar colors for light theme
                            'toolbar_bg': pygame.Color(220, 220, 220),
                            'toolbar_button_bg': pygame.Color(240, 240, 240),
                            'toolbar_button_text': pygame.Color(0, 0, 0),
                            'toolbar_button_active': pygame.Color(180, 210, 255),
                            # Search colors for light theme
                            'search_bg': pygame.Color(250, 250, 250),
                            'search_text': pygame.Color(0, 0, 0),
                            'search_placeholder': pygame.Color(120, 120, 120),
                            'search_border': pygame.Color(180, 180, 180),
                        }
                        tool_palette.apply_color_scheme(light_colors)
                        current_theme = "light"
                        print("Switched to light theme")
                    else:
                        # Reset to dark theme
                        tool_palette.theme_manager.update_theme_data()
                        tool_palette.rebuild_image()
                        current_theme = "dark"
                        print("Switched to dark theme")
                elif event.key == pygame.K_f:
                    # Toggle favorite for selected tool
                    if tool_palette.selected_tool:
                        tool_palette.toggle_favorite(tool_palette.selected_tool)
                elif event.key == pygame.K_u:
                    # Toggle usage statistics
                    tool_palette.config.behavior.show_usage_stats = not tool_palette.config.behavior.show_usage_stats
                    tool_palette.rebuild_image()
                    print(f"Usage statistics: {'on' if tool_palette.config.behavior.show_usage_stats else 'off'}")
                elif event.key == pygame.K_a:
                    # Toggle animations
                    tool_palette.config.behavior.animate_hover_effects = not tool_palette.config.behavior.animate_hover_effects
                    print(f"Animations: {'on' if tool_palette.config.behavior.animate_hover_effects else 'off'}")
                elif event.key == pygame.K_r:
                    # Reset view
                    tool_palette.set_view_mode(ToolViewMode.GRID)
                    tool_palette.set_search_query("")
                    tool_palette.scroll_y = 0
                    tool_palette.rebuild_ui()
                    tool_palette.rebuild_image()
                    print("View reset")
                elif event.key == pygame.K_i:
                    # Toggle debug info display
                    show_debug_info = not show_debug_info
                    print(f"Debug info: {'on' if show_debug_info else 'off'}")

            # Handle custom events
            elif event.type == UI_TOOL_SELECTED:
                if event.tool:
                    print(f"Tool selected: {event.tool.name} (used {event.tool.use_count} times)")

            elif event.type == UI_TOOL_DOUBLE_CLICKED:
                if event.tool:
                    print(f"Tool executed: {event.tool.name}")

            elif event.type == UI_TOOL_RIGHT_CLICKED:
                if event.tool:
                    print(f"Right-clicked tool: {event.tool.name}")

            elif event.type == UI_TOOL_FAVORITED:
                print(f"Tool favorited: {event.tool.name} (total favorites: {event.favorites_count})")

            elif event.type == UI_TOOL_UNFAVORITED:
                print(f"Tool unfavorited: {event.tool.name} (total favorites: {event.favorites_count})")

            elif event.type == UI_TOOL_GROUP_EXPANDED:
                print(f"Group expanded: {event.group.name}")

            elif event.type == UI_TOOL_GROUP_COLLAPSED:
                print(f"Group collapsed: {event.group.name}")

            elif event.type == UI_TOOL_VIEW_MODE_CHANGED:
                print(f"View mode changed: {event.previous_mode.value} -> {event.view_mode.value}")

            elif event.type == UI_TOOL_SEARCH_CHANGED:
                print(
                    f"Search changed: '{event.previous_query}' -> '{event.search_query}' ({event.results_count} results)")

            # Pass to manager and tool palette
            manager.process_events(event)

        # Update with timing
        manager.update(time_delta)
        tool_palette.update(time_delta)

        # Draw interface
        screen.fill((35, 35, 35))

        # info display
        font = pygame.font.Font(None, 28)
        info_text = font.render("Tool Palette Demo", True, pygame.Color(255, 255, 255))
        screen.blit(info_text, (550, 50))

        # status information
        info_font = pygame.font.Font(None, 18)
        y_offset = 100

        # Get debug info
        debug_info = tool_palette.get_debug_info()

        info_lines = [
            f"Theme: {current_theme.title()}",
            f"View Mode: {debug_info['view_mode'].title()}",
            f"Search: '{debug_info['search_query']}'" if debug_info['search_query'] else "Search: (none)",
            f"Tools: {debug_info['visible_tools']}/{debug_info['total_tools']} visible",
            f"Groups: {debug_info['visible_groups']}/{debug_info['total_groups']} visible",
            f"Favorites: {debug_info['favorites']}",
            f"Selected: {debug_info['selected_tool'] or '(none)'}",
            f"Scroll: {debug_info['scroll_position']}",
            f"Animations: {'on' if tool_palette.config.behavior.animate_hover_effects else 'off'}",
            f"Usage Stats: {'on' if tool_palette.config.behavior.show_usage_stats else 'off'}",
            "",
            "Hotkeys:",
            "G/L/D - View modes",
            "S - Toggle search",
            "T - Toggle theme",
            "F - Toggle favorite",
            "U - Toggle usage stats",
            "A - Toggle animations",
            "R - Reset view",
            "I - Toggle debug info",
        ]

        for i, line in enumerate(info_lines):
            color = pygame.Color(255, 255, 255) if not line.startswith(" ") else pygame.Color(200, 200, 200)
            text = info_font.render(line, True, color)
            screen.blit(text, (550, y_offset + i * 22))

        # Show debug info if enabled
        if show_debug_info:
            debug_y = y_offset + len(info_lines) * 22 + 20
            debug_font = pygame.font.Font(None, 16)

            debug_text = debug_font.render("DEBUG INFO", True, pygame.Color(255, 255, 0))
            screen.blit(debug_text, (550, debug_y))
            debug_y += 25

            for key, value in debug_info.items():
                if key not in ['view_mode', 'search_query', 'visible_tools', 'total_tools',
                               'visible_groups', 'total_groups', 'favorites', 'selected_tool']:
                    debug_line = f"{key}: {value}"
                    debug_text = debug_font.render(debug_line, True, pygame.Color(200, 200, 200))
                    screen.blit(debug_text, (550, debug_y))
                    debug_y += 18

        # Draw the tool palette
        # tool_palette.draw(screen)
        manager.draw_ui(screen)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()