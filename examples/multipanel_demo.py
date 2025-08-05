import pygame
import pygame_gui
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Protocol
from pathlib import Path
import time

from pygame import Rect

# Import all the panel classes and their configurations

# TODO: Fix Docking System and implement it here. Make Timeline/Console tabs in same panel.
# from pygame_gui_extensions.docking_system import DockingManager, DockingConfig, DockDirection

from pygame_gui_extensions.asset_browser_panel import AssetBrowserPanel, AssetConfig, AssetItem, AssetType, \
    AssetMetadata
from pygame_gui_extensions.console_panel import ConsolePanel, ConsoleConfig
from pygame_gui_extensions.hierarchy_panel import HierarchyPanel, HierarchyConfig, HierarchyNode, HierarchyNodeType
from pygame_gui_extensions.navigator_panel import NavigatorPanel, NavigatorConfig, NavigatorViewport
from pygame_gui_extensions.node_editor_panel import NodeEditorPanel, NodeEditorConfig, Node, NodeGraph, NodeType
from pygame_gui_extensions.property_panel import PropertyPanel, PropertyConfig, PropertySchema, PropertyType
from pygame_gui_extensions.timeline_panel import (TimelinePanel, TimelineConfig, Keyframe, AnimationClip,
                                                  AnimationLayer, AnimationCurve, LayerType, InterpolationType)
from pygame_gui_extensions.tool_panel import ToolPalettePanel, ToolPaletteConfig, Tool, ToolType, ToolGroup


# Shared data model that all panels will interact with
@dataclass
class SceneObject:
    """A simple 3D object that all panels can manipulate"""
    id: str
    name: str = "Cube"
    position: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    rotation: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    scale: List[float] = field(default_factory=lambda: [1.0, 1.0, 1.0])
    color: List[int] = field(default_factory=lambda: [255, 255, 255])
    visible: bool = True
    locked: bool = False
    material: str = "Default"
    tags: List[str] = field(default_factory=list)

    # Animation keyframes (simple position animation)
    keyframes: Dict[int, List[float]] = field(default_factory=dict)

    def __post_init__(self):
        # Add some default keyframes
        if not self.keyframes:
            self.keyframes = {
                0: self.position.copy(),
                30: [self.position[0] + 2.0, self.position[1], self.position[2]],
                60: self.position.copy()
            }


class SceneDataModel:
    """Central data model that all panels share"""

    def __init__(self):
        self.objects: Dict[str, SceneObject] = {}
        self.selected_object_id: Optional[str] = None
        self.current_frame: int = 0
        self.playing: bool = False
        self.observers: List = []

        # Create some default objects
        self.add_object(SceneObject("cube1", "My Cube", [0, 0, 0]))
        self.add_object(SceneObject("sphere1", "My Sphere", [3, 0, 0]))
        self.add_object(SceneObject("camera1", "Main Camera", [0, 2, 5]))

        # Select the first object
        self.selected_object_id = "cube1"

    def add_object(self, obj: SceneObject):
        """Add an object to the scene"""
        self.objects[obj.id] = obj
        self._notify_observers("object_added", obj.id)

    def remove_object(self, obj_id: str):
        """Remove an object from the scene"""
        if obj_id in self.objects:
            del self.objects[obj_id]
            if self.selected_object_id == obj_id:
                self.selected_object_id = None
            self._notify_observers("object_removed", obj_id)

    def select_object(self, obj_id: str):
        """Select an object"""
        if obj_id in self.objects:
            self.selected_object_id = obj_id
            self._notify_observers("selection_changed", obj_id)

    def get_selected_object(self) -> Optional[SceneObject]:
        """Get the currently selected object"""
        if self.selected_object_id:
            return self.objects.get(self.selected_object_id)
        return None

    def update_object_property(self, obj_id: str, prop_name: str, value: Any):
        """Update a property of an object"""
        if obj_id in self.objects:
            obj = self.objects[obj_id]
            if hasattr(obj, prop_name):
                setattr(obj, prop_name, value)
                self._notify_observers("property_changed", obj_id, prop_name, value)

    def set_current_frame(self, frame: int):
        """Set the current animation frame"""
        self.current_frame = frame
        self._notify_observers("frame_changed", frame)

    def add_observer(self, observer):
        """Add an observer for data changes"""
        self.observers.append(observer)

    def _notify_observers(self, event_type: str, *args):
        """Notify all observers of a data change"""
        for observer in self.observers:
            if hasattr(observer, 'on_data_changed'):
                observer.on_data_changed(event_type, *args)


class PanelDemoApp:
    """Main application that demonstrates all panels working together"""

    def __init__(self):
        pygame.init()
        self.screen_size = (1300, 850)
        self.screen = pygame.display.set_mode(self.screen_size)
        pygame.display.set_caption("Multi-Panel Demo - All Panels Working Together")
        self.clock = pygame.time.Clock()

        # Create UI manager
        self.manager = pygame_gui.UIManager(self.screen_size)

        # Create shared data model
        self.data_model = SceneDataModel()

        # Initialize all panels
        self._create_panels()
        self._setup_panel_interactions()

        print("Multi-Panel Demo Initialized!")

    def _create_panels(self):
        """Create and dock all panels"""

        # 1. Hierarchy Panel - left side, taller
        hierarchy_root = self._create_hierarchy_from_scene()
        self.hierarchy_panel = HierarchyPanel(
            pygame.Rect(10, 10, 220, 350),  # Made wider and taller
            self.manager,
            hierarchy_root,
            HierarchyConfig()
        )

        # 2. Property Panel - below hierarchy, taller
        self.property_panel = PropertyPanel(
            pygame.Rect(10, 370, 220, 350),  # Made taller
            self.manager,
            PropertyConfig()
        )

        # 3. Node Editor Panel - center, SMALLER
        self.node_editor_panel = NodeEditorPanel(
            pygame.Rect(240, 10, 700, 450),  # Much smaller height
            self.manager,
            NodeEditorConfig()
        )

        # 4. Asset Browser - right side top
        self.asset_panel = AssetBrowserPanel(
            pygame.Rect(950, 10, 340, 280),  # Adjusted for smaller width
            self.manager,
            AssetConfig()
        )

        # 5. Tool Panel - right side middle
        self.tool_panel = ToolPalettePanel(
            pygame.Rect(950, 300, 340, 360),  # More space
            self.manager,
            ToolPaletteConfig()
        )

        # 6. Navigator Panel - right bottom
        viewport = NavigatorViewport(0, 0, 100, 100, 1.0, 200, 200)
        self.navigator_panel = NavigatorPanel(
            pygame.Rect(950, 670, 340, 180),  # Bigger navigator
            self.manager,
            self._create_navigator_provider(),
            viewport,
            NavigatorConfig()
        )

        # 7. Timeline Panel - bottom spanning width, bigger
        self.timeline_panel = TimelinePanel(
            pygame.Rect(240, 470, 700, 200),  # More height for timeline
            self.manager,
            TimelineConfig()
        )

        # 8. Console Panel - bottom, bigger
        self.console_panel = ConsolePanel(
            pygame.Rect(240, 680, 700, 150),  # Bigger console
            self.manager,
            ConsoleConfig()
        )

        self.data_model.add_observer(self.hierarchy_panel)
        self.data_model.add_observer(self.property_panel)
        self.data_model.add_observer(self.timeline_panel)
        self._setup_property_panel()
        self._setup_timeline_panel()
        self._setup_asset_panel()
        self._setup_tool_panel()
        self._setup_console_panel()
        self._setup_node_editor_panel()

    def _create_hierarchy_from_scene(self):
        """Create hierarchy structure from scene objects"""
        root = HierarchyNode("root", "Scene", HierarchyNodeType.ROOT)

        for obj_id, obj in self.data_model.objects.items():
            node = HierarchyNode(obj_id, obj.name, HierarchyNodeType.ITEM)
            root.add_child(node)

        return root

    def _setup_property_panel(self):
        """Configure property panel with object properties"""

        def on_property_changed(prop_id: str, old_value: Any, new_value: Any):
            """Handle property changes"""
            obj = self.data_model.get_selected_object()
            if obj and hasattr(obj, prop_id):
                self.data_model.update_object_property(obj.id, prop_id, new_value)

        self.property_panel.change_callback = on_property_changed
        self._update_property_panel()

    def _update_property_panel(self):
        """Update property panel with selected object properties"""
        obj = self.data_model.get_selected_object()
        if not obj:
            self.property_panel.clear_properties()
            return

        # Create property schemas for the selected object
        properties = [
            PropertySchema("name", "Name", PropertyType.TEXT, obj.name),
            PropertySchema("position", "Position", PropertyType.VECTOR3, obj.position),
            PropertySchema("rotation", "Rotation", PropertyType.VECTOR3, obj.rotation),
            PropertySchema("scale", "Scale", PropertyType.VECTOR3, obj.scale),
            PropertySchema("visible", "Visible", PropertyType.BOOLEAN, obj.visible),
            PropertySchema("locked", "Locked", PropertyType.BOOLEAN, obj.locked),
            PropertySchema("material", "Material", PropertyType.DROPDOWN, obj.material,
                           options=["Default", "Metal", "Plastic", "Glass", "Wood"]),
        ]

        self.property_panel.set_properties(properties, obj)

    def _setup_timeline_panel(self):
        """Configure timeline panel with object animation"""
        # Create an animation clip
        clip = AnimationClip("Scene Animation", length=120, fps=30.0)

        # Get the selected object for animation setup
        obj = self.data_model.get_selected_object()
        if obj:
            # Create a position animation layer
            position_layer = AnimationLayer("position", "Position", LayerType.TRANSFORM)

            # Create animation curves for X, Y, Z position
            for i, axis in enumerate(['x', 'y', 'z']):
                curve = AnimationCurve(f"position_{axis}", default_value=obj.position[i])

                # Add keyframes from the object's keyframe data
                for frame, pos in obj.keyframes.items():
                    keyframe = Keyframe(frame, pos[i], InterpolationType.LINEAR)
                    curve.add_keyframe(keyframe)

                position_layer.add_curve(curve)

            # Add the layer to the clip
            clip.add_layer(position_layer)

        # Set the clip on the timeline panel
        if hasattr(self.timeline_panel, 'set_clip'):
            self.timeline_panel.set_clip(clip)
        elif hasattr(self.timeline_panel, 'clip'):
            self.timeline_panel.clip = clip

    def _setup_asset_panel(self):
        """Configure asset panel with materials and objects"""
        # Create collections first
        materials_collection = self.asset_panel.add_collection("Materials", "Material assets")

        # Create sample material assets directly (following the pattern from the asset browser demo)
        sample_materials = [
            ("metal.mat", AssetType.MATERIAL, "Metal Material"),
            ("plastic.mat", AssetType.MATERIAL, "Plastic Material"),
            ("glass.mat", AssetType.MATERIAL, "Glass Material"),
            ("wood.mat", AssetType.MATERIAL, "Wood Material"),
        ]

        for filename, asset_type, display_name in sample_materials:
            # Create temporary file path (these would be actual files in real usage)
            temp_path = Path(f"temp_materials/{filename}")

            # Create fake metadata
            metadata = AssetMetadata()
            metadata.file_size = hash(filename) % 10000 + 1000  # Fake file size
            metadata.date_created = time.time() - (hash(filename) % 10000)
            metadata.date_modified = time.time() - (hash(filename) % 5000)
            metadata.description = f"A {display_name.lower()} for 3D objects"
            metadata.tags.add("material")
            metadata.tags.add(display_name.split()[0].lower())

            # Generate asset ID and create asset item directly
            asset_id = self.asset_panel.generate_asset_id(temp_path)
            asset = AssetItem(
                id=asset_id,
                name=Path(filename).stem,
                file_path=temp_path,
                asset_type=asset_type,
                metadata=metadata,
                collection_id=materials_collection.id
            )

            # Add asset directly to the browser's assets dictionary
            self.asset_panel.assets[asset_id] = asset

            # Add to collection
            materials_collection.add_asset(asset_id)

        # Force rebuild to show assets
        self.asset_panel._force_rebuild = True
        self.asset_panel.rebuild_ui()
        self.asset_panel.rebuild_image()

    def _setup_tool_panel(self):
        """Configure tool panel with object manipulation tools"""
        # Create tool groups
        transform_group = ToolGroup("transform", "Transform Tools")
        modeling_group = ToolGroup("modeling", "Modeling Tools")

        # Transform tools - using MODIFICATION type instead of TRANSFORM
        transform_tools = [
            Tool("move", "Move", "Move objects in 3D space", ToolType.MODIFICATION, "Transform", "G"),
            Tool("rotate", "Rotate", "Rotate objects", ToolType.MODIFICATION, "Transform", "R"),
            Tool("scale", "Scale", "Scale objects", ToolType.MODIFICATION, "Transform", "S"),
        ]

        # Modeling tools
        modeling_tools = [
            Tool("duplicate", "Duplicate", "Duplicate selected object", ToolType.CREATION, "Modeling", "Ctrl+D"),
            Tool("delete", "Delete", "Delete selected object", ToolType.MODIFICATION, "Modeling", "X"),
            Tool("reset", "Reset Transform", "Reset object transform", ToolType.ACTION, "Modeling", "Alt+R"),
        ]

        for tool in transform_tools:
            transform_group.add_tool(tool)
        for tool in modeling_tools:
            modeling_group.add_tool(tool)

        self.tool_panel.add_group(transform_group)
        self.tool_panel.add_group(modeling_group)

    def _setup_console_panel(self):
        """Configure console panel with object commands"""

        def move_object_command(args):
            """Command to move an object"""
            if len(args) < 4:
                return "Usage: move_object <object_id> <x> <y> <z>"

            obj_id, x, y, z = args[0], float(args[1]), float(args[2]), float(args[3])
            if obj_id in self.data_model.objects:
                self.data_model.update_object_property(obj_id, "position", [x, y, z])
                return f"Moved {obj_id} to ({x}, {y}, {z})"
            return f"Object {obj_id} not found"

        def list_objects_command(args):
            """Command to list all objects"""
            if not self.data_model.objects:
                return "No objects in scene"

            result = "Scene Objects:\n"
            for obj_id, obj in self.data_model.objects.items():
                pos = obj.position
                result += f"  {obj_id}: {obj.name} at ({pos[0]:.1f}, {pos[1]:.1f}, {pos[2]:.1f})\n"
            return result.strip()

        def select_object_command(args):
            """Command to select an object"""
            if len(args) < 1:
                return "Usage: select_object <object_id>"

            obj_id = args[0]
            if obj_id in self.data_model.objects:
                self.data_model.select_object(obj_id)
                return f"Selected {obj_id}"
            return f"Object {obj_id} not found"

        # Register commands
        if hasattr(self.console_panel.command_handler, 'register_command'):
            self.console_panel.command_handler.register_command("move_object", move_object_command)
            self.console_panel.command_handler.register_command("list_objects", list_objects_command)
            self.console_panel.command_handler.register_command("select_object", select_object_command)

    def _create_navigator_provider(self):
        """Create a simple content provider for the navigator"""
        data_model = self.data_model  # Capture reference to data model

        # Import the proper base class if needed
        try:
            from pygame_gui_extensions.navigator_panel import ContentProvider
            base_class = ContentProvider
        except ImportError:
            # Fallback to object if ContentProvider not available
            ContentProvider = Protocol
            base_class = ContentProvider

        class SceneContentProvider(base_class):
            @staticmethod
            def get_content_size() -> tuple[float, float]:
                return 200, 200

            @staticmethod
            def render_content(surface, rect):
                # Simple visualization of scene objects
                surface.fill((50, 50, 50))

                # Draw objects as colored rectangles
                colors = [(255, 100, 100), (100, 255, 100), (100, 100, 255)]
                for i, (obj_id, obj) in enumerate(data_model.objects.items()):
                    if obj.visible:
                        color = colors[i % len(colors)]
                        x = int(obj.position[0] * 10 + rect.width // 2)
                        y = int(obj.position[2] * 10 + rect.height // 2)
                        pygame.draw.circle(surface, color, (x, y), 5)

            @staticmethod
            def get_selection_bounds() -> Rect | None:
                """Return bounds of current selection, if any"""
                obj = data_model.get_selected_object()
                if obj:
                    x = int(obj.position[0] * 10 + 100)  # 100 = rect.width // 2
                    y = int(obj.position[2] * 10 + 100)  # 100 = rect.height // 2
                    return pygame.Rect(x - 10, y - 10, 20, 20)
                return None

        return SceneContentProvider()

    def _setup_node_editor_panel(self):
        """Configure node editor with object relationships"""
        # Create a simple node graph showing object relationships
        graph = NodeGraph()

        # Create nodes for each scene object
        for obj_id, obj in self.data_model.objects.items():
            node = Node(obj_id, obj.name, NodeType.BASIC, position=(int(obj.position[0] * 20), int(obj.position[2] * 20)))
            graph.add_node(node)

        if hasattr(self.node_editor_panel, 'set_graph'):
            self.node_editor_panel.set_graph(graph)

    def _setup_panel_interactions(self):
        """Set up interactions between panels"""

        # Make hierarchy panel notify about selections
        def on_hierarchy_selection(node_id):
            if node_id in self.data_model.objects:
                self.data_model.select_object(node_id)

        if hasattr(self.hierarchy_panel, 'selection_callback'):
            self.hierarchy_panel.selection_callback = on_hierarchy_selection

        # Make asset panel apply materials to selected objects
        def on_asset_applied(asset_id):
            obj = self.data_model.get_selected_object()
            if obj and asset_id in self.asset_panel.assets:
                asset = self.asset_panel.assets[asset_id]
                if asset.asset_type == AssetType.MATERIAL:
                    material_name = asset.name.title()
                    self.data_model.update_object_property(obj.id, "material", material_name)

        if hasattr(self.asset_panel, 'asset_applied_callback'):
            self.asset_panel.asset_applied_callback = on_asset_applied

        # Make tool panel execute actions on selected objects
        def on_tool_activated(tool_id):
            obj = self.data_model.get_selected_object()
            if not obj:
                return

            if tool_id == "duplicate":
                new_obj = SceneObject(f"{obj.id}_copy", f"{obj.name} Copy")
                new_obj.position = [obj.position[0] + 1, obj.position[1], obj.position[2]]
                self.data_model.add_object(new_obj)
            elif tool_id == "delete":
                self.data_model.remove_object(obj.id)
            elif tool_id == "reset":
                self.data_model.update_object_property(obj.id, "position", [0.0, 0.0, 0.0])
                self.data_model.update_object_property(obj.id, "rotation", [0.0, 0.0, 0.0])
                self.data_model.update_object_property(obj.id, "scale", [1.0, 1.0, 1.0])

        if hasattr(self.tool_panel, 'tool_activated_callback'):
            self.tool_panel.tool_activated_callback = on_tool_activated

    def on_data_changed(self, event_type: str, *args):
        """Handle data model changes (implementation for all panels)"""
        if event_type == "selection_changed":
            self._update_property_panel()
            # Update other panels as needed
        elif event_type == "property_changed":
            # Refresh displays
            if hasattr(self, 'navigator_panel'):
                self.navigator_panel.refresh()
        elif event_type == "object_added" or event_type == "object_removed":
            # Rebuild hierarchy
            self._update_hierarchy()

    def _update_hierarchy(self):
        """Update hierarchy panel structure"""
        new_root = self._create_hierarchy_from_scene()
        if hasattr(self.hierarchy_panel, 'set_root_node'):
            self.hierarchy_panel.set_root_node(new_root)

    def run(self):
        """Main application loop"""
        running = True

        while running:
            time_delta = self.clock.tick(60) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False

                # Process UI events
                self.manager.process_events(event)

            # Update UI
            self.manager.update(time_delta)

            # Draw everything
            self.screen.fill((30, 30, 30))
            self.manager.draw_ui(self.screen)

            pygame.display.flip()

        pygame.quit()


def main():
    """Run the multi-panel demo"""
    app = PanelDemoApp()
    app.run()


if __name__ == "__main__":
    main()