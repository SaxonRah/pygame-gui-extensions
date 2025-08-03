import pygame
import pygame_gui
import math
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import copy

# Import the provided UI panels
from pygame_gui_extensions.hierarchy_panel import (
    HierarchyPanel, HierarchyNode, HierarchyNodeType, HierarchyConfig,
    UI_HIERARCHY_NODE_SELECTED, UI_HIERARCHY_NODE_DESELECTED
)

from pygame_gui_extensions.property_panel import (
    PropertyPanel, PropertySchema, PropertyType, PropertyConfig,
    UI_PROPERTY_CHANGED
)

from pygame_gui_extensions.timeline_panel import (
    TimelinePanel, AnimationClip, AnimationLayer, AnimationCurve, Keyframe,
    InterpolationType, LayerType, TimelineConfig,
    UI_TIMELINE_FRAME_CHANGED, UI_TIMELINE_KEYFRAME_ADDED, PlaybackState
)

SKELETON_DEBUG = True


@dataclass
class Bone:
    """Represents a bone in the skeleton with 2D transform properties"""
    id: str
    name: str
    length: float = 50.0

    # Transform properties
    position_x: float = 0.0
    position_y: float = 0.0
    rotation: float = 0.0  # in degrees

    # Visual properties
    thickness: float = 4.0
    color: pygame.Color = None

    # Hierarchy
    parent: Optional['Bone'] = None
    children: List['Bone'] = None

    # Animation data
    animated_properties: Dict[str, Any] = None

    def __post_init__(self):
        if self.children is None:
            self.children = []
        if self.color is None:
            self.color = pygame.Color(255, 255, 255)
        if self.animated_properties is None:
            self.animated_properties = {}

    def add_child(self, child_bone: 'Bone'):
        """Add a child bone"""
        if child_bone not in self.children:
            child_bone.parent = self
            self.children.append(child_bone)

    def remove_child(self, child_bone: 'Bone'):
        """Remove a child bone"""
        if child_bone in self.children:
            child_bone.parent = None
            self.children.remove(child_bone)

    def get_world_position(self) -> Tuple[float, float]:
        """Get the world position of this bone's start"""
        if self.parent is None:
            return self.position_x, self.position_y

        # Get parent's end position
        parent_world_pos = self.parent.get_world_end_position()
        return parent_world_pos[0] + self.position_x, parent_world_pos[1] + self.position_y

    def get_world_end_position(self) -> Tuple[float, float]:
        """Get the world position of this bone's end"""
        start_x, start_y = self.get_world_position()

        # Calculate end position based on rotation and length
        angle_rad = math.radians(self.rotation)
        end_x = start_x + math.cos(angle_rad) * self.length
        end_y = start_y + math.sin(angle_rad) * self.length

        return end_x, end_y

    def get_world_rotation(self) -> float:
        """Get the world rotation of this bone"""
        if self.parent is None:
            return self.rotation

        return self.parent.get_world_rotation() + self.rotation

    def apply_animation_frame(self, frame: float, animation_clip: AnimationClip):
        """Apply animation values from the given frame"""
        if not animation_clip:
            return

        # Find layer for this bone
        layer = animation_clip.get_layer(self.id)
        if not layer:
            return

        # Apply animated properties
        for curve in layer.curves:
            value = curve.get_value_at_frame(frame)
            if value is not None:
                setattr(self, curve.property_name, value)


class SkeletonSystem:
    """Manages the skeleton hierarchy and integrates with UI panels"""

    def __init__(self):
        self.bones: Dict[str, Bone] = {}
        self.root_bones: List[Bone] = []
        self.selected_bone: Optional[Bone] = None

        # Create a simple default skeleton
        self._create_default_skeleton()

    def _create_default_skeleton(self):
        """Create a simple humanoid skeleton for demonstration"""
        # Root/Hip
        hip = Bone("hip", "Hip", length=30, position_x=400, position_y=300,
                   color=pygame.Color(255, 100, 100))

        # Spine
        spine1 = Bone("spine1", "Spine Lower", length=40, rotation=-90,
                      color=pygame.Color(100, 255, 100))
        spine2 = Bone("spine2", "Spine Upper", length=40, rotation=0,
                      color=pygame.Color(100, 255, 100))

        # Left Leg
        left_thigh = Bone("left_thigh", "Left Thigh", length=60, rotation=90,
                          color=pygame.Color(100, 100, 255))
        left_shin = Bone("left_shin", "Left Shin", length=55, rotation=0,
                         color=pygame.Color(150, 150, 255))
        left_foot = Bone("left_foot", "Left Foot", length=25, rotation=-45,
                         color=pygame.Color(200, 200, 255))

        # Right Leg
        right_thigh = Bone("right_thigh", "Right Thigh", length=60, rotation=90,
                           color=pygame.Color(255, 100, 255))
        right_shin = Bone("right_shin", "Right Shin", length=55, rotation=0,
                          color=pygame.Color(255, 150, 255))
        right_foot = Bone("right_foot", "Right Foot", length=25, rotation=-45,
                          color=pygame.Color(255, 200, 255))

        # Left Arm
        left_shoulder = Bone("left_shoulder", "Left Shoulder", length=35, rotation=-45,
                             color=pygame.Color(255, 255, 100))
        left_upper_arm = Bone("left_upper_arm", "Left Upper Arm", length=45, rotation=-30,
                              color=pygame.Color(255, 255, 150))
        left_forearm = Bone("left_forearm", "Left Forearm", length=40, rotation=0,
                            color=pygame.Color(255, 255, 200))

        # Right Arm
        right_shoulder = Bone("right_shoulder", "Right Shoulder", length=35, rotation=45,
                              color=pygame.Color(100, 255, 255))
        right_upper_arm = Bone("right_upper_arm", "Right Upper Arm", length=45, rotation=30,
                               color=pygame.Color(150, 255, 255))
        right_forearm = Bone("right_forearm", "Right Forearm", length=40, rotation=0,
                             color=pygame.Color(200, 255, 255))

        # Head
        neck = Bone("neck", "Neck", length=20, rotation=0,
                    color=pygame.Color(255, 200, 100))
        head = Bone("head", "Head", length=25, rotation=0,
                    color=pygame.Color(255, 220, 150))

        # Build hierarchy
        hip.add_child(spine1)
        hip.add_child(left_thigh)
        hip.add_child(right_thigh)

        spine1.add_child(spine2)
        spine2.add_child(left_shoulder)
        spine2.add_child(right_shoulder)
        spine2.add_child(neck)

        left_thigh.add_child(left_shin)
        left_shin.add_child(left_foot)

        right_thigh.add_child(right_shin)
        right_shin.add_child(right_foot)

        left_shoulder.add_child(left_upper_arm)
        left_upper_arm.add_child(left_forearm)

        right_shoulder.add_child(right_upper_arm)
        right_upper_arm.add_child(right_forearm)

        neck.add_child(head)

        # Add to skeleton
        all_bones = [
            hip, spine1, spine2, left_thigh, left_shin, left_foot,
            right_thigh, right_shin, right_foot, left_shoulder, left_upper_arm,
            left_forearm, right_shoulder, right_upper_arm, right_forearm,
            neck, head
        ]

        for bone in all_bones:
            self.bones[bone.id] = bone

        self.root_bones = [hip]

    def get_bone(self, bone_id: str) -> Optional[Bone]:
        """Get bone by ID"""
        return self.bones.get(bone_id)

    def select_bone(self, bone_id: str):
        """Select a bone"""
        self.selected_bone = self.bones.get(bone_id)

    def deselect_bone(self):
        """Deselect the current bone"""
        self.selected_bone = None

    def create_hierarchy_nodes(self) -> List[HierarchyNode]:
        """Create hierarchy nodes for the hierarchy panel"""

        def create_node(bone: Bone) -> HierarchyNode:
            node = HierarchyNode(
                id=bone.id,
                name=bone.name,
                node_type=HierarchyNodeType.ITEM,
                data={"bone": bone}
            )

            for child_bone in bone.children:
                child_node = create_node(child_bone)
                node.add_child(child_node)

            return node

        # Create root node
        root = HierarchyNode("skeleton_root", "Skeleton", HierarchyNodeType.ROOT)

        for root_bone in self.root_bones:
            bone_node = create_node(root_bone)
            root.add_child(bone_node)

        return [root]

    @staticmethod
    def create_property_schemas(bone: Bone) -> List[PropertySchema]:
        """Create property schemas for the selected bone"""
        if not bone:
            return []

        properties = [
            # Transform section
            PropertySchema(
                id="position_x",
                label="Position X",
                property_type=PropertyType.NUMBER,
                value=bone.position_x,
                default_value=0.0,
                precision=1,
                section="Transform",
                order=0,
                tooltip="X position relative to parent bone"
            ),
            PropertySchema(
                id="position_y",
                label="Position Y",
                property_type=PropertyType.NUMBER,
                value=bone.position_y,
                default_value=0.0,
                precision=1,
                section="Transform",
                order=1,
                tooltip="Y position relative to parent bone"
            ),
            PropertySchema(
                id="rotation",
                label="Rotation",
                property_type=PropertyType.NUMBER,
                value=bone.rotation,
                default_value=0.0,
                min_value=-360.0,
                max_value=360.0,
                precision=1,
                section="Transform",
                order=2,
                tooltip="Rotation in degrees"
            ),
            PropertySchema(
                id="length",
                label="Length",
                property_type=PropertyType.NUMBER,
                value=bone.length,
                default_value=50.0,
                min_value=1.0,
                max_value=200.0,
                precision=1,
                section="Transform",
                order=3,
                tooltip="Length of the bone"
            ),

            # Visual section
            PropertySchema(
                id="thickness",
                label="Thickness",
                property_type=PropertyType.NUMBER,
                value=bone.thickness,
                default_value=4.0,
                min_value=1.0,
                max_value=20.0,
                precision=1,
                section="Visual",
                order=0,
                tooltip="Visual thickness of the bone"
            ),
            PropertySchema(
                id="color",
                label="Color",
                property_type=PropertyType.COLOR,
                value=bone.color,
                default_value=pygame.Color(255, 255, 255),
                section="Visual",
                order=1,
                tooltip="Color of the bone"
            ),

            # Info section
            PropertySchema(
                id="name",
                label="Name",
                property_type=PropertyType.TEXT,
                value=bone.name,
                section="Info",
                order=0,
                tooltip="Name of the bone"
            ),
            PropertySchema(
                id="id",
                label="ID",
                property_type=PropertyType.TEXT,
                value=bone.id,
                section="Info",
                order=1,
                flags=[],  # Keep editable for now
                tooltip="Unique identifier"
            ),
        ]

        return properties

    def create_animation_clip(self) -> AnimationClip:
        """Create animation clip with layers for each bone"""
        clip = AnimationClip("Skeleton Animation", length=120, fps=30.0)

        for bone_id, bone in self.bones.items():
            # Create layer for this bone
            layer = AnimationLayer(bone_id, bone.name, LayerType.TRANSFORM)
            layer.target_object = bone
            layer.visible = True  # Ensure layer is visible
            layer.height = 35  # Set proper height

            # Add curves for animatable properties with current values as defaults
            animatable_props = ["position_x", "position_y", "rotation", "length"]

            for prop_name in animatable_props:
                if hasattr(bone, prop_name):
                    current_value = getattr(bone, prop_name)
                    curve = AnimationCurve(prop_name, default_value=current_value)
                    curve.enabled = True
                    layer.add_curve(curve)

            clip.add_layer(layer)

        return clip

    def apply_animation_frame(self, frame: float, animation_clip: AnimationClip):
        """Apply animation to all bones for the given frame"""
        for bone in self.bones.values():
            bone.apply_animation_frame(frame, animation_clip)


class SkeletonRenderer:
    """Renders the skeleton in 2D"""

    def __init__(self):
        self.show_joints = True
        self.show_bone_names = True
        self.joint_radius = 6
        self.selected_color = pygame.Color(255, 255, 0)
        self.joint_color = pygame.Color(255, 255, 255)

    def draw_skeleton(self, surface: pygame.Surface, skeleton_system: SkeletonSystem):
        """Draw the entire skeleton"""
        # Draw all bones
        for bone in skeleton_system.bones.values():
            self.draw_bone(surface, bone, bone == skeleton_system.selected_bone)

        # Draw joints on top
        if self.show_joints:
            for bone in skeleton_system.bones.values():
                self.draw_joint(surface, bone, bone == skeleton_system.selected_bone)

    def draw_bone(self, surface: pygame.Surface, bone: Bone, is_selected: bool = False):
        """Draw a single bone"""
        start_pos = bone.get_world_position()
        end_pos = bone.get_world_end_position()

        # Choose color
        color = self.selected_color if is_selected else bone.color

        # Draw bone line
        if bone.thickness > 1:
            pygame.draw.line(surface, color, start_pos, end_pos, int(bone.thickness))
        else:
            pygame.draw.line(surface, color, start_pos, end_pos)

        # Draw bone name if enabled
        if self.show_bone_names:
            font = pygame.font.Font(None, 16)
            text_surface = font.render(bone.name, True, color)

            # Position text near the middle of the bone
            mid_x = (start_pos[0] + end_pos[0]) / 2
            mid_y = (start_pos[1] + end_pos[1]) / 2
            text_rect = text_surface.get_rect(center=(mid_x, mid_y - 15))
            surface.blit(text_surface, text_rect)

    def draw_joint(self, surface: pygame.Surface, bone: Bone, is_selected: bool = False):
        """Draw bone joint (start point)"""
        pos = bone.get_world_position()
        color = self.selected_color if is_selected else self.joint_color

        pygame.draw.circle(surface, color, (int(pos[0]), int(pos[1])), self.joint_radius)
        pygame.draw.circle(surface, pygame.Color(0, 0, 0), (int(pos[0]), int(pos[1])), self.joint_radius, 2)

    def get_bone_at_position(self, skeleton_system: SkeletonSystem, pos: Tuple[int, int]) -> Optional[Bone]:
        """Find bone at the given screen position"""
        for bone in skeleton_system.bones.values():
            # Check if click is near bone joint
            bone_pos = bone.get_world_position()
            distance = math.sqrt((pos[0] - bone_pos[0]) ** 2 + (pos[1] - bone_pos[1]) ** 2)

            if distance <= self.joint_radius + 5:  # Add some tolerance
                return bone

            # Check if click is on bone line
            start_pos = bone.get_world_position()
            end_pos = bone.get_world_end_position()

            # Simple line intersection check
            line_distance = self._point_to_line_distance(pos, start_pos, end_pos)
            if line_distance <= bone.thickness / 2 + 3:  # Add tolerance
                return bone

        return None

    @staticmethod
    def _point_to_line_distance(point: Tuple[float, float],
                                line_start: Tuple[float, float],
                                line_end: Tuple[float, float]) -> float:
        """Calculate distance from point to line segment"""
        px, py = point
        x1, y1 = line_start
        x2, y2 = line_end

        # Vector from line start to end
        dx = x2 - x1
        dy = y2 - y1

        if dx == 0 and dy == 0:
            # Line has no length
            return math.sqrt((px - x1) ** 2 + (py - y1) ** 2)

        # Parameter t for closest point on line
        t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
        t = max(0, min(1, t))  # Clamp to line segment

        # Closest point on the line
        closest_x = x1 + t * dx
        closest_y = y1 + t * dy

        # Distance from point to the closest point
        return math.sqrt((px - closest_x) ** 2 + (py - closest_y) ** 2)


class SkeletonAnimationTool:
    """Main application that integrates all UI panels"""

    def __init__(self):
        pygame.init()

        self.screen_width = 1400
        self.screen_height = 900
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Skeleton Animation Tool")

        # UI Manager
        self.ui_manager = pygame_gui.UIManager((self.screen_width, self.screen_height))

        # Core systems
        self.skeleton_system = SkeletonSystem()
        self.skeleton_renderer = SkeletonRenderer()

        # Animation
        self.animation_clip = self.skeleton_system.create_animation_clip()
        self.current_frame = 0.0

        # Create UI panels
        self._create_ui_panels()

        # Setup initial state
        self._update_hierarchy_panel()
        self._update_timeline_panel()
        self._force_timeline_refresh()

        # Set initial frame
        self.timeline_panel.set_current_frame(0.0)
        self.current_frame = 0.0

        # Main loop variables
        self.clock = pygame.time.Clock()
        self.running = True

        print("Skeleton Animation Tool Initialized")
        print("Features:")
        print("- Hierarchical bone system with parent-child relationships")
        print("- Real-time property editing")
        print("- Keyframe animation with interpolation")
        print("- Visual skeleton display")
        print("\nControls:")
        print("- Click bones in viewport to select them")
        print("- Click empty space to deselect")
        print("- Edit bone properties in the property panel")
        print("- Use timeline to create keyframe animations")
        print("- Press 'A' to add keyframe at current frame")
        print("- Press 'R' to reset to bind pose")
        print("- Press 'Space' to play/pause animation")

    def _create_ui_panels(self):
        """Create and position UI panels"""
        # Hierarchy Panel (left side)
        hierarchy_config = HierarchyConfig()
        hierarchy_config.show_root = False
        self.hierarchy_panel = HierarchyPanel(
            pygame.Rect(10, 10, 300, 400),
            self.ui_manager,
            HierarchyNode("root", "Root", HierarchyNodeType.ROOT),
            hierarchy_config
        )

        # Property Panel (left bottom)
        property_config = PropertyConfig()
        self.property_panel = PropertyPanel(
            pygame.Rect(10, 420, 300, 300),
            self.ui_manager,
            property_config
        )

        # Set up property change callback
        self.property_panel.set_change_callback(self._on_property_changed)

        # Timeline Panel (bottom) - with proper configuration
        timeline_config = TimelineConfig()
        timeline_config.layout.layer_height = 40  # Make slightly taller
        timeline_config.layout.controls_height = 40
        timeline_config.layout.scrubber_height = 30
        timeline_config.layout.layer_label_width = 150  # Make wider for bone names
        timeline_config.layout.keyframe_size = 25  # Make keyframes more visible
        timeline_config.behavior.show_frame_numbers = True
        timeline_config.behavior.show_layer_names = True
        timeline_config.behavior.show_grid = True
        timeline_config.behavior.keyframe_shape = "diamond"
        timeline_config.behavior.color_keyframes_by_interpolation = True
        timeline_config.behavior.show_interpolation_curves = True
        timeline_config.behavior.lazy_redraw = False  # Disable lazy redraw for debugging


        self.timeline_panel = TimelinePanel(
            pygame.Rect(320, 450, 1070, 440),
            self.ui_manager,
            timeline_config
        )

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

        self.timeline_panel.theme_manager.themed_colors = color_mappings

        # Viewport area (right side)
        self.viewport_rect = pygame.Rect(320, 10, 1070, 430)

    def _update_hierarchy_panel(self):
        """Update hierarchy panel with current skeleton"""
        hierarchy_nodes = self.skeleton_system.create_hierarchy_nodes()
        if hierarchy_nodes:
            self.hierarchy_panel.root_node = hierarchy_nodes[0]
            self.hierarchy_panel.rebuild_ui()

    def _update_property_panel(self):
        """Update property panel with selected bone properties"""
        if self.skeleton_system.selected_bone:
            properties = self.skeleton_system.create_property_schemas(self.skeleton_system.selected_bone)
            self.property_panel.set_properties(properties, self.skeleton_system.selected_bone)
        else:
            self.property_panel.set_properties([], None)

    def _update_timeline_panel(self):
        """Update timeline panel with animation clip"""
        # Recreate the animation clip to ensure fresh state
        self.animation_clip = self.skeleton_system.create_animation_clip()

        # Add some default keyframes for testing
        self._add_default_keyframes()

        # Set the clip on timeline FIRST
        self.timeline_panel.set_clip(self.animation_clip)

        # Set the frame change callback
        self.timeline_panel.set_frame_change_callback(self._on_frame_changed)

        # Force complete timeline rebuild
        self.timeline_panel.setup_layout()

        # Clear any cached state that might interfere
        self.timeline_panel._last_rebuild_state = None
        self.timeline_panel.scroll_x = 0
        self.timeline_panel.scroll_y = 0
        self.timeline_panel.zoom = 3.0

        # Force immediate rebuild of the image
        self.timeline_panel.rebuild_image()

        # Set initial frame to ensure playhead is visible
        self.timeline_panel.set_current_frame(0.0)

        # Additional debug to verify the setup
        if SKELETON_DEBUG:
            print(f"Timeline updated:")
            print(f"  Clip: {self.animation_clip.name}")
            print(f"  Layers: {len(self.animation_clip.layers)}")
            print(f"  Current frame: {self.timeline_panel.current_frame}")
            print(f"  Timeline rect: {self.timeline_panel.timeline_rect}")
            print(f"  Zoom: {self.timeline_panel.zoom}")

            # Verify keyframes are accessible
            for layer in self.animation_clip.layers:
                total_kf = sum(len(curve.keyframes) for curve in layer.curves)
                if total_kf > 0:
                    print(f"  Layer '{layer.name}': {total_kf} keyframes, visible: {layer.visible}")

    def _on_frame_changed(self, frame: float):
        """Handle frame changes from timeline"""
        self.current_frame = frame

        # Apply animation to all bones
        for bone_id, bone in self.skeleton_system.bones.items():
            layer = self.animation_clip.get_layer(bone_id)
            if layer:
                for curve in layer.curves:
                    value = curve.get_value_at_frame(frame)
                    if value is not None and hasattr(bone, curve.property_name):
                        setattr(bone, curve.property_name, value)

        # Update property panel if bone is selected (but don't cause rebuild loop)
        if self.skeleton_system.selected_bone:
            # Just update the values without rebuilding
            for prop_id, renderer in self.property_panel.renderers.items():
                if hasattr(self.skeleton_system.selected_bone, prop_id):
                    new_value = getattr(self.skeleton_system.selected_bone, prop_id)
                    renderer.property.value = new_value
            # Only rebuild the image, not the full UI
            self.property_panel.rebuild_image()

    def _on_property_changed(self, prop_id: str, old_value: Any, new_value: Any):
        """Handle property changes from the property panel"""
        if self.skeleton_system.selected_bone:
            bone = self.skeleton_system.selected_bone

            if hasattr(bone, prop_id):
                setattr(bone, prop_id, new_value)

                if SKELETON_DEBUG:
                    print(f"Updated {bone.name}.{prop_id} = {new_value}")

    def _on_bone_selected(self, bone: Bone):
        """Handle bone selection"""
        # Avoid spamming if bone is already selected
        if self.skeleton_system.selected_bone == bone:
            return

        self.skeleton_system.select_bone(bone.id)
        self._update_property_panel()

        # Update hierarchy panel selection
        self.hierarchy_panel.set_selected_node(bone.id)

        if SKELETON_DEBUG:
            print(f"Selected bone: {bone.name} ({bone.id})")

    def _on_bone_deselected(self):
        """Handle bone deselection"""
        if self.skeleton_system.selected_bone:
            if SKELETON_DEBUG:
                print(f"Deselected bone: {self.skeleton_system.selected_bone.name}")

            self.skeleton_system.deselect_bone()
            self._update_property_panel()

            # Clear hierarchy panel selection
            if hasattr(self.hierarchy_panel, 'selected_node'):
                self.hierarchy_panel.selected_node = None
                self.hierarchy_panel.rebuild_ui()

    def _add_keyframe_for_selected_bone(self):
        """Add keyframe for selected bone at current frame"""
        if not self.skeleton_system.selected_bone:
            print("No bone selected")
            return

        bone = self.skeleton_system.selected_bone
        frame = int(self.current_frame)

        # Add keyframes for all animatable properties
        animatable_props = ["position_x", "position_y", "rotation", "length"]

        added_any = False
        for prop_name in animatable_props:
            if hasattr(bone, prop_name):
                value = getattr(bone, prop_name)
                success = self.timeline_panel.add_keyframe(
                    bone.id, prop_name, frame, value, InterpolationType.LINEAR
                )
                if success:
                    added_any = True
                    if SKELETON_DEBUG:
                        print(f"Added keyframe: {bone.name}.{prop_name} = {value} @ frame {frame}")

        if added_any:
            # IMPORTANT: Force timeline to rebuild after adding keyframes
            self.timeline_panel._last_rebuild_state = None
            self.timeline_panel.rebuild_image()
            print(f"Added keyframes for {bone.name} at frame {frame}")
        else:
            print(f"Failed to add keyframes for {bone.name}")

    def _force_timeline_refresh(self):
        """Force a complete timeline refresh"""
        if self.timeline_panel and self.animation_clip:
            # Clear all cached state
            self.timeline_panel._last_rebuild_state = None

            # Rebuild layout and image
            self.timeline_panel.setup_layout()
            self.timeline_panel.rebuild_image()

            if SKELETON_DEBUG:
                print("Forced timeline refresh")

    def _reset_to_bind_pose(self):
        """Reset all bones to their default bind pose"""
        # Reset skeleton to default state
        self.skeleton_system = SkeletonSystem()
        self.animation_clip = self.skeleton_system.create_animation_clip()

        # Update UI
        self._update_hierarchy_panel()
        self._update_property_panel()
        self._update_timeline_panel()

        print("Reset to bind pose")

    def _add_default_keyframes(self):
        """Add some default keyframes for testing"""
        # Add keyframes for multiple bones to make animation more visible
        test_bones = ["hip", "left_thigh", "right_thigh", "spine1"]

        for bone_id in test_bones:
            bone = self.skeleton_system.get_bone(bone_id)
            layer = self.animation_clip.get_layer(bone_id)

            if bone and layer:
                # Add rotation keyframes
                rotation_curve = layer.get_curve("rotation")
                if rotation_curve:
                    if bone_id == "hip":
                        rotation_curve.add_keyframe(Keyframe(0, 0.0, InterpolationType.LINEAR))
                        rotation_curve.add_keyframe(Keyframe(30, 15.0, InterpolationType.EASE_IN_OUT))
                        rotation_curve.add_keyframe(Keyframe(60, -15.0, InterpolationType.EASE_IN_OUT))
                        rotation_curve.add_keyframe(Keyframe(90, 0.0, InterpolationType.LINEAR))
                    elif bone_id == "left_thigh":
                        rotation_curve.add_keyframe(Keyframe(0, 90.0, InterpolationType.LINEAR))
                        rotation_curve.add_keyframe(Keyframe(30, 110.0, InterpolationType.EASE_IN_OUT))
                        rotation_curve.add_keyframe(Keyframe(60, 70.0, InterpolationType.EASE_IN_OUT))
                        rotation_curve.add_keyframe(Keyframe(90, 90.0, InterpolationType.LINEAR))
                    elif bone_id == "right_thigh":
                        rotation_curve.add_keyframe(Keyframe(0, 90.0, InterpolationType.LINEAR))
                        rotation_curve.add_keyframe(Keyframe(30, 70.0, InterpolationType.EASE_IN_OUT))
                        rotation_curve.add_keyframe(Keyframe(60, 110.0, InterpolationType.EASE_IN_OUT))
                        rotation_curve.add_keyframe(Keyframe(90, 90.0, InterpolationType.LINEAR))
                    elif bone_id == "spine1":
                        rotation_curve.add_keyframe(Keyframe(0, -90.0, InterpolationType.LINEAR))
                        rotation_curve.add_keyframe(Keyframe(45, -80.0, InterpolationType.EASE_IN_OUT))
                        rotation_curve.add_keyframe(Keyframe(90, -100.0, InterpolationType.LINEAR))

                # Add position keyframes for hip
                if bone_id == "hip":
                    pos_x_curve = layer.get_curve("position_x")
                    pos_y_curve = layer.get_curve("position_y")

                    if pos_x_curve:
                        pos_x_curve.add_keyframe(Keyframe(0, bone.position_x, InterpolationType.LINEAR))
                        pos_x_curve.add_keyframe(Keyframe(30, bone.position_x + 20, InterpolationType.EASE_IN_OUT))
                        pos_x_curve.add_keyframe(Keyframe(60, bone.position_x - 20, InterpolationType.EASE_IN_OUT))
                        pos_x_curve.add_keyframe(Keyframe(90, bone.position_x, InterpolationType.LINEAR))

                    if pos_y_curve:
                        pos_y_curve.add_keyframe(Keyframe(0, bone.position_y, InterpolationType.LINEAR))
                        pos_y_curve.add_keyframe(Keyframe(15, bone.position_y - 10, InterpolationType.EASE_OUT))
                        pos_y_curve.add_keyframe(Keyframe(75, bone.position_y + 10, InterpolationType.EASE_IN))
                        pos_y_curve.add_keyframe(Keyframe(90, bone.position_y, InterpolationType.LINEAR))

        if SKELETON_DEBUG:
            total_keyframes = sum(
                len(curve.keyframes) for layer in self.animation_clip.layers for curve in layer.curves)
            print(f"Added {total_keyframes} default keyframes across {len(self.animation_clip.layers)} layers")

            # Debug each layer
            for layer in self.animation_clip.layers:
                layer_keyframes = sum(len(curve.keyframes) for curve in layer.curves)
                if layer_keyframes > 0:
                    print(f"  {layer.name}: {layer_keyframes} keyframes")

    def run(self):
        """Main application loop"""
        while self.running:

            time_delta = self.clock.tick(60) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_a:
                        self._add_keyframe_for_selected_bone()
                    elif event.key == pygame.K_r:
                        self._reset_to_bind_pose()
                    elif event.key == pygame.K_SPACE:
                        # Toggle playback
                        # self.timeline_panel._handle_key_event(event)
                        # self.timeline_panel._toggle_playback()
                        if self.timeline_panel.playback_state == PlaybackState.STOPPED or \
                           self.timeline_panel.playback_state == PlaybackState.PAUSED:
                            self.timeline_panel.playback_state = PlaybackState.PLAYING
                        else:
                            self.timeline_panel.playback_state = PlaybackState.PAUSED
                        ...

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Left click
                        # Check if click is in viewport
                        if self.viewport_rect.collidepoint(event.pos):
                            # Convert to viewport-relative coordinates
                            viewport_pos = (event.pos[0] - self.viewport_rect.x,
                                            event.pos[1] - self.viewport_rect.y)

                            # Find bone at position
                            clicked_bone = self.skeleton_renderer.get_bone_at_position(
                                self.skeleton_system, viewport_pos)

                            if clicked_bone:
                                self._on_bone_selected(clicked_bone)
                            else:
                                # FIXED: Deselect bone when clicking empty space
                                self._on_bone_deselected()

                # Handle hierarchy panel events
                elif event.type == UI_HIERARCHY_NODE_SELECTED:
                    node = event.node
                    if node and "bone" in node.data:
                        bone = node.data["bone"]
                        self._on_bone_selected(bone)

                elif event.type == UI_HIERARCHY_NODE_DESELECTED:
                    # FIXED: Handle deselection from hierarchy panel
                    self._on_bone_deselected()

                # Handle timeline events
                elif event.type == UI_TIMELINE_FRAME_CHANGED:
                    self._on_frame_changed(event.frame)

                elif event.type == UI_TIMELINE_KEYFRAME_ADDED:
                    if SKELETON_DEBUG:
                        print(f"Keyframe added: {event.layer_id}.{event.property_name} @ {event.frame}")

                # Forward to UI manager
                self.ui_manager.process_events(event)
            self.ui_manager.update(time_delta)

            # Clear screen
            self.screen.fill((40, 40, 40))

            # Draw viewport background
            pygame.draw.rect(self.screen, (50, 50, 50), self.viewport_rect)
            pygame.draw.rect(self.screen, (100, 100, 100), self.viewport_rect, 2)

            # Create viewport surface for skeleton rendering
            try:
                viewport_surface = self.screen.subsurface(self.viewport_rect)
                # Draw skeleton
                self.skeleton_renderer.draw_skeleton(viewport_surface, self.skeleton_system)
            except (ValueError, pygame.error) as e:
                if SKELETON_DEBUG:
                    print(f"Error creating viewport subsurface: {e}")
                # Fallback: draw directly on screen with clipping
                self.screen.set_clip(self.viewport_rect)
                # Adjust drawing offset
                offset_x, offset_y = self.viewport_rect.x, self.viewport_rect.y
                # This would require modifying the skeleton renderer to handle offsets
                # For now, just continue without the skeleton display
                self.screen.set_clip(None)

            # Draw frame info
            font = pygame.font.Font(None, 24)
            frame_text = f"Frame: {self.current_frame:.1f}"
            text_surface = font.render(frame_text, True, pygame.Color(255, 255, 255))
            self.screen.blit(text_surface, (self.viewport_rect.x + 10, self.viewport_rect.y + 10))

            # Draw selected bone info
            if self.skeleton_system.selected_bone:
                bone = self.skeleton_system.selected_bone
                info_lines = [
                    f"Selected: {bone.name}",
                    f"Position: ({bone.position_x:.1f}, {bone.position_y:.1f})",
                    f"Rotation: {bone.rotation:.1f}°",
                    f"Length: {bone.length:.1f}"
                ]

                y_offset = 40
                for line in info_lines:
                    text_surface = font.render(line, True, pygame.Color(255, 255, 100))
                    self.screen.blit(text_surface, (self.viewport_rect.x + 10, self.viewport_rect.y + y_offset))
                    y_offset += 25
            else:
                # Show deselected state
                text_surface = font.render("No bone selected - click to select", True, pygame.Color(200, 200, 200))
                self.screen.blit(text_surface, (self.viewport_rect.x + 10, self.viewport_rect.y + 40))

            # Draw help text
            help_font = pygame.font.Font(None, 16)
            help_lines = [
                "Controls:",
                "A - Add keyframe",
                "R - Reset to bind pose",
                "Space - Play/pause",
                "Click bones to select",
                "Click empty space to deselect"
            ]

            y_offset = self.viewport_rect.bottom - 120
            for line in help_lines:
                text_surface = help_font.render(line, True, pygame.Color(200, 200, 200))
                self.screen.blit(text_surface, (self.viewport_rect.x + 10, y_offset))
                y_offset += 18

            # Draw UI
            self.ui_manager.draw_ui(self.screen)
            pygame.display.flip()

        pygame.quit()


def main():
    """Run the skeleton animation tool"""
    app = SkeletonAnimationTool()
    app.run()


if __name__ == "__main__":
    main()