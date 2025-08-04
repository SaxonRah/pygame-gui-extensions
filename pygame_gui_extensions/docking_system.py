# docking_system.py
import pygame
import pygame_gui
from pygame_gui.core import UIElement, ObjectID
from pygame_gui.core.interfaces import IContainerLikeInterface
from typing import List, Optional, Dict, Any, Union, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
import copy

# Custom events for docking system
UI_DOCK_PANEL_ADDED = pygame.USEREVENT + 200
UI_DOCK_PANEL_REMOVED = pygame.USEREVENT + 201
UI_DOCK_TAB_SELECTED = pygame.USEREVENT + 202
UI_DOCK_LAYOUT_CHANGED = pygame.USEREVENT + 203
UI_DOCK_SPLITTER_MOVED = pygame.USEREVENT + 204

DOCK_DEBUG = False


class DockDirection(Enum):
    """Docking directions"""
    LEFT = "left"
    RIGHT = "right"
    TOP = "top"
    BOTTOM = "bottom"
    CENTER = "center"  # For tabbed groups


class DockZoneType(Enum):
    """Types of dock zones"""
    CONTAINER = "container"  # Holds a single panel or tab group
    SPLITTER = "splitter"  # Splits space between zones
    ROOT = "root"  # Root container


@dataclass
class DockingLayoutConfig:
    """Layout configuration for docking system"""
    # Tab configuration
    tab_height: int = 30
    tab_min_width: int = 100
    tab_max_width: int = 200
    tab_close_button_size: int = 16
    tab_close_button_margin: int = 4

    # Splitter configuration
    splitter_size: int = 4
    splitter_hover_size: int = 8
    splitter_min_panel_size: int = 100

    # Drop zone configuration
    drop_zone_size: int = 40
    drop_zone_margin: int = 20
    drop_indicator_thickness: int = 3

    # Panel configuration
    panel_header_height: int = 25
    panel_border_width: int = 1
    panel_minimum_size: Tuple[int, int] = (200, 150)

    # Animation settings
    tab_animation_speed: float = 0.2
    drop_zone_fade_speed: float = 0.3


@dataclass
class DockingBehaviorConfig:
    """Behavior configuration for docking system"""
    allow_tab_reordering: bool = True
    allow_tab_detaching: bool = True
    allow_floating_panels: bool = True
    auto_hide_tabs_single: bool = False
    show_close_buttons: bool = True
    allow_panel_resize: bool = True
    snap_to_edges: bool = True
    snap_distance: int = 10


@dataclass
class DockingConfig:
    """Main configuration for docking system"""
    layout: DockingLayoutConfig = field(default_factory=DockingLayoutConfig)
    behavior: DockingBehaviorConfig = field(default_factory=DockingBehaviorConfig)
    title: str = "Docking System"


class DockingThemeManager:
    """Theme manager for docking system components"""

    def __init__(self, ui_manager: pygame_gui.UIManager, element_ids: List[str]):
        self.ui_manager = ui_manager
        self.element_ids = element_ids
        self.themed_colors = {}
        self.themed_font = None
        self._update_theme_data()

    def _update_theme_data(self):
        """Update theme-dependent data with fallbacks"""
        color_mappings = {
            'background': pygame.Color(40, 40, 40),
            'panel_bg': pygame.Color(50, 50, 50),
            'panel_border': pygame.Color(80, 80, 80),
            'panel_header_bg': pygame.Color(60, 60, 60),
            'panel_header_text': pygame.Color(255, 255, 255),
            'tab_bg': pygame.Color(70, 70, 70),
            'tab_active_bg': pygame.Color(90, 90, 90),
            'tab_hover_bg': pygame.Color(80, 80, 80),
            'tab_text': pygame.Color(255, 255, 255),
            'tab_border': pygame.Color(100, 100, 100),
            'splitter_bg': pygame.Color(60, 60, 60),
            'splitter_hover_bg': pygame.Color(80, 80, 80),
            'splitter_active_bg': pygame.Color(100, 100, 100),
            'drop_zone_valid': pygame.Color(100, 150, 255, 128),
            'drop_zone_invalid': pygame.Color(255, 100, 100, 128),
            'drop_indicator': pygame.Color(120, 160, 255),
            'close_button_bg': pygame.Color(80, 80, 80),
            'close_button_hover_bg': pygame.Color(200, 100, 100),
            'close_button_text': pygame.Color(255, 255, 255),
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
            except Exception:
                pass

            if not self.themed_font:
                try:
                    self.themed_font = pygame.font.SysFont('Arial', 12)
                except:
                    self.themed_font = pygame.font.Font(None, 12)

        except Exception as e:
            if DOCK_DEBUG:
                print(f"Error updating dock theme data: {e}")
            # Set all to defaults
            self.themed_colors = color_mappings.copy()
            self.themed_font = pygame.font.Font(None, 12)

    def get_color(self, color_id: str) -> pygame.Color:
        """Get themed color with fallback"""
        return self.themed_colors.get(color_id, pygame.Color(100, 100, 100))

    def get_font(self, size: int = None) -> pygame.font.Font:
        """Get themed font with optional size override"""
        if size and size != 12:
            try:
                return pygame.font.SysFont('Arial', size)
            except:
                return pygame.font.Font(None, size)
        return self.themed_font

    def rebuild_from_changed_theme_data(self):
        """Rebuild theme data when theme changes"""
        self._update_theme_data()


class DockContainer:
    """Container that wraps a panel for docking functionality"""

    def __init__(self, panel: UIElement, title: str = None, closable: bool = True):
        self.panel = panel
        self.title = title or getattr(panel, 'title', type(panel).__name__)
        self.closable = closable
        self.is_active = False
        self.original_rect = panel.rect.copy()
        self.dock_zone: Optional['DockZone'] = None

        # Store original container for restoration - handle different pygame-gui versions
        self.original_container = getattr(panel, 'container', None)
        if self.original_container is None:
            # Try alternative attribute names
            self.original_container = getattr(panel, 'ui_container', None)

    def set_rect(self, rect: pygame.Rect):
        """Update the panel's rect properly"""
        self.panel.relative_rect = pygame.Rect(0, 0, rect.width, rect.height)
        self.panel.rect = rect.copy()

        # Ensure pygame-gui updates the element
        if hasattr(self.panel, 'set_relative_position'):
            self.panel.set_relative_position((rect.x, rect.y))
        if hasattr(self.panel, 'set_dimensions'):
            self.panel.set_dimensions((rect.width, rect.height))

    def get_rect(self) -> pygame.Rect:
        """Get the panel's current rect"""
        return self.panel.rect

    def restore_original_container(self):
        """Restore panel to its original container"""
        if self.original_container:
            # Handle different pygame-gui versions
            if hasattr(self.panel, 'container'):
                self.panel.container = self.original_container
            elif hasattr(self.panel, 'ui_container'):
                self.panel.ui_container = self.original_container


class TabGroup:
    """Manages a group of tabbed panels"""

    def __init__(self, config: DockingConfig, theme_manager: DockingThemeManager):
        self.config = config
        self.theme_manager = theme_manager
        self.containers: List[DockContainer] = []
        self.active_index = 0
        self.rect = pygame.Rect(0, 0, 200, 200)
        self.tab_rects: List[pygame.Rect] = []
        self.close_button_rects: List[pygame.Rect] = []
        self.hovered_tab = -1
        self.hovered_close_button = -1
        self.dragging_tab = -1
        self.drag_start_pos = (0, 0)
        self.drag_offset = (0, 0)

    def add_container(self, container: DockContainer, index: int = -1):
        """Add a container to the tab group"""
        if index == -1:
            self.containers.append(container)
            index = len(self.containers) - 1
        else:
            self.containers.insert(index, container)

        container.dock_zone = None  # Will be set by the DockZone
        self.active_index = index
        self._update_layout()

    def remove_container(self, container: DockContainer) -> bool:
        """Remove a container from the tab group"""
        if container in self.containers:
            index = self.containers.index(container)
            self.containers.remove(container)

            if self.active_index >= len(self.containers):
                self.active_index = max(0, len(self.containers) - 1)

            self._update_layout()
            return True
        return False

    def get_active_container(self) -> Optional[DockContainer]:
        """Get the currently active container"""
        if 0 <= self.active_index < len(self.containers):
            return self.containers[self.active_index]
        return None

    def set_active_index(self, index: int):
        """Set the active tab index"""
        if 0 <= index < len(self.containers):
            self.active_index = index
            self._update_layout()

    def set_rect(self, rect: pygame.Rect):
        """Update the tab group's rect"""
        old_rect = self.rect
        self.rect = rect

        # Only update layout if the rect actually changed
        if old_rect != rect:
            self._update_layout()

    def _update_layout(self):
        """Update tab and panel layout"""
        if not self.containers:
            return

        # Calculate tab rects
        self.tab_rects.clear()
        self.close_button_rects.clear()

        tab_height = self.config.layout.tab_height
        total_width = self.rect.width
        tab_count = len(self.containers)

        if tab_count == 0:
            return

        # Calculate tab width
        tab_width = min(
            self.config.layout.tab_max_width,
            max(self.config.layout.tab_min_width, total_width // tab_count)
        )

        for i, container in enumerate(self.containers):
            x = self.rect.x + i * tab_width
            tab_rect = pygame.Rect(x, self.rect.y, tab_width, tab_height)
            self.tab_rects.append(tab_rect)

            # Close button rect
            if self.config.behavior.show_close_buttons and container.closable:
                close_size = self.config.layout.tab_close_button_size
                close_margin = self.config.layout.tab_close_button_margin
                close_x = tab_rect.right - close_size - close_margin
                close_y = tab_rect.y + (tab_rect.height - close_size) // 2
                close_rect = pygame.Rect(close_x, close_y, close_size, close_size)
                self.close_button_rects.append(close_rect)
            else:
                self.close_button_rects.append(pygame.Rect(0, 0, 0, 0))

        # Update active panel rect
        active_container = self.get_active_container()
        if active_container:
            panel_rect = pygame.Rect(
                self.rect.x,
                self.rect.y + tab_height,
                self.rect.width,
                self.rect.height - tab_height
            )
            active_container.set_rect(panel_rect)

    def handle_mouse_click(self, pos: Tuple[int, int]) -> Optional[str]:
        """Handle mouse click on tabs"""
        for i, tab_rect in enumerate(self.tab_rects):
            if tab_rect.collidepoint(pos):
                # Check close button first
                if (i < len(self.close_button_rects) and
                        self.close_button_rects[i].collidepoint(pos)):
                    return f"close_tab_{i}"
                else:
                    # Start potential drag
                    if self.config.behavior.allow_tab_reordering:
                        self.dragging_tab = i
                        self.drag_start_pos = pos
                        self.drag_offset = (pos[0] - tab_rect.x, pos[1] - tab_rect.y)

                    self.set_active_index(i)
                    return f"select_tab_{i}"
        return None

    def handle_mouse_motion(self, pos: Tuple[int, int]):
        """Handle mouse motion for hover effects and dragging"""
        self.hovered_tab = -1
        self.hovered_close_button = -1

        # Handle tab dragging
        if self.dragging_tab >= 0:
            # Check if we've moved far enough to start dragging
            drag_distance = ((pos[0] - self.drag_start_pos[0]) ** 2 +
                             (pos[1] - self.drag_start_pos[1]) ** 2) ** 0.5

            if drag_distance > 5:  # Minimum drag distance
                # Check if we should reorder tabs
                for i, tab_rect in enumerate(self.tab_rects):
                    if i != self.dragging_tab and tab_rect.collidepoint(pos):
                        # Reorder tabs
                        self._reorder_tabs(self.dragging_tab, i)
                        self.dragging_tab = i
                        break
            return

        # Normal hover handling
        for i, tab_rect in enumerate(self.tab_rects):
            if tab_rect.collidepoint(pos):
                self.hovered_tab = i
                if (i < len(self.close_button_rects) and
                        self.close_button_rects[i].collidepoint(pos)):
                    self.hovered_close_button = i
                break

    def handle_mouse_up(self) -> bool:
        """Handle mouse up - stop dragging"""
        was_dragging = self.dragging_tab >= 0
        self.dragging_tab = -1
        return was_dragging

    def _reorder_tabs(self, from_index: int, to_index: int):
        """Reorder tabs by moving from_index to to_index"""
        if (0 <= from_index < len(self.containers) and
                0 <= to_index < len(self.containers) and
                from_index != to_index):

            # Move the container
            container = self.containers.pop(from_index)
            self.containers.insert(to_index, container)

            # Update active index
            if self.active_index == from_index:
                self.active_index = to_index
            elif from_index < self.active_index <= to_index:
                self.active_index -= 1
            elif to_index <= self.active_index < from_index:
                self.active_index += 1

            self._update_layout()

    def draw(self, surface: pygame.Surface):
        """Draw the tab group"""
        if not self.containers:
            return

        # Draw tabs
        for i, (container, tab_rect) in enumerate(zip(self.containers, self.tab_rects)):
            is_active = (i == self.active_index)
            is_hovered = (i == self.hovered_tab)

            # Tab background
            if is_active:
                bg_color = self.theme_manager.get_color('tab_active_bg')
            elif is_hovered:
                bg_color = self.theme_manager.get_color('tab_hover_bg')
            else:
                bg_color = self.theme_manager.get_color('tab_bg')

            pygame.draw.rect(surface, bg_color, tab_rect)

            # Tab border
            border_color = self.theme_manager.get_color('tab_border')
            pygame.draw.rect(surface, border_color, tab_rect, 1)

            # Tab text
            font = self.theme_manager.get_font()
            text_color = self.theme_manager.get_color('tab_text')

            # Calculate text rect (account for close button)
            text_rect = tab_rect.copy()
            if i < len(self.close_button_rects) and self.close_button_rects[i].width > 0:
                text_rect.width -= self.close_button_rects[i].width + 4

            # Truncate text if needed
            text = container.title

            # Handle pygame-gui font rendering
            try:
                if hasattr(font, 'render'):
                    # Regular pygame font
                    text_surface = font.render(text, True, text_color)
                elif hasattr(font, 'render_text'):
                    # pygame-gui font interface
                    text_surface = font.render_text(text, text_color)
                else:
                    # Fallback to basic pygame font
                    fallback_font = pygame.font.Font(None, 12)
                    text_surface = fallback_font.render(text, True, text_color)
            except Exception:
                # Ultimate fallback
                fallback_font = pygame.font.Font(None, 12)
                text_surface = fallback_font.render(text, True, text_color)

            # Truncate if text is too wide
            if text_surface.get_width() > text_rect.width - 8:
                # Truncate with ellipsis
                while len(text) > 3:
                    try_text = text[:-1] + "..."
                    try:
                        if hasattr(font, 'render'):
                            test_surface = font.render(try_text, True, text_color)
                        elif hasattr(font, 'render_text'):
                            test_surface = font.render_text(try_text, text_color)
                        else:
                            fallback_font = pygame.font.Font(None, 12)
                            test_surface = fallback_font.render(try_text, True, text_color)
                    except Exception:
                        fallback_font = pygame.font.Font(None, 12)
                        test_surface = fallback_font.render(try_text, True, text_color)

                    if test_surface.get_width() <= text_rect.width - 8:
                        text_surface = test_surface
                        break
                    text = text[:-1]

            # Center text in tab
            text_x = text_rect.x + (text_rect.width - text_surface.get_width()) // 2
            text_y = text_rect.y + (text_rect.height - text_surface.get_height()) // 2
            surface.blit(text_surface, (text_x, text_y))

            # Draw close button
            if (i < len(self.close_button_rects) and
                    self.close_button_rects[i].width > 0 and
                    container.closable):
                close_rect = self.close_button_rects[i]

                # Close button background
                if i == self.hovered_close_button:
                    close_bg = self.theme_manager.get_color('close_button_hover_bg')
                else:
                    close_bg = self.theme_manager.get_color('close_button_bg')

                pygame.draw.rect(surface, close_bg, close_rect)

                # Close button X
                close_color = self.theme_manager.get_color('close_button_text')
                center_x, center_y = close_rect.center
                size = close_rect.width // 3

                # Draw X
                pygame.draw.line(
                    surface, close_color,
                    (center_x - size, center_y - size),
                    (center_x + size, center_y + size), 2
                )
                pygame.draw.line(
                    surface, close_color,
                    (center_x + size, center_y - size),
                    (center_x - size, center_y + size), 2
                )


class Splitter:
    """Handles resizing between dock zones"""

    def __init__(self, orientation: str, config: DockingConfig, theme_manager: DockingThemeManager):
        self.orientation = orientation  # 'horizontal' or 'vertical'
        self.config = config
        self.theme_manager = theme_manager
        self.rect = pygame.Rect(0, 0, 0, 0)
        self.is_hovered = False
        self.is_dragging = False
        self.drag_start_pos = (0, 0)
        self.split_ratio = 0.5  # 0.0 to 1.0

    def set_rect(self, rect: pygame.Rect):
        """Set the splitter's rect"""
        self.rect = rect

    def get_hover_rect(self) -> pygame.Rect:
        """Get the hover detection rect (larger than visual rect)"""
        hover_size = self.config.layout.splitter_hover_size
        if self.orientation == 'horizontal':
            # Horizontal splitter (resizes vertically)
            return pygame.Rect(
                self.rect.x,
                self.rect.y - (hover_size - self.rect.height) // 2,
                self.rect.width,
                hover_size
            )
        else:
            # Vertical splitter (resizes horizontally)
            return pygame.Rect(
                self.rect.x - (hover_size - self.rect.width) // 2,
                self.rect.y,
                hover_size,
                self.rect.height
            )

    def handle_mouse_motion(self, pos: Tuple[int, int]) -> bool:
        """Handle mouse motion, return True if cursor should change"""
        hover_rect = self.get_hover_rect()
        self.is_hovered = hover_rect.collidepoint(pos)
        return self.is_hovered

    def handle_mouse_down(self, pos: Tuple[int, int]) -> bool:
        """Handle mouse down, return True if dragging started"""
        if self.is_hovered:
            self.is_dragging = True
            self.drag_start_pos = pos
            return True
        return False

    def handle_mouse_up(self) -> bool:
        """Handle mouse up, return True if was dragging"""
        was_dragging = self.is_dragging
        self.is_dragging = False
        return was_dragging

    def handle_drag(self, pos: Tuple[int, int], container_rect: pygame.Rect) -> float:
        """Handle drag motion, return new split ratio"""
        if not self.is_dragging:
            return self.split_ratio

        if self.orientation == 'horizontal':
            # Dragging vertically
            relative_y = pos[1] - container_rect.y
            new_ratio = relative_y / container_rect.height
        else:
            # Dragging horizontally
            relative_x = pos[0] - container_rect.x
            new_ratio = relative_x / container_rect.width

        # Clamp ratio to reasonable bounds
        min_size = self.config.layout.splitter_min_panel_size
        if self.orientation == 'horizontal':
            min_ratio = min_size / container_rect.height
            max_ratio = (container_rect.height - min_size) / container_rect.height
        else:
            min_ratio = min_size / container_rect.width
            max_ratio = (container_rect.width - min_size) / container_rect.width

        self.split_ratio = max(min_ratio, min(max_ratio, new_ratio))
        return self.split_ratio

    def draw(self, surface: pygame.Surface):
        """Draw the splitter"""
        if self.is_dragging:
            color = self.theme_manager.get_color('splitter_active_bg')
        elif self.is_hovered:
            color = self.theme_manager.get_color('splitter_hover_bg')
        else:
            color = self.theme_manager.get_color('splitter_bg')

        pygame.draw.rect(surface, color, self.rect)


class DockZone:
    """Represents a dockable area that can contain panels or other zones"""

    def __init__(self, zone_type: DockZoneType, config: DockingConfig, theme_manager: DockingThemeManager):
        self.zone_type = zone_type
        self.config = config
        self.theme_manager = theme_manager
        self.rect = pygame.Rect(0, 0, 200, 200)

        # For container zones
        self.tab_group: Optional[TabGroup] = None

        # For splitter zones
        self.child_zones: List['DockZone'] = []
        self.splitter: Optional[Splitter] = None
        self.split_direction: Optional[str] = None  # 'horizontal' or 'vertical'

        # Parent relationship
        self.parent_zone: Optional['DockZone'] = None

    def is_empty(self) -> bool:
        """Check if this zone is empty"""
        if self.zone_type == DockZoneType.CONTAINER:
            return self.tab_group is None or len(self.tab_group.containers) == 0
        elif self.zone_type == DockZoneType.SPLITTER:
            return len(self.child_zones) == 0
        return True

    def add_container(self, container: DockContainer, direction: DockDirection = DockDirection.CENTER):
        """Add a container to this zone"""
        if self.zone_type == DockZoneType.CONTAINER:
            if direction == DockDirection.CENTER:
                # Add to existing tab group or create new one
                if self.tab_group is None:
                    self.tab_group = TabGroup(self.config, self.theme_manager)
                    self.tab_group.set_rect(self.rect)

                self.tab_group.add_container(container)
                container.dock_zone = self
            else:
                # Convert to splitter zone
                self._convert_to_splitter(container, direction)
        elif self.zone_type == DockZoneType.SPLITTER:
            # Add to appropriate child zone or create new one
            self._add_to_splitter(container, direction)

    def remove_container(self, container: DockContainer) -> bool:
        """Remove a container from this zone"""
        if self.zone_type == DockZoneType.CONTAINER and self.tab_group:
            success = self.tab_group.remove_container(container)
            if success:
                container.dock_zone = None
                # Clean up empty tab group
                if len(self.tab_group.containers) == 0:
                    self.tab_group = None
            return success
        elif self.zone_type == DockZoneType.SPLITTER:
            # Try to remove from child zones
            for zone in self.child_zones:
                if zone.remove_container(container):
                    self._cleanup_empty_children()
                    return True
        return False

    def _convert_to_splitter(self, new_container: DockContainer, direction: DockDirection):
        """Convert this container zone to a splitter zone"""
        # Save existing containers
        existing_containers = []
        if self.tab_group:
            existing_containers = self.tab_group.containers.copy()

        # Clear current state
        self.tab_group = None
        self.zone_type = DockZoneType.SPLITTER

        # Set split direction
        if direction in [DockDirection.LEFT, DockDirection.RIGHT]:
            self.split_direction = 'vertical'
        else:
            self.split_direction = 'horizontal'

        # Create child zones
        zone1 = DockZone(DockZoneType.CONTAINER, self.config, self.theme_manager)
        zone2 = DockZone(DockZoneType.CONTAINER, self.config, self.theme_manager)
        zone1.parent_zone = self
        zone2.parent_zone = self

        # Add containers to appropriate zones
        if direction in [DockDirection.LEFT, DockDirection.TOP]:
            # New container goes first
            zone1.add_container(new_container)
            for container in existing_containers:
                zone2.add_container(container)
        else:
            # Existing containers go first
            for container in existing_containers:
                zone1.add_container(container)
            zone2.add_container(new_container)

        self.child_zones = [zone1, zone2]

        # Create splitter
        self.splitter = Splitter(self.split_direction, self.config, self.theme_manager)

        # Update layout
        self._update_splitter_layout()

    def _add_to_splitter(self, container: DockContainer, direction: DockDirection):
        """Add container to splitter zone"""
        # For now, add to the first available child zone
        # In a full implementation, you'd determine the best zone based on direction
        for zone in self.child_zones:
            if not zone.is_empty():
                zone.add_container(container, direction)
                return

        # If all zones are empty, add to first
        if self.child_zones:
            self.child_zones[0].add_container(container, direction)

    def _cleanup_empty_children(self):
        """Remove empty child zones and simplify structure"""
        # Remove empty child zones
        self.child_zones = [zone for zone in self.child_zones if not zone.is_empty()]

        # If only one child remains, convert back to container
        if len(self.child_zones) == 1:
            remaining_zone = self.child_zones[0]
            if remaining_zone.zone_type == DockZoneType.CONTAINER:
                self.zone_type = DockZoneType.CONTAINER
                self.tab_group = remaining_zone.tab_group
                self.child_zones.clear()
                self.splitter = None
                self.split_direction = None

                # Update parent references
                if self.tab_group:
                    for container in self.tab_group.containers:
                        container.dock_zone = self

    def _update_splitter_layout(self):
        """Update layout for splitter zone"""
        if (self.zone_type != DockZoneType.SPLITTER or
                len(self.child_zones) != 2 or
                not self.splitter):
            return

        splitter_size = self.config.layout.splitter_size

        if self.split_direction == 'horizontal':
            # Split horizontally (top/bottom)
            split_y = int(self.rect.y + self.rect.height * self.splitter.split_ratio)

            # First zone (top)
            zone1_rect = pygame.Rect(
                self.rect.x, self.rect.y,
                self.rect.width, split_y - self.rect.y
            )

            # Splitter
            splitter_rect = pygame.Rect(
                self.rect.x, split_y,
                self.rect.width, splitter_size
            )

            # Second zone (bottom)
            zone2_rect = pygame.Rect(
                self.rect.x, split_y + splitter_size,
                self.rect.width, self.rect.bottom - (split_y + splitter_size)
            )
        else:
            # Split vertically (left/right)
            split_x = int(self.rect.x + self.rect.width * self.splitter.split_ratio)

            # First zone (left)
            zone1_rect = pygame.Rect(
                self.rect.x, self.rect.y,
                split_x - self.rect.x, self.rect.height
            )

            # Splitter
            splitter_rect = pygame.Rect(
                split_x, self.rect.y,
                splitter_size, self.rect.height
            )

            # Second zone (right)
            zone2_rect = pygame.Rect(
                split_x + splitter_size, self.rect.y,
                self.rect.right - (split_x + splitter_size), self.rect.height
            )

        # Update child zones and splitter
        self.child_zones[0].set_rect(zone1_rect)
        self.child_zones[1].set_rect(zone2_rect)
        self.splitter.set_rect(splitter_rect)

    def set_rect(self, rect: pygame.Rect):
        """Set the zone's rect"""
        self.rect = rect

        if self.zone_type == DockZoneType.CONTAINER and self.tab_group:
            self.tab_group.set_rect(rect)
            # Force layout update
            self.tab_group._update_layout()
        elif self.zone_type == DockZoneType.SPLITTER:
            self._update_splitter_layout()
            # Update child zones recursively
            for child_zone in self.child_zones:
                child_zone.set_rect(child_zone.rect)  # This will cascade the updates

    def handle_mouse_click(self, pos: Tuple[int, int]) -> Optional[str]:
        """Handle mouse click"""
        if not self.rect.collidepoint(pos):
            return None

        if self.zone_type == DockZoneType.CONTAINER and self.tab_group:
            return self.tab_group.handle_mouse_click(pos)
        elif self.zone_type == DockZoneType.SPLITTER:
            # Handle splitter drag
            if self.splitter and self.splitter.handle_mouse_down(pos):
                return "splitter_drag"

            # Forward to child zones
            for zone in self.child_zones:
                result = zone.handle_mouse_click(pos)
                if result:
                    return result

        return None

    def handle_mouse_motion(self, pos: Tuple[int, int]) -> Optional[str]:
        """Handle mouse motion, return cursor hint"""
        if not self.rect.collidepoint(pos):
            return None

        if self.zone_type == DockZoneType.CONTAINER and self.tab_group:
            self.tab_group.handle_mouse_motion(pos)
            return None
        elif self.zone_type == DockZoneType.SPLITTER:
            # Check splitter hover
            if self.splitter and self.splitter.handle_mouse_motion(pos):
                return "resize_" + self.split_direction

            # Forward to child zones
            for zone in self.child_zones:
                result = zone.handle_mouse_motion(pos)
                if result:
                    return result

        return None

    def handle_mouse_drag(self, pos: Tuple[int, int]) -> bool:
        """Handle mouse drag for splitter"""
        if (self.zone_type == DockZoneType.SPLITTER and
                self.splitter and self.splitter.is_dragging):
            self.splitter.handle_drag(pos, self.rect)
            self._update_splitter_layout()
            return True
        return False

    def handle_mouse_up(self) -> bool:
        """Handle mouse up"""
        handled = False

        if self.zone_type == DockZoneType.CONTAINER and self.tab_group:
            handled = self.tab_group.handle_mouse_up() or handled
        elif self.zone_type == DockZoneType.SPLITTER:
            if self.splitter:
                handled = self.splitter.handle_mouse_up() or handled

            for zone in self.child_zones:
                handled = zone.handle_mouse_up() or handled

        return handled

    def draw(self, surface: pygame.Surface):
        """Draw the dock zone"""
        if self.zone_type == DockZoneType.CONTAINER:
            if self.tab_group and self.tab_group.containers:
                self.tab_group.draw(surface)
            else:
                # Draw empty zone
                empty_color = self.theme_manager.get_color('panel_bg')
                pygame.draw.rect(surface, empty_color, self.rect)
                pygame.draw.rect(surface, self.theme_manager.get_color('panel_border'), self.rect, 1)
        elif self.zone_type == DockZoneType.SPLITTER:
            # Draw child zones first
            for zone in self.child_zones:
                zone.draw(surface)

            # Draw splitter
            if self.splitter:
                self.splitter.draw(surface)

    def get_all_containers(self) -> List[DockContainer]:
        """Get all containers in this zone recursively"""
        containers = []

        if self.zone_type == DockZoneType.CONTAINER and self.tab_group:
            containers.extend(self.tab_group.containers)
        elif self.zone_type == DockZoneType.SPLITTER:
            for zone in self.child_zones:
                containers.extend(zone.get_all_containers())

        return containers


class DockingManager(UIElement):
    """Main docking system manager"""

    def __init__(self, relative_rect: pygame.Rect,
                 manager: pygame_gui.UIManager,
                 config: DockingConfig = None,
                 container: IContainerLikeInterface = None,
                 object_id: Union[ObjectID, str, None] = None,
                 anchors: Dict[str, str] = None):

        # Handle object_id
        if isinstance(object_id, ObjectID):
            self._object_id = object_id
        elif isinstance(object_id, str):
            self._object_id = ObjectID(object_id=object_id, class_id=None)
        else:
            self._object_id = ObjectID(object_id='#docking_manager', class_id=None)

        super().__init__(relative_rect, manager, container,
                         starting_height=1, layer_thickness=1,
                         anchors=anchors, object_id=self._object_id)

        self.config = config or DockingConfig()

        # Create theme manager
        element_ids = ['docking_manager']
        if hasattr(self, 'object_ids') and self.object_ids:
            element_ids.extend(self.object_ids)
        self.theme_manager = DockingThemeManager(manager, element_ids)

        # Root dock zone
        self.root_zone = DockZone(DockZoneType.ROOT, self.config, self.theme_manager)
        self.root_zone.set_rect(pygame.Rect(0, 0, relative_rect.width, relative_rect.height))

        # Panel management
        self.containers: Dict[str, DockContainer] = {}
        self.floating_panels: List[DockContainer] = []

        # Interaction state
        self.current_cursor = None

        # Create image surface
        self.image = pygame.Surface(self.rect.size).convert()

        # Initial draw
        self.rebuild_image()

    def get_top_layer(self) -> int:
        """Get the top layer for elements"""
        return 1

    def get_starting_height(self) -> int:
        """Get starting height for elements"""
        return 1

    def layer_thickness(self) -> int:
        """Get layer thickness"""
        return 1

    def on_contained_elements_changed(self, element):
        """Called when a contained element changes"""
        # For the docking system, we don't need to do anything special here
        # as we manage the layout ourselves
        pass

    def get_container(self):
        """Get the container for this element"""
        return self

    def get_rect(self) -> pygame.Rect:
        """Get the rect for container interface"""
        return self.rect

    def get_relative_rect(self) -> pygame.Rect:
        """Get relative rect for container interface"""
        return pygame.Rect(0, 0, self.rect.width, self.rect.height)

    def get_size(self) -> Tuple[int, int]:
        """Get size for container interface"""
        return self.rect.width, self.rect.height

    def get_abs_rect(self) -> pygame.Rect:
        """Get absolute rect for container interface"""
        return self.rect

    def _check_container_overlaps(self, other_element):
        """Check if container overlaps with other element"""
        return self.rect.colliderect(other_element.rect)

    def add_element(self, element):
        """Add element to container"""
        # This is handled by our docking system
        pass

    def remove_element(self, element):
        """Remove element from container"""
        # Find and remove the panel
        for panel_id, container in self.containers.items():
            if container.panel == element:
                self.remove_panel(panel_id)
                break

    def add_panel(self, panel: UIElement, title: str = None,
                  dock_direction: DockDirection = DockDirection.CENTER,
                  closable: bool = True) -> str:
        """Add a panel to the docking system"""
        # Create container
        container = DockContainer(panel, title, closable)

        # Set manager as container - handle different pygame-gui versions
        if hasattr(panel, 'container'):
            panel.container = self
        elif hasattr(panel, 'ui_container'):
            panel.ui_container = self

        # Generate unique ID
        panel_id = f"panel_{len(self.containers)}_{id(panel)}"
        self.containers[panel_id] = container

        # Add to root zone
        if self.root_zone.is_empty():
            # First panel becomes a container zone
            self.root_zone.zone_type = DockZoneType.CONTAINER

        self.root_zone.add_container(container, dock_direction)

        # Post event
        event_data = {
            'panel_id': panel_id,
            'panel': panel,
            'title': container.title
        }
        event = pygame.event.Event(UI_DOCK_PANEL_ADDED, event_data)
        pygame.event.post(event)

        self.rebuild_image()
        return panel_id

    def remove_panel(self, panel_id: str) -> bool:
        """Remove a panel from the docking system"""
        if panel_id not in self.containers:
            return False

        container = self.containers[panel_id]

        # Remove from dock zone
        success = self.root_zone.remove_container(container)

        if success:
            # Restore original container
            container.restore_original_container()

            # Remove from tracking
            del self.containers[panel_id]

            # Post event
            event_data = {
                'panel_id': panel_id,
                'panel': container.panel,
                'title': container.title
            }
            event = pygame.event.Event(UI_DOCK_PANEL_REMOVED, event_data)
            pygame.event.post(event)

            self.rebuild_image()

        return success

    def get_panel(self, panel_id: str) -> Optional[UIElement]:
        """Get a panel by ID"""
        container = self.containers.get(panel_id)
        return container.panel if container else None

    def get_all_panels(self) -> Dict[str, UIElement]:
        """Get all managed panels"""
        return {pid: container.panel for pid, container in self.containers.items()}

    def set_active_tab(self, panel_id: str) -> bool:
        """Set a panel as the active tab in its group"""
        if panel_id not in self.containers:
            return False

        container = self.containers[panel_id]
        if container.dock_zone and hasattr(container.dock_zone, 'tab_group'):
            tab_group = container.dock_zone.tab_group
            if tab_group and container in tab_group.containers:
                index = tab_group.containers.index(container)
                tab_group.set_active_index(index)
                self.rebuild_image()
                return True
        return False

    def save_layout(self) -> Dict[str, Any]:
        """Save the current layout to a dictionary"""

        def serialize_zone(zone: DockZone) -> Dict[str, Any]:
            zone_data = {
                'type': zone.zone_type.value,
                'rect': [zone.rect.x, zone.rect.y, zone.rect.width, zone.rect.height]
            }

            if zone.zone_type == DockZoneType.CONTAINER and zone.tab_group:
                zone_data['containers'] = []
                for container in zone.tab_group.containers:
                    # Find panel ID
                    panel_id = None
                    for pid, cont in self.containers.items():
                        if cont == container:
                            panel_id = pid
                            break

                    if panel_id:
                        zone_data['containers'].append({
                            'panel_id': panel_id,
                            'title': container.title,
                            'closable': container.closable
                        })

                zone_data['active_index'] = zone.tab_group.active_index

            elif zone.zone_type == DockZoneType.SPLITTER:
                zone_data['split_direction'] = zone.split_direction
                zone_data['split_ratio'] = zone.splitter.split_ratio if zone.splitter else 0.5
                zone_data['children'] = [serialize_zone(child) for child in zone.child_zones]

            return zone_data

        return {
            'version': '1.0',
            'root_zone': serialize_zone(self.root_zone),
            'config': {
                'title': self.config.title
            }
        }

    def load_layout(self, layout_data: Dict[str, Any]) -> bool:
        """Load a layout from dictionary"""
        try:
            # This is a simplified version - full implementation would
            # recursively rebuild the zone structure and restore panels
            # For now, just clear and start fresh

            # Clear current layout
            self.root_zone = DockZone(DockZoneType.ROOT, self.config, self.theme_manager)
            self.root_zone.set_rect(pygame.Rect(0, 0, self.rect.width, self.rect.height))

            self.rebuild_image()
            return True

        except Exception as e:
            if DOCK_DEBUG:
                print(f"Error loading layout: {e}")
            return False

    def rebuild_image(self):
        """Rebuild the docking system image"""
        # Fill background
        bg_color = self.theme_manager.get_color('background')
        self.image.fill(bg_color)

        # Draw root zone
        self.root_zone.draw(self.image)

    def process_event(self, event: pygame.event.Event) -> bool:
        """Process pygame events"""
        consumed = False

        try:
            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.rect.collidepoint(event.pos):
                    relative_pos = (event.pos[0] - self.rect.x, event.pos[1] - self.rect.y)
                    result = self.root_zone.handle_mouse_click(relative_pos)

                    if result:
                        if result.startswith('close_tab_'):
                            # Extract tab index and find the container to close
                            try:
                                tab_index = int(result.split('_')[-1])
                                # Find which tab group this belongs to and close the right panel
                                closed = self._handle_close_tab(relative_pos, tab_index)
                                consumed = closed
                            except (ValueError, IndexError):
                                pass
                        elif result.startswith('select_tab_'):
                            # Tab selection is already handled
                            consumed = True
                        elif result == 'splitter_drag':
                            consumed = True

            elif event.type == pygame.MOUSEBUTTONUP:
                consumed = self.root_zone.handle_mouse_up()

            elif event.type == pygame.MOUSEMOTION:
                if self.rect.collidepoint(event.pos):
                    relative_pos = (event.pos[0] - self.rect.x, event.pos[1] - self.rect.y)
                    cursor_hint = self.root_zone.handle_mouse_motion(relative_pos)

                    # Handle drag
                    self.root_zone.handle_mouse_drag(relative_pos)

                    # Update cursor
                    if cursor_hint != self.current_cursor:
                        self.current_cursor = cursor_hint

        except Exception as e:
            if DOCK_DEBUG:
                print(f"Error processing dock event: {e}")

        return consumed

    def _handle_close_tab(self, pos: Tuple[int, int], tab_index: int) -> bool:
        """Handle closing a tab at the given position"""

        # Find the tab group that contains this position
        def find_tab_group_at_pos(zone: DockZone, pos: Tuple[int, int]) -> Optional[TabGroup]:
            if not zone.rect.collidepoint(pos):
                return None

            if zone.zone_type == DockZoneType.CONTAINER and zone.tab_group:
                return zone.tab_group
            elif zone.zone_type == DockZoneType.SPLITTER:
                for child_zone in zone.child_zones:
                    result = find_tab_group_at_pos(child_zone, pos)
                    if result:
                        return result
            return None

        tab_group = find_tab_group_at_pos(self.root_zone, pos)
        if tab_group and 0 <= tab_index < len(tab_group.containers):
            container = tab_group.containers[tab_index]

            # Find the panel ID
            panel_id = None
            for pid, cont in self.containers.items():
                if cont == container:
                    panel_id = pid
                    break

            if panel_id:
                return self.remove_panel(panel_id)

        return False


# Example theme for docking system
DOCKING_THEME = {
    "docking_manager": {
        "colours": {
            "background": "#2d2d2d",
            "panel_bg": "#353535",
            "panel_border": "#505050",
            "panel_header_bg": "#404040",
            "panel_header_text": "#ffffff",
            "tab_bg": "#464646",
            "tab_active_bg": "#5a5a5a",
            "tab_hover_bg": "#505050",
            "tab_text": "#ffffff",
            "tab_border": "#646464",
            "splitter_bg": "#404040",
            "splitter_hover_bg": "#505050",
            "splitter_active_bg": "#646464",
            "drop_zone_valid": "#6496ff80",
            "drop_zone_invalid": "#ff646480",
            "drop_indicator": "#78a0ff",
            "close_button_bg": "#505050",
            "close_button_hover_bg": "#c86464",
            "close_button_text": "#ffffff"
        },
        "font": {
            "name": "arial",
            "size": "12",
            "bold": "0",
            "italic": "0"
        }
    }
}


def create_docking_demo():
    """Create a demo of the docking system"""
    pygame.init()
    screen = pygame.display.set_mode((1200, 800))
    pygame.display.set_caption("Docking System Demo")
    clock = pygame.time.Clock()

    # Create manager with theme
    manager = pygame_gui.UIManager((1200, 800), DOCKING_THEME)

    # Create docking manager
    docking_config = DockingConfig()
    docking_manager = DockingManager(
        pygame.Rect(0, 0, 1200, 800),
        manager,
        docking_config,
        object_id='#main_docking'
    )

    # Create some demo panels - don't set container initially
    demo_panel1 = pygame_gui.elements.UIPanel(
        relative_rect=pygame.Rect(0, 0, 300, 200),
        manager=manager
        # Don't set container here
    )

    demo_panel2 = pygame_gui.elements.UIPanel(
        relative_rect=pygame.Rect(0, 0, 300, 200),
        manager=manager
        # Don't set container here
    )

    # Add panels to docking system (container will be set inside add_panel)
    panel1_id = docking_manager.add_panel(demo_panel1, "Panel 1", DockDirection.CENTER)
    panel2_id = docking_manager.add_panel(demo_panel2, "Panel 2", DockDirection.RIGHT)

    print("\nDocking System Demo")
    print("\nControls:")
    print("- Click tabs to switch between panels")
    print("- Drag splitters to resize")
    print("- ESC to quit")

    running = True
    while running:
        time_delta = clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_s:
                    # Save layout
                    layout = docking_manager.save_layout()
                    print("Layout saved:", json.dumps(layout, indent=2))

            # Process pygame-gui events FIRST
            manager.process_events(event)
            # Then process docking events (only if not consumed by pygame-gui)
            docking_manager.process_event(event)

            # Process docking events first
            # if not docking_manager.process_event(event):
            #     manager.process_events(event)

        manager.update(time_delta)

        # Draw
        screen.fill((30, 30, 30))
        manager.draw_ui(screen)

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    create_docking_demo()