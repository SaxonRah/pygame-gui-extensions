import pygame
import pygame_gui
from pygame_gui.core import UIElement, ObjectID
from pygame_gui.core.interfaces import IContainerLikeInterface
from typing import List, Optional, Dict, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import os

try:
    from pygame_gui.core.interfaces.gui_font_interface import IGUIFontInterface
except ImportError:
    IGUIFontInterface = None

HIERARCHY_DEBUG = False

# Define custom pygame-gui events
UI_HIERARCHY_NODE_SELECTED = pygame.USEREVENT + 1
UI_HIERARCHY_NODE_DESELECTED = pygame.USEREVENT + 2
UI_HIERARCHY_NODE_DOUBLE_CLICKED = pygame.USEREVENT + 3
UI_HIERARCHY_NODE_RIGHT_CLICKED = pygame.USEREVENT + 4
UI_HIERARCHY_NODE_EXPANDED = pygame.USEREVENT + 5
UI_HIERARCHY_NODE_COLLAPSED = pygame.USEREVENT + 6
UI_HIERARCHY_DRAG_STARTED = pygame.USEREVENT + 7
UI_HIERARCHY_DROP_COMPLETED = pygame.USEREVENT + 8


class HierarchyNodeType(Enum):
    FOLDER = "folder"
    ITEM = "item"
    ROOT = "root"


@dataclass
class HierarchyNode:
    """Generic hierarchy node that can represent any data structure"""
    id: str
    name: str
    node_type: HierarchyNodeType
    data: Dict[str, Any] = field(default_factory=dict)
    children: List['HierarchyNode'] = field(default_factory=list)
    parent: Optional['HierarchyNode'] = None
    expanded: bool = True
    icon_name: Optional[str] = None

    def add_child(self, child: 'HierarchyNode'):
        """Add a child node"""
        child.parent = self
        self.children.append(child)

    def remove_child(self, child: 'HierarchyNode'):
        """Remove a child node"""
        if child in self.children:
            child.parent = None
            self.children.remove(child)

    def get_depth(self) -> int:
        """Get the depth level of this node"""
        depth = 0
        current = self.parent
        while current:
            depth += 1
            current = current.parent
        return depth

    def find_node(self, node_id: str) -> Optional['HierarchyNode']:
        """Find a node by ID recursively"""
        if self.id == node_id:
            return self
        for child in self.children:
            found = child.find_node(node_id)
            if found:
                return found
        return None


@dataclass
class HierarchyLayoutConfig:
    """Layout and spacing configuration for hierarchy panel"""
    # Node sizing
    node_height: int = 25
    indent_size: int = 20
    icon_size: tuple = (16, 16)

    # Expand button configuration
    expand_button_size: int = 12
    expand_button_margin_left: int = 5
    expand_button_triangle_size: int = 4

    # Icon positioning
    icon_margin_with_button: int = 20
    icon_margin_without_button: int = 5
    icon_margin_right: int = 5

    # Text positioning
    text_margin_left: int = 5

    # Border and line widths
    focus_border_width: int = 2
    drop_line_width: int = 3

    # Fallback icon configuration
    fallback_icon_circle_radius: int = 4
    fallback_font_size: int = 16


@dataclass
class HierarchyInteractionConfig:
    """Interaction and timing configuration"""
    double_click_time: int = 500  # milliseconds
    drop_zone_ratio: float = 0.25  # for before/after drop detection (0 to 1)

    # Scroll behavior
    scroll_speed: int = 3
    scroll_margin: int = 10


@dataclass
class HierarchyConfig:
    """Configuration for the hierarchy panel"""
    # Layout settings
    layout: HierarchyLayoutConfig = field(default_factory=HierarchyLayoutConfig)

    # Interaction settings
    interaction: HierarchyInteractionConfig = field(default_factory=HierarchyInteractionConfig)

    # Behavior
    allow_drag: bool = True
    allow_drop: bool = True
    allow_reorder: bool = True
    show_root: bool = False
    folders_only_have_children: bool = False

    # Animation settings
    expand_animation_time: float = 0.0  # 0 = no animation

    # Convenience properties for backward compatibility
    @property
    def indent_size(self) -> int:
        return self.layout.indent_size

    @property
    def node_height(self) -> int:
        return self.layout.node_height

    @property
    def icon_size(self) -> tuple:
        return self.layout.icon_size


class IconManager:
    """Manages icons for the hierarchy panel"""

    def __init__(self, manager: pygame_gui.UIManager, config: HierarchyLayoutConfig):
        self.manager = manager
        self.config = config
        self.icon_cache = {}
        self.default_icons = {}
        self._create_default_icons()

    def _create_default_icons(self):
        """Create default icons for common node types"""
        icon_surface = pygame.Surface(self.config.icon_size, pygame.SRCALPHA)

        # Folder icon (yellow folder shape)
        folder_surface = icon_surface.copy()
        folder_color = pygame.Color(255, 215, 0)  # Gold
        pygame.draw.rect(folder_surface, folder_color,
                         pygame.Rect(1, 4, 12, 8))
        pygame.draw.rect(folder_surface, folder_color,
                         pygame.Rect(1, 2, 4, 2))
        self.default_icons[HierarchyNodeType.FOLDER] = folder_surface

        # Folder open icon (opened folder)
        folder_open_surface = icon_surface.copy()
        pygame.draw.rect(folder_open_surface, folder_color,
                         pygame.Rect(1, 6, 12, 6))
        pygame.draw.polygon(folder_open_surface, folder_color,
                            [(1, 4), (5, 4), (6, 6), (1, 6)])
        self.default_icons['folder_open'] = folder_open_surface

        # Item icon (document/file)
        item_surface = icon_surface.copy()
        item_color = pygame.Color(200, 200, 200)  # Light gray
        pygame.draw.rect(item_surface, item_color,
                         pygame.Rect(3, 2, 8, 11))
        pygame.draw.rect(item_surface, pygame.Color(100, 100, 100),
                         pygame.Rect(3, 2, 8, 11), 1)
        # Small lines to represent text
        pygame.draw.line(item_surface, pygame.Color(100, 100, 100),
                         (4, 5), (9, 5))
        pygame.draw.line(item_surface, pygame.Color(100, 100, 100),
                         (4, 7), (9, 7))
        pygame.draw.line(item_surface, pygame.Color(100, 100, 100),
                         (4, 9), (7, 9))
        self.default_icons[HierarchyNodeType.ITEM] = item_surface

    def get_icon(self, node: HierarchyNode, is_expanded: bool = False) -> pygame.Surface:
        """Get icon for a node, with caching"""
        cache_key = f"{node.id}_{node.node_type.value}_{is_expanded}_{node.icon_name}"

        if cache_key in self.icon_cache:
            return self.icon_cache[cache_key]

        icon_surface = None

        # Try custom icon first
        if node.icon_name:
            icon_surface = self._load_themed_icon(node.icon_name)

        # Fall back to default icons
        if icon_surface is None:
            if node.node_type == HierarchyNodeType.FOLDER:
                if is_expanded and node.children:
                    icon_surface = self.default_icons['folder_open']
                else:
                    icon_surface = self.default_icons[HierarchyNodeType.FOLDER]
            else:
                icon_surface = self.default_icons.get(node.node_type)

        # Create a blank icon if nothing found
        if icon_surface is None:
            icon_surface = pygame.Surface(self.config.icon_size, pygame.SRCALPHA)
            center = (self.config.icon_size[0] // 2, self.config.icon_size[1] // 2)
            pygame.draw.circle(icon_surface, pygame.Color(150, 150, 150),
                               center, self.config.fallback_icon_circle_radius)

        self.icon_cache[cache_key] = icon_surface
        return icon_surface

    def _load_themed_icon(self, icon_name: str) -> Optional[pygame.Surface]:
        """Load icon from theme or file system"""
        try:
            icon_paths = [
                f"icons/{icon_name}.png",
                f"assets/icons/{icon_name}.png",
                f"data/icons/{icon_name}.png",
                f"{icon_name}.png"
            ]

            for path in icon_paths:
                if os.path.exists(path):
                    surface = pygame.image.load(path).convert_alpha()
                    return pygame.transform.scale(surface, self.config.icon_size)

        except Exception as e:
            if HIERARCHY_DEBUG:
                print(f"Failed to load icon {icon_name}: {e}")

        return None

    def clear_cache(self):
        """Clear the icon cache"""
        self.icon_cache.clear()


class HierarchyNodeUI:
    """UI representation of a hierarchy node"""

    def __init__(self, node: HierarchyNode, rect: pygame.Rect, config: HierarchyConfig):
        self.node = node
        self.rect = rect
        self.config = config
        self.is_hovered = False
        self.is_selected = False
        self.is_focused = False
        self.is_drop_target = False
        self.is_invalid_drop_target = False
        self.drop_position = None
        self.expand_button_rect = None

        # Calculate expand button position if node has children
        if self.node.children:
            button_size = self.config.layout.expand_button_size
            indent = self.node.get_depth() * self.config.layout.indent_size
            self.expand_button_rect = pygame.Rect(
                indent + self.config.layout.expand_button_margin_left,
                (rect.height - button_size) // 2,
                button_size,
                button_size
            )

    def draw(self, surface: pygame.Surface,
             font: Union[pygame.font.Font, 'IGUIFontInterface', Any],
             surface_rect: pygame.Rect,
             colors: Dict[str, pygame.Color],
             icon_manager: IconManager):
        """Draw the node UI onto the surface (relative coordinates)"""
        layout = self.config.layout
        draw_rect = pygame.Rect(0, 0, surface_rect.width, layout.node_height)

        # Background
        if self.is_invalid_drop_target:
            drop_color = colors.get('invalid_drop', pygame.Color(150, 80, 80))
            if self.drop_position == 1:  # As child - highlight entire node
                pygame.draw.rect(surface, drop_color, draw_rect)
            else:  # Before/after - draw line
                line_y = draw_rect.top if self.drop_position == 0 else draw_rect.bottom - 1
                pygame.draw.line(surface, drop_color,
                                 (draw_rect.left, line_y), (draw_rect.right, line_y),
                                 layout.drop_line_width)
        elif self.is_drop_target:
            drop_color = colors.get('valid_drop', pygame.Color(100, 150, 100))
            if self.drop_position == 1:  # As child - highlight entire node
                pygame.draw.rect(surface, drop_color, draw_rect)
            else:  # Before/after - draw line
                line_y = draw_rect.top if self.drop_position == 0 else draw_rect.bottom - 1
                pygame.draw.line(surface, drop_color,
                                 (draw_rect.left, line_y), (draw_rect.right, line_y),
                                 layout.drop_line_width)
        elif self.is_focused:
            pygame.draw.rect(surface, colors.get('focused_bg', pygame.Color(100, 160, 220)), draw_rect)
            # Draw focus border
            pygame.draw.rect(surface, colors.get('focus_border', pygame.Color(255, 255, 255)),
                             draw_rect, layout.focus_border_width)
        elif self.is_selected:
            pygame.draw.rect(surface, colors.get('selected_bg', pygame.Color(70, 130, 180)), draw_rect)
        elif self.is_hovered:
            pygame.draw.rect(surface, colors.get('hovered_bg', pygame.Color(60, 60, 60)), draw_rect)

        indent = self.node.get_depth() * layout.indent_size

        # Draw expand/collapse button
        if self.node.children and self.expand_button_rect:
            center_x = self.expand_button_rect.centerx
            center_y = self.expand_button_rect.centery
            text_color = colors.get('normal_text', pygame.Color(255, 255, 255))
            triangle_size = layout.expand_button_triangle_size

            if self.node.expanded:
                # Draw collapse button (triangle pointing down)
                points = [
                    (center_x - triangle_size, center_y - triangle_size // 2),
                    (center_x + triangle_size, center_y - triangle_size // 2),
                    (center_x, center_y + triangle_size - 1)
                ]
            else:
                # Draw expand button (triangle pointing right)
                points = [
                    (center_x - triangle_size // 2, center_y - triangle_size),
                    (center_x - triangle_size // 2, center_y + triangle_size),
                    (center_x + triangle_size - 1, center_y)
                ]
            pygame.draw.polygon(surface, text_color, points)

        # Draw icon
        icon_x = indent + (layout.icon_margin_with_button if self.node.children
                           else layout.icon_margin_without_button)
        icon_surface = icon_manager.get_icon(self.node, self.node.expanded)
        icon_y = (draw_rect.height - icon_surface.get_height()) // 2
        surface.blit(icon_surface, (icon_x, icon_y))

        # Draw text
        text_x = icon_x + layout.icon_size[0] + layout.icon_margin_right
        try:
            text_color = colors.get('normal_text', pygame.Color(255, 255, 255))

            # Check if it's a pygame-gui font or regular pygame font
            if hasattr(font, 'render_premul'):
                text_surface = font.render_premul(self.node.name, text_color)
            elif hasattr(font, 'render'):
                text_surface = font.render(self.node.name, True, text_color)
            else:
                fallback_font = pygame.font.Font(None, layout.fallback_font_size)
                text_surface = fallback_font.render(self.node.name, True, text_color)

            text_y = (draw_rect.height - text_surface.get_height()) // 2
            surface.blit(text_surface, (text_x, text_y))

        except Exception as e:
            if HIERARCHY_DEBUG:
                print(f"Error rendering text for {self.node.name}: {e}")
            try:
                fallback_font = pygame.font.Font(None, layout.fallback_font_size)
                text_surface = fallback_font.render(self.node.name, True, pygame.Color(255, 255, 255))
                text_y = (draw_rect.height - text_surface.get_height()) // 2
                surface.blit(text_surface, (text_x, text_y))
            except:
                pass

    def handle_click(self, pos: tuple, panel_rect: pygame.Rect) -> str:
        """Handle click events, return action type"""
        relative_pos = (pos[0] - self.rect.x, pos[1] - self.rect.y)

        if self.expand_button_rect and self.expand_button_rect.collidepoint(relative_pos):
            return "expand_toggle"
        return "select"


class HierarchyPanel(UIElement):
    """Main hierarchy panel widget that inherits from UIElement"""

    def __init__(self, relative_rect: pygame.Rect,
                 manager: pygame_gui.UIManager,
                 root_node: HierarchyNode,
                 config: HierarchyConfig = None,
                 container: IContainerLikeInterface = None,
                 object_id: Union[ObjectID, str, None] = None,
                 anchors: Dict[str, str] = None):

        if isinstance(object_id, ObjectID):
            self._object_id = object_id
        elif isinstance(object_id, str):
            self._object_id = ObjectID(object_id=object_id, class_id=None)
        else:
            self._object_id = ObjectID(object_id='#hierarchy_panel', class_id=None)

        super().__init__(relative_rect, manager, container,
                         starting_height=1, layer_thickness=1,
                         anchors=anchors, object_id=self._object_id)

        self.root_node = root_node
        self.config = config or HierarchyConfig()

        # Icon manager
        self.icon_manager = IconManager(manager, self.config.layout)

        # UI state
        self.visible_nodes: List[HierarchyNode] = []
        self.node_uis: List[HierarchyNodeUI] = []
        self.selected_node: Optional[HierarchyNode] = None
        self.focused_node: Optional[HierarchyNode] = None
        self.hovered_node: Optional[HierarchyNode] = None
        self.dragging_node: Optional[HierarchyNode] = None
        self.drag_offset = (0, 0)
        self.drop_target: Optional[HierarchyNode] = None
        self.drop_position = 0
        self.is_valid_drop = False

        # Keyboard navigation state
        self.is_focused = False
        self.last_click_time = 0
        self.double_click_time = self.config.interaction.double_click_time

        # Scrolling
        self.scroll_y = 0
        self.max_scroll = 0

        # Theme data
        self._update_theme_data()

        # Create the image surface that pygame-gui will draw
        self.image = pygame.Surface(self.rect.size).convert()

        # Set up the initial state
        self.rebuild_ui()
        self._rebuild_image()

    def _update_theme_data(self):
        """Update theme-dependent data"""
        try:
            self.themed_colors = {}

            color_mappings = {
                'dark_bg': pygame.Color(40, 40, 40),
                'normal_text': pygame.Color(255, 255, 255),
                'selected_bg': pygame.Color(70, 130, 180),
                'hovered_bg': pygame.Color(60, 60, 60),
                'focused_bg': pygame.Color(100, 160, 220),
                'normal_border': pygame.Color(100, 100, 100),
                'focus_border': pygame.Color(255, 255, 255),
                'valid_drop': pygame.Color(100, 150, 100),
                'invalid_drop': pygame.Color(150, 80, 80),
            }

            theme = self.ui_manager.get_theme()

            for color_id, default_color in color_mappings.items():
                try:
                    if hasattr(theme, 'get_colour_or_gradient'):
                        combined_id_parts = []

                        if hasattr(self, 'object_ids') and self.object_ids:
                            for obj_id in self.object_ids:
                                if obj_id:
                                    combined_id_parts.append(obj_id)

                        if hasattr(self, 'class_ids') and self.class_ids:
                            for class_id in self.class_ids:
                                if class_id:
                                    combined_id_parts.append(class_id)

                        if hasattr(self, 'element_ids') and self.element_ids:
                            for elem_id in self.element_ids:
                                if elem_id:
                                    combined_id_parts.append(elem_id)

                        combined_id = '.'.join(combined_id_parts) if combined_id_parts else None

                        if combined_id:
                            themed_color = theme.get_colour_or_gradient(color_id, combined_id)
                            if themed_color:
                                if hasattr(themed_color, 'colour'):
                                    self.themed_colors[color_id] = themed_color.colour
                                else:
                                    self.themed_colors[color_id] = themed_color
                            else:
                                self.themed_colors[color_id] = default_color
                        else:
                            self.themed_colors[color_id] = default_color
                    else:
                        self.themed_colors[color_id] = default_color

                except Exception:
                    self.themed_colors[color_id] = default_color

            try:
                self.themed_font = pygame.font.SysFont('Arial', 12)
            except:
                self.themed_font = pygame.font.Font(None, 12)

        except Exception as e:
            if HIERARCHY_DEBUG:
                print(f"Error updating theme data: {e}")
            # Fallback colors
            self.themed_colors = {
                'dark_bg': pygame.Color(40, 40, 40),
                'normal_text': pygame.Color(255, 255, 255),
                'selected_bg': pygame.Color(70, 130, 180),
                'hovered_bg': pygame.Color(60, 60, 60),
                'focused_bg': pygame.Color(100, 160, 220),
                'normal_border': pygame.Color(100, 100, 100),
                'focus_border': pygame.Color(255, 255, 255),
                'valid_drop': pygame.Color(100, 150, 100),
                'invalid_drop': pygame.Color(150, 80, 80),
            }
            try:
                self.themed_font = pygame.font.SysFont('Arial', 12)
            except:
                self.themed_font = pygame.font.Font(None, 12)

    def rebuild_from_changed_theme_data(self):
        """Called when theme data changes"""
        self._update_theme_data()
        self.rebuild_ui()
        self._rebuild_image()

    def _can_accept_children(self, node: HierarchyNode) -> bool:
        """Check if a node can accept children based on configuration"""
        if not self.config.folders_only_have_children:
            return True

        return node.node_type in [HierarchyNodeType.FOLDER, HierarchyNodeType.ROOT]

    def _is_valid_drop_target(self, target: HierarchyNode, position: int) -> bool:
        """Check if a drop operation would be valid"""
        if not target or not self.dragging_node:
            return False

        if target == self.dragging_node:
            return False

        if self._is_descendant(target, self.dragging_node):
            return False

        if position == 1:
            return self._can_accept_children(target)

        if target.parent:
            return self._can_accept_children(target.parent)

        return True

    def _collect_visible_nodes(self, node: HierarchyNode, nodes: List[HierarchyNode]):
        """Collect all visible nodes (accounting for expanded state)"""
        if node.node_type == HierarchyNodeType.ROOT and not self.config.show_root:
            pass
        else:
            nodes.append(node)

        if node.expanded:
            for child in node.children:
                self._collect_visible_nodes(child, nodes)

    def rebuild_ui(self):
        """Rebuild the UI node list"""
        if HIERARCHY_DEBUG:
            print("Rebuilding UI...")

        self.visible_nodes.clear()
        self._collect_visible_nodes(self.root_node, self.visible_nodes)

        self.node_uis.clear()
        for i, node in enumerate(self.visible_nodes):
            y_pos = i * self.config.layout.node_height - self.scroll_y
            rect = pygame.Rect(
                self.rect.x,
                self.rect.y + y_pos,
                self.rect.width,
                self.config.layout.node_height
            )
            node_ui = HierarchyNodeUI(node, rect, self.config)

            # Preserve state
            if node == self.selected_node:
                node_ui.is_selected = True
            if node == self.focused_node:
                node_ui.is_focused = True
            if node == self.hovered_node:
                node_ui.is_hovered = True

            self.node_uis.append(node_ui)

        # Update scroll bounds
        total_height = len(self.visible_nodes) * self.config.layout.node_height
        self.max_scroll = max(0, total_height - self.rect.height)

        if HIERARCHY_DEBUG:
            print(f"UI rebuilt: {len(self.visible_nodes)} visible nodes")

    def _rebuild_image(self):
        """Rebuild the image surface"""
        bg_color = self.themed_colors.get('dark_bg', pygame.Color(40, 40, 40))
        self.image.fill(bg_color)

        nodes_drawn = 0
        for node_ui in self.node_uis:
            if (node_ui.rect.bottom >= self.rect.y and
                    node_ui.rect.top < self.rect.y + self.rect.height):

                try:
                    surface_y = node_ui.rect.y - self.rect.y
                    if surface_y < 0:
                        clip_height = node_ui.rect.height + surface_y
                        if clip_height <= 0:
                            continue
                        surface_y = 0
                    else:
                        clip_height = min(node_ui.rect.height,
                                          self.rect.height - surface_y)

                    if clip_height <= 0:
                        continue

                    node_surface = self.image.subsurface(pygame.Rect(
                        0, surface_y, self.rect.width, clip_height
                    ))

                    surface_rect = pygame.Rect(0, 0, self.rect.width, clip_height)

                    node_ui.draw(node_surface, self.themed_font, surface_rect,
                                 self.themed_colors, self.icon_manager)
                    nodes_drawn += 1

                except (ValueError, pygame.error) as e:
                    if HIERARCHY_DEBUG:
                        print(f"Error drawing node: {e}")

        if HIERARCHY_DEBUG:
            print(f"Drew {nodes_drawn} nodes")

    @staticmethod
    def _is_descendant(potential_descendant: HierarchyNode, ancestor: HierarchyNode) -> bool:
        """Check if potential_descendant is a descendant of ancestor"""
        current = potential_descendant.parent
        while current:
            if current == ancestor:
                return True
            current = current.parent
        return False

    def update(self, time_delta: float):
        """Update the panel"""
        super().update(time_delta)
        self._rebuild_image()

    def process_event(self, event: pygame.event.Event) -> bool:
        """Process events for the hierarchy panel"""
        consumed = super().process_event(event)

        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                consumed = self._handle_mouse_down(event)

        elif event.type == pygame.MOUSEBUTTONUP:
            if self.dragging_node:
                consumed = self._handle_mouse_up(event)

        elif event.type == pygame.MOUSEMOTION:
            if self.rect.collidepoint(event.pos):
                consumed = self._handle_mouse_motion(event)

        elif event.type == pygame.KEYDOWN:
            if self.is_focused:
                consumed = self._handle_key_down(event)

        elif event.type == pygame.MOUSEWHEEL:
            if self.rect.collidepoint(pygame.mouse.get_pos()):
                consumed = self._handle_scroll(event)

        return consumed

    def _handle_mouse_down(self, event: pygame.event.Event) -> bool:
        """Handle mouse down events"""
        for node_ui in self.node_uis:
            if node_ui.rect.collidepoint(event.pos):
                action = node_ui.handle_click(event.pos, self.rect)

                if action == "expand_toggle":
                    node_ui.node.expanded = not node_ui.node.expanded
                    self.rebuild_ui()

                    event_data = {
                        'node_id': node_ui.node.id,
                        'expanded': node_ui.node.expanded,
                        'ui_element': self
                    }

                    if node_ui.node.expanded:
                        expand_event = pygame.event.Event(UI_HIERARCHY_NODE_EXPANDED, event_data)
                    else:
                        expand_event = pygame.event.Event(UI_HIERARCHY_NODE_COLLAPSED, event_data)

                    pygame.event.post(expand_event)
                    return True

                elif action == "select":
                    current_time = pygame.time.get_ticks()

                    # Check for double click
                    if (self.selected_node == node_ui.node and
                            current_time - self.last_click_time < self.double_click_time):

                        double_click_event = pygame.event.Event(UI_HIERARCHY_NODE_DOUBLE_CLICKED, {
                            'node_id': node_ui.node.id,
                            'ui_element': self
                        })
                        pygame.event.post(double_click_event)

                    else:
                        # Single click selection
                        if self.selected_node != node_ui.node:
                            old_selected = self.selected_node
                            self.selected_node = node_ui.node

                            if old_selected:
                                deselect_event = pygame.event.Event(UI_HIERARCHY_NODE_DESELECTED, {
                                    'node_id': old_selected.id,
                                    'ui_element': self
                                })
                                pygame.event.post(deselect_event)

                            select_event = pygame.event.Event(UI_HIERARCHY_NODE_SELECTED, {
                                'node_id': node_ui.node.id,
                                'ui_element': self
                            })
                            pygame.event.post(select_event)

                        # Start drag operation if enabled
                        if self.config.allow_drag and event.button == 1:
                            self.dragging_node = node_ui.node
                            self.drag_offset = (event.pos[0] - node_ui.rect.x,
                                                event.pos[1] - node_ui.rect.y)

                            drag_event = pygame.event.Event(UI_HIERARCHY_DRAG_STARTED, {
                                'node_id': node_ui.node.id,
                                'ui_element': self
                            })
                            pygame.event.post(drag_event)

                    self.last_click_time = current_time
                    self.rebuild_ui()
                    return True

        return False

    def _handle_mouse_up(self, event: pygame.event.Event) -> bool:
        """Handle mouse up events"""
        if self.dragging_node and self.config.allow_drop:
            if self.drop_target and self.is_valid_drop:
                # Perform the drop operation
                self._perform_drop_operation()

                drop_event = pygame.event.Event(UI_HIERARCHY_DROP_COMPLETED, {
                    'dragged_node_id': self.dragging_node.id,
                    'target_node_id': self.drop_target.id,
                    'drop_position': self.drop_position,
                    'ui_element': self
                })
                pygame.event.post(drop_event)

        # Clear drag state
        self.dragging_node = None
        self.drop_target = None
        self.is_valid_drop = False
        self.rebuild_ui()
        return True

    def _handle_mouse_motion(self, event: pygame.event.Event) -> bool:
        """Handle mouse motion events"""
        # Update hover state
        old_hovered = self.hovered_node
        self.hovered_node = None

        for node_ui in self.node_uis:
            if node_ui.rect.collidepoint(event.pos):
                self.hovered_node = node_ui.node
                break

        if old_hovered != self.hovered_node:
            self.rebuild_ui()

        # Handle drag and drop
        if self.dragging_node and self.config.allow_drop:
            self._update_drop_target(event.pos)

        return True

    def _handle_key_down(self, event: pygame.event.Event) -> bool:
        """Handle keyboard navigation"""
        if not self.selected_node:
            return False

        if event.key == pygame.K_UP:
            self._navigate_up()
            return True
        elif event.key == pygame.K_DOWN:
            self._navigate_down()
            return True
        elif event.key == pygame.K_LEFT:
            if self.selected_node.expanded and self.selected_node.children:
                self.selected_node.expanded = False
                self.rebuild_ui()
            return True
        elif event.key == pygame.K_RIGHT:
            if not self.selected_node.expanded and self.selected_node.children:
                self.selected_node.expanded = True
                self.rebuild_ui()
            return True

        return False

    def _handle_scroll(self, event: pygame.event.Event) -> bool:
        """Handle scroll wheel events"""
        scroll_amount = -event.y * self.config.interaction.scroll_speed * self.config.layout.node_height
        old_scroll = self.scroll_y
        self.scroll_y = max(0, min(self.max_scroll, self.scroll_y + scroll_amount))

        if old_scroll != self.scroll_y:
            self.rebuild_ui()
            return True

        return False

    def _navigate_up(self):
        """Navigate to previous visible node"""
        try:
            current_index = self.visible_nodes.index(self.selected_node)
            if current_index > 0:
                self.selected_node = self.visible_nodes[current_index - 1]
                self._ensure_node_visible(self.selected_node)
                self.rebuild_ui()
        except ValueError:
            pass

    def _navigate_down(self):
        """Navigate to next visible node"""
        try:
            current_index = self.visible_nodes.index(self.selected_node)
            if current_index < len(self.visible_nodes) - 1:
                self.selected_node = self.visible_nodes[current_index + 1]
                self._ensure_node_visible(self.selected_node)
                self.rebuild_ui()
        except ValueError:
            pass

    def _ensure_node_visible(self, node: HierarchyNode):
        """Ensure a node is visible by adjusting scroll"""
        try:
            node_index = self.visible_nodes.index(node)
            node_y = node_index * self.config.layout.node_height

            margin = self.config.interaction.scroll_margin

            if node_y - margin < self.scroll_y:
                self.scroll_y = max(0, node_y - margin)
            elif node_y + self.config.layout.node_height + margin > self.scroll_y + self.rect.height:
                self.scroll_y = min(self.max_scroll,
                                    node_y + self.config.layout.node_height + margin - self.rect.height)
        except ValueError:
            pass

    def _update_drop_target(self, mouse_pos: tuple):
        """Update drop target based on mouse position"""
        self.drop_target = None
        self.drop_position = 0
        self.is_valid_drop = False

        for node_ui in self.node_uis:
            if node_ui.rect.collidepoint(mouse_pos):
                relative_y = (mouse_pos[1] - node_ui.rect.y) / node_ui.rect.height
                drop_ratio = self.config.interaction.drop_zone_ratio

                if relative_y < drop_ratio:
                    # Drop before
                    self.drop_position = 0
                elif relative_y > 1 - drop_ratio:
                    # Drop after
                    self.drop_position = 2
                else:
                    # Drop as child
                    self.drop_position = 1

                self.drop_target = node_ui.node
                self.is_valid_drop = self._is_valid_drop_target(self.drop_target, self.drop_position)

                # Update UI state
                for ui in self.node_uis:
                    ui.is_drop_target = False
                    ui.is_invalid_drop_target = False

                if self.is_valid_drop:
                    node_ui.is_drop_target = True
                else:
                    node_ui.is_invalid_drop_target = True

                node_ui.drop_position = self.drop_position
                break

    def _perform_drop_operation(self):
        """Perform the actual drop operation"""
        if not self.dragging_node or not self.drop_target:
            return

        # Remove from current parent
        if self.dragging_node.parent:
            self.dragging_node.parent.remove_child(self.dragging_node)

        # Add to new location
        if self.drop_position == 1:  # As child
            self.drop_target.add_child(self.dragging_node)
        else:  # Before or after
            target_parent = self.drop_target.parent
            if target_parent:
                target_index = target_parent.children.index(self.drop_target)
                if self.drop_position == 2:  # After
                    target_index += 1
                target_parent.children.insert(target_index, self.dragging_node)
                self.dragging_node.parent = target_parent

    def get_selected_node(self) -> Optional[HierarchyNode]:
        """Get the currently selected node"""
        return self.selected_node

    def set_selected_node(self, node: Optional[HierarchyNode]):
        """Set the selected node"""
        if self.selected_node != node:
            old_selected = self.selected_node
            self.selected_node = node

            if old_selected:
                deselect_event = pygame.event.Event(UI_HIERARCHY_NODE_DESELECTED, {
                    'node_id': old_selected.id,
                    'ui_element': self
                })
                pygame.event.post(deselect_event)

            if node:
                select_event = pygame.event.Event(UI_HIERARCHY_NODE_SELECTED, {
                    'node_id': node.id,
                    'ui_element': self
                })
                pygame.event.post(select_event)

            self.rebuild_ui()

    def expand_all(self):
        """Expand all nodes in the hierarchy"""

        def expand_recursive(node: HierarchyNode):
            node.expanded = True
            for child in node.children:
                expand_recursive(child)

        expand_recursive(self.root_node)
        self.rebuild_ui()

    def collapse_all(self):
        """Collapse all nodes in the hierarchy"""

        def collapse_recursive(node: HierarchyNode):
            node.expanded = False
            for child in node.children:
                collapse_recursive(child)

        collapse_recursive(self.root_node)
        self.rebuild_ui()

    def load_icons_from_directory(self, directory_path: str):
        """Load custom icons from a directory"""
        if not os.path.exists(directory_path):
            return

        for filename in os.listdir(directory_path):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                icon_name = os.path.splitext(filename)[0]
                icon_path = os.path.join(directory_path, filename)

                try:
                    surface = pygame.image.load(icon_path).convert_alpha()
                    scaled_surface = pygame.transform.scale(surface, self.config.layout.icon_size)
                    self.icon_manager.icon_cache[icon_name] = scaled_surface
                except Exception as e:
                    if HIERARCHY_DEBUG:
                        print(f"Failed to load icon {icon_path}: {e}")


########################################################################################################################
def create_sample_hierarchy():
    """Create a sample hierarchy for demonstration"""
    root = HierarchyNode("root", "Project Files", HierarchyNodeType.ROOT)

    # Create folders
    folder1 = HierarchyNode("folder1", "Documents", HierarchyNodeType.FOLDER, icon_name="folder")
    folder2 = HierarchyNode("folder2", "Images", HierarchyNodeType.FOLDER, icon_name="folder")
    folder3 = HierarchyNode("folder3", "Source Code", HierarchyNodeType.FOLDER, icon_name="code")

    # Create items
    item1 = HierarchyNode("item1", "readme.txt", HierarchyNodeType.ITEM, icon_name="text")
    item2 = HierarchyNode("item2", "photo.jpg", HierarchyNodeType.ITEM, icon_name="image")
    item3 = HierarchyNode("item3", "main.py", HierarchyNodeType.ITEM, icon_name="python")
    item4 = HierarchyNode("item4", "config.json", HierarchyNodeType.ITEM, icon_name="json")

    root.add_child(folder1)
    root.add_child(folder2)
    root.add_child(folder3)

    folder1.add_child(item1)
    folder1.add_child(item4)
    folder2.add_child(item2)
    folder3.add_child(item3)

    # Add nested folder
    subfolder = HierarchyNode("subfolder1", "Python Scripts", HierarchyNodeType.FOLDER, icon_name="python_folder")
    nested_item = HierarchyNode("nested1", "utils.py", HierarchyNodeType.ITEM, icon_name="python")
    subfolder.add_child(nested_item)
    folder3.add_child(subfolder)

    return root


def main():
    """Example: demonstration of the configurable Hierarchy Panel"""
    pygame.init()
    screen = pygame.display.set_mode((1200, 800))
    pygame.display.set_caption("Configurable Hierarchy Panel Demo")
    clock = pygame.time.Clock()

    # Create manager
    manager = pygame_gui.UIManager((1200, 800))

    # Create hierarchy data
    root_node = create_sample_hierarchy()

    if HIERARCHY_DEBUG:
        print(f"Created hierarchy with root: {root_node.name}, children: {len(root_node.children)}")

    # Example 1: Compact layout with small icons
    compact_layout = HierarchyLayoutConfig(
        node_height=20,
        indent_size=15,
        icon_size=(12, 12),
        expand_button_size=8,
        expand_button_triangle_size=3,
        icon_margin_with_button=15,
        icon_margin_without_button=3,
        text_margin_left=3,
        focus_border_width=1,
        fallback_font_size=12
    )

    compact_interaction = HierarchyInteractionConfig(
        double_click_time=400,
        drop_zone_ratio=0.2,
        scroll_speed=2
    )

    compact_config = HierarchyConfig(
        layout=compact_layout,
        interaction=compact_interaction,
        show_root=False,
        allow_drag=True,
        allow_drop=True
    )

    # Example 2: Large layout with big icons
    large_layout = HierarchyLayoutConfig(
        node_height=40,
        indent_size=30,
        icon_size=(24, 24),
        expand_button_size=16,
        expand_button_triangle_size=6,
        icon_margin_with_button=25,
        icon_margin_without_button=8,
        text_margin_left=8,
        focus_border_width=3,
        drop_line_width=4,
        fallback_font_size=16
    )

    large_interaction = HierarchyInteractionConfig(
        double_click_time=600,
        drop_zone_ratio=0.35,
        scroll_speed=5
    )

    large_config = HierarchyConfig(
        layout=large_layout,
        interaction=large_interaction,
        show_root=True,
        allow_drag=True,
        allow_drop=True,
        folders_only_have_children=True
    )

    # Example 3: Custom themed layout
    custom_layout = HierarchyLayoutConfig(
        node_height=28,
        indent_size=22,
        icon_size=(18, 18),
        expand_button_size=14,
        expand_button_triangle_size=5,
        icon_margin_with_button=22,
        icon_margin_without_button=6,
        text_margin_left=6,
        focus_border_width=2,
        drop_line_width=3
    )

    custom_interaction = HierarchyInteractionConfig(
        double_click_time=500,
        drop_zone_ratio=0.25,
        scroll_speed=4,
        scroll_margin=15
    )

    custom_config = HierarchyConfig(
        layout=custom_layout,
        interaction=custom_interaction,
        show_root=False,
        allow_drag=True,
        allow_drop=True
    )

    # Create three hierarchy panels with different configurations
    hierarchy_compact = HierarchyPanel(
        pygame.Rect(50, 50, 300, 300),
        manager,
        create_sample_hierarchy(),  # Each panel gets its own copy
        compact_config,
        object_id=ObjectID(object_id='#compact_hierarchy', class_id='compact_hierarchy')
    )

    hierarchy_large = HierarchyPanel(
        pygame.Rect(400, 50, 350, 200),
        manager,
        create_sample_hierarchy(),
        large_config,
        object_id=ObjectID(object_id='#large_hierarchy', class_id='large_hierarchy')
    )

    hierarchy_custom = HierarchyPanel(
        pygame.Rect(800, 50, 320, 350),
        manager,
        create_sample_hierarchy(),
        custom_config,
        object_id=ObjectID(object_id='#custom_hierarchy', class_id='custom_hierarchy')
    )

    # Load custom icons if available
    if os.path.exists("icons"):
        hierarchy_compact.load_icons_from_directory("icons")
        hierarchy_large.load_icons_from_directory("icons")
        hierarchy_custom.load_icons_from_directory("icons")

    # Create labels to describe each panel
    compact_label = pygame_gui.elements.UILabel(
        pygame.Rect(50, 20, 300, 25),
        "Compact Layout (20px height, 12px icons)",
        manager
    )

    large_label = pygame_gui.elements.UILabel(
        pygame.Rect(400, 20, 350, 25),
        "Large Layout (40px height, 24px icons)",
        manager
    )

    custom_label = pygame_gui.elements.UILabel(
        pygame.Rect(800, 20, 320, 25),
        "Custom Layout (28px height, 18px icons)",
        manager
    )

    # Configuration display
    config_display = pygame_gui.elements.UITextBox(
        """<b>Configuration Examples:</b><br>
        <b>Compact:</b> 20px nodes, 15px indent, 12px icons<br>
        <b>Large:</b> 40px nodes, 30px indent, 24px icons<br>
        <b>Custom:</b> 28px nodes, 22px indent, 18px icons<br><br>
        <b>Features Demonstrated:</b><br>
        - Configurable node heights and indentation<br>
        - Adjustable icon sizes and positioning<br>
        - Customizable interaction timing<br>
        - Flexible drag & drop zones<br>
        - Variable scroll speeds<br>
        - Different expand button sizes<br>
        - Configurable border widths<br><br>
        <b>Try:</b> Click nodes, expand/collapse, drag & drop!""",
        pygame.Rect(50, 480, 800, 200),
        manager
    )

    # Add instructions
    print("\nConfigurable Hierarchy Panel Demo")
    print("\nThree panels showing different configurations:")
    print("1. Compact - Small, dense layout")
    print("2. Large - Spacious layout with big icons")
    print("3. Custom - Medium layout with custom spacing")
    print("\nFeatures:")
    print("- All layout constants are now configurable")
    print("- Node heights, indentation, and icon sizes")
    print("- Expand button sizes and triangle sizes")
    print("- Text and icon positioning margins")
    print("- Border widths and drop line widths")
    print("- Interaction timing (double-click, drag zones)")
    print("- Scroll speeds and margins")
    print("\nControls:")
    print("- Click to select nodes")
    print("- Double-click to trigger double-click events")
    print("- Click expand buttons to expand/collapse")
    print("- Drag and drop to reorder (where allowed)")
    print("- Mouse wheel to scroll")
    print("- Arrow keys for keyboard navigation (when focused)")

    running = True
    while running:
        time_delta = clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # Handle custom hierarchy events - Fixed event data access
            elif event.type == UI_HIERARCHY_NODE_SELECTED:
                # Access event data via event.dict or direct dictionary access
                event_data = getattr(event, 'dict', {})
                node_id = event_data.get('node_id', 'unknown')
                print(f"Node selected: {node_id}")

            elif event.type == UI_HIERARCHY_NODE_DOUBLE_CLICKED:
                event_data = getattr(event, 'dict', {})
                node_id = event_data.get('node_id', 'unknown')
                print(f"Node double-clicked: {node_id}")

            elif event.type == UI_HIERARCHY_NODE_EXPANDED:
                event_data = getattr(event, 'dict', {})
                node_id = event_data.get('node_id', 'unknown')
                expanded = event_data.get('expanded', 'unknown')
                print(f"Node expanded: {node_id} (expanded: {expanded})")

            elif event.type == UI_HIERARCHY_NODE_COLLAPSED:
                event_data = getattr(event, 'dict', {})
                node_id = event_data.get('node_id', 'unknown')
                expanded = event_data.get('expanded', 'unknown')
                print(f"Node collapsed: {node_id} (expanded: {expanded})")

            elif event.type == UI_HIERARCHY_DRAG_STARTED:
                event_data = getattr(event, 'dict', {})
                node_id = event_data.get('node_id', 'unknown')
                print(f"Drag started: {node_id}")

            elif event.type == UI_HIERARCHY_DROP_COMPLETED:
                event_data = getattr(event, 'dict', {})
                dragged_node_id = event_data.get('dragged_node_id', 'unknown')
                target_node_id = event_data.get('target_node_id', 'unknown')
                drop_position = event_data.get('drop_position', 'unknown')
                print(f"Drop completed: {dragged_node_id} -> {target_node_id} (position: {drop_position})")

            manager.process_events(event)

        manager.update(time_delta)

        # Render
        screen.fill((30, 30, 30))
        manager.draw_ui(screen)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
