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


@dataclass
class ToolPaletteBehaviorConfig:
    """Behavior configuration"""
    show_descriptions: bool = True
    show_shortcuts: bool = True
    show_tooltips: bool = True
    show_categories: bool = True
    show_favorites_section: bool = True
    search_in_descriptions: bool = True
    group_by_category: bool = True
    track_usage_statistics: bool = True
    auto_expand_on_search: bool = True


@dataclass
class ToolPaletteConfig:
    """Complete configuration for tool palette panel"""
    layout: ToolPaletteLayoutConfig = field(default_factory=ToolPaletteLayoutConfig)
    behavior: ToolPaletteBehaviorConfig = field(default_factory=ToolPaletteBehaviorConfig)
    default_view_mode: ToolViewMode = ToolViewMode.GRID


class ToolThemeManager:
    """Theme manager following property panel pattern"""

    def __init__(self, ui_manager: pygame_gui.UIManager, element_ids: List[str]):
        self.ui_manager = ui_manager
        self.element_ids = element_ids
        self.themed_colors = {}
        self.themed_font = None
        self._update_theme_data()

    def _update_theme_data(self):
        """Update theme-dependent data with comprehensive fallbacks"""
        color_mappings = {
            'dark_bg': pygame.Color(45, 45, 45),
            'normal_text': pygame.Color(255, 255, 255),
            'secondary_text': pygame.Color(180, 180, 180),
            'section_bg': pygame.Color(35, 35, 35),
            'section_text': pygame.Color(200, 200, 200),
            'tool_bg': pygame.Color(60, 60, 60),
            'tool_text': pygame.Color(255, 255, 255),
            'tool_border': pygame.Color(100, 100, 100),
            'focused_bg': pygame.Color(50, 80, 120),
            'focused_border': pygame.Color(120, 160, 255),
            'hovered_bg': pygame.Color(50, 50, 50),
            'selected_bg': pygame.Color(70, 130, 180),
            'disabled_bg': pygame.Color(40, 40, 40),
            'disabled_text': pygame.Color(120, 120, 120),
            'favorite_star': pygame.Color(255, 215, 0),
            'normal_border': pygame.Color(80, 80, 80),
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
                    self.themed_font = pygame.font.SysFont('Arial', 12)
                except:
                    self.themed_font = pygame.font.Font(None, 12)

        except Exception as e:
            if TOOL_DEBUG:
                print(f"Error getting theme data: {e}")
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

    def get_font(self):
        """Get the themed font"""
        return self.themed_font


class ToolRenderer:
    """Base tool renderer following property panel renderer pattern"""

    def __init__(self, tool: Tool, config: ToolPaletteConfig):
        self.tool = tool
        self.config = config
        self.is_selected = False
        self.is_focused = False
        self.is_hovered = False
        self.rect = pygame.Rect(0, 0, 0, 0)

    def set_geometry(self, rect: pygame.Rect):
        """Set the geometry for this tool renderer"""
        self.rect = rect

    def draw(self, surface: pygame.Surface, theme_manager: ToolThemeManager):
        """Draw the tool renderer"""
        self._draw_background(surface, theme_manager)
        self._draw_content(surface, theme_manager)
        self._draw_favorite_indicator(surface, theme_manager)

    def _draw_background(self, surface: pygame.Surface, theme_manager: ToolThemeManager):
        """Draw background highlighting"""
        if not self.tool.enabled:
            bg_color = theme_manager.get_color('disabled_bg')
        elif self.is_selected:
            bg_color = theme_manager.get_color('selected_bg')
        elif self.is_hovered:
            bg_color = theme_manager.get_color('hovered_bg')
        else:
            bg_color = theme_manager.get_color('tool_bg')

        pygame.draw.rect(surface, bg_color, self.rect,
                         border_radius=self.config.layout.corner_radius)

        # Border
        border_color = theme_manager.get_color('focused_border' if self.is_focused else 'tool_border')
        pygame.draw.rect(surface, border_color, self.rect,
                         self.config.layout.border_width,
                         border_radius=self.config.layout.corner_radius)

    def _draw_content(self, surface: pygame.Surface, theme_manager: ToolThemeManager):
        """Draw tool content - override in subclasses"""
        pass

    def _draw_favorite_indicator(self, surface: pygame.Surface, theme_manager: ToolThemeManager):
        """Draw favorite star indicator"""
        if self.tool.is_favorite and self.config.behavior.show_favorites_section:
            star_color = theme_manager.get_color('favorite_star')
            star_x = self.rect.right - self.config.layout.favorite_star_offset[0]
            star_y = self.rect.y + self.config.layout.favorite_star_offset[1]
            star_size = self.config.layout.favorite_star_size

            # Simple star (circle for now)
            pygame.draw.circle(surface, star_color, (star_x, star_y), star_size // 3)

    def handle_event(self, event: pygame.event.Event, relative_pos: Tuple[int, int]) -> bool:
        """Handle input events"""
        return False


class GridToolRenderer(ToolRenderer):
    """Grid view tool renderer"""

    def _draw_content(self, surface: pygame.Surface, theme_manager: ToolThemeManager):
        layout = self.config.layout

        # Icon area
        icon_size = layout.grid_icon_size
        icon_rect = pygame.Rect(
            self.rect.centerx - icon_size[0] // 2,
            self.rect.y + layout.grid_padding,
            icon_size[0],
            icon_size[1]
        )

        # Draw icon placeholder
        icon_color = theme_manager.get_color('tool_text' if self.tool.enabled else 'disabled_text')
        pygame.draw.rect(surface, icon_color, icon_rect, 1)

        # Tool name
        name_y = icon_rect.bottom + layout.grid_padding
        text_color = theme_manager.get_color('tool_text' if self.tool.enabled else 'disabled_text')

        try:
            font = theme_manager.get_font()
            if hasattr(font, 'render_premul'):
                text_surface = font.render_premul(self.tool.name, text_color)
            else:
                text_surface = font.render(self.tool.name, True, text_color)

            text_x = self.rect.x + (self.rect.width - text_surface.get_width()) // 2
            text_y = name_y + (self.rect.bottom - name_y - text_surface.get_height()) // 2
            surface.blit(text_surface, (text_x, text_y))
        except Exception:
            pass


class ListToolRenderer(ToolRenderer):
    """List view tool renderer"""

    def _draw_content(self, surface: pygame.Surface, theme_manager: ToolThemeManager):
        layout = self.config.layout

        # Icon
        icon_size = layout.list_icon_size
        icon_rect = pygame.Rect(
            self.rect.x + layout.list_text_padding,
            self.rect.y + (self.rect.height - icon_size) // 2,
            icon_size,
            icon_size
        )

        # Draw icon placeholder
        icon_color = theme_manager.get_color('tool_text' if self.tool.enabled else 'disabled_text')
        pygame.draw.rect(surface, icon_color, icon_rect, 1)

        # Tool name
        name_x = icon_rect.right + layout.list_text_padding
        text_color = theme_manager.get_color('tool_text' if self.tool.enabled else 'disabled_text')

        try:
            font = theme_manager.get_font()
            if hasattr(font, 'render_premul'):
                text_surface = font.render_premul(self.tool.name, text_color)
            else:
                text_surface = font.render(self.tool.name, True, text_color)

            text_y = self.rect.y + (self.rect.height - text_surface.get_height()) // 2
            surface.blit(text_surface, (name_x, text_y))

            # Shortcut (right aligned)
            if self.tool.shortcut and self.config.behavior.show_shortcuts:
                shortcut_color = theme_manager.get_color('secondary_text')
                if hasattr(font, 'render_premul'):
                    shortcut_surface = font.render_premul(self.tool.shortcut, shortcut_color)
                else:
                    shortcut_surface = font.render(self.tool.shortcut, True, shortcut_color)

                shortcut_x = self.rect.right - layout.list_text_padding - shortcut_surface.get_width()
                surface.blit(shortcut_surface, (shortcut_x, text_y))
        except Exception:
            pass


class DetailToolRenderer(ToolRenderer):
    """Detail view tool renderer"""

    def _draw_content(self, surface: pygame.Surface, theme_manager: ToolThemeManager):
        layout = self.config.layout

        # Icon
        icon_size = layout.detail_icon_size
        icon_rect = pygame.Rect(
            self.rect.x + layout.list_text_padding,
            self.rect.y + layout.list_text_padding,
            icon_size,
            icon_size
        )

        # Draw icon placeholder
        icon_color = theme_manager.get_color('tool_text' if self.tool.enabled else 'disabled_text')
        pygame.draw.rect(surface, icon_color, icon_rect, 1)

        # Text area
        text_x = icon_rect.right + layout.list_text_padding
        text_color = theme_manager.get_color('tool_text' if self.tool.enabled else 'disabled_text')

        try:
            font = theme_manager.get_font()

            # Tool name
            if hasattr(font, 'render_premul'):
                name_surface = font.render_premul(self.tool.name, text_color)
            else:
                name_surface = font.render(self.tool.name, True, text_color)

            name_y = self.rect.y + layout.list_text_padding
            surface.blit(name_surface, (text_x, name_y))

            # Tool description
            if self.tool.description and self.config.behavior.show_descriptions:
                desc_color = theme_manager.get_color('secondary_text')
                desc_y = name_y + name_surface.get_height() + 2

                # Truncate description if too long
                max_desc_length = 60
                display_desc = self.tool.description[:max_desc_length]
                if len(self.tool.description) > max_desc_length:
                    display_desc += "..."

                if hasattr(font, 'render_premul'):
                    desc_surface = font.render_premul(display_desc, desc_color)
                else:
                    desc_surface = font.render(display_desc, True, desc_color)

                surface.blit(desc_surface, (text_x, desc_y))

            # Shortcut (bottom right)
            if self.tool.shortcut and self.config.behavior.show_shortcuts:
                shortcut_color = theme_manager.get_color('secondary_text')
                if hasattr(font, 'render_premul'):
                    shortcut_surface = font.render_premul(self.tool.shortcut, shortcut_color)
                else:
                    shortcut_surface = font.render(self.tool.shortcut, True, shortcut_color)

                shortcut_x = self.rect.right - layout.list_text_padding - shortcut_surface.get_width()
                shortcut_y = self.rect.bottom - layout.list_text_padding - shortcut_surface.get_height()
                surface.blit(shortcut_surface, (shortcut_x, shortcut_y))
        except Exception:
            pass


class ToolPalettePanel(UIElement):
    """Main tool palette panel widget following property panel architecture"""

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
        """Called when theme data changes"""
        self.theme_manager.rebuild_from_changed_theme_data()
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

    def draw(self, surface: pygame.Surface):
        """Draw the panel image to the screen."""
        surface.blit(self.image, self.rect)

    def _update_visible_items(self):
        """Update visible groups and tools based on search and filters"""
        self.visible_groups = []
        self.visible_tools = []

        # Get all groups sorted by order
        all_groups = sorted(self.tool_groups.values(), key=lambda g: g.order)

        if TOOL_DEBUG:
            print(f"Updating visible items. Total groups: {len(all_groups)}")
            for group in all_groups:
                print(f"  Group {group.name}: {len(group.tools)} tools")

        for group in all_groups:
            group_tools = []

            # Check all tools in this group
            for tool in group.tools:
                if self._should_show_tool(tool):
                    group_tools.append(tool)

            if TOOL_DEBUG:
                print(f"  Group {group.name} visible tools: {[t.name for t in group_tools]}")

            # Only show group if it has visible tools or no search is active
            if group_tools or not self.search_query:
                self.visible_groups.append(group)

                # Only add tools to visible_tools if group is expanded
                if group.expanded:
                    self.visible_tools.extend(group_tools)
                    if TOOL_DEBUG:
                        print(f"    Added {len(group_tools)} tools to visible_tools (group expanded)")
                else:
                    if TOOL_DEBUG:
                        print(f"    Group collapsed, not adding tools to visible_tools")

        if TOOL_DEBUG:
            print(f"Final visible_tools: {[t.name for t in self.visible_tools]}")

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
        self.renderers.clear()  # <- ensure full clear

        for tool in self.visible_tools:  # <- only visible tools
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
                    # Use group.tools directly and filter by visibility, not by visible_tools
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
                    # Use group.tools directly and filter by visibility
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
        """Rebuild the image surface (following property panel pattern)"""
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
        """Draw the toolbar"""
        if self.toolbar_rect.height <= 0:
            return

        try:
            toolbar_surface = self.image.subsurface(self.toolbar_rect)
        except (ValueError, pygame.error):
            return

        # Background
        bg_color = self.theme_manager.get_color('section_bg')
        toolbar_surface.fill(bg_color)

        # View mode buttons
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
        """Draw a toolbar button"""
        bg_color = self.theme_manager.get_color('selected_bg' if active else 'tool_bg')
        pygame.draw.rect(surface, bg_color, rect, border_radius=self.config.layout.corner_radius)

        # Border
        border_color = self.theme_manager.get_color('tool_border')
        pygame.draw.rect(surface, border_color, rect, self.config.layout.border_width,
                         border_radius=self.config.layout.corner_radius)

        # Text
        try:
            font = self.theme_manager.get_font()
            text_color = self.theme_manager.get_color('normal_text')

            if hasattr(font, 'render_premul'):
                text_surface = font.render_premul(text, text_color)
            else:
                text_surface = font.render(text, True, text_color)

            text_rect = text_surface.get_rect(center=rect.center)
            surface.blit(text_surface, text_rect)
        except Exception:
            pass

    def _draw_search_bar(self):
        """Draw the search bar"""
        if self.search_rect.height <= 0:
            return

        try:
            search_surface = self.image.subsurface(self.search_rect)
        except (ValueError, pygame.error):
            return

        # Background
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

        # Input background
        input_bg_color = self.theme_manager.get_color('tool_bg')
        pygame.draw.rect(search_surface, input_bg_color, input_rect,
                         border_radius=self.config.layout.corner_radius)

        # Input border
        border_color = self.theme_manager.get_color('tool_border')
        pygame.draw.rect(search_surface, border_color, input_rect,
                         self.config.layout.border_width,
                         border_radius=self.config.layout.corner_radius)

        # Search text
        display_text = self.search_query if self.search_query else "Search tools..."
        text_color = self.theme_manager.get_color('normal_text' if self.search_query else 'secondary_text')

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
        except Exception:
            pass

    def _draw_content(self):
        """Draw the content area - SAFE version that doesn't modify stored rects"""
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
                # Create display rect WITHOUT modifying stored rect
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
            # Create display rect WITHOUT modifying stored rect
            display_rect = pygame.Rect(
                renderer.rect.x,
                renderer.rect.y - self.scroll_y,
                renderer.rect.width,
                renderer.rect.height
            )

            # Only draw if visible
            if display_rect.bottom >= 0 and display_rect.y < content_surface.get_height():
                # Draw tool safely without modifying renderer.rect
                self._draw_tool_at_position(content_surface, renderer, display_rect)

    def _draw_tool_at_position(self, surface: pygame.Surface, renderer: ToolRenderer, display_rect: pygame.Rect):
        """Draw a tool at a specific display position without modifying the renderer's stored rect"""
        # Check if tool is visible at all
        if display_rect.bottom < 0 or display_rect.y >= surface.get_height():
            return

        # Calculate visible portion
        visible_rect = display_rect.clip(pygame.Rect(0, 0, surface.get_width(), surface.get_height()))

        if visible_rect.width > 0 and visible_rect.height > 0:
            try:
                # Create subsurface for the visible portion
                tool_surface = surface.subsurface(visible_rect)

                # Create a temporary renderer with the display position
                # Save original state
                original_rect = renderer.rect

                # Set temporary rect for drawing (relative to the subsurface)
                renderer.rect = pygame.Rect(
                    display_rect.x - visible_rect.x,  # Offset within subsurface
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
        """Draw group header (following property panel section header pattern)"""
        if rect.bottom < 0 or rect.y >= surface.get_height():
            return

        visible_rect = rect.clip(pygame.Rect(0, 0, surface.get_width(), surface.get_height()))
        if visible_rect.width <= 0 or visible_rect.height <= 0:
            return

        # Background
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
        """Draw group header content (following property panel pattern)"""
        layout = self.config.layout

        # Expand/collapse triangle (same as property panel)
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

        # Group name
        text_x = triangle_x + triangle_size * 3 + layout.group_text_padding
        text_color = self.theme_manager.get_color('section_text')

        try:
            font = self.theme_manager.get_font()
            if hasattr(font, 'render_premul'):
                text_surface = font.render_premul(group.name, text_color)
            else:
                text_surface = font.render(group.name, True, text_color)

            text_y = rect.y + (rect.height - text_surface.get_height()) // 2
            surface.blit(text_surface, (text_x, text_y))
        except Exception:
            pass

    def _draw_tool_clipped(self, surface: pygame.Surface, renderer: ToolRenderer):
        """Draw a tool with proper clipping - SIMPLIFIED"""
        tool_rect = renderer.rect

        # Check if tool is visible at all
        if tool_rect.bottom < 0 or tool_rect.y >= surface.get_height():
            return

        # Calculate visible portion
        visible_rect = tool_rect.clip(pygame.Rect(0, 0, surface.get_width(), surface.get_height()))

        if visible_rect.width > 0 and visible_rect.height > 0:
            try:
                # Create subsurface for the visible portion
                tool_surface = surface.subsurface(visible_rect)

                # Adjust renderer rect to draw within the subsurface
                draw_rect = pygame.Rect(
                    visible_rect.x - tool_rect.x,  # Offset within the tool
                    visible_rect.y - tool_rect.y,
                    visible_rect.width,
                    visible_rect.height
                )

                # Temporarily adjust renderer geometry
                old_rect = renderer.rect
                renderer.rect = pygame.Rect(0, 0, tool_rect.width, tool_rect.height)

                # Draw the tool
                renderer.draw(tool_surface, self.theme_manager)

                # Restore geometry
                renderer.rect = old_rect

            except (ValueError, pygame.error) as e:
                if TOOL_DEBUG:
                    print(f"Error drawing tool {renderer.tool.id}: {e}")
                # Fallback: draw directly on surface
                renderer.draw(surface, self.theme_manager)

    def process_event(self, event: pygame.event.Event) -> bool:
        """Process pygame events (following property panel pattern)"""
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
        """Handle left mouse click (following property panel pattern)"""
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

                # Send event
                event_type = UI_TOOL_GROUP_EXPANDED if group.expanded else UI_TOOL_GROUP_COLLAPSED
                event_data = {'ui_element': self, 'group_id': group_id, 'group': group}
                pygame.event.post(pygame.event.Event(event_type, event_data))
                return True

            # Check tool clicks
            tool_id = self._get_tool_at_position(pos)
            if tool_id:
                # Check for double click
                is_double_click = (tool_id == self.last_clicked_tool and
                                   current_time - self.last_click_time < 500)

                self.last_clicked_tool = tool_id
                self.last_click_time = current_time

                if is_double_click:
                    # Double click event
                    tool = self.tools.get(tool_id)
                    event_data = {'ui_element': self, 'tool_id': tool_id, 'tool': tool}
                    pygame.event.post(pygame.event.Event(UI_TOOL_DOUBLE_CLICKED, event_data))

                    # Execute tool callback
                    if tool and tool.callback and tool.enabled:
                        try:
                            tool.callback()
                        except Exception as e:
                            if TOOL_DEBUG:
                                print(f"Error executing tool callback: {e}")
                else:
                    # Single click - select tool
                    self.select_tool(tool_id)

                return True

        return False

    def _handle_right_click(self, pos: Tuple[int, int]) -> bool:
        """Handle right mouse click"""
        if self.content_rect.collidepoint(pos):
            tool_id = self._get_tool_at_position(pos)
            if tool_id:
                tool = self.tools.get(tool_id)
                event_data = {'ui_element': self, 'tool_id': tool_id, 'tool': tool, 'mouse_pos': pos}
                pygame.event.post(pygame.event.Event(UI_TOOL_RIGHT_CLICKED, event_data))
                return True
        return False

    def _handle_mouse_motion(self, pos: Tuple[int, int]) -> bool:
        """Handle mouse motion / coordinate handling"""
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
        """Handle scroll wheel"""
        old_scroll = self.scroll_y
        self.scroll_y = max(0, min(self.max_scroll, self.scroll_y - delta * 20))

        if old_scroll != self.scroll_y:
            self.rebuild_ui()
            self.rebuild_image()
            return True

        return False

    def _handle_key_event(self, event: pygame.event.Event) -> bool:
        """Handle keyboard events"""
        # TODO: Implement keyboard navigation
        return False

    def _handle_toolbar_click(self, pos: Tuple[int, int]) -> bool:
        """Handle toolbar button clicks"""
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
        """Get group ID of header at position"""
        if not self.config.behavior.show_categories:
            return None

        # pos is already relative to the panel, we need to make it relative to content area
        if not self.content_rect.collidepoint(pos):
            return None

        # Convert to content-relative coordinates
        content_relative_pos = (pos[0] - self.content_rect.x, pos[1] - self.content_rect.y)

        # Check against stored group rects
        for group_id, stored_rect in self.group_rects.items():
            # Convert stored rect (content space) to display space by applying scroll
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
        """Get tool ID at position"""
        # Convert to content-relative coordinates
        relative_pos = (pos[0] - self.content_rect.x, pos[1] - self.content_rect.y)

        # Check against tool renderer rects
        for tool_id, renderer in self.renderers.items():
            # The renderer.rect is stored in content space (without scroll offset)
            # We need to convert it to display space for collision detection
            display_rect = pygame.Rect(
                renderer.rect.x,
                renderer.rect.y - self.scroll_y,  # Apply scroll offset
                renderer.rect.width,
                renderer.rect.height
            )
            collision = display_rect.collidepoint(relative_pos)

            if collision:
                return tool_id
        return None

    def select_tool(self, tool_id: Optional[str]):
        """Select a tool"""
        if self.selected_tool != tool_id:
            old_selection = self.selected_tool
            self.selected_tool = tool_id

            # Update renderer states
            for renderer in self.renderers.values():
                renderer.is_selected = (renderer.tool.id == tool_id)

            self.rebuild_image()

            # Track usage
            if tool_id and tool_id in self.tools:
                self.tools[tool_id].use_tool()

            # Send event
            event_data = {
                'ui_element': self,
                'tool_id': tool_id,
                'tool': self.tools.get(tool_id) if tool_id else None,
                'previous_selection': old_selection
            }
            pygame.event.post(pygame.event.Event(UI_TOOL_SELECTED, event_data))

    def set_view_mode(self, mode: ToolViewMode):
        """Set the view mode"""
        if self.view_mode != mode:
            self.view_mode = mode
            self.scroll_y = 0  # Reset scroll
            self.rebuild_ui()
            self.rebuild_image()

            # Send event
            event_data = {'ui_element': self, 'view_mode': mode}
            pygame.event.post(pygame.event.Event(UI_TOOL_VIEW_MODE_CHANGED, event_data))

    def set_search_query(self, query: str):
        """Set search query"""
        if self.search_query != query:
            self.search_query = query
            self.scroll_y = 0  # Reset scroll
            self.rebuild_ui()
            self.rebuild_image()

            # Send event
            event_data = {'ui_element': self, 'search_query': query}
            pygame.event.post(pygame.event.Event(UI_TOOL_SEARCH_CHANGED, event_data))

    # Public API methods (following property panel pattern)
    def add_group(self, group: ToolGroup):
        """Add a tool group"""
        self.tool_groups[group.id] = group
        for tool in group.tools:
            self.tools[tool.id] = tool
            if tool.is_favorite:
                self.favorites.add(tool.id)
        self.rebuild_ui()
        self.rebuild_image()

    def add_tool(self, tool: Tool, group_id: str = "default"):
        """Add a tool to a group"""
        if group_id not in self.tool_groups:
            self.tool_groups[group_id] = ToolGroup(
                id=group_id,
                name=group_id.replace("_", " ").title()
            )

        self.tool_groups[group_id].add_tool(tool)
        self.tools[tool.id] = tool

        if tool.is_favorite:
            self.favorites.add(tool.id)

        self.rebuild_ui()
        self.rebuild_image()

    def remove_tool(self, tool_id: str) -> bool:
        """Remove a tool"""
        if tool_id in self.tools:
            # Remove from all groups
            for group in self.tool_groups.values():
                group.remove_tool(tool_id)

            # Remove from main dict and favorites
            del self.tools[tool_id]
            self.favorites.discard(tool_id)

            # Clear selection if this tool was selected
            if self.selected_tool == tool_id:
                self.selected_tool = None

            self.rebuild_ui()
            self.rebuild_image()
            return True
        return False

    def toggle_favorite(self, tool_id: str):
        """Toggle favorite status of a tool"""
        if tool_id in self.tools:
            tool = self.tools[tool_id]
            tool.is_favorite = not tool.is_favorite

            if tool.is_favorite:
                self.favorites.add(tool_id)
            else:
                self.favorites.discard(tool_id)

            self.rebuild_image()

            # Send event
            event_type = UI_TOOL_FAVORITED if tool.is_favorite else UI_TOOL_UNFAVORITED
            event_data = {'ui_element': self, 'tool_id': tool_id, 'tool': tool}
            pygame.event.post(pygame.event.Event(event_type, event_data))

    def update(self, time_delta: float):
        """Update the panel"""
        super().update(time_delta)


# Default theme
TOOL_PALETTE_THEME = {
    "tool_palette_panel": {
        "colours": {
            "dark_bg": "#2d2d2d",
            "normal_text": "#ffffff",
            "secondary_text": "#b4b4b4",
            "section_bg": "#232323",
            "section_text": "#c8c8c8",
            "tool_bg": "#3c3c3c",
            "tool_text": "#ffffff",
            "tool_border": "#646464",
            "focused_bg": "#325078",
            "focused_border": "#78a0ff",
            "hovered_bg": "#323232",
            "selected_bg": "#4682b4",
            "disabled_bg": "#1e1e1e",
            "disabled_text": "#969696",
            "favorite_star": "#ffd700",
            "normal_border": "#505050"
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

    # Creation Tools
    creation_group = ToolGroup("creation", "Creation Tools", "Tools for creating new content")
    creation_group.add_tool(Tool("new_file", "New File", "Create a new file", ToolType.CREATION, "File", shortcut="Ctrl+N"))
    creation_group.add_tool(Tool("new_folder", "New Folder", "Create a new folder", ToolType.CREATION, "File", shortcut="Ctrl+Shift+N"))
    creation_group.add_tool(Tool("new_project", "New Project", "Create a new project", ToolType.CREATION, "Project"))
    creation_group.add_tool(Tool("add_sprite", "Add Sprite", "Add a sprite to the scene", ToolType.CREATION, "Game", is_favorite=True))
    groups.append(creation_group)

    # Edit Tools - ADD MISSING TOOLS
    edit_group = ToolGroup("modification", "Edit Tools", "Tools for modifying content")
    edit_group.add_tool(Tool("cut", "Cut", "Cut selected items", ToolType.MODIFICATION, "Edit", shortcut="Ctrl+X"))
    edit_group.add_tool(Tool("copy", "Copy", "Copy selected items", ToolType.MODIFICATION, "Edit", shortcut="Ctrl+C"))
    edit_group.add_tool(Tool("paste", "Paste", "Paste from clipboard", ToolType.MODIFICATION, "Edit", shortcut="Ctrl+V"))
    edit_group.add_tool(Tool("delete", "Delete", "Delete selected items", ToolType.MODIFICATION, "Edit", shortcut="Delete"))  # MISSING
    edit_group.add_tool(Tool("undo", "Undo", "Undo last action", ToolType.MODIFICATION, "Edit", shortcut="Ctrl+Z", is_favorite=True))
    edit_group.add_tool(Tool("redo", "Redo", "Redo last undone action", ToolType.MODIFICATION, "Edit", shortcut="Ctrl+Y"))  # MISSING
    groups.append(edit_group)

    # Navigation Tools - ADD MISSING TOOL
    nav_group = ToolGroup("navigation", "Navigation", "Tools for navigation")
    nav_group.add_tool(Tool("zoom_in", "Zoom In", "Zoom in on content", ToolType.NAVIGATION, "View", shortcut="Ctrl++"))
    nav_group.add_tool(Tool("zoom_out", "Zoom Out", "Zoom out from content", ToolType.NAVIGATION, "View", shortcut="Ctrl+-"))
    nav_group.add_tool(Tool("fit_view", "Fit to View", "Fit content to view", ToolType.NAVIGATION, "View", shortcut="Ctrl+0"))  # MISSING
    nav_group.add_tool(Tool("pan_tool", "Pan Tool", "Pan around content", ToolType.NAVIGATION, "View", shortcut="Space"))
    groups.append(nav_group)

    return groups


def main():
    """Example demonstration with debugging"""
    pygame.init()
    screen = pygame.display.set_mode((1200, 800))
    pygame.display.set_caption("Tool Palette Panel Demo")
    clock = pygame.time.Clock()

    # Create manager with theme
    manager = pygame_gui.UIManager((1200, 800), TOOL_PALETTE_THEME)

    # Create tool palette
    tool_palette = ToolPalettePanel(
        pygame.Rect(50, 50, 400, 600),
        manager,
        ToolPaletteConfig(),
        object_id=ObjectID(object_id='#main_palette', class_id='@tool_palette')
    )

    # Add sample tools
    sample_groups = create_sample_tools()
    print(f"Created {len(sample_groups)} sample groups:")
    for group in sample_groups:
        print(f"  {group.name}: {[tool.name for tool in group.tools]}")
        tool_palette.add_group(group)

    print(f"\nAfter adding groups:")
    print(f"  Total tools in palette: {len(tool_palette.tools)}")
    print(f"  Tool IDs: {list(tool_palette.tools.keys())}")
    print(f"  Visible tools: {[t.name for t in tool_palette.visible_tools]}")

    print("\nTool Palette Panel Demo")
    print("Controls:")
    print("- Press 'G/L/D' to change view mode")
    print("- Press 'S' to toggle search")
    print("- Click group headers to expand/collapse")

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

            # Handle custom events
            elif event.type == UI_TOOL_SELECTED:
                if event.tool:
                    print(f"Tool selected: {event.tool.name}")

            elif event.type == UI_TOOL_DOUBLE_CLICKED:
                if event.tool:
                    print(f"Tool executed: {event.tool.name}")

            elif event.type == UI_TOOL_GROUP_EXPANDED:
                print(f"Group expanded: {event.group.name}")

            elif event.type == UI_TOOL_GROUP_COLLAPSED:
                print(f"Group collapsed: {event.group.name}")

            # Pass to manager and tool palette
            manager.process_events(event)
            # tool_palette.process_event(event)

        manager.update(time_delta)

        # Draw
        screen.fill((30, 30, 30))

        # Info
        font = pygame.font.Font(None, 24)
        info_text = font.render("Tool Palette Demo", True, pygame.Color(255, 255, 255))
        screen.blit(info_text, (500, 50))

        info_font = pygame.font.Font(None, 18)
        y_offset = 100

        info_lines = [
            f"View Mode: {tool_palette.view_mode.value.title()}",
            f"Search: '{tool_palette.search_query}'" if tool_palette.search_query else "Search: (none)",
            f"Tools: {len(tool_palette.visible_tools)} visible / {len(tool_palette.tools)} total",
            f"Groups: {len(tool_palette.tool_groups)}",
            f"Selected: {tool_palette.selected_tool or '(none)'}",
            f"Renderers: {len(tool_palette.renderers)}",
            "",
            "Press G/L/D for view modes",
            "Press S to toggle search",
            "Click headers to expand/collapse",
        ]

        for i, line in enumerate(info_lines):
            color = pygame.Color(200, 200, 200)
            text = info_font.render(line, True, color)
            screen.blit(text, (500, y_offset + i * 20))

        tool_palette.draw(screen)  # draw first
        manager.draw_ui(screen)  # draw UIManager elements on top
        pygame.display.flip()
    pygame.quit()


if __name__ == "__main__":
    main()